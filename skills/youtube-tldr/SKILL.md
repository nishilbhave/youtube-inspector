---
name: youtube-tldr
description: |
  Fast neutral summary tool for YouTube videos — no verdict, no judgment.
  Use when the user pastes a YouTube URL and asks "summarize this video",
  "tl;dr", "what does this video cover", "what's actually in this video",
  "give me the gist", "what does this say", "what's in here", or wants a
  30-second read of what was actually said. Returns a 3–4 sentence TL;DR, a
  section-by-section breakdown with timestamps, top takeaways as bullets,
  and skippable-section markers so the reader can fast-forward past pitches
  and outros. Factual and neutral — never recommends watching or skipping.
  For a watch/skip recommendation use `youtube-verdict` instead. Saves the
  full summary to ~/youtube-reports/ and prints a one-glance dashboard
  inline.
---

# youtube-tldr — fast summary tool for YouTube videos

You are the host agent running this skill. The user has asked for a summary, TL;DR, or "what's in this video" without asking for a verdict. Your job is to produce a structured summary at `~/youtube-reports/{date}-{slug}-{video_id}-tldr.md`.

This skill never says "watch" or "skip" — that's `youtube-verdict`'s job. If the user is asking for a verdict, hand off; otherwise produce a neutral factual summary.

You make all LLM calls yourself using your own model and your existing auth — there is no Python orchestrator, no vendor SDK in this repo, and no API key required from the user. The only system requirement is **Python 3.11+** for the bundled `scripts/fetch.py` and `scripts/segments.py`.

The skill assumes the working directory is the root of the `youtube-inspector` repo (where `scripts/`, `prompts/`, and `skills/` all live as siblings).

## Workflow — follow these steps in order

### Step 1 — Extract the video URL or 11-char ID from the user's input

Accepted forms (each is recognized by `scripts/fetch.py`):

- Plain 11-char ID: `n0phBDPz8z0`
- `https://www.youtube.com/watch?v=…` (also `m.youtube.com`, `music.youtube.com`)
- `https://youtu.be/…`
- `https://www.youtube.com/shorts/…`, `/embed/…`, `/live/…`

Reject playlist URLs (`/playlist`) — pass a specific video instead. If no URL is found in the user's message, ask them for one and stop.

### Step 2 — Fetch transcript and metadata

Run as a subprocess (no LLM call):

```
python3 scripts/fetch.py <url-or-id> --cache
```

The `--cache` flag reads/writes `~/youtube-reports/.cache/{video_id}.json` so a second run on the same video skips the network entirely.

Interpret the exit code:

| Exit | Meaning | Action |
|---|---|---|
| `0` | Success | Parse stdout JSON; continue to Step 3 |
| `2` | Documented rejection | Parse stderr JSON `{error, message, video_id}`; surface verbatim to the user and **stop** |
| `1` | Unexpected error | Surface to user and **stop** |

Documented rejection codes (exit 2): `INVALID_URL`, `PLAYLIST`, `LIVE_STREAM`, `TOO_SHORT` (under 180s), `NO_TRANSCRIPT`, `NON_ENGLISH`. Do **not** attempt the LLM passes when fetch rejects.

### Step 3 — Pass 1: Structure extraction (shared with youtube-verdict)

Cache file: `~/youtube-reports/.cache/{video_id}-pass1.json`.

This pass is **shared infrastructure** — the same prompt (`prompts/extract_structure.md`) and the same input (the fetch.py JSON) produce the same output regardless of which skill is asking. If a previous `youtube-verdict` run already wrote this cache file, this skill will hit it for free, and vice versa.

1. Compute `prompt_hash` for `prompts/extract_structure.md` (see "Cache protocol" below).
2. Compute `inputs_hash` for the canonical JSON `{"transcript": <full fetch.py output from Step 2>}`.
3. Try to read the cache file. If it exists, parses cleanly, has every required field, and both hashes match → **cache HIT**: load the `output` field as the Pass 1 result and continue to Step 4.
4. Otherwise → **cache MISS**: read `prompts/extract_structure.md`, apply it to the transcript JSON as a single LLM pass following the prompt's instructions exactly, parse the model response as JSON (it must be a single JSON object — no preamble, no markdown fences), and write the cache wrapper file:

```json
{
  "video_id": "<11-char id>",
  "pass": 1,
  "prompt_hash": "<sha256 hex>",
  "inputs_hash": "<sha256 hex>",
  "output": <the Pass 1 JSON object you just produced>,
  "produced_at": "<ISO 8601 UTC, e.g. 2026-05-05T14:32:08Z>"
}
```

Tell the user one short line: `Pass 1: cache hit` or `Pass 1: ran (N sections extracted)`.

### Step 4 — Pass 2: Per-section summarization

Cache file: `~/youtube-reports/.cache/{video_id}-tldr-pass2.json`.

The cache wrapper schema is identical to Pass 1 (`video_id`, `pass: 2`, `prompt_hash`, `inputs_hash`, `output`, `produced_at`). What differs:

- Prompt: `prompts/summarize_sections.md`.
- Canonical inputs (used **only** for `inputs_hash`): `{"pass1": <full Pass 1 output>, "transcript": <full fetch.py output>}`.
- The `output` field is the merged Pass 2 JSON object (`{video_id, by_section}`).

If hashes match → HIT, skip to "Tell the user".

#### On a cache miss — per-section execution

Loading the entire transcript into context burns ~17 K tokens for a 15-min video and ~120 K for a 75-min one. Process the transcript section by section instead.

For each section in Pass 1's `sections[]`, in order:

1. Run as a subprocess (no LLM call):
   ```
   python3 scripts/segments.py <video_id> <section.start> <section.end>
   ```
   Pass `<section.start>` and `<section.end>` as the `M:SS` (or `H:MM:SS`) strings from Pass 1 unchanged. Stdout is a compact JSON object:
   ```json
   {"video_id":"…","title":"…","duration_seconds":N,"transcript":[<segments in [start,end)>]}
   ```
   Capture stdout. Do **not** also Read the full transcript file.

2. Apply `prompts/summarize_sections.md` as a single LLM pass with these inputs:
   ```json
   {
     "pass1": {"video_id": "<id>", "sections": [<just this one section object from Pass 1>]},
     "transcript": <stdout from step 1, parsed as JSON>
   }
   ```
   The model returns a JSON object `{"video_id":"<id>","by_section":{"<this section's id>": {...}}}` (one key in `by_section`).

3. Merge that one `by_section` entry into a running merged dict. Drop the section's transcript slice from your context before moving to the next section.

After all sections are processed, the final Pass 2 output is `{"video_id": "<id>", "by_section": <merged dict>}`. Write the cache wrapper using this output and the `inputs_hash` computed over the FULL canonical inputs (full Pass 1 + full fetch.py JSON), not the per-section slices.

If `scripts/segments.py` is unavailable, the inline fallback documented in `youtube-verdict`'s SKILL.md (Step 4) applies here unchanged.

#### Tell the user

`Pass 2: cache hit` or `Pass 2: ran (N sections summarized)`.

### Step 5 — Pass 3: Synthesis into TL;DR report

Cache file: `~/youtube-reports/.cache/{video_id}-tldr-pass3.json`.

Same wrapper schema. Differences:

- Prompt: `prompts/generate_tldr.md`.
- Canonical inputs: `{"metadata": <metadata subset>, "pass1": <Pass 1 output>, "pass2": <Pass 2 output>}`.
- Metadata subset: `{title, channel, duration_seconds, view_count, upload_date}` from the Step 2 fetch JSON.
- **Pass 3 does not need the transcript at all.** Pass 2 already contains every section's summary and key points. Do not Read `~/youtube-reports/.cache/{video_id}.json` for this pass.
- The model's response is markdown wrapped in a single fenced code block (the prompt enforces this). Strip the outer ` ``` ` fence; what remains is the report text.
- The `output` field of the cache wrapper is the **stripped** report **as a JSON string**.

Tell the user: `Pass 3: cache hit` or `Pass 3: ran`.

### Step 6 — Write the final report

Build the filename from the Step 2 fetch JSON:

- `{date}` — first 10 characters of `fetched_at` (UTC, `YYYY-MM-DD`).
- `{slug}` — the `slug` field from the fetch JSON (deterministic, lowercase, ≤ 60 chars; falls back to `untitled`).
- `{video_id}` — the 11-char ID.

Write the unwrapped Pass 3 report (the markdown text from the cache `output`) to:

```
~/youtube-reports/{date}-{slug}-{video_id}-tldr.md
```

The `-tldr` suffix differentiates this from `youtube-verdict`'s output for the same video. Always overwrite if it exists. Do not print the full report inline — terminal output is the dashboard in Step 7.

### Step 7 — Show the TL;DR dashboard inline

Print this dashboard directly to the user. Borders are exactly 54 box-drawing characters `━`. Two-space indent on every content line. Soft-wrap the TL;DR paragraph around column 60.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📝 TL;DR  ·  {title_truncated}  ·  {duration_human}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  {tldr_paragraph — 3–4 sentences, soft-wrapped to ~60 cols}

  🎯 Top takeaways
     • {bullet 1, ≤ 80 chars}
     • {bullet 2, ≤ 80 chars}
     • {bullet 3, ≤ 80 chars}

  ⏭️  Skippable     {comma-separated [start–end] ranges, or "—"}

  📄 ~/youtube-reports/{date}-{slug}-{video_id}-tldr.md
```

#### Field extraction

- `title_truncated`: first 50 chars of `title` from Step 2 fetch JSON, suffixed with `…` if longer.
- `duration_human`: `M:SS` if `duration_seconds` < 3600, else `H:MM:SS`.
- `tldr_paragraph`: the prose paragraph(s) under the `TL;DR` header in the Pass 3 report. Strip leading/trailing whitespace. Soft-wrap to ~60 cols at word boundaries; indent wrapped lines with 2 spaces (align under the dashboard's content indent).
- `Top takeaways`: the first three bullets from the `KEY TAKEAWAYS` section of the Pass 3 report. Truncate each bullet at 80 chars + `…` if longer. If fewer than 3 bullets exist, show what's there.
- `Skippable`: parse the `SKIPPABLE SECTIONS` section. Show comma-separated `[start–end]` ranges. If the section is empty or missing, render the value as `—`.
- File path footer: literal `📄 ` + the path written in Step 6.

## Cache protocol

Identical to `youtube-verdict`'s cache protocol. See `skills/youtube-verdict/SKILL.md` → "Cache protocol — exact contract" for the full spec (file layout, wrapper schema, hashing recipe, hit decision, invalidation events).

**Always compute hashes via `scripts/cache.py`** — `python3 scripts/cache.py hash-file <prompt-path>` for `prompt_hash`, and `python3 scripts/cache.py hash-json` (reading canonical-inputs JSON from stdin) for `inputs_hash`. Inline shell or `python3 -c` snippets drift across host agents and produce spurious cache misses.

Skill-specific cache files:

| Filename | Owner | Contents |
|---|---|---|
| `{video_id}.json` | `scripts/fetch.py` | Transcript JSON (shared) |
| `{video_id}-pass1.json` | shared (verdict + tldr) | Pass 1 cache wrapper |
| `{video_id}-tldr-pass2.json` | this skill | Pass 2 cache wrapper |
| `{video_id}-tldr-pass3.json` | this skill | Pass 3 cache wrapper |

Per-pass canonical inputs:

| Pass | Prompt | Canonical inputs |
|---|---|---|
| 1 | `prompts/extract_structure.md` | `{"transcript": <full fetch.py JSON>}` |
| 2 | `prompts/summarize_sections.md` | `{"pass1": <Pass 1 output>, "transcript": <full fetch.py JSON>}` |
| 3 | `prompts/generate_tldr.md` | `{"metadata": {"title":…, "channel":…, "duration_seconds":…, "view_count":…, "upload_date":…}, "pass1": <Pass 1 output>, "pass2": <Pass 2 output>}` |

## Cross-platform notes

- Steps 3, 4, and 5 use your own LLM and auth. No `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / vendor key required.
- Step 2 is the only subprocess call. If the host can't shell out, importing `scripts.fetch` as a Python module and calling `fetch(video_id, "en")` is equivalent.
- Cache reads and writes use ordinary file tool use.
- If `python3 scripts/fetch.py` fails with `ModuleNotFoundError`, run `python3 scripts/doctor.py` for the exact `pipx install` command to fix the deps prereq.

## Output format reminder

- Pass 1 output: shared with verdict, see `prompts/extract_structure.md`.
- Pass 2 output: JSON object `{video_id, by_section}` where each section has `summary` (2–4 sentences) and `key_points` (array of short strings) — see `prompts/summarize_sections.md`.
- Pass 3 output: a single fenced markdown block following the report layout in `prompts/generate_tldr.md`. Tone is **factual and neutral** — no recommendations, no judgments, no "you should watch this". The output answers "what was actually said?" and nothing more.
