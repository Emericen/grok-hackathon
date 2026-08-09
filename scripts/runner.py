#!/usr/bin/env python3
"""runner.py - an agent works a case. Used on BOTH sides of the pipeline:
on a real case to generate the trace, on a twin world to evaluate it, and
(via pipeline.py, as a library) to fabricate twin artifacts.

USAGE
    # real case (dirty room - stays on this machine)
    python runner.py path/to/real-case --task "prepare the filing review" --out dirty/case-run

    # twin world (task read from its task.json), N times for a reproduction rate
    python runner.py worlds/b2-wang-guirong --runs 10 --out out/

    # model selection: --provider anthropic (default, ANTHROPIC_API_KEY)
    #                  --provider openai --base-url https://api.x.ai/v1 --model grok-4  (XAI_API_KEY)

Each run copies the case into a fresh run-NN/filesystem/ (the original is never
touched), gives the agent bash / read_file / write_file / done with paths locked
inside the run dir, and leaves transcript.jsonl - which is the trace format that
pipeline.py ingests.
"""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from lib import add_provider_args, extract, make_provider, text_block

BOLD, DIM, CYAN, GREEN, RESET = "\033[1m", "\033[2m", "\033[36m", "\033[32m", "\033[0m"

SYSTEM_PROMPT = """You are an autonomous agent working a professional case inside a sandboxed \
filesystem. Your working directory is the case root; all paths are relative to it.

Tools:
- bash: run a shell command (ls, grep, mkdir, etc.). Do NOT use it to read documents.
- read_file: read any document - text, images, scanned PDFs, docx, xlsx. Always use this to \
read case files; scanned documents are rendered so you can see them.
- write_file: write a deliverable file.
- done: call when every deliverable is written.

Work the case thoroughly. Read every file before drawing conclusions. Base every claim on a \
document you actually read; if something is inconsistent or unconfirmed, say so explicitly \
in the deliverables rather than guessing."""

TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command in the case directory.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a case file (handles images, scanned PDFs, docx, xlsx).",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write a file (creates parent dirs).",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "done",
        "description": "Declare the task complete.",
        "parameters": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": [],
        },
    },
]


def safe_path(run_dir, rel):
    p = (run_dir / rel).resolve()
    if not str(p).startswith(str(run_dir.resolve())):
        raise ValueError(f"path escapes sandbox: {rel}")
    return p


def exec_tool(run_dir, name, args):
    if name == "bash":
        r = subprocess.run(
            args["command"], shell=True, cwd=run_dir, capture_output=True, timeout=60
        )
        out = (r.stdout + r.stderr).decode(errors="replace")
        return [text_block(out[:8000] or "(no output)")]
    if name == "read_file":
        p = safe_path(run_dir, args["path"])
        if not p.exists():
            return [text_block(f"file not found: {args['path']}")]
        return extract(p)
    if name == "write_file":
        p = safe_path(run_dir, args["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"])
        return [text_block(f"wrote {args['path']} ({len(args['content'])} chars)")]
    return [text_block(f"unknown tool: {name}")]


def run_agent(
    src_fs,
    task_text,
    run_dir,
    provider,
    model,
    base_url,
    max_steps=50,
    system_prompt=SYSTEM_PROMPT,
    extra_mount=None,
):
    """One agent run. Copies src_fs into run_dir/filesystem, loops until done/cap.

    extra_mount: optional (name, path) - a second directory copied into the run dir
    alongside filesystem/ (pipeline.py uses this to expose the real case read-side).
    Returns the run_dir.
    """
    run_dir = Path(run_dir)
    if src_fs is not None:
        shutil.copytree(src_fs, run_dir / "filesystem")
    else:
        (run_dir / "filesystem").mkdir(parents=True)
    if extra_mount is not None:
        name, path = extra_mount
        shutil.copytree(path, run_dir / name)

    agent = make_provider(provider, model, base_url)
    agent.add_user([text_block(task_text)])
    transcript = open(run_dir / "transcript.jsonl", "w")

    def log(**kw):
        transcript.write(json.dumps(kw, ensure_ascii=False) + "\n")
        transcript.flush()

    log(role="user", text=task_text)
    task_preview = " ".join(task_text.split())[:260]
    print(f"{BOLD}task ▸ {task_preview}…{RESET}")
    for step in range(max_steps):
        agent.prune_images()
        text, calls = agent.call(system_prompt, TOOLS)
        log(
            role="assistant",
            text=text,
            calls=[{"name": c["name"], "args": c["args"]} for c in calls],
        )
        if text.strip():
            print(f"  {DIM}[{step}]{RESET} {CYAN}{text.strip()[:160]}{RESET}")
        if not calls or any(c["name"] == "done" for c in calls):
            print(f"  {GREEN}{BOLD}done after {step + 1} steps{RESET}")
            break
        results = []
        for c in calls:
            print(
                f"  {DIM}[{step}] {c['name']}: {json.dumps(c['args'], ensure_ascii=False)[:90]}{RESET}"
            )
            try:
                blocks = exec_tool(run_dir, c["name"], c["args"])
            except Exception as e:
                blocks = [text_block(f"tool error: {e}")]
            results.append((c["id"], blocks))
            log(
                role="tool",
                name=c["name"],
                result="".join(b.get("text", "<image>") for b in blocks)[:2000],
            )
        agent.add_tool_results(results)
    else:
        print(f"  step cap ({max_steps}) reached")
    transcript.close()
    return run_dir


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "case",
        help="a twin world dir (has task.json) or any real case dir (needs --task)",
    )
    ap.add_argument(
        "--task", help="task text; required when the case dir has no task.json"
    )
    ap.add_argument("--out", default="out")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--max-steps", type=int, default=500)
    add_provider_args(ap)
    args = ap.parse_args()

    case = Path(args.case)
    task_file = case / "task.json"
    if task_file.exists():
        task_text = json.loads(task_file.read_text())["task"]
        src_fs = case / "filesystem"
    else:
        if not args.task:
            ap.error(f"{case} has no task.json - pass --task")
        task_text = args.task
        src_fs = case

    out_root = Path(args.out)
    existing = [
        int(p.name.split("-")[1])
        for p in out_root.glob("run-*")
        if p.name.split("-")[1].isdigit()
    ]
    start = max(existing, default=0) + 1
    for n in range(start, start + args.runs):
        run_dir = out_root / f"run-{n:02d}"
        print(f"{BOLD}=== {run_dir} ({args.provider}:{args.model}) ==={RESET}")
        run_agent(
            src_fs,
            task_text,
            run_dir,
            args.provider,
            args.model,
            args.base_url,
            args.max_steps,
        )


if __name__ == "__main__":
    main()
