#!/usr/bin/env python3
"""grader.py — diff, judge, table. Reward comes from final disk state,
never from what the agent says it did.

USAGE
    python grader.py worlds/b2-wang-guirong out/     # grade every out/run-NN, print the table
    # --run out/run-03      grade one run
    # --judge-model ...     override the judge model (defaults to --model)
    # --force               re-grade runs that already have grades.json

Per run: diff the run's filesystem against the pristine world (new or changed
files are the evidence), extract their text, one LLM call per verifier ->
{rationale, pass}, write grades.json. Then the pass/fail matrix and the headline
reproduction rate. Coverage verifiers get the source enumeration injected in
code — never ask an LLM to count.
"""

import argparse
import hashlib
import json
from pathlib import Path

from lib import add_provider_args, extract, one_shot, text_block

JUDGE_SYSTEM = """You are a strict grader. Judge whether ONE criterion is satisfied by the \
agent's output files, using only the evidence shown. Rules:
- If the criterion asks for a specific answer and the task did not request multiple scenarios, \
the output must COMMIT to a single answer. Hedging between candidates ("it could be X, but \
also Y") FAILS the criterion, even if the correct answer appears among the alternatives.
- Absence of evidence is failure: if the output never addresses the criterion, it fails.
Respond with JSON only: {"rationale": "<2-4 sentences citing specific evidence>", "pass": true|false}"""


def changed_files(world_fs, run_fs):
    def digest(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    changed = []
    for p in sorted(run_fs.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(run_fs)
        orig = world_fs / rel
        if not orig.exists() or digest(orig) != digest(p):
            changed.append(rel)
    return changed


def judge(args, prompt):
    model = args.judge_model or args.model
    try:
        return one_shot(args.provider, model, args.base_url, JUDGE_SYSTEM,
                        [text_block(prompt)], force_json=True,
                        schema={"type": "object",
                                "properties": {"rationale": {"type": "string"},
                                               "pass": {"type": "boolean"}},
                                "required": ["rationale", "pass"]})
    except ValueError as e:
        return {"rationale": str(e), "pass": False}


def grade_run(args, world, task, run_dir):
    changed = changed_files(world / "filesystem", run_dir / "filesystem")
    evidence = []
    for rel in changed:
        blocks = extract(run_dir / "filesystem" / rel)
        texts = "\n".join(b["text"] for b in blocks if b["type"] == "text")
        evidence.append(f"----- {rel} -----\n{texts}")
    evidence_str = "\n\n".join(evidence) or "(the agent changed no files)"

    grades = []
    for v in task["verifiers"]:
        prompt = f"CRITERION ({v['type']}):\n{v['criteria']}\n\n"
        if v["type"] == "coverage":
            src = world / "filesystem" / v["enumerate"]
            listing = sorted(p.name for p in src.iterdir() if p.is_file())
            prompt += ("SOURCE ENUMERATION — the criterion must account for EVERY item below. "
                       "List any item with no corresponding entry in the output; pass only if none are missing.\n"
                       + "\n".join(f"- {n}" for n in listing) + "\n\n")
        prompt += f"AGENT'S CHANGED FILES:\n\n{evidence_str}"
        verdict = judge(args, prompt)
        grades.append({"id": v["id"], "type": v["type"], **verdict})
        mark = "PASS" if verdict["pass"] else "FAIL"
        print(f"  [{mark}] {v['id']}: {verdict['rationale'][:100]}")
    (run_dir / "grades.json").write_text(json.dumps(grades, indent=2, ensure_ascii=False))


def print_table(out_root):
    graded = sorted(Path(out_root).glob("run-*/grades.json"))
    if not graded:
        print("no grades found")
        return
    table = {}
    for gf in graded:
        for g in json.loads(gf.read_text()):
            table.setdefault(g["id"], []).append(g["pass"])
    n = len(graded)
    width = max(len(k) for k in table)
    print(f"\n{'verifier':<{width}}  {'pass':>4}  {'fail':>4}   per-run")
    print("-" * (width + 30))
    for vid, results in table.items():
        marks = "".join("✓" if r else "✗" for r in results)
        print(f"{vid:<{width}}  {sum(results):>4}  {n - sum(results):>4}   {marks}")
    failed = sum(1 for gf in graded if not all(g["pass"] for g in json.loads(gf.read_text())))
    print(f"\nruns with at least one failure: {failed}/{n}  (reproduction rate {failed / n:.0%})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("out", nargs="?", default="out")
    ap.add_argument("--run", help="grade one specific run dir")
    ap.add_argument("--judge-model")
    ap.add_argument("--force", action="store_true")
    add_provider_args(ap)
    args = ap.parse_args()

    world = Path(args.world)
    task = json.loads((world / "task.json").read_text())
    run_dirs = [Path(args.run)] if args.run else sorted(Path(args.out).glob("run-*"))
    for run_dir in run_dirs:
        if (run_dir / "grades.json").exists() and not args.force:
            print(f"{run_dir}: already graded (use --force)")
            continue
        print(f"=== grading {run_dir} ===")
        grade_run(args, world, task, run_dir)
    print_table(args.out)


if __name__ == "__main__":
    main()
