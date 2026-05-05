---
name: yt-verdict
description: |
  Pre-watch decision tool for YouTube. Given a video URL, produces a
  WATCH/SKIM/SKIP verdict with a 0–10 score, what the video actually
  delivers vs what the title promises, substance density, who should
  watch or skip, and the best minutes if you must watch. Saves a full
  report to ~/yt-reports/ and prints a one-glance dashboard inline.
---

# yt-verdict — pre-watch decision tool for YouTube videos

You are the host agent running this skill. The user has asked whether a YouTube video is worth watching, what's actually in it, or for a pre-watch summary. Your job is to produce a structured report at `~/yt-reports/{video_id}.md`.

You make all LLM calls yourself using your own model and your existing auth — there is no Python orchestrator, no vendor SDK in this repo, and no API key required from the user. The only system requirement is **Python 3.11+** for the bundled `scripts/fetch.py`.

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
python scripts/fetch.py <url-or-id> --cache
```

The `--cache` flag reads/writes `~/yt-reports/.cache/{video_id}.json` so a second run on the same video skips the network entirely.

Interpret the exit code:

| Exit | Meaning | Action |
|---|---|---|
| `0` | Success | Parse stdout JSON; continue to Step 3 |
| `2` | Documented rejection | Parse stderr JSON `{error, message, video_id}`; surface the rejection to the user verbatim and **stop** |
| `1` | Unexpected error | Surface to user and **stop** |

Documented rejection codes (exit 2): `INVALID_URL`, `PLAYLIST`, `LIVE_STREAM`, `TOO_SHORT` (under 180s), `NO_TRANSCRIPT`, `NON_ENGLISH`. Do **not** attempt the LLM passes when fetch rejects.

The success JSON has these keys (you'll need them later):

```
video_id, url, title, channel, channel_id,
duration_seconds, view_count, upload_date, language,
transcript[]      // each segment: {start, duration, text}
fetched_at
```

### Step 3 — Pass 1: Structure extraction

Cache file: `~/yt-reports/.cache/{video_id}-pass1.json`.

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

### Step 4 — Pass 2: Claim & evidence inventory

Cache file: `~/yt-reports/.cache/{video_id}-pass2.json`.

The Pass 2 cache protocol is the same as Step 3 (prompt-hash + inputs-hash check, then write the wrapper file on a miss). What's different is **how a cache miss is executed**: do not load the full transcript into your context. Process the transcript section by section instead.

#### Cache hit/miss decision

- Prompt: `prompts/inventory_claims.md`.
- Canonical inputs (used **only** for `inputs_hash`): `{"pass1": <full Pass 1 output>, "transcript": <full fetch.py output>}`. This is the same canonical hash input as before — a cache written by an older version of this skill is still a hit.
- The `output` field of the cache wrapper is the merged Pass 2 JSON object (`{video_id, by_section}`).

If the hash check produces a HIT → skip to "Tell the user" below.

#### On a cache miss — per-section execution

Loading the entire transcript into context burns ~17 K tokens for a 15-min video and ~120 K for a 75-min one. Do this instead:

For each section in Pass 1's `sections[]`, in order:

1. Run as a subprocess (no LLM call):
   ```
   python scripts/segments.py <video_id> <section.start> <section.end>
   ```
   `<section.start>` and `<section.end>` are the `M:SS` (or `H:MM:SS`) strings from Pass 1 — pass them through unchanged. Stdout is a compact JSON object of the form:
   ```json
   {"video_id":"…","title":"…","duration_seconds":N,"transcript":[<segments in [start,end)>]}
   ```
   Capture stdout. Do **not** also Read the full transcript file.

2. Apply `prompts/inventory_claims.md` as a single LLM pass with these inputs (just this one section, just its segments):
   ```json
   {
     "pass1": {"video_id": "<id>", "sections": [<just this one section object from Pass 1>]},
     "transcript": <stdout from step 1, parsed as JSON>
   }
   ```
   The model returns a JSON object `{"video_id":"<id>","by_section":{"<this section's id>": {...}}}` (one key in `by_section`).

3. Merge that one `by_section` entry into a running merged dict. Keep the cumulative dict, drop the section's transcript slice from your context before moving to the next section.

After all sections are processed, the final Pass 2 output is `{"video_id": "<id>", "by_section": <merged dict>}`. Write the cache wrapper using this output and the `inputs_hash` computed over the FULL canonical inputs (full Pass 1 + full fetch.py JSON), not the per-section slices.

If `scripts/segments.py` is unavailable for any reason, an inline fallback is:
```
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); s,e=<start_sec>,<end_sec>; \
  print(json.dumps({k:d[k] for k in ['video_id','title','duration_seconds']} | \
  {'transcript':[x for x in d['transcript'] if s<=x['start']<e]}, separators=(',',':')))" \
  ~/yt-reports/.cache/<video_id>.json
```
Convert the Pass 1 `M:SS` boundaries to seconds yourself in this fallback.

#### Tell the user

`Pass 2: cache hit` or `Pass 2: ran (N items inventoried)` (where N is the total of all `concrete_claims`/`vague_claims`/`evidence_shown`/`pitches` across sections).

### Step 5 — Pass 3: Synthesis

Cache file: `~/yt-reports/.cache/{video_id}-pass3.json`.

Same protocol as Step 3, but:

- Prompt: `prompts/generate_verdict.md`.
- Canonical inputs: `{"metadata": <metadata subset>, "pass1": <Pass 1 output>, "pass2": <Pass 2 output>}`.
- The metadata subset is exactly: `{title, channel, duration_seconds, view_count, upload_date}` from the Step 2 fetch JSON.
- **Pass 3 does not need the transcript at all.** Every flag in the verdict cites a quote from Pass 2 (which already substring-matches the transcript). Do not Read `~/yt-reports/.cache/{video_id}.json` for this pass.
- The model's response is markdown wrapped in a single fenced code block (the prompt enforces this format). Strip the outer ` ``` ` fence; what remains is the report text.
- The `output` field of the cache wrapper is the **stripped** report **as a JSON string**.

Tell the user: `Pass 3: cache hit` or `Pass 3: ran` plus the verdict line (e.g. `→ SKIM 5/10`).

### Step 6 — Write the final report

Build the filename from the Step 2 fetch JSON:

- `{date}` — first 10 characters of `fetched_at` (UTC, `YYYY-MM-DD`).
- `{slug}` — the `slug` field from the fetch JSON (already deterministic, lowercase, ≤ 60 chars; falls back to `untitled` for non-Latin titles).
- `{video_id}` — the 11-char ID, kept at the end so cache lookups and re-runs match unambiguously.

Write the unwrapped Pass 3 report (the markdown text from the cache `output`) to:

```
~/yt-reports/{date}-{slug}-{video_id}.md
```

Always overwrite if it exists. Re-running on the same video produces an identical filename — `--cache` keeps `fetched_at` stable, so no orphan files accumulate. Do **not** print the full report inline — it's a structured document meant for the file. Terminal output is the dashboard in Step 7.

### Step 7 — Show the verdict dashboard inline

Print this dashboard directly to the user. Borders are exactly 54 box-drawing characters `━`. Two-space indent on every content line. Soft-wrap the executive verdict around column 60.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {STATE_BADGE}  {VERDICT}  ·  {score}/10  ·  Gap {LOW|MEDIUM|HIGH}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  {STATE_PROSE_GLYPH} {executive_verdict — 2–3 sentences, soft-wrapped}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  {title}
  {channel}  ·  {duration_human}

  🎯 Best minutes   [{start}–{end}] — {one-line description}
  📊 Substance      {concrete} concrete · {vague} vague · {evidence} evidence
  👥 Watch if       {audience}
  👥 Skip if        {audience}

  🚩 Flags ({n})
     [{ts}] "{quote, ≤40 chars}…"   — {short reason}
     [{ts}] "{quote, ≤40 chars}…"   — {short reason}

  📄 ~/yt-reports/{date}-{slug}-{video_id}.md
```

#### State glyph table

| `VERDICT` | `STATE_BADGE` | `STATE_PROSE_GLYPH` |
| --------- | ------------- | ------------------- |
| WATCH     | ✅            | ✨                  |
| SKIM      | ⚠️             | ⏩                  |
| SKIP      | ❌            | 🚫                  |

#### Field extraction

- `VERDICT`, `score`: parse from the Pass 3 report's `VERDICT: …` line.
- `Gap`: parse from the `Gap:` line under `TITLE vs CONTENT`.
- `executive_verdict`: the prose paragraph(s) under the new `EXECUTIVE VERDICT` header in the Pass 3 report. Strip any leading/trailing whitespace. Soft-wrap to ~60 columns by inserting newlines at word boundaries; indent wrapped lines to align under the prose glyph (3 spaces).
- `title`, `channel`: from the Step 2 fetch JSON.
- `duration_human`: `M:SS` if `duration_seconds` < 3600, else `H:MM:SS`.
- `Best minutes`: parse the `BEST {n} MINUTES (if you must watch)` block; show the `[start–end]` range and the one-line description on a single line. **Omit this entire line** when the report says `Nothing — full skip recommended.`
- `Substance`: integer counts from `SUBSTANCE DENSITY` — `Concrete claims`, `Vague claims`, `Evidence shown`.
- `Watch if`: copy the line under `WHO SHOULD WATCH` verbatim (one line; if it's `Nobody`, render the value as `Nobody`).
- `Skip if`: copy the line under `WHO SHOULD SKIP` verbatim.
- `Flags`: count = total bullets in the `FLAGS` section. Show the **first two bullets only**. Each bullet's `quote` is truncated to 40 chars + `…` if longer; the timestamp and reason are kept verbatim. **Omit the entire Flags block** (header + bullets) when the report omits its `FLAGS` section (verdict WATCH, Gap LOW); the `Flags` line and bullets are dropped together.
- File path footer: literal `📄 ` + the path you wrote in Step 6.

The user gets the verdict at a glance and opens the file only for the full breakdown (sections, substance density details, all flags with full quotes).

## Cache protocol — exact contract

This is the contract any host agent implements via file tool use. There is no Python helper; all hashing and JSON read/write is done with the host's standard tools.

### File layout

All cache files live under `~/yt-reports/.cache/`:

| Filename | Owner | Contents |
|---|---|---|
| `{video_id}.json` | `scripts/fetch.py` | Transcript JSON (or rejection JSON with `error` key) |
| `{video_id}-pass1.json` | this skill | Pass 1 cache wrapper |
| `{video_id}-pass2.json` | this skill | Pass 2 cache wrapper |
| `{video_id}-pass3.json` | this skill | Pass 3 cache wrapper |

### Cache wrapper schema (Pass N, N ∈ {1, 2, 3})

```json
{
  "video_id": "<11-char id>",
  "pass": <1 | 2 | 3>,
  "prompt_hash": "<sha256 hex string, lowercase, 64 chars>",
  "inputs_hash": "<sha256 hex string, lowercase, 64 chars>",
  "output": <object for pass 1 & 2; string for pass 3>,
  "produced_at": "<ISO 8601 UTC, ending in Z>"
}
```

### How to compute `prompt_hash`

Hash the **raw bytes** of the prompt file. Any of these works (pick one consistent with your platform):

```
# macOS / Linux shell
shasum -a 256 prompts/extract_structure.md | awk '{print $1}'

# Or via Python (same result, more portable):
python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" prompts/extract_structure.md
```

Mapping: Pass 1 → `prompts/extract_structure.md`; Pass 2 → `prompts/inventory_claims.md`; Pass 3 → `prompts/generate_verdict.md`.

### How to compute `inputs_hash`

Build the inputs object for the pass (see each step), then hash its **canonical JSON** form. Canonical means:

- Keys sorted lexicographically at every nesting level.
- Compact separators (no spaces): `","` and `":"`.
- `ensure_ascii=False` (UTF-8 output, non-ASCII characters preserved as-is).
- No trailing newline before hashing.

In Python (use this exact one-liner pattern when in doubt):

```
python3 -c "import json,hashlib,sys; \
  obj=json.load(sys.stdin); \
  s=json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8'); \
  print(hashlib.sha256(s).hexdigest())"
```

Per pass:

| Pass | Canonical inputs |
|---|---|
| 1 | `{"transcript": <full fetch.py JSON>}` |
| 2 | `{"pass1": <Pass 1 output>, "transcript": <full fetch.py JSON>}` |
| 3 | `{"metadata": {"title":…, "channel":…, "duration_seconds":…, "view_count":…, "upload_date":…}, "pass1": <Pass 1 output>, "pass2": <Pass 2 output>}` |

The whole transcript object (including `fetched_at`) goes into Passes 1 and 2's input. In practice `--cache` keeps `fetched_at` stable across re-runs so this doesn't cause spurious misses.

### Cache hit decision

A cache file is a HIT if and only if **all** of the following are true:

1. The file exists at `~/yt-reports/.cache/{video_id}-pass{N}.json` and parses as JSON.
2. The JSON contains all required fields: `video_id`, `pass`, `prompt_hash`, `inputs_hash`, `output`.
3. `video_id` matches the request and `pass` equals N.
4. `prompt_hash` equals the freshly computed hash of the corresponding prompt file.
5. `inputs_hash` equals the freshly computed hash of the canonical inputs.

Otherwise it's a MISS — re-run the pass and overwrite the file.

### Invalidation events (all handled automatically by the hash check)

- Prompt file edited → `prompt_hash` mismatch → MISS.
- Transcript re-fetched with different segments → `inputs_hash` mismatch on Pass 1 → cascades through Pass 2 and Pass 3.
- File deleted by hand → MISS.
- File corrupted (bad JSON, missing fields) → MISS.
- Pass 1 output changes (re-run) → Pass 2's `inputs_hash` mismatches → cascades to Pass 3.

You **never** overwrite `~/yt-reports/{video_id}.md` from cache. Step 6 only writes that file when Step 5 produces a Pass 3 result (whether from cache or fresh). The user's final report is always derived from a Pass 3 cache hit or a fresh Pass 3 run — never stale.

## Cross-platform notes

- Steps 3, 4, and 5 use your own LLM and auth. No `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / vendor key is required from the user.
- Step 2 is the only subprocess call. If your host can't shell out, importing `scripts.fetch` as a Python module and calling `fetch(video_id, "en")` is equivalent.
- Cache reads and writes use ordinary file tool use. The hashing instructions above are deterministic across hosts when followed exactly.
- If you find that hash computation is brittle in your host environment (e.g. canonical JSON serialization disagrees between runs), a `scripts/cache.py` helper can be added to the repo to centralize the logic. None is shipped today.

## Output format reminder

- Pass 1 output: JSON object `{video_id, sections[]}` — see `prompts/extract_structure.md`.
- Pass 2 output: JSON object `{video_id, by_section}` — see `prompts/inventory_claims.md`.
- Pass 3 output: a single fenced markdown block following the report layout in `prompts/generate_verdict.md`. Every flag MUST cite a transcript timestamp + verbatim quote drawn from Pass 2 — this is the skill's hard rule. If the model can't quote it, it can't flag it.
