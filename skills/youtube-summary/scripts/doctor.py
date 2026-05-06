#!/usr/bin/env python3
"""doctor.py — pre-flight dependency check for the youtube-inspector skills.

No LLM calls. No network calls. Stdlib only (apart from the imports it tests
for). Reports whether `yt-dlp` and `youtube-transcript-api` are importable in
the current Python environment, and prints the exact `pipx install` command
to fix it if not. Designed to be invoked manually when a skill subprocess
fails with `ModuleNotFoundError` from `scripts/fetch.py`.

CLI:
    python3 scripts/doctor.py
        Exit 0 if both deps importable; print `✓ all deps present (...)`.
        Exit 1 if either is missing; print `✗ missing: <module>` and the
        pipx install command (with a pip --user fallback line).
"""
from __future__ import annotations

import sys

REQUIRED: list[tuple[str, str]] = [
    ("yt_dlp", "yt-dlp"),
    ("youtube_transcript_api", "youtube-transcript-api"),
]

INSTALL_PIPX = "pipx install yt-dlp youtube-transcript-api"
INSTALL_PIP = "pip install --user yt-dlp youtube-transcript-api"


def check() -> list[str]:
    """Return the list of missing module-import-names."""
    missing: list[str] = []
    for import_name, _ in REQUIRED:
        try:
            __import__(import_name)
        except ModuleNotFoundError:
            missing.append(import_name)
    return missing


def main() -> int:
    missing = check()
    if not missing:
        names = ", ".join(pkg for _, pkg in REQUIRED)
        print(f"✓ all deps present ({names})")
        return 0
    for name in missing:
        print(f"✗ missing: {name}")
    print(f"Run: {INSTALL_PIPX}")
    print(f"Or:  {INSTALL_PIP}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
