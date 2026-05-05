# Iteration notes — youtube-verdict prompts

This file logs prompt iteration history during Phase 2: what failed on real transcripts, what was changed, and why. Cross-model spot-check is **out of scope per user direction**; Phase 2 testing was Claude only. Model-agnosticism is upheld by prompt construction (no vendor-specific syntax) — Phase 4 cross-platform validation is where empirical multi-host verification will happen.

## Test corpus

12 real YouTube transcripts fetched via `scripts/fetch.py` and stored under `prompts/samples/transcripts/`:

| ID | Channel | Title | Duration | Category |
|---|---|---|---|---|
| `W6NZfCO5SIk` | Programming with Mosh | JavaScript Course for Beginners | 48m | Tutorial |
| `erEgovG9WBs` | Fireship | 100+ Web Development Things you Should Know | 13m | Tutorial |
| `3qHkcs3kG44` | PowerfulJRE | JRE #1309 — Naval Ravikant | 132m | Podcast >1hr |
| `n0phBDPz8z0` | Travis Nicholson | The Lazy Way I Make Money With AI (2026) | 4m | Finance pitch |
| `ru7fWKD4cyw` | Jono Catliff | Claude Code Websites: How I Earned $1.2M | 77m | Finance pitch (long) |
| `eRS3CmvrOvA` | Nate Herk \| AI Automation | I Tried 100+ Claude Code Skills. These 6 Are The Best | 14m | Tutorial / review |
| `SVTPv4sI_Jc` | Veritasium | Can a quantum sensor detect your heartbeat from 60 km away? | 21m | News / explainer |
| `L9ub_B71U0E` | StarTalk | Astrophysicists Try to Resolve the Wave-Particle Duality | 13m | Podcast / explainer |
| `6TXvaWX5OFk` | FloatHeadPhysics | I finally understood why quantum particles are uncertain! | 21m | Tutorial / explainer |
| `ECOazagKKTo` | Albert Olgaard | I killed every AI notetaker... and built my own (It's free) | 11m | Tutorial / pitch hybrid |
| `4Qw4kyW8Ux8` | Richard Yu | How to Build an App with AI & Start Selling It (No Coding) | 20m | Tutorial / finance pitch |
| `rIuv8mmshsY` | Sahil & Sarra | Code on a Notebook. It will change your life. | 9m | Tutorial / pitch hybrid |

Coverage gap vs Phase 2's original "2 each of 5 types" target: 0 vlog samples (vlog handling unverified). Acknowledged; will revisit in Phase 4 if needed.

## Pass 1 — `extract_structure.md`

### v1 — initial draft

Applied to all 12 transcripts in parallel via Claude subagents. **All 12 outputs were valid JSON, contiguous, and covered the full duration on the first pass.** No iteration required.

Pattern frequency across 12 outputs:
- Most common shape: `hook → content → pitch → content → outro` (5 of 12)
- Tight educational shape `hook → content → outro` (2 of 12)
- Long-form podcast `hook → content×N → outro`, no pitch (1 of 12 — JRE)
- Pitch-dominant `content → pitch → content → pitch` with no hook/outro (1 of 12 — Mosh course preview)
- 3-section monetization video `hook → content → pitch` (1 of 12 — Jono's $1.2M video, end-section is pitch with thanks-for-watching folded in)

Borderline cases the prompt handled correctly without rework:
- Mid-roll sponsor reads correctly emitted as own `pitch` section between `content` blocks (Veritasium → Ground News at 6:19; FloatHeadPhysics → Brilliant at 9:36).
- Closing span dominated by course pitch correctly classified `pitch`, not `outro` (Mosh — final 34s is course pitch with no separate outro).
- "Smash that like button" embedded inside a content joke kept as content, not pitch (Fireship at ~3:34).
- Lead-magnet teaser ("free list of 20 products in description") classified as pitch even when brief (Travis at 2:50).

No prompt edits made. Pass 1 v1 ships.

## Pass 2 — `inventory_claims.md`

### v1 — initial draft

Applied to 3 representative transcripts (Travis Nicholson, Jono Catliff, Fireship) covering: short pitch-heavy, long pitch-heavy, low-pitch educational. Each agent ran the substring audit (every quote must be a verbatim substring of the transcript text).

Results — independent verbatim audit:

| Video | Items | Audit | Counts (concrete / vague / evidence / pitches) |
|---|---|---|---|
| Travis Nicholson (4m, finance pitch) | 46 | 46/46 verbatim, 0 missing | 29 / 11 / 4 / 2 |
| Jono Catliff (77m, monetization) | 66 | 66/66 verbatim, 0 missing | 25 / 15 / 14 / 12 |
| Fireship (13m, explainer) | 49 | 49/49 verbatim, 0 missing | 44 / 3 / 1 / 1 |

Total 161 items, 100% verbatim against the source transcripts. Hard-rule satisfied.

### v1 → v2 — rolling-caption fix

All three agents independently surfaced the same prompt issue: **YouTube auto-caption segments overlap** (sliding-window captioner), so the v1 instruction "join consecutive segments with single space and quote the joined string" produces concatenated text that does not appear anywhere in the source video. Substring audit fails.

Each agent worked around it by emitting one item per single segment. v2 makes that the explicit rule:

- **Verbatim** is now defined as a substring of one segment's `text` only (no joining).
- The "claim spans multiple consecutive segments" edge case now instructs the model to emit one item per segment, each with its own timestamp.

This is a no-op on output quality (data was preserved by the workaround) but stops future runs from chasing a broken concatenation rule. v2 ships; sample outputs already comply.

## Pass 3 — `generate_verdict.md`

### v1 — initial draft

Drafted with explicit `FLAGS` section (departing from the spec sketch in `docs/yt-worth-it-plan.md`) so the hard rule "every flag cites a timestamp + verbatim quote" can be satisfied without inline-citation clutter in WHO SHOULD WATCH / Gap / VERDICT lines. The `FLAGS` header is omitted entirely when verdict is WATCH and Gap is LOW.

Results — applied to the same 3 transcripts that completed Pass 2:

| Video | Verdict | Score | Gap | Flags | Hard-rule audit |
|---|---|---|---|---|---|
| Fireship — 100+ Web Dev Things | WATCH | 9/10 | LOW | 0 (omitted) | n/a (no flags to cite) |
| Travis Nicholson — Lazy Way I Make Money With AI | OKAY | 5/10 | MEDIUM | 6 | 6/6 verbatim against Pass 2 |
| Jono Catliff — Claude Code Websites $1.2M | OKAY | 5/10 | MEDIUM | 6 | 6/6 verbatim against Pass 2 |

Total 12 flags, 100% sourced from Pass 2 with exact `(timestamp, quote)` matches. Hard rule satisfied across the sample set.

Verdict-rubric calibration check:
- Fireship: 44 concrete vs 3 vague (≈14:1), 1 pitch, title delivers exactly what it promises → WATCH 9/10 with the score reduced one point for sparse evidence-shown. Reasonable.
- Travis: title promises a "lazy" workflow with revenue; content delivers revenue claims plus a stack name-check but defers the actual how-to to future videos → OKAY with Gap MEDIUM. The flags cite the deferred-content quotes ("how to create your first digital product, how to drive...") that justify the Gap.
- Jono: title makes a specific outcome claim ($1.2M, 20% conversions); content does deliver substantive landing-page tutoring (14 evidence_shown items including PostHog/Vercel demos), but the headline revenue number is asserted in the hook and only loosely demoed at 1:46. Pitch density (12 pitches across hook + content + closing pitch section) tilts it from WATCH → OKAY.

No iteration needed; Pass 3 v1 ships.

## Iteration tally

- Pass 1: 1 round (no rework). Most common pattern handled correctly: hook → content → pitch → content → outro.
- Pass 2: 1 round + 1 prompt patch (rolling-caption overlap fix; output unchanged because agents discovered and worked around the bug independently).
- Pass 3: 1 round (no rework). FLAGS section enforces the hard rule cleanly.

Most common failure mode discovered: **YouTube auto-caption sliding-window overlap** in Pass 2's "join consecutive segments" rule. Fixed in Pass 2 v2 by switching to single-segment quotes only.

## Cross-model spot-check

**Skipped per user direction** (auto mode, conversation 2026-05-05). Empirical multi-host verification deferred to Phase 4. Prompts are model-agnostic by construction:

- Output formats are JSON or plain Markdown, not vendor-specific (no Anthropic XML conventions, no `cache_control`, no model-name dependencies).
- Instructions use plain natural language without "step by step think carefully" patterns or "thinking" tags.
- No tool-use schemas referenced; the host agent handles tool wiring.

Compliance grep on shipping prompts:
```
grep -RE "(cache_control|<thinking>|claude-sonnet|gpt-4|ANTHROPIC_API_KEY|OPENAI_API_KEY)" prompts/ --include='*.md'
```
Expected to return empty after Phase 2 ships.
