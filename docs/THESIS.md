# Thesis: sandbox twins

**A data pipeline that turns real experts' AI-failure moments into anonymized, verifier-scored sandbox twins that frontier labs can legally train on.**

> **Every document referenced here is synthetic** — generated mockups, no real person's
> records, no real case, no scanned originals. That is the entire point of the pipeline.

---

## 1. Pitch

Sandboxes / worlds to train on are worth a lot.

- Labs spend roughly **$6–8.5B/year** on human training data — about **$1B/year each** for the majors. Triangulated from vendor run rates: Surge ~$1.2–1.4B ([Sacra](https://sacra.com/c/surge-ai/), [Inc.](https://www.inc.com/brian-contreras/surge-ai-startup-bootstrapped-1-billion-revenue-venture-capital-vc/91205888)), Mercor ~$2B gross ([Dealroom](https://app.dealroom.co/news/note/mercor-doubles-to-2b-gross-revenue-run-rate-as-ai-labs-buy-expert-data)), Handshake ~$1.1B gross ([Dealroom](https://app.dealroom.co/news/note/handshake-s-arr-crosses-1b-as-ai-training-revenue-surges)), Scale ~$1–1.5B ([CNBC](https://www.cnbc.com/2025/11/04/scale-ais-life-after-meta-has-been-rocky-cfo-insists-not-a-zombie.html)). Menlo Ventures catalogs the sector at **~$8.5B across 50+ companies**, >75% to the top four ([via Pebblous](https://blog.pebblous.ai/blog/labeling-to-rl-environments/en/)).
- **Anthropic discussed spending >$1B on RL environments alone** in a single year — The Information, Sep 2025, relayed by [TechCrunch](https://techcrunch.com/2025/09/21/silicon-valley-bets-big-on-environments-to-train-ai-agents/) and [Epoch AI](https://epoch.ai/gradient-updates/state-of-rl-envs). *Discussed, never confirmed as executed.*
- **Google reportedly in talks to pay $1.5B+ for Mechanize**, a ~12-person environments team ([Seeking Alpha](https://seekingalpha.com/news/4626111-google-considers-15b-deal-with-mechanize-to-bolster-ai-coding-capabilities-report), Aug 2026, orig. The Information). *In talks — terms could change.*
- Unit economics ([Epoch AI](https://epoch.ai/gradient-updates/state-of-rl-envs), sourced to anonymous founders): ~$20k for a website-replica environment, ~$300k for a complex app clone, $200–2,000 per expert-authored task, **4–5x premium for exclusivity**, seven figures per quarter for frontier-lab contracts.

The bottleneck is not demand. It is **supply you are allowed to use.**

Real professional work is where the valuable failures live — messy client folders, two languages, scanned documents, no API. But nobody hands over client files, so the industry routes around it:

- Mercor recruits **ex-employees of firms that won't sell**, and sells an "Enterprise Workflow Data" product ([TechCrunch](https://techcrunch.com/2025/10/29/how-ai-labs-use-mercor-to-get-the-data-companies-wont-share), Oct 2025; [mercor.com/data](https://www.mercor.com/data/)).
- SimpleClosure sold the full Slack/Jira/email archives of ~100 defunct companies to labs at **$10k–100k per company** ([Forbes](https://www.forbes.com/sites/annatong/2026/04/16/ais-new-training-data-your-old-work-slacks-and-emails/), Apr 2026).
- xAI's Grok Build CLI was caught wire-uploading entire private repos — **5.1 GB out the door on a 12 GB repo for a task that needed 192 KB** — into a bucket named `grok-code-session-traces`, with an "Improve the model" opt-out that never stopped it ([The Hacker News](https://thehackernews.com/2026/07/grok-build-uploads-entire-git.html), [The Register](https://www.theregister.com/ai-and-ml/2026/07/14/musk-promises-purge-after-grok-build-caught-sending-entire-repos-to-the-cloud/5271123), [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uvlwz0/this_is_why_we_need_local_models_and_opensource/) — 3.5k upvotes).

**Privacy is not a caveat on this idea. It is the moat** — whoever solves consented collection owns the only clean supply of real-world environments.

So: a pipeline that reconstructs a real OS sandbox preserving the *case* — its structure, its traps, its failure mode — while changing every fact inside it.

### Why a lab wants it

- **Reward where they have none.** Verifiable reward exists for code (tests pass) and math (answers check), essentially none for judgment-heavy professional work. Verifiers turn an expert's judgment into machine-checkable reward.
- **Difficulty at the learnable frontier.** RL only works on tasks a model fails *sometimes*; a measured reproduction rate is a pre-qualified difficulty label. At ~$2,400 of RL compute per task, cheap tasks waste money ([Mechanize](https://www.mechanize.work/blog/cheap-rl-tasks-will-waste-compute/)).
- **A frontier that refreshes.** Worlds saturate once a model passes them reliably, and clean synthetic curricula saturate fastest. This source is renewable: experts keep working, models keep failing in new ways. Selling worlds is selling depreciating assets; selling the pipeline is a subscription to the moving frontier.
- **Provenance is now the first question.** Post-Grok-Build, "is this safe to train on?" precedes "is it good?" The certificate is the answer.

---

## 2. What comes in

Three inputs. The trace alone is not enough: it produces a twin tidier than reality, and tidy worlds don't reproduce real failures.

```jsonc
// 1. THE TRACE — exported agent chat history (Claude Code / Codex .jsonl)
[
  { "role": "user",
    "content": "review the client's uploaded documents and prep the case" },

  { "role": "assistant", "content": [
    { "type": "tool_use", "name": "Bash",
      "input": { "command": "ls client_upload/" } }
  ]},
  { "role": "tool", "content": "passport bio.jpg  bank statement jan-jun.pdf  …" },

  ...

  { "role": "user",
    "content": "you missed the prior refusal — it's in the 2023 slip" },
  ...
]

// 2. THE MANIFEST — the shape of the folder the trace only partly saw
{ "files": 21, "types": { "pdf": 9, "jpg": 9, "docx": 1, "xlsx": 1, "txt": 1 }, "tree": "…" }

// 3. THE CORRECTION — the expert's fix. This is what "right" means.
{ "wrong":    "package omitted the Oct 2023 refusal; deposit left unexplained",
  "evidence": "visa refusal 2023.pdf; bank statement vs sale contract",
  "why":      "an undisclosed refusal is a permanent-record misrepresentation" }
```

- **Trace** — what the model saw, through a keyhole.
- **Manifest** — the shape of the whole room. Cheap, trivially anonymized, and the thing that prevents the tidy-twin failure.
- **Correction** — ground truth, and it's free: the expert was doing their own work, not authoring a benchmark. The scarce input, and the reason this is cheap.

Plus a **consent + scope declaration**: which fields may be reused, which must be replaced.

### Where traces come from

CLI harnesses leave clean local transcripts; consumer desktop apps keep nothing locally.

| Source | Location | Readable |
|---|---|---|
| Claude Code | `~/.claude/projects/<slug>/*.jsonl` | yes, one file per session |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | yes; `~/.codex/history.jsonl` indexes prompts → session_id |
| This repo's `runner.py` | `<run_dir>/transcript.jsonl` | yes — run it on a real case locally |
| Claude Desktop | `~/Library/Application Support/Claude/` | no — IndexedDB/LevelDB, server-synced |
| ChatGPT Desktop | `~/Library/Application Support/com.openai.chat/` | no — server-side |

---

## 3. What comes out

A directory and a JSON. That is the whole deliverable.

```jsonc
// worlds/b2-visa/task.json
{
  "task": "Review every document and produce the visa-preparation work product…",
  "verifiers": [
    { "id": "disclose-refusal",   "type": "output",
      "criteria": "identified the prior 214(b) refusal and addressed it honestly…" },
    { "id": "checklist-coverage", "type": "coverage", "enumerate": "client_upload",
      "criteria": "the checklist accounts for EVERY uploaded document…" },
    { "id": "no-fabrication",     "type": "negative",
      "criteria": "did NOT invent facts absent from the file set…" }
  ]
}
// + filesystem/  — the fabricated case files the agent works on
// + manifest.json — shape of the folder, provenance metadata
```

An initial state, a task, and a reward function — the form an RL engineer already thinks in. (The production pipeline ships the same thing as a bootable qcow2; see §6.)

Shipped alongside for a real sale: **reproduction report** (failure rate over N runs) and **certificate** (substitution scan clean, re-identification failed, consent recorded).

---

## 4. How

### Generate — trace → world

1. **Parse** trace + manifest. Extract what files existed, what the agent read, in what order, and where it went wrong.
2. **Build the substitution map.** Real entities → fabricated ones, preserving every constraint the traps depend on: IDs still pass checksums, dates keep their ordering and intervals, amounts that must reconcile still reconcile. **The map never leaves the local machine.**
3. **Fabricate** the case documents (see below).
4. **Write verifiers** from the expert's correction (see §5).

**Fabricating documents.** Text-like artifacts (md, txt, csv, xlsx, docx) are written directly from the substitution map with Python document libraries — deterministic, cheap, regenerable. Scanned-looking documents (deeds, certificates, passports) take one of two routes: **template-render** — draw the document with an image library and write the fabricated fields in — or **image-edit** — an image-to-image model swaps the fields on a synthetic template. A real scan never goes to a non-consented endpoint; edit models operate on templates or fully-fabricated bases only.

### Evaluate — world → score

5. Agent works a fresh copy of the world through bash/read/write tools, changing files.
6. Diff the changed files against the initial state and run an LLM judge over the diff against each verifier. **Reward comes from final disk state, never from what the agent says it did.**
7. Repeat N times → a reproduction rate.

---

## 5. Verifier design

A verifier is one plain-English criterion, judged pass/fail against the final filesystem. Schema: `{id, criteria, type}` where type is `output` (must be present), `negative` (must be absent), or `coverage` (see below).

The judge itself is **a single LLM call, not an agent** — one criterion in, `{rationale, pass}` out. All the intelligence is in the preparation: deterministic diffing, text/table extraction from changed artifacts, and only then the judge. (Mercor's Archipelago does exactly this; they only give the judge tools when it must query a live database it can't read from a file.)

### Two kinds of criteria — this distinction matters

**Presence checks** need only the output:
> "the output discloses the Oct 2023 §214(b) refusal"

**Coverage checks** need the *initial state too*, because you cannot verify "every X" without enumerating X:
> "every uploaded client document appears in the interview checklist"

Do not hand a coverage check to a bare LLM judge — ask a model "do all 21 documents appear?" and it glances and says yes. Split it: **code enumerates, model matches.** The grader lists the source files in code and asks the judge only for the fuzzy join — which entries have no counterpart. Pass = empty list, and it fails *legibly* ("3 of 21 missing: …") instead of "FAIL".

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

## 6. Production sandbox mechanics (not used in the demo)

The demo evaluates worlds as plain directories — reset is `cp -r`, capture is the changed files. Production ships worlds as bootable disks; the mechanics differ only at the packaging layer:

- **Reset**: `utmctl` exposes `list status start suspend stop attach file exec ip-address clone delete usb` — note **no `snapshot` subcommand**. Per-run reset is `clone` + `delete`, or cheaper: `qemu-img` backing file + throwaway overlay per run.
- **Guest I/O**: `utmctl file push/pull` + `utmctl exec` (exec returns no stdout — redirect in the guest, pull the file).
- **Capture ≠ reset**: do not diff qcow2 images for grading — a qcow2 diff is block-level. Snapshot/clone is the reset mechanism; directory pull is the capture mechanism; diff directories on the host.
- **Isolation**: any third-party CLI harness runs inside the VM with nothing else mounted. We know what at least one of them uploads.

### Why not AgentENV / Firecracker

Moonshot open-sourced [AgentENV](https://github.com/kvcache-ai/AgentENV), the environment platform behind Kimi K3. It runs **Firecracker** microVMs — same KVM foundation as QEMU, leaner VMM. The VM is not faster; the **lifecycle** is: resume < 50 ms, **fork a running environment into N sandboxes in ~100 ms** (refcounted memory/disk layers, diverge on write — the one thing plain QEMU can't do, and what RL rollouts need), `overlaybd` on-demand image layers, warm pools and a scheduler.

**QEMU gets you eval speed. AgentENV exists to get environment lifecycle to training speed.** We operate at eval speed. The buyer operates at training speed. Same artifact, two speeds; their infrastructure problem, not ours.

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

A US visitor-visa (B-2) application, prepared by a small immigration practice. 21 client files as they actually arrive: Chinese property deeds (房产证, 房屋买卖合同), household registration (户口本), two passports, marriage certificate (结婚证), business license (营业执照), WeChat merchant records, bank statements, pension and lease documents, a 2023 visa refusal slip, an invitation letter draft, and camera-filename photos (`IMG_2043.jpg`). Two languages. A document pile, not a dataset.

Task: produce six deliverables in `filesystem/output/`.

Eight verifiers, each a trap a competent practitioner catches and a model tends to miss:

| Verifier | The trap |
|---|---|
| **canonical-name** | Name spellings conflict across documents — establish one canonical applicant name |
| **disclose-refusal** | Find *and honestly disclose* the Oct 2023 §214(b) refusal |
| **explain-deposit** | Connect the 380,000 CNY deposit to the apartment sale contract |
| **date-conflict** | Catch the date conflict: invitation letter vs ticketed itinerary |
| **ties-evidence** | Ties-to-China summary drawing on ≥3 distinct evidence sources |
| **both-passports** | Travel history lives in **both** passports — Japan 2019 and South Korea 2016 |
| **checklist-coverage** | Every uploaded document accounted for in the checklist (coverage — code enumerates) |
| **no-fabrication** | Negative — invent nothing absent from the file set |

These are the mistakes that get a visa denied.

---

## 9. Non-negotiables

- **The substitution map never leaves the dirty room.** Packaging fails the build if any real entity survives into output. Enforced in `.gitignore` too.
- **Anonymization must survive *structural* re-identification, not just name-swapping.** A rare enough fact pattern identifies a person even with every name changed — a 214(b) refusal plus an apartment sale plus that specific deposit structure may describe exactly one applicant. Thin-crowd cases get generalized or discarded.
- **Capture is consented and credited.** Not because derivatives are illegal, but because the suppliers are attorneys and CPAs with professional-responsibility duties — and because clean provenance is precisely what makes the inventory sellable.
- **Claims stay checkable.** Say *certified*, not *legal*, and show the certificate. Never spend a claim without the receipt on the next slide.
