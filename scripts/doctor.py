#!/usr/bin/env python3
"""doctor.py — pre-flight dependency check for the youtube-inspector skills.

No LLM calls. No network calls. Stdlib only (apart from the imports it tests
for). Reports whether `yt-dlp` and `youtube-transcript-api` are importable in
the current Python environment, and prints the install command tailored to
that environment if not.

The skill imports both packages from `python3` (see `scripts/fetch.py`), so
they must land on the import path of the same Python the skill subprocess
uses. That rules out `pipx`, which isolates each tool in its own private
venv — `pipx install yt-dlp` makes the `yt-dlp` CLI available but does NOT
make `import yt_dlp` work from your default `python3`. doctor.py therefore
recommends `pip3 install --user`, adding `--break-system-packages` only when
the current Python is marked externally managed per PEP 668 (Homebrew Python
on macOS, apt-installed Python on Debian/Ubuntu).

CLI:
    python3 scripts/doctor.py
        Exit 0 if both deps importable; print `✓ all deps present (...)`.
        Exit 1 if either is missing; print `✗ missing: <module>` and the
        install command for the current environment.
"""
from __future__ import annotations

import sys
import sysconfig
from pathlib import Path

REQUIRED: list[tuple[str, str]] = [
    ("yt_dlp", "yt-dlp"),
    ("youtube_transcript_api", "youtube-transcript-api"),
]

_PACKAGES = " ".join(pkg for _, pkg in REQUIRED)
INSTALL_PIP = f"pip3 install --user {_PACKAGES}"
INSTALL_PIP_PEP668 = f"pip3 install --user --break-system-packages {_PACKAGES}"


def is_externally_managed() -> bool:
    """Return True if the current Python is marked externally-managed (PEP 668).

    The marker is a file named `EXTERNALLY-MANAGED` in the stdlib directory.
    Common on Homebrew Python (macOS) and apt-installed Python (Debian/Ubuntu).
    """
    stdlib = Path(sysconfig.get_path("stdlib"))
    return (stdlib / "EXTERNALLY-MANAGED").exists()


def install_command() -> str:
    """Return the install command appropriate for the current Python."""
    if is_externally_managed():
        return INSTALL_PIP_PEP668
    return INSTALL_PIP


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
    print(f"Run: {install_command()}")
    if is_externally_managed():
        print(
            "     (--break-system-packages bypasses PEP 668; --user keeps the"
        )
        print(
            "      install in ~/Library/Python/, so Homebrew files are untouched.)"
        )
    print(
        "Note: don't use `pipx` for these — it isolates packages in a private"
    )
    print(
        "      venv, but the skill needs `import yt_dlp` from your default python3."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
