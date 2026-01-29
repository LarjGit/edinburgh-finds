"""Tests for lens mapping engine."""
import pytest
from engine.lenses.mapping_engine import match_rule_against_entity, execute_mapping_rules, stabilize_canonical_dimensions


def test_simple_pattern_match_returns_dimension_and_value():
    """Pattern matching should extract dimension and value from entity."""
    rule = {
        "pattern": r"(?i)padel",
        "canonical": "padel",
        "dimension": "canonical_activities",
        "source_fields": ["entity_name"]
    }
    entity = {"entity_name": "Powerleague Padel Club"}

    result = match_rule_against_entity(rule, entity)

    assert result is not None
    assert result["dimension"] == "canonical_activities"
    assert result["value"] == "padel"


def test_pattern_mismatch_returns_none():
    """Non-matching pattern should return None."""
    rule = {
        "pattern": r"(?i)tennis",
        "canonical": "tennis",
        "dimension": "canonical_activities",
        "source_fields": ["entity_name"]
    }
    entity = {"entity_name": "Padel Club"}

    result = match_rule_against_entity(rule, entity)

    assert result is None


def test_pattern_searches_multiple_source_fields():
    """Pattern should match against union of source_fields."""
    rule = {
        "pattern": r"(?i)leisure centre",
        "canonical": "sports_facility",
        "dimension": "canonical_place_types",
        "source_fields": ["entity_name", "description", "raw_categories"]
    }
    entity = {
        "entity_name": "Powerleague",
        "description": "Premier leisure centre in Edinburgh",
        "raw_categories": []
    }

    result = match_rule_against_entity(rule, entity)

    assert result is not None
    assert result["value"] == "sports_facility"


def test_multiple_rules_append_to_same_dimension():
    """Multiple matching rules should append values to same dimension."""
    rules = [
        {
            "pattern": r"(?i)padel",
            "canonical": "padel",
            "dimension": "canonical_activities",
            "source_fields": ["entity_name"]
        },
        {
            "pattern": r"(?i)tennis",
            "canonical": "tennis",
            "dimension": "canonical_activities",
            "source_fields": ["entity_name"]
        }
    ]
    entity = {"entity_name": "Padel and Tennis Club"}

    result = execute_mapping_rules(rules, entity)

    assert "canonical_activities" in result
    assert "padel" in result["canonical_activities"]
    assert "tennis" in result["canonical_activities"]


def test_first_match_wins_per_rule():
    """First matching source_field should win per rule."""
    rule = {
        "pattern": r"(?i)sports",
        "canonical": "sports_facility",
        "dimension": "canonical_place_types",
        "source_fields": ["entity_name", "description"]
    }
    entity = {
        "entity_name": "Sports Centre Edinburgh",
        "description": "Premier sports facility"
    }

    # Should match entity_name (first field), not description
    result = execute_mapping_rules([rule], entity)

    assert result["canonical_place_types"] == ["sports_facility"]


def test_canonical_dimensions_deduplicated_and_sorted():
    """Dimension values should be deduplicated and lexicographically sorted."""
    dimensions = {
        "canonical_activities": ["tennis", "padel", "tennis", "badminton"],
        "canonical_place_types": []
    }

    result = stabilize_canonical_dimensions(dimensions)

    # Deduplicated
    assert result["canonical_activities"].count("tennis") == 1
    # Sorted lexicographically
    assert result["canonical_activities"] == ["badminton", "padel", "tennis"]
