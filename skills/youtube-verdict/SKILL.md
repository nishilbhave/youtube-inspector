---
name: youtube-verdict
description: |
  Pre-watch decision tool for YouTube videos. Use when the user pastes a
  YouTube URL and asks "is this worth watching", "should I watch this",
  "should I skip this", "watch or skip", "give me a verdict on this video",
  "is this YouTube video any good", or wants a pre-watch summary that ends
  in a recommendation. Returns WATCH / OKAY / SKIP with a 0–10 score, a
  best-minutes range, substance density (concrete vs vague claims, evidence
  shown, pitches), and a who-should-watch / who-should-skip split. Every
  flag cites a verbatim transcript quote with a timestamp — no hallucinated
  criticism. For neutral summaries with no judgment use `youtube-summary`
  instead. Saves the full report to ~/youtube-reports/ and prints a
  one-glance dashboard inline.
---

# youtube-verdict — pre-watch decision tool for YouTube videos

You are the host agent running this skill. The user has asked whether a YouTube video is worth watching, what's actually in it, or for a pre-watch summary. Your job is to produce a structured report at `~/youtube-reports/{date}-{slug}-{video_id}.md`.

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

**Always pass the URL inside double quotes** when shelling out — zsh and other shells will treat the `?` in `?v=…` as a glob otherwise (`no matches found` errors).

### Step 1.5 — Pre-flight dependency check

Run once, before the first fetch:

```
python3 "<SKILL_DIR>/scripts/doctor.py"
```

If it exits non-zero, surface the printed `pip3 install` command verbatim to the user (doctor.py tailors it to the user's Python — adding `--break-system-packages` for PEP 668 environments like Homebrew Python on macOS), ask them to run it, and **stop**. Do not retry the fetch until the user confirms the install succeeded. This converts what would otherwise be a `ModuleNotFoundError: yt_dlp` mid-run into a single guided remediation.

### Step 2 — Fetch transcript and metadata

Run as a subprocess (no LLM call):

```
python3 "<SKILL_DIR>/scripts/fetch.py" "<url-or-id>" --cache
```

The `--cache` flag reads/writes `~/youtube-reports/.cache/{video_id}.json` so a second run on the same video skips the network entirely.

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
fetched_at, slug
```

### Step 3 — Pass 1: Structure extraction

Cache file: `~/youtube-reports/.cache/{video_id}-pass1.json`. The cache wrapper schema is documented under "Cache protocol" below.

1. Try a cache read in one subprocess call (canonical inputs piped in via stdin):
   ```
   echo '{"transcript": <full Step 2 fetch JSON>}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" read 1 <video_id> "<SKILL_DIR>/prompts/extract_structure.md"
   ```
   Exit 0 means **cache HIT** — stdout is the Pass 1 output JSON; parse it and continue to Step 4. Exit 1 means **MISS** (stderr says why: `not-found` / `prompt-mismatch` / `inputs-mismatch` / `corrupt` / `field-missing`).

2. On a MISS, read `prompts/extract_structure.md`, apply it to the transcript JSON as a single LLM pass following the prompt's instructions exactly, parse the model response as JSON (it must be a single JSON object — no preamble, no markdown fences). Then write the cache wrapper:
   ```
   echo '{"inputs": {"transcript": <full Step 2 fetch JSON>}, "output": <Pass 1 JSON>}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" write 1 <video_id> "<SKILL_DIR>/prompts/extract_structure.md"
   ```

Tell the user one short line: `Pass 1: cache hit` or `Pass 1: ran (N sections extracted)`.

### Step 4 — Pass 2: Claim & evidence inventory

Cache file: `~/youtube-reports/.cache/{video_id}-pass2.json`.

1. Try a cache read:
   ```
   echo '{"pass1": <Pass 1 output>, "transcript": <full fetch.py output>}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" read 2 <video_id> "<SKILL_DIR>/prompts/inventory_claims.md"
   ```
   Exit 0 = HIT (parse the output JSON, continue to "Tell the user"). Exit 1 = MISS, run per-section processing.

#### On a cache miss — per-section execution

Loading the entire transcript into context burns ~17 K tokens for a 15-min video and ~120 K for a 75-min one. Process the transcript section by section instead.

The Pass 1 timestamps (`section.start`, `section.end`) are **authoritative** — pass them straight to `segments.py`. Do **not** search the transcript to "verify" or "snap" boundaries; that's not part of the protocol and wastes tool calls.

For each section in Pass 1's `sections[]`, in order:

1. Slice the transcript via subprocess (no LLM call):
   ```
   python3 "<SKILL_DIR>/scripts/segments.py" <video_id> <section.start> <section.end>
   ```
   Stdout is a compact JSON object of the form:
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

3. Merge that one `by_section` entry into a running merged dict. Drop the section's transcript slice from your context before moving to the next section.

After all sections are processed, the final Pass 2 output is `{"video_id": "<id>", "by_section": <merged dict>}`. Write the cache wrapper:
```
echo '{"inputs": {"pass1": <Pass 1>, "transcript": <fetch.py output>}, "output": <merged Pass 2>}' | \
  python3 "<SKILL_DIR>/scripts/cache.py" write 2 <video_id> "<SKILL_DIR>/prompts/inventory_claims.md"
```

Optionally verify every quote substring-matches the transcript (the prompt enforces this, but verification catches model drift):
```
echo '<merged Pass 2 output>' | \
  python3 "<SKILL_DIR>/scripts/cache.py" verify-quotes <video_id>
```
Exit 0 = clean. Exit 1 = at least one quote isn't verbatim; stderr lists each mismatch. Re-run the offending section if any.

#### Tell the user

`Pass 2: cache hit` or `Pass 2: ran (N items inventoried)` (where N is the total of all `concrete_claims` / `vague_claims` / `evidence_shown` / `pitches` across sections).

### Step 5 — Pass 3: Synthesis

Cache file: `~/youtube-reports/.cache/{video_id}-pass3.json`.

1. Try a cache read with the canonical Pass 3 inputs:
   ```
   echo '{"metadata": {title,channel,duration_seconds,view_count,upload_date}, "pass1": <Pass 1>, "pass2": <Pass 2>}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" read 3 <video_id> "<SKILL_DIR>/prompts/generate_verdict.md"
   ```
   Exit 0 = HIT (stdout is the report markdown). Exit 1 = MISS.

2. On MISS, read `prompts/generate_verdict.md`, apply it to the canonical inputs as a single LLM pass. **Pass 3 does not need the transcript at all** — every flag cites a quote already substring-matched by Pass 2. Do not Read `~/youtube-reports/.cache/{video_id}.json` for this pass. The model's response is markdown wrapped in a single fenced code block; strip the outer ` ``` ` fence — the inner text is the report. Then write the cache wrapper with the stripped report as a JSON string:
   ```
   echo '{"inputs": <same canonical inputs>, "output": "<stripped report markdown as JSON string>"}' | \
     python3 "<SKILL_DIR>/scripts/cache.py" write 3 <video_id> "<SKILL_DIR>/prompts/generate_verdict.md"
   ```

Tell the user: `Pass 3: cache hit` or `Pass 3: ran` plus the verdict line (e.g. `→ OKAY 5/10`).

### Step 6 — Write the final report

Build the filename from the Step 2 fetch JSON:

- `{date}` — first 10 characters of `fetched_at` (UTC, `YYYY-MM-DD`).
- `{slug}` — the `slug` field from the fetch JSON (already deterministic, lowercase, ≤ 60 chars; falls back to `untitled` for non-Latin titles).
- `{video_id}` — the 11-char ID.

Write the unwrapped Pass 3 report (the markdown text from the cache `output`) to:

```
~/youtube-reports/{date}-{slug}-{video_id}.md
```

Always overwrite if it exists. Re-running on the same video produces an identical filename — `--cache` keeps `fetched_at` stable, so no orphan files accumulate. Do **not** print the full report inline — it's a structured document meant for the file. Terminal output is the dashboard in Step 7.

### Step 7 — Show the verdict dashboard inline

Render the dashboard via the bundled renderer — do not format it by hand. The renderer handles all the layout details (54-char ━ borders, soft-wrap at 60 cols, badge selection, omit-Best-minutes / omit-Flags logic, 40-char quote truncation):

```
echo '<the unwrapped Pass 3 report markdown>' | \
  python3 "<SKILL_DIR>/scripts/dashboard.py" <video_id> --report-path "<the path you wrote in Step 6>"
```

The renderer reads `~/youtube-reports/.cache/{video_id}.json` for title/channel/duration. Print its stdout directly to the user.

The renderer enforces the dashboard format below. State badges and prose glyphs come from the verdict:

| `VERDICT` | `STATE_BADGE` | `STATE_PROSE_GLYPH` |
| --------- | ------------- | ------------------- |
| WATCH     | ✅            | ✨                  |
| OKAY      | ⚠️             | ⏩                  |
| SKIP      | ❌            | 🚫                  |

The user gets the verdict at a glance and opens the file only for the full breakdown.

## Cache protocol — exact contract

This is the contract any host agent implements via `scripts/cache.py`. Hashing is deterministic across hosts (locked by `tests/test_cache.py`).

### File layout

All cache files live under `~/youtube-reports/.cache/`:

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

Use `cache.py read` and `cache.py write` (Steps 3–5) — they handle wrapper construction, hashing, hit detection, and atomic writes for you.

### How the `cache.py` subcommands map to the protocol

| Step | Command | What it does |
|---|---|---|
| Hit check | `cache.py read <pass> <video_id> <prompt-path>` (stdin = canonical inputs JSON) | Reads cache file, recomputes both hashes, exits 0 + stdout = `output` on hit; exit 1 + stderr reason on miss (`not-found` / `prompt-mismatch` / `inputs-mismatch` / `corrupt` / `field-missing`) |
| Write | `cache.py write <pass> <video_id> <prompt-path>` (stdin = `{inputs, output}`) | Computes both hashes, writes wrapper file with `produced_at` set to current UTC |
| Pass 2 quote audit | `cache.py verify-quotes <video_id>` (stdin = Pass 2 output) | Substring-checks every `quote` field across `concrete_claims` / `vague_claims` / `evidence_shown` / `pitches`; exit 0 if clean, exit 1 + stderr listing mismatches |

The locked canonicalization (so any host agent producing the same logical input gets the same digest):

- Keys sorted lexicographically at every nesting level.
- Compact separators (no spaces): `","` and `":"`.
- `ensure_ascii=False` (UTF-8 output, non-ASCII characters preserved as-is).
- No trailing newline before hashing.

Equivalent Python: `hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()`.

If your host cannot shell out, importing the module is equivalent: `from scripts import cache; cache.read_cache(...)` / `cache.write_cache(...)`.

Per-pass canonical inputs:

| Pass | Canonical inputs |
|---|---|
| 1 | `{"transcript": <full fetch.py JSON>}` |
| 2 | `{"pass1": <Pass 1 output>, "transcript": <full fetch.py JSON>}` |
| 3 | `{"metadata": {"title":…, "channel":…, "duration_seconds":…, "view_count":…, "upload_date":…}, "pass1": <Pass 1 output>, "pass2": <Pass 2 output>}` |

The whole transcript object (including `fetched_at`) goes into Passes 1 and 2's input. In practice `--cache` keeps `fetched_at` stable across re-runs so this doesn't cause spurious misses.

### Invalidation events (all handled automatically by `cache.py read`)

- Prompt file edited → `prompt_hash` mismatch → MISS.
- Transcript re-fetched with different segments → `inputs_hash` mismatch on Pass 1 → cascades through Pass 2 and Pass 3.
- File deleted by hand → MISS.
- File corrupted (bad JSON, missing fields) → MISS.
- Pass 1 output changes (re-run) → Pass 2's `inputs_hash` mismatches → cascades to Pass 3.

You **never** overwrite `~/youtube-reports/{date}-{slug}-{video_id}.md` from cache. Step 6 only writes that file when Step 5 produces a Pass 3 result (whether from cache or fresh). The user's final report is always derived from a Pass 3 cache hit or a fresh Pass 3 run — never stale.

## Cross-platform notes

- Steps 3, 4, and 5 use your own LLM and auth. No `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / vendor key is required from the user.
- The subprocess calls are: `doctor.py` (Step 1.5), `fetch.py` (Step 2), `cache.py read` / `cache.py write` (Steps 3–5), `segments.py` (Step 4 inside the per-section loop), `cache.py verify-quotes` (optional, Step 4), `dashboard.py` (Step 7). If your host can't shell out, importing each module from `<SKILL_DIR>/scripts/` is equivalent.
- All cache wrapper construction goes through `cache.py write` so per-host JSON quirks (key ordering, whitespace, escaping) cannot produce a spurious miss on the next run.
- If `python3 "<SKILL_DIR>/scripts/fetch.py"` ever fails with `ModuleNotFoundError`, run `python3 "<SKILL_DIR>/scripts/doctor.py"` for the exact `pip3 install` command for the user's Python (Step 1.5 should have caught this already).

## Output format reminder

- Pass 1 output: JSON object `{video_id, sections[]}` — see `prompts/extract_structure.md`.
- Pass 2 output: JSON object `{video_id, by_section}` — see `prompts/inventory_claims.md`.
- Pass 3 output: a single fenced markdown block following the report layout in `prompts/generate_verdict.md`. Every flag MUST cite a transcript timestamp + verbatim quote drawn from Pass 2 — this is the skill's hard rule. If the model can't quote it, it can't flag it.
