---
name: youtube-extract
description: |
  Artifact extraction tool for YouTube videos — pulls links, code snippets,
  named books, tools, and people mentioned. Use when the user pastes a
  YouTube URL and asks "extract links from this video", "what tools did
  they mention", "what books did they reference", "pull the code snippets",
  "list the resources", "give me the references", or wants a clean
  reference list of named artifacts. Returns a categorized list (links,
  code, books, tools, people) with timestamps and verbatim mentions, plus
  an inline counts dashboard. Useful for tutorials, podcasts, and
  explainers where the creator references many resources. Saves the full
  extract to ~/youtube-reports/ and prints a one-glance dashboard inline.
---

# youtube-extract — pull named artifacts from a YouTube video

You are the host agent running this skill. The user has asked for the resources, references, links, code, books, tools, or people mentioned in a video. Your job is to produce a categorized reference list at `~/youtube-reports/{date}-{slug}-{video_id}-extract.md`.

This skill is purely **factual reference extraction**. It does not summarize, recommend, judge, or rank. Every entry is a verbatim mention from the transcript with a timestamp.

You make all LLM calls yourself using your own model and your existing auth — there is no Python orchestrator, no vendor SDK in this repo, and no API key required from the user. The only system requirement is **Python 3.11+** for the bundled `scripts/fetch.py`, `scripts/segments.py`, and `scripts/cache.py`.

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

Interpret the exit code per the standard mapping (0 success, 2 documented rejection, 1 unexpected error). Documented rejection codes (exit 2): `INVALID_URL`, `PLAYLIST`, `LIVE_STREAM`, `TOO_SHORT` (under 180s), `NO_TRANSCRIPT`, `NON_ENGLISH`. Surface rejections verbatim and stop — do not attempt the LLM passes.

### Step 3 — Pass 1: Structure extraction (shared with youtube-verdict and youtube-tldr)

Cache file: `~/youtube-reports/.cache/{video_id}-pass1.json`.

Pass 1 is **shared infrastructure** — same prompt, same input, same output regardless of which skill is asking. Hits cache for free if `youtube-verdict` or `youtube-tldr` previously ran on this video.

1. Compute `prompt_hash`: `python3 scripts/cache.py hash-file prompts/extract_structure.md`.
2. Compute `inputs_hash`: pipe the canonical inputs JSON `{"transcript": <full fetch.py output>}` to `python3 scripts/cache.py hash-json`.
3. Read `~/youtube-reports/.cache/{video_id}-pass1.json`. If both hashes match → **cache HIT**: load the `output` field and continue. Otherwise → **cache MISS**: read `prompts/extract_structure.md`, apply it as a single LLM pass following the prompt's instructions, parse the model response as JSON, and write the cache wrapper file (schema below).

Tell the user: `Pass 1: cache hit` or `Pass 1: ran (N sections extracted)`.

### Step 4 — Pass 2: Per-section artifact extraction

Cache file: `~/youtube-reports/.cache/{video_id}-extract-pass2.json`.

Cache wrapper schema is identical to Pass 1 (`video_id`, `pass: 2`, `prompt_hash`, `inputs_hash`, `output`, `produced_at`). What differs:

- Prompt: `prompts/extract_artifacts.md`.
- Canonical inputs (used **only** for `inputs_hash`): `{"pass1": <full Pass 1 output>, "transcript": <full fetch.py output>}`.
- The `output` field is the merged Pass 2 JSON object (`{video_id, by_section}`).

If hashes match → HIT, skip to "Tell the user".

#### On a cache miss — per-section execution

For each section in Pass 1's `sections[]`, in order:

1. Run as a subprocess (no LLM call):
   ```
   python3 scripts/segments.py <video_id> <section.start> <section.end>
   ```
   Pass `<section.start>` and `<section.end>` as the `M:SS` (or `H:MM:SS`) strings from Pass 1 unchanged. Stdout is a compact JSON object containing only the segments in `[start, end)`.

2. Apply `prompts/extract_artifacts.md` as a single LLM pass with these inputs:
   ```json
   {
     "pass1": {"video_id": "<id>", "sections": [<just this one section object>]},
     "transcript": <stdout from step 1, parsed as JSON>
   }
   ```
   The model returns a JSON object `{"video_id":"<id>","by_section":{"<this section's id>": {...}}}` (one key in `by_section`).

3. Merge that one `by_section` entry into a running merged dict. Drop the section's transcript slice from your context before moving to the next section.

After all sections are processed, the final Pass 2 output is `{"video_id": "<id>", "by_section": <merged dict>}`. Write the cache wrapper using this output and the `inputs_hash` computed over the FULL canonical inputs.

#### Tell the user

`Pass 2: cache hit` or `Pass 2: ran (N artifacts found across L/C/B/T/P)` (where L/C/B/T/P are counts for links/code/books/tools/people).

### Step 5 — Pass 3: Synthesis into the extract report

Cache file: `~/youtube-reports/.cache/{video_id}-extract-pass3.json`.

Same wrapper schema. Differences:

- Prompt: `prompts/generate_extract.md`.
- Canonical inputs: `{"metadata": <metadata subset>, "pass1": <Pass 1 output>, "pass2": <Pass 2 output>}`.
- Metadata subset: `{title, channel, duration_seconds, view_count, upload_date}` from the Step 2 fetch JSON.
- **Pass 3 does not need the transcript at all.** Pass 2 already contains every artifact's verbatim quote and timestamp. Do not Read `~/youtube-reports/.cache/{video_id}.json` for this pass.
- The model's response is markdown wrapped in a single fenced code block. Strip the outer ` ``` ` fence; what remains is the report text.
- The `output` field of the cache wrapper is the **stripped** report **as a JSON string**.

Tell the user: `Pass 3: cache hit` or `Pass 3: ran`.

### Step 6 — Write the final report

Build the filename from the Step 2 fetch JSON: `{date}-{slug}-{video_id}-extract.md` (date = first 10 chars of `fetched_at`, slug = the `slug` field, video_id = 11-char ID).

Write the unwrapped Pass 3 report (the markdown text from the cache `output`) to:

```
~/youtube-reports/{date}-{slug}-{video_id}-extract.md
```

Always overwrite if it exists. Do not print the full report inline — terminal output is the dashboard in Step 7.

### Step 7 — Show the extract dashboard inline

Print this dashboard directly to the user. Borders are exactly 54 box-drawing characters `━`. Two-space indent on every content line.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📚 Extract  ·  {title_truncated}  ·  {duration_human}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  {N_total} artifacts extracted

  🔗 Links    {N_links}     💻 Code     {N_code}     📖 Books    {N_books}
  🛠  Tools    {N_tools}     👤 People   {N_people}

  Notable
     • {bullet 1, ≤ 70 chars}
     • {bullet 2, ≤ 70 chars}
     • {bullet 3, ≤ 70 chars}

  📄 ~/youtube-reports/{date}-{slug}-{video_id}-extract.md
```

#### Field extraction

- `title_truncated`: first 50 chars of `title` from Step 2 fetch JSON, suffixed with `…` if longer.
- `duration_human`: `M:SS` if `duration_seconds` < 3600, else `H:MM:SS`.
- `N_total`, `N_links`, `N_code`, `N_books`, `N_tools`, `N_people`: counts parsed from the Pass 3 report's `OVERVIEW` block (one line per category with its count).
- `Notable` bullets: the first three bullets from the Pass 3 report's `NOTABLE` section. Truncate each at 70 chars + `…` if longer. If fewer than 3 exist, show what's there. If `Notable` is empty, omit the entire `Notable` block (header and bullets) from the dashboard.
- File path footer: literal `📄 ` + the path written in Step 6.

If `N_total == 0`, render the dashboard with all-zero counts and the literal line `  No named artifacts found in this video.` in place of the `Notable` block. The user gets a clear "nothing to extract" signal.

## Cache protocol

Identical to `youtube-verdict`'s cache protocol. See `skills/youtube-verdict/SKILL.md` → "Cache protocol — exact contract" for the full spec (file layout, wrapper schema, hashing recipe, hit decision, invalidation events).

**Always compute hashes via `scripts/cache.py`** — `python3 scripts/cache.py hash-file <prompt-path>` for `prompt_hash`, and `python3 scripts/cache.py hash-json` (reading canonical-inputs JSON from stdin) for `inputs_hash`. Inline shell or `python3 -c` snippets drift across host agents and produce spurious cache misses.

Skill-specific cache files:

| Filename | Owner | Contents |
|---|---|---|
| `{video_id}.json` | `scripts/fetch.py` | Transcript JSON (shared) |
| `{video_id}-pass1.json` | shared (verdict + tldr + extract) | Pass 1 cache wrapper |
| `{video_id}-extract-pass2.json` | this skill | Pass 2 cache wrapper |
| `{video_id}-extract-pass3.json` | this skill | Pass 3 cache wrapper |

Per-pass canonical inputs:

| Pass | Prompt | Canonical inputs |
|---|---|---|
| 1 | `prompts/extract_structure.md` | `{"transcript": <full fetch.py JSON>}` |
| 2 | `prompts/extract_artifacts.md` | `{"pass1": <Pass 1 output>, "transcript": <full fetch.py JSON>}` |
| 3 | `prompts/generate_extract.md` | `{"metadata": {"title":…, "channel":…, "duration_seconds":…, "view_count":…, "upload_date":…}, "pass1": <Pass 1 output>, "pass2": <Pass 2 output>}` |

## Cross-platform notes

- Steps 3, 4, and 5 use your own LLM and auth. No `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / vendor key required.
- Steps 2 and 4 are the only subprocess calls. If the host can't shell out, importing `scripts.fetch` / `scripts.segments` / `scripts.cache` as Python modules is equivalent.
- Cache reads and writes use ordinary file tool use.
- If `python3 scripts/fetch.py` fails with `ModuleNotFoundError`, run `python3 scripts/doctor.py` for the exact `pipx install` command to fix the deps prereq.

## Output format reminder

- Pass 1 output: shared with verdict and tldr, see `prompts/extract_structure.md`.
- Pass 2 output: JSON object `{video_id, by_section}` where each section has five arrays (`links`, `code`, `books`, `tools`, `people`), every entry with timestamp + verbatim quote — see `prompts/extract_artifacts.md`.
- Pass 3 output: a single fenced markdown block following the report layout in `prompts/generate_extract.md`. Tone is **factual reference extraction** — no recommendations, no rankings beyond the small `Notable` shortlist, no judgments about whether the resources are good.

## Scope reminder

Audio-only transcripts cannot capture content that is **only shown visually** (e.g., on-screen code that is never spoken). The skill extracts what is audibly mentioned: function names spoken aloud, library imports dictated, command-line invocations read out, URLs spelled or named, book titles announced, tools referenced by name, people introduced. Visual-only artifacts are out of scope.
