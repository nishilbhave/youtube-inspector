#!/usr/bin/env python3
"""dashboard.py — render the verdict dashboard from a Pass 4 report.

Part of the youtube-verdict skill. No LLM calls. No network calls.

Reads the Pass 4 markdown report from stdin (the unwrapped report — no outer
``` fence) and reads the fetch.py transcript cache for title/channel/duration
/view_count. Prints the formatted dashboard to stdout exactly per SKILL.md
Step 8:

    - 54-char ━ borders
    - Two-space indent on every content line
    - Soft-wrap the EXECUTIVE VERDICT prose at ~60 columns at word boundaries
    - State badge selection from VERDICT (WATCH/SKIP)
    - Channel line includes view_count when known (e.g. `… · 14:44 · 445,168 views`)
    - Substance line shows 4 counts: concrete · vague · evidence · pitches
    - Conditional `📐 Title says / Delivers` pair when title gap is MEDIUM/HIGH
    - Conditional `🖼️ Thumbnail / Delivers` pair when thumb gap is MEDIUM/HIGH
    - Omit the "Best minutes" line when the report says "Nothing — full skip
      recommended."
    - Omit the entire FLAGS block when the report has no FLAGS section
    - First three flag bullets only; quote truncated to 60 chars + …
    - `❓ Ask next` block — up to 3 numbered follow-up questions, soft-wrapped
      with hanging indent
    - File path footer

CLI:
    python3 scripts/dashboard.py <video_id> [--cache-dir DIR] [--report-path PATH]
        Stdin = the Pass 4 report markdown (no outer fence).
        --report-path is optional and only used to fill in the file footer
        path; if omitted the footer line is omitted.

Exit codes:
    0  success
    1  missing transcript cache / missing required fields in report
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path

DEFAULT_CACHE_DIR = Path.home() / "youtube-reports" / ".cache"
BORDER = "━" * 54
INDENT = "  "
WRAP_WIDTH = 60

STATE_BADGE = {"WATCH": "✅", "SKIP": "❌"}
STATE_PROSE_GLYPH = {"WATCH": "✨", "SKIP": "🚫"}

# Pass 4 report headers, in document order. Used both as terminators when
# slicing one section's body and as the lookup keys for `_section_block`.
# `BEST` and `VERDICT` are matched as line prefixes since their headers
# include variable suffixes (`BEST 6 MINUTES (if you must watch)`,
# `VERDICT: SKIP   [3/10]`).
KNOWN_HEADERS = (
    "EXECUTIVE VERDICT",
    "VERDICT:",
    "WHAT IT ACTUALLY DELIVERS",
    "TITLE vs CONTENT",
    "THUMBNAIL vs CONTENT",
    "SUBSTANCE DENSITY",
    "WHO SHOULD WATCH",
    "WHO SHOULD SKIP",
    "BEST",
    "FLAGS",
    "FOLLOW-UP QUESTIONS",
)


def _read_metadata(video_id: str, cache_dir: Path) -> dict:
    path = cache_dir / f"{video_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _human_duration(seconds: int) -> str:
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _matches_header(line: str, header: str) -> bool:
    """A line matches a known header if it equals it or starts with `<header> `
    (or `<header>:` for the `VERDICT:` prefix)."""
    if line == header:
        return True
    if line.startswith(header + " "):
        return True
    if header.endswith(":") and line.startswith(header):
        return True
    return False


def _is_known_header(line: str) -> bool:
    return any(_matches_header(line, h) for h in KNOWN_HEADERS)


def _section_block(report: str, header: str) -> str:
    """Return the body lines under `header` up to the next known header."""
    lines = report.splitlines()
    body: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.rstrip()
        if not in_section:
            if _matches_header(stripped, header):
                in_section = True
            continue
        if _is_known_header(stripped):
            break
        body.append(line)
    return "\n".join(body).strip()


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _select_dashboard_flags(flags: list[dict], limit: int = 2) -> list[dict]:
    """Pick which flags to surface in the truncated dashboard slot.

    The dashboard only fits ``limit`` flag bullets. If the report has any
    ``[thumb]`` flags, surface one of them first so both deception axes
    (transcript + thumbnail) show in the inline summary. Within each
    bucket, preserve the report's original order.
    """
    if not flags:
        return []
    thumb_flags = [f for f in flags if f.get("timestamp") == "thumb"]
    other_flags = [f for f in flags if f.get("timestamp") != "thumb"]
    if thumb_flags and other_flags and limit >= 2:
        return [thumb_flags[0], other_flags[0]] + (
            thumb_flags[1:] + other_flags[1:]
        )[: limit - 2]
    return (thumb_flags + other_flags)[:limit]


def _extract_compare(block: str, promise_label: str = "Title promises") -> dict | None:
    """Extract `<promise_label>:` and `Content delivers:` from a TITLE/THUMBNAIL
    vs CONTENT block. Returns None when either line is missing."""
    if not block:
        return None
    promise_re = rf"^{re.escape(promise_label)}:\s*(.+?)\s*$"
    delivers_re = r"^Content delivers:\s*(.+?)\s*$"
    pm = re.search(promise_re, block, re.MULTILINE)
    dm = re.search(delivers_re, block, re.MULTILINE)
    if not pm or not dm:
        return None
    return {"promises": pm.group(1).strip(), "delivers": dm.group(1).strip()}


def parse_report(report: str) -> dict:
    """Extract fields from the Pass 4 markdown report."""
    fields: dict = {}

    m = re.search(r"^VERDICT:\s+(\w+)\s+\[(\d+)/10\]", report, re.MULTILINE)
    if not m:
        raise ValueError("dashboard.py: report missing VERDICT line")
    fields["verdict"] = m.group(1).upper()
    fields["score"] = int(m.group(2))

    title_block = _section_block(report, "TITLE vs CONTENT")
    title_gap = re.search(r"^Gap:\s+(\w+)", title_block, re.MULTILINE)
    fields["gap"] = title_gap.group(1).upper() if title_gap else "LOW"
    fields["title_compare"] = _extract_compare(title_block)

    thumb_block = _section_block(report, "THUMBNAIL vs CONTENT")
    if thumb_block:
        thumb_gap = re.search(r"^Gap:\s+(\w+)", thumb_block, re.MULTILINE)
        fields["thumb_gap"] = thumb_gap.group(1).upper() if thumb_gap else "LOW"
        fields["thumb_compare"] = _extract_compare(thumb_block, promise_label="Thumbnail promises")
    else:
        fields["thumb_gap"] = None
        fields["thumb_compare"] = None

    fields["executive_verdict"] = _section_block(report, "EXECUTIVE VERDICT")

    best = _section_block(report, "BEST")
    if best.startswith("Nothing"):
        fields["best_minutes"] = None
    else:
        bm = re.match(r"\[([\d:]+)[–-]([\d:]+)\]\s*(.*)", best)
        if bm:
            fields["best_minutes"] = {
                "start": bm.group(1),
                "end": bm.group(2),
                "description": bm.group(3).strip(),
            }
        else:
            fields["best_minutes"] = None

    sd = _section_block(report, "SUBSTANCE DENSITY")
    counts = {}
    for label, key in (
        ("Concrete claims", "concrete"),
        ("Vague claims", "vague"),
        ("Evidence shown", "evidence"),
        ("Pitches/CTAs", "pitches"),
    ):
        cm = re.search(rf"{re.escape(label)}:\s*(\d+)", sd)
        counts[key] = int(cm.group(1)) if cm else 0
    fields["substance"] = counts

    fields["watch_if"] = _section_block(report, "WHO SHOULD WATCH")
    fields["skip_if"] = _section_block(report, "WHO SHOULD SKIP")

    fields["flags"] = []
    flags_block = _section_block(report, "FLAGS")
    if flags_block:
        for line in flags_block.splitlines():
            fm = re.match(r'^-\s*\[([^\]]+)\]\s*"(.*?)"\s*[—-]\s*(.*)$', line.strip())
            if fm:
                fields["flags"].append(
                    {
                        "timestamp": fm.group(1),
                        "quote": fm.group(2),
                        "reason": fm.group(3).strip(),
                    }
                )

    fields["followups"] = []
    fu_block = _section_block(report, "FOLLOW-UP QUESTIONS")
    if fu_block:
        for line in fu_block.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                question = stripped[2:].strip()
                if question:
                    fields["followups"].append(question)
            if len(fields["followups"]) >= 3:
                break

    return fields


def _human_views(view_count: int | None) -> str:
    """Mirror generate_verdict.md's views_human rule: <1M = comma-separated,
    else `1.2M`/`15.3M`. Missing or zero → em-dash."""
    if not view_count:
        return "—"
    if view_count < 1_000_000:
        return f"{view_count:,}"
    return f"{view_count / 1_000_000:.1f}M"


def render(parsed: dict, metadata: dict, report_path: str | None = None) -> str:
    verdict = parsed["verdict"]
    badge = STATE_BADGE.get(verdict, "•")
    glyph = STATE_PROSE_GLYPH.get(verdict, "•")
    score = parsed["score"]
    gap = parsed["gap"]
    thumb_gap = parsed.get("thumb_gap")
    duration = _human_duration(metadata.get("duration_seconds", 0))
    title = metadata.get("title", "(unknown title)")
    channel = metadata.get("channel", "(unknown channel)")
    views = _human_views(metadata.get("view_count"))

    out: list[str] = []
    out.append(BORDER)
    if thumb_gap:
        out.append(
            f"{INDENT}{badge}  {verdict}  ·  {score}/10  ·  "
            f"Title gap {gap}  ·  Thumb gap {thumb_gap}"
        )
    else:
        out.append(f"{INDENT}{badge}  {verdict}  ·  {score}/10  ·  Gap {gap}")
    out.append(BORDER)
    out.append("")

    exec_text = parsed.get("executive_verdict", "").strip()
    if exec_text:
        # First line gets the prose glyph + space; subsequent wrapped lines
        # align under the first character of the prose (3-space hang).
        wrapped = textwrap.wrap(
            exec_text, width=WRAP_WIDTH, break_long_words=False, break_on_hyphens=False
        )
        if wrapped:
            out.append(f"{INDENT}{glyph} {wrapped[0]}")
            for line in wrapped[1:]:
                out.append(f"{INDENT}   {line}")
        out.append("")

    out.append(BORDER)
    out.append("")
    out.append(f"{INDENT}{title}")
    if views == "—":
        out.append(f"{INDENT}{channel}  ·  {duration}")
    else:
        out.append(f"{INDENT}{channel}  ·  {duration}  ·  {views} views")
    out.append("")

    if parsed.get("best_minutes"):
        bm = parsed["best_minutes"]
        out.append(
            f"{INDENT}🎯 Best minutes   [{bm['start']}–{bm['end']}] — {bm['description']}"
        )
    sd = parsed["substance"]
    out.append(
        f"{INDENT}📊 Substance      {sd['concrete']} concrete · {sd['vague']} vague"
        f" · {sd['evidence']} evidence · {sd['pitches']} pitches"
    )

    title_compare = parsed.get("title_compare")
    if title_compare and gap in ("MEDIUM", "HIGH"):
        out.append(f"{INDENT}📐 Title says     {title_compare['promises']}")
        out.append(f"{INDENT}   Delivers      {title_compare['delivers']}")

    thumb_compare = parsed.get("thumb_compare")
    if thumb_compare and thumb_gap in ("MEDIUM", "HIGH"):
        out.append(f"{INDENT}🖼️  Thumbnail     {thumb_compare['promises']}")
        out.append(f"{INDENT}   Delivers      {thumb_compare['delivers']}")

    if parsed.get("watch_if"):
        out.append(f"{INDENT}👥 Watch if       {parsed['watch_if']}")
    if parsed.get("skip_if"):
        out.append(f"{INDENT}👥 Skip if        {parsed['skip_if']}")

    flags = parsed.get("flags") or []
    if flags:
        out.append("")
        out.append(f"{INDENT}🚩 Flags ({len(flags)})")
        for flag in _select_dashboard_flags(flags, limit=3):
            quote = _truncate(flag["quote"], 60)
            out.append(f'{INDENT}   [{flag["timestamp"]}] "{quote}"   — {flag["reason"]}')

    followups = parsed.get("followups") or []
    if followups:
        out.append("")
        out.append(f"{INDENT}❓ Ask next")
        for idx, question in enumerate(followups[:3], start=1):
            wrapped = textwrap.wrap(
                question,
                width=WRAP_WIDTH,
                break_long_words=False,
                break_on_hyphens=False,
            )
            if not wrapped:
                continue
            out.append(f"{INDENT}   {idx}. {wrapped[0]}")
            for cont in wrapped[1:]:
                out.append(f"{INDENT}      {cont}")

    if report_path:
        out.append("")
        out.append(f"{INDENT}📄 {report_path}")

    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the verdict dashboard from a Pass 3 report."
    )
    parser.add_argument("video_id")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--report-path", default=None, help="Path to the saved .md report")
    args = parser.parse_args(argv)

    report = sys.stdin.read()
    if not report.strip():
        sys.stderr.write("dashboard.py: stdin is empty (expected Pass 3 report)\n")
        return 1

    try:
        metadata = _read_metadata(args.video_id, args.cache_dir)
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"dashboard.py: cannot read transcript cache: {e}\n")
        return 1

    try:
        parsed = parse_report(report)
    except ValueError as e:
        sys.stderr.write(str(e) + "\n")
        return 1

    sys.stdout.write(render(parsed, metadata, args.report_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
