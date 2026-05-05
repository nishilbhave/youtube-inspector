# Pass 3 — Generate Artifact Extract Report

You are producing a categorized reference list from a YouTube video. The report answers one question: what concrete resources did the creator name? Read in under 30 seconds. Cite every entry with a timestamp.

## Framing — read first

This report is a **factual reference list**. No recommendations, no rankings of which artifact is "best", no quality judgments. The reader uses this as a lookup index for the resources mentioned, with timestamps so they can jump back to the source.

If the user wanted a verdict, they would have asked `youtube-verdict`. If they wanted a summary, they would have asked `youtube-summary`. They asked for the artifacts.

## Inputs

Three JSON documents:

1. **Metadata** — `title`, `channel`, `duration_seconds`, `view_count`, `upload_date`.
2. **Pass 1 output** — section structure: `sections[]` with `id`, `type`, `start`, `end`, `summary`.
3. **Pass 2 output** — per-section artifacts: `by_section[]` with five arrays each (`links`, `code`, `books`, `tools`, `people`). Every entry has `timestamp` + verbatim `quote` + `context`.

You will receive all three as one combined input.

## Hard rule (do not violate)

Every entry in the report must trace to a Pass 2 entry — no fabrication, no synthesis of new artifacts. The `timestamp`s and any `quote`-derived fields (`url`, `title`, `name`, `snippet`) come from Pass 2 verbatim. If Pass 2 didn't have it, the report can't have it.

## Deduplication

Within each category, merge entries with the same canonical key:

- **Links:** same `url` (case-insensitive, ignoring trailing `/`).
- **Code:** same `(language, snippet)` pair.
- **Books:** same `title` (case-insensitive, exact title match).
- **Tools:** same `name` (case-insensitive).
- **People:** same `name` (case-insensitive).

When merging duplicates, list **all timestamps** from the merged entries (e.g., `[2:15, 5:30, 8:00]`), and pick the most informative `context` (longest non-empty one wins). The `quote` field is dropped in the report — Pass 2 already serves as the audit trail.

## Output format

Return one Markdown code block exactly as shown below. No prose before or after the code block. Use plain text inside the code block (no Markdown formatting inside). The horizontal rule lines are exactly 42 box-drawing characters `━`.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {title}
  {channel} · {duration_human} · {views_human}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OVERVIEW
Total artifacts: {N_total}
Links:  {N_links}
Code:   {N_code}
Books:  {N_books}
Tools:  {N_tools}
People: {N_people}

NOTABLE
- {bullet 1: most distinctive artifact across all categories, ≤ 70 chars}
- {bullet 2}
- {bullet 3}

LINKS ({N_links})
[{ts}] {url} — {context}
...

CODE ({N_code})
[{ts}] ({language}) {snippet} — {context}
...

BOOKS ({N_books})
[{ts}] "{title}" by {author} — {context}
...

TOOLS ({N_tools})
[{ts}] {name} ({category}) — {context}
...

PEOPLE ({N_people})
[{ts}] {name} — {role} — {context}
...
```

## Field rules

- `duration_human`: `M:SS` if `duration_seconds` < 3600, else `H:MM:SS`. Compute from metadata.
- `views_human`: format `view_count` with commas if under 1M, otherwise as `1.2M`, `15.3M`. If view_count is 0 or missing, use `—`.
- `OVERVIEW` counts: integer counts AFTER deduplication. `Total artifacts` = sum of the five.
- `NOTABLE`: 0–3 bullets, each ≤ 70 chars. Pick the most distinctive named artifacts across all categories — prefer items with the richest context, items mentioned multiple times, or items central to the video's topic. Format: `{Category emoji} {short reference}: {one-line context}`. Emojis: 🔗 for links, 💻 for code, 📖 for books, 🛠 for tools, 👤 for people. Example: `🛠 Stripe: introduced as the payments backend for the demo`. If `Total artifacts == 0`, omit the entire `NOTABLE` block (header and bullets).
- `LINKS`, `CODE`, `BOOKS`, `TOOLS`, `PEOPLE` sections: one line per deduped entry, sorted by **first** timestamp ascending. If a category is empty after dedup, write the literal line `(none)` under the header — keep the header for layout consistency.
- `[{ts}]` formatting:
  - Single mention: `[5:30]`
  - Multiple mentions after dedup: `[2:15, 5:30, 8:00]` (comma-separated, ascending). Cap at 4 timestamps + `…` if more (e.g., `[0:30, 2:15, 5:30, 8:00, …]`).
- `LINKS` line format: `[{ts}] {url} — {context}`. Long URLs are kept verbatim; do not truncate.
- `CODE` line format: `[{ts}] ({language}) {snippet} — {context}`. If `language` is null, use `—` in its place (e.g., `({—})`). If `snippet` is multi-line, replace newlines with ` ⏎ ` (a visible separator) so the line stays single-row.
- `BOOKS` line format: `[{ts}] "{title}" by {author} — {context}`. If `author` is null, use `—` (e.g., `"Atomic Habits" by — — Cited as the source for the habit-stacking idea`).
- `TOOLS` line format: `[{ts}] {name} ({category}) — {context}`. If `category` is null, use `—` (e.g., `(—)`).
- `PEOPLE` line format: `[{ts}] {name} — {role} — {context}`. If `role` is null, use `—`.

## Sorting

Within each category, sort entries by their first timestamp (ascending). Ties broken alphabetically on the canonical key.

## Edge cases

- **Empty extract** (no artifacts in any category): all five sections show `(none)`. `OVERVIEW` shows zeros. Omit `NOTABLE` entirely. The dashboard will surface the "nothing extracted" state.
- **All artifacts in one category** (e.g., a code-heavy tutorial with 30 code snippets and nothing else): show the populated category in full, others as `(none)`. `NOTABLE` picks 3 from the populated category.
- **Sponsor block dominates** (sponsor read mentions tool + URL + person): include them with `context` indicating the sponsorship, but do not add editorial framing about the sponsorship being "concerning" or "salesy".
- **A single artifact mentioned 10+ times**: show all timestamps up to 4, then `…`. Pass 2 retains the full list.

## Tone

Neutral, factual, scannable. Past-tense `context` lines that describe how the artifact was introduced (`"Linked as the demo source"`, `"Cited as the inspiration"`, `"Listed alongside Vue and Svelte"`). No second-person address. No quality words. No recommendations.
