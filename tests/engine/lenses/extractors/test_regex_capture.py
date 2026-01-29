"""Tests for regex capture extractor."""
import pytest
from engine.lenses.extractors.regex_capture import extract_regex_capture


def test_extract_regex_capture_returns_first_group():
    """Should return first captured group."""
    pattern = r"(?i)(\d+)\s*padel\s*courts?"
    text = "The facility has 5 padel courts"

    result = extract_regex_capture(text, pattern)

    assert result == "5"


def test_extract_regex_capture_returns_none_on_no_match():
    """Should return None when pattern doesn't match."""
    pattern = r"(\d+)\s*tennis\s*courts?"
    text = "Padel facility"

    result = extract_regex_capture(text, pattern)

    assert result is None


def test_extract_regex_capture_case_insensitive():
    """Should support case-insensitive matching."""
    pattern = r"(?i)(\d+)\s*PADEL\s*courts?"
    text = "5 padel courts available"

    result = extract_regex_capture(text, pattern)

    assert result == "5"
