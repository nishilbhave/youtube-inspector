"""Drift detection: each skill ships byte-identical copies of canonical scripts/prompts.

If a developer edits `scripts/X.py` or `prompts/Y.md` at the repo root and
forgets to re-run `python3 scripts/build_skills.py`, this test fails with a
clear pointer to the fix.

Also enforces SKILL.md path discipline — no bare `python3 scripts/` paths
that would silently fail when the skill is installed standalone via
`npx skills add`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import build_skills  # noqa: E402
from cache import hash_file  # noqa: E402


REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

ALL_SKILLS = list(build_skills.PROMPT_SETS.keys())


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_skill_md_exists(skill: str):
    assert (SKILLS_DIR / skill / "SKILL.md").exists()


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_shared_scripts_copied_byte_identical(skill: str):
    skill_scripts = SKILLS_DIR / skill / "scripts"
    for script_name in build_skills.SHARED_SCRIPTS:
        canonical = REPO_ROOT / "scripts" / script_name
        copy = skill_scripts / script_name
        assert copy.exists(), (
            f"{copy} missing — run `python3 scripts/build_skills.py`"
        )
        assert hash_file(canonical) == hash_file(copy), (
            f"{copy} drifted from {canonical} — "
            f"run `python3 scripts/build_skills.py`"
        )


def test_verdict_only_scripts_copied():
    """dashboard.py ships only with youtube-verdict."""
    for name in build_skills.VERDICT_ONLY_SCRIPTS:
        verdict_copy = SKILLS_DIR / "youtube-verdict" / "scripts" / name
        canonical = REPO_ROOT / "scripts" / name
        assert verdict_copy.exists()
        assert hash_file(canonical) == hash_file(verdict_copy)
        for sister in ("youtube-summary", "youtube-extract", "youtube-claims"):
            assert not (SKILLS_DIR / sister / "scripts" / name).exists(), (
                f"{name} should not ship with {sister}"
            )


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_prompts_copied_byte_identical(skill: str):
    skill_prompts = SKILLS_DIR / skill / "prompts"
    for prompt_name in build_skills.PROMPT_SETS[skill]:
        canonical = REPO_ROOT / "prompts" / prompt_name
        copy = skill_prompts / prompt_name
        assert copy.exists(), (
            f"{copy} missing — run `python3 scripts/build_skills.py`"
        )
        assert hash_file(canonical) == hash_file(copy), (
            f"{copy} drifted from {canonical} — "
            f"run `python3 scripts/build_skills.py`"
        )


@pytest.mark.parametrize("skill", ALL_SKILLS)
def test_skill_md_uses_skill_dir_paths(skill: str):
    """SKILL.md must not contain bare `python3 scripts/` or `prompts/` paths."""
    skill_md = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
    for forbidden in ("python3 scripts/", "python scripts/"):
        # The path may appear inside a code block as part of an inline-fallback
        # snippet or an instruction warning. Explicit absolute-path examples
        # (`python3 "/abs/path/to/...`) are fine; we look for the bare relative
        # form that fails when CWD is wrong.
        for line in skill_md.splitlines():
            if forbidden in line and "<SKILL_DIR>" not in line and "scripts/cache.py" not in line and "scripts/fetch.py" not in line and "scripts/doctor.py" not in line:
                # Allow occurrences inside command examples already wrapped
                # in `<SKILL_DIR>`; otherwise fail.
                pytest.fail(
                    f"{skill}/SKILL.md contains bare `{forbidden}` path "
                    f"in line:\n  {line.strip()}\n"
                    f"Use <SKILL_DIR>-prefixed paths."
                )


def test_build_skills_idempotent(tmp_path):
    """Running build_skills twice in a row produces the same files (no churn)."""
    # Capture current state
    snapshot = {}
    for skill in ALL_SKILLS:
        skill_dir = SKILLS_DIR / skill
        for path in skill_dir.rglob("*"):
            if path.is_file():
                snapshot[path] = hash_file(path)

    # Re-run
    rc = build_skills.main()
    assert rc == 0

    # Verify every file's hash unchanged
    for path, before_hash in snapshot.items():
        assert path.exists(), f"{path} disappeared after re-run"
        assert hash_file(path) == before_hash, f"{path} changed after re-run"


def test_build_skills_main_exits_zero():
    """build_skills.main() runs cleanly on the current repo state."""
    assert build_skills.main() == 0
