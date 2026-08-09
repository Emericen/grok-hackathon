#!/usr/bin/env python3
r"""pipeline.py — the factory: trace in, twin world out.

USAGE
    python pipeline.py dirty/case-run/transcript.jsonl \
        --case path/to/real-case \         # the real files (dirty room, never ships)
        --correction dirty/correction.md \  # the expert's fix, freeform text
        --out worlds/my-twin

STAGES
    1. PARSE       trace (runner.py or Claude Code jsonl) -> digest; real case dir -> raw manifest.
    2. SUBSTITUTE  one LLM call -> substitution map (real -> fake, constraints preserved).
                   Written to dirty/substitution_map.json. NEVER ships.
    3. FABRICATE   launches the SAME runner.py agent loop, one shot: the fabricator agent
                   reads real_case/ and writes twin files into filesystem/, applying the map.
                   Text formats are written directly; scanned-look documents are written as
                   <name>.render.json specs, which the pipeline then template-renders to
                   images with PIL. (--fab-model picks the fabricator model.)
    4. VERIFY-GEN  one LLM call: trace digest + correction + twin listing -> task.json
                   (task prompt + verifiers, incl. coverage/negative types).
    5. PACKAGE     substitution scan — packaging FAILS if any real entity survives —
                   then write worlds/<id>/{filesystem/, task.json, manifest.json}.

Model knobs: --fab-* for the fabricator agent, top-level --provider/--model for the
one-shot calls (map + verifiers). The model under test is chosen later, at runner time.
"""

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

from lib import add_provider_args, extract, one_shot, text_block
from runner import run_agent

# ------------------------------------------------------------------ stage 1

def parse_trace(path, cap=24000):
    """Tolerant digest of a runner.py or Claude Code transcript jsonl."""
    lines = []
    for raw in Path(path).read_text().splitlines():
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue
        # runner.py format
        if "role" in d:
            if d["role"] == "user":
                lines.append(f"USER: {d.get('text', '')[:600]}")
            elif d["role"] == "assistant":
                for c in d.get("calls", []):
                    lines.append(f"AGENT calls {c['name']}: {json.dumps(c['args'], ensure_ascii=False)[:200]}")
                if d.get("text"):
                    lines.append(f"AGENT: {d['text'][:400]}")
            elif d["role"] == "tool":
                lines.append(f"RESULT: {d.get('result', '')[:300]}")
            continue
        # Claude Code format
        msg = d.get("message") or {}
        content = msg.get("content")
        if d.get("type") == "user" and isinstance(content, str):
            lines.append(f"USER: {content[:600]}")
        elif isinstance(content, list):
            for b in content:
                if b.get("type") == "text":
                    lines.append(f"AGENT: {b['text'][:400]}")
                elif b.get("type") == "tool_use":
                    lines.append(f"AGENT calls {b['name']}: {json.dumps(b.get('input', {}), ensure_ascii=False)[:200]}")
                elif b.get("type") == "tool_result":
                    lines.append(f"RESULT: {json.dumps(b.get('content', ''), ensure_ascii=False)[:300]}")
    digest = "\n".join(lines)
    if len(digest) > cap:
        head = digest[: cap // 2]
        tail = digest[-cap // 2:]
        digest = head + "\n...[trace middle elided]...\n" + tail
    return digest


def raw_manifest(case_dir):
    files = [p for p in Path(case_dir).rglob("*") if p.is_file() and not p.name.startswith(".")]
    types = {}
    for p in files:
        ext = p.suffix.lower() or "(none)"
        types[ext] = types.get(ext, 0) + 1
    tree = sorted(str(p.relative_to(case_dir)) for p in files)
    return {"files": len(files), "types": types, "tree": tree}



def valid_map(m):
    if not isinstance(m, dict) or not isinstance(m.get("entities"), list):
        return False
    ents = m["entities"]
    if len(ents) < 5:
        return False
    return all(isinstance(e, dict) and isinstance(e.get("real"), str)
               and isinstance(e.get("fake"), str) for e in ents)


def valid_task(t):
    if not isinstance(t, dict) or not isinstance(t.get("task"), str):
        return False
    vs = t.get("verifiers")
    if not isinstance(vs, list) or not vs:
        return False
    return all(isinstance(v, dict) and isinstance(v.get("criteria"), str)
               and v.get("type") in ("output", "negative", "coverage") for v in vs)


def one_shot_valid(validate, *args, **kwargs):
    """one_shot + structural validation; retry because tool-input schemas are advisory."""
    for attempt in range(3):
        result = one_shot(*args, **kwargs)
        if validate(result):
            return result
        print(f"    malformed structure (attempt {attempt + 1}/3), retrying", file=sys.stderr)
    sys.exit("structured call kept returning malformed output — aborting")


# ------------------------------------------------------------------ stage 2

MAP_SYSTEM = """You build substitution maps for anonymizing professional case files. Given an \
agent trace, a file tree, extracted case-file text, and an expert correction, list every \
real-world entity that must be replaced (people, companies, ID/registration numbers, project \
names and codes, addresses, account numbers, distinctive amounts, filenames containing names) \
and invent a consistent fabricated replacement for each.

Map the CASE, exhaustively: every named party, every identifier, every project name/code, and \
every distinctive amount appearing in the case-file text or the correction gets an entry. The \
operator's own machine details in the trace (usernames, local paths) are not case entities — \
ignore them; they never ship.

Preserve every constraint the case's traps depend on: replacement IDs keep format and length, \
dates keep their ordering and relative intervals, amounts that must reconcile still reconcile \
(state the arithmetic in constraints), names stay plausible for the locale and keep the same \
script (Chinese stays Chinese). Also propose a substituted filename for every tree entry whose \
name leaks an entity.

Respond with JSON only:
{"entities": [{"real": "...", "fake": "...", "kind": "person|org|id|amount|date|address|other",
               "constraints": "..."}],
 "filenames": {"<real relative path>": "<twin relative path>"},
 "notes": "constraints that span entities"}"""



MAP_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {"type": "array", "items": {
            "type": "object",
            "properties": {"real": {"type": "string"}, "fake": {"type": "string"},
                           "kind": {"type": "string"}, "constraints": {"type": "string"}},
            "required": ["real", "fake", "kind"]}},
        "filenames": {"type": "object", "additionalProperties": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["entities", "filenames"],
}

# ------------------------------------------------------------------ stage 3

FAB_TASK = """You are fabricating an anonymized TWIN of a real case. The real files are in \
real_case/ (read-only reference). Write the twin into filesystem/ — one twin file for every \
real file, same disorder, same traps, every real-world fact replaced per the substitution map \
below.

Rules:
- Apply the substitution map EXACTLY and CONSISTENTLY — the same real entity always becomes \
the same fake entity, across every file. Use the mapped filenames.
- Preserve structure: if the real file is a messy scan of a two-page form, the twin says so; \
if amounts reconcile across files, the twin's amounts reconcile identically (the map's \
constraints tell you the arithmetic).
- Text-like files (txt, md, csv, docx, xlsx content): write the twin content directly as a \
text file with the same meaning and layout. For docx/xlsx, write a .md or .csv twin — \
format fidelity matters less than content fidelity.
- Image or scanned files (jpg, png, image-based pdf): do NOT write an image. Write \
`<twin name>.render.json` instead: {"filename": "<twin name>.png", "doc_type": "...", \
"title": "<document title, original language>", "fields": [["label", "value"], ...], \
"stamp": "<seal/stamp text or null>"}. Every visible fact from the real document appears \
in fields, substituted.
- Read every real file before writing its twin. Do not invent facts with no real counterpart.
- Before calling done, SELF-SCAN: grep filesystem/ (contents AND filenames) for every "real" \
string in the map. Any hit means you missed a substitution — fix it. Packaging will hard-fail \
on any surviving real entity, so do not call done while a hit remains.

SUBSTITUTION MAP:
{map_json}

When every real file has a twin in filesystem/, call done."""


def render_specs(fs_dir):
    """Turn every *.render.json the fabricator left into a document-looking PNG."""
    from PIL import Image, ImageDraw, ImageFont

    def font(size):
        for path in ("/System/Library/Fonts/PingFang.ttc",
                     "/System/Library/Fonts/STHeiti Medium.ttc",
                     "/System/Library/Fonts/Helvetica.ttc"):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    for spec_path in sorted(Path(fs_dir).rglob("*.render.json")):
        spec = json.loads(spec_path.read_text())
        rows = spec.get("fields", [])
        height = 260 + 64 * len(rows) + (120 if spec.get("stamp") else 0)
        img = Image.new("RGB", (1400, height), "#f4f1ea")
        draw = ImageDraw.Draw(img)
        draw.rectangle([30, 30, 1370, height - 30], outline="#8a8578", width=3)
        draw.text((70, 70), spec.get("title", spec.get("doc_type", "")), fill="#1a1a1a", font=font(52))
        y = 190
        for label, value in rows:
            draw.text((90, y), str(label), fill="#555046", font=font(30))
            draw.text((520, y), str(value), fill="#111", font=font(34))
            y += 64
        if spec.get("stamp"):
            draw.ellipse([1020, y - 20, 1300, y + 90], outline="#b03a2e", width=5)
            draw.text((1060, y + 10), spec["stamp"][:14], fill="#b03a2e", font=font(30))
        out = spec_path.with_name(spec["filename"])
        img.save(out)
        spec_path.unlink()
        print(f"  rendered {out.name}")


# ------------------------------------------------------------------ stage 4

VERIFY_SYSTEM = """You write evaluation tasks for anonymized twin worlds. Given the original \
agent trace, the expert's correction, and the twin's file listing, produce the task an agent \
will be given and the verifiers that decide pass/fail.

The task must mirror the original ask, phrased for the twin's fabricated facts, with concrete \
deliverable files under filesystem/output/. Each verifier is ONE plain-English criterion \
judged against the final files. Derive them from the expert's correction — each one a trap \
the expert caught. Include:
- output criteria for each thing the correction says must be present,
- exactly one negative criterion ("did NOT ...") for fabrication/concealment,
- a coverage criterion ("every file in <dir> is accounted for") ONLY if the correction \
implies completeness, with "enumerate" set to that dir relative to filesystem/.
CRITICAL: criteria must reference ONLY the twin's fabricated names, amounts, and dates — read
them from the twin file contents provided. The trace and correction contain the REAL values;
translate every one through the substitution map. A criterion naming a real entity is a
privacy leak and will fail packaging.

Respond with JSON only:
{"task": "...", "verifiers": [{"id": "kebab-slug", "type": "output|negative|coverage",
                               "criteria": "...", "enumerate": "<dir, coverage only>"}]}"""



VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {"type": "string"},
        "verifiers": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "string"},
                           "type": {"type": "string", "enum": ["output", "negative", "coverage"]},
                           "criteria": {"type": "string"}, "enumerate": {"type": "string"}},
            "required": ["id", "type", "criteria"]}},
    },
    "required": ["task", "verifiers"],
}

# ------------------------------------------------------------------ stage 5

def substitution_scan(fs_dir, sub_map):
    """Fail packaging if any real entity string survives in the twin's text files."""
    reals = [e["real"] for e in sub_map["entities"]
             if len(e["real"]) >= 4 and e["real"] != e.get("fake")]
    hits = []
    for p in Path(fs_dir).rglob("*"):
        if not p.is_file():
            continue
        try:
            content = p.read_bytes().decode("utf-8", errors="ignore")
        except OSError:
            continue
        for real in reals:
            if real in content or real in p.name:
                hits.append((str(p.relative_to(fs_dir)), real))
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trace", help="transcript.jsonl from runner.py, or a Claude Code session jsonl")
    ap.add_argument("--case", required=True, help="the real case directory")
    ap.add_argument("--correction", required=True, help="file with the expert's fix, freeform")
    ap.add_argument("--out", required=True, help="twin world output dir, e.g. worlds/my-twin")
    ap.add_argument("--fab-provider", choices=["anthropic", "openai"])
    ap.add_argument("--fab-model")
    ap.add_argument("--fab-base-url")
    ap.add_argument("--fab-max-steps", type=int, default=80)
    add_provider_args(ap)
    args = ap.parse_args()
    fab_provider = args.fab_provider or args.provider
    fab_model = args.fab_model or args.model
    fab_base_url = args.fab_base_url or args.base_url

    out = Path(args.out)
    if out.exists():
        sys.exit(f"{out} already exists — refusing to overwrite a world")
    dirty = Path("dirty")
    dirty.mkdir(exist_ok=True)

    print("[1/5] parse")
    digest = parse_trace(args.trace)
    manifest = raw_manifest(args.case)
    correction = Path(args.correction).read_text()

    print("[2/5] substitution map")
    case_texts = []
    for rel in manifest["tree"]:
        blocks = extract(Path(args.case) / rel)
        text = "\n".join(b["text"] for b in blocks if b["type"] == "text")
        case_texts.append(f"----- {rel} -----\n{text[:2500]}")
    prompt = (f"TRACE:\n{digest}\n\nFILE TREE ({manifest['files']} files):\n"
              + "\n".join(manifest["tree"])
              + "\n\nCASE FILE TEXT (extracted, partial — scanned files yield little):\n\n"
              + "\n\n".join(case_texts)
              + f"\n\nEXPERT CORRECTION:\n{correction}")
    sub_map = one_shot_valid(valid_map, args.provider, args.model, args.base_url,
                              MAP_SYSTEM, [text_block(prompt)], force_json=True, schema=MAP_SCHEMA)
    map_path = dirty / "substitution_map.json"
    map_path.write_text(json.dumps(sub_map, indent=2, ensure_ascii=False))
    print(f"  {len(sub_map['entities'])} entities -> {map_path} (never ships)")

    print(f"[3/5] fabricate ({fab_provider}:{fab_model})")
    fab_dir = dirty / f"fab-{out.name}"
    if fab_dir.exists():
        shutil.rmtree(fab_dir)
    task = FAB_TASK.replace("{map_json}", json.dumps(sub_map, indent=2, ensure_ascii=False))
    run_agent(None, task, fab_dir, fab_provider, fab_model, fab_base_url,
              max_steps=args.fab_max_steps, extra_mount=("real_case", args.case))
    render_specs(fab_dir / "filesystem")

    print("[4/5] task + verifiers")
    fab_fs = fab_dir / "filesystem"
    twin_files = sorted(str(p.relative_to(fab_fs)) for p in fab_fs.rglob("*") if p.is_file())
    twin_contents = []
    for rel in twin_files:
        blocks = extract(fab_fs / rel)
        text = "\n".join(b["text"] for b in blocks if b["type"] == "text")
        twin_contents.append(f"----- {rel} -----\n{text[:3000]}")
    prompt = (f"TRACE (real values — do NOT reuse them):\n{digest}\n\n"
              f"EXPERT CORRECTION (real values — do NOT reuse them):\n{correction}\n\n"
              f"SUBSTITUTION MAP:\n{json.dumps(sub_map, ensure_ascii=False)}\n\n"
              f"TWIN FILE CONTENTS (use THESE names/amounts/dates in criteria):\n\n"
              + "\n\n".join(twin_contents))
    task_json = one_shot_valid(valid_task, args.provider, args.model, args.base_url,
                                VERIFY_SYSTEM, [text_block(prompt)], force_json=True, schema=VERIFY_SCHEMA)

    print("[5/5] package")
    hits = substitution_scan(fab_fs, sub_map)
    task_str = json.dumps(task_json, ensure_ascii=False)
    for e in sub_map["entities"]:
        if len(e["real"]) >= 4 and e["real"] != e.get("fake") and e["real"] in task_str:
            hits.append(("task.json", e["real"]))
    if hits:
        for path, real in hits[:20]:
            print(f"  LEAK: '{real}' in {path}", file=sys.stderr)
        sys.exit("packaging FAILED — real entities survived; twin left in dirty/, nothing shipped")
    out.mkdir(parents=True)
    shutil.copytree(fab_dir / "filesystem", out / "filesystem")
    (out / "task.json").write_text(json.dumps(task_json, indent=2, ensure_ascii=False))
    twin_manifest = {
        "files": len(twin_files),
        "types": {ext: n for ext, n in raw_manifest(out / "filesystem")["types"].items()},
        "tree": twin_files,
        "provenance": {"substitution_scan": "clean", "entities_substituted": len(sub_map["entities"]),
                       "consent": "recorded off-repo", "created": date.today().isoformat()},
    }
    (out / "manifest.json").write_text(json.dumps(twin_manifest, indent=2, ensure_ascii=False))
    print(f"  {out}/ ready: filesystem/ ({len(twin_files)} files), task.json "
          f"({len(task_json['verifiers'])} verifiers), manifest.json")


if __name__ == "__main__":
    main()
