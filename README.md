<div align="center">

<img src="assets/banner.svg" alt="youtube-inspector — four skills, zero setup, vendor-neutral" width="900">

# youtube-inspector

[![install](https://img.shields.io/badge/install-one--command-8b5cf6?style=flat-square)](#install)
[![license](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](#license)
[![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square)](#install)
[![agents](https://img.shields.io/badge/agents-Claude%20Code%20%7C%20Cursor%20%7C%20Antigravity%20%7C%20Codex-7c3aed?style=flat-square)](#how-it-works)

</div>

Four [agent skills](https://skills.sh) that turn any YouTube URL into a watch-decision, a neutral summary, an artifact list, or a claim inventory — vendor-neutral, no API keys, with verbatim transcript citations on every flag and claim.

- **Pre-watch verdict** — WATCH or SKIP with a 0–10 score (5 and 6 disallowed), title-vs-content and thumbnail-vs-content gap analysis, best-minutes range, who-should-watch / who-should-skip split, and three follow-up questions.
- **Section-by-section TL;DR** — 3–4 sentence summary, per-section breakdown, skippable-segment markers for pitches and outros.
- **Categorized artifact extraction** — links, code, books, tools, and people referenced in the video, each with timestamp and verbatim mention.
- **Research-grade claim inventory** — concrete claims, vague claims, evidence shown, and pitches, every entry timestamped and quoted verbatim.
- **No hallucinated criticism** — every flag, claim, and reference cites a verbatim transcript quote with timestamp; if the model can't quote it, it can't write it.
- **Shared transcript cache** — all four skills hit the same `~/youtube-reports/.cache/{video_id}.json`. Run any combination on the same video; the network call happens once.

## Sample Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ❌  SKIP  ·  3/10  ·  Title gap HIGH  ·  Thumb gap HIGH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🚫 The $5,219 case study at the center of this video stays
     redacted: the actual store, the influencer who drove seed
     traffic, the Facebook ad account, and the ad spend are all
     withheld on camera. What remains is a generic
     Facebook-pixel-to-lookalike-audience tutorial wrapped in
     affiliate plugs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  I Just Used Claude AI To Make $5,000 In 24 Hours Online
  Money Talk With Leon  ·  22:44  ·  168,099 views

  🎯 Best minutes   [17:00–22:00] — Concrete walkthrough of building add-to-cart custom audiences and a 5% lookalike for the parenting niche.
  📊 Substance      15 concrete · 3 vague · 2 evidence · 5 pitches
  📐 Title says     A verifiable 24-hour case study showing how Claude AI generated $5,000.
     Delivers      A redacted narrative around the dollar figure plus a generic Facebook pixel + lookalike audience walkthrough.
  🖼️  Thumbnail     A Claude AI + PDF product method that produces $5,000 in 24 hours.
     Delivers      The headline figure is repeated verbally; no unredacted Stripe, Shopify, or ad-account screenshot ties it to a real store.
  👥 Watch if       Marketers who want a fast verbal recap of the Facebook custom-audience to lookalike-audience workflow and don't need verified case-study numbers.
  👥 Skip if        Anyone hoping to verify the $5,219 figure, see an unredacted Shopify or ad account, or learn what it actually cost to generate the result.

  🚩 Flags (6)
     [thumb] "$5,000 in 24 Hours"   — Headline dollar number on the thumbnail; no unredacted dashboard ties it to a real store anywhere in the video.
     [5:14] "$5,219 in 24 hours"   — Central revenue claim repeats throughout, with the actual store and screenshot deliberately hidden.
     [8:18] "I had a 3.67 conversion rate"   — On-screen conversion-rate proof is on a proxy account the creator admits is not the real store.

  ❓ Ask next
     1. What was the gross ad spend behind the $5,219 day, and what
        was the resulting net margin after Shopify, payment, and
        Facebook fees?
     2. Which redacted product, store, and influencer drove the seed
        traffic — without those, the case study can't be replicated.
     3. Does the 3.67% conversion rate on the proxy store hold on
        the real store, or only on a low-volume staging account?

  📄 ~/youtube-reports/2026-05-09-i-just-used-claude-ai-...-cqY6_zyLt1Q.md
```

Saved to `~/youtube-reports/<date>-<slug>-<video_id>.md`. Same shape across all four skills (verdict adds `WATCH/SKIP`; tldr/extract/claims swap in their own dashboards).

## Install

```bash
# 1. Install Python deps once (skills.sh skills don't bundle pip deps)

# macOS Homebrew Python — or any externally-managed Python (PEP 668):
pip3 install --user --break-system-packages yt-dlp youtube-transcript-api

# pyenv, python.org, or Linux without PEP 668 lock:
pip3 install --user yt-dlp youtube-transcript-api

# 2. Install all four skills
npx skills add nishilbhave/youtube-inspector
```

That's it. No API keys, no env vars, no config files — the host agent's existing model subscription does the LLM work, and the only system requirement is **Python 3.11+**.

**Why `--break-system-packages` on macOS?** Homebrew's Python ships PEP 668's `EXTERNALLY-MANAGED` marker, which makes `pip` refuse to install anything by default. The flag bypasses that single upfront check; the `--user` flag — which the PEP 668 error message itself recommends pairing with it — then writes the install to `~/Library/Python/3.X/site-packages/`, leaving Homebrew's own Python directories untouched. Worst case: `rm -rf ~/Library/Python/3.X` and you're back to factory state.

**Don't use `pipx` for these deps**, even if you already have it. `pipx install yt-dlp` puts the package in a private venv that exposes the `yt-dlp` CLI on your `$PATH`, but it does NOT make `import yt_dlp` work from your default `python3` — and the skill's `scripts/fetch.py` imports both packages directly from Python. Use `pip --user` so the deps land on your default `python3`'s import path.

Each skill is **self-contained**. `npx skills add` ships `SKILL.md` plus `scripts/` (fetch, segments, cache, doctor — and `dashboard.py` for verdict) and `prompts/` to the host's skill directory (e.g. `~/.claude/skills/youtube-verdict/`). No working-directory assumptions: SKILL.md uses `<SKILL_DIR>`-prefixed paths so the skill works wherever your shell happens to be when you invoke it.

Manage:

```bash
npx skills update nishilbhave/youtube-inspector
npx skills remove nishilbhave/youtube-inspector
```

Each skill runs `scripts/doctor.py` automatically before its first fetch (Step 1.5 of every SKILL.md). If your Python environment is missing `yt-dlp` or `youtube-transcript-api`, the skill stops with the exact `pip3 install` command for your environment (PEP 668-aware) — no mid-run `ModuleNotFoundError` surprises, and no need to remember whether you need `--break-system-packages`.

## Skills

- **`youtube-verdict`** — *"is this worth watching?"* → WATCH or SKIP, 0–10 score (5/6 disallowed), title-vs-content and thumbnail-vs-content gap, best-minutes range, substance density, who-should-watch / who-should-skip split, three follow-up questions, every flag a timestamped verbatim quote.
- **`youtube-summary`** — *"summarize this video"* / *"tl;dr"* → 3–4 sentence TL;DR, section-by-section breakdown, top takeaways, skippable-section markers. Factual and neutral — never recommends watching or skipping.
- **`youtube-extract`** — *"what tools / books / links did they mention?"* → categorized list of links, code, books, tools, and people, each with timestamp and verbatim mention.
- **`youtube-claims`** — *"list every claim this video makes"* → research-grade chronological inventory of concrete claims, vague claims, evidence shown, and pitches, with timestamps and verbatim quotes. V1 is inventory-only; no external verification.

## How It Works

Three-pass pipeline shared across all four skills:

- **Pass 1 — structure (shared by all 4)**: `python3 scripts/fetch.py <url> --cache` pulls metadata + transcript and writes `~/youtube-reports/.cache/{video_id}.json`. The host agent then runs `prompts/extract_structure.md` once over the transcript to segment it into hook / content / pitch / outro with timestamps. Output is cached at `{video_id}-pass1.json` and reused by every skill that runs on the same video.
- **Pass 2 — per-skill inventory (partial sharing)**: `python3 scripts/segments.py <video_id> <start> <end>` slices the cached transcript per Pass 1 section, so the host agent's LLM only sees one section at a time. `youtube-verdict` and `youtube-claims` share `prompts/inventory_claims.md` and the same `{video_id}-pass2.json` cache; `youtube-summary` uses `prompts/summarize_sections.md`; `youtube-extract` uses `prompts/extract_artifacts.md`.
- **Pass 3 — per-skill synthesis**: each skill's own prompt (`prompts/generate_verdict.md`, `prompts/generate_summary.md`, `prompts/generate_extract.md`, `prompts/generate_claims.md`) takes Pass 1 + Pass 2 + a small metadata subset and produces the final report — the transcript itself is never reloaded for Pass 3.

**Cache protocol** is locked by `scripts/cache.py`: SHA-256 of the prompt file's raw bytes (`prompt_hash`) plus SHA-256 of the canonical-JSON form of the inputs (`inputs_hash`). Same logical input on any host produces the same digest; edits to a prompt or transcript automatically invalidate downstream passes. Unit tests in `tests/test_cache.py` lock the canonicalization (`sort_keys=True`, compact separators, UTF-8).

**Vendor-neutral by construction**: no Anthropic, OpenAI, or other vendor SDK is imported anywhere in the repo. The host agent's existing LLM and auth do every model call. Skills work the same on Claude Code, Cursor, Antigravity, Codex, and any other agent that follows the [skills.sh](https://skills.sh) convention.

## Roadmap

- **`youtube-batch`** — apply any of the above to N videos at once. Planned for V2; pending cross-platform validation of V1.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Pre-flight: confirm yt-dlp + youtube-transcript-api importable
python3 scripts/doctor.py

# Test suite (fetch, segments, cache, slug, doctor)
pytest -q
```

Architecture spec: [`docs/yt-worth-it-plan.md`](./docs/yt-worth-it-plan.md). Publish prep tracker: [`docs/PUBLISH.md`](./docs/PUBLISH.md). Phase tracker (Phases 0–3 complete; Phase 4 superseded by `PUBLISH.md`): [`docs/PHASES.md`](./docs/PHASES.md).

## License

MIT.
