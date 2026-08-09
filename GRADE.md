# GRADE.md — grade the work in this world against its verifiers

You are an agent inside a coding harness. The current working directory is a twin world
(`task.json` + `filesystem/`), and deliverables have been written to `filesystem/output/`.
Grade them.

```bash
[ -d twin-pipeline ] || git clone https://github.com/Emericen/grok-hackathon twin-pipeline
python3 twin-pipeline/scripts/grader.py . --in-place
```

That's the entire job: run it, show the user the full colored output — every verifier's
PASS/FAIL with its rationale — and then summarize in one sentence how many criteria
failed and which ones.

Rules:
- Do NOT judge the criteria yourself; the grader script is the reward function and its
  verdict is final. Your judgment was already tested — that's what's being graded.
- Do NOT edit the deliverables, task.json, or the grader before or after grading.
- If the grader errors, show the error verbatim; do not improvise a grade.
