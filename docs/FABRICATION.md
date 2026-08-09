# Fabricating case documents that read as real

How to produce a document pile that carries the same story with different names — realistic
enough that an agent works it like a real case, synthetic enough that nothing real ships.

> Scope and ethics: these documents exist to make *training worlds* realistic. Every entity
> is fictional (or substituted via the dirty-room map), institutions are invented, and
> generation is seeded so worlds regenerate deterministically. This is not a guide to
> deceiving people or institutions — a twin's documents never impersonate a real bank,
> person, or agency.

## 1. Same story, different names — the substitution discipline

The story *is* the asset; the names are the liability. So:

- Every real entity gets exactly one fake counterpart (the substitution map), applied
  consistently across every document. One inconsistent spelling and the trap "reconcile
  the name variants" becomes noise instead of signal — unless the inconsistency itself
  is the trap, in which case fabricate the *same* inconsistency deliberately.
- Arithmetic constraints carry the traps. If the real case turns on
  `1099-K gross − sales tax − refunds = reported + $826`, the twin's numbers must
  satisfy the same equation with new values. State the equation in the map's
  `constraints` field and verify it with code, not by eye.
- Dates keep ordering and intervals ("signed 7 days before the deposit landed"), IDs
  keep format and checksum shape, names keep locale and script (Chinese stays Chinese).

## 2. Format realism — who produced the document decides its format

A real shoebox mixes three provenances; match them:

| Provenance | Real-world form | Fabricate as |
|---|---|---|
| Institutions (IRS/bank/processor) | scans of printed letters | HTML → PDF → degraded image |
| The client's own records | living files, sometimes wrong | native .xlsx / .docx |
| Physical world | phone photos on a desk | image with perspective + lighting |

Native files are a trap surface of their own: the reference case ships an .xlsx whose
TOTAL formula deliberately sums only rows 3–42 — the agent must trust source documents
over the client's arithmetic. Only a real spreadsheet can carry that trap.

## 3. Rendering: clean first, then degrade

Two-stage, never one:

1. **Clean render.** Write the document as HTML/CSS and print to PDF (headless Chrome),
   or draw it with PIL (`pipeline.py::render_specs` does title + label/value fields +
   seal). Get every fact right here — content edits after degradation are impossible.
2. **Degrade per provenance** — [`tools/scanify.py`](../tools/scanify.py) is the
   reference implementation, three profiles:
   - `flatbed` — slight rotation (±0.8°), paper tone, sensor noise, mid JPEG quality
   - `photocopy` — grayscale gen-2: blur, harsh contrast, edge band, heavy noise
   - `phone` — perspective warp, rotation, warm cast, vignette, desk shadow

   Filenames follow the degradation: a phone photo is `IMG_5203.pdf`, not
   `05-bank-mar.pdf`. Clients name files badly; twins should too.

## 4. Disorder is content

A twin tidier than reality reproduces nothing. Preserve: mixed languages, camera
filenames, near-duplicate files (`11张表.xlsx` and `11张表(1).xlsx`), one document that
is deliberately ABSENT (the missing-invoice trap — the agent must notice the hole, not
just read what's there), and the client's own optimistic note contradicting the records.

## 5. Verification before shipping

- `python scan.py dirty/substitution_map.json <world>` — zero real entities, hard gate.
- Open every rendered image and *read it back* — a degraded scan whose text is
  illegible is a scaffolding failure that will masquerade as a model failure.
- Run the world once (`runner.py`) and grade it — every verifier must be judgeable
  from what a competent run leaves on disk.
