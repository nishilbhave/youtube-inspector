# Pass 2 — Summarize Sections

You are summarizing a YouTube video transcript section by section. Your job is to produce a short factual summary of each section plus 0–4 key points the section actually delivers. No judgment, no recommendation, no marketing language.

## Input

Two JSON documents:

1. **Pass 1 output** — section structure with `video_id` and `sections[]` (each with `id`, `type`, `start`, `end`, `summary`).
2. **Transcript** — `video_id`, `title`, `duration_seconds`, and `transcript[]` (each segment is `{start, duration, text}`).

You will receive both as one combined input. The transcript may contain segments for **only one section** (per-section processing) — in that case, summarize only the section(s) listed in `pass1.sections[]`. Do not invent sections that aren't in the input.

## Task

For each section from Pass 1, walk the transcript segments whose `start` falls in `[section.start, section.end)` and produce:

- **summary** — 2–4 sentences describing what the section actually covered. Factual, neutral, past-tense narrative. No marketing, no recommendation, no "the creator does a great job of...". Just what happened.
- **key_points** — an array of 0–4 short strings (each ≤ 100 chars) capturing the concrete takeaways a viewer would remember. Empty array for `pitch` and `outro` sections (they have no takeaways). For `hook` sections, key_points may be empty or 1–2 bullets if the hook itself contains substance.
- **type** — copy the `type` from Pass 1 verbatim (`hook`, `content`, `pitch`, or `outro`).

## Section-type guidance

- **content** — the substance. Summary describes what was demonstrated, taught, or argued. Key points list 2–4 specific takeaways (named tools, concrete numbers, key insights, named techniques). Do not exceed 4 bullets — pick the most concrete.
- **hook** — the opening framing. Summary describes what the creator promised would come. Key points usually empty unless the hook delivers a substantive claim itself.
- **pitch** — selling something. Summary names what's being sold (course, sponsor product, newsletter) in one factual line: e.g. "Promotes the creator's $497 cohort with a 50% discount code." Key points: empty array.
- **outro** — closing remarks. Summary is a single line: e.g. "Asks viewers to like and subscribe; teases next video." Key points: empty array.

## Hard rules

1. **No invented content.** Every claim in `summary` and every bullet in `key_points` must be supported by the transcript segments for that section. If you can't point at the words, don't write it.
2. **Past tense, descriptive.** Use "showed", "demonstrated", "explained", "argued", "promoted". Avoid "is excellent", "great example", "should watch", "must-see".
3. **No second-person address.** Do not write "you'll learn", "you can use this". Write "the section walked through X", "the creator demonstrated Y".
4. **No editorializing.** No adverbs like "really", "actually", "obviously". No hedging like "seems to", "appears to". Just description.
5. **Key points are concrete.** Prefer "Listed three React state libraries: Zustand, Jotai, Redux" over "Discussed state management options". Numbers, named entities, specific techniques win.

## Output format

Return one JSON object. No preamble, no markdown fences, no trailing prose. The output must parse as JSON.

Required shape:

```
{
  "video_id": "<11-char id>",
  "by_section": {
    "S1": {
      "type": "hook",
      "summary": "Creator opened by promising three free tools that earned $5K last month, framing the video as a no-cost SaaS toolkit demo.",
      "key_points": []
    },
    "S2": {
      "type": "content",
      "summary": "Walked through three SaaS tools with screen demos and pricing. First tool was a Notion-based CRM at $0/month for solo use. Second was an email scheduler integrating with Gmail at $9/month. Third was a free Stripe-Notion sync built with Zapier.",
      "key_points": [
        "Tool 1: Notion CRM template, free tier",
        "Tool 2: Email scheduler $9/month, Gmail integration",
        "Tool 3: Zapier Stripe-Notion sync, free with usage caps"
      ]
    },
    "S3": {
      "type": "pitch",
      "summary": "Promoted the creator's $497 'No-Code Founder' cohort with a 50% discount code valid for 48 hours.",
      "key_points": []
    },
    "S4": {
      "type": "outro",
      "summary": "Asked viewers to like and subscribe; teased a follow-up on email automations.",
      "key_points": []
    }
  }
}
```

## Field constraints

- Every section ID present in `pass1.sections[]` MUST appear as a key in `by_section`.
- `summary`: a single string, 2–4 sentences. ≤ 500 chars total.
- `key_points`: array of strings. Each ≤ 70 chars. 0 to 4 entries. Punchy and concrete — the dashboard renders the first three of these inline, so they need to fit on a single terminal line.
- `type`: one of `hook`, `content`, `pitch`, `outro` — copied from Pass 1.

## Edge cases

- **Section span has zero transcript segments** (e.g. boundary issue): emit the section ID with a `summary` of `"No transcript content in this span."` and an empty `key_points` array. Do not skip the key.
- **Pure pitch section with no concrete product named** (e.g. generic "support the channel"): summary describes what was solicited in one line. key_points: empty.
- **Content section that's mostly filler** (low-density rambling): summary captures the dominant theme even if vague; key_points may be empty if no concrete takeaway exists. Do not pad — fewer high-quality points beats more low-quality ones.
- **Section transcript contains [Music], (laughter), [Applause]** or similar markers: ignore them; they're not content. If they dominate the section (e.g. an extended musical interlude), the summary may say so.
- **Hook section with substantive content** (e.g. opens with a concrete demo): treat the demo's specifics as key_points; classify as hook in `type` regardless.
