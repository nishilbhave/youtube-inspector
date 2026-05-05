# Publish Punchlist — youtube-inspector suite

Tracker for shipping the four built skills (verdict, summary, extract, claims) to skills.sh.
This is **not** the verdict-V1-only Phase 4 from `PHASES.md` — the suite scope subsumes it.

**Status legend:** `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` deferred / out of scope

---

## Already cleared

- `[x]` Public GitHub repo at `github.com/nishilbhave/youtube-inspector`
- `[x]` Working tree clean (latest commit `abad007` — fix #3 + cache.py mandate)
- `[x]` Vendor-purity grep clean across all skills + scripts + prompts
- `[x]` 121 tests passing (35 fetch + 30 segments + 22 cache + 34 slug)
- `[x]` Four SKILL.md files written, three smoke-tested (verdict in Phase 3, summary/extract/claims this session)
- `[x]` `youtube-tldr` renamed to `youtube-summary` for naming-register consistency with verdict/extract/claims (formal English nouns instead of internet shorthand). All cross-references, prompt paths (`generate_tldr.md` → `generate_summary.md`), report-filename suffix (`-tldr.md` → `-summary.md`), and cache filenames (`-tldr-pass2.json`/`-tldr-pass3.json` → `-summary-pass*.json`) updated. "tl;dr" preserved as a trigger phrase; "TL;DR" preserved as the report's section header (it's the format, not the skill name).
- `[x]` `scripts/cache.py` shipped — deterministic hashing, eliminates the cross-host cache-miss drift documented in fix #1
- `[x]` `python` → `python3` in all SKILL.md subprocess calls (fix #3)
- **No skills.sh registration step needed — skills.sh indexes `npx skills add <owner>/<repo>` automatically once the repo is public.** This drops what was item #11 of the Phase 4 punchlist.

---

## Pending — auto-executable in next session

### `[ ]` 1. Rewrite `README.md` in the codeprobe style

Reference template: <https://github.com/nishilbhave/codeprobe/blob/main/README.md>

Key sections to mirror (in order):
1. **Hero block** — center-aligned title, optional banner SVG, shields (install / license / platform / agents).
2. **One-paragraph pitch** — link `[agent skill](https://skills.sh)`. State what the suite does in one sentence.
3. **Feature bullets** — 5–6 high-density bullets (one per skill + one per cross-cutting property like "every flag cites a verbatim quote", "shared transcript cache across all skills", "no API keys").
4. **Sample Output** — show one real dashboard (verdict's WATCH/OKAY/SKIP block is the most striking) + a one-line "saved to ~/youtube-reports/..." caption.
5. **Install** — single `npx skills add nishilbhave/youtube-inspector` line (see decision §A below). Plus `npx skills update` / `npx skills remove` manage commands. Plus the deps prereq (see #3).
6. **Skills** — table of the 4 skills with trigger phrases and a one-line description of what each returns. Replace the current "Planned" table.
7. **How It Works** — architecture: 3-pass pipeline, Pass 1 shared, Pass 2 partial sharing (verdict ↔ claims), Pass 3 per-skill. Mention `scripts/fetch.py`, `scripts/segments.py`, `scripts/cache.py` as the shared scripts layer.
8. **Configuration** (or skip for V1) — none currently exists; could be a placeholder for future per-skill flags.

Strip the existing "Build status" section that points at PHASES.md; replace with a link to PUBLISH.md (this file) for ongoing publish work.

### `[ ]` 2. Add a banner SVG to `assets/banner.svg`

Codeprobe has one. Optional but elevates the README. Width 900, project name + tagline. Could be done with a simple SVG generator or hand-written.

### `[ ]` 3. Cross-platform deps story — README doc + `scripts/doctor.py`

**The biggest open cross-platform gap.** Smoke test on `n0phBDPz8z0` revealed bare `python3 scripts/fetch.py` fails with `ModuleNotFoundError: yt_dlp` on a default Mac (only `.venv/bin/python` has the deps).

Plan:
- README "Install" section: explicit one-liner `pipx install yt-dlp youtube-transcript-api` as a prerequisite. `pipx` keeps each tool isolated and is the modern Python-app install path; works on Mac (Homebrew) and most Linux. Document `pip install --user yt-dlp youtube-transcript-api` as a fallback for users without pipx.
- `scripts/doctor.py` — a ~60-LOC stdlib script that:
  - Imports `yt_dlp` and `youtube_transcript_api`
  - Prints `✓ all deps present` on success or the exact `pipx install ...` command on `ModuleNotFoundError`
  - Exits 0 / 1 accordingly
  - Has `tests/test_doctor.py` to lock the contract
- Document in each SKILL.md "Cross-platform notes" section: "If fetch.py fails with `ModuleNotFoundError`, run `python3 scripts/doctor.py` for the exact install command."

### `[ ]` 4. SKILL.md description audit — trigger collisions across 4 skills

Read all four `description:` frontmatter blocks side-by-side. Risk areas:

| Phrase | Should route to | Risk |
|---|---|---|
| "summarize this video" | summary | Could trigger summary OR verdict (verdict has "what's actually in this video") |
| "what's in this video" | summary or verdict (tied) | Both currently claim it |
| "is this worth watching" | verdict | Should be exclusive |
| "extract links" / "what tools did they mention" | extract | Should be exclusive |
| "what claims did they make" | claims | Should be exclusive |
| "list every claim" / "fact-check material" | claims | Should be exclusive |
| "best 5 minutes of this video" | verdict (already has BEST N MINUTES output) | Currently fine |

Action: rewrite each description so trigger phrases are exclusive to one skill. Move overlapping phrases to the most specific owner. Update `youtube-verdict/SKILL.md` description to drop "what's actually in this video" → that should belong to summary.

### `[ ]` 5. Pull the existing build status out of `README.md`'s "Build status" section

Currently points at PHASES.md (verdict-V1-only tracker). Replace with a link to this PUBLISH.md.

### `[ ]` 6. Update `PHASES.md`

Two cleanup tasks:
- Mark Phase 4's verdict-only deliverables as **superseded by PUBLISH.md** (the suite publish path subsumes them).
- Add a Change log entry summarizing this session: 3 sister skills built (summary, extract, claims), `scripts/cache.py` + 22 tests added, fix #3 (python→python3), publish punchlist scoped.

### `[ ]` 7. Run full test suite once more before any push

`.venv/bin/python -m pytest tests/ -q` — should be 121 passing or higher (will go up if doctor.py adds tests in #3).

---

## Pending — manual / requires you to drive

### `[ ]` 8. Trigger-quality test in Claude Code

For each of the 4 skills, 5 fresh sessions, 5 distinct natural-language phrasings + a YouTube URL. Acceptance: ≥ 4/5 triggers without prompting. **Do this AFTER #4** so the descriptions are tight before testing.

Suggested phrasings per skill (pick 5 each before running):

- **verdict:** "is this worth watching", "should I skip this", "give me a verdict on this video", "is this YouTube video any good", "watch or skip"
- **summary:** "summarize this video", "tl;dr", "what does this video cover", "give me the gist", "what does this say"
- **extract:** "extract links from this video", "what tools did they mention", "pull the code snippets", "what books did they reference", "list the resources"
- **claims:** "what claims does this video make", "list every claim", "show me the evidence", "extract testable claims", "what does this person assert"

### `[ ]` 9. Trigger-quality test in Cursor

Same 5 × 4 = 20 phrasings, fresh Cursor sessions. ≥ 4/5 per skill.

### `[ ]` 10. Zero-setup smoke test in Cursor

Per the "zero-setup hard rule" already locked into `yt-worth-it-plan.md` Hard constraint #3a:
1. Uninstall any prior install of the suite from Cursor.
2. Clear `~/youtube-reports/` (rename it aside if you want to keep current reports).
3. Run `pipx install yt-dlp youtube-transcript-api` (per #3).
4. Run `npx skills add nishilbhave/youtube-inspector`.
5. Paste a Phase 2 sample URL with a natural ask ("is this worth watching?").
6. Capture a transcript of every prompt the agent emits from install to verdict output.
7. **Acceptance:** zero prompts asking for keys, env vars, or config. First non-install thing the user sees is the verdict report.

### `[ ]` 11. Output parity check — Claude Code vs Cursor

Run the same skill on the same URL on both hosts. Acceptance: same WATCH/OKAY/SKIP (for verdict), same flag count ± 1, same evidence quality (verbatim quotes + timestamps). Repeat for one summary, one extract, one claims invocation each.

### `[ ]` 12. Commit + push

After #1 – #7 land, commit with a message that names the publish prep (e.g., `docs: rewrite README for 4-skill suite publish; add doctor.py for deps prereq`). Push to `origin/main` only with explicit go-ahead (no force push).

skills.sh will auto-index the repo on next crawl — no separate registration call needed.

### `[ ]` 13. (Post-publish) Verify install flow end-to-end

After skills.sh has indexed the repo, run `npx skills add nishilbhave/youtube-inspector` on a fresh machine (or container). Paste a URL. Confirm verdict, summary, extract, claims all trigger and produce reports.

---

## Open decisions for next session

### A. Single install vs per-skill install

Codeprobe's pattern is **one** install command, sub-skills auto-discovered:
```
npx skills add nishilbhave/codeprobe
```

Our current PHASES.md plan was per-skill:
```
npx skills add nishilbhave/youtube-inspector --skill youtube-verdict
```

**Recommendation:** match codeprobe — single install, all 4 skills come along. Pros: cleaner README, fewer commands to remember, skills.sh ranks one entry not four. Cons: a user who only wants verdict gets the others too — but at near-zero footprint (skills are markdown + Python; no runtime cost until invoked).

If you agree with the recommendation, the README install becomes a one-liner like codeprobe. If you want per-skill granularity, document both.

### B. Drop "youtube-batch" from the README's planned-skills section?

Per the May plan-mode session: batch is "last in ship sequence" but deferred until the four single-video skills validate cross-platform. Should the README mention it as "planned" or omit it for V1?

**Recommendation:** mention it as "Planned (V2)" so users see the roadmap, but don't include it in the install-eligible list.

### C. Drop quote / clip / channel from the README entirely?

The plan-mode session decided: drop quote, fold clip into verdict's `BEST N MINUTES` output (already done), defer channel hard.

**Recommendation:** omit from README entirely. They're not on the roadmap and listing them creates expectations we don't intend to ship.

---

## Punchlist summary (one-shot order for next session)

When you continue:

1. Open this file (`PUBLISH.md`) and confirm the open decisions in §A / §B / §C.
2. Auto-executable: items 1, 2, 3, 4, 5, 6, 7 in order. Roughly 30–60 minutes of editing + scripting; produces a clean repo state ready to push.
3. Hand off for items 8 – 13 (manual cross-platform tests + push + post-publish verification).

---

## Where context lives

- `PHASES.md` — verdict-V1 phase tracker (Phases 0–3 complete, Phase 4 superseded by this file)
- `yt-worth-it-plan.md` — original architecture spec (read first if context-loading from cold)
- `/Users/nishil/.claude/plans/image-4-what-all-dreamy-turing.md` — strategic plan from this session that decided which skills to build (summary, extract, claims, batch) and which to drop
- `~/youtube-reports/` — actual reports from smoke tests (verdict, summary, extract, claims all have at least one report each on disk; some legacy `-tldr.md` files remain from before the rename and can be cleared at smoke-test time)
- `~/youtube-reports/.cache/` — full cache state across all skills, validates the shared-cache architecture is working
