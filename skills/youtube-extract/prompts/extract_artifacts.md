# Pass 2 — Extract Named Artifacts

You are extracting named artifacts from a YouTube video transcript, section by section. Your job is to identify every concrete reference the creator makes to a link, a piece of code, a book, a tool/product, or a person — and capture it with a timestamp and a verbatim quote from the transcript.

## Input

Two JSON documents:

1. **Pass 1 output** — section structure with `video_id` and `sections[]` (each with `id`, `type`, `start`, `end`, `summary`).
2. **Transcript** — `video_id`, `title`, `duration_seconds`, and `transcript[]` (each segment is `{start, duration, text}`).

You will receive both as one combined input. The transcript may contain segments for **only one section** (per-section processing) — in that case, extract artifacts only from the section(s) listed in `pass1.sections[]`.

## Categories

For each section, return five arrays. Even if a section has no items in a category, the array MUST appear (empty `[]`).

- **links** — URLs the creator references. The URL may be spoken aloud ("github dot com slash anthropic"), displayed and read out, or directly stated. Reconstruct the URL into canonical form (`https://github.com/anthropic`) but the `quote` must be the verbatim transcript text that contains the spoken/named URL.
- **code** — code or syntax the creator audibly mentions: function names spoken aloud, library imports dictated, command-line invocations read out, named hooks/methods/syntax patterns. **Out of scope:** code that appears only on screen and is never spoken about by name. If the only signal is "and here's the code" with no audible reference to specific syntax, do not record it.
- **books** — named books, papers, articles, blog posts, research publications. Title must be spoken; author optional.
- **tools** — named software, libraries, frameworks, services, platforms, or products. Examples: "React", "Postgres", "Stripe", "VSCode", "Notion", "AWS Lambda". Generic categories ("a database", "a chat app") are NOT tools — only proper names.
- **people** — named individuals: creators, authors, founders, researchers, characters, public figures referenced by name. "My friend" or "the user" without a proper name is NOT a person.

## Hard rule (do not violate)

**Every entry must have a non-empty `timestamp` AND a non-empty `quote` that is a verbatim substring of one transcript segment's `text` field.** No paraphrased quotes. Copy the exact words from the transcript segment(s). If you cannot quote it verbatim, you cannot include the entry. When in doubt, drop it — quality over quantity.

The `timestamp` is the `start` of the first transcript segment containing the quote, formatted as `M:SS` if `duration_seconds` is under 3600, otherwise `H:MM:SS`.

**YouTube auto-caption segments overlap.** Adjacent transcript segments often share text (sliding-window captioner). Do NOT concatenate consecutive segments to form a longer quote — the joined text typically does not appear anywhere in the source video and won't pass the substring check. Each `quote` must come from a single transcript segment.

## Reconstruction rules (only the URL/title/snippet may be reconstructed; the `quote` cannot)

- **Links:** speakers commonly spell URLs aloud — "https colon slash slash example dot com slash foo" → reconstruct as `https://example.com/foo`. The `url` field is the reconstructed canonical form; the `quote` is the verbatim spoken text. Drop the entry if the spoken text is too partial to reconstruct (e.g. just "a GitHub repo" with no path).
- **Books:** if the speaker says "the book Atomic Habits by James Clear", record `title: "Atomic Habits"`, `author: "James Clear"`. If only the title is named, set `author: null`.
- **Code:** the `snippet` is the canonical syntax form. If the speaker says "use the useState hook", `snippet: "useState"`. If they dictate "import numpy as np", `snippet: "import numpy as np"`.
- **Tools:** the `name` is the canonical brand name. If the speaker says "we use React", `name: "React"`. Casing follows the brand's standard (React, npm, GitHub, AWS).
- **People:** the `name` is the proper name as spoken. Preserve original casing.

## Output format

Return one JSON object. No preamble, no markdown fences, no trailing prose. The output must parse as JSON.

Required shape:

```
{
  "video_id": "<11-char id>",
  "by_section": {
    "S1": {
      "links": [
        {
          "timestamp": "0:42",
          "url": "https://github.com/anthropics/claude-code",
          "quote": "<verbatim segment text containing the URL spoken or displayed>",
          "context": "<≤ 80 chars: how the link was introduced>"
        }
      ],
      "code": [
        {
          "timestamp": "1:15",
          "language": "python",
          "snippet": "import numpy as np",
          "quote": "<verbatim segment>",
          "context": "<≤ 80 chars>"
        }
      ],
      "books": [
        {
          "timestamp": "2:30",
          "title": "Atomic Habits",
          "author": "James Clear",
          "quote": "<verbatim segment>",
          "context": "<≤ 80 chars>"
        }
      ],
      "tools": [
        {
          "timestamp": "3:00",
          "name": "React",
          "category": "library",
          "quote": "<verbatim segment>",
          "context": "<≤ 80 chars>"
        }
      ],
      "people": [
        {
          "timestamp": "5:00",
          "name": "Linus Torvalds",
          "role": "creator of Linux",
          "quote": "<verbatim segment>",
          "context": "<≤ 80 chars>"
        }
      ]
    },
    "S2": {"links": [], "code": [], "books": [], "tools": [], "people": []}
  }
}
```

Every section ID present in `pass1.sections[]` MUST appear as a key in `by_section`, with all five arrays present (possibly empty).

## Field constraints

- `language` ∈ `python`, `javascript`, `typescript`, `shell`, `bash`, `html`, `css`, `sql`, `go`, `rust`, `ruby`, `java`, `csharp`, `cpp`, `c`, `swift`, `kotlin`, or `null` if unknown.
- `category` (tools) ∈ `library`, `framework`, `service`, `product`, `platform`, `language`, `editor`, or `null` if unclear.
- `author` (books), `role` (people) — `null` if not stated.
- `context` — single sentence, ≤ 80 chars, neutral and factual. No "the speaker recommends" framing — just describe how the artifact was introduced. Examples: "Linked as the demo source code", "Cited as evidence for the 10x productivity claim", "Listed as a Python alternative to Pandas".

## Classification rules

- A URL pointing to a tool's homepage (e.g., `https://stripe.com`) → record in BOTH `links` (with the URL) AND `tools` (with the name "Stripe"). The two share a timestamp and the same `quote`.
- A book mentioned by title only ("the book that changed my career") with no actual title given → drop. Title is required.
- "I" / "me" / "we" / "our team" — not people. Skip.
- Generic role with no name ("a friend of mine", "this guy") — not a person. Skip.
- Casual mention without commitment ("things like React, Vue, or Svelte" as examples) → record each named tool. Casual is fine; named is the bar.
- Sponsor reads — extract any tool/link/code mentioned, but use a `context` line that notes the sponsorship, e.g., "Mentioned as the video's sponsor".

## Edge cases

- **Section span has zero transcript segments:** emit the section ID with all five arrays empty. Do not skip the key.
- **Same artifact mentioned multiple times in one section:** record each mention with its own timestamp. Pass 3 will dedupe across sections.
- **Quote contains brackets, parentheses, or quotation marks:** keep them as-is. The verifier substring-matches against the transcript JSON.
- **Foreign-language proper names:** preserve original casing and characters; the `quote` must still be verbatim.
- **Hashtags or @mentions** ("@anthropic on Twitter") — extract as a `link` if a platform is named (record the canonical URL, e.g., `https://twitter.com/anthropic`); otherwise drop.
