#!/usr/bin/env python3
"""pipeline.py — the factory: trace in, twin world out.

USAGE
    python pipeline.py dirty/case-run/transcript.jsonl \
        --case path/to/real-case \         # for the manifest: the shape of the whole folder
        --correction dirty/correction.md \  # the expert's fix, freeform text
        --out worlds/my-twin

INPUTS (the three-legged stool — the trace alone produces a twin tidier than
reality, and tidy worlds don't reproduce real failures)
    transcript.jsonl   what the agent saw and did — runner.py output, or a
                       Claude Code / Codex session jsonl.
    --case             the real case directory; only its SHAPE is taken (file count,
                       types, tree, sizes) — the manifest. Trivially anonymized.
    --correction       the expert's fix: what was wrong, where the evidence was,
                       why it matters. This is what "right" means; ground truth.

STAGES
    1. PARSE      trace + manifest → what files existed, what was read in what order,
                  where the work went wrong.
    2. SUBSTITUTE build the substitution map: real entities → fabricated ones,
                  preserving every constraint the traps depend on (IDs still pass
                  checksums, dates keep ordering and intervals, amounts that must
                  reconcile still reconcile).
                  >>> written to dirty/substitution_map.json — gitignored, NEVER ships.
    3. FABRICATE  write the twin's case files into <out>/filesystem/:
                  - text artifacts (md/txt/csv/xlsx/docx): rendered directly from the
                    substitution map with Python document libraries — deterministic,
                    regenerable.
                  - scanned-look documents (deeds, certificates, passports): either
                    template-render (draw the document, write fabricated fields in)
                    or image-edit (an image-to-image model swaps fields on a synthetic
                    template). A real scan never goes to a non-consented endpoint.
    4. VERIFY-GEN write <out>/task.json: the task prompt distilled from the trace's
                  original ask, plus verifiers derived from the correction —
                  each one a trap the expert caught. Types: output / negative /
                  coverage (coverage carries an `enumerate` dir for the grader).
    5. MANIFEST   write <out>/manifest.json: shape + provenance metadata
                  (counts, types, consent scope, substitution-scan result).

OUTPUT
    worlds/my-twin/{filesystem/, task.json, manifest.json}
    — safe to ship. The dirty room keeps the map.

PACKAGING GUARANTEE
    Packaging must FAIL if any real entity from the substitution map survives
    into the output — scan before writing manifest.json, refuse on any hit.
"""

raise SystemExit("spec only — implementation coming; see module docstring")
