# Redline

Turn an expert-corrected AI failure into an anonymized, verifier-graded training world.

## Setup

```bash
curl -fsSL https://x.ai/cli/install.sh | bash     # Grok Build
git clone https://github.com/Emericen/grok-hackathon
echo 'XAI_API_KEY=xai-...' > grok-hackathon/.env  # auto-loaded by the scripts
```

## The journey

**1. Work a real case.**

```bash
cd your-case && grok
```

Do the work; correct the agent like you'd correct an associate. That conversation is the trace and the corrections.

**2. Twin it.** In the same session:

```
fetch and follow https://raw.githubusercontent.com/Emericen/grok-hackathon/master/TWIN.md
```

Grok builds `twin/<case>/` - same story, same traps, every real fact replaced - and must pass the leak scan (`clean`) before handing it over.

**3. Run and grade the twin.** New session in the twin dir, let it work the task one shot, then:

```
fetch and follow https://raw.githubusercontent.com/Emericen/grok-hackathon/master/GRADE.md
```

Grok runs the grader on its own work. The judge is also Grok - but it goes through the script, so it can't improvise the verdict.

Optional: install the skill so `twin this case` triggers without the curl (Grok Build reads Claude-format skills):

```bash
cp -r grok-hackathon/.claude/skills/redline ~/.agents/skills/
```

## Scripts (what the markdowns call)

```bash
python3 scripts/scan.py dirty/substitution_map.json <world>   # leak gate - nonzero exit on any real entity
python3 scripts/grader.py <world>                             # judge runs in out/; --in-place for TUI sessions
python3 scripts/runner.py <world> --runs 5                    # headless N runs → reproduction rate
python3 scripts/pipeline.py <trace.jsonl> --case <dir> --correction <file> --out <name>-intake     # headless twin build
```

Defaults: grok-4.5, temperature 0, output to `out/`. Needs python3 + PIL + poppler (`pdftotext`).

## World format

```
<name>-intake/     # the twin: a flat client folder, documents only
<name>-task.json   # {"task": "...", "verifiers": [{"id", "type", "criteria"}]}
                   # lives OUTSIDE the folder so the evaluated agent can't read it
```

Why and how it works: [docs/THESIS.md](docs/THESIS.md) · [docs/FABRICATION.md](docs/FABRICATION.md)
