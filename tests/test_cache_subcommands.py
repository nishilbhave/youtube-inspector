"""Unit tests for cache.py read/write/verify-quotes subcommands."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import cache  # noqa: E402


REPO_ROOT = Path(__file__).parent.parent
PROMPT_PATH = REPO_ROOT / "prompts" / "extract_structure.md"


def _run_cli(*args, stdin: str | None = None):
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "cache.py"), *args]
    return subprocess.run(
        cmd, input=stdin, capture_output=True, text=True, check=False
    )


# ----------------------------------------------------------------------------
# write + read round-trip
# ----------------------------------------------------------------------------


class TestReadWriteRoundTrip:
    def test_write_then_read_returns_same_output(self, tmp_path):
        inputs = {"transcript": {"video_id": "abc", "transcript": []}}
        output = {"video_id": "abc", "sections": [{"id": "s1", "type": "hook"}]}
        payload = json.dumps({"inputs": inputs, "output": output})
        write_result = _run_cli(
            "write", "1", "abc11charsxx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path), stdin=payload,
        )
        assert write_result.returncode == 0
        written_path = Path(write_result.stdout.strip())
        assert written_path.exists()
        assert written_path == tmp_path / "abc11charsxx-pass1.json"

        read_result = _run_cli(
            "read", "1", "abc11charsxx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path), stdin=json.dumps(inputs),
        )
        assert read_result.returncode == 0
        assert json.loads(read_result.stdout) == output

    def test_write_pass3_thumbnail_json_roundtrips(self, tmp_path):
        inputs = {"metadata": {"title": "x", "channel": "y", "thumbnail_sha256": "abc"}}
        output = {
            "video_id": "thumb11charsx",
            "vision_available": True,
            "text_overlays": ["$10K/DAY"],
            "deception_signals": [{"signal": "extreme number", "severity": "HIGH"}],
        }
        prompt_path = REPO_ROOT / "prompts" / "extract_thumbnail.md"
        wr = _run_cli(
            "write", "3", "thumb11charsx", str(prompt_path),
            "--cache-dir", str(tmp_path),
            stdin=json.dumps({"inputs": inputs, "output": output}),
        )
        assert wr.returncode == 0
        written = Path(wr.stdout.strip())
        assert written == tmp_path / "thumb11charsx-pass3.json"

        rr = _run_cli(
            "read", "3", "thumb11charsx", str(prompt_path),
            "--cache-dir", str(tmp_path), stdin=json.dumps(inputs),
        )
        assert rr.returncode == 0
        assert json.loads(rr.stdout) == output

    def test_write_pass4_string_output_roundtrips(self, tmp_path):
        inputs = {
            "metadata": {"title": "x"},
            "pass1": {},
            "pass2": {},
            "passthumb": {"vision_available": False},
        }
        output = "VERDICT: WATCH [9/10]\n\nfull report markdown"
        payload = json.dumps({"inputs": inputs, "output": output})
        prompt_path = REPO_ROOT / "prompts" / "generate_verdict.md"
        wr = _run_cli(
            "write", "4", "verdict11xxx", str(prompt_path),
            "--cache-dir", str(tmp_path), stdin=payload,
        )
        assert wr.returncode == 0
        written = Path(wr.stdout.strip())
        assert written == tmp_path / "verdict11xxx-pass4.json"

        rr = _run_cli(
            "read", "4", "verdict11xxx", str(prompt_path),
            "--cache-dir", str(tmp_path), stdin=json.dumps(inputs),
        )
        assert rr.returncode == 0
        # String output is printed as-is, with a trailing newline if missing.
        assert rr.stdout.rstrip("\n") == output

    def test_unicode_inputs_roundtrip(self, tmp_path):
        inputs = {"transcript": {"title": "café — naïve"}}
        output = {"video_id": "u1", "summary": "résumé"}
        payload = json.dumps(
            {"inputs": inputs, "output": output}, ensure_ascii=False
        )
        wr = _run_cli(
            "write", "1", "unicode11xx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path), stdin=payload,
        )
        assert wr.returncode == 0

        rr = _run_cli(
            "read", "1", "unicode11xx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path),
            stdin=json.dumps(inputs, ensure_ascii=False),
        )
        assert rr.returncode == 0
        assert json.loads(rr.stdout) == output


# ----------------------------------------------------------------------------
# read miss paths
# ----------------------------------------------------------------------------


class TestReadMisses:
    def test_not_found(self, tmp_path):
        result = _run_cli(
            "read", "1", "missing11xxx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path), stdin='{"transcript": {}}',
        )
        assert result.returncode == 1
        assert result.stderr.strip() == "not-found"

    def test_inputs_mismatch(self, tmp_path):
        # Write with one inputs object
        inputs1 = {"transcript": {"a": 1}}
        wr = _run_cli(
            "write", "1", "abc11charsxx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path),
            stdin=json.dumps({"inputs": inputs1, "output": {}}),
        )
        assert wr.returncode == 0

        # Read with a different inputs object → inputs-mismatch
        inputs2 = {"transcript": {"a": 2}}
        rr = _run_cli(
            "read", "1", "abc11charsxx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path), stdin=json.dumps(inputs2),
        )
        assert rr.returncode == 1
        assert rr.stderr.strip() == "inputs-mismatch"

    def test_prompt_mismatch(self, tmp_path):
        # Write with one prompt path
        wr = _run_cli(
            "write", "1", "abc11charsxx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path),
            stdin=json.dumps({"inputs": {"x": 1}, "output": {}}),
        )
        assert wr.returncode == 0

        # Read with a different prompt → prompt-mismatch
        other_prompt = REPO_ROOT / "prompts" / "inventory_claims.md"
        rr = _run_cli(
            "read", "1", "abc11charsxx", str(other_prompt),
            "--cache-dir", str(tmp_path), stdin=json.dumps({"x": 1}),
        )
        assert rr.returncode == 1
        assert rr.stderr.strip() == "prompt-mismatch"

    def test_corrupt_json(self, tmp_path):
        cache_file = tmp_path / "abc11charsxx-pass1.json"
        cache_file.write_text("not json", encoding="utf-8")
        rr = _run_cli(
            "read", "1", "abc11charsxx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path), stdin='{"x":1}',
        )
        assert rr.returncode == 1
        assert rr.stderr.strip() == "corrupt"

    def test_field_missing(self, tmp_path):
        cache_file = tmp_path / "abc11charsxx-pass1.json"
        cache_file.write_text(
            json.dumps({"video_id": "abc11charsxx", "pass": 1}),
            encoding="utf-8",
        )
        rr = _run_cli(
            "read", "1", "abc11charsxx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path), stdin='{"x":1}',
        )
        assert rr.returncode == 1
        assert rr.stderr.strip() == "field-missing"


# ----------------------------------------------------------------------------
# write input validation
# ----------------------------------------------------------------------------


class TestWriteValidation:
    def test_missing_inputs_key(self, tmp_path):
        wr = _run_cli(
            "write", "1", "x11xxxxxxxx", str(PROMPT_PATH),
            "--cache-dir", str(tmp_path),
            stdin='{"output": {}}',
        )
        assert wr.returncode == 1
        assert "inputs" in wr.stderr.lower()

    def test_missing_prompt_file(self, tmp_path):
        wr = _run_cli(
            "write", "1", "x11xxxxxxxx", str(tmp_path / "nope.md"),
            "--cache-dir", str(tmp_path),
            stdin='{"inputs": {}, "output": {}}',
        )
        assert wr.returncode == 1
        assert "not found" in wr.stderr.lower()


# ----------------------------------------------------------------------------
# verify-quotes
# ----------------------------------------------------------------------------


def _make_transcript_cache(tmp_path: Path, video_id: str, segments: list[dict]) -> None:
    cache_dir = tmp_path
    payload = {
        "video_id": video_id,
        "title": "test",
        "duration_seconds": 60,
        "transcript": segments,
    }
    (cache_dir / f"{video_id}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


class TestVerifyQuotes:
    def test_all_quotes_verbatim_passes(self, tmp_path):
        _make_transcript_cache(
            tmp_path, "v11charsabcd",
            [
                {"start": 0, "duration": 2, "text": "Hello world"},
                {"start": 2, "duration": 2, "text": "Goodnight moon"},
            ],
        )
        pass2 = {
            "video_id": "v11charsabcd",
            "by_section": {
                "s1": {
                    "concrete_claims": [
                        {"timestamp": "0:00", "quote": "Hello world"},
                    ],
                    "vague_claims": [],
                    "evidence_shown": [],
                    "pitches": [
                        {"timestamp": "0:02", "quote": "Goodnight moon"},
                    ],
                }
            },
        }
        result = _run_cli(
            "verify-quotes", "v11charsabcd",
            "--cache-dir", str(tmp_path),
            stdin=json.dumps(pass2),
        )
        assert result.returncode == 0
        assert result.stderr == ""

    def test_one_bad_quote_fails(self, tmp_path):
        _make_transcript_cache(
            tmp_path, "v11charsabcd",
            [{"start": 0, "duration": 2, "text": "Hello world"}],
        )
        pass2 = {
            "video_id": "v11charsabcd",
            "by_section": {
                "s1": {
                    "concrete_claims": [
                        {"timestamp": "0:00", "quote": "Hello world"},
                        {"timestamp": "0:01", "quote": "Not in transcript"},
                    ],
                    "vague_claims": [],
                    "evidence_shown": [],
                    "pitches": [],
                }
            },
        }
        result = _run_cli(
            "verify-quotes", "v11charsabcd",
            "--cache-dir", str(tmp_path),
            stdin=json.dumps(pass2),
        )
        assert result.returncode == 1
        assert "Not in transcript" in result.stderr
        assert "1 mismatch" in result.stderr

    def test_missing_transcript_cache_fails(self, tmp_path):
        result = _run_cli(
            "verify-quotes", "missing11xxx",
            "--cache-dir", str(tmp_path),
            stdin='{"by_section": {}}',
        )
        assert result.returncode == 1
        assert "transcript not found" in result.stderr.lower()

    def test_empty_pass2_passes(self, tmp_path):
        """No quotes to check = vacuously true."""
        _make_transcript_cache(
            tmp_path, "v11charsabcd",
            [{"start": 0, "duration": 2, "text": "anything"}],
        )
        result = _run_cli(
            "verify-quotes", "v11charsabcd",
            "--cache-dir", str(tmp_path),
            stdin='{"video_id":"v11charsabcd","by_section":{}}',
        )
        assert result.returncode == 0


# ----------------------------------------------------------------------------
# Module-level API (covers hosts that import rather than shell out)
# ----------------------------------------------------------------------------


class TestModuleAPI:
    def test_read_cache_module(self, tmp_path):
        inputs = {"transcript": {"x": 1}}
        output = {"video_id": "abc", "result": 42}
        cache.write_cache(
            "abc11charsxx", 1, PROMPT_PATH, inputs, output, cache_dir=tmp_path
        )
        got, reason = cache.read_cache(
            "abc11charsxx", 1, PROMPT_PATH, inputs, cache_dir=tmp_path
        )
        assert reason == "hit"
        assert got == output

    def test_read_cache_miss_reason(self, tmp_path):
        got, reason = cache.read_cache(
            "missing11xxx", 1, PROMPT_PATH, {}, cache_dir=tmp_path
        )
        assert got is None
        assert reason == "not-found"

    def test_verify_quotes_returns_mismatches_list(self, tmp_path):
        _make_transcript_cache(
            tmp_path, "v11charsabcd",
            [{"start": 0, "duration": 2, "text": "Hello"}],
        )
        bad_pass2 = {
            "video_id": "v11charsabcd",
            "by_section": {
                "s1": {
                    "concrete_claims": [{"timestamp": "0:00", "quote": "Bye"}],
                }
            },
        }
        mismatches = cache.verify_quotes(bad_pass2, "v11charsabcd", cache_dir=tmp_path)
        assert len(mismatches) == 1
        assert "Bye" in mismatches[0]
