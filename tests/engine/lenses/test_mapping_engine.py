"""Tests for lens mapping engine."""
import pytest
from pathlib import Path
from engine.lenses.loader import VerticalLens
from engine.lenses.mapping_engine import match_rule_against_entity, execute_mapping_rules, stabilize_canonical_dimensions, apply_lens_mapping


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


def test_omitted_source_fields_searches_all_default_fields():
    """When source_fields is omitted, should search all default text fields."""
    rule = {
        "pattern": r"(?i)tennis",
        "canonical": "tennis",
        "dimension": "canonical_activities"
        # source_fields intentionally omitted
    }

    # Pattern only appears in description (not in entity_name)
    entity = {
        "entity_name": "The Sports Club",
        "description": "We offer tennis coaching and courts"
    }

    result = match_rule_against_entity(rule, entity)

    # Should match because description is in default source_fields
    assert result is not None
    assert result["dimension"] == "canonical_activities"
    assert result["value"] == "tennis"


def test_explicit_source_fields_narrows_search_surface():
    """When source_fields is explicit, should only search those fields."""
    rule = {
        "pattern": r"(?i)tennis",
        "canonical": "tennis",
        "dimension": "canonical_activities",
        "source_fields": ["entity_name"]  # Explicitly only entity_name
    }

    # Pattern only appears in description (not in entity_name)
    entity = {
        "entity_name": "The Sports Club",
        "description": "We offer tennis coaching and courts"
    }

    result = match_rule_against_entity(rule, entity)

    # Should NOT match because description is excluded
    assert result is None


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


class MockExecutionContext:
    """Mock ExecutionContext for testing."""
    def __init__(self, lens):
        self.lens = lens
        self.source = "serper"


def test_apply_lens_mapping_populates_canonical_dimensions():
    """End-to-end: apply_lens_mapping should populate canonical dimensions."""
    # Load real Edinburgh Finds lens
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    lens = VerticalLens(lens_path)

    # Create entity with raw data
    entity = {
        "entity_name": "Powerleague Padel Edinburgh",
        "description": "Premier sports facility with 5 padel courts",
        "raw_categories": ["Sports Centre", "Leisure Facility"]
    }

    # Create mock context
    ctx = MockExecutionContext(lens)

    # Apply lens mapping
    result = apply_lens_mapping(entity, ctx)

    # Should populate canonical_activities
    assert "canonical_activities" in result
    assert "padel" in result["canonical_activities"]

    # Should populate canonical_place_types
    assert "canonical_place_types" in result
    assert "sports_facility" in result["canonical_place_types"]

    # Should preserve original entity fields
    assert result["entity_name"] == "Powerleague Padel Edinburgh"
