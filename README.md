# youtube-inspector

Umbrella repo for YouTube analysis agent skills. Each skill answers a different question about a YouTube video, all built on a shared transcript + metadata pipeline.

**Works on Claude Code and Cursor (verified at publish time).** Antigravity, Codex, and any other agent that follows the agent-skills convention work via the same `npx skills add` install path.

## Zero setup

- **No API keys.** No `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `YOUTUBE_API_KEY` — none.
- **No environment variables.** Nothing to export.
- **No config files.** No `.env`, no `~/.config/`.
- **No third-party accounts.** No Google Cloud project, no API console.
- **No additional cost.** The host agent's existing LLM subscription does the work.

The only system requirement is **Python 3.11+** (already on most developer machines).

## Skills

| Skill | Status | What it does |
|---|---|---|
| `yt-verdict` | In development (V1) | Pre-watch decision: WATCH / SKIM / SKIP, with timestamped citations |
| `yt-claims` | Planned | Extract every concrete claim with timestamp + evidence (V2 adds web verification) |
| `yt-tldr` | Planned | Fast summary of what was actually said, no verdict |
| `yt-extract` | Planned | Pull links, code snippets, citations, book titles mentioned |
| `yt-channel` | Planned | Analyze a creator's pattern across N videos |
| `yt-quote` | Planned | Search transcript for verbatim quotes by topic |
| `yt-clip` | Planned | Find the best N-minute segment of a video |

## Build status

See [`PHASES.md`](./PHASES.md) for the runbook (status checkboxes, copy-paste prompts per phase).

## Install

_Install instructions will be added in Phase 4 once `yt-verdict` is published to skills.sh._

Planned form:

```
npx skills add <owner>/youtube-inspector --skill yt-verdict
```

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Architecture

Architectural spec: [`yt-worth-it-plan.md`](./yt-worth-it-plan.md). Read it before working in this repo.
