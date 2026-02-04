"""
Tests for engine/extraction/merging.py — missingness predicate and FieldMerger filter.
"""

import pytest
from engine.extraction.merging import _is_missing, FieldValue, FieldMerger, TrustHierarchy


# ---------------------------------------------------------------------------
# _is_missing unit tests
# ---------------------------------------------------------------------------

class TestIsMissing:
    """_is_missing must treat None, empty/whitespace strings, and known
    placeholders as missing.  Everything else is a real value."""

    # --- should be treated as missing ---
    @pytest.mark.parametrize("value", [
        None,
        "",
        "   ",
        "\t",
        "\n",
        " \t\n ",
        "N/A",
        "n/a",
        "NA",
        "-",
        "\u2013",          # en-dash –
        "\u2014",          # em-dash —
    ])
    def test_missing_values(self, value):
        assert _is_missing(value) is True

    # --- should NOT be treated as missing ---
    @pytest.mark.parametrize("value", [
        "hello",
        "0",
        " real value ",      # has non-whitespace content
        "N/A extra",         # placeholder substring, not exact match
        "-dash",             # starts with dash but is a real value
        0,                   # integer zero
        False,               # boolean False
        [],                  # empty list — not a string sentinel
        {},                  # empty dict — not a string sentinel
    ])
    def test_real_values(self, value):
        assert _is_missing(value) is False


# ---------------------------------------------------------------------------
# FieldMerger integration — empty string no longer blocks a real value
# ---------------------------------------------------------------------------

class TestFieldMergerMissnessFilter:
    """When one source returns "" and another returns a real value,
    the real value must win regardless of source trust order."""

    @pytest.fixture
    def merger(self, tmp_path):
        """FieldMerger backed by a minimal extraction.yaml with two sources."""
        cfg = tmp_path / "extraction.yaml"
        cfg.write_text(
            "trust_levels:\n"
            "  high_trust: 80\n"
            "  low_trust:  40\n"
            "  unknown_source: 10\n"
        )
        th = TrustHierarchy(config_path=str(cfg))
        return FieldMerger(trust_hierarchy=th)

    def test_empty_string_from_high_trust_does_not_block_real_value(self, merger):
        """high_trust returns ""; low_trust returns real text.
        Result must be the real text from low_trust."""
        values = [
            FieldValue(value="", source="high_trust", confidence=0.9),
            FieldValue(value="A great summary", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("summary", values)
        assert result.value == "A great summary"
        assert result.source == "low_trust"

    def test_placeholder_from_high_trust_does_not_block_real_value(self, merger):
        """high_trust returns "N/A"; low_trust returns real text."""
        values = [
            FieldValue(value="N/A", source="high_trust", confidence=0.9),
            FieldValue(value="Useful description", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("description", values)
        assert result.value == "Useful description"
        assert result.source == "low_trust"

    def test_both_missing_yields_none(self, merger):
        """Both sources are missing — result value is None."""
        values = [
            FieldValue(value="", source="high_trust", confidence=0.9),
            FieldValue(value="N/A", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("summary", values)
        assert result.value is None

    def test_real_value_from_high_trust_still_wins(self, merger):
        """Normal case: both have real values, higher trust wins as before."""
        values = [
            FieldValue(value="High trust text", source="high_trust", confidence=0.9),
            FieldValue(value="Low trust text", source="low_trust", confidence=0.8),
        ]
        result = merger.merge_field("summary", values)
        assert result.value == "High trust text"
        assert result.source == "high_trust"
