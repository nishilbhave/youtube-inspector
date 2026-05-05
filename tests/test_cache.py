"""Unit tests for scripts/cache.py — no network, no LLM."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import cache  # noqa: E402


REPO_ROOT = Path(__file__).parent.parent


# ----------------------------------------------------------------------------
# hash_file
# ----------------------------------------------------------------------------


class TestHashFile:
    def test_known_content(self, tmp_path):
        f = tmp_path / "fixture.txt"
        f.write_bytes(b"hello\n")
        # sha256 of b"hello\n"
        expected = "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"
        assert cache.hash_file(f) == expected

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        # sha256 of empty bytes
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert cache.hash_file(f) == expected

    def test_binary_file(self, tmp_path):
        f = tmp_path / "binary.bin"
        payload = bytes(range(256))
        f.write_bytes(payload)
        expected = hashlib.sha256(payload).hexdigest()
        assert cache.hash_file(f) == expected

    def test_real_prompt_files_hash_stably(self):
        """Hashing a real prompt file twice yields the same digest."""
        prompt = REPO_ROOT / "prompts" / "extract_structure.md"
        if not prompt.exists():
            pytest.skip("extract_structure.md not present")
        h1 = cache.hash_file(prompt)
        h2 = cache.hash_file(prompt)
        assert h1 == h2
        assert len(h1) == 64
        assert all(c in "0123456789abcdef" for c in h1)

    def test_accepts_str_path(self, tmp_path):
        """hash_file accepts both Path and str arguments (ergonomic API)."""
        f = tmp_path / "x.txt"
        f.write_bytes(b"hello\n")
        assert cache.hash_file(str(f)) == cache.hash_file(f)


# ----------------------------------------------------------------------------
# canonical_json
# ----------------------------------------------------------------------------


class TestCanonicalJson:
    def test_simple_object(self):
        assert cache.canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'

    def test_nested_keys_sorted_at_every_level(self):
        obj = {"outer": {"z": 1, "a": 2}, "first": [1, 2, 3]}
        # sort_keys applies recursively
        expected = b'{"first":[1,2,3],"outer":{"a":2,"z":1}}'
        assert cache.canonical_json(obj) == expected

    def test_compact_separators(self):
        # No spaces around : or ,
        out = cache.canonical_json({"a": [1, 2], "b": "c"})
        assert b" " not in out

    def test_unicode_preserved(self):
        # ensure_ascii=False keeps non-ASCII chars verbatim
        obj = {"title": "café — naïve résumé"}
        out = cache.canonical_json(obj)
        assert "café".encode("utf-8") in out
        assert b"\\u" not in out  # no JSON unicode escapes

    def test_order_independence(self):
        a = cache.canonical_json({"a": 1, "b": 2, "c": 3})
        b = cache.canonical_json({"c": 3, "a": 1, "b": 2})
        assert a == b

    def test_arrays_preserve_order(self):
        # Arrays are NOT sorted; only object keys are.
        a = cache.canonical_json([3, 1, 2])
        b = cache.canonical_json([1, 2, 3])
        assert a != b
        assert a == b'[3,1,2]'

    def test_floats_consistent(self):
        # Floats should serialize the same way every time.
        out1 = cache.canonical_json({"x": 1.5, "y": 0.1})
        out2 = cache.canonical_json({"y": 0.1, "x": 1.5})
        assert out1 == out2


# ----------------------------------------------------------------------------
# hash_json
# ----------------------------------------------------------------------------


class TestHashJson:
    def test_deterministic(self):
        obj = {"video_id": "abc12345678", "pass": 1, "data": [1, 2, 3]}
        assert cache.hash_json(obj) == cache.hash_json(obj)

    def test_order_independence(self):
        a = cache.hash_json({"a": 1, "b": 2})
        b = cache.hash_json({"b": 2, "a": 1})
        assert a == b

    def test_locked_algorithm_matches_inline_recipe(self):
        """Spec contract: hash matches the inline `python3 -c` recipe in SKILL.md."""
        obj = {"transcript": {"video_id": "x", "transcript": [{"start": 0.0, "duration": 1.0, "text": "hi"}]}}
        # Reproduce the algorithm by hand to lock the spec.
        s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        expected = hashlib.sha256(s).hexdigest()
        assert cache.hash_json(obj) == expected

    def test_returns_64_lowercase_hex(self):
        h = cache.hash_json({"a": 1})
        assert len(h) == 64
        assert h == h.lower()
        assert all(c in "0123456789abcdef" for c in h)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def _run_cli(*args, stdin: str | None = None):
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "cache.py"), *args]
    return subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


class TestCliHashFile:
    def test_success(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_bytes(b"hello\n")
        result = _run_cli("hash-file", str(f))
        assert result.returncode == 0
        assert result.stdout.strip() == cache.hash_file(f)

    def test_missing_file(self, tmp_path):
        result = _run_cli("hash-file", str(tmp_path / "nope.txt"))
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()


class TestCliHashJson:
    def test_success(self):
        payload = '{"a":1,"b":2}'
        result = _run_cli("hash-json", stdin=payload)
        assert result.returncode == 0
        assert result.stdout.strip() == cache.hash_json({"a": 1, "b": 2})

    def test_invalid_json(self):
        result = _run_cli("hash-json", stdin="not json")
        assert result.returncode == 1
        assert "invalid json" in result.stderr.lower()

    def test_unicode_stdin(self):
        # Unicode round-trips through stdin via UTF-8.
        payload = json.dumps({"title": "café"}, ensure_ascii=False)
        result = _run_cli("hash-json", stdin=payload)
        assert result.returncode == 0
        assert result.stdout.strip() == cache.hash_json({"title": "café"})


class TestCliMissingSubcommand:
    def test_no_args(self):
        result = _run_cli()
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "usage" in result.stderr.lower()
