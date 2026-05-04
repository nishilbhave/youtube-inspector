# youtube-inspector — Phase Tracker

Master runbook for building `yt-verdict` (V1 skill) inside the `youtube-inspector` repo. Each phase has a status, deliverables, verification gate, and a copy-paste prompt for Claude Code.

- **Working dir:** `/Users/nishil/Documents/work/youtube-inspector/`
- **Architecture spec:** `yt-worth-it-plan.md` (read first; defines product, three-pass design, hard constraints)
- **Phase 1 detailed spec:** `/Users/nishil/.claude/plans/velvety-cuddling-lighthouse.md`

## Status legend

- `[ ]` Pending
- `[~]` In progress
- `[x]` Complete
- `[-]` Skipped / deferred

## Phase summary

| # | Phase | Status | Blocked by | Output |
|---|---|---|---|---|
| 0 | Repo bootstrap | `[x]` Complete | — | `pyproject.toml`, `.gitignore`, `README.md`, `git init` |
| 1 | `scripts/fetch.py` | `[~]` Code complete; awaiting 5-video e2e | 0 | URL → validated JSON; tested on 5 video types |
| 2 | Prompts (3 passes) | `[ ]` | 1 | `prompts/*.md`; agent-agnostic; iterated on 10 real transcripts |
| 3 | `SKILL.md` orchestration | `[ ]` | 2 | Frontmatter + step-by-step workflow the host agent follows; cache instructions |
| 4 | Cross-platform validation + skills.sh publish | `[ ]` | 3 | Smoke-tested on ≥2 agents; public GitHub repo; install command verified |

**Important:** This is an agent-agnostic skill. It ships on skills.sh and runs inside whatever host agent installs it (Claude Code, Cursor, Antigravity, Codex, etc.). The host agent's underlying LLM does all three passes. We do **not** ship orchestrator code that calls a specific vendor's API. No `ANTHROPIC_API_KEY` requirement, no Anthropic SDK in the repo, no model lock-in.

---

## Phase 0 — Repo bootstrap

**Status:** `[x]` Complete (2026-05-05)

**Goal:** Clean Python repo skeleton. No domain code yet.

**Deliverable checklist:**
- [x] `.gitignore` — `.venv/`, `__pycache__/`, `*.pyc`, `.DS_Store`, `~/yt-reports/.cache/` reference, `.pytest_cache/`
- [x] `pyproject.toml` — project metadata, Python `>=3.11`, deps `yt-dlp`, `youtube-transcript-api>=0.6.2,<1.0`; dev extra `pytest`
- [x] `README.md` — one-paragraph repo description, sister-skill roadmap table, install placeholder
- [x] `git init` + first commit (`353a412 chore: bootstrap repo`)
- [x] Fresh venv: `pip install -e ".[dev]"` succeeds

**Verification:** `pip install -e .` in a clean venv works. `pytest -q` reports 0 tests collected (no error). `git log --oneline` shows one commit.

**Prompt to submit to Claude Code:**

```
Bootstrap the youtube-inspector repo (Phase 0).

Read first:
- /Users/nishil/Documents/work/youtube-inspector/yt-worth-it-plan.md (project architecture)
- /Users/nishil/Documents/work/youtube-inspector/PHASES.md (Phase 0 section)

Working directory: /Users/nishil/Documents/work/youtube-inspector/

Create:
- .gitignore (Python defaults: .venv/, __pycache__/, *.pyc, .pytest_cache/, .DS_Store, plus a comment that ~/yt-reports/.cache/ is also ignored since it lives outside the repo)
- pyproject.toml: name "youtube-inspector", version 0.0.1, requires-python >=3.11, dependencies ["yt-dlp>=2024.0", "youtube-transcript-api>=0.6"], optional-dependencies.dev ["pytest>=8"]
- README.md: project description (umbrella for YouTube analysis skills), sister-skill roadmap as a table (yt-verdict, yt-claims, yt-tldr, yt-extract, yt-channel, yt-quote, yt-clip), placeholder for install instructions
- git init; commit message "chore: bootstrap repo"

Verify:
- python -m venv .venv && source .venv/bin/activate && pip install -e .  → succeeds
- pytest -q  → 0 tests collected, exit 5 (acceptable, no error)
- git log --oneline  → one commit

When done:
- Update PHASES.md: tick every checkbox in the Phase 0 section, change the row in the summary table to [x] Complete, add an entry to the Change log at the bottom.
- Report what you changed.
```

---

## Phase 1 — `scripts/fetch.py`

**Status:** `[~]` Code complete (2026-05-05); awaits e2e verification on 5 real video URLs.  
**Blocked by:** Phase 0

**Goal:** URL → schema-valid JSON with metadata + transcript. No LLM calls.

**Spec:** Full CLI contract, JSON schema, rejection rules, library plan, test plan, and verification steps live in `/Users/nishil/.claude/plans/velvety-cuddling-lighthouse.md`. Read it before starting.

**Deliverable checklist:**
- [x] `scripts/fetch.py` — CLI implements all rejection rules in cheap→expensive order
- [x] `tests/test_fetch.py` — URL parsing, error JSON shape, cache round-trip (no network; mock yt-dlp). 35 tests passing.
- [ ] 5 happy-path video types produce schema-valid JSON: tutorial, podcast (>1hr), finance pitch, news, vlog *(still pending — needs real >5min English video URLs)*
- [x] **5 of 6 rejection paths live-verified:** `INVALID_URL` (`"not-a-url"`), `PLAYLIST`, `TOO_SHORT` (URL `n0phBDPz8z0`, 228s), `NON_ENGLISH` (URL `xP0SQHXVHjQ`, Hindi transcript), and empty-input → `INVALID_URL`.
- [ ] Live e2e of `LIVE_STREAM` and `NO_TRANSCRIPT` against real videos *(unit-test mocks cover the code paths; live URLs are volatile/rare, low priority)*
- [x] `--cache` flag round-trips correctly — verified live: rejection JSON written to `~/yt-reports/.cache/{video_id}.json` (perms `0700`), second run serves from cache in ~0.03s vs 1.6–3.0s fresh (~50× speedup), no network call.
- [x] `pytest tests/` passes (35 passed in 0.43s)

**Verification:** Run the full Verification block in the plan file (5 happy-path videos + 6 rejection cases + cache check + pytest). Show the actual command output, not summaries.

**Prompt to submit to Claude Code:**

```
Implement Phase 1 — scripts/fetch.py — for the youtube-inspector repo.

Read first (in order):
- /Users/nishil/.claude/plans/velvety-cuddling-lighthouse.md (the detailed spec — CLI contract, output JSON schema, rejection rules, library plan, test plan, verification commands)
- /Users/nishil/Documents/work/youtube-inspector/yt-worth-it-plan.md (architecture context)
- /Users/nishil/Documents/work/youtube-inspector/PHASES.md (Phase 1 section)

Working directory: /Users/nishil/Documents/work/youtube-inspector/

Build:
- scripts/fetch.py per the contract in the plan file
- tests/test_fetch.py covering URL parsing + each rejection rule (mock yt-dlp + youtube-transcript-api; no real network calls in tests)

Library plan from the spec: yt-dlp for metadata; youtube-transcript-api primary for transcript with yt-dlp auto-subs as fallback.

Verify by running every step of the Verification block in the plan file:
- 5 happy-path video types (you pick real public URLs and report which you used)
- 6 rejection cases
- Cache round-trip
- pytest tests/

Do NOT claim success until every item passes. Show the actual command output.

When done:
- Update PHASES.md: tick the relevant Phase 1 checkboxes, change summary table row to [x] Complete, log in Change log with which 5 video URLs you used.
- Report.
```

---

## Phase 2 — Prompts

**Status:** `[ ]` Pending  
**Blocked by:** Phase 1

**Goal:** Three production-grade prompts. The plan doc is explicit: *"the prompts are the actual product. Code is glue."* This phase is where the skill earns its keep.

**Deliverable checklist:**
- [ ] `prompts/extract_structure.md` — Pass 1: mechanical segmentation into hook/content/pitch/outro with timestamps
- [ ] `prompts/inventory_claims.md` — Pass 2: per-section inventory of concrete claims, vague claims, evidence shown, pitches; **every item has timestamp + verbatim quote**
- [ ] `prompts/generate_verdict.md` — Pass 3: synthesis to the report format from the plan doc
- [ ] Prompts are **model-agnostic** — written in plain natural language, no vendor-specific syntax (no `cache_control`, no Anthropic-style XML tag conventions over-relied on, no Claude-specific instructions). Output formats are explicit so any frontier LLM produces consistent structure.
- [ ] `prompts/iteration-notes.md` — log of what changed each iteration and why
- [ ] `prompts/samples/transcripts/` — fetch.py output for the 10 test videos
- [ ] `prompts/samples/outputs/` — Pass-1, Pass-2, Pass-3 outputs for ≥3 of the 10
- [ ] **Cross-model spot-check:** run Pass 3 on the same Pass-1 + Pass-2 inputs against ≥2 different frontier models (e.g., one Anthropic, one OpenAI). Verdict shouldn't flip; format should hold.
- [ ] **Hard rule check:** every flag in every Pass-3 sample cites a timestamp + verbatim quote. Anything that doesn't is broken; iterate until clean.

**Verification:** Manual review. Pass-3 outputs read in <30 seconds. Format matches the plan doc exactly. No flags without quoted citations. No prompt phrasing that locks in a single vendor's model.

**Prompt to submit to your agent:**

```
Implement Phase 2 — three prompts for yt-verdict.

Read first:
- /Users/nishil/Documents/work/youtube-inspector/yt-worth-it-plan.md (especially "Three-pass analysis" and "Hard constraints" — every flag MUST cite a timestamp + verbatim quote, no exceptions)
- /Users/nishil/Documents/work/youtube-inspector/PHASES.md (Phase 2 section)

Working directory: /Users/nishil/Documents/work/youtube-inspector/

CONTEXT: This skill ships on skills.sh and runs inside any host agent (Claude Code, Cursor, Antigravity, Codex). The prompts must work across frontier models — do not write prompts that depend on Anthropic-specific syntax, Claude-specific instructions, or any single vendor's quirks.

Phase 1 (scripts/fetch.py) is complete. Use it to fetch transcripts for 10 real YouTube videos covering the 5 types from the plan doc (tutorial, podcast, finance pitch, news, vlog — at least 2 of each). Save them under prompts/samples/transcripts/.

Build, in order, iterating against the 10 transcripts:
1. prompts/extract_structure.md — Pass 1: mechanical segmentation
2. prompts/inventory_claims.md — Pass 2: claim/evidence inventory with verbatim quotes
3. prompts/generate_verdict.md — Pass 3: synthesis into the report format

For each prompt: write v1 in plain natural language, run on the 10 transcripts, record failures in prompts/iteration-notes.md, revise, repeat. Save final outputs under prompts/samples/outputs/.

Cross-model check: spot-test Pass 3 against ≥2 different frontier models on the same Pass-1+Pass-2 inputs. Verdict should not flip; output format should hold. Document the test in iteration-notes.md.

Hard rule (do NOT mark complete until satisfied): every flag in every Pass-3 sample output quotes the transcript verbatim AND includes a timestamp. Hallucinated quotes or unsourced flags = not done.

When done:
- Update PHASES.md: tick checkboxes, change summary row to [x], log the 10 video URLs in the Change log.
- Report which prompts went through how many iterations and the most common failure mode.
```

---

## Phase 3 — `SKILL.md` orchestration

**Status:** `[ ]` Pending  
**Blocked by:** Phase 2

**Goal:** Wire the three prompts and `fetch.py` into a complete agent-runnable workflow. The host agent (Claude Code / Cursor / Antigravity / Codex) reads `SKILL.md`, follows the steps, makes its own LLM calls using its own auth and model. There is **no** Python orchestrator, **no** vendor SDK in the repo, and **no** API key the user has to provide.

Caching is the agent's job. SKILL.md instructs it: before each pass, check the relevant cache file at `~/yt-reports/.cache/{video_id}-pass{n}.json`. If present and the prompt hash matches, reuse. Otherwise run the pass and write the cache.

**Deliverable checklist:**
- [ ] `skills/yt-verdict/SKILL.md` with YAML frontmatter (name, description) — see Phase 4 for description tuning
- [ ] SKILL.md body documents the workflow as numbered steps the agent follows verbatim
- [ ] Workflow steps reference `scripts/fetch.py` (run it as a subprocess) and `prompts/*.md` (apply each as an LLM pass)
- [ ] Cache protocol documented in SKILL.md: cache key per pass, what counts as a cache hit (prompt-content hash + transcript-hash matching), when to invalidate
- [ ] Final report written to `~/yt-reports/{video_id}.md` per the format in `yt-worth-it-plan.md`
- [ ] Optional thin Python helper `scripts/cache.py` if file-path caching needs more than what SKILL.md instructions can express. **Default: don't add it.** Only introduce if the agent struggles to manage cache reads/writes via tool use alone.
- [ ] End-to-end smoke on 3 transcripts from Phase 2: run inside a host agent (Claude Code) with no API key set in the environment beyond what the agent itself uses; produce reports matching the Phase 2 samples within iteration drift.

**Verification:**
- Run the skill against 3 known transcripts inside Claude Code; outputs land in `~/yt-reports/` and match Phase 2 samples within iteration drift.
- Delete only `~/yt-reports/.cache/{video_id}-pass3.json` and re-trigger; confirm the agent reuses Pass 1 and Pass 2 caches and only re-runs Pass 3.
- Confirm no `import anthropic` / `import openai` / vendor SDK anywhere in the shipped repo.

**Prompt to submit to your agent:**

```
Implement Phase 3 — SKILL.md orchestration — for yt-verdict.

Read first:
- /Users/nishil/Documents/work/youtube-inspector/yt-worth-it-plan.md ("Implementation phases" → Phase 3, "Three-pass analysis", "Publishing to skills.sh")
- /Users/nishil/Documents/work/youtube-inspector/PHASES.md (Phase 3 section)
- prompts/extract_structure.md, prompts/inventory_claims.md, prompts/generate_verdict.md

Working directory: /Users/nishil/Documents/work/youtube-inspector/

CRITICAL CONSTRAINT: this is a cross-platform skill. It will be installed via `npx skills add` and run inside Claude Code, Cursor, Antigravity, Codex, etc. The host agent's underlying LLM does the work. Do NOT:
- Write a Python orchestrator that calls anthropic/openai SDKs
- Require ANTHROPIC_API_KEY or any vendor key from the user
- Hardcode model names (claude-sonnet-4-6, gpt-4, etc.)
- Use vendor-specific prompt features (Anthropic cache_control, etc.)

Build skills/yt-verdict/SKILL.md:
- YAML frontmatter: name=yt-verdict, description=(placeholder; tuned in Phase 4)
- Body: numbered workflow the host agent follows when triggered
  1. Extract video URL from user input
  2. Run `python scripts/fetch.py <url> --cache` and parse the JSON
  3. Check cache for Pass 1 at ~/yt-reports/.cache/{video_id}-pass1.json — reuse if prompt hash matches; else apply prompts/extract_structure.md to the transcript and write to cache
  4. Same pattern for Pass 2 (input: Pass 1 output + transcript) and Pass 3 (input: Pass 1 + Pass 2 + metadata)
  5. Write final report to ~/yt-reports/{video_id}.md per the format in yt-worth-it-plan.md
- Cache protocol: SKILL.md must spell out the cache key, hash inputs, and invalidation rules so any agent can implement them via file tool use

If the agent reports cache management is too brittle as pure SKILL.md instructions, add scripts/cache.py — a tiny Python helper with `read(pass_n, video_id)` / `write(pass_n, video_id, content, prompt_hash)` operations. No LLM calls in cache.py. Document the choice in SKILL.md.

Verify:
- Run yt-verdict against 3 of the Phase 2 sample transcripts inside Claude Code (or any installed host agent). Outputs at ~/yt-reports/{video_id}.md match the Phase 2 samples within iteration drift.
- Delete only ~/yt-reports/.cache/{video_id}-pass3.json; re-run; confirm Passes 1–2 are NOT re-executed (the agent should report it skipped them due to cache hits).
- grep -r "import anthropic\|import openai\|from anthropic\|from openai\|ANTHROPIC_API_KEY\|OPENAI_API_KEY" . — must return nothing.

When done:
- Update PHASES.md: tick checkboxes, change summary row to [x], note the 3 transcripts used.
- Report.
```

---

## Phase 4 — Cross-platform validation + skills.sh publish

**Status:** `[ ]` Pending  
**Blocked by:** Phase 3

**Goal:** Tune the description for trigger quality, validate the skill works on **at least two different host agents** (proves cross-platform claim), publish to GitHub, register on skills.sh.

**Deliverable checklist:**
- [ ] `SKILL.md` description tuned: 80–120 words, mentions concrete trigger phrases ("is this video worth watching", "what's actually in this video", "should I watch this", "skip or watch", "pre-watch summary", "is this YouTube video any good")
- [ ] `README.md` updated: install command, 3–4 example invocations, sister-skill roadmap, **explicit "works on Claude Code, Cursor, Antigravity, Codex" line**, list of dependencies the user needs (Python 3.11+, that's it — no API keys)
- [ ] Trigger-quality test on the primary agent (Claude Code): 5 different natural-language phrasings + YouTube URL pasted into fresh sessions; skill triggers in ≥4/5
- [ ] **Cross-platform smoke test:** install + run yt-verdict on at least one non-Claude-Code agent (Cursor or Antigravity). Same URL, compare outputs. Acceptance: same WATCH/SKIM/SKIP verdict, same evidence quality (verbatim quotes + timestamps).
- [ ] Public GitHub repo at `github.com/<owner>/youtube-inspector` (do NOT push without explicit user confirmation)
- [ ] `npx skills add <owner>/youtube-inspector --skill yt-verdict` install command verified end-to-end on a clean machine

**Verification:** A fresh user on a non-Claude agent (Cursor/Antigravity) installs via the published command, pastes a YouTube URL with a natural ask ("is this worth watching?"), gets a verdict report. No API key prompts. No "ANTHROPIC_API_KEY missing" errors.

**Prompt to submit to your agent:**

```
Implement Phase 4 — cross-platform validation and skills.sh publish prep — for yt-verdict.

Read first:
- /Users/nishil/Documents/work/youtube-inspector/yt-worth-it-plan.md ("Publishing to skills.sh")
- /Users/nishil/Documents/work/youtube-inspector/PHASES.md (Phase 4 section)

Working directory: /Users/nishil/Documents/work/youtube-inspector/

Phases 0–3 are complete and verified.

Tune:
- skills/yt-verdict/SKILL.md description (frontmatter): 80–120 words; concrete trigger phrases for "is this video worth watching", "what's actually in this video", "should I watch this", "skip or watch", "pre-watch summary", "is this YouTube video any good".
- README.md:
  - Install command: npx skills add <owner>/youtube-inspector --skill yt-verdict
  - 3–4 example invocations
  - Explicit "Works on Claude Code, Cursor, Antigravity, Codex" line
  - Dependencies: Python 3.11+ (no API keys; the host agent provides LLM access)
  - Sister-skill roadmap

Trigger-quality test (Claude Code):
- 5 fresh sessions, 5 different natural-language phrasings + a YouTube URL
- Acceptance: ≥4/5 triggers without prompting

Cross-platform smoke test (must do at least one):
- Install yt-verdict in Cursor (or Antigravity)
- Run on a known URL from the Phase 2 sample set
- Compare verdict + format against the Claude Code output
- Acceptance: same WATCH/SKIM/SKIP, same flag count ±1, same evidence-quality bar (verbatim quotes + timestamps)

Stop before pushing to GitHub or skills.sh. Report:
- 5 trigger-test phrasings + outcomes
- Cross-platform smoke test result with both agent names
- Final SKILL.md description text
- Any naming/description tweaks you'd recommend

DO NOT run git push or any skills.sh publish command without explicit user confirmation.

When done:
- Update PHASES.md: tick checkboxes, change summary row to [x] Complete, log the trigger-test phrasings + cross-platform results in Change log.
```

---

## Open questions parking lot

Carry forward; don't act on without confirming.

- `[-]` `--query "what I'm looking for"` flag — V2 (deferred this round)
- `[ ]` Obsidian integration (auto-link reports? frontmatter format?) — V2
- `[ ]` Second-opinion mode (re-run Pass 3 with different thresholds) — V2
- `[ ]` Sister-skill priority order: which of `yt-claims` / `yt-tldr` / `yt-extract` ships next?
- `[ ]` Single-repo-multi-skill layout: shared `scripts/` at root vs per-skill `skills/<name>/scripts/` — finalize in Phase 4

## Change log

| Date | Phase | Change |
|---|---|---|
| 2026-05-05 | — | PHASES.md tracker created |
| 2026-05-05 | 0 | Repo bootstrapped: `.gitignore`, `pyproject.toml`, `README.md`, `git init` + first commit `353a412`. `pip install -e ".[dev]"` succeeds in fresh `.venv/`. |
| 2026-05-05 | 1 | `scripts/fetch.py` + `tests/test_fetch.py` written. 35 unit tests pass (URL parsing, error JSON shape, cache round-trip, VTT parser, mocked rejection paths, mocked happy path). CLI rejection paths smoke-tested without network: `INVALID_URL`, `PLAYLIST`, empty input → all exit 2 with structured stderr JSON. **Pending:** real-URL e2e for the 5 video types and the network-dependent rejection cases. |
| 2026-05-05 | 1 | Live e2e against 2 real URLs: `n0phBDPz8z0` (228s) → `TOO_SHORT` rejected at 300s floor; `xP0SQHXVHjQ` (Hindi) → `NON_ENGLISH` rejected. Cache round-trip verified live: rejection JSON cached at `~/yt-reports/.cache/`, second run ~0.03s vs 1.6–3.0s fresh (~50× speedup). |
| 2026-05-05 | 1 | Lowered `MIN_DURATION_SECONDS` from 300 → 180 per user direction; updated `yt-worth-it-plan.md` Hard constraint #2 to match. After re-fetching `n0phBDPz8z0` (228s) it now passes: title "The Lazy Way I Make Money With AI (2026)", channel "Travis Nicholson", 186 transcript segments, language `en-orig`, all required fields populated, timestamps monotonic. Added `noprogress=True` to yt-dlp fallback opts to suppress download progress noise. |
| 2026-05-05 | 2–4 | **Re-architected Phases 2–4 to remove Anthropic-specific assumptions.** Old Phase 3 (`scripts/analyze.py` calling Anthropic SDK with `ANTHROPIC_API_KEY`) deleted. New Phase 3 = `SKILL.md` orchestration (host agent runs the three passes using its own LLM/auth). Phase 4 split out as cross-platform validation + publish. Phase 2 prompts now required to be model-agnostic with cross-model spot-checks. Reason: skill ships on skills.sh and runs on any host agent (Claude Code, Cursor, Antigravity, Codex) — must not lock to a single vendor. Updated `yt-worth-it-plan.md` to match. No code changes; only doc surgery. |
