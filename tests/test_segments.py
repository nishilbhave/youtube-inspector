"""Unit tests for scripts/segments.py — no real network calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import segments  # noqa: E402


# ----------------------------------------------------------------------------
# parse_timestamp
# ----------------------------------------------------------------------------


class TestParseTimestamp:
    @pytest.mark.parametrize(
        "ts,expected",
        [
            ("0:00", 0),
            ("0:42", 42),
            ("3:48", 228),
            ("15:00", 900),
            ("59:59", 3599),
            ("1:00:00", 3600),
            ("1:24:30", 5070),
            ("10:00:00", 36000),
        ],
    )
    def test_valid(self, ts, expected):
        assert segments.parse_timestamp(ts) == expected

    @pytest.mark.parametrize(
        "ts",
        [
            "",
            "abc",
            "1:2:3:4",
            "1:60",
            "1:00:60",
            "1:60:00",
            "-1:00",
            "1:-5",
            "5",
        ],
    )
    def test_invalid(self, ts):
        with pytest.raises(ValueError):
            segments.parse_timestamp(ts)


# ----------------------------------------------------------------------------
# slice_transcript — boundary semantics
# ----------------------------------------------------------------------------


@pytest.fixture
def sample_data():
    return {
        "video_id": "abc12345678",
        "title": "Test",
        "duration_seconds": 100,
        "transcript": [
            {"start": 0.0, "duration": 1.0, "text": "intro"},
            {"start": 10.0, "duration": 2.0, "text": "ten seconds"},
            {"start": 20.0, "duration": 3.0, "text": "twenty seconds"},
            {"start": 30.0, "duration": 1.5, "text": "thirty seconds"},
            {"start": 60.0, "duration": 0.5, "text": "one minute"},
        ],
    }


class TestSliceTranscript:
    def test_inclusive_start_exclusive_end(self, sample_data):
        # [10, 30) — should include 10 and 20, exclude 30
        result = segments.slice_transcript(sample_data, 10, 30)
        starts = [seg["start"] for seg in result["transcript"]]
        assert starts == [10.0, 20.0]

    def test_segment_at_exact_end_excluded(self, sample_data):
        # boundary case: a segment whose start == end must NOT be included
        result = segments.slice_transcript(sample_data, 0, 30)
        starts = [seg["start"] for seg in result["transcript"]]
        assert 30.0 not in starts
        assert starts == [0.0, 10.0, 20.0]

    def test_empty_range_yields_empty_list(self, sample_data):
        # zero-width range
        result = segments.slice_transcript(sample_data, 5, 5)
        assert result["transcript"] == []

    def test_range_beyond_duration_empty(self, sample_data):
        result = segments.slice_transcript(sample_data, 1000, 2000)
        assert result["transcript"] == []

    def test_preserves_segment_field_shape(self, sample_data):
        result = segments.slice_transcript(sample_data, 0, 15)
        for seg in result["transcript"]:
            assert set(seg.keys()) == {"start", "duration", "text"}

    def test_preserves_video_metadata(self, sample_data):
        result = segments.slice_transcript(sample_data, 0, 100)
        assert result["video_id"] == "abc12345678"
        assert result["title"] == "Test"
        assert result["duration_seconds"] == 100


# ----------------------------------------------------------------------------
# main() — CLI behavior
# ----------------------------------------------------------------------------


class TestMainCLI:
    def test_happy_path(self, tmp_path, sample_data, capsys):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "abc12345678.json").write_text(json.dumps(sample_data))

        rc = segments.main(
            ["abc12345678", "0:10", "0:30", "--cache-dir", str(cache_dir)]
        )
        assert rc == 0

        out = capsys.readouterr().out.strip()
        parsed = json.loads(out)
        assert parsed["video_id"] == "abc12345678"
        assert [seg["start"] for seg in parsed["transcript"]] == [10.0, 20.0]

    def test_missing_cache_returns_1(self, tmp_path, capsys):
        rc = segments.main(
            ["nonexistent0", "0:00", "1:00", "--cache-dir", str(tmp_path)]
        )
        assert rc == 1
        assert "cache miss" in capsys.readouterr().err

    def test_bad_timestamp_returns_1(self, tmp_path, sample_data, capsys):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "abc12345678.json").write_text(json.dumps(sample_data))

        rc = segments.main(
            ["abc12345678", "garbage", "0:30", "--cache-dir", str(cache_dir)]
        )
        assert rc == 1

    def test_end_before_start_returns_1(self, tmp_path, sample_data, capsys):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "abc12345678.json").write_text(json.dumps(sample_data))

        rc = segments.main(
            ["abc12345678", "1:00", "0:30", "--cache-dir", str(cache_dir)]
        )
        assert rc == 1
        assert "precedes" in capsys.readouterr().err

    def test_rejection_record_returns_1(self, tmp_path, capsys):
        # A fetch.py rejection record (exit 2) is cached as {"error": ..., "message": ...}
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "rejected123.json").write_text(
            json.dumps({"error": "TOO_SHORT", "message": "too short", "video_id": "rejected123"})
        )

        rc = segments.main(
            ["rejected123", "0:00", "1:00", "--cache-dir", str(cache_dir)]
        )
        assert rc == 1
        assert "rejection" in capsys.readouterr().err

    def test_output_is_compact_json(self, tmp_path, sample_data, capsys):
        # No spaces between separators — saves bytes in tool-result context
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "abc12345678.json").write_text(json.dumps(sample_data))

        rc = segments.main(
            ["abc12345678", "0:00", "1:30", "--cache-dir", str(cache_dir)]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert ", " not in out
        assert ": " not in out


# ----------------------------------------------------------------------------
# Verbatim invariant — slicing must preserve the substring property exactly.
# Uses the real frozen sample transcript so this catches any future drift in
# fetch.py's segment shape.
# ----------------------------------------------------------------------------


def test_real_sample_preserves_verbatim_text():
    sample_path = (
        Path(__file__).parent.parent
        / "prompts"
        / "samples"
        / "transcripts"
        / "n0phBDPz8z0.json"
    )
    if not sample_path.exists():
        pytest.skip(f"sample fixture missing: {sample_path}")

    data = json.loads(sample_path.read_text())
    # full-duration slice: every segment in the sliced output must appear,
    # character-for-character, in the original transcript.
    sliced = segments.slice_transcript(data, 0, 10**9)
    original_texts = {seg["text"] for seg in data["transcript"]}
    for seg in sliced["transcript"]:
        assert seg["text"] in original_texts
