"""lib.py — shared extractors and model providers for runner.py / grader.py.

Stdlib only. Needs `pdftotext`/`pdftoppm` (poppler) on PATH for PDF worlds.
"""

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------- extractors

TEXT_EXTS = {".txt", ".md", ".json", ".csv", ".html", ".xml", ".yml", ".yaml"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_PDF_PAGES = 4
MAX_TEXT_CHARS = 20000


def text_block(text):
    return {"type": "text", "text": text[:MAX_TEXT_CHARS]}


def image_block(data, media_type):
    return {"type": "image", "media_type": media_type, "data": data}


def extract(path):
    """Return a list of content blocks (text/image) representing the file."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext in TEXT_EXTS or ext == "":
        try:
            return [text_block(path.read_text(errors="replace"))]
        except Exception as e:
            return [text_block(f"<unreadable: {e}>")]
    if ext in IMAGE_EXTS:
        return [load_image(path)]
    if ext == ".pdf":
        return extract_pdf(path)
    if ext == ".docx":
        return [text_block(extract_docx(path))]
    if ext == ".xlsx":
        return [text_block(extract_xlsx(path))]
    return [text_block(f"<binary file: {path.name}, {path.stat().st_size} bytes>")]



def load_image(path, max_dim=1500):
    """Image file -> block, downscaled to API-safe dimensions (many-image limit is 2000px)."""
    import io
    from PIL import Image
    img = Image.open(path)
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=85)
    return image_block(base64.b64encode(buf.getvalue()).decode(), "image/jpeg")


def extract_pdf(path):
    try:
        out = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, timeout=30)
        text = out.stdout.decode(errors="replace").strip()
    except Exception:
        text = ""
    if len(text) > 40:
        return [text_block(text)]
    # image-based pdf: render pages to png
    import tempfile
    blocks = [text_block(f"<{path.name}: scanned pdf, pages rendered as images>")]
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            ["pdftoppm", "-png", "-r", "100", "-l", str(MAX_PDF_PAGES), str(path), td + "/p"],
            capture_output=True, timeout=60,
        )
        for page in sorted(Path(td).glob("p*.png")):
            blocks.append(load_image(page))
    return blocks


def extract_docx(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode(errors="replace")
        xml = re.sub(r"</w:p>", "\n", xml)
        return re.sub(r"<[^>]+>", "", xml)
    except Exception as e:
        return f"<unreadable docx: {e}>"


def extract_xlsx(path):
    try:
        with zipfile.ZipFile(path) as z:
            shared = []
            if "xl/sharedStrings.xml" in z.namelist():
                sxml = z.read("xl/sharedStrings.xml").decode(errors="replace")
                shared = [re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<si>(.*?)</si>", sxml, re.S)]
            lines = []
            sheets = [n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n)]
            for name in sorted(sheets):
                xml = z.read(name).decode(errors="replace")
                for row in re.findall(r"<row[^>]*>(.*?)</row>", xml, re.S):
                    cells = []
                    for t, v in re.findall(r'<c[^>]*?(?: t="(\w+)")?[^>]*>.*?<v>(.*?)</v>', row, re.S):
                        if t == "s" and v.isdigit() and int(v) < len(shared):
                            cells.append(shared[int(v)])
                        else:
                            cells.append(v)
                    if cells:
                        lines.append(" | ".join(cells))
            return "\n".join(lines) or "<empty xlsx>"
    except Exception as e:
        return f"<unreadable xlsx: {e}>"


# ---------------------------------------------------------------- providers

def http_json(url, headers, payload, retries=4):
    body = json.dumps(payload).encode()
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503, 529) and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"    [{e.code}] retrying in {wait}s: {detail[:120]}", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {e.code}: {detail}")
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
            if attempt < retries - 1:
                print(f"    [net: {type(e).__name__}] retrying", file=sys.stderr)
                continue
            raise
    raise RuntimeError("unreachable")


class Anthropic:
    def __init__(self, model):
        self.model = model
        self.key = os.environ["ANTHROPIC_API_KEY"]
        self.url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/") + "/v1/messages"
        self.messages = []

    def add_user(self, blocks):
        content = [self._block(b) for b in blocks]
        self.messages.append({"role": "user", "content": content})

    def add_tool_results(self, results):
        content = []
        for call_id, blocks in results:
            content.append({"type": "tool_result", "tool_use_id": call_id,
                            "content": [self._block(b) for b in blocks]})
        self.messages.append({"role": "user", "content": content})

    @staticmethod
    def _block(b):
        if b["type"] == "image":
            return {"type": "image", "source": {"type": "base64", "media_type": b["media_type"], "data": b["data"]}}
        return b

    def call(self, system, tools, force_tool=None):
        payload = {
            "model": self.model, "max_tokens": 8192, "temperature": 0,
            "system": system, "messages": self.messages,
            "tools": [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools],
        }
        if force_tool:
            payload["tool_choice"] = {"type": "tool", "name": force_tool}
        resp = http_json(self.url, {
            "content-type": "application/json", "x-api-key": self.key, "anthropic-version": "2023-06-01",
        }, payload)
        self.messages.append({"role": "assistant", "content": resp["content"]})
        text = "".join(c.get("text", "") for c in resp["content"] if c["type"] == "text")
        calls = [{"id": c["id"], "name": c["name"], "args": c["input"]}
                 for c in resp["content"] if c["type"] == "tool_use"]
        return text, calls


class OpenAICompat:
    def __init__(self, model, base_url):
        self.model = model
        self.key = os.environ.get("XAI_API_KEY") or os.environ["OPENAI_API_KEY"]
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.messages = []
        self.system = None

    def add_user(self, blocks):
        self.messages.append({"role": "user", "content": self._content(blocks)})

    def add_tool_results(self, results):
        # openai tool messages are text-only; images ride in a follow-up user message
        pending_images = []
        for call_id, blocks in results:
            texts = [b["text"] for b in blocks if b["type"] == "text"]
            images = [b for b in blocks if b["type"] == "image"]
            if images:
                texts.append(f"[{len(images)} image(s) attached in the next message]")
                pending_images.extend(images)
            self.messages.append({"role": "tool", "tool_call_id": call_id, "content": "\n".join(texts) or "(no output)"})
        if pending_images:
            self.messages.append({"role": "user", "content": self._content(pending_images)})

    @staticmethod
    def _content(blocks):
        out = []
        for b in blocks:
            if b["type"] == "image":
                uri = f"data:{b['media_type']};base64,{b['data']}"
                out.append({"type": "image_url", "image_url": {"url": uri}})
            else:
                out.append({"type": "text", "text": b["text"]})
        return out

    def call(self, system, tools, force_tool=None):
        msgs = [{"role": "system", "content": system}] + self.messages
        payload = {
            "model": self.model, "messages": msgs, "max_tokens": 8192, "temperature": 0,
            "tools": [{"type": "function", "function": t} for t in tools],
        }
        if force_tool:
            payload["tool_choice"] = {"type": "function", "function": {"name": force_tool}}
        resp = http_json(self.url, {
            "content-type": "application/json", "authorization": f"Bearer {self.key}",
        }, payload)
        msg = resp["choices"][0]["message"]
        self.messages.append(msg)
        calls = []
        for tc in msg.get("tool_calls") or []:
            calls.append({"id": tc["id"], "name": tc["function"]["name"],
                          "args": json.loads(tc["function"]["arguments"] or "{}")})
        return msg.get("content") or "", calls


def make_provider(provider, model, base_url="https://api.x.ai/v1"):
    if provider == "anthropic":
        return Anthropic(model)
    return OpenAICompat(model, base_url)


def add_provider_args(parser):
    parser.add_argument("--provider", choices=["anthropic", "openai"], default="anthropic")
    parser.add_argument("--model", default="claude-sonnet-5")
    parser.add_argument("--base-url", default="https://api.x.ai/v1",
                        help="OpenAI-compatible endpoint (xAI: https://api.x.ai/v1)")


def one_shot(provider, model, base_url, system, prompt_blocks, force_json=False, schema=None):
    """Single stateless LLM call. Returns text; with force_json, forces the answer
    through a schema-carrying tool call so the API guarantees valid, shaped JSON."""
    p = make_provider(provider, model, base_url)
    p.add_user(prompt_blocks)
    if not force_json:
        text, _ = p.call(system, [])
        return text
    emit = {"name": "emit_json",
            "description": "Emit the complete final result. Every field filled — never empty.",
            "parameters": schema or {"type": "object", "additionalProperties": True}}
    system = system + "\n\nCall emit_json exactly once with the COMPLETE result as its argument."
    text, calls = p.call(system, [emit], force_tool="emit_json")
    for c in calls:
        if c["name"] == "emit_json" and c["args"]:
            return c["args"]
    raise ValueError(f"model returned no/empty emit_json: {text[:300]}")


