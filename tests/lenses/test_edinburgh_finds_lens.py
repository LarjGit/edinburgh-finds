"""
Tests for Edinburgh Finds lens configuration.

Validates that the Edinburgh Finds lens.yaml follows all architectural contracts:
- Loads successfully
- All facets use valid dimension_source
- All values reference existing facets
- All mapping rules reference existing values
- No duplicate values
- Role facet exists and is internal-only
"""

import pytest
from pathlib import Path
from engine.lenses.loader import VerticalLens, LensConfigError
from engine.lenses.validator import ALLOWED_DIMENSION_SOURCES


class TestEdinburghFindsLens:
    """Test suite for Edinburgh Finds lens configuration."""

    @pytest.fixture
    def lens(self):
        """Load Edinburgh Finds lens."""
        lens_path = Path("lenses/edinburgh_finds/lens.yaml")
        if not lens_path.exists():
            pytest.skip(f"Edinburgh Finds lens not found at {lens_path}")
        return VerticalLens(lens_path)

    def test_lens_loads_successfully(self, lens):
        """Edinburgh Finds lens should load without errors."""
        # If we got here, the lens loaded successfully
        assert lens is not None
        assert lens.config is not None

    def test_all_facets_use_valid_dimension_source(self, lens):
        """All facets should use one of the 4 allowed dimension sources."""
        facets = lens.config.get("facets", {})

        for facet_key, facet_config in facets.items():
            dimension_source = facet_config.get("dimension_source")
            assert dimension_source in ALLOWED_DIMENSION_SOURCES, (
                f"Facet '{facet_key}' uses invalid dimension_source '{dimension_source}'. "
                f"Must be one of: {ALLOWED_DIMENSION_SOURCES}"
            )

    def test_all_values_reference_existing_facets(self, lens):
        """All values should reference facets that exist in the facets section."""
        facets = lens.config.get("facets", {})
        values = lens.config.get("values", [])
        facet_keys = set(facets.keys())

        for value in values:
            value_key = value.get("key")
            facet_ref = value.get("facet")
            assert facet_ref in facet_keys, (
                f"Value '{value_key}' references non-existent facet '{facet_ref}'. "
                f"Available facets: {facet_keys}"
            )

    def test_all_mapping_rules_reference_existing_values(self, lens):
        """All mapping rules should reference values that exist in the values section."""
        values = lens.config.get("values", [])
        mapping_rules = lens.config.get("mapping_rules", [])
        value_keys = {value.get("key") for value in values}

        for rule in mapping_rules:
            canonical = rule.get("canonical")
            raw_values = rule.get("raw", [])
            assert canonical in value_keys, (
                f"Mapping rule for {raw_values} references non-existent value '{canonical}'. "
                f"Available values: {value_keys}"
            )

    def test_no_duplicate_values(self, lens):
        """All value keys should be unique."""
        values = lens.config.get("values", [])
        value_keys = [value.get("key") for value in values]

        # Check for duplicates
        seen = set()
        duplicates = []
        for key in value_keys:
            if key in seen:
                duplicates.append(key)
            else:
                seen.add(key)

        assert len(duplicates) == 0, (
            f"Duplicate value keys found: {duplicates}"
        )

    def test_role_facet_exists_and_is_internal_only(self, lens):
        """Edinburgh Finds should have a 'role' facet that is internal-only."""
        facets = lens.config.get("facets", {})

        # Check role facet exists
        assert "role" in facets, "Edinburgh Finds lens should have a 'role' facet"

        role_facet = facets["role"]

        # Check it maps to canonical_roles dimension
        assert role_facet.get("dimension_source") == "canonical_roles", (
            "Role facet should map to canonical_roles dimension"
        )

        # Check it's internal-only (not shown in UI)
        # Internal facets should have show_in_filters=false and show_in_navigation=false
        assert role_facet.get("show_in_filters") == False, (
            "Role facet should not be shown in filters (internal-only)"
        )
        assert role_facet.get("show_in_navigation") == False, (
            "Role facet should not be shown in navigation (internal-only)"
        )

    def test_all_four_dimension_sources_used(self, lens):
        """Edinburgh Finds should use all 4 dimension sources."""
        facets = lens.config.get("facets", {})
        used_dimensions = {
            facet_config.get("dimension_source")
            for facet_config in facets.values()
        }

        # Edinburgh Finds should use all 4 dimensions
        assert used_dimensions == ALLOWED_DIMENSION_SOURCES, (
            f"Edinburgh Finds should use all 4 dimension sources. "
            f"Used: {used_dimensions}, Expected: {ALLOWED_DIMENSION_SOURCES}"
        )

    def test_facet_keys_match_expected(self, lens):
        """Edinburgh Finds should have expected facet keys."""
        facets = lens.config.get("facets", {})
        facet_keys = set(facets.keys())

        expected_facets = {"activity", "role", "place_type", "access"}
        assert facet_keys == expected_facets, (
            f"Edinburgh Finds facets don't match expected. "
            f"Got: {facet_keys}, Expected: {expected_facets}"
        )

    def test_all_values_have_required_fields(self, lens):
        """All values should have required fields: key, facet, display_name."""
        values = lens.config.get("values", [])

        for value in values:
            value_key = value.get("key")
            assert value_key is not None, "Value missing 'key' field"
            assert value.get("facet") is not None, f"Value '{value_key}' missing 'facet' field"
            assert value.get("display_name") is not None, f"Value '{value_key}' missing 'display_name' field"
