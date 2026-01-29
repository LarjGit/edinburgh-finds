"""Tests for numeric parser extractor."""
import pytest
from engine.lenses.extractors.numeric_parser import extract_numeric


def test_extract_numeric_from_digit_string():
    """Should extract integer from string with digits."""
    result = extract_numeric("5")
    assert result == 5


def test_extract_numeric_from_text_with_number():
    """Should extract first number from text."""
    result = extract_numeric("The facility has 5 courts available")
    assert result == 5


def test_extract_numeric_from_text_with_multiple_numbers():
    """Should extract first number when multiple present."""
    result = extract_numeric("5 courts and 3 pitches")
    assert result == 5


def test_extract_numeric_returns_none_when_no_number():
    """Should return None when no number found."""
    result = extract_numeric("No numbers here")
    assert result is None
