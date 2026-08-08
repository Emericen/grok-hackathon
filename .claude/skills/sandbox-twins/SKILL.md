---
name: sandbox-twins
description: Turn a real AI-failure moment (agent trace + case files + expert correction) into an anonymized, verifier-scored sandbox twin world that is safe to ship. Use when the user says "twin this case", "anonymize this case into a world", or points at a work directory plus a correction and wants a training/eval world out.
---

# Sandbox twins: real failure in, shippable world out

You are the fabrication brain of the sandbox-twins pipeline. Your harness gives you the
inputs in place: the case files in the working directory, the trace (this or a prior
session's transcript), and the expert's correction. Your job is the judgment work —
mapping, authoring, verifier design. The guarantees are NOT yours to improvise: the
packaging gate and the grader are scripts in this repo, and you MUST run them.

## Inputs (confirm all three before starting)

1. **Case directory** — the real files. Never modified, never shipped.
2. **Correction** — the expert's fix: what was wrong, where the evidence is, why it
   matters. This defines "right". If the user hasn't provided one, ask — a twin
   without a correction has no verifiers worth selling.
3. **Trace** — what the agent saw and did (session jsonl or the current conversation).
   Used to learn where the work went wrong and what the original ask was.

## Stage 1 — substitution map (the dirty room)

Write `dirty/substitution_map.json`:

```json
{"entities": [{"real": "...", "fake": "...", "kind": "person|org|id|amount|date|address|other",
               "constraints": "..."}],
 "filenames": {"<real relative path>": "<twin relative path>"},
 "notes": "constraints that span entities"}
```

- Map the CASE exhaustively: every named party, identifier, project name/code, address,
  account number, distinctive amount, and every filename that leaks a name.
- Preserve every constraint the traps depend on: IDs keep format and length; dates keep
  ordering and relative intervals; amounts that must reconcile still reconcile — state
  the arithmetic in `constraints` and check it with a calculation, not by eye.
- Names stay plausible for locale and keep their script (Chinese stays Chinese).
- The operator's machine details (usernames, local paths) are not case entities.
- `dirty/` is gitignored. The map never ships. Never echo real↔fake pairs into any
  file outside `dirty/`.

## Stage 2 — fabricate the twin

Write the twin into `<out>/filesystem/`, one twin file per real file, same disorder,
same traps:

- Apply the map exactly and consistently across every file; use the mapped filenames.
- Text-like sources (txt/md/csv/docx/xlsx): write the twin content directly. Prefer
  native formats when you have the tools (a real .xlsx with a formula trap beats a
  .csv describing one).
- Scanned/image sources: render a document-looking image — write the fabricated fields
  onto a drawn template (PIL), then optionally degrade it for realism (rotation, noise,
  shadow, phone-perspective — see `scanify.py` in the openmnk gtm history for the
  reference implementation). Never send a real scan to an image model.
- Do not invent facts with no real counterpart; do not tidy the disorder. A twin
  cleaner than reality reproduces nothing.

## Stage 3 — task + verifiers

Write `<out>/task.json`: `{"task": "...", "verifiers": [{"id", "type", "criteria", ...}]}`.

- The task mirrors the original ask, phrased in twin facts, with concrete deliverables
  under `filesystem/output/`.
- Each verifier is ONE plain-English criterion derived from the correction — a trap the
  expert caught. Types: `output` (must be present), `negative` ("did NOT ..." — exactly
  one for fabrication/concealment), `coverage` ("every X accounted for" — set
  `enumerate` to the source dir; the grader does the enumeration in code).
- Criteria reference ONLY twin entities. A real name in a criterion is a leak.

## Stage 4 — the gates (mandatory, non-negotiable)

```bash
python scan.py dirty/substitution_map.json <out>     # MUST print "clean" — else fix and rescan
python runner.py <out> --runs 1 --out out-smoke/     # the twin must be workable
python grader.py <out> out-smoke/                    # verifiers must be judgeable
```

If `scan.py` reports a leak, fix the twin and rerun it. Never hand the user a twin that
has not passed the scan — an unscanned twin is not a deliverable, it is a liability.
Finish by writing `<out>/manifest.json` (file count, types, tree, provenance: scan
result, entity count, consent noted, date).

## Never

- Never copy a real file into the twin "temporarily".
- Never put real entities in task.json, manifest.json, filenames, or your own summary
  messages once outside the dirty room.
- Never skip the scan because the fabrication "obviously" substituted everything —
  both leaks caught so far were obvious in hindsight and missed by the fabricator.
