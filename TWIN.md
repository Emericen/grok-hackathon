# TWIN.md — one-line twin factory for any agent harness

You are an agent inside a coding harness, and the user has asked you to follow this file.
Your job: replicate the case in the current working directory into an **anonymized twin
world** — same story, same disorder, same traps, every real-world fact replaced — then
prove the twin works. Follow every stage. The gates at the end are not optional.

## Setup

```bash
git clone https://github.com/Emericen/grok-hackathon twin-pipeline   # scripts + docs
```

Confirm you have, or ask the user for:
1. **The case** — the working directory of real files (never modified, never shipped).
2. **The correction** — what the expert said was wrong with the agent work done on this
   case (it may be earlier in this very conversation). This defines the verifiers.
3. **The trace** — the earlier back-and-forth on this case (this conversation, or a
   session transcript). If the work happened here, you already have it.

## Stage 1 — substitution map (dirty room)

Create `dirty/` (add it to .gitignore) and write `dirty/substitution_map.json`:

```json
{"entities": [{"real": "...", "fake": "...", "kind": "person|org|id|amount|date|address|other",
               "constraints": "..."}],
 "filenames": {"<real relative path>": "<twin relative path>"}}
```

Exhaustive over the CASE: every named party, identifier, project/account number, address,
distinctive amount, and every filename that leaks a name. Constraints preserve the traps:
IDs keep format and length; dates keep ordering and intervals; amounts that must
reconcile still reconcile — state the arithmetic and verify it with code. Names keep
locale and script. The map never leaves `dirty/`; never echo real↔fake pairs anywhere else.

## Stage 2 — fabricate the twin

Write `twin/<case-name>/filesystem/` — one twin file per real file:

- Apply the map exactly and consistently; use the mapped filenames.
- Client-made files stay native (.xlsx with its formulas — including deliberately wrong
  ones, .docx); institutional scans become rendered images (draw with PIL, then degrade:
  `twin-pipeline/tools/scanify.py` has flatbed/photocopy/phone profiles); phone photos
  get perspective and warm cast. Full playbook: `twin-pipeline/docs/FABRICATION.md`.
- Preserve disorder: bad filenames, near-duplicates, mixed languages, and any
  deliberately ABSENT document. Never send a real scan to an image model.

## Stage 3 — task + verifiers

Write `twin/<case-name>/task.json`: the original ask rephrased in twin facts with
concrete deliverables under `filesystem/output/`, plus verifiers — one plain-English
criterion per trap the expert's correction caught. Types: `output` (must be present),
`negative` (exactly one, "did NOT ..."), `coverage` ("every X accounted for", with
`enumerate` naming the source dir). Criteria reference ONLY twin entities.

## Stage 4 — gates (mandatory)

```bash
python twin-pipeline/scan.py dirty/substitution_map.json twin/<case-name>   # MUST print "clean"
python twin-pipeline/runner.py twin/<case-name> --runs 1 --out out-smoke/   # twin is workable
python twin-pipeline/grader.py twin/<case-name> out-smoke/                  # verifiers judgeable
```

If the scan reports a leak: fix the twin, rescan. Never present an unscanned twin —
both leaks caught in this pipeline's own testing were "obvious" substitutions the
fabricator missed. Finish with `twin/<case-name>/manifest.json` (file count, types,
tree, provenance: scan result, entity count, consent noted, date) and tell the user:
files fabricated, entities substituted, scan verdict, and the one command to evaluate
their model on the twin:

```bash
python twin-pipeline/runner.py twin/<case-name> --runs 5 --out out/ \
    --provider openai --base-url https://api.x.ai/v1 --model grok-4
python twin-pipeline/grader.py twin/<case-name> out/
```
