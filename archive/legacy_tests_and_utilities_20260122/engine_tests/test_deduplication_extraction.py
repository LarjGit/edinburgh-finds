"""
Tests for the extraction deduplication orchestrator.

The deduplication system uses a cascade of strategies:
1. External ID matching (highest confidence)
2. Slug matching (medium confidence)
3. Fuzzy name + location matching (requires higher threshold)
"""

import pytest
from engine.extraction.deduplication import Deduplicator, MatchResult


class TestDeduplicator:
    """Test the main deduplication orchestrator."""

    def test_external_id_match_takes_precedence(self):
        """External ID match should be used first and skip other strategies."""
        deduplicator = Deduplicator()

        listing1 = {
            "entity_name": "Game4Padel Edinburgh",
            "slug": "game4padel-edinburgh",
            "external_ids": {"google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"},
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Different Name",  # Different name
            "slug": "different-slug",  # Different slug
            "external_ids": {"google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"},  # Same external ID
            "latitude": 51.5074,  # Different location
            "longitude": -0.1278
        }

        result = deduplicator.find_match(listing1, listing2)

        assert result.is_match is True
        assert result.match_type == "external_id"
        assert result.confidence == 1.0

    def test_slug_match_when_no_external_ids(self):
        """Slug matching should be used when external IDs don't match."""
        deduplicator = Deduplicator()

        listing1 = {
            "entity_name": "Game4Padel Edinburgh",
            "slug": "game4padel-edinburgh",
            "external_ids": {},
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Game4Padel Edinburgh",
            "slug": "game4padel-edinburgh",
            "external_ids": {},
            "latitude": 55.9534,
            "longitude": -3.1884
        }

        result = deduplicator.find_match(listing1, listing2)

        assert result.is_match is True
        assert result.match_type == "slug"
        assert result.confidence == 1.0

    def test_fuzzy_match_as_fallback(self):
        """Fuzzy matching should be used when external ID and slug don't match."""
        deduplicator = Deduplicator()

        listing1 = {
            "entity_name": "Game4Padel Edinburgh",
            "slug": "game4padel-edinburgh-sports",  # Different slug
            "external_ids": {"google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"},
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Game 4 Padel Edinburgh",  # Similar name
            "slug": "padel-venue-edinburgh",  # Very different slug
            "external_ids": {"osm": "way/12345678"},  # Different external ID type
            "latitude": 55.9534,  # Very close location
            "longitude": -3.1884
        }

        result = deduplicator.find_match(listing1, listing2)

        assert result.is_match is True
        assert result.match_type == "fuzzy"
        assert result.confidence >= 0.85

    def test_no_match_all_strategies_fail(self):
        """Should return no match when all strategies fail."""
        deduplicator = Deduplicator()

        listing1 = {
            "entity_name": "Game4Padel Edinburgh",
            "slug": "game4padel-edinburgh",
            "external_ids": {"google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"},
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Tennis Club Glasgow",  # Different name
            "slug": "tennis-club-glasgow",  # Different slug
            "external_ids": {"google_places": "ChIJAQAAADeuEmsRUsoyG83frY5"},  # Different ID
            "latitude": 55.8642,  # Glasgow (~70km away)
            "longitude": -4.2518
        }

        result = deduplicator.find_match(listing1, listing2)

        assert result.is_match is False
        assert result.confidence < 0.5

    def test_find_duplicates_in_list(self):
        """Should find all duplicate pairs in a list of listings."""
        deduplicator = Deduplicator()

        listings = [
            {
                "id": "1",
                "entity_name": "Game4Padel Edinburgh",
                "slug": "game4padel-edinburgh",
                "external_ids": {"google_places": "ChIJ123"},
                "latitude": 55.9533,
                "longitude": -3.1883
            },
            {
                "id": "2",
                "entity_name": "Game4Padel Edinburgh",
                "slug": "game4padel-edinburgh-2",
                "external_ids": {"google_places": "ChIJ123"},  # Same as listing 1
                "latitude": 55.9534,
                "longitude": -3.1884
            },
            {
                "id": "3",
                "entity_name": "Tennis Club",
                "slug": "tennis-club",
                "external_ids": {"osm": "way/999"},
                "latitude": 55.9600,
                "longitude": -3.2000
            }
        ]

        duplicate_groups = deduplicator.find_duplicates(listings)

        assert len(duplicate_groups) == 1
        assert len(duplicate_groups[0]) == 2
        assert set(l["id"] for l in duplicate_groups[0]) == {"1", "2"}

    def test_find_duplicates_multiple_groups(self):
        """Should group multiple sets of duplicates correctly."""
        deduplicator = Deduplicator()

        listings = [
            {"id": "1", "entity_name": "Venue A", "slug": "venue-a", "external_ids": {"google": "A"}, "latitude": 55.95, "longitude": -3.18},
            {"id": "2", "entity_name": "Venue A", "slug": "venue-a", "external_ids": {"google": "A"}, "latitude": 55.95, "longitude": -3.18},
            {"id": "3", "entity_name": "Venue B", "slug": "venue-b", "external_ids": {"google": "B"}, "latitude": 55.96, "longitude": -3.19},
            {"id": "4", "entity_name": "Venue B", "slug": "venue-b", "external_ids": {"google": "B"}, "latitude": 55.96, "longitude": -3.19},
            {"id": "5", "entity_name": "Venue C", "slug": "venue-c", "external_ids": {"google": "C"}, "latitude": 55.97, "longitude": -3.20},
        ]

        duplicate_groups = deduplicator.find_duplicates(listings)

        assert len(duplicate_groups) == 2
        assert all(len(group) == 2 for group in duplicate_groups)

    def test_no_duplicates_found(self):
        """Should return empty list when no duplicates exist."""
        deduplicator = Deduplicator()

        listings = [
            {"id": "1", "entity_name": "Venue A", "slug": "venue-a", "external_ids": {"google": "A"}, "latitude": 55.95, "longitude": -3.18},
            {"id": "2", "entity_name": "Venue B", "slug": "venue-b", "external_ids": {"google": "B"}, "latitude": 55.96, "longitude": -3.19},
            {"id": "3", "entity_name": "Venue C", "slug": "venue-c", "external_ids": {"google": "C"}, "latitude": 55.97, "longitude": -3.20},
        ]

        duplicate_groups = deduplicator.find_duplicates(listings)

        assert len(duplicate_groups) == 0
