#!/usr/bin/env python3
"""segments.py — slice a cached transcript to one section's segments.

Part of the yt-verdict skill. No LLM calls. No network calls.

Reads `~/yt-reports/.cache/{video_id}.json` (written by fetch.py) and prints
a JSON object on stdout with the same shape the Pass 2 prompt expects, but
containing only the segments whose `start` is in `[start_ts, end_ts)`.

CLI:
    python scripts/segments.py <video_id> <start_ts> <end_ts> [--cache-dir DIR]

Timestamps accept `M:SS` or `H:MM:SS` — the same formats Pass 1 emits.

Exit codes:
    0  success
    1  usage error / missing cache / bad timestamp
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_CACHE_DIR = Path.home() / "yt-reports" / ".cache"


def parse_timestamp(ts: str) -> int:
    """Parse `M:SS` or `H:MM:SS` into integer seconds. Raises ValueError on bad input."""
    parts = ts.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"bad timestamp {ts!r}: expected M:SS or H:MM:SS")
    nums = [int(p) for p in parts]  # raises ValueError on non-int parts
    if any(n < 0 for n in nums):
        raise ValueError(f"bad timestamp {ts!r}: negative component")
    if len(parts) == 2:
        m, s = nums
        if s >= 60:
            raise ValueError(f"bad timestamp {ts!r}: seconds >= 60")
        return m * 60 + s
    h, m, s = nums
    if m >= 60 or s >= 60:
        raise ValueError(f"bad timestamp {ts!r}: minutes/seconds >= 60")
    return h * 3600 + m * 60 + s


def slice_transcript(data: dict, start_seconds: int, end_seconds: int) -> dict:
    """Return a new transcript dict containing only segments in [start, end)."""
    sliced = [
        seg for seg in data.get("transcript", [])
        if start_seconds <= seg["start"] < end_seconds
    ]
    return {
        "video_id": data["video_id"],
        "title": data["title"],
        "duration_seconds": data["duration_seconds"],
        "transcript": sliced,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Slice a cached transcript to one section's segments."
    )
    parser.add_argument("video_id")
    parser.add_argument("start_ts", help="M:SS or H:MM:SS")
    parser.add_argument("end_ts", help="M:SS or H:MM:SS")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Override the cache directory (default: ~/yt-reports/.cache)",
    )
    args = parser.parse_args(argv)

    try:
        start_seconds = parse_timestamp(args.start_ts)
        end_seconds = parse_timestamp(args.end_ts)
    except ValueError as e:
        sys.stderr.write(f"segments.py: {e}\n")
        return 1

    if end_seconds < start_seconds:
        sys.stderr.write(
            f"segments.py: end ({args.end_ts}) precedes start ({args.start_ts})\n"
        )
        return 1

    cache_path = args.cache_dir / f"{args.video_id}.json"
    if not cache_path.exists():
        sys.stderr.write(f"segments.py: cache miss at {cache_path}\n")
        return 1

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"segments.py: failed to read {cache_path}: {e}\n")
        return 1

    if "error" in data:
        sys.stderr.write(
            f"segments.py: cache file is a rejection record ({data.get('error')})\n"
        )
        return 1

    sliced = slice_transcript(data, start_seconds, end_seconds)
    sys.stdout.write(json.dumps(sliced, ensure_ascii=False, separators=(",", ":")))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
