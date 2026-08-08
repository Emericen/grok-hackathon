#!/usr/bin/env python3
"""grader.py — diff, judge, table. Reward comes from final disk state,
never from what the agent says it did.

USAGE
    python grader.py worlds/b2-wang-guirong out/     # grade every out/run-NN, print the table
    # --run out/run-03      grade one run
    # --judge-model ...     override the judge model (defaults to --model)
    # --force               re-grade runs that already have grades.json

WHAT IT DOES, PER RUN
    1. DIFF     walk the run's filesystem/ against the pristine world's; a file is
                evidence if it's new or its hash changed. (Directory diff on the host —
                never block-level image diffs.)
    2. EXTRACT  pull text out of every changed file (same extractors as runner.py).
    3. JUDGE    one LLM call per verifier — NOT an agent. One criterion + the evidence
                in, strict JSON {rationale, pass} out. All the intelligence is in the
                preparation, not the judge.
    4. WRITE    run-NN/grades.json.

THEN THE TABLE
    verifier x run pass/fail matrix, per-verifier totals, and the headline:
    runs with >=1 failure / total runs  ==  the reproduction rate.

VERIFIER TYPES (from the world's task.json)
    output     the thing must be present in the output.
    negative   phrased as "did NOT ..." — judged as written, no inversion.
    coverage   "every X is accounted for" — NEVER handed raw to the judge, because a
               model glances at 21 files and says yes. Code enumerates the source dir
               (the verifier's `enumerate` field) and injects the listing; the judge
               only does the fuzzy join and must list items with no counterpart.
               Pass = empty list. Fails legibly ("3 of 21 missing: ...").

JUDGE PROMPT RULES (anti-hedging, lifted from Archipelago nearly verbatim)
    - If the criterion asks for a specific answer and the task didn't request multiple
      scenarios, the output must COMMIT. "Could be X, but also Y" FAILS even if the
      right answer is among the alternatives.
    - Absence of evidence is failure: output that never addresses the criterion fails.
"""

raise SystemExit("spec only — implementation coming; see module docstring")
