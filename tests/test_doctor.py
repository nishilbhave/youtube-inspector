"""Unit tests for scripts/doctor.py — no network, no LLM."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
DOCTOR = REPO_ROOT / "scripts" / "doctor.py"


def run_doctor(interp_flags: list[str] | None = None) -> subprocess.CompletedProcess:
    """Invoke doctor.py via subprocess; return the CompletedProcess."""
    cmd = [sys.executable, *(interp_flags or []), str(DOCTOR)]
    return subprocess.run(cmd, capture_output=True, text=True)


class TestDoctor:
    def test_succeeds_when_deps_present(self):
        """The test venv installs yt-dlp + youtube-transcript-api via `pip
        install -e ".[dev]"`, so doctor.py must report success here."""
        result = run_doctor()
        assert result.returncode == 0, (
            f"expected exit 0; got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "✓ all deps present" in result.stdout
        assert "yt-dlp" in result.stdout
        assert "youtube-transcript-api" in result.stdout

    def test_fails_when_modules_unimportable(self):
        """`python -S` skips site-packages, hiding both deps. doctor.py must
        exit 1 and print the exact pipx install command + pip fallback."""
        result = run_doctor(interp_flags=["-S"])
        assert result.returncode == 1, (
            f"expected exit 1; got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "✗ missing" in result.stdout
        assert "pipx install yt-dlp youtube-transcript-api" in result.stdout
        assert "pip install --user yt-dlp youtube-transcript-api" in result.stdout

    def test_failure_names_at_least_one_missing_module(self):
        """When deps are unreachable, the failure output names which module
        is missing — not just a generic error."""
        result = run_doctor(interp_flags=["-S"])
        assert result.returncode == 1
        assert "yt_dlp" in result.stdout or "youtube_transcript_api" in result.stdout


class TestCheckFunction:
    """Direct in-process tests of the `check()` helper."""

    def test_check_returns_empty_list_when_all_present(self, monkeypatch):
        """With both modules importable in this venv, check() returns []."""
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        try:
            import doctor
            assert doctor.check() == []
        finally:
            sys.path.pop(0)

    def test_required_list_shape(self):
        """REQUIRED is a list of (import_name, package_name) tuples — both
        the doctor CLI output and any future tooling depend on that shape."""
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        try:
            import doctor
            assert isinstance(doctor.REQUIRED, list)
            assert len(doctor.REQUIRED) >= 2
            for entry in doctor.REQUIRED:
                assert isinstance(entry, tuple) and len(entry) == 2
                assert all(isinstance(s, str) and s for s in entry)
            import_names = {e[0] for e in doctor.REQUIRED}
            assert "yt_dlp" in import_names
            assert "youtube_transcript_api" in import_names
        finally:
            sys.path.pop(0)
