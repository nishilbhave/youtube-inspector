# yt-worth-it — Claude Code Skill Plan

## Why this exists

Pre-watch decision tool for YouTube. Answers one question:

> *Should I spend 20 minutes on this video, or skip it?*

Built to stop wasting 3–4 minutes scrubbing through videos that turn out to be filler, clickbait, or course pitches.

End goal: ship as a public skill on **skills.sh** so others can install it with one command.

---

## Critical framing — read first

This is **not** a "scam detector" or "BS detector."

That framing is inflammatory, creates defamation risk, and produces output people stop trusting. The skill rates **fit between a video's promise and its delivery** — never the creator's morality.

| Don't say | Do say |
|---|---|
| "This creator is misleading" | "Title promises X, content delivers Y" |
| "Scam" | "Low evidence quality" |
| "Fake guru" | "High pitch density, low substance" |

**Hard rule for prompts:** every flag in the report MUST cite a transcript timestamp + verbatim quote. No exceptions.

This single rule is what makes the skill defensible, auditable, and resistant to LLM hallucination. If the model can't quote it, it can't flag it.

---

## The output (this is the product)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {Title}
  {Channel} · {Duration} · {Views}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERDICT: {WATCH | SKIM | SKIP}            [{n}/10]

WHAT IT ACTUALLY DELIVERS
{section 1 with time range}
{section 2 with time range}
{section 3 with time range}

TITLE vs CONTENT
Title promises:  {claim}
Content delivers: {what appears}
Gap: {LOW | MEDIUM | HIGH}

SUBSTANCE DENSITY
Concrete claims: {n}
Vague claims:    {n}
Evidence shown:  {n}
Pitches/CTAs:    {n}

WHO SHOULD WATCH
{specific audience or "Nobody"}

WHO SHOULD SKIP
{specific audience}

BEST {n} MINUTES (if you must watch)
[{start}–{end}] {what's covered}
```

Designed to read in under 30 seconds.

---

## Architecture

```
yt-worth-it/
├── SKILL.md
├── scripts/
│   ├── fetch.py
│   └── analyze.py
├── prompts/
│   ├── extract_structure.md
│   ├── inventory_claims.md
│   └── generate_verdict.md
└── README.md
```

---

## Three-pass analysis

**Pass 1 — Structure extraction**

Transcript with timestamps → time-coded sections (hook / content / pitch / outro).

Mechanical segmentation. Use Haiku.

**Pass 2 — Claim & evidence inventory**

For each section, extract concrete claims, vague claims, evidence shown, and pitches. Each item must have a timestamp and quote.

Use Sonnet.

**Pass 3 — Synthesis**

Inputs: structure + claim inventory + metadata. Output: the report shown above.

Use Sonnet.

Don't combine these into one pass. Quality drops sharply, structured outputs become unreliable.

---

## Implementation phases

**Phase 1: `fetch.py`**

URL → JSON with video_id, title, channel, duration, transcript.

Primary: `youtube-transcript-api`. Fallback: `yt-dlp`.

Test on 5 video types before moving on: tutorial, podcast, finance pitch, news, vlog.

**Phase 2: prompts**

Write the three prompts. Iterate them on 10 real videos before wiring up Python.

The prompts are the actual product. Code is glue.

**Phase 3: `analyze.py`**

Orchestrate the three LLM calls. Cache by video_id. Save report to `~/yt-reports/{video_id}.md`.

**Phase 4: `SKILL.md`**

Routing logic + invocation triggers. See "Publishing to skills.sh" below for what this file needs.

---

## Hard constraints

1. Every flag cites a timestamp + verbatim quote. Drop anything that can't.

2. Reject videos under 3 minutes (180s). Not enough signal, false positive rate spikes. Lowered from 5min after testing — 3min still filters Shorts and trailers while letting dense finance/tutorial content through.

3. Reject live streams and playlists.

4. Phrase outputs as fit-with-title, never as judgments of the creator.

5. Cache by `video_id` — same video analyzed twice serves from cache.

6. Three separate LLM passes, not one combined prompt.

---

## V1 explicit non-goals

- ❌ Web search verification of claims
- ❌ Frame / visual analysis
- ❌ Multi-language support beyond English
- ❌ Comparison across multiple videos
- ❌ Public sharing of reports with creator names

These are V2. Don't scope-creep.

---

## Publishing to skills.sh

skills.sh indexes skills from public GitHub repos that follow the agent-skills convention.

**Requirements:**

1. Public GitHub repo
2. `SKILL.md` at the skill's root with YAML frontmatter:

   ```yaml
   ---
   name: yt-worth-it
   description: |
     Pre-watch decision tool for YouTube videos. Given a video URL, 
     produces a structured report showing what the video actually 
     delivers vs. what its title promises, with a WATCH/SKIM/SKIP 
     verdict. Use when user pastes a YouTube URL and asks whether 
     it's worth watching, what's actually in a video, or asks for 
     a pre-watch summary.
   ---
   ```

3. Description quality determines discoverability and trigger accuracy. Spend real time on it. Mention concrete trigger phrases ("is this video worth watching", "what's actually in this video", "should I watch").

4. README with install command and 3–4 example invocations.

5. Install entry: `npx skills add {owner}/{repo} --skill yt-worth-it`

**Discoverability angle:** no existing skill on skills.sh does pre-watch evaluation. Closest are transcript-dump skills and summarizers. Position the description to fill that gap explicitly.

---

## Open questions to brainstorm in Claude Code

1. Add `--query "what I'm looking for"` so users can frame the fit ("I want a Laravel queues tutorial") — V1 or V2?

2. Obsidian integration — auto-link reports? Frontmatter format?

3. Naming: `yt-worth-it`, `yt-prescreen`, `yt-decide`, `yt-skip-or-watch`? Picks affects discoverability on skills.sh.

4. Non-English videos — fetch + translate, or reject in V1?

5. Should the skill expose a "second opinion" mode that re-runs Pass 3 with different thresholds?

---

## First task in Claude Code

Build `fetch.py` first. No LLM, no prompts, just clean structured JSON output for the 5 test video types. Get the foundation solid before touching analysis.

Once that's stable, the prompts become the focus — and the prompts are where this skill lives or dies.
