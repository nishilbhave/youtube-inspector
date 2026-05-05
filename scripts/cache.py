#!/usr/bin/env python3
"""cache.py — deterministic hashing for skill cache wrappers.

Part of the youtube-inspector skills. No LLM calls. No network calls.

Centralizes the canonical-JSON serialization and SHA-256 hashing used by
SKILL.md cache protocols (`prompt_hash` and `inputs_hash`) so different host
agents and ad-hoc shell snippets cannot drift apart on the same logical
input.

The locked canonicalization is:

    json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        .encode('utf-8')

then SHA-256 in lowercase hex (64 chars). For raw file content (used by
`prompt_hash`) the hash is over the file bytes verbatim — no normalization.

CLI:
    python3 scripts/cache.py hash-file <path>
        Print the SHA-256 hex of the file's raw bytes.

    python3 scripts/cache.py hash-json
        Read JSON from stdin, print the SHA-256 hex of its canonical form.

Exit codes:
    0  success
    1  usage error / IO error / invalid JSON on stdin
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def hash_file(path: Path | str) -> str:
    """SHA-256 hex of the file's raw bytes. Used for `prompt_hash`."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_json(obj: Any) -> bytes:
    """Canonical JSON serialization: sorted keys, compact separators, UTF-8."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def hash_json(obj: Any) -> str:
    """SHA-256 hex of the canonical-JSON form of obj. Used for `inputs_hash`."""
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def _cmd_hash_file(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        sys.stderr.write(f"cache.py: file not found: {path}\n")
        return 1
    try:
        sys.stdout.write(hash_file(path) + "\n")
    except OSError as e:
        sys.stderr.write(f"cache.py: failed to read {path}: {e}\n")
        return 1
    return 0


def _cmd_hash_json(args: argparse.Namespace) -> int:
    raw = sys.stdin.read()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"cache.py: invalid JSON on stdin: {e}\n")
        return 1
    sys.stdout.write(hash_json(obj) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic hashing for skill cache wrappers."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_file = sub.add_parser("hash-file", help="SHA-256 hex of file bytes")
    p_file.add_argument("path", help="Path to the file to hash")
    p_file.set_defaults(func=_cmd_hash_file)

    p_json = sub.add_parser(
        "hash-json",
        help="SHA-256 hex of canonical-JSON form of stdin",
    )
    p_json.set_defaults(func=_cmd_hash_json)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
