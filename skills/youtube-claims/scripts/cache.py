#!/usr/bin/env python3
"""cache.py — deterministic hashing and pass-cache I/O for skill cache wrappers.

Part of the youtube-inspector skills. No LLM calls. No network calls.

Centralizes the canonical-JSON serialization and SHA-256 hashing used by
SKILL.md cache protocols (`prompt_hash` and `inputs_hash`) so different host
agents and ad-hoc shell snippets cannot drift apart on the same logical
input.

Also provides the cache wrapper read/write/verify-quotes operations that
SKILL.md previously asked the agent to implement via inline Python heredocs.

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

    python3 scripts/cache.py read <pass> <video_id> <prompt-path> [--cache-dir DIR]
        Read canonical inputs JSON from stdin. If a matching cache wrapper
        exists at ~/youtube-reports/.cache/{video_id}-pass{N}.json, print its
        `output` field to stdout (JSON for pass 1/2, raw string for pass 3)
        and exit 0. On miss, print a one-word reason to stderr (`not-found`,
        `corrupt`, `prompt-mismatch`, `inputs-mismatch`, `field-missing`,
        `wrong-pass`, `wrong-video`) and exit 1.

    python3 scripts/cache.py write <pass> <video_id> <prompt-path> [--cache-dir DIR]
        Read JSON `{"inputs": <canonical>, "output": <pass output>}` from
        stdin. Compute prompt+inputs hashes, write the cache wrapper file
        with all required fields (video_id, pass, prompt_hash, inputs_hash,
        output, produced_at). Print the absolute path written to stdout.

    python3 scripts/cache.py verify-quotes <video_id> [--cache-dir DIR]
        Read Pass 2 output JSON from stdin (`{video_id, by_section}`).
        Substring-check every `quote` field across all `concrete_claims`,
        `vague_claims`, `evidence_shown`, and `pitches` against the
        transcript at ~/youtube-reports/.cache/{video_id}.json. Exit 0 if
        every quote is found. Exit 1 if any quote is missing; print one
        line per mismatch to stderr ("[ts] section.field: <quote>") and
        a final summary line.

Exit codes:
    0  success
    1  usage error / IO error / invalid JSON / cache miss / verification failure
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR = Path.home() / "youtube-reports" / ".cache"


# ----------------------------------------------------------------------------
# Hashing primitives — public API used by tests and (optionally) by hosts.
# ----------------------------------------------------------------------------


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


# ----------------------------------------------------------------------------
# Pass cache I/O — wraps the file-layout convention shared by all 4 skills.
# ----------------------------------------------------------------------------


REQUIRED_FIELDS = ("video_id", "pass", "prompt_hash", "inputs_hash", "output")


def cache_path(video_id: str, pass_n: int, cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    return cache_dir / f"{video_id}-pass{pass_n}.json"


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_cache(
    video_id: str,
    pass_n: int,
    prompt_path: Path,
    inputs_obj: Any,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> tuple[Any, str]:
    """Look up a cache wrapper. Returns (output, "hit") or (None, reason)."""
    path = cache_path(video_id, pass_n, cache_dir)
    if not path.exists():
        return None, "not-found"
    try:
        wrapper = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "corrupt"
    if not isinstance(wrapper, dict):
        return None, "corrupt"
    for field in REQUIRED_FIELDS:
        if field not in wrapper:
            return None, "field-missing"
    if wrapper["video_id"] != video_id:
        return None, "wrong-video"
    if wrapper["pass"] != pass_n:
        return None, "wrong-pass"
    if wrapper["prompt_hash"] != hash_file(prompt_path):
        return None, "prompt-mismatch"
    if wrapper["inputs_hash"] != hash_json(inputs_obj):
        return None, "inputs-mismatch"
    return wrapper["output"], "hit"


def write_cache(
    video_id: str,
    pass_n: int,
    prompt_path: Path,
    inputs_obj: Any,
    output: Any,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Path:
    """Write a cache wrapper. Returns the absolute path written."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(video_id, pass_n, cache_dir)
    wrapper = {
        "video_id": video_id,
        "pass": pass_n,
        "prompt_hash": hash_file(prompt_path),
        "inputs_hash": hash_json(inputs_obj),
        "output": output,
        "produced_at": _utc_now_iso(),
    }
    path.write_text(
        json.dumps(wrapper, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


# ----------------------------------------------------------------------------
# Pass 2 quote verification — substring-check against the transcript cache.
# ----------------------------------------------------------------------------


QUOTE_BUCKETS = ("concrete_claims", "vague_claims", "evidence_shown", "pitches")


def verify_quotes(
    pass2_output: Any,
    video_id: str,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> list[str]:
    """Return a list of mismatch lines. Empty list = all quotes verbatim."""
    transcript_path = cache_dir / f"{video_id}.json"
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    full_text = " ".join(seg["text"] for seg in transcript["transcript"])
    mismatches: list[str] = []
    by_section = pass2_output.get("by_section", {}) if isinstance(pass2_output, dict) else {}
    for section_id, section in by_section.items():
        if not isinstance(section, dict):
            continue
        for bucket in QUOTE_BUCKETS:
            for item in section.get(bucket, []) or []:
                quote = item.get("quote", "") if isinstance(item, dict) else ""
                ts = item.get("timestamp", "?") if isinstance(item, dict) else "?"
                if quote and quote not in full_text:
                    mismatches.append(f"[{ts}] {section_id}.{bucket}: {quote!r}")
    return mismatches


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


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


def _cmd_read(args: argparse.Namespace) -> int:
    prompt_path = Path(args.prompt_path)
    if not prompt_path.exists():
        sys.stderr.write(f"cache.py: prompt not found: {prompt_path}\n")
        return 1
    raw = sys.stdin.read()
    try:
        inputs_obj = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"cache.py: invalid JSON on stdin: {e}\n")
        return 1
    output, reason = read_cache(
        args.video_id,
        args.pass_n,
        prompt_path,
        inputs_obj,
        cache_dir=args.cache_dir,
    )
    if reason != "hit":
        sys.stderr.write(reason + "\n")
        return 1
    if isinstance(output, str):
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
    else:
        sys.stdout.write(json.dumps(output, ensure_ascii=False))
        sys.stdout.write("\n")
    return 0


def _cmd_write(args: argparse.Namespace) -> int:
    prompt_path = Path(args.prompt_path)
    if not prompt_path.exists():
        sys.stderr.write(f"cache.py: prompt not found: {prompt_path}\n")
        return 1
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"cache.py: invalid JSON on stdin: {e}\n")
        return 1
    if not isinstance(payload, dict) or "inputs" not in payload or "output" not in payload:
        sys.stderr.write(
            "cache.py: stdin must be a JSON object with `inputs` and `output` keys\n"
        )
        return 1
    written = write_cache(
        args.video_id,
        args.pass_n,
        prompt_path,
        payload["inputs"],
        payload["output"],
        cache_dir=args.cache_dir,
    )
    sys.stdout.write(str(written) + "\n")
    return 0


def _cmd_verify_quotes(args: argparse.Namespace) -> int:
    transcript_path = args.cache_dir / f"{args.video_id}.json"
    if not transcript_path.exists():
        sys.stderr.write(f"cache.py: transcript not found at {transcript_path}\n")
        return 1
    raw = sys.stdin.read()
    try:
        pass2 = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"cache.py: invalid JSON on stdin: {e}\n")
        return 1
    try:
        mismatches = verify_quotes(pass2, args.video_id, cache_dir=args.cache_dir)
    except (OSError, KeyError, json.JSONDecodeError) as e:
        sys.stderr.write(f"cache.py: failed to verify quotes: {e}\n")
        return 1
    if mismatches:
        for line in mismatches:
            sys.stderr.write(line + "\n")
        sys.stderr.write(f"verify-quotes: {len(mismatches)} mismatch(es)\n")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic hashing and pass-cache I/O for skill cache wrappers."
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

    p_read = sub.add_parser(
        "read",
        help="Read pass cache; print output on hit, exit 1 on miss",
    )
    p_read.add_argument("pass_n", type=int, choices=[1, 2, 3], help="Pass number (1, 2, or 3)")
    p_read.add_argument("video_id", help="11-char YouTube video ID")
    p_read.add_argument("prompt_path", help="Path to the prompt file used by this pass")
    p_read.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Override the cache directory (default: ~/youtube-reports/.cache)",
    )
    p_read.set_defaults(func=_cmd_read)

    p_write = sub.add_parser(
        "write",
        help="Write pass cache wrapper; stdin = {inputs, output}",
    )
    p_write.add_argument("pass_n", type=int, choices=[1, 2, 3])
    p_write.add_argument("video_id")
    p_write.add_argument("prompt_path")
    p_write.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
    )
    p_write.set_defaults(func=_cmd_write)

    p_verify = sub.add_parser(
        "verify-quotes",
        help="Substring-check every Pass 2 quote against the transcript cache",
    )
    p_verify.add_argument("video_id")
    p_verify.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
    )
    p_verify.set_defaults(func=_cmd_verify_quotes)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
