"""Tests for normalizers."""
import pytest
from engine.lenses.extractors.normalizers import (
    normalize_trim,
    normalize_round_integer,
    normalize_lowercase,
    apply_normalizers
)


def test_normalize_trim_removes_whitespace():
    """Should remove leading and trailing whitespace."""
    assert normalize_trim("  hello  ") == "hello"
    assert normalize_trim("\n\tworld\n") == "world"


def test_normalize_round_integer_converts_to_int():
    """Should convert numeric values to integers."""
    assert normalize_round_integer(5.7) == 5
    assert normalize_round_integer("5") == 5
    assert normalize_round_integer("5.9") == 5


def test_normalize_lowercase_converts_to_lower():
    """Should convert string to lowercase."""
    assert normalize_lowercase("HELLO") == "hello"
    assert normalize_lowercase("MiXeD") == "mixed"


def test_apply_normalizers_executes_pipeline():
    """Should apply normalizers in left-to-right order."""
    value = "  5.7  "
    normalizers = ["trim", "round_integer"]

    result = apply_normalizers(value, normalizers)

    assert result == 5
