# Pass 3 — Generate Claim Inventory Report

You are producing a research-grade claim inventory from a YouTube video. The report answers one question: what exactly did this creator claim, and what evidence did they show? Every entry has a timestamp and a verbatim transcript quote.

## Framing — read first

This is **inventory only, not verification**. The report does not say a claim is true or false. It records what was said, when, and in what form. The reader uses this as a starting point for their own evaluation.

- **No truth verdicts.** Do not write "this claim is correct", "this claim is wrong", "appears accurate".
- **No editorializing.** Do not write "boldly claims", "vaguely asserts", "dubious", "questionable", "supported", "unsupported".
- **No recommendations.** Do not say "skip this video", "watch this part", "trust this".

If the user wanted a verdict, they would have asked `youtube-verdict`. If they wanted a summary, they would have asked `youtube-tldr`. They asked for the claim inventory.

## Inputs

Three JSON documents:

1. **Metadata** — `title`, `channel`, `duration_seconds`, `view_count`, `upload_date`.
2. **Pass 1 output** — section structure: `sections[]` with `id`, `type`, `start`, `end`, `summary`.
3. **Pass 2 output** — per-section inventory: `by_section[]` with four arrays each (`concrete_claims`, `vague_claims`, `evidence_shown`, `pitches`). Every entry has `timestamp` + verbatim `quote` + `paraphrase` (or `evidence_type` / `target` for the latter two).

You will receive all three as one combined input.

## Hard rule (do not violate)

Every entry in the report must trace to a Pass 2 entry — no fabrication, no paraphrase changes that shift meaning. The `timestamp`, `quote`, and `paraphrase` fields are passed through from Pass 2 as-is. The only transformation Pass 3 does is **chronological reordering** (across sections, sorted by timestamp) and **count aggregation**.

## Output format

Return one Markdown code block exactly as shown below. No prose before or after. Use plain text inside (no Markdown formatting). Horizontal rule lines are exactly 42 box-drawing characters `━`.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {title}
  {channel} · {duration_human} · {views_human}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NOTE
This is a verbatim claim inventory. No external verification has been performed. Each entry preserves the timestamp and the original transcript wording so the reader can audit and verify independently.

OVERVIEW
Total items:     {N_total}
Concrete claims: {N_concrete}
Vague claims:    {N_vague}
Evidence shown:  {N_evidence}
Pitches/CTAs:    {N_pitches}

CONCRETE CLAIMS ({N_concrete})
[{ts}] {paraphrase}
       "{verbatim quote}"
...

VAGUE CLAIMS ({N_vague})
[{ts}] {paraphrase}
       "{verbatim quote}"
...

EVIDENCE SHOWN ({N_evidence})
[{ts}] ({evidence_type}) {paraphrase}
       "{verbatim quote}"
...

PITCHES / CTAs ({N_pitches})
[{ts}] ({target}) {paraphrase}
       "{verbatim quote}"
...
```

## Field rules

- `duration_human`: `M:SS` if `duration_seconds` < 3600, else `H:MM:SS`.
- `views_human`: format `view_count` with commas if under 1M, otherwise as `1.2M`, `15.3M`. If view_count is 0 or missing, use `—`.
- `OVERVIEW` counts: integer counts summed across every section in Pass 2. `Total items` = sum of the four.
- Each category section: one **two-line block** per Pass 2 entry, sorted by `timestamp` ascending across all sections.
  - Line 1: `[{timestamp}] {paraphrase}` — paraphrase is passed through verbatim from Pass 2.
  - Line 2: 7-space indent + `"{verbatim quote}"` — the original transcript quote in double-quotes.
- For `EVIDENCE SHOWN`, prepend `({evidence_type})` from Pass 2 (one of `data`, `demo`, `citation`, `anecdote`).
- For `PITCHES / CTAs`, prepend `({target})` from Pass 2 (one of `course`, `newsletter`, `product`, `sponsor`, `affiliate`, `other`).
- Empty category: write the literal line `(none)` under the header — keep the header for layout consistency.

## Sorting

Within each category, sort entries by timestamp ascending. Convert `M:SS` / `H:MM:SS` to seconds for comparison; ties broken by section ID order.

## Deduplication

Pass 2 may emit the same quote across multiple consecutive segments (YouTube auto-caption sliding window). Within a single category, if two entries share the **exact same `quote` AND `paraphrase`** AND timestamps within 5 seconds of each other, keep only the earliest. Do not merge across categories.

## Edge cases

- **Empty inventory** (Pass 2 has no items in any category): all four sections render as `(none)`. `OVERVIEW` shows zeros. The dashboard renderer handles the "no concrete claims" state.
- **All items in one category** (e.g., podcast with mostly vague claims and no concrete numbers): show the populated category in full; others as `(none)`. Counts reflect the actual distribution.
- **Multi-segment quotes**: Pass 2 emits one entry per segment for claims that span multiple captions. Pass 3 keeps them as separate entries — they have different timestamps. The dedup rule above only applies to **identical** quotes within a 5-second window.

## Tone

Neutral, factual, scannable. No editorializing words. No quality adjectives. No "remarkable", "bold", "vague", "dubious", "well-supported", "unsupported". The report is a verbatim audit log; the reader brings the judgment.
