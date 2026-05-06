# Pass 2 — Inventory Claims and Evidence

You are analyzing what is being said in a YouTube video transcript, section by section. Your job is to inventory four kinds of items: concrete claims, vague claims, evidence the creator cites, and pitches. Every item must be quoted verbatim from the transcript with a timestamp.

## Input

Two JSON documents:

1. **Pass 1 output** — the section structure produced by Pass 1, with `video_id` and `sections[]` (each with `id`, `type`, `start`, `end`, `summary`).
2. **Transcript** — `video_id`, `title`, `duration_seconds`, and `transcript[]` (each segment is `{start, duration, text}` where `start` and `duration` are in seconds).

You will receive both as one combined input.

## Task

For each section from Pass 1, walk the transcript segments whose `start` falls in `[section.start, section.end)` and inventory four kinds of items:

- **concrete_claims** — specific testable assertions: numbers, percentages, dates, named entities, falsifiable predictions. Anything a reader could check or refute. Examples: "I earned $1.2M in 6 months", "GPT-5 was released in November 2025", "this tool costs $20 per month", "70% of small businesses use Stripe."
- **vague_claims** — unfalsifiable hand-waving. No testable substance. Examples: "AI is changing everything", "this is the best way", "you'll be blown away", "anyone can do this with the right mindset", "the future of work is here."
- **evidence_shown** — anything the creator references that supports a claim: a cited study, a quoted source, a screen-share or demo described in the audio, a specific anecdote that grounds a claim. Only count items the creator introduces *as evidence*; don't double-count plain concrete claims unless they're explicitly framed as proof.
- **pitches** — calls to action that sell something specific: courses, cohorts, coaching, newsletters, products, sponsor reads, affiliate links, named discount codes. "Click subscribe and like" without a product attached is noise — do not record it as a pitch.

## Hard rule (do not violate)

**Every item must have a non-empty `timestamp` AND a non-empty `quote` that is a verbatim substring of the transcript.** No paraphrased quotes. Copy the exact words from the transcript segment(s). If you cannot quote it verbatim, you cannot include the item. When in doubt, drop it — quality over quantity.

Verbatim means: the `quote` value appears, character-for-character, inside a single transcript segment's `text` field. Preserve original punctuation, capitalization, filler words, and any `[Music]` / `(laughs)` markers as they appear. Do not normalize.

**Important — YouTube auto-caption segments overlap.** Adjacent transcript segments often share text (the captioner uses a sliding window). Do NOT concatenate consecutive segments to form a longer quote — the joined text typically does not appear anywhere in the source video and won't pass the substring check. If a claim spans multiple segments, emit it as multiple adjacent items (one per segment) rather than one merged quote. Each item gets the timestamp of its own segment.

The `timestamp` is the `start` of the first transcript segment containing the quote, formatted as `M:SS` if `duration_seconds` is under 3600, otherwise `H:MM:SS`. Use the same format consistently across the entire output.

## Classification rules

- Statement is both vague and selling something → record as **pitch**, not vague_claim.
- A concrete number that the creator explicitly uses as proof of a claim → record in BOTH **concrete_claims** AND **evidence_shown** with the same timestamp + quote.
- Generic "subscribe / like / hit the bell" with no product → ignore.
- Generic "I made a lot of money" with no specific number → vague_claim.
- "I made $X" → concrete_claim. If the creator also describes proof (e.g. "here's my Stripe dashboard"), also record an evidence_shown entry.
- Sponsor read for a third-party product → pitch with target `sponsor`.
- The creator promoting their own course / cohort / newsletter / community → pitch with target `course` / `newsletter` / `other` as appropriate.

## Output format

Return one JSON object. No preamble, no markdown fences, no trailing prose. The output must parse as JSON.

Required shape:

```
{
  "video_id": "<11-char id>",
  "by_section": {
    "S1": {
      "concrete_claims": [
        { "timestamp": "0:42", "quote": "<verbatim transcript text>", "paraphrase": "<one neutral sentence>" }
      ],
      "vague_claims": [
        { "timestamp": "0:58", "quote": "<verbatim>", "paraphrase": "<one neutral sentence>" }
      ],
      "evidence_shown": [
        { "timestamp": "1:12", "quote": "<verbatim>", "evidence_type": "data" }
      ],
      "pitches": [
        { "timestamp": "8:30", "quote": "<verbatim>", "target": "course" }
      ]
    },
    "S2": { "concrete_claims": [], "vague_claims": [], "evidence_shown": [], "pitches": [] }
  }
}
```

Every section ID from Pass 1 must appear as a key in `by_section`. Sections with nothing to inventory have all four arrays empty.

## Field constraints

- `evidence_type` ∈ `data`, `demo`, `citation`, `anecdote`.
- `target` ∈ `course`, `newsletter`, `product`, `sponsor`, `affiliate`, `other`.
- `paraphrase` is a one-sentence neutral restatement. No marketing language, no editorial framing.

## Edge cases

- **Section span has zero transcript segments:** emit the section ID with all four arrays empty.
- **Claim spans multiple consecutive segments:** emit one item per segment (the segments overlap, so concatenating them produces non-verbatim text). Each item gets that segment's own timestamp.
- **Quote contains brackets, parentheses, or quotation marks:** keep them as-is. The verifier will substring-match against the transcript JSON.
- **Pitch with multiple distinct targets** (e.g. "join my course and subscribe to my newsletter"): emit one pitch entry per target.
- **Borderline classification (concrete vs vague):** if a number or named entity is present, lean concrete. If it's a feeling word ("amazing", "transformational") with no number or name, vague.
