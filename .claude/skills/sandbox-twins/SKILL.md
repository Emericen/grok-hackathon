---
name: sandbox-twins
description: Turn an expert-corrected AI failure into an anonymized twin world, or grade work in a twin world against its verifiers. Use when the user says "twin this case", "anonymize this case", or "grade this world".
---

# Sandbox twins

Two jobs, each fully specified in one file at the repo root — fetch and follow it
exactly; do not improvise a different procedure.

- **Twin a case** (you are in a case directory, the user has corrected agent work on
  it): follow [TWIN.md](../../../TWIN.md) — identity map, rebuild only identity-bearing
  files, frozen numbers, mandatory `scripts/scan.py` gate.
- **Grade a world** (you are in a twin world with deliverables in `filesystem/output/`):
  follow [GRADE.md](../../../GRADE.md) — run `scripts/grader.py . --in-place`; the
  script's verdict is final.

If the repo isn't on disk: `git clone https://github.com/Emericen/grok-hackathon twin-pipeline`
and read the same two files from there.

Non-negotiables carried by both: the substitution map lives in `dirty/` and never
ships; never present an unscanned twin; never grade by your own judgment instead of
the script.
