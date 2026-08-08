# Sandbox Twins

**A data pipeline that turns real experts' AI-failure moments into anonymized, verifier-scored sandbox twins that frontier labs can legally train on.**

Built for the SpaceXAI Grokathon, Aug 8 2026. The full argument — market, mechanics, verifier design, prior art — is in [docs/THESIS.md](docs/THESIS.md). This file is how to use it.

> Every document in this repo is synthetic — generated mockups, no real person's records. That is the entire point of the pipeline.

---

## The loop

```
real case ──runner──▶ trace + expert correction ──pipeline──▶ twin world ──runner──▶ N runs ──grader──▶ reproduction rate
   (stays local, always)                              (safe to ship)
```

Three scripts, one job each. The same runner works both sides — it generates the trace on the real case and evaluates the twin — so a failure on the twin is comparable to the failure that actually happened.

## 1. `runner.py` — an agent works a case

```bash
# on a REAL case (dirty room: stays on this machine)
python runner.py path/to/real-case --task "prepare the filing review" --out dirty/case-run

# on a TWIN world (task comes from its task.json), 10 times for a reproduction rate
python runner.py worlds/b2-wang-guirong --runs 10 --out out/
```

Each run copies the case into a fresh `run-NN/` (the original is never touched) and gives the agent three tools: `bash`, `read_file` (images, scanned PDFs, docx, xlsx all rendered readable), `write_file`. It leaves `transcript.jsonl` plus whatever files it changed.

Models: `--provider anthropic` (default, `ANTHROPIC_API_KEY`) or `--provider openai` for any OpenAI-compatible endpoint — for Grok: `--provider openai --base-url https://api.x.ai/v1 --model grok-4` (`XAI_API_KEY`).

## 2. `pipeline.py` — the factory: trace in, twin out

```bash
python pipeline.py dirty/case-run/transcript.jsonl \
    --case path/to/real-case \        # for the manifest: the shape of the whole folder
    --correction dirty/correction.md \ # the expert's fix, freeform text
    --out worlds/my-twin
```

Steps: parse the trace → build the substitution map (real entities → fabricated ones, constraints preserved — written to `dirty/`, gitignored, never ships) → fabricate the case files → write verifiers from the correction.

Fabrication routes:
- **text artifacts** (md, txt, csv, xlsx, docx) — written directly from the substitution map with Python document libraries; deterministic and regenerable.
- **scanned-look documents** (deeds, certificates, passports) — **template-render** (draw the document, write the fabricated fields in) or **image-edit** (an image-to-image model swaps fields on a synthetic template). A real scan never goes to a non-consented endpoint.

Output: `worlds/my-twin/` with `filesystem/` + `task.json` + `manifest.json`.

## 3. `grader.py` — diff, judge, table

```bash
python grader.py worlds/b2-wang-guirong out/
```

For each run: diff changed files against the pristine world, extract their text, one LLM call per verifier → `{rationale, pass}`. Then the aggregate table: pass/fail per verifier per run, and the headline reproduction rate. Verifier types: `output` (must be present), `negative` (must be absent), `coverage` (code enumerates the source files, the judge only does the fuzzy matching — never ask an LLM to count).

## World format

A world is just a directory:

```
worlds/<id>/
  task.json        # {"task": "...", "verifiers": [{"id", "type", "criteria", ...}]}
  filesystem/      # the initial state the agent works on
  manifest.json    # shape + provenance metadata
```

`worlds/b2-wang-guirong/` is the built exemplar: a B-2 visa case, 21 files, two languages, eight verifiers. See [docs/THESIS.md §8](docs/THESIS.md) for its traps and [docs/DEMO.md](docs/DEMO.md) for the run sheet.

## Status

The three scripts are currently **spec-only** — each file's docstring is the full spec, including implementation notes from a working prototype (multimodal reads, both providers, and the grade→table path were verified end-to-end, then stashed pending this spec).

- [x] Demo world (21 files, 8 verifiers)
- [x] Spec: README + script docstrings
- [ ] Runner
- [ ] Grader + reproduction table
- [ ] Pipeline (trace → twin)
- [ ] Reproduction report over N runs on Grok
- [ ] Certificate exhibit (substitution scan, re-identification attempt, consent record)
