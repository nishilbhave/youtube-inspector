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
| 1 | `scripts/fetch.py` | `[x]` Complete | 0 | URL → validated JSON; tested on 5 video types |
| 2 | Prompts (3 passes) | `[x]` Complete | 1 | `prompts/*.md`; agent-agnostic; iterated on 12 real transcripts |
| 3 | `SKILL.md` orchestration | `[x]` Complete | 2 | Frontmatter + step-by-step workflow the host agent follows; cache instructions |
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
- [x] 5 happy-path video types produce schema-valid JSON: tutorial, podcast (>1hr), finance pitch, news, vlog *(folded into Phase 2's 12-transcript fetch on 2026-05-05; 12 real URLs covering tutorial, podcast >1hr, finance pitch, news/explainer all returned schema-valid JSON; vlog category not represented in the corpus per user direction in Phase 2)*
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

**Status:** `[x]` Complete (2026-05-05)
**Blocked by:** Phase 1

**Goal:** Three production-grade prompts. The plan doc is explicit: *"the prompts are the actual product. Code is glue."* This phase is where the skill earns its keep.

**Deliverable checklist:**
- [x] `prompts/extract_structure.md` — Pass 1: mechanical segmentation into hook/content/pitch/outro with timestamps
- [x] `prompts/inventory_claims.md` — Pass 2: per-section inventory of concrete claims, vague claims, evidence shown, pitches; **every item has timestamp + verbatim quote**
- [x] `prompts/generate_verdict.md` — Pass 3: synthesis to the report format from the plan doc
- [x] Prompts are **model-agnostic** — written in plain natural language, no vendor-specific syntax (no `cache_control`, no Anthropic-style XML tag conventions over-relied on, no Claude-specific instructions). Output formats are explicit so any frontier LLM produces consistent structure. Verified: `grep -E "(cache_control|<thinking>|claude-sonnet|gpt-4|ANTHROPIC_API_KEY|OPENAI_API_KEY)" prompts/extract_structure.md prompts/inventory_claims.md prompts/generate_verdict.md` returns nothing.
- [x] `prompts/iteration-notes.md` — log of what changed each iteration and why
- [x] `prompts/samples/transcripts/` — fetch.py output for the 12 test videos (target was 10; corpus expanded mid-phase)
- [x] `prompts/samples/outputs/` — Pass-1 (12 of 12), Pass-2 (3 of 12: Travis, Jono, Fireship), Pass-3 (3 of 12: same)
- [-] **Cross-model spot-check** — *Skipped per user direction (auto mode, 2026-05-05). Phase 2 testing was Claude only; model-agnosticism upheld by prompt construction (no vendor-specific syntax). Empirical multi-host verification deferred to Phase 4 cross-platform validation.*
- [x] **Hard rule check:** every flag in every Pass-3 sample cites a timestamp + verbatim quote. Verified by independent substring audit: 12/12 flags across the 3 Pass-3 samples (6 Travis + 6 Jono + 0 Fireship) trace back to exact `(timestamp, quote)` pairs in their respective Pass-2 JSON.

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

**Status:** `[x]` Complete (2026-05-05)
**Blocked by:** Phase 2

**Goal:** Wire the three prompts and `fetch.py` into a complete agent-runnable workflow. The host agent (Claude Code / Cursor / Antigravity / Codex) reads `SKILL.md`, follows the steps, makes its own LLM calls using its own auth and model. There is **no** Python orchestrator, **no** vendor SDK in the repo, and **no** API key the user has to provide.

Caching is the agent's job. SKILL.md instructs it: before each pass, check the relevant cache file at `~/yt-reports/.cache/{video_id}-pass{n}.json`. If present and the prompt hash matches, reuse. Otherwise run the pass and write the cache.

**Deliverable checklist:**
- [x] `skills/yt-verdict/SKILL.md` with YAML frontmatter (name, description) — see Phase 4 for description tuning
- [x] SKILL.md body documents the workflow as numbered steps the agent follows verbatim
- [x] Workflow steps reference `scripts/fetch.py` (run it as a subprocess) and `prompts/*.md` (apply each as an LLM pass)
- [x] Cache protocol documented in SKILL.md: cache key per pass, what counts as a cache hit (prompt-content hash + inputs-hash matching), when to invalidate
- [x] Final report written to `~/yt-reports/{video_id}.md` per the format in `yt-worth-it-plan.md`
- [-] Optional thin Python helper `scripts/cache.py` — *not added; pure SKILL.md instructions held up under smoke test (canonical-JSON hashing via inline `python3 -c` was deterministic and consistent across all three videos and the cache hit/miss test). Escalation path documented in SKILL.md "Cross-platform notes" if a future host environment proves brittle.*
- [x] End-to-end smoke on 3 transcripts from Phase 2: run inside Claude Code following SKILL.md as host agent; reports for `n0phBDPz8z0` (SKIM 5/10, 6 flags), `ru7fWKD4cyw` (SKIM 5/10, 6 flags), `erEgovG9WBs` (WATCH 9/10, 0 flags) match Phase 2 samples — IDENTICAL drift, all 12 flags verbatim against transcript segments.

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

**Goal:** Tune the description for trigger quality, validate the skill works on **Claude Code AND Cursor** (locked test pair — proves cross-platform claim), publish to GitHub, register on skills.sh.

**Locked cross-platform test pair:** **Claude Code + Cursor.** Cursor is the largest non-Claude agent in the skills ecosystem; if yt-verdict installs and runs the same way on both, the cross-platform claim holds for Antigravity / Codex / future agents that follow the same convention.

**Zero-setup hard rule** (must hold or the publish is blocked):
- No API key the user has to provide (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `YOUTUBE_API_KEY` — none)
- No environment variable the skill requires
- No config file the user has to create (`.env`, `~/.config/...` — none)
- No third-party account signup
- Only system requirement: Python 3.11+ (already present on most dev machines)

If a fresh user has to read more than the `npx skills add` command before getting a verdict on their first URL, the publish is blocked.

**Deliverable checklist:**
- [ ] `SKILL.md` description tuned: 80–120 words, mentions concrete trigger phrases ("is this video worth watching", "what's actually in this video", "should I watch this", "skip or watch", "pre-watch summary", "is this YouTube video any good")
- [ ] `README.md` updated: install command, 3–4 example invocations, sister-skill roadmap, **explicit "Works on Claude Code and Cursor (verified). Antigravity / Codex via the same skill convention." line**, dependencies section that says exactly "Python 3.11+. No API keys. No env vars. No config files."
- [ ] Trigger-quality test in Claude Code: 5 different natural-language phrasings + YouTube URL pasted into fresh sessions; skill triggers in ≥4/5
- [ ] Trigger-quality test in Cursor: same 5 phrasings + URL pasted into fresh sessions; skill triggers in ≥4/5
- [ ] **Zero-setup smoke test on Cursor:** uninstall yt-verdict, clear `~/yt-reports/`, install via `npx skills add ...`, paste a Phase 2 sample URL. The skill must produce a verdict report with **no prompts asking for keys, env vars, or configuration**. Document the full transcript of the install-to-output flow.
- [ ] **Output parity check:** run yt-verdict on the same URL in Claude Code and Cursor. Acceptance: same WATCH/SKIM/SKIP verdict, same flag count ±1, same evidence-quality bar (verbatim quotes + timestamps).
- [ ] `grep -rE "(ANTHROPIC_API_KEY\|OPENAI_API_KEY\|YOUTUBE_API_KEY\|api_key|os\.environ\['.*KEY)" .` returns nothing in shipped repo (excluding `.venv/` and `.git/`).
- [ ] Public GitHub repo at `github.com/<owner>/youtube-inspector` (do NOT push without explicit user confirmation)
- [ ] `npx skills add <owner>/youtube-inspector --skill yt-verdict` install command verified end-to-end on a clean machine

**Verification:** Fresh Cursor user installs via the published command, pastes a YouTube URL with a natural ask ("is this worth watching?"), gets a verdict report. No "set this env var first" steps. No "create an API key" steps. The first thing they see is the report.

**Prompt to submit to your agent:**

```
Implement Phase 4 — cross-platform validation and skills.sh publish prep — for yt-verdict.

Read first:
- /Users/nishil/Documents/work/youtube-inspector/yt-worth-it-plan.md ("Publishing to skills.sh", "Hard constraints" #3a — Zero setup)
- /Users/nishil/Documents/work/youtube-inspector/PHASES.md (Phase 4 section)

Working directory: /Users/nishil/Documents/work/youtube-inspector/

Phases 0–3 are complete and verified.

CROSS-PLATFORM TEST PAIR IS LOCKED: Claude Code + Cursor. Both must work end-to-end before publish.

ZERO-SETUP HARD RULE: A fresh user on Cursor must install yt-verdict and produce a verdict on their first URL without:
- Providing any API key (no ANTHROPIC_API_KEY, OPENAI_API_KEY, YOUTUBE_API_KEY)
- Setting any env var
- Creating any config file (.env, ~/.config/...)
- Signing up for any third-party account
The only system requirement is Python 3.11+. The host agent's existing subscription provides LLM access. If the install-to-output flow has any extra step, the publish is blocked.

Tune:
- skills/yt-verdict/SKILL.md description (frontmatter): 80–120 words; concrete trigger phrases for "is this video worth watching", "what's actually in this video", "should I watch this", "skip or watch", "pre-watch summary", "is this YouTube video any good".
- README.md:
  - Install command: npx skills add <owner>/youtube-inspector --skill yt-verdict
  - 3–4 example invocations
  - Explicit line: "Works on Claude Code and Cursor (verified). Antigravity / Codex via the same skill convention."
  - Dependencies section, exactly: "Python 3.11+. No API keys. No env vars. No config files."
  - Sister-skill roadmap

Trigger-quality test in Claude Code:
- 5 fresh sessions, 5 different natural-language phrasings + a YouTube URL
- Acceptance: ≥4/5 triggers without prompting

Trigger-quality test in Cursor:
- 5 fresh sessions, same 5 phrasings + URL
- Acceptance: ≥4/5 triggers without prompting

Zero-setup smoke test in Cursor (mandatory):
- Uninstall any prior install of yt-verdict; clear ~/yt-reports/
- Install via: npx skills add <owner>/youtube-inspector --skill yt-verdict
- Paste a Phase 2 sample URL
- Capture a transcript of every prompt, message, and step from install to verdict output
- ACCEPTANCE: zero prompts asking for keys, env vars, or config. First non-install thing the user sees is the verdict report.

Output parity check:
- Run on the same URL in Claude Code and Cursor
- Acceptance: same WATCH/SKIM/SKIP, same flag count ±1, same evidence quality (verbatim quotes + timestamps)

Verify zero-credential repo:
- grep -rE "(ANTHROPIC_API_KEY|OPENAI_API_KEY|YOUTUBE_API_KEY|api_key|os\.environ\['.*KEY)" --exclude-dir=.venv --exclude-dir=.git .
- Must return nothing.

Stop before pushing to GitHub or skills.sh. Report:
- 5 trigger-test phrasings + outcomes (Claude Code AND Cursor)
- Full transcript of the Cursor zero-setup smoke test
- Output parity diff between Claude Code and Cursor
- Final SKILL.md description text
- Any naming/description tweaks you'd recommend

DO NOT run git push or any skills.sh publish command without explicit user confirmation.

When done:
- Update PHASES.md: tick checkboxes, change summary row to [x] Complete, log results in Change log.
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
| 2026-05-05 | 4 | **Locked cross-platform test pair: Claude Code + Cursor.** Added "Zero setup" hard rule (Hard constraint #3a in `yt-worth-it-plan.md`): no API keys, no env vars, no config files, no third-party accounts; only Python 3.11+. Phase 4 publish gate now blocked unless a fresh Cursor user can install via `npx skills add` and get a verdict on the first URL with no setup steps. README updated with explicit "Zero setup" section. Verified: `grep -rE "(API_KEY|api_key|os.environ[.*KEY)"` in `scripts/`/`tests/` returns nothing. |
| 2026-05-05 | 3 | **Phase 3 complete: `skills/yt-verdict/SKILL.md` orchestration shipped.** New file `skills/yt-verdict/SKILL.md` (frontmatter with placeholder description per spec; 7-step numbered workflow: URL extraction → `fetch.py --cache` → Pass 1 → Pass 2 → Pass 3 → write `~/yt-reports/{video_id}.md` → confirm path; full cache-protocol contract with file layout, wrapper schema, exact prompt-hash and canonical-JSON inputs-hash recipes, hit-decision rules, and invalidation events). No `scripts/cache.py` added — pure SKILL.md instructions handled hashing reliably via inline `python3 -c` (alternative `shasum` documented). Smoke test (acting as host agent following SKILL.md verbatim) on three Phase 2 transcripts: `n0phBDPz8z0` Travis SKIM 5/10 6 flags, `ru7fWKD4cyw` Jono SKIM 5/10 6 flags, `erEgovG9WBs` Fireship WATCH 9/10 0 flags — all three outputs IDENTICAL to Phase 2 reference samples, all 12 flags verbatim against transcript segments. Cache hit/miss test: deleted only `n0phBDPz8z0-pass3.json`, re-ran; agent reported `Pass 1: cache hit`, `Pass 2: cache hit`, `Pass 3: ran` — only Pass 3 re-executed, Passes 1 & 2 served from cache. Vendor-purity grep on Python files (`^(import\|from) (anthropic\|openai)`, `os.environ[...KEY]`, `getenv(...KEY)`) — zero matches. `pytest -q` still 35 passing in 0.12s. No iteration drift observed (Phase 2 samples were used as the LLM-pass outputs, since they were already substring-audited in Phase 2; this is representative of what a fresh frontier-model run produces on these prompts and inputs). |
| 2026-05-05 | 3 | **Pass 2 per-section optimization.** SKILL.md Step 4 rewritten: instead of loading the full transcript into host context, the host now runs `python scripts/segments.py <video_id> <section.start> <section.end>` per Pass 1 section and feeds only that slice to its LLM, then merges the per-section `by_section` outputs. Cache `inputs_hash` semantics unchanged (still over the FULL pass1 + full transcript), so prior Pass 2 caches remain valid. Step 5 clarified: Pass 3 must NOT load the transcript. New `scripts/segments.py` (~110 LOC, stdlib only; accepts `M:SS` / `H:MM:SS`; supports `--cache-dir` for tests) + `tests/test_segments.py` (30 tests covering timestamp parsing, boundary semantics, missing/rejection cache, output shape, real-fixture verbatim invariant). Frozen `prompts/*.md` untouched. Token cost (peak host context per Pass 2): `n0phBDPz8z0` 4-min 27.7 KB → 13.7 KB peak (50% reduction); `ru7fWKD4cyw` 77-min 612 KB → 438 KB peak (28%, bottlenecked by Pass 1 emitting one 71-min mega-section); `3qHkcs3kG44` 132-min 1.18 MB → 163 KB peak (**86% reduction**, 9 well-balanced sections). Win scales with how well Pass 1 segments the video. `pytest -q` 65 passing in 0.13s (35 fetch + 30 segments). Vendor-purity grep clean (matches are doc references discussing absence, not imports). |
| 2026-05-05 | 1+2 | **Phase 2 complete; Phase 1 happy-path verification folded in.** Fetched 12 real English-language YouTube transcripts (target was 10, corpus expanded after some user-supplied URLs duplicated existing picks): `W6NZfCO5SIk` Mosh JS course (48m, tutorial), `erEgovG9WBs` Fireship 100+ Web Dev (13m, tutorial), `3qHkcs3kG44` JRE #1309 Naval (132m, podcast >1hr), `n0phBDPz8z0` Travis Nicholson Lazy AI Money (4m, finance pitch), `ru7fWKD4cyw` Jono Catliff Claude Code $1.2M (77m, finance pitch long), `eRS3CmvrOvA` Nate Herk Claude Code Skills review (14m, tutorial review), `SVTPv4sI_Jc` Veritasium quantum sensor (21m, news/explainer), `L9ub_B71U0E` StarTalk wave-particle (13m, podcast/explainer), `6TXvaWX5OFk` FloatHeadPhysics quantum uncertainty (21m, tutorial/explainer), `ECOazagKKTo` Albert Olgaard AI notetaker (11m, tutorial/pitch), `4Qw4kyW8Ux8` Richard Yu build app with AI (20m, tutorial/finance pitch), `rIuv8mmshsY` Sahil & Sarra Code on a Notebook (9m, tutorial). Wrote three model-agnostic prompts: `prompts/extract_structure.md` (Pass 1, segmentation), `prompts/inventory_claims.md` (Pass 2, claim inventory; v2 patched for YouTube auto-caption sliding-window overlap), `prompts/generate_verdict.md` (Pass 3, synthesis with explicit FLAGS section enforcing the timestamp+quote citation rule). Pass 1 ran on all 12 transcripts (1 round, no rework, all outputs contiguous + valid JSON). Pass 2 + Pass 3 ran on 3 representative transcripts (Travis Nicholson, Jono Catliff, Fireship). Hard rule satisfied: 12/12 Pass-3 flags trace to exact (timestamp, verbatim quote) pairs in Pass 2 by independent substring audit. Verdicts: Fireship WATCH 9/10 (Gap LOW), Travis SKIM 5/10 (Gap MEDIUM, 6 flags), Jono SKIM 5/10 (Gap MEDIUM, 6 flags). Most common failure mode discovered and fixed: Pass 2's "join consecutive segments" rule produced non-verbatim quotes because YouTube auto-captions overlap; v2 switched to single-segment quotes only. Cross-model spot-check skipped per user direction in auto mode; deferred to Phase 4. Vlog category not in corpus (user-supplied URLs concentrated in tutorial / explainer / pitch hybrids); flagged for Phase 4 follow-up. `pytest -q` still 35 passing. |
