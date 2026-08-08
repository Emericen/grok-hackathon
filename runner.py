#!/usr/bin/env python3
"""runner.py — an agent works a case. Used on BOTH sides of the pipeline:
on a real case to generate the trace, and on a twin world to evaluate it.
Same scaffolding both places, so a failure on the twin is comparable to the
failure that actually happened.

USAGE
    # real case (dirty room — stays on this machine)
    python runner.py path/to/real-case --task "prepare the filing review" --out dirty/case-run

    # twin world (task read from its task.json), N times for a reproduction rate
    python runner.py worlds/b2-wang-guirong --runs 10 --out out/

    # model selection: --provider anthropic (default, ANTHROPIC_API_KEY)
    #                  --provider openai --base-url https://api.x.ai/v1 --model grok-4  (XAI_API_KEY)

WHAT IT DOES, PER RUN
    1. Copy the case into a fresh out/run-NN/filesystem/ — the original is never touched.
       (If the case dir has task.json, copy its filesystem/ and take the task text from it;
       otherwise copy the dir itself and require --task.)
    2. Agent loop, step-capped (~50): call the model with three tools, execute the calls,
       feed results back, until the model calls `done` or stops calling tools.
    3. Append every turn to run-NN/transcript.jsonl — this transcript IS the trace format
       that pipeline.py ingests.

TOOLS GIVEN TO THE AGENT
    bash        shell command, cwd pinned inside the run dir, 60s timeout, output truncated.
    read_file   THE way to read case documents. Text returns as text; images return as
                image blocks; image-based/scanned PDFs render via pdftoppm; docx/xlsx get
                text-extracted. Without this, failures on scanned piles are scaffolding
                artifacts ("couldn't see the file"), not model failures.
    write_file  write a deliverable (parents created).
    done        declare completion.
    All paths resolve inside the run dir — escapes are rejected.

IMPLEMENTATION NOTES (learned from the working prototype, since stashed)
    - Providers: anthropic /v1/messages and any OpenAI-compatible /chat/completions.
      OpenAI-compat quirk: tool-result messages are text-only, so image blocks from
      read_file ride in a follow-up user message ("[2 images attached in the next message]").
    - Retry 429/5xx with linear backoff; stdlib urllib only, no pip deps.
    - System prompt tells the agent: read every file before concluding, never guess,
      flag inconsistencies explicitly in the deliverables.
"""

raise SystemExit("spec only — implementation coming; see module docstring")
