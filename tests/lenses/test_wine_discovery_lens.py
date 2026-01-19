"""
Tests for Wine Discovery lens configuration.

Validates that the Wine Discovery lens.yaml follows all architectural contracts:
- Loads successfully
- wine_type facet maps to canonical_activities
- venue_type facet maps to canonical_place_types
- All contracts validated
"""

import pytest
from pathlib import Path
from engine.lenses.loader import VerticalLens, LensConfigError
from engine.lenses.validator import ALLOWED_DIMENSION_SOURCES


class TestWineDiscoveryLens:
    """Test suite for Wine Discovery lens configuration."""

    @pytest.fixture
    def lens(self):
        """Load Wine Discovery lens."""
        lens_path = Path("lenses/wine_discovery/lens.yaml")
        if not lens_path.exists():
            pytest.skip(f"Wine Discovery lens not found at {lens_path}")
        return VerticalLens(lens_path)

    def test_lens_loads_successfully(self, lens):
        """Wine Discovery lens should load without errors."""
        # If we got here, the lens loaded successfully
        assert lens is not None
        assert lens.config is not None

    def test_wine_type_facet_maps_to_canonical_activities(self, lens):
        """The wine_type facet should map to canonical_activities dimension."""
        facets = lens.config.get("facets", {})

        assert "wine_type" in facets, "Wine Discovery lens should have a 'wine_type' facet"

        wine_type_facet = facets["wine_type"]
        assert wine_type_facet.get("dimension_source") == "canonical_activities", (
            "wine_type facet should map to canonical_activities dimension"
        )

    def test_venue_type_facet_maps_to_canonical_place_types(self, lens):
        """The venue_type facet should map to canonical_place_types dimension."""
        facets = lens.config.get("facets", {})

        assert "venue_type" in facets, "Wine Discovery lens should have a 'venue_type' facet"

        venue_type_facet = facets["venue_type"]
        assert venue_type_facet.get("dimension_source") == "canonical_place_types", (
            "venue_type facet should map to canonical_place_types dimension"
        )

    def test_all_contracts_validated(self, lens):
        """All architectural contracts should be validated during lens loading."""
        # CONTRACT 1: All facets use valid dimension_source
        facets = lens.config.get("facets", {})
        for facet_key, facet_config in facets.items():
            dimension_source = facet_config.get("dimension_source")
            assert dimension_source in ALLOWED_DIMENSION_SOURCES, (
                f"Facet '{facet_key}' uses invalid dimension_source '{dimension_source}'"
            )

        # CONTRACT 2: All values reference existing facets
        values = lens.config.get("values", [])
        facet_keys = set(facets.keys())
        for value in values:
            value_key = value.get("key")
            facet_ref = value.get("facet")
            assert facet_ref in facet_keys, (
                f"Value '{value_key}' references non-existent facet '{facet_ref}'"
            )

        # CONTRACT 3: All mapping rules reference existing values
        mapping_rules = lens.config.get("mapping_rules", [])
        value_keys = {value.get("key") for value in values}
        for rule in mapping_rules:
            canonical = rule.get("canonical")
            assert canonical in value_keys, (
                f"Mapping rule references non-existent value '{canonical}'"
            )

        # CONTRACT 4: No duplicate value keys
        value_key_list = [value.get("key") for value in values]
        assert len(value_key_list) == len(set(value_key_list)), (
            f"Duplicate value keys found in Wine Discovery lens"
        )

    def test_role_facet_exists_and_is_internal_only(self, lens):
        """Wine Discovery should have a 'role' facet that is internal-only."""
        facets = lens.config.get("facets", {})

        # Check role facet exists
        assert "role" in facets, "Wine Discovery lens should have a 'role' facet"

        role_facet = facets["role"]

        # Check it maps to canonical_roles dimension
        assert role_facet.get("dimension_source") == "canonical_roles", (
            "Role facet should map to canonical_roles dimension"
        )

        # Check it's internal-only (not shown in UI)
        assert role_facet.get("show_in_filters") == False, (
            "Role facet should not be shown in filters (internal-only)"
        )
        assert role_facet.get("show_in_navigation") == False, (
            "Role facet should not be shown in navigation (internal-only)"
        )

    def test_all_values_reference_valid_facets(self, lens):
        """All values should reference facets defined in the Wine Discovery lens."""
        facets = lens.config.get("facets", {})
        values = lens.config.get("values", [])
        facet_keys = set(facets.keys())

        # Expected facets in Wine Discovery lens
        expected_facets = {"wine_type", "role", "venue_type", "access"}
        assert facet_keys == expected_facets, (
            f"Wine Discovery facets don't match expected. "
            f"Got: {facet_keys}, Expected: {expected_facets}"
        )

        # Check all values reference one of these facets
        for value in values:
            value_key = value.get("key")
            facet_ref = value.get("facet")
            assert facet_ref in facet_keys, (
                f"Value '{value_key}' references non-existent facet '{facet_ref}'. "
                f"Available facets: {facet_keys}"
            )

    def test_demonstrates_dimension_reuse(self, lens):
        """Wine Discovery demonstrates dimension reuse with different facet names."""
        facets = lens.config.get("facets", {})

        # wine_type facet reuses canonical_activities dimension
        assert facets["wine_type"]["dimension_source"] == "canonical_activities", (
            "wine_type should reuse canonical_activities dimension"
        )

        # venue_type facet reuses canonical_place_types dimension
        assert facets["venue_type"]["dimension_source"] == "canonical_place_types", (
            "venue_type should reuse canonical_place_types dimension"
        )

        # This demonstrates the lens abstraction: different vertical (wine) reuses
        # the same universal engine dimensions with different facet names/semantics
