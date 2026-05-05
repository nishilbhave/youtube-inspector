---
name: youtube-claims
description: |
  Claim inventory tool for YouTube videos. Use when the user pastes a
  YouTube URL and asks "what claims does this video make", "list every
  claim", "show me the evidence", "fact-check material", "extract the
  testable claims", "what does this person assert", or wants a research-
  grade timeline of every concrete and vague claim, every piece of
  evidence cited, and every pitch made — with timestamps and verbatim
  quotes for each. V1 is inventory-only; it does not verify the claims
  against external sources. Useful for researchers, journalists,
  skeptics, and anyone preparing to evaluate a creator's substance.
  Saves the full inventory to ~/youtube-reports/ and prints a one-glance
  dashboard inline.
---

# youtube-claims — claim inventory tool for YouTube videos

You are the host agent running this skill. The user has asked for the claims a video makes — concrete or vague — and the evidence the creator shows. Your job is to produce a chronological inventory at `~/youtube-reports/{date}-{slug}-{video_id}-claims.md`.

This skill is **inventory only, not verification**. It captures what was said with timestamps and verbatim quotes. It does not check whether claims are true. The report header states this explicitly so readers don't mistake a high concrete-claim count for "the video is accurate".

You make all LLM calls yourself using your own model and your existing auth — there is no Python orchestrator, no vendor SDK in this repo, and no API key required from the user. The only system requirement is **Python 3.11+** for the bundled `scripts/fetch.py`, `scripts/segments.py`, and `scripts/cache.py`.

The skill assumes the working directory is the root of the `youtube-inspector` repo.

## Workflow — follow these steps in order

### Step 1 — Extract the video URL or 11-char ID from the user's input

Same as the other skills. Plain ID, `youtube.com/watch?v=…`, `youtu.be/…`, `/shorts/…`, `/embed/…`, `/live/…` are all accepted. Reject playlist URLs. If no URL is found, ask the user and stop.

### Step 2 — Fetch transcript and metadata

```
python3 scripts/fetch.py <url-or-id> --cache
```

Standard exit-code interpretation: 0 success, 2 documented rejection (`INVALID_URL`, `PLAYLIST`, `LIVE_STREAM`, `TOO_SHORT`, `NO_TRANSCRIPT`, `NON_ENGLISH`), 1 unexpected error. Surface rejections verbatim and stop.

### Step 3 — Pass 1: Structure extraction (shared with verdict, tldr, extract)

Cache file: `~/youtube-reports/.cache/{video_id}-pass1.json`. Pass 1 is **shared infrastructure** — same prompt, same input, same output across all four skills. Likely a free cache hit.

1. `prompt_hash`: `python3 scripts/cache.py hash-file prompts/extract_structure.md`.
2. `inputs_hash`: pipe `{"transcript": <full fetch.py output>}` to `python3 scripts/cache.py hash-json`.
3. Read the cache file. If both hashes match → HIT, load the `output` field. Else MISS, apply `prompts/extract_structure.md` and write the wrapper.

Tell the user: `Pass 1: cache hit` or `Pass 1: ran (N sections extracted)`.

### Step 4 — Pass 2: Claim & evidence inventory (shared with youtube-verdict)

Cache file: `~/youtube-reports/.cache/{video_id}-pass2.json`. **Shared with `youtube-verdict`** — same prompt (`prompts/inventory_claims.md`), same canonical inputs, same cache file. Running verdict first then claims (or vice versa) yields a free Pass 2 cache hit.

1. `prompt_hash`: `python3 scripts/cache.py hash-file prompts/inventory_claims.md`.
2. `inputs_hash`: pipe `{"pass1": <Pass 1 output>, "transcript": <full fetch.py output>}` to `python3 scripts/cache.py hash-json`.
3. Read the cache file. If both hashes match → HIT, load `output`. Else MISS, run per-section processing.

#### On a cache miss — per-section execution

For each section in Pass 1's `sections[]`, in order:

1. `python3 scripts/segments.py <video_id> <section.start> <section.end>` — capture stdout JSON.
2. Apply `prompts/inventory_claims.md` as a single LLM pass with input `{"pass1": {"video_id":"<id>","sections":[<just this one section>]}, "transcript": <stdout>}`. The model returns `{"video_id":"<id>","by_section":{"<this section's id>":{...}}}`.
3. Merge the one `by_section` entry into a running merged dict. Drop the section's transcript slice from your context.

After all sections processed: final Pass 2 output is `{"video_id":"<id>","by_section":<merged dict>}`. Write the wrapper using `inputs_hash` over the FULL canonical inputs.

Tell the user: `Pass 2: cache hit` or `Pass 2: ran (N items inventoried)` (where N is the total of `concrete_claims`/`vague_claims`/`evidence_shown`/`pitches` across sections).

### Step 5 — Pass 3: Synthesis into the claim inventory report

Cache file: `~/youtube-reports/.cache/{video_id}-claims-pass3.json`.

- Prompt: `prompts/generate_claims.md`.
- Canonical inputs: `{"metadata": <metadata subset>, "pass1": <Pass 1 output>, "pass2": <Pass 2 output>}`.
- Metadata subset: `{title, channel, duration_seconds, view_count, upload_date}` from the Step 2 fetch JSON.
- **Pass 3 does not need the transcript at all** — every quote in the report comes from Pass 2 (which already substring-matches the transcript).
- Model response: markdown wrapped in a single fenced code block. Strip the outer ` ``` ` fence; the remainder is the report text.
- The `output` field of the cache wrapper is the **stripped** report **as a JSON string**.

Tell the user: `Pass 3: cache hit` or `Pass 3: ran`.

### Step 6 — Write the final report

Filename: `{date}-{slug}-{video_id}-claims.md` (date = first 10 chars of `fetched_at`, slug = `slug` field, video_id = 11-char ID).

```
~/youtube-reports/{date}-{slug}-{video_id}-claims.md
```

Always overwrite. Don't print the full report inline — the dashboard in Step 7 is the terminal output.

### Step 7 — Show the inventory dashboard inline

Print this dashboard. Borders are exactly 54 box-drawing characters `━`. Two-space indent on content lines.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔬 Claims  ·  {title_truncated}  ·  {duration_human}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Inventory only — no external verification performed.

  📊 Substance density
     Concrete claims  {N_concrete}
     Vague claims     {N_vague}
     Evidence shown   {N_evidence}
     Pitches/CTAs     {N_pitches}

  🔍 Top concrete claims
     [{ts1}] {paraphrase 1, ≤ 70 chars}
     [{ts2}] {paraphrase 2, ≤ 70 chars}
     [{ts3}] {paraphrase 3, ≤ 70 chars}

  📄 ~/youtube-reports/{date}-{slug}-{video_id}-claims.md
```

#### Field extraction

- `title_truncated`: first 50 chars of `title`, suffixed with `…` if longer.
- `duration_human`: `M:SS` if `duration_seconds` < 3600, else `H:MM:SS`.
- Counts: parse from the Pass 3 report's `OVERVIEW` block (one line per category).
- `Top concrete claims`: the first three `[ts] paraphrase` entries from the Pass 3 report's `CONCRETE CLAIMS` section. Truncate each `paraphrase` at 70 chars + `…` if longer. If fewer than 3 concrete claims exist, show what's there. If `N_concrete == 0`, replace the entire `🔍 Top concrete claims` block with `  No concrete claims inventoried.`
- File path footer: literal `📄 ` + the path written in Step 6.

The user gets a one-glance picture of substance density and the top concrete claims, then opens the file for the full chronological inventory across all four categories.

## Cache protocol

Identical to `youtube-verdict`'s. See `skills/youtube-verdict/SKILL.md` → "Cache protocol — exact contract" for the full spec.

**Always compute hashes via `scripts/cache.py`** — `python3 scripts/cache.py hash-file <prompt-path>` for `prompt_hash`, and `python3 scripts/cache.py hash-json` (canonical inputs JSON on stdin) for `inputs_hash`.

Skill-specific cache files:

| Filename | Owner | Contents |
|---|---|---|
| `{video_id}.json` | `scripts/fetch.py` | Transcript JSON (shared) |
| `{video_id}-pass1.json` | shared (verdict + tldr + extract + claims) | Pass 1 cache wrapper |
| `{video_id}-pass2.json` | shared (verdict + claims) | Pass 2 cache wrapper |
| `{video_id}-claims-pass3.json` | this skill | Pass 3 cache wrapper |

Per-pass canonical inputs:

| Pass | Prompt | Canonical inputs |
|---|---|---|
| 1 | `prompts/extract_structure.md` | `{"transcript": <full fetch.py JSON>}` |
| 2 | `prompts/inventory_claims.md` | `{"pass1": <Pass 1 output>, "transcript": <full fetch.py JSON>}` |
| 3 | `prompts/generate_claims.md` | `{"metadata": {"title":…, "channel":…, "duration_seconds":…, "view_count":…, "upload_date":…}, "pass1": <Pass 1 output>, "pass2": <Pass 2 output>}` |

## Cross-platform notes

- All LLM calls use the host's own model and auth. No `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / vendor key required.
- Steps 2 and 4 are the only subprocess calls. Importing `scripts.fetch` / `scripts.segments` / `scripts.cache` as Python modules is equivalent if shelling out is not available.
- Cache reads and writes use ordinary file tool use.

## Output format reminder

- Pass 1 output: shared with verdict/tldr/extract, see `prompts/extract_structure.md`.
- Pass 2 output: shared with verdict, see `prompts/inventory_claims.md` (4 arrays per section: `concrete_claims`, `vague_claims`, `evidence_shown`, `pitches`, every entry timestamp + verbatim quote).
- Pass 3 output: a single fenced markdown block following the chronological-inventory layout in `prompts/generate_claims.md`. **Inventory only** — no truth verdicts, no fact-checks, no recommendations.

## Scope reminder

V1 lists what was claimed, not whether claims are true. Web verification, citation lookup, and fact-checking against external sources are V2 work — not in this skill's scope. Readers evaluating accuracy should treat this report as a starting point: each entry is the verbatim quote and timestamp where they can verify their own conclusion.
