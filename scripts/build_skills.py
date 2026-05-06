#!/usr/bin/env python3
"""build_skills.py — copy canonical scripts/ + per-skill prompts into skills/<name>/.

Part of the youtube-inspector skill suite. No LLM calls. No network calls.

Each skill in `skills/<name>/` ships only its `SKILL.md` from source control,
but the SKILL.md references `scripts/X.py` and `prompts/Y.md` paths that
must be resolvable when a fresh user installs via `npx skills add`. This
script populates `skills/<name>/scripts/` and `skills/<name>/prompts/` with
byte-identical copies of the canonical files at the repo root.

Per-skill prompt sets (defined below) ship only the prompts each skill
actually uses, so a user installing one skill doesn't ship dead artifacts
from the others.

Idempotent. Run before tagging a release. `tests/test_skill_packaging.py`
verifies that the per-skill copies are byte-identical to the canonical
source — out-of-sync runs of build_skills.py are caught by CI.

CLI:
    python3 scripts/build_skills.py
        Sync per-skill copies of scripts/ and prompts/ for all 4 skills.
        Prints one line per skill on completion.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Scripts shipped with every skill. fetch.py needs deps; segments/cache/doctor
# are stdlib-only.
SHARED_SCRIPTS = ("fetch.py", "cache.py", "segments.py", "doctor.py")

# Per-skill prompt sets. Pass 1's extract_structure.md is shared across all 4.
# Pass 2 is shared between verdict and claims (inventory_claims.md). Pass 3
# is unique per skill.
PROMPT_SETS = {
    "youtube-verdict": (
        "extract_structure.md",
        "inventory_claims.md",
        "generate_verdict.md",
    ),
    "youtube-summary": (
        "extract_structure.md",
        "summarize_sections.md",
        "generate_summary.md",
    ),
    "youtube-extract": (
        "extract_structure.md",
        "extract_artifacts.md",
        "generate_extract.md",
    ),
    "youtube-claims": (
        "extract_structure.md",
        "inventory_claims.md",
        "generate_claims.md",
    ),
}

# Verdict-only scripts. dashboard.py renders the WATCH/OKAY/SKIP dashboard
# from a Pass 3 report and is not used by the other three skills.
VERDICT_ONLY_SCRIPTS = ("dashboard.py",)


def _sync_dir(src_files: list[Path], dest_dir: Path) -> int:
    """Copy each source file into dest_dir; return number of files copied."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in src_files:
        dest = dest_dir / src.name
        shutil.copyfile(src, dest)
        copied += 1
    return copied


def build_skill(name: str, prompts: tuple[str, ...]) -> tuple[int, int]:
    skill_dir = REPO_ROOT / "skills" / name
    if not (skill_dir / "SKILL.md").exists():
        raise FileNotFoundError(f"build_skills.py: missing {skill_dir / 'SKILL.md'}")

    scripts_to_copy = [REPO_ROOT / "scripts" / s for s in SHARED_SCRIPTS]
    if name == "youtube-verdict":
        scripts_to_copy += [REPO_ROOT / "scripts" / s for s in VERDICT_ONLY_SCRIPTS]
    n_scripts = _sync_dir(scripts_to_copy, skill_dir / "scripts")

    prompts_to_copy = [REPO_ROOT / "prompts" / p for p in prompts]
    n_prompts = _sync_dir(prompts_to_copy, skill_dir / "prompts")

    return n_scripts, n_prompts


def main() -> int:
    for name, prompts in PROMPT_SETS.items():
        try:
            n_scripts, n_prompts = build_skill(name, prompts)
        except FileNotFoundError as e:
            sys.stderr.write(str(e) + "\n")
            return 1
        sys.stdout.write(
            f"{name}: {n_scripts} scripts + {n_prompts} prompts copied\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
