"""Unit tests for fetch._slug — deterministic title → filename slug."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import fetch  # noqa: E402

SLUG_FORMAT = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TestSlugBasic:
    @pytest.mark.parametrize(
        "title,expected",
        [
            ("Hello World", "hello-world"),
            ("hello world", "hello-world"),
            ("HELLO WORLD", "hello-world"),
            ("Hello   World", "hello-world"),
            ("  Hello World  ", "hello-world"),
            ("hello-world", "hello-world"),
            ("hello_world", "hello-world"),
            ("Hello, World!", "hello-world"),
        ],
    )
    def test_basic_normalization(self, title, expected):
        assert fetch._slug(title) == expected


class TestSlugAccentsAndUnicode:
    @pytest.mark.parametrize(
        "title,expected",
        [
            ("Café", "cafe"),
            ("naïve", "naive"),
            ("Crème brûlée", "creme-brulee"),
            ("résumé", "resume"),
        ],
    )
    def test_accents_transliterated(self, title, expected):
        assert fetch._slug(title) == expected

    def test_emoji_dropped(self):
        assert fetch._slug("Hello 🚀 World") == "hello-world"

    def test_non_latin_dropped(self):
        # Cyrillic, CJK, etc. drop to nothing — fallback applies.
        assert fetch._slug("привет") == "untitled"
        assert fetch._slug("你好") == "untitled"

    def test_mixed_latin_and_non_latin(self):
        assert fetch._slug("Hello 你好 World") == "hello-world"


class TestSlugFallbacks:
    @pytest.mark.parametrize(
        "title",
        ["", "   ", "!!!", "***", "🚀🚀🚀", "...", "---"],
    )
    def test_empty_or_punctuation_only_yields_untitled(self, title):
        assert fetch._slug(title) == "untitled"

    def test_none_input_yields_untitled(self):
        assert fetch._slug(None) == "untitled"  # type: ignore[arg-type]


class TestSlugLength:
    def test_short_titles_pass_through(self):
        assert fetch._slug("ab cd") == "ab-cd"

    def test_truncates_at_word_boundary(self):
        # 70 chars worth of words; should truncate at last `-` ≤ 60.
        title = "the quick brown fox jumps over the lazy dog and then jumps again over"
        result = fetch._slug(title)
        assert len(result) <= 60
        assert not result.endswith("-")
        # Result must still parse as proper slug shape.
        assert SLUG_FORMAT.match(result)

    def test_truncates_long_unbroken_run(self):
        # No dashes in the first 60 chars at all.
        result = fetch._slug("a" * 80)
        assert result == "a" * 60

    def test_at_boundary(self):
        # Exactly 60 chars, no truncation.
        title = "a" + "-b" * 29 + "c"  # 1 + 58 + 1 = 60 chars after slugify
        result = fetch._slug(title)
        assert len(result) <= 60


class TestSlugFormatInvariants:
    @pytest.mark.parametrize(
        "title",
        [
            "Did ChatGPT Just Beat Claude? (NEW MASSIVE UPDATE) 🚀",
            "100+ Web Development Things you Should Know",
            "The Lazy Way I Make Money With AI (2026)",
            "I Earned $1.2M with Claude Code",
            "Hello",
        ],
    )
    def test_output_matches_format(self, title):
        result = fetch._slug(title)
        assert SLUG_FORMAT.match(result), f"bad slug: {result!r}"
        assert len(result) <= 60

    def test_sample_from_design_doc(self):
        title = "Did ChatGPT Just Beat Claude? (NEW MASSIVE UPDATE) 🚀"
        assert fetch._slug(title) == "did-chatgpt-just-beat-claude-new-massive-update"
