"""Unit tests for scripts/dashboard.py — render the verdict dashboard."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import dashboard  # noqa: E402


REPO_ROOT = Path(__file__).parent.parent


# A self-contained Pass 3 report fixture with all sections present.
SAMPLE_REPORT = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Sample Video Title
  Sample Channel · 14:44 · 445,168
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE VERDICT
The eight "billionaire rules" frame collapses into three named anecdotes plus a stack of unsourced figures and aphorisms.
Half the runtime restates self-help truisms; one mid-roll DM pitch interrupts the only stretch worth keeping.

VERDICT: SKIP   [4/10]

WHAT IT ACTUALLY DELIVERS
[0:00–0:37] Hook
[0:37–4:01] Buckets 1–2

TITLE vs CONTENT
Title promises:  X
Content delivers: Y
Gap: MEDIUM

SUBSTANCE DENSITY
Concrete claims: 25
Vague claims:    12
Evidence shown:  10
Pitches/CTAs:    4

WHO SHOULD WATCH
Founders new to billionaire content who want a fast sampler.

WHO SHOULD SKIP
Anyone already familiar with Naval, Musk, or Bezos talking points.

BEST 6 MINUTES
[1:38–7:30] Rules 1–4 with the four most concrete anecdotes.

FLAGS
- [7:01] "in business make. Elon Musk only owns $19.8% of Tesla and that business makes" — Stat is mis-stated.
- [3:24] "laws of physics, it should work. See, NASA paid roughly 380 million per launch" — Round-number cost claim, no citation.
"""


WATCH_REPORT_NO_FLAGS = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Solid Tutorial
  TutChan · 8:30 · 12,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE VERDICT
Watch start to finish. Concrete examples throughout.

VERDICT: WATCH   [9/10]

WHAT IT ACTUALLY DELIVERS
[0:00–8:30] Full tutorial.

TITLE vs CONTENT
Title promises:  A tutorial.
Content delivers: A tutorial.
Gap: LOW

SUBSTANCE DENSITY
Concrete claims: 30
Vague claims:    2
Evidence shown:  8
Pitches/CTAs:    0

WHO SHOULD WATCH
Beginners.

WHO SHOULD SKIP
Experts.

BEST 8 MINUTES (if you must watch)
[0:00–8:30] The whole thing.
"""


THUMBNAIL_REPORT = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Make $10K/Day With This One Trick
  ScammyTube · 12:00 · 1,000,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE VERDICT
The thumbnail headlines a $10K/day outcome that the transcript never substantiates.
The video is mostly a pitch for a paid course with no concrete numbers shown.

VERDICT: SKIP   [2/10]

WHAT IT ACTUALLY DELIVERS
[0:00–1:00] Hook
[1:00–10:00] Pitch loop

TITLE vs CONTENT
Title promises:  $10K/day from one trick.
Content delivers: A pitch for a course.
Gap: HIGH

THUMBNAIL vs CONTENT
Thumbnail promises:  $10K/day in passive income from a method shown in this video.
Content delivers:    A pitch for a paid course; no method shown.
Gap: HIGH

SUBSTANCE DENSITY
Concrete claims: 0
Vague claims:    18
Evidence shown:  0
Pitches/CTAs:    9

WHO SHOULD WATCH
Nobody.

WHO SHOULD SKIP
Anyone valuing their time.

BEST 0 MINUTES
Nothing — full skip recommended.

FLAGS
- [thumb] "$10K/DAY" — Headline number on thumbnail is unsupported by any concrete claim or evidence in the transcript.
- [0:30] "best system ever" — Vague claim with no methodology.
- [thumb] "stack of cash on desk" — Cash imagery implies a payoff the video never demonstrates.
- [4:12] "act now before the price goes up" — Urgency pitch.
"""


SKIP_REPORT_NO_BEST = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Empty Pitch
  PitchTube · 5:00 · 100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE VERDICT
Full skip. Pure pitch with no content.

VERDICT: SKIP   [2/10]

WHAT IT ACTUALLY DELIVERS
[0:00–5:00] Pitch.

TITLE vs CONTENT
Title promises:  A workflow.
Content delivers: An ad.
Gap: HIGH

SUBSTANCE DENSITY
Concrete claims: 0
Vague claims:    20
Evidence shown:  0
Pitches/CTAs:    8

WHO SHOULD WATCH
Nobody.

WHO SHOULD SKIP
Everyone.

BEST 0 MINUTES
Nothing — full skip recommended.

FLAGS
- [0:01] "best system ever" — vague.
- [0:30] "act now" — pitch.
- [1:00] "limited time" — pitch.
"""


METADATA = {
    "title": "Sample Video Title",
    "channel": "Sample Channel",
    "duration_seconds": 884,
}


def _run_cli(*args, stdin: str = ""):
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "dashboard.py"), *args]
    return subprocess.run(
        cmd, input=stdin, capture_output=True, text=True, check=False
    )


# ----------------------------------------------------------------------------
# parse_report
# ----------------------------------------------------------------------------


class TestParseReport:
    def test_extracts_verdict_and_score(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        assert parsed["verdict"] == "SKIP"
        assert parsed["score"] == 4

    def test_extracts_gap(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        assert parsed["gap"] == "MEDIUM"

    def test_extracts_executive_verdict(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        assert parsed["executive_verdict"].startswith("The eight \"billionaire rules\"")
        # Must NOT bleed into the next section
        assert "VERDICT:" not in parsed["executive_verdict"]

    def test_extracts_substance_counts(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        assert parsed["substance"] == {"concrete": 25, "vague": 12, "evidence": 10}

    def test_extracts_best_minutes(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        assert parsed["best_minutes"]["start"] == "1:38"
        assert parsed["best_minutes"]["end"] == "7:30"
        assert "concrete anecdotes" in parsed["best_minutes"]["description"]

    def test_extracts_audience_lines(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        assert parsed["watch_if"].startswith("Founders new to billionaire")
        assert parsed["skip_if"].startswith("Anyone already familiar")

    def test_extracts_flags(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        assert len(parsed["flags"]) == 2
        assert parsed["flags"][0]["timestamp"] == "7:01"
        assert "Elon Musk" in parsed["flags"][0]["quote"]
        assert "mis-stated" in parsed["flags"][0]["reason"].lower()

    def test_skip_no_best_minutes(self):
        parsed = dashboard.parse_report(SKIP_REPORT_NO_BEST)
        assert parsed["best_minutes"] is None

    def test_no_flags_section_returns_empty_list(self):
        parsed = dashboard.parse_report(WATCH_REPORT_NO_FLAGS)
        assert parsed["flags"] == []

    def test_missing_verdict_raises(self):
        with pytest.raises(ValueError, match="VERDICT"):
            dashboard.parse_report("no verdict here")

    def test_thumb_gap_absent_when_no_thumbnail_block(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        assert parsed["thumb_gap"] is None

    def test_thumb_gap_extracted_when_block_present(self):
        parsed = dashboard.parse_report(THUMBNAIL_REPORT)
        assert parsed["gap"] == "HIGH"          # title gap
        assert parsed["thumb_gap"] == "HIGH"    # thumbnail gap

    def test_thumbnail_block_does_not_bleed_into_title_gap(self):
        """Title-gap regex must scope to TITLE vs CONTENT block only."""
        report = SAMPLE_REPORT.replace("Gap: MEDIUM", "Gap: LOW")
        # Build a report where TITLE gap is LOW and THUMBNAIL gap is HIGH.
        # The bare `^Gap:\s+(\w+)` regex would have grabbed whichever came
        # first; the scoped extraction must pick TITLE = LOW.
        spliced = report.replace(
            "SUBSTANCE DENSITY",
            "THUMBNAIL vs CONTENT\nThumbnail promises: x\n"
            "Content delivers: y\nGap: HIGH\n\nSUBSTANCE DENSITY",
        )
        parsed = dashboard.parse_report(spliced)
        assert parsed["gap"] == "LOW"
        assert parsed["thumb_gap"] == "HIGH"

    def test_thumb_flag_extracted(self):
        parsed = dashboard.parse_report(THUMBNAIL_REPORT)
        thumb_flags = [f for f in parsed["flags"] if f["timestamp"] == "thumb"]
        assert len(thumb_flags) == 2
        assert thumb_flags[0]["quote"] == "$10K/DAY"


# ----------------------------------------------------------------------------
# render
# ----------------------------------------------------------------------------


class TestRender:
    def test_borders_are_54_chars(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        out = dashboard.render(parsed, METADATA)
        for line in out.splitlines():
            if line.startswith("━"):
                assert len(line) == 54

    def test_sample_skip_uses_x_badge(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        out = dashboard.render(parsed, METADATA)
        assert "❌" in out
        assert "SKIP" in out
        assert "4/10" in out

    def test_watch_uses_check_badge(self):
        parsed = dashboard.parse_report(WATCH_REPORT_NO_FLAGS)
        out = dashboard.render(parsed, {"title": "Solid Tutorial", "channel": "TutChan", "duration_seconds": 510})
        assert "✅" in out
        assert "✨" in out

    def test_skip_uses_x_badge(self):
        parsed = dashboard.parse_report(SKIP_REPORT_NO_BEST)
        out = dashboard.render(parsed, {"title": "Empty Pitch", "channel": "PitchTube", "duration_seconds": 300})
        assert "❌" in out
        assert "🚫" in out

    def test_executive_verdict_soft_wrapped(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        out = dashboard.render(parsed, METADATA)
        # The exec verdict line and its wrapped continuations should appear.
        # Each prose line should be ≤ 60 cols of content.
        prose_lines = [
            line for line in out.splitlines()
            if line.startswith("  🚫") or line.startswith("     ")
        ]
        assert len(prose_lines) >= 2  # multi-line wrap for this fixture

    def test_flag_quote_truncated_to_40_chars(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        out = dashboard.render(parsed, METADATA)
        # The Musk quote is way over 40 chars; should appear truncated.
        for line in out.splitlines():
            if "Elon Musk" in line:
                # Extract the inner quoted text
                start = line.index('"') + 1
                end = line.index('"', start)
                assert end - start <= 40

    def test_only_first_two_flags_rendered(self):
        # Build a report with 4 flags; only 2 should appear.
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        # Sample has 2 flags; add fake extras for this test
        parsed["flags"].extend([
            {"timestamp": "8:00", "quote": "third", "reason": "third"},
            {"timestamp": "9:00", "quote": "fourth", "reason": "fourth"},
        ])
        out = dashboard.render(parsed, METADATA)
        assert "Flags (4)" in out
        assert "third" not in out
        assert "fourth" not in out

    def test_omit_flags_block_when_no_flags(self):
        parsed = dashboard.parse_report(WATCH_REPORT_NO_FLAGS)
        out = dashboard.render(parsed, {"title": "Solid Tutorial", "channel": "TutChan", "duration_seconds": 510})
        assert "🚩" not in out
        assert "Flags" not in out

    def test_omit_best_minutes_when_full_skip(self):
        parsed = dashboard.parse_report(SKIP_REPORT_NO_BEST)
        out = dashboard.render(parsed, {"title": "Empty Pitch", "channel": "PitchTube", "duration_seconds": 300})
        assert "🎯 Best minutes" not in out

    def test_duration_human_under_one_hour(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        out = dashboard.render(parsed, METADATA)
        assert "14:44" in out

    def test_duration_human_over_one_hour(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        out = dashboard.render(parsed, {**METADATA, "duration_seconds": 3725})
        assert "1:02:05" in out

    def test_report_path_footer_included_when_provided(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        out = dashboard.render(parsed, METADATA, report_path="~/youtube-reports/foo.md")
        assert "📄 ~/youtube-reports/foo.md" in out

    def test_report_path_footer_omitted_when_not_provided(self):
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        out = dashboard.render(parsed, METADATA)
        assert "📄" not in out

    def test_thumb_gap_line_rendered_when_thumbnail_block_present(self):
        parsed = dashboard.parse_report(THUMBNAIL_REPORT)
        out = dashboard.render(
            parsed,
            {"title": "Make $10K/Day With This One Trick",
             "channel": "ScammyTube", "duration_seconds": 720},
        )
        assert "Title gap HIGH" in out
        assert "Thumb gap HIGH" in out

    def test_thumb_gap_line_omitted_when_no_thumbnail_block(self):
        """Silent fallback: dashboard layout unchanged when thumbnail axis absent."""
        parsed = dashboard.parse_report(SAMPLE_REPORT)
        out = dashboard.render(parsed, METADATA)
        assert "Thumb gap" not in out
        assert "Gap MEDIUM" in out  # original single-axis line preserved

    def test_dashboard_prioritizes_thumb_flag_in_top_two(self):
        """When [thumb] flags exist, surface one in the truncated 2-flag slot."""
        parsed = dashboard.parse_report(THUMBNAIL_REPORT)
        out = dashboard.render(
            parsed,
            {"title": "x", "channel": "y", "duration_seconds": 720},
        )
        # 4 flags total — first two rendered should be one [thumb] then one transcript.
        thumb_lines = [
            line for line in out.splitlines()
            if "[thumb]" in line and "$" in line
        ]
        assert len(thumb_lines) == 1
        # And one transcript-flag bullet is present.
        transcript_lines = [
            line for line in out.splitlines()
            if "[0:30]" in line and "vague claim" in line.lower()
        ]
        assert len(transcript_lines) == 1
        # The 4th flag (act now) should NOT appear.
        assert "act now" not in out

    def test_select_dashboard_flags_with_no_thumb(self):
        flags = [
            {"timestamp": "0:01", "quote": "a", "reason": "r1"},
            {"timestamp": "0:02", "quote": "b", "reason": "r2"},
            {"timestamp": "0:03", "quote": "c", "reason": "r3"},
        ]
        # Falls back to first 2 in original order.
        picked = dashboard._select_dashboard_flags(flags, limit=2)
        assert [f["timestamp"] for f in picked] == ["0:01", "0:02"]

    def test_select_dashboard_flags_only_thumb(self):
        flags = [
            {"timestamp": "thumb", "quote": "a", "reason": "r1"},
            {"timestamp": "thumb", "quote": "b", "reason": "r2"},
        ]
        picked = dashboard._select_dashboard_flags(flags, limit=2)
        assert len(picked) == 2
        assert all(f["timestamp"] == "thumb" for f in picked)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


class TestCli:
    def test_runs_end_to_end(self, tmp_path):
        # Create a transcript cache file
        cache_file = tmp_path / "abc11charsxx.json"
        cache_file.write_text(json.dumps({
            "video_id": "abc11charsxx",
            "title": "Sample Video Title",
            "channel": "Sample Channel",
            "duration_seconds": 884,
            "transcript": [],
        }), encoding="utf-8")

        result = _run_cli(
            "abc11charsxx",
            "--cache-dir", str(tmp_path),
            stdin=SAMPLE_REPORT,
        )
        assert result.returncode == 0
        assert "SKIP" in result.stdout
        assert "Sample Video Title" in result.stdout
        assert "━" * 54 in result.stdout

    def test_missing_transcript_cache(self, tmp_path):
        result = _run_cli(
            "missing11xxx",
            "--cache-dir", str(tmp_path),
            stdin=SAMPLE_REPORT,
        )
        assert result.returncode == 1
        assert "transcript cache" in result.stderr.lower()

    def test_empty_stdin(self, tmp_path):
        cache_file = tmp_path / "abc11charsxx.json"
        cache_file.write_text(json.dumps({
            "video_id": "abc11charsxx",
            "title": "x", "channel": "y", "duration_seconds": 60,
            "transcript": [],
        }), encoding="utf-8")
        result = _run_cli(
            "abc11charsxx",
            "--cache-dir", str(tmp_path),
            stdin="",
        )
        assert result.returncode == 1
        assert "empty" in result.stderr.lower()

    def test_malformed_report(self, tmp_path):
        cache_file = tmp_path / "abc11charsxx.json"
        cache_file.write_text(json.dumps({
            "video_id": "abc11charsxx",
            "title": "x", "channel": "y", "duration_seconds": 60,
            "transcript": [],
        }), encoding="utf-8")
        result = _run_cli(
            "abc11charsxx",
            "--cache-dir", str(tmp_path),
            stdin="garbage report with no VERDICT line",
        )
        assert result.returncode == 1
        assert "VERDICT" in result.stderr
