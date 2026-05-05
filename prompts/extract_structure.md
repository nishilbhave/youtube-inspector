# Pass 1 — Extract Structure

You are analyzing the structure of a YouTube video transcript. Your job is to segment the transcript into contiguous, non-overlapping sections classified by what kind of content occurs in each.

## Input

A transcript JSON object with these fields:

- `video_id` — 11-character YouTube ID
- `title` — video title
- `channel` — channel name
- `duration_seconds` — total video length, integer seconds
- `transcript` — chronologically ordered array of `{start, duration, text}` segments where `start` and `duration` are seconds (float)

You will receive this as one JSON document. Treat `transcript` as the source of truth for what was said and when.

## Task

Segment the transcript into contiguous sections. Each section has exactly one type:

- **hook** — the opening framing where the creator sets up what the video will deliver. Typically the first 15–120 seconds. Examples: "in this video I'll show you...", a curiosity gap, a bold claim, a teaser. Some videos open directly into content with no separate hook — in that case there is no hook section.
- **content** — the substance the title implies the video delivers. Tutorials, demonstrations, interviews, explanations, news segments, vlog activities. The bulk of most videos.
- **pitch** — selling something rather than delivering content. Course/cohort/coaching offers, newsletter signups, sponsor reads, affiliate-link reads, "click subscribe and like and hit the bell." A mid-roll sponsor read is a pitch even if it interrupts content.
- **outro** — closing remarks, sign-off, generic "thanks for watching." Typically the last 10–30 seconds. If the closing span is mostly a course/product pitch, classify it as `pitch`, not `outro`.

A video can have multiple `content` sections (distinct topics) and multiple `pitch` sections (intro sponsor + mid-roll + end-card pitch).

## Rules

1. **Contiguous and non-overlapping.** The first section starts at `0:00`. The last section ends at the full video duration. No gaps. No overlaps.
2. **Type is one of:** `hook`, `content`, `pitch`, `outro`. No other types.
3. **Timestamp format:** if `duration_seconds` is under 3600, use `M:SS` (e.g. `4:07`). Otherwise use `H:MM:SS` (e.g. `1:24:30`). Use the same format for both `start` and `end`, and for every section in the output.
4. **Default to `content`** if a span doesn't clearly fit hook / pitch / outro.
5. **Granularity:** aim for 3–10 sections in a typical video. Don't over-segment minor topic shifts inside long content. Don't under-segment by lumping a clear pitch into a content block.
6. **Summaries describe what actually happened**, not what the title or hook promised. One sentence each, factual, no marketing language.
7. Section IDs are `S1`, `S2`, `S3`, ... in order.

## Output format

Return one JSON object. No preamble, no commentary, no markdown fences around the JSON, no trailing text. The output must parse as JSON on its own.

Required shape:

```
{
  "video_id": "<11-char id from input>",
  "sections": [
    {
      "id": "S1",
      "type": "hook",
      "start": "0:00",
      "end": "0:42",
      "summary": "Creator promises to show three free tools that earned them $5K last month."
    },
    {
      "id": "S2",
      "type": "content",
      "start": "0:42",
      "end": "8:15",
      "summary": "Walks through three SaaS tools with screen demos and pricing."
    },
    {
      "id": "S3",
      "type": "pitch",
      "start": "8:15",
      "end": "9:30",
      "summary": "Promotes a paid cohort with a discount code and signup link."
    },
    {
      "id": "S4",
      "type": "outro",
      "start": "9:30",
      "end": "9:48",
      "summary": "Asks viewers to like and subscribe; teases next video."
    }
  ]
}
```

## Edge cases

- **Transcript has fewer than 5 segments or `duration_seconds` is missing:** return `{ "video_id": "<id>", "sections": [], "error": "transcript_too_short" }`.
- **Pure pitch video (no real content):** classify the whole body as `pitch`. The verdict pass will use the resulting structure to flag the title/content gap.
- **Sponsor read inside content:** emit it as its own `pitch` section, then continue the `content` section after it.
- **Long content with multiple distinct topics:** split into multiple `content` sections only when the topic shift is unambiguous (e.g. a podcast moves from one guest's expertise to a different topic).
