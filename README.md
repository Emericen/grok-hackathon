# Sandbox Twins

**A data pipeline that turns real experts' AI-failure moments into anonymized, verifier-scored sandbox twins that frontier labs can legally train on.**

Built for the SpaceXAI Grokathon, Aug 8 2026.

> **Every document referenced here is synthetic.** The `b2-wang-guirong` world contains
> generated mockups — no real person's records, no real case, no scanned originals.
> That is the entire point of the pipeline.

This README is written to be self-contained: an engineer (or their agent) should be able to read only this file and understand the thesis, the architecture, the mechanics, and what's left to build.

---

## 1. Pitch

Sandboxes / worlds to train on are worth a lot.

- Labs spend roughly **$6–8.5B/year** on human training data — about **$1B/year each** for the majors. Triangulated from vendor run rates (Surge ~$1.2–1.4B, Mercor ~$2B gross, Handshake ~$1.1B gross, Scale ~$1–1.5B); Menlo Ventures catalogs the sector at ~$8.5B across 50+ companies with >75% going to the top four.
- **Anthropic discussed spending >$1B on RL environments alone** in a single year (The Information, Sep 2025).
- **Google is reportedly in talks to pay $1.5B+ for Mechanize**, a ~12-person environments team (Aug 2026).
- Unit economics: ~$20k for a website-replica environment, ~$300k for a complex app clone, $200–2,000 per expert-authored task, 4–5x premium for exclusivity, seven figures per quarter for frontier-lab contracts.

The bottleneck is not demand. It is **supply you are allowed to use.**

Real professional work is where the valuable failures live — messy client folders, two languages, scanned documents, jurisdiction-specific rules, no API. But nobody hands over client files. So the industry routes around it: Mercor pays ex-employees for their old work product, SimpleClosure sold dead companies' Slack/Jira/email archives at $10k–100k per company, and xAI's Grok Build CLI was caught wire-uploading entire private repos — **5.1 GB out the door on a 12 GB repo for a task that needed 192 KB** — into a bucket named `grok-code-session-traces`, with an "Improve the model" opt-out that never stopped the uploads. ([r/LocalLLaMA thread](https://www.reddit.com/r/LocalLLaMA/comments/1uvlwz0/this_is_why_we_need_local_models_and_opensource/), 3.5k upvotes.)

**Privacy is not a caveat on this idea. It is the moat.** Whoever solves consented collection owns the only clean supply of real-world environments.

So: a pipeline that reconstructs a real OS sandbox preserving the *case* — its structure, its traps, its failure mode — while changing every fact inside it.

### Why a lab wants it

- **Reward where they currently have none.** Labs have verifiable reward in code (tests pass) and math (answers check). They have essentially none for judgment-heavy professional work. Verifiers convert an expert's judgment into machine-checkable reward.
- **Difficulty at the learnable frontier.** RL only works on tasks a model fails *sometimes*. A measured reproduction rate ("fails 7/10") is a pre-qualified difficulty label. Mechanize's own argument: at ~$2,400 of RL compute per task, cheap tasks waste money.
- **A frontier that refreshes.** Worlds saturate — once a model passes reliably, that world is spent, and clean synthetic curricula saturate fastest. This source is renewable by construction: experts keep working, models keep failing in new ways as they improve. Selling worlds is selling depreciating assets; selling the pipeline is a subscription to the moving frontier of real failure.
- **Provenance is now the first question.** Post-Grok-Build, "how do I know this is safe to train on?" precedes "is it good?" The certificate is the answer.

---

## 2. What comes in

Three inputs. The trace alone is not enough — that mistake produces a twin tidier than reality, and tidy worlds do not reproduce real failures.

```jsonc
// 1. THE TRACE — exported agent chat history (Claude Code / Codex .jsonl)
[
  { "role": "user",
    "content": "navigate the case in ~/desktop/workfile/liang thoroughly" },

  { "role": "assistant", "content": [
    { "type": "tool_use", "name": "Bash",
      "input": { "command": "ls -R ~/desktop/workfile/liang" } }
  ]},
  { "role": "tool", "content": "bank_statement.pdf  receipt_0243.jpg  …" },

  ...

  { "role": "user",
    "content": "convert receipts into text and document in spreadsheet first" },
  ...
]

// 2. THE MANIFEST — the shape of the folder the trace only partly saw
{ "files": 47, "types": { "pdf": 12, "jpg": 28, "xlsx": 3 }, "tree": "…" }

// 3. THE CORRECTION — the expert's fix. This is what "right" means.
{ "wrong":    "workbook missing 3 receipts; totals didn't reconcile",
  "evidence": "receipts/ vs workbook.xlsx",
  "why":      "understates deductible expenses" }
```

- **Trace** — what the model saw, through a keyhole. Every file it opened and what came back.
- **Manifest** — the shape of the whole room. Cheap to capture, trivially anonymized, and it is what prevents the tidy-twin failure mode.
- **Correction** — ground truth, and it is free: the expert was doing their own work, not authoring a benchmark. This is the scarce input and the reason the whole thing is cheap.

Plus a **consent + scope declaration** riding alongside — which fields may be reused, which must be replaced.

### Where traces come from

CLI harnesses leave clean local transcripts; consumer desktop apps keep nothing locally.

| Source | Location | Readable |
|---|---|---|
| Claude Code | `~/.claude/projects/<slug>/*.jsonl` | yes, one file per session |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | yes; `~/.codex/history.jsonl` indexes prompts → session_id |
| Claude Desktop | `~/Library/Application Support/Claude/` | no — IndexedDB/LevelDB, server-synced |
| ChatGPT Desktop | `~/Library/Application Support/com.openai.chat/` | no — server-side |

---

## 3. What comes out

Two artifacts. That is the whole deliverable.

```jsonc
{
  "snapshot": "1e243r-8zsd9-gp18sj.qcow2",
  "task": "build a workbook for kowalski's business",
  "verifiers": [
    "every receipt in /filesystem/receipts appears as a row in the workbook",
    "workbook totals reconcile to the bank statement closing balance",
    "each expense row cites the source file it came from",
    "NEGATIVE: no line item that isn't backed by a document in /filesystem"
  ]
}
```

A bootable disk and a reward function — i.e. `(initial state, task, reward)`. That is a training environment in the form an RL engineer already thinks in.

Shipped alongside for a real sale: the **reproduction report** (failure rate over N runs) and the **certificate** (substitution scan clean, re-identification attempt failed, consent recorded).

---

## 4. How

### Generate — trace → world

1. **Parse** trace + manifest. Extract what files existed, what the agent read, in what order, and where it went wrong.
2. **Build the substitution map.** Real entities → fabricated ones, preserving every constraint the traps depend on: IDs still pass checksums, dates keep their ordering and intervals, amounts that must reconcile still reconcile. **The map never leaves the local machine.**
3. **Fabricate** the case documents and write them into a VM; snapshot the disk → `qcow2`.
4. **Write verifiers** from the expert's correction (see §5).

### Evaluate — world → score

5. Agent boots the `qcow2` and operates through bash, changing the disk.
6. Pull the changed files, diff against the initial state, and run an LLM judge over the diff against each verifier rule. **Reward comes from final disk state, never from what the agent says it did.**
7. Repeat N times → a reproduction rate.

---

## 5. Verifier design

A verifier is one plain-English criterion, judged pass/fail against the final filesystem. Minimum viable schema is a string; the fuller form is `{id, criteria, type}` where type is `output` (must be present) or `negative` (must be absent).

The judge itself is **a single LLM call, not an agent** — one criterion in, `{rationale, pass}` out. All the intelligence is in the preparation: deterministic diffing, text/table extraction from changed artifacts, and only then the judge. (Mercor's Archipelago does exactly this; they only give the judge tools when it must query a live database it can't read from a file.)

### Two kinds of criteria — this distinction matters

**Presence checks** need only the output:
> "the output discloses the Oct 2023 §214(b) refusal"

**Coverage checks** need the *initial state too*, because you cannot verify "every X" without enumerating X:
> "every receipt in /filesystem/receipts appears as a row in the workbook"

Do not hand a coverage check to a bare LLM judge — ask a model "do all 41 receipts appear?" and it glances and says yes. Split it: **code enumerates, model matches.**

```python
receipts = os.listdir("world/filesystem/receipts")   # 41 files
rows     = sheet_to_text("out/workbook.xlsx")        # 38 rows

judge(f"""Receipts on disk ({len(receipts)}):
{chr(10).join(receipts)}

Workbook rows ({len(rows)}):
{chr(10).join(rows)}

Which receipt files have NO corresponding row? Return a JSON list.""")
```

Pass = empty list. The LLM does only the fuzzy join (`receipt_0243.jpg` ↔ `"Home Depot · 3/14 · $82.10"`) which code cannot do; code does the counting, which the model is bad at. Bonus: it fails *legibly* — "3 of 41 missing: receipt_0243, …" instead of "FAIL".

**Rule of thumb: if a criterion contains "every", "all", or "each", it needs an enumeration from the initial state.**

### Catching "the model jumped to a conclusion"

You cannot verify reasoning. You build worlds where sloppy reasoning leaves a **signature in the output**:

| Mechanism | Signature |
|---|---|
| Buried contradiction (two documents disagree; one is easier to find) | Output asserts the wrong one |
| Fact requiring connection across files | Output leaves a large number unexplained |
| Evidence findable only by exhausting the pile | Output omits a disclosure |
| Fabrication | Output contains a fact absent from the file set |
| Hedging | Output lists candidates instead of committing |

The last two need explicit guards. A **negative criterion** catches fabrication. For hedging, lift Archipelago's anti-scattergunning rule into the judge prompt nearly verbatim:

> If the criterion asks for a specific answer and the task did not request multiple scenarios, the response must commit to a single answer. Hedging between candidates ("it could be X, but also Y") **FAILS the criterion — even if the correct answer appears among the alternatives.**

---

## 6. Sandbox mechanics

### Reset

`utmctl` (at `/Applications/UTM.app/Contents/MacOS/utmctl`) exposes:

```
list  status  start  suspend  stop  attach  file  exec  ip-address  clone  delete  usb
```

**Note: there is no `snapshot` subcommand.** Reset per run is therefore either:

```bash
UTM=/Applications/UTM.app/Contents/MacOS/utmctl
$UTM clone "world-pristine" --name "run-007"   # fresh copy of the world
$UTM start "run-007"
# … agent works …
$UTM stop "run-007" && $UTM delete "run-007"
```

or manage the disk directly outside UTM with `qemu-img` (backing file + throwaway overlay per run), which is cheaper than a full clone.

### Guest I/O

```bash
$UTM file push "run-007" ./case-files/          # load the world
$UTM exec "run-007" -- <cmd>                    # run something in the guest
$UTM file pull "run-007" /output ./out/run-007/ # capture results
```

`exec` returns no stdout — redirect inside the guest to a file, then `file pull` it.

### Capture ≠ reset

Do **not** try to diff qcow2 images for grading. A qcow2 diff is block-level (changed sectors), not file-level; `virt-diff` can give you files, but the simple path is: **snapshot/clone = reset mechanism, directory pull + tar = capture mechanism.** Diff two directories on the host in ~15 lines of Python.

### Why not AgentENV / Firecracker

Moonshot open-sourced [AgentENV](https://github.com/kvcache-ai/AgentENV), the environment platform behind Kimi K3. It runs **Firecracker** microVMs — same KVM foundation as QEMU, leaner VMM. The VM is not faster; the **lifecycle** is:

- resume < 50 ms, pause < 100 ms — so idle environments release CPU/RAM instead of holding it
- **fork** a *running* environment into N independent sandboxes in ~100 ms, sharing memory/disk layers by refcount and diverging on write — this is the one thing plain QEMU can't do well, and it's what RL rollouts need
- `overlaybd` layered images loaded on demand, so total image catalog can exceed host disk
- gateway + scheduler + warm pools = a fleet control plane, not a hypervisor

**QEMU gets you eval speed. AgentENV exists to get environment lifecycle to training speed.** We operate at eval speed (a handful of runs, minutes each — lifecycle cost amortizes away). The buyer operates at training speed. Same artifact, two speeds; their infrastructure problem, not ours.

---

## 7. Prior art and format compatibility

[Mercor's Archipelago](https://github.com/Mercor-Intelligence/archipelago) is the closest public thing and we build in its format on purpose. It ships **APEX-Agents**, a 480-task benchmark across investment banking, tax accounting, and consulting ([arXiv 2601.14242](https://arxiv.org/abs/2601.14242)), with three components: Environment (Docker container exposing an MCP gateway over fake apps — mail, chat, calendar, spreadsheets, SEC filings), Agents runner, and Grading (snapshot diff + LLM judge over criteria, with negative criteria, weights, and universal penalties).

| | Archipelago / APEX | This pipeline |
|---|---|---|
| Origin of task | Expert paid to *imagine* a scenario | Anonymized twin of a failure that *actually happened* |
| Cost per task | Professional hours ($85–200/hr) | ~0 — exhaust of work already being done |
| Realism | Fake apps, tidy by construction | Real document disorder, preserved via the manifest |
| Difficulty | Assumed | Measured (reproduction rate) |
| Provenance | n/a | Certificate: substitution scan + failed re-identification + consent |
| Renewal | New authoring project | Continuous — models improve, new failures arrive |

Because a world tarball + verifiers array is exactly what their open-source runner ingests, **any lab already running that stack can run this inventory unmodified.**

---

## 8. The demo world

`b2-wang-guirong` — a B-2 visitor visa preparation case. 21 client files as they actually arrive: Chinese property deeds (房产证, 房屋买卖合同), household registration (户口本), two passports, marriage certificate (结婚证), business license (营业执照), WeChat merchant records, bank statements, pension and lease documents, a 2023 visa refusal slip, an invitation letter draft, and camera-filename photos (`IMG_2043.jpg`). Two languages. A document pile, not a dataset.

Task: produce six deliverables in `/filesystem/output/`.

Eight verifiers, each a trap a competent practitioner catches and a model tends to miss:

| Verifier | Trap |
|---|---|
| `ver_b2_001` | Name spellings conflict across documents — establish one canonical applicant name |
| `ver_b2_002` | Find *and honestly disclose* the Oct 2023 §214(b) refusal |
| `ver_b2_003` | Connect the 380,000 CNY deposit (2026-03-18) to the apartment sale contract |
| `ver_b2_004` | Catch the date conflict: invitation letter (May 10–31, 2027) vs ticketed itinerary |
| `ver_b2_005` | Ties-to-China summary drawing on ≥3 distinct evidence sources |
| `ver_b2_006` | Travel history lives in **both** passports — Japan 2019 and South Korea 2016 |
| `ver_b2_007` | Translation/consistency |
| `ver_b2_008` | Negative — invent nothing absent from the file set |

These are the mistakes that get a visa denied.

### Demo order (the reveal comes last, deliberately)

1. Show the case. Twenty-one files, two languages, real disorder.
2. Watch a frontier model work it. It produces a confident, professional-looking package.
3. Watch the grader light up red on specific traps.
4. **Reveal:** nobody authored this. It's the anonymized twin of a real case that failed exactly this way, ground truth from a real practitioner's correction, zero professional hours — and here's the certificate saying nothing real survived.
5. Regenerate a variant (new names, new numbers, same traps); scores move coherently. That's a factory, not an artifact.

The audience must take the world seriously *before* learning it was free.

---

## 9. Build

Deliberately minimal — the world and the verifiers are what's on trial, not the scaffolding.

- **`runner/`** — ~100-line agent loop (bash/read/write tools, step cap). Harness-neutral on purpose: if the loop is weak, the model fails for scaffolding reasons and you misdiagnose a harness bug as a reproduced failure. Give it clean tools and enough steps.
- **`grader/`** — directory diff + one LLM call per criterion, `{rationale, pass}` schema, negative criteria inverted, coverage criteria pre-enumerated in code.
- **Isolation** — run any third-party CLI harness inside the VM with nothing else mounted. We know what at least one of them uploads.

Status:

- [x] World built (`b2-wang-guirong`, 21 files, 8 verifiers)
- [ ] Runner
- [ ] Grader
- [ ] Reproduction report over N runs
- [ ] Variant regeneration
- [ ] Correction artifact exhibit

---

## 10. Non-negotiables

- **The substitution map never leaves the dirty room.** Packaging fails the build if any real entity survives into output. Enforced in `.gitignore` too.
- **Anonymization must survive *structural* re-identification, not just name-swapping.** A rare enough fact pattern identifies a person even with every name changed — a 214(b) refusal plus an apartment sale plus that specific deposit structure may describe exactly one applicant. Thin-crowd cases get generalized or discarded.
- **Capture is consented and credited.** Not because derivatives are illegal, but because the suppliers are attorneys and CPAs with professional-responsibility duties — and because clean provenance is precisely what makes the inventory sellable.
- **Claims stay checkable.** "No file upload needed" is true. "Works offline" is not — the agent's reads transit a cloud API. Never spend a claim without the receipt on the next slide. Say *certified*, not *legal*, and show the certificate.
