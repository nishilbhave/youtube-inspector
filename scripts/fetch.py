#!/usr/bin/env python3
"""fetch.py — YouTube URL → validated JSON (metadata + transcript).

Part of the yt-verdict skill in the youtube-inspector repo. No LLM calls.

CLI:
    python scripts/fetch.py <url-or-id> [--out PATH] [--cache] [--language en]

Exit codes:
    0  success
    2  documented rejection (INVALID_URL, PLAYLIST, LIVE_STREAM, TOO_SHORT,
       NO_TRANSCRIPT, NON_ENGLISH)
    1  unexpected error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import parse_qs, urlparse

CACHE_DIR = Path.home() / "yt-reports" / ".cache"
MIN_DURATION_SECONDS = 180
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
VALID_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "music.youtube.com",
}


class FetchError(Exception):
    """Raised on documented rejection rules."""

    def __init__(self, code: str, message: str, video_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.video_id = video_id


def emit_error(err: FetchError) -> NoReturn:
    payload = {
        "error": err.code,
        "message": err.message,
        "video_id": err.video_id or "",
    }
    sys.stderr.write(json.dumps(payload) + "\n")
    sys.exit(2)


def parse_video_id(raw: str) -> str:
    """Parse a YouTube URL or 11-char video ID. Reject playlist URLs.

    Raises FetchError(INVALID_URL or PLAYLIST) on failure.
    """
    raw = (raw or "").strip()
    if not raw:
        raise FetchError("INVALID_URL", "Empty input.")

    if VIDEO_ID_RE.match(raw):
        return raw

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower()
    if host not in VALID_HOSTS:
        raise FetchError("INVALID_URL", f"Could not extract video ID from {raw}")

    path = parsed.path or ""
    qs = parse_qs(parsed.query or "")

    if path == "/playlist":
        raise FetchError("PLAYLIST", "Playlist URL detected; pass a specific video.")

    if path == "/watch":
        v = qs.get("v", [""])[0]
        if VIDEO_ID_RE.match(v):
            return v
        raise FetchError("INVALID_URL", f"Could not extract video ID from {raw}")

    if host == "youtu.be":
        candidate = path.lstrip("/").split("/")[0]
        if VIDEO_ID_RE.match(candidate):
            return candidate
        raise FetchError("INVALID_URL", f"Could not extract video ID from {raw}")

    for prefix in ("/shorts/", "/embed/", "/live/"):
        if path.startswith(prefix):
            candidate = path[len(prefix):].split("/")[0]
            if VIDEO_ID_RE.match(candidate):
                return candidate

    raise FetchError("INVALID_URL", f"Could not extract video ID from {raw}")


def fetch_metadata(video_id: str) -> dict[str, Any]:
    """Fetch metadata via yt-dlp; enforce LIVE_STREAM and TOO_SHORT rules."""
    import yt_dlp

    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except FetchError:
        raise
    except Exception as e:
        raise FetchError("INVALID_URL", f"Could not fetch metadata: {e}", video_id) from e

    if info is None:
        raise FetchError("INVALID_URL", "yt-dlp returned no info.", video_id)

    if info.get("is_live") or info.get("live_status") == "is_live":
        raise FetchError("LIVE_STREAM", "Live streams are not supported in V1.", video_id)

    duration = info.get("duration")
    if not isinstance(duration, (int, float)):
        raise FetchError("INVALID_URL", "Could not determine video duration.", video_id)
    duration = int(duration)

    if duration < MIN_DURATION_SECONDS:
        raise FetchError(
            "TOO_SHORT",
            f"Video is {duration}s; minimum is {MIN_DURATION_SECONDS}s.",
            video_id,
        )

    return {
        "video_id": video_id,
        "url": url,
        "title": info.get("title", "") or "",
        "channel": info.get("channel", info.get("uploader", "")) or "",
        "channel_id": info.get("channel_id", "") or "",
        "duration_seconds": duration,
        "view_count": int(info.get("view_count") or 0),
        "upload_date": _format_upload_date(info.get("upload_date", "") or ""),
    }


def _format_upload_date(yyyymmdd: str) -> str:
    if yyyymmdd and len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"
    return ""


def fetch_transcript(video_id: str, language: str) -> tuple[list[dict[str, Any]], str]:
    """Try youtube-transcript-api first, fall back to yt-dlp auto-subs.

    Returns (segments, detected_language). Raises FetchError on failure.
    """
    try:
        return _fetch_transcript_primary(video_id, language)
    except FetchError:
        raise
    except Exception:
        # Primary failed (rate limit, signature change, etc.) → try fallback.
        pass

    try:
        return _fetch_transcript_fallback(video_id, language)
    except FetchError:
        raise
    except Exception as e:
        raise FetchError(
            "NO_TRANSCRIPT",
            f"All transcript fetch methods failed: {e}",
            video_id,
        ) from e


def _fetch_transcript_primary(
    video_id: str, language: str
) -> tuple[list[dict[str, Any]], str]:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
    except (TranscriptsDisabled, VideoUnavailable) as e:
        raise FetchError("NO_TRANSCRIPT", "No captions available for this video.", video_id) from e

    try:
        transcript = transcripts.find_transcript([language])
    except NoTranscriptFound:
        available = [t.language_code for t in transcripts]
        if available:
            raise FetchError(
                "NON_ENGLISH",
                f"Transcript language is {available[0]}; V1 only supports {language}.",
                video_id,
            )
        raise FetchError("NO_TRANSCRIPT", "No captions available for this video.", video_id)

    raw = transcript.fetch()
    segments = [
        {
            "start": float(s["start"]),
            "duration": float(s.get("duration", 0.0)),
            "text": s["text"],
        }
        for s in raw
    ]
    return segments, transcript.language_code


def _fetch_transcript_fallback(
    video_id: str, language: str
) -> tuple[list[dict[str, Any]], str]:
    """Use yt-dlp's auto-sub download as a fallback."""
    import yt_dlp

    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmp:
        out_template = str(Path(tmp) / "%(id)s.%(ext)s")
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [language, f"{language}.*"],
            "subtitlesformat": "vtt",
            "outtmpl": out_template,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)

        vtt_files = sorted(Path(tmp).glob(f"{video_id}*.vtt"))
        if not vtt_files:
            raise FetchError(
                "NO_TRANSCRIPT", "No captions available for this video.", video_id
            )

        # Filename pattern: <id>.<lang>.vtt — language-match before parsing.
        vtt_path = vtt_files[0]
        detected_lang = _vtt_language_from_filename(vtt_path.name, video_id)
        if detected_lang and not detected_lang.startswith(language):
            raise FetchError(
                "NON_ENGLISH",
                f"Transcript language is {detected_lang}; V1 only supports {language}.",
                video_id,
            )

        segments = _parse_vtt(vtt_path.read_text(encoding="utf-8"))
        if not segments:
            raise FetchError(
                "NO_TRANSCRIPT", "Downloaded captions were empty.", video_id
            )
        return segments, detected_lang or language


def _vtt_language_from_filename(name: str, video_id: str) -> str:
    """Extract '<lang>' from '<video_id>.<lang>.vtt' (or empty on miss)."""
    if name.startswith(f"{video_id}.") and name.endswith(".vtt"):
        middle = name[len(video_id) + 1 : -4]
        return middle
    return ""


def _parse_vtt(content: str) -> list[dict[str, Any]]:
    """Minimal WebVTT → [{start, duration, text}]. Tolerant of extra blocks."""
    segments: list[dict[str, Any]] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" in line:
            try:
                head, _, tail = line.partition("-->")
                start = _parse_vtt_time(head.strip().split(" ")[0])
                end = _parse_vtt_time(tail.strip().split(" ")[0])
            except ValueError:
                i += 1
                continue
            i += 1
            text_lines: list[str] = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(_strip_vtt_tags(lines[i]).strip())
                i += 1
            text = " ".join(t for t in text_lines if t)
            if text:
                segments.append(
                    {"start": start, "duration": max(0.0, end - start), "text": text}
                )
        else:
            i += 1
    return segments


_VTT_TAG_RE = re.compile(r"<[^>]+>")


def _strip_vtt_tags(line: str) -> str:
    return _VTT_TAG_RE.sub("", line)


def _parse_vtt_time(s: str) -> float:
    parts = s.split(":")
    if len(parts) == 3:
        h, m, sec = parts
        return int(h) * 3600 + int(m) * 60 + float(sec)
    if len(parts) == 2:
        m, sec = parts
        return int(m) * 60 + float(sec)
    return float(s)


def cache_path(video_id: str) -> Path:
    return CACHE_DIR / f"{video_id}.json"


def cache_read(video_id: str) -> dict[str, Any] | None:
    p = cache_path(video_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def cache_write(video_id: str, payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache_path(video_id).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def fetch(video_id: str, language: str) -> dict[str, Any]:
    metadata = fetch_metadata(video_id)
    segments, detected = fetch_transcript(video_id, language)
    return {
        **metadata,
        "language": detected or language,
        "transcript": segments,
        "fetched_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    }


def _emit(payload: dict[str, Any], out: str | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if out:
        Path(out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fetch.py",
        description="Fetch a YouTube video's metadata + transcript as structured JSON.",
    )
    parser.add_argument("url", help="YouTube URL or 11-char video ID")
    parser.add_argument("--out", help="Write JSON to file (default: stdout)")
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Read/write ~/yt-reports/.cache/{video_id}.json",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Required transcript language code (default: en)",
    )
    args = parser.parse_args(argv)

    try:
        video_id = parse_video_id(args.url)
    except FetchError as e:
        emit_error(e)

    if args.cache:
        cached = cache_read(video_id)
        if cached is not None:
            if "error" in cached:
                emit_error(
                    FetchError(
                        cached["error"],
                        cached.get("message", ""),
                        cached.get("video_id") or video_id,
                    )
                )
            _emit(cached, args.out)
            return 0

    try:
        payload = fetch(video_id, args.language)
    except FetchError as e:
        if args.cache:
            cache_write(
                video_id,
                {
                    "error": e.code,
                    "message": e.message,
                    "video_id": e.video_id or video_id,
                },
            )
        emit_error(e)

    if args.cache:
        cache_write(video_id, payload)

    _emit(payload, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
