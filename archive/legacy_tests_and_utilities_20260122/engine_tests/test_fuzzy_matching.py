"""
Tests for fuzzy name + location matching.

Fuzzy matching combines:
1. String similarity (name comparison)
2. Geographic proximity (lat/lng distance)

This is the fallback strategy when external IDs and slugs don't match.
"""

import pytest
from engine.extraction.deduplication import FuzzyMatcher, MatchResult


class TestFuzzyMatcher:
    """Test fuzzy matching logic."""

    def test_exact_name_and_location_match(self):
        """Should match with high confidence for identical name and location."""
        matcher = FuzzyMatcher()

        listing1 = {
            "entity_name": "Game4Padel Edinburgh",
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Game4Padel Edinburgh",
            "latitude": 55.9533,
            "longitude": -3.1883
        }

        result = matcher.match(listing1, listing2)

        assert result.is_match is True
        assert result.confidence >= 0.95
        assert result.match_type == "fuzzy"

    def test_similar_name_close_location(self):
        """Should match similar names at same location."""
        matcher = FuzzyMatcher()

        listing1 = {
            "entity_name": "Game4Padel Edinburgh",
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Game 4 Padel Edinburgh",  # Slightly different formatting
            "latitude": 55.9534,  # ~10 meters away
            "longitude": -3.1884
        }

        result = matcher.match(listing1, listing2)

        assert result.is_match is True
        assert result.confidence >= 0.85

    def test_no_match_same_name_different_locations(self):
        """Should not match same name at very different locations."""
        matcher = FuzzyMatcher()

        listing1 = {
            "entity_name": "David Lloyd",
            "latitude": 55.9533,  # Edinburgh
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "David Lloyd",
            "latitude": 51.5074,  # London (~400km away)
            "longitude": -0.1278
        }

        result = matcher.match(listing1, listing2)

        # Same chain, different locations - should not match
        assert result.is_match is False
        assert result.confidence < 0.5

    def test_no_match_different_names_same_location(self):
        """Should not match very different names even at same location."""
        matcher = FuzzyMatcher()

        listing1 = {
            "entity_name": "Game4Padel",
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Tennis Club",
            "latitude": 55.9533,
            "longitude": -3.1883
        }

        result = matcher.match(listing1, listing2)

        # Different businesses at same location - should not match
        assert result.is_match is False
        assert result.confidence < 0.5

    def test_match_typo_tolerance(self):
        """Should handle minor typos in names."""
        matcher = FuzzyMatcher()

        listing1 = {
            "entity_name": "Game4Padel Edinburgh",
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Game4Padel Edinbrugh",  # Typo in city name
            "latitude": 55.9533,
            "longitude": -3.1883
        }

        result = matcher.match(listing1, listing2)

        assert result.is_match is True
        assert result.confidence >= 0.85

    def test_match_with_abbreviations(self):
        """Should handle common abbreviations."""
        matcher = FuzzyMatcher()

        listing1 = {
            "entity_name": "Edinburgh Leisure Centre",
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Edinburgh Leisure Ctr",
            "latitude": 55.9533,
            "longitude": -3.1883
        }

        result = matcher.match(listing1, listing2)

        assert result.is_match is True
        assert result.confidence >= 0.80

    def test_no_match_missing_coordinates(self):
        """Should not match if coordinates are missing."""
        matcher = FuzzyMatcher()

        listing1 = {
            "entity_name": "Game4Padel Edinburgh",
            "latitude": None,
            "longitude": None
        }
        listing2 = {
            "entity_name": "Game4Padel Edinburgh",
            "latitude": 55.9533,
            "longitude": -3.1883
        }

        result = matcher.match(listing1, listing2)

        # Without location, we can't be confident enough
        assert result.is_match is False

    def test_partial_match_threshold(self):
        """Should not match below confidence threshold."""
        matcher = FuzzyMatcher(threshold=0.85)

        listing1 = {
            "entity_name": "Edinburgh Sports Centre",
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Edinburgh Tennis Club",  # Related but different
            "latitude": 55.9540,  # ~80 meters away
            "longitude": -3.1890
        }

        result = matcher.match(listing1, listing2)

        # Similar name, close location, but not similar enough
        assert result.is_match is False
        assert result.confidence < 0.85

    def test_distance_calculation_meters(self):
        """Should correctly calculate distance in meters."""
        # Use lower threshold for this test since 100m+ is reasonably far
        matcher = FuzzyMatcher(threshold=0.7)

        # Two points ~100 meters apart in Edinburgh
        listing1 = {
            "entity_name": "Game4Padel",
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Game4Padel",
            "latitude": 55.9543,  # ~111 meters north
            "longitude": -3.1883
        }

        result = matcher.match(listing1, listing2)

        # Same name, ~100m away - should match with lower threshold
        assert result.is_match is True
        assert result.confidence >= 0.70

    def test_distance_threshold_rejection(self):
        """Should reject matches beyond distance threshold."""
        matcher = FuzzyMatcher(max_distance_meters=50)

        listing1 = {
            "entity_name": "Game4Padel",
            "latitude": 55.9533,
            "longitude": -3.1883
        }
        listing2 = {
            "entity_name": "Game4Padel",
            "latitude": 55.9543,  # ~111 meters north (beyond threshold)
            "longitude": -3.1883
        }

        result = matcher.match(listing1, listing2)

        # Beyond distance threshold
        assert result.is_match is False
