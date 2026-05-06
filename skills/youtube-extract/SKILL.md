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

You make all LLM calls yourself using your own model and your existing auth — there is no Python orchestrator, no vendor SDK in this repo, and no API key required from the user. The only system requirement is **Python 3.11+** with `yt-dlp` and `youtube-transcript-api` installed (Step 1.5 verifies this).

## Workflow — follow these steps in order

### Step 0 — Resolve skill paths

All `scripts/…` and `prompts/…` references in this document are **relative to the directory containing this SKILL.md file** — not the user's working directory. Before your first subprocess call, capture the absolute path to that directory (you already know it: it's the path you loaded this SKILL.md from). Use it as `<SKILL_DIR>` for every script and prompt path below.

In every shell call, pass quoted absolute paths:

```
python3 "<SKILL_DIR>/scripts/fetch.py" "<url>" --cache
```

Do **not** assume the user's working directory is the repo root. Do **not** rely on a `.venv` being activated.

### Step 1 — Extract the video URL or 11-char ID from the user's input

Accepted forms (each is recognized by `scripts/fetch.py`):

- Plain 11-char ID: `n0phBDPz8z0`
- `https://www.youtube.com/watch?v=…` (also `m.youtube.com`, `music.youtube.com`)
- `https://youtu.be/…`
- `https://www.youtube.com/shorts/…`, `/embed/…`, `/live/…`

Reject playlist URLs (`/playlist`) — pass a specific video instead. If no URL is found in the user's message, ask them for one and stop.

**Always pass the URL inside double quotes** when shelling out — zsh and other shells will treat the `?` in `?v=…` as a glob otherwise.

### Step 1.5 — Pre-flight dependency check

Run once, before the first fetch:

```
python3 "<SKILL_DIR>/scripts/doctor.py"
```

If it exits non-zero, surface the printed `pipx install` command verbatim to the user, ask them to run it, and **stop**.

### Step 2 — Fetch transcript and metadata

```
python3 "<SKILL_DIR>/scripts/fetch.py" "<url-or-id>" --cache
```

Interpret the exit code per the standard mapping (0 success, 2 documented rejection, 1 unexpected error). Documented rejection codes (exit 2): `INVALID_URL`, `PLAYLIST`, `LIVE_STREAM`, `TOO_SHORT` (under 180s), `NO_TRANSCRIPT`, `NON_ENGLISH`. Surface rejections verbatim and stop — do not attempt the LLM passes.

### Step 3 — Pass 1: Structure extraction (shared with verdict, summary, claims)

Cache file: `~/youtube-reports/.cache/{video_id}-pass1.json`. Pass 1 is **shared infrastructure** — same prompt, same input, same output across all four skills. Likely a free cache hit if any sister skill ran on this video first.

1. Try a cache read in one subprocess call:
   ```
   echo '{"transcript": <full Step 2 fetch JSON>}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" read 1 <video_id> "<SKILL_DIR>/prompts/extract_structure.md"
   ```
   Exit 0 = HIT (parse stdout as JSON). Exit 1 = MISS.

2. On MISS, read `prompts/extract_structure.md`, apply it as a single LLM pass, parse the model response as JSON, then write the cache wrapper:
   ```
   echo '{"inputs": {"transcript": <full fetch JSON>}, "output": <Pass 1 JSON>}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" write 1 <video_id> "<SKILL_DIR>/prompts/extract_structure.md"
   ```

Tell the user: `Pass 1: cache hit` or `Pass 1: ran (N sections extracted)`.

### Step 4 — Pass 2: Per-section artifact extraction

Cache file: `~/youtube-reports/.cache/{video_id}-extract-pass2.json`.

- Prompt: `prompts/extract_artifacts.md`.
- Canonical inputs: `{"pass1": <full Pass 1 output>, "transcript": <full fetch.py output>}`.

The Pass 1 timestamps (`section.start`, `section.end`) are **authoritative** — pass them straight to `segments.py`. Do not search the transcript to "verify" or "snap" boundaries.

1. Try a cache read:
   ```
   echo '{"pass1": <Pass 1>, "transcript": <fetch.py output>}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" read 2 <video_id> "<SKILL_DIR>/prompts/extract_artifacts.md"
   ```
   Exit 0 = HIT. Exit 1 = MISS.

#### On a cache miss — per-section execution

For each section in Pass 1's `sections[]`, in order:

1. Slice the transcript via subprocess:
   ```
   python3 "<SKILL_DIR>/scripts/segments.py" <video_id> <section.start> <section.end>
   ```
   Stdout is a compact JSON object containing only the segments in `[start, end)`.

2. Apply `prompts/extract_artifacts.md` as a single LLM pass with these inputs:
   ```json
   {
     "pass1": {"video_id": "<id>", "sections": [<just this one section>]},
     "transcript": <stdout from step 1, parsed as JSON>
   }
   ```
   The model returns `{"video_id":"<id>","by_section":{"<this section's id>":{...}}}`.

3. Merge that one `by_section` entry into a running merged dict. Drop the section's transcript slice from your context.

After all sections are processed, write the cache wrapper:
```
echo '{"inputs": {"pass1": <Pass 1>, "transcript": <fetch.py output>}, "output": <merged Pass 2>}' | \
  python3 "<SKILL_DIR>/scripts/cache.py" write 2 <video_id> "<SKILL_DIR>/prompts/extract_artifacts.md"
```

#### Tell the user

`Pass 2: cache hit` or `Pass 2: ran (N artifacts found across L/C/B/T/P)` (where L/C/B/T/P are counts for links/code/books/tools/people).

### Step 5 — Pass 3: Synthesis into the extract report

Cache file: `~/youtube-reports/.cache/{video_id}-extract-pass3.json`.

- Prompt: `prompts/generate_extract.md`.
- Canonical inputs: `{"metadata": {title,channel,duration_seconds,view_count,upload_date}, "pass1": <Pass 1>, "pass2": <Pass 2>}`.
- **Pass 3 does not need the transcript at all.** Pass 2 already contains every artifact's verbatim quote and timestamp. Do not Read `~/youtube-reports/.cache/{video_id}.json` for this pass.

1. Try a cache read:
   ```
   echo '{"metadata": {...}, "pass1": <Pass 1>, "pass2": <Pass 2>}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" read 3 <video_id> "<SKILL_DIR>/prompts/generate_extract.md"
   ```
   Exit 0 = HIT (stdout is the report markdown). Exit 1 = MISS.

2. On MISS, apply `prompts/generate_extract.md` as a single LLM pass. Strip the outer ``` ``` ``` fence; the inner text is the report. Then write the cache wrapper:
   ```
   echo '{"inputs": <same canonical inputs>, "output": "<stripped report markdown>"}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" write 3 <video_id> "<SKILL_DIR>/prompts/generate_extract.md"
   ```

Tell the user: `Pass 3: cache hit` or `Pass 3: ran`.

### Step 6 — Write the final report

Filename: `{date}-{slug}-{video_id}-extract.md` (date = first 10 chars of `fetched_at`, slug = `slug` field, video_id = 11-char ID).

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

Identical to `youtube-verdict`'s cache protocol. See `skills/youtube-verdict/SKILL.md` → "Cache protocol — exact contract" for the full spec.

**Always use `cache.py read` and `cache.py write`** (Steps 3–5) — they handle wrapper construction, hashing, hit detection, and atomic writes. Inline shell or `python3 -c` snippets drift across host agents and produce spurious cache misses.

Skill-specific cache files:

| Filename | Owner | Contents |
|---|---|---|
| `{video_id}.json` | `scripts/fetch.py` | Transcript JSON (shared) |
| `{video_id}-pass1.json` | shared (verdict + summary + extract + claims) | Pass 1 cache wrapper |
| `{video_id}-extract-pass2.json` | this skill | Pass 2 cache wrapper |
| `{video_id}-extract-pass3.json` | this skill | Pass 3 cache wrapper |

Per-pass canonical inputs:

| Pass | Prompt | Canonical inputs |
|---|---|---|
| 1 | `prompts/extract_structure.md` | `{"transcript": <full fetch.py JSON>}` |
| 2 | `prompts/extract_artifacts.md` | `{"pass1": <Pass 1 output>, "transcript": <full fetch.py JSON>}` |
| 3 | `prompts/generate_extract.md` | `{"metadata": {title,channel,duration_seconds,view_count,upload_date}, "pass1": <Pass 1>, "pass2": <Pass 2>}` |

## Cross-platform notes

- Steps 3, 4, and 5 use your own LLM and auth. No `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / vendor key required.
- Subprocess calls: `doctor.py` (Step 1.5), `fetch.py` (Step 2), `cache.py read` / `cache.py write` (Steps 3–5), `segments.py` (Step 4 inside per-section loop). If your host can't shell out, importing each module from `<SKILL_DIR>/scripts/` is equivalent.
- All cache wrapper construction goes through `cache.py write` so per-host JSON quirks cannot produce a spurious miss.
- If `python3 "<SKILL_DIR>/scripts/fetch.py"` ever fails with `ModuleNotFoundError`, run `python3 "<SKILL_DIR>/scripts/doctor.py"` for the exact `pipx install` command.

## Output format reminder

- Pass 1 output: shared with verdict and summary, see `prompts/extract_structure.md`.
- Pass 2 output: JSON object `{video_id, by_section}` where each section has five arrays (`links`, `code`, `books`, `tools`, `people`), every entry with timestamp + verbatim quote — see `prompts/extract_artifacts.md`.
- Pass 3 output: a single fenced markdown block following the report layout in `prompts/generate_extract.md`. Tone is **factual reference extraction** — no recommendations, no rankings beyond the small `Notable` shortlist, no judgments about whether the resources are good.

## Scope reminder

Audio-only transcripts cannot capture content that is **only shown visually** (e.g., on-screen code that is never spoken). The skill extracts what is audibly mentioned: function names spoken aloud, library imports dictated, command-line invocations read out, URLs spelled or named, book titles announced, tools referenced by name, people introduced. Visual-only artifacts are out of scope.
