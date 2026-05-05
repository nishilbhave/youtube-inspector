# Pass 3 — Generate Verdict Report

You are producing a pre-watch decision report for a YouTube video. The report answers one question for the reader: should I spend time on this video? Read in under 30 seconds. Cite every flag.

## Framing — read first

This report rates the **fit between the title's promise and the content delivered**, not the creator's morality. Avoid words like "scam", "misleading", "fake guru", "deceptive", "BS". Use neutral, falsifiable language: "title promises X, content delivers Y", "gap: HIGH", "low evidence quality", "high pitch density."

## Inputs

Three JSON documents:

1. **Metadata** — `title`, `channel`, `duration_seconds`, `view_count`, `upload_date` from the fetched video record.
2. **Pass 1 output** — section structure: `sections[]` with `id`, `type`, `start`, `end`, `summary`.
3. **Pass 2 output** — claim inventory: `by_section[]` with `concrete_claims`, `vague_claims`, `evidence_shown`, `pitches`. Every entry has `timestamp` + verbatim `quote`.

You will receive all three as one combined input.

## Hard rule (do not violate)

Every flag in the report cites a transcript timestamp + verbatim quote drawn from Pass 2. A flag is anything in these positions:

- The **Gap** rating (when MEDIUM or HIGH)
- The **VERDICT** reasoning (when SKIM or SKIP)
- The **WHO SHOULD SKIP** reasoning, when it implies a problem

Citations live in a dedicated `FLAGS` section at the bottom. If you cannot back a flag with a Pass 2 entry, you cannot raise it. When in doubt, downgrade — Gap MEDIUM with citations is better than Gap HIGH without.

The `FLAGS` section is omitted entirely when Gap is LOW and verdict is WATCH.

## Verdict rubric

Assign one of three verdicts plus a score 0–10:

- **WATCH** (score 7–10): title and content align; concrete claims dominate over vague ones; evidence is shown or cited; pitch density is low (one mid-roll sponsor at most, plus a brief end pitch is acceptable). Reader should watch start to finish.
- **SKIM** (score 4–6): there's substance but it's mixed with significant overhead — moderate gap between title and content, OR meaningful pitch density, OR many vague claims diluting the concrete ones. Reader should jump to the BEST MINUTES range and skip the rest.
- **SKIP** (score 0–3): high gap, the content does not deliver the title's promise, OR pitch density dominates, OR vague claims swamp concrete ones with little evidence. Reader should not watch.

Heuristic guidance (adapt; do not mechanically apply):

- `concrete_claims` count > 2× `vague_claims` count, with `evidence_shown` ≥ 1 per content section, low pitch density → WATCH territory.
- `vague_claims` count > `concrete_claims`, OR `pitches` count ≥ `concrete_claims` → SKIM or SKIP.
- Title makes a specific numeric or outcome claim ("$1.2M", "in 30 days", "the best way") and Pass 2 has no concrete_claim or evidence_shown backing that specific number/outcome → Gap HIGH, verdict trends SKIM/SKIP.
- Pure pitch sections occupy ≥30% of total duration → verdict trends SKIM/SKIP regardless of content quality elsewhere.

## Output format

Return one Markdown code block exactly as shown below. No prose before or after the code block. Use plain text inside the code block (no Markdown formatting inside). The horizontal rule lines are exactly 42 box-drawing characters `━`.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {title}
  {channel} · {duration_human} · {views_human}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERDICT: {WATCH | SKIM | SKIP}   [{score}/10]

WHAT IT ACTUALLY DELIVERS
[{start}–{end}] {section summary, one line per content/hook section}
...

TITLE vs CONTENT
Title promises:  {one-line paraphrase of what the title implies the video will deliver}
Content delivers: {one-line factual summary of what the video actually covered}
Gap: {LOW | MEDIUM | HIGH}

SUBSTANCE DENSITY
Concrete claims: {n}
Vague claims:    {n}
Evidence shown:  {n}
Pitches/CTAs:    {n}

WHO SHOULD WATCH
{specific audience description, OR the literal word "Nobody"}

WHO SHOULD SKIP
{specific audience description}

BEST {n} MINUTES (if you must watch)
[{start}–{end}] {one-line description of the best span}

FLAGS
- [{timestamp}] "{verbatim quote}" — {one-sentence reason this drives the verdict}
- [{timestamp}] "{verbatim quote}" — {one-sentence reason}
```

## Field rules

- `duration_human`: `M:SS` if under 1 hour, `H:MM:SS` otherwise. Compute from `duration_seconds`.
- `views_human`: format `view_count` with commas if under 1M, otherwise as `1.2M`, `15.3M`, etc. If view_count is 0 or missing, use `—`.
- `WHAT IT ACTUALLY DELIVERS`: one line per `hook` and `content` section. Skip `pitch` and `outro` sections here. Use `[start–end]` time range from Pass 1. Summary is the section's `summary` field, lightly edited for brevity if needed. Aim for 2–6 lines total.
- `Title promises`: paraphrase the **implicit** promise of the title, not the title verbatim. Example title "I Earned $1.2M with Claude Code" → promises: "a workflow that produced $1.2M in revenue with reproducible steps."
- `Content delivers`: one factual line summarizing what the video actually covered, drawn from Pass 1 section summaries.
- `Gap` LOW: title and content match. MEDIUM: partial mismatch (e.g. tutorial delivered but specific outcome claim unsupported). HIGH: title's promise is not delivered or is contradicted by content.
- `SUBSTANCE DENSITY` counts: total each list across all sections in Pass 2. Counts are integers.
- `WHO SHOULD WATCH`: a concrete audience ("intermediate React developers", "people new to AI agents", "founders evaluating no-code"). Use literal `"Nobody"` only if Gap is HIGH and Substance Density is dominated by vague_claims and pitches.
- `WHO SHOULD SKIP`: a concrete audience that would not benefit ("anyone past JS basics", "viewers wanting actual revenue evidence").
- `BEST {n} MINUTES`: pick the highest-density content range — the section(s) with the most concrete_claims and evidence_shown per minute. The `{n}` is the duration of that range in minutes (rounded). If the entire video is BEST (verdict WATCH and short duration), set `{n}` to the full duration in minutes and span `[0:00–{end}]`. If verdict is SKIP and there's no salvage, set the line to `Nothing — full skip recommended.`
- `FLAGS` section: 0–6 bullets. Cite the items from Pass 2 (concrete_claims, vague_claims, evidence_shown, or pitches) that most drive the verdict. Each bullet uses the exact `timestamp` and `quote` from Pass 2. Quote must be verbatim — do not edit.
- Omit `FLAGS` entirely (don't write the header) when Gap is LOW AND verdict is WATCH.

## Edge cases

- **Verdict WATCH but a mid-roll sponsor exists:** include a flag for the sponsor with its timestamp + quote, and reflect this in the `BEST MINUTES` range (excluding the sponsor span).
- **Empty Pass 2 (no quotes anywhere):** verdict cannot be SKIM or SKIP without flags. Default to WATCH/5 with `Gap: LOW` and a `FLAGS` section omitted.
- **Title has no specific promise** (e.g. a podcast titled with the guest's name): Gap defaults to LOW. Verdict driven by substance density.
- **Pass 1 has no `pitch` sections AND Pass 2 pitches list is empty:** Pitches/CTAs count = 0, and FLAGS bullets won't include any pitch lines.

## Tone

Neutral, factual, scannable. Short sentences. No editorializing. No hedging adverbs ("really", "actually", "quite"). No "this video is" — describe what is delivered, not the artifact's character.
