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
| 2 | Prompts (3 passes) | `[ ]` | 1 | `prompts/*.md`; iterated on 10 real transcripts |
| 3 | `scripts/analyze.py` | `[ ]` | 2 | LLM orchestrator; report at `~/yt-reports/{video_id}.md` |
| 4 | `SKILL.md` + skills.sh publish | `[ ]` | 3 | Public GitHub repo; install command verified |

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
- [ ] `prompts/extract_structure.md` — Pass 1 (Haiku): mechanical segmentation into hook/content/pitch/outro with timestamps
- [ ] `prompts/inventory_claims.md` — Pass 2 (Sonnet): per-section inventory of concrete claims, vague claims, evidence shown, pitches; **every item has timestamp + verbatim quote**
- [ ] `prompts/generate_verdict.md` — Pass 3 (Sonnet): synthesis to the report format from the plan doc
- [ ] `prompts/iteration-notes.md` — log of what changed each iteration and why
- [ ] `prompts/samples/transcripts/` — fetch.py output for the 10 test videos
- [ ] `prompts/samples/outputs/` — Pass-1, Pass-2, Pass-3 outputs for ≥3 of the 10
- [ ] **Hard rule check:** every flag in every Pass-3 sample cites a timestamp + verbatim quote. Anything that doesn't is broken; iterate until clean.

**Verification:** Manual review. Pass-3 outputs read in <30 seconds. Format matches the plan doc exactly. No flags without quoted citations.

**Prompt to submit to Claude Code:**

```
Implement Phase 2 — three prompts for yt-verdict.

Read first:
- /Users/nishil/Documents/work/youtube-inspector/yt-worth-it-plan.md (especially "Three-pass analysis" and "Hard constraints" — every flag MUST cite a timestamp + verbatim quote, no exceptions)
- /Users/nishil/Documents/work/youtube-inspector/PHASES.md (Phase 2 section)

Working directory: /Users/nishil/Documents/work/youtube-inspector/

Phase 1 (scripts/fetch.py) is complete. Use it to fetch transcripts for 10 real YouTube videos covering the 5 types from the plan doc (tutorial, podcast, finance pitch, news, vlog — at least 2 of each). Save them under prompts/samples/transcripts/.

Build, in order, iterating against the 10 transcripts:
1. prompts/extract_structure.md (Pass 1, claude-haiku-4-5)
2. prompts/inventory_claims.md (Pass 2, claude-sonnet-4-6)
3. prompts/generate_verdict.md (Pass 3, claude-sonnet-4-6)

For each prompt: write v1, run on the 10 transcripts, record failures in prompts/iteration-notes.md, revise, repeat. Save final-version outputs under prompts/samples/outputs/.

Hard rule (do NOT mark complete until satisfied): every flag in every Pass-3 sample output quotes the transcript verbatim AND includes a timestamp. Hallucinated quotes or unsourced flags = not done.

When done:
- Update PHASES.md: tick checkboxes, change summary row to [x], log the 10 video URLs in the Change log.
- Report which prompts went through how many iterations and the most common failure mode.
```

---

## Phase 3 — `scripts/analyze.py`

**Status:** `[ ]` Pending  
**Blocked by:** Phase 2

**Goal:** Orchestrate the three LLM passes. Cache aggressively so prompt edits don't re-trigger expensive earlier passes. Write final report to `~/yt-reports/{video_id}.md`.

**Deliverable checklist:**
- [ ] `scripts/analyze.py` — Anthropic SDK; `claude-haiku-4-5` for Pass 1, `claude-sonnet-4-6` for Passes 2–3
- [ ] Per-pass intermediate cache: `~/yt-reports/.cache/{video_id}-pass{n}.json` so re-runs after a prompt edit only re-run from the changed pass
- [ ] Prompt caching enabled (`cache_control` on system prompt blocks)
- [ ] Final report written to `~/yt-reports/{video_id}.md`
- [ ] CLI: `python scripts/analyze.py <url-or-video-id>`
- [ ] `tests/test_analyze.py` — mocks Anthropic SDK; verifies pipeline order, cache reuse, error propagation
- [ ] End-to-end run on 5 of the Phase 2 transcripts; outputs match Phase 2 samples within iteration drift

**Verification:** Run on 5 known transcripts; diff vs saved Phase 2 samples. `pytest tests/test_analyze.py` passes. Cache reuse verified by deleting only `pass3.json`, re-running, confirming Passes 1–2 are not re-called.

**Prompt to submit to Claude Code:**

```
Implement Phase 3 — scripts/analyze.py orchestrator.

Read first:
- /Users/nishil/Documents/work/youtube-inspector/yt-worth-it-plan.md ("Implementation phases" → Phase 3)
- /Users/nishil/Documents/work/youtube-inspector/PHASES.md (Phase 3 section)
- The three prompt files in prompts/

Working directory: /Users/nishil/Documents/work/youtube-inspector/

Use the claude-api skill — invoke it before writing Anthropic SDK code so prompt caching, model selection, and SDK best practices are correct.

Build scripts/analyze.py:
- Input: URL or video_id
- Pipeline: load fetch.py output (use --cache) → Pass 1 (claude-haiku-4-5) → Pass 2 (claude-sonnet-4-6) → Pass 3 (claude-sonnet-4-6) → write Markdown report to ~/yt-reports/{video_id}.md
- Cache each pass to ~/yt-reports/.cache/{video_id}-pass{n}.json. On re-run, skip passes whose cache exists AND whose prompt hash hasn't changed (store the prompt hash alongside the output)
- Add prompt caching (cache_control) on the long system prompt blocks
- Errors: surface clearly; don't write a half-baked report

tests/test_analyze.py: mock anthropic.Anthropic; verify pass order, cache reuse, prompt-hash invalidation, error propagation. No real API calls in tests.

Verify:
- Run on 5 of the Phase 2 sample transcripts; diff against prompts/samples/outputs/ — matches within iteration drift
- Delete only ~/yt-reports/.cache/{video_id}-pass3.json, re-run, confirm Passes 1–2 are NOT re-called (check with a debug log)
- pytest tests/test_analyze.py passes

When done:
- Update PHASES.md: tick checkboxes, change summary row to [x], log API spend estimate per video in Change log.
- Report.
```

---

## Phase 4 — `SKILL.md` + skills.sh publish

**Status:** `[ ]` Pending  
**Blocked by:** Phase 3

**Goal:** Wrap as a publishable Claude Code skill. Install command works on a fresh machine. Description triggers reliably from natural-language prompts.

**Deliverable checklist:**
- [ ] `skills/yt-verdict/SKILL.md` with YAML frontmatter; description 80–120 words mentioning concrete trigger phrases
- [ ] `skills/yt-verdict/` references the shared `scripts/fetch.py` and `scripts/analyze.py` (decide: symlink / relative path call / copy — document the choice in `SKILL.md`)
- [ ] `README.md` updated: install command, 3–4 example invocations, sister-skill roadmap
- [ ] Trigger-quality test: 5 different natural-language phrasings for "is this worth watching" pasted into a fresh Claude Code session; skill triggers in ≥4/5
- [ ] Public GitHub repo at `github.com/<owner>/youtube-inspector` (do NOT push without explicit confirmation)
- [ ] `npx skills add <owner>/youtube-inspector --skill yt-verdict` install command verified end-to-end

**Verification:** A fresh user installs via the published command, pastes a YouTube URL with a natural ask ("is this worth watching?"), gets a verdict report.

**Prompt to submit to Claude Code:**

```
Implement Phase 4 — skill packaging and skills.sh publish prep — for yt-verdict.

Read first:
- /Users/nishil/Documents/work/youtube-inspector/yt-worth-it-plan.md ("Publishing to skills.sh")
- /Users/nishil/Documents/work/youtube-inspector/PHASES.md (Phase 4 section)

Working directory: /Users/nishil/Documents/work/youtube-inspector/

Phases 0–3 are complete and verified.

Build:
- skills/yt-verdict/SKILL.md with YAML frontmatter (name: yt-verdict). The description is the most important part of this phase — spend real time on it. 80–120 words, mention concrete trigger phrases: "is this video worth watching", "what's actually in this video", "should I watch this", "skip or watch", "pre-watch summary", "is this YouTube video any good".
- Decide how skills/yt-verdict/ accesses scripts/fetch.py and scripts/analyze.py (symlink / relative-path subprocess call / copy). Document the choice and rationale in SKILL.md.
- Update README.md: install command (npx skills add <owner>/youtube-inspector --skill yt-verdict), 3–4 example invocations, sister-skill roadmap.

Trigger-quality test (you must run this before marking complete):
- Open 5 fresh Claude Code sessions in this repo
- Paste 5 different natural-language phrasings + a YouTube URL
- Record whether the skill triggered without prompting
- Acceptance: ≥4/5 trigger correctly. If <4/5, revise the description and retest.

Stop before pushing to GitHub or skills.sh. Report:
- Which 5 phrasings you tested and the trigger results
- The final description text
- The integration approach you chose (symlink/subprocess/copy)
- Any naming/description tweaks you'd recommend

DO NOT run git push or any skills.sh publish command without explicit user confirmation.

When done:
- Update PHASES.md: tick checkboxes, change summary row to [x] Complete, log the 5 trigger-test phrasings + outcomes in Change log.
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
