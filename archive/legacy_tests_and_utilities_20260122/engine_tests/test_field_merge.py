"""
Tests for field-level merging logic.

Field merging combines values from multiple sources based on trust hierarchy.
The source with the highest trust level wins for each field independently.
"""

import pytest
from engine.extraction.merging import FieldMerger, FieldValue


class TestFieldValue:
    """Test FieldValue data class."""

    def test_field_value_creation(self):
        """Should create FieldValue with all attributes."""
        field_value = FieldValue(
            value="Game4Padel Edinburgh",
            source="google_places",
            confidence=0.95
        )

        assert field_value.value == "Game4Padel Edinburgh"
        assert field_value.source == "google_places"
        assert field_value.confidence == 0.95

    def test_field_value_with_none(self):
        """Should handle None values."""
        field_value = FieldValue(
            value=None,
            source="osm",
            confidence=0.5
        )

        assert field_value.value is None
        assert field_value.source == "osm"


class TestFieldMerger:
    """Test field-level merging logic."""

    def test_merge_single_value(self):
        """Should return the only value when there's no conflict."""
        merger = FieldMerger()

        field_values = [
            FieldValue(value="Game4Padel Edinburgh", source="google_places", confidence=0.9)
        ]

        result = merger.merge_field("entity_name", field_values)

        assert result.value == "Game4Padel Edinburgh"
        assert result.source == "google_places"
        assert result.confidence == 0.9

    def test_merge_identical_values(self):
        """Should merge identical values from multiple sources."""
        merger = FieldMerger()

        field_values = [
            FieldValue(value="55.9533", source="google_places", confidence=0.9),
            FieldValue(value="55.9533", source="osm", confidence=0.7),
        ]

        result = merger.merge_field("latitude", field_values)

        # Should choose the higher trust source
        assert result.value == "55.9533"
        assert result.source == "google_places"  # Higher trust
        assert result.confidence >= 0.9

    def test_merge_conflicting_values_trust_wins(self):
        """Should choose value from higher trust source when values conflict."""
        merger = FieldMerger()

        field_values = [
            FieldValue(value="+44 131 123 4567", source="google_places", confidence=0.9),
            FieldValue(value="+44 131 999 8888", source="serper", confidence=0.7),
            FieldValue(value=None, source="osm", confidence=0.5),
        ]

        result = merger.merge_field("phone", field_values)

        # Google Places has higher trust (70) than Serper (50)
        assert result.value == "+44 131 123 4567"
        assert result.source == "google_places"

    def test_merge_manual_override_always_wins(self):
        """Manual override should always win regardless of other sources."""
        merger = FieldMerger()

        field_values = [
            FieldValue(value="Corrected Name", source="manual_override", confidence=1.0),
            FieldValue(value="Wrong Name", source="sport_scotland", confidence=0.95),
            FieldValue(value="Another Wrong Name", source="google_places", confidence=0.9),
        ]

        result = merger.merge_field("entity_name", field_values)

        assert result.value == "Corrected Name"
        assert result.source == "manual_override"

    def test_merge_skips_none_values(self):
        """Should skip None/null values when merging."""
        merger = FieldMerger()

        field_values = [
            FieldValue(value=None, source="osm", confidence=0.7),
            FieldValue(value="info@game4padel.com", source="serper", confidence=0.6),
            FieldValue(value=None, source="google_places", confidence=0.9),
        ]

        result = merger.merge_field("email", field_values)

        # Should choose serper even though google_places has higher trust
        # because google_places value is None
        assert result.value == "info@game4padel.com"
        assert result.source == "serper"

    def test_merge_all_none_values(self):
        """Should return None when all values are None."""
        merger = FieldMerger()

        field_values = [
            FieldValue(value=None, source="google_places", confidence=0.9),
            FieldValue(value=None, source="osm", confidence=0.7),
        ]

        result = merger.merge_field("email", field_values)

        assert result.value is None
        # Should still track the highest trust source that provided None
        assert result.source == "google_places"

    def test_merge_empty_field_values(self):
        """Should handle empty field values list."""
        merger = FieldMerger()

        result = merger.merge_field("entity_name", [])

        assert result.value is None
        assert result.source is None

    def test_merge_with_confidence_tie_breaker(self):
        """When trust levels equal, higher confidence should win."""
        merger = FieldMerger()

        field_values = [
            FieldValue(value="Value A", source="osm", confidence=0.95),
            FieldValue(value="Value B", source="open_charge_map", confidence=0.7),
        ]

        result = merger.merge_field("some_field", field_values)

        # Both OSM and OpenChargeMap have trust level 40
        # OSM should win due to higher confidence
        assert result.value == "Value A"
        assert result.source == "osm"

    def test_merge_tracks_field_provenance(self):
        """Should track all sources that provided values."""
        merger = FieldMerger()

        field_values = [
            FieldValue(value="123 Street", source="google_places", confidence=0.9),
            FieldValue(value="123 Street", source="osm", confidence=0.7),
            FieldValue(value="124 Street", source="serper", confidence=0.6),
        ]

        result = merger.merge_field("street_address", field_values)

        # Should track that multiple sources provided this field
        assert hasattr(result, 'all_sources')
        assert "google_places" in result.all_sources
        assert "osm" in result.all_sources
        assert "serper" in result.all_sources

    def test_merge_different_types(self):
        """Should handle different data types (strings, numbers, booleans)."""
        merger = FieldMerger()

        # Test with boolean
        bool_values = [
            FieldValue(value=True, source="google_places", confidence=0.9),
            FieldValue(value=False, source="osm", confidence=0.7),
        ]
        result = merger.merge_field("is_accessible", bool_values)
        assert result.value is True
        assert result.source == "google_places"

        # Test with number
        num_values = [
            FieldValue(value=4.5, source="google_places", confidence=0.9),
            FieldValue(value=4.2, source="serper", confidence=0.6),
        ]
        result = merger.merge_field("rating", num_values)
        assert result.value == 4.5
        assert result.source == "google_places"
