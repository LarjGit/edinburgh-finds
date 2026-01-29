"""Tests for lens mapping engine."""
import pytest
from engine.lenses.mapping_engine import match_rule_against_entity


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
