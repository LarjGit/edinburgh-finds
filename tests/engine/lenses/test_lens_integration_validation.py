"""
Direct validation test for lens mapping integration.

Tests the complete extraction pipeline with real lens contract,
verifying canonical dimensions are populated from mapping rules.
"""
import pytest
from pathlib import Path
from engine.lenses.loader import VerticalLens
from tests.engine.extraction.test_helpers import extract_with_lens_for_testing


def test_padel_extraction_populates_canonical_activities():
    """Verify padel-related input populates canonical_activities with 'padel' value."""
    # Arrange
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    lens = VerticalLens(lens_path)

    # Create lens contract (plain dict for engine)
    lens_contract = {
        "facets": lens.facets,
        "values": lens.values,
        "mapping_rules": lens.mapping_rules,
        "modules": lens.config.get("modules", {}),
        "module_triggers": lens.module_triggers
    }

    raw_data = {
        "entity_name": "Powerleague Portobello",
        "description": "Sports facility with 4 padel courts and 5 football pitches",
        "categories": ["Sports Centre", "Recreation"],
        "source": "test"
    }

    # Act
    result = extract_with_lens_for_testing(raw_data, lens_contract)

    # Assert
    assert "canonical_activities" in result
    assert isinstance(result["canonical_activities"], list)
    assert "padel" in result["canonical_activities"], \
        f"Expected 'padel' in canonical_activities, got: {result['canonical_activities']}"

    # entity_class should be set (classifier determines this)
    assert result["entity_class"] in ["place", "organization", "thing"]
    assert len(result["canonical_place_types"]) > 0, "canonical_place_types should not be empty"


def test_sports_facility_extraction_populates_place_types():
    """Verify sports facility category populates canonical_place_types."""
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    lens = VerticalLens(lens_path)

    lens_contract = {
        "facets": lens.facets,
        "values": lens.values,
        "mapping_rules": lens.mapping_rules,
        "modules": lens.config.get("modules", {}),
        "module_triggers": lens.module_triggers
    }

    raw_data = {
        "entity_name": "Edinburgh Sports Centre",
        "description": "Large sports facility with multiple courts",
        "categories": ["Sports Centre"],
        "source": "test"
    }

    result = extract_with_lens_for_testing(raw_data, lens_contract)

    assert "sports_facility" in result["canonical_place_types"], \
        f"Expected 'sports_facility' in canonical_place_types, got: {result['canonical_place_types']}"


def test_multiple_patterns_extracted():
    """Verify entity with multiple patterns gets all canonical values."""
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    lens = VerticalLens(lens_path)

    lens_contract = {
        "facets": lens.facets,
        "values": lens.values,
        "mapping_rules": lens.mapping_rules,
        "modules": lens.config.get("modules", {}),
        "module_triggers": lens.module_triggers
    }

    raw_data = {
        "entity_name": "Padel Edinburgh Sports Centre",
        "description": "Premier padel facility with indoor and outdoor courts",
        "categories": ["Sports Centre", "Leisure Centre"],
        "source": "test"
    }

    result = extract_with_lens_for_testing(raw_data, lens_contract)

    # Should extract padel activity from name/description
    assert "padel" in result["canonical_activities"], \
        f"Expected 'padel' in canonical_activities, got: {result['canonical_activities']}"

    # Should extract sports_facility from categories
    assert "sports_facility" in result["canonical_place_types"], \
        f"Expected 'sports_facility' in canonical_place_types, got: {result['canonical_place_types']}"


def test_canonical_dimensions_stabilized():
    """Verify canonical dimensions are deduplicated and sorted (determinism requirement)."""
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    lens = VerticalLens(lens_path)

    lens_contract = {
        "facets": lens.facets,
        "values": lens.values,
        "mapping_rules": lens.mapping_rules,
        "modules": lens.config.get("modules", {}),
        "module_triggers": lens.module_triggers
    }

    # Create data that might produce duplicate values
    raw_data = {
        "entity_name": "Tennis and Racket Sports Centre",
        "description": "Tennis facility with tennis courts and tennis coaching",
        "categories": ["Tennis", "Sports"],
        "source": "test"
    }

    result = extract_with_lens_for_testing(raw_data, lens_contract)

    activities = result["canonical_activities"]

    # No duplicates
    assert len(activities) == len(set(activities)), \
        f"canonical_activities has duplicates: {activities}"

    # Lexicographically sorted (determinism)
    assert activities == sorted(activities), \
        f"canonical_activities not sorted: {activities}"
