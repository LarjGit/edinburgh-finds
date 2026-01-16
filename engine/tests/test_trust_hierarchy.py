"""
Tests for trust hierarchy loading and management.

The trust hierarchy determines which source's data takes precedence when merging
conflicting fields from multiple sources.

Trust levels (higher = more trusted):
- manual_override: 100 (manually curated data)
- sport_scotland: 90 (official government data)
- edinburgh_council: 85 (official council data)
- google_places: 70 (commercial aggregator)
- serper: 50 (web search results)
- osm: 40 (open community data)
- open_charge_map: 40 (open community data)
- unknown_source: 10 (fallback)
"""

import pytest
from engine.extraction.merging import TrustHierarchy


class TestTrustHierarchy:
    """Test trust hierarchy loading and querying."""

    def test_load_trust_hierarchy_from_config(self):
        """Should load trust levels from extraction.yaml"""
        hierarchy = TrustHierarchy()

        # Check that trust levels are loaded
        assert hierarchy.get_trust_level("manual_override") == 100
        assert hierarchy.get_trust_level("sport_scotland") == 90
        assert hierarchy.get_trust_level("edinburgh_council") == 85
        assert hierarchy.get_trust_level("google_places") == 70
        assert hierarchy.get_trust_level("serper") == 50
        assert hierarchy.get_trust_level("osm") == 40
        assert hierarchy.get_trust_level("open_charge_map") == 40

    def test_get_trust_level_unknown_source(self):
        """Should return default trust level for unknown sources."""
        hierarchy = TrustHierarchy()

        # Unknown source should get low default trust
        assert hierarchy.get_trust_level("unknown_source_xyz") == 10

    def test_compare_trust_levels(self):
        """Should correctly compare trust levels between sources."""
        hierarchy = TrustHierarchy()

        # Higher trust should win
        assert hierarchy.is_more_trusted("manual_override", "google_places") is True
        assert hierarchy.is_more_trusted("sport_scotland", "osm") is True
        assert hierarchy.is_more_trusted("edinburgh_council", "serper") is True

        # Lower trust should not win
        assert hierarchy.is_more_trusted("osm", "google_places") is False
        assert hierarchy.is_more_trusted("serper", "sport_scotland") is False

    def test_equal_trust_levels(self):
        """Should handle equal trust levels."""
        hierarchy = TrustHierarchy()

        # Same source
        assert hierarchy.is_more_trusted("osm", "osm") is False

        # Different sources with same trust level
        assert hierarchy.is_more_trusted("osm", "open_charge_map") is False
        assert hierarchy.is_more_trusted("open_charge_map", "osm") is False

    def test_get_highest_trust_source(self):
        """Should identify the source with highest trust from a list."""
        hierarchy = TrustHierarchy()

        sources = ["serper", "google_places", "osm"]
        highest = hierarchy.get_highest_trust_source(sources)

        assert highest == "google_places"  # 70 > 50 > 40

    def test_get_highest_trust_source_with_manual_override(self):
        """Manual override should always win."""
        hierarchy = TrustHierarchy()

        sources = ["manual_override", "sport_scotland", "google_places"]
        highest = hierarchy.get_highest_trust_source(sources)

        assert highest == "manual_override"

    def test_get_highest_trust_source_empty_list(self):
        """Should handle empty source list."""
        hierarchy = TrustHierarchy()

        result = hierarchy.get_highest_trust_source([])

        assert result is None

    def test_get_highest_trust_source_single_source(self):
        """Should return the only source if list has one element."""
        hierarchy = TrustHierarchy()

        result = hierarchy.get_highest_trust_source(["osm"])

        assert result == "osm"

    def test_sort_sources_by_trust(self):
        """Should sort sources by trust level (highest first)."""
        hierarchy = TrustHierarchy()

        sources = ["osm", "google_places", "manual_override", "serper"]
        sorted_sources = hierarchy.sort_by_trust(sources)

        assert sorted_sources == ["manual_override", "google_places", "serper", "osm"]

    def test_trust_level_boundaries(self):
        """Should enforce trust level boundaries (0-100)."""
        hierarchy = TrustHierarchy()

        # All trust levels should be within 0-100 range
        for source in ["manual_override", "sport_scotland", "google_places", "osm"]:
            trust = hierarchy.get_trust_level(source)
            assert 0 <= trust <= 100
