"""Unit tests for scripts/fetch.py — no real network calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Allow `import fetch` from the scripts/ dir without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import fetch  # noqa: E402


# ----------------------------------------------------------------------------
# parse_video_id
# ----------------------------------------------------------------------------


class TestParseVideoId:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("http://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ?t=42", "dQw4w9WgXcQ"),
        ],
    )
    def test_valid_inputs(self, raw, expected):
        assert fetch.parse_video_id(raw) == expected

    def test_empty_input_rejected(self):
        with pytest.raises(fetch.FetchError) as exc:
            fetch.parse_video_id("")
        assert exc.value.code == "INVALID_URL"

    def test_garbage_string_rejected(self):
        with pytest.raises(fetch.FetchError) as exc:
            fetch.parse_video_id("not-a-url")
        assert exc.value.code == "INVALID_URL"

    def test_non_youtube_domain_rejected(self):
        with pytest.raises(fetch.FetchError) as exc:
            fetch.parse_video_id("https://vimeo.com/12345")
        assert exc.value.code == "INVALID_URL"

    def test_playlist_url_rejected(self):
        with pytest.raises(fetch.FetchError) as exc:
            fetch.parse_video_id("https://www.youtube.com/playlist?list=PLxxx")
        assert exc.value.code == "PLAYLIST"

    def test_watch_url_without_v_param_rejected(self):
        with pytest.raises(fetch.FetchError) as exc:
            fetch.parse_video_id("https://www.youtube.com/watch")
        assert exc.value.code == "INVALID_URL"

    def test_short_id_rejected(self):
        with pytest.raises(fetch.FetchError) as exc:
            fetch.parse_video_id("abc123")
        assert exc.value.code == "INVALID_URL"


# ----------------------------------------------------------------------------
# Error JSON shape
# ----------------------------------------------------------------------------


class TestErrorOutput:
    def test_emit_error_writes_json_to_stderr(self, capsys):
        err = fetch.FetchError(
            "TOO_SHORT", "Video is 142s; minimum is 180s.", "abc12345678"
        )
        with pytest.raises(SystemExit) as exit_info:
            fetch.emit_error(err)
        assert exit_info.value.code == 2

        captured = capsys.readouterr()
        assert captured.out == ""  # no partial JSON on stdout
        payload = json.loads(captured.err)
        assert payload == {
            "error": "TOO_SHORT",
            "message": "Video is 142s; minimum is 180s.",
            "video_id": "abc12345678",
        }

    def test_emit_error_omits_missing_video_id(self, capsys):
        err = fetch.FetchError("INVALID_URL", "bad input")
        with pytest.raises(SystemExit):
            fetch.emit_error(err)
        payload = json.loads(capsys.readouterr().err)
        assert payload == {
            "error": "INVALID_URL",
            "message": "bad input",
            "video_id": "",
        }


# ----------------------------------------------------------------------------
# fetch_metadata rejection rules (mocked yt-dlp)
# ----------------------------------------------------------------------------


class TestFetchMetadataRejections:
    def _patch_ydl(self, info: dict | None):
        ydl_instance = MagicMock()
        ydl_instance.extract_info.return_value = info
        ydl_class = MagicMock()
        ydl_class.return_value.__enter__ = MagicMock(return_value=ydl_instance)
        ydl_class.return_value.__exit__ = MagicMock(return_value=False)
        return patch("yt_dlp.YoutubeDL", ydl_class)

    def test_live_stream_is_rejected(self):
        with self._patch_ydl({"is_live": True, "duration": 1000}):
            with pytest.raises(fetch.FetchError) as exc:
                fetch.fetch_metadata("dQw4w9WgXcQ")
        assert exc.value.code == "LIVE_STREAM"

    def test_live_status_is_live_is_rejected(self):
        with self._patch_ydl({"live_status": "is_live", "duration": 1000}):
            with pytest.raises(fetch.FetchError) as exc:
                fetch.fetch_metadata("dQw4w9WgXcQ")
        assert exc.value.code == "LIVE_STREAM"

    def test_too_short_is_rejected(self):
        with self._patch_ydl(
            {"duration": 142, "title": "x", "channel": "y", "channel_id": "z"}
        ):
            with pytest.raises(fetch.FetchError) as exc:
                fetch.fetch_metadata("dQw4w9WgXcQ")
        assert exc.value.code == "TOO_SHORT"
        assert "142s" in exc.value.message
        assert "180s" in exc.value.message

    def test_happy_path_returns_metadata(self):
        info = {
            "title": "Example",
            "channel": "TestChannel",
            "channel_id": "UC123",
            "duration": 600,
            "view_count": 10000,
            "upload_date": "20260101",
            "is_live": False,
        }
        with self._patch_ydl(info):
            meta = fetch.fetch_metadata("dQw4w9WgXcQ")
        assert meta == {
            "video_id": "dQw4w9WgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "Example",
            "channel": "TestChannel",
            "channel_id": "UC123",
            "duration_seconds": 600,
            "view_count": 10000,
            "upload_date": "2026-01-01",
        }


# ----------------------------------------------------------------------------
# Cache round-trip
# ----------------------------------------------------------------------------


class TestCache:
    def test_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fetch, "CACHE_DIR", tmp_path / "cache")
        payload = {
            "video_id": "test1234567",
            "title": "Test",
            "transcript": [{"start": 0.0, "duration": 1.0, "text": "hello"}],
        }
        fetch.cache_write("test1234567", payload)
        assert fetch.cache_read("test1234567") == payload

    def test_miss_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fetch, "CACHE_DIR", tmp_path / "cache")
        assert fetch.cache_read("missing12345") is None

    def test_corrupt_cache_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fetch, "CACHE_DIR", tmp_path / "cache")
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "corrupted12.json").write_text("not-json")
        assert fetch.cache_read("corrupted12") is None

    def test_cached_success_skips_network(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(fetch, "CACHE_DIR", tmp_path / "cache")
        cached = {
            "video_id": "dQw4w9WgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "Cached",
            "channel": "x",
            "channel_id": "y",
            "duration_seconds": 600,
            "view_count": 1,
            "upload_date": "2026-01-01",
            "language": "en",
            "transcript": [{"start": 0.0, "duration": 1.0, "text": "cached"}],
            "fetched_at": "2026-05-05T00:00:00Z",
        }
        fetch.cache_write("dQw4w9WgXcQ", cached)

        with patch.object(fetch, "fetch_metadata") as mock_meta, patch.object(
            fetch, "fetch_transcript"
        ) as mock_tr:
            exit_code = fetch.main(["dQw4w9WgXcQ", "--cache"])
        assert exit_code == 0
        mock_meta.assert_not_called()
        mock_tr.assert_not_called()
        out = capsys.readouterr().out
        assert json.loads(out)["title"] == "Cached"

    def test_cached_rejection_re_emits_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(fetch, "CACHE_DIR", tmp_path / "cache")
        fetch.cache_write(
            "dQw4w9WgXcQ",
            {"error": "TOO_SHORT", "message": "Video is 142s.", "video_id": "dQw4w9WgXcQ"},
        )

        with patch.object(fetch, "fetch_metadata") as mock_meta, patch.object(
            fetch, "fetch_transcript"
        ) as mock_tr:
            with pytest.raises(SystemExit) as exit_info:
                fetch.main(["dQw4w9WgXcQ", "--cache"])
        assert exit_info.value.code == 2
        mock_meta.assert_not_called()
        mock_tr.assert_not_called()

        err_payload = json.loads(capsys.readouterr().err)
        assert err_payload["error"] == "TOO_SHORT"


# ----------------------------------------------------------------------------
# main() integration with mocked network
# ----------------------------------------------------------------------------


class TestMainIntegration:
    def test_invalid_url_exits_2(self, capsys):
        with pytest.raises(SystemExit) as exit_info:
            fetch.main(["not-a-url"])
        assert exit_info.value.code == 2
        err = json.loads(capsys.readouterr().err)
        assert err["error"] == "INVALID_URL"

    def test_playlist_url_exits_2(self, capsys):
        with pytest.raises(SystemExit) as exit_info:
            fetch.main(["https://www.youtube.com/playlist?list=PLxx"])
        assert exit_info.value.code == 2
        err = json.loads(capsys.readouterr().err)
        assert err["error"] == "PLAYLIST"

    def test_happy_path_writes_json(self, capsys):
        meta = {
            "video_id": "dQw4w9WgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "T",
            "channel": "C",
            "channel_id": "CID",
            "duration_seconds": 600,
            "view_count": 0,
            "upload_date": "2026-01-01",
        }
        segs = ([{"start": 0.0, "duration": 1.0, "text": "hi"}], "en")
        with patch.object(fetch, "fetch_metadata", return_value=meta), patch.object(
            fetch, "fetch_transcript", return_value=segs
        ):
            exit_code = fetch.main(["dQw4w9WgXcQ"])
        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["video_id"] == "dQw4w9WgXcQ"
        assert payload["language"] == "en"
        assert payload["transcript"] == [
            {"start": 0.0, "duration": 1.0, "text": "hi"}
        ]
        assert payload["fetched_at"].endswith("Z")


# ----------------------------------------------------------------------------
# VTT parser
# ----------------------------------------------------------------------------


class TestVtt:
    def test_parses_basic_vtt(self):
        content = """WEBVTT

00:00:00.000 --> 00:00:02.500
Hello world

00:00:02.500 --> 00:00:05.000
This is a test
"""
        segs = fetch._parse_vtt(content)
        assert len(segs) == 2
        assert segs[0]["start"] == 0.0
        assert abs(segs[0]["duration"] - 2.5) < 0.01
        assert segs[0]["text"] == "Hello world"
        assert segs[1]["start"] == 2.5

    def test_strips_inline_tags(self):
        content = """WEBVTT

00:00:00.000 --> 00:00:01.000
<c.colorE5E5E5>Hello</c> <i>world</i>
"""
        segs = fetch._parse_vtt(content)
        assert segs[0]["text"] == "Hello world"

    def test_handles_mm_ss_form(self):
        assert fetch._parse_vtt_time("01:30.500") == 90.5
        assert fetch._parse_vtt_time("00:00:01.000") == 1.0

    def test_language_from_filename(self):
        assert fetch._vtt_language_from_filename("dQw4w9WgXcQ.en.vtt", "dQw4w9WgXcQ") == "en"
        assert (
            fetch._vtt_language_from_filename("dQw4w9WgXcQ.en-US.vtt", "dQw4w9WgXcQ")
            == "en-US"
        )
        assert fetch._vtt_language_from_filename("other.vtt", "dQw4w9WgXcQ") == ""
