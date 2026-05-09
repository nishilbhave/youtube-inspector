# Pass 3 — Thumbnail Promise Extraction

You are analyzing the **thumbnail image** for a YouTube video. Output a structured inventory of what the thumbnail visually promises the viewer. The verdict pass downstream uses your output to flag thumbnail-vs-content gaps — situations where the thumbnail makes a specific claim that the video's transcript never substantiates.

This is the deception axis: text overlays like "$10K/DAY", visual tropes like cash stacks and supercars, fake-looking screenshots, before/after splits, and shocked-face reaction shots are some of the most common ways scammy creators get clicks. Extract them faithfully so the verdict can call them out.

## Vision capability gate — read this first

If you cannot interpret images on this host (no vision capability, or the image at `thumbnail_path` is not present / not readable), return **only** this JSON object and nothing else:

```json
{"vision_available": false}
```

Do not invent thumbnail content. The verdict pass detects this sentinel and silently omits the thumbnail block from the report.

If you **can** interpret the image, return the full schema in the next section.

## Inputs

You receive a single combined JSON document with these fields:

- `video_id` — 11-char YouTube ID (echo this verbatim in your output).
- `title` — the video's title text. Use it as context for what the thumbnail is reinforcing or contradicting, but **do not** copy title text into `text_overlays` unless it actually appears on the thumbnail.
- `channel` — the uploader's channel name.
- `thumbnail_path` — absolute filesystem path to the JPG. Read it as an image with your vision capability.

## Output schema — return one JSON object, no preamble, no markdown fence

```json
{
  "video_id": "<echoed verbatim>",
  "vision_available": true,
  "text_overlays": ["VERBATIM TEXT FROM THUMBNAIL", "..."],
  "visual_elements": [
    {
      "element": "short factual description of one visible element",
      "implied_promise": "what a viewer would expect this element to mean about the video"
    }
  ],
  "deception_signals": [
    {"signal": "<one of the catalog entries below, or a short novel description>", "severity": "HIGH" | "MEDIUM" | "LOW"}
  ],
  "thumbnail_summary": "One factual sentence describing what the thumbnail shows.",
  "implicit_promise": "One sentence: the specific outcome or content the thumbnail leads a viewer to expect from the video."
}
```

Field-by-field rules:

- `text_overlays` — list every distinct piece of text **drawn on top of** the thumbnail image, **verbatim**, in the order it would naturally be read (top → bottom, left → right). Preserve exact casing (`$10K/DAY` not `$10k/day`). Preserve currency symbols, punctuation, and emoji. Do not include the YouTube duration badge or YouTube watermark — only the creator's overlays. If there is no text on the thumbnail, return an empty list.
- `visual_elements` — 1–6 entries describing the most prominent non-text elements: people (faces, expressions, gestures), props (cash, cars, electronics, charts, screenshots-of-screens), settings (mansion, beach, office), composition tropes (before/after split, big number with arrow, red circle highlight). Each `element` is a short factual phrase — what is *literally visible*. Each `implied_promise` is what a viewer would reasonably take that element to mean about the video's content.
- `deception_signals` — 0–6 entries. Each signal is a pattern from the catalog below (or a novel description if it doesn't fit a catalog entry). Severity calibration:
  - **HIGH** — the signal alone justifies a SKIP-leaning thumbnail flag. Specific numeric outcomes without qualifier; fake-looking screenshots; before/after with no methodology in the title.
  - **MEDIUM** — adds to the case but not decisive on its own. Lifestyle imagery; shock-face reactions; urgency tags; over-saturated colors.
  - **LOW** — present but mild. A single arrow, a generic dollar sign, mildly outsized typography.
  - If the thumbnail has none of the catalog patterns and looks like a normal informational thumbnail, return an empty list. Do **not** invent signals to fill the field.
- `thumbnail_summary` — one factual sentence describing what is on the thumbnail. Plain prose. No marketing language, no scare quotes, no judgment.
- `implicit_promise` — one sentence stating the **specific** outcome or content the thumbnail leads a viewer to expect from the video. Be concrete enough that the verdict pass can compare it against the transcript's `concrete_claims` and `evidence_shown`. Examples:
  - Good: "A method that generates $10K/day in passive income through digital products."
  - Good: "A workflow that turns a $5K investment into $50K within 30 days using the shown crypto bot."
  - Bad: "Making money online." (too vague — verdict pass cannot compare against anything specific)
  - Bad: "Watching this video." (meaningless)

## Catalog of common scam-thumbnail patterns

Use these as `signal` strings when they apply (verbatim, so the verdict pass can pattern-match):

- `extreme dollar number with no qualifier` — e.g. "$10K/DAY", "$1M IN 30 DAYS", "$500/HR" presented as a headline with no time/effort/risk caveat.
- `before/after split with no methodology shown` — left side shows a "bad" state (poor person, broken phone, empty wallet), right side shows a "good" state (cash, success), with the title not promising a process.
- `fake-screenshot of earnings dashboard` — a stylized screenshot that looks like Stripe / PayPal / brokerage with a large number, but the proportions, fonts, or UI chrome don't match the real product.
- `lifestyle imagery (luxury car/mansion/yacht) without methodology` — Lambo, Ferrari, beachfront mansion, private jet placed alongside a financial promise.
- `shocked-face reaction shot` — open-mouthed surprise face, hand on head, oversized eyes — the standard YouTube clickbait expression.
- `urgency tag or scarcity tag` — "BEFORE IT'S GONE", "LAST CHANCE", "ENDS TODAY", "ONLY 3 LEFT".
- `arrow pointing at oversized number` — large arrow (often red or yellow) pointing at a number with no source.
- `red circle around face/object suggesting hidden truth` — the "they don't want you to see this" composition.
- `text claim contradicted by visible state of speaker` — e.g. text says "I made $1M" but the visible person is filming in a basic bedroom with no other supporting evidence.
- `pure brand or logo collage with no creator face/voice` — common in dropshipping/MLM thumbnails — implies endorsement without one.

If the thumbnail uses a pattern not in this catalog, write a short novel description (≤ 60 chars) and pick a calibrated severity.

## Quote discipline — important for the downstream verdict pass

Every entry you produce must be **groundable** in the actual image. The verdict pass quotes your `text_overlays` and `visual_elements[].element` strings *verbatim* in flag bullets, with the slot `[thumb]` instead of a transcript timestamp. Do not invent text that is not on the thumbnail. Do not describe elements that are not visible. If a thumbnail is bland and contains nothing scammy, it is fine — and important — to return an empty `deception_signals` list. The skill's whole value depends on this honesty.

## Edge cases

- **Thumbnail is a static head-and-shoulders shot of the speaker, no overlays:** `text_overlays: []`, one `visual_elements` entry for the speaker, `deception_signals: []`. `implicit_promise` should reflect the title, not invent thumbnail content.
- **Thumbnail is mostly text (a Twitter-style screenshot, a quote card):** all visible text goes in `text_overlays` verbatim. `visual_elements` describes the card composition. `deception_signals` only if the text claim itself is a hyperbolic outcome promise.
- **Thumbnail is an in-game / in-app screenshot:** treat it as a `visual_elements` entry; `deception_signals` only if the screenshot is staged or composited to imply something the video doesn't deliver.
- **Multiple text overlays in the same thumbnail:** each goes in `text_overlays` as its own entry, in reading order. Don't concatenate them.

## Self-check before returning

1. JSON is valid. Single object. No markdown fence around it. No prose before or after.
2. `vision_available` is `true` if you produced the rest of the schema; `false` only when you genuinely cannot read the image.
3. `text_overlays` are verbatim — no paraphrasing, no case changes, no spelling fixes.
4. Every `deception_signals[].signal` corresponds to something a downstream reader could verify by looking at the same thumbnail.
5. `implicit_promise` is concrete enough that "transcript substantiates this" is a falsifiable claim.

If any check fails, fix and re-emit.
