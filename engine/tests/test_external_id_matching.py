"""
Tests for external ID-based deduplication matching.

External IDs are the most reliable way to match duplicate listings across sources.
Each source has its own external ID format (Google Place ID, OSM ID, etc.)
"""

import pytest
from engine.extraction.deduplication import ExternalIDMatcher, MatchResult


class TestExternalIDMatcher:
    """Test external ID matching logic."""

    def test_exact_google_place_id_match(self):
        """Should match two listings with identical Google Place ID."""
        matcher = ExternalIDMatcher()

        listing1_ids = {
            "google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"
        }
        listing2_ids = {
            "google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"
        }

        result = matcher.match(listing1_ids, listing2_ids)

        assert result.is_match is True
        assert result.confidence == 1.0
        assert result.match_type == "external_id"
        assert result.matched_on == "google_places"

    def test_exact_osm_id_match(self):
        """Should match two listings with identical OSM ID."""
        matcher = ExternalIDMatcher()

        listing1_ids = {
            "osm": "way/12345678"
        }
        listing2_ids = {
            "osm": "way/12345678"
        }

        result = matcher.match(listing1_ids, listing2_ids)

        assert result.is_match is True
        assert result.confidence == 1.0
        assert result.match_type == "external_id"
        assert result.matched_on == "osm"

    def test_no_match_different_external_ids(self):
        """Should not match listings with different external IDs."""
        matcher = ExternalIDMatcher()

        listing1_ids = {
            "google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"
        }
        listing2_ids = {
            "google_places": "ChIJAQAAADeuEmsRUsoyG83frY5"
        }

        result = matcher.match(listing1_ids, listing2_ids)

        assert result.is_match is False
        assert result.confidence == 0.0

    def test_no_match_no_common_id_types(self):
        """Should not match if no common external ID types."""
        matcher = ExternalIDMatcher()

        listing1_ids = {
            "google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"
        }
        listing2_ids = {
            "osm": "way/12345678"
        }

        result = matcher.match(listing1_ids, listing2_ids)

        assert result.is_match is False
        assert result.confidence == 0.0

    def test_match_multiple_common_ids(self):
        """Should match if any common external ID matches."""
        matcher = ExternalIDMatcher()

        listing1_ids = {
            "google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "osm": "way/12345678"
        }
        listing2_ids = {
            "google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "osm": "way/99999999"  # Different OSM ID, but Google matches
        }

        result = matcher.match(listing1_ids, listing2_ids)

        assert result.is_match is True
        assert result.confidence == 1.0
        assert result.matched_on == "google_places"

    def test_no_match_empty_ids(self):
        """Should not match if either listing has no external IDs."""
        matcher = ExternalIDMatcher()

        result = matcher.match({}, {"google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"})
        assert result.is_match is False

        result = matcher.match({"google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"}, {})
        assert result.is_match is False

        result = matcher.match({}, {})
        assert result.is_match is False

    def test_case_insensitive_matching(self):
        """External ID matching should be case-insensitive."""
        matcher = ExternalIDMatcher()

        listing1_ids = {
            "osm": "WAY/12345678"
        }
        listing2_ids = {
            "osm": "way/12345678"
        }

        result = matcher.match(listing1_ids, listing2_ids)

        assert result.is_match is True
        assert result.confidence == 1.0

    def test_whitespace_normalization(self):
        """Should normalize whitespace in external IDs."""
        matcher = ExternalIDMatcher()

        listing1_ids = {
            "google_places": " ChIJN1t_tDeuEmsRUsoyG83frY4 "
        }
        listing2_ids = {
            "google_places": "ChIJN1t_tDeuEmsRUsoyG83frY4"
        }

        result = matcher.match(listing1_ids, listing2_ids)

        assert result.is_match is True
        assert result.confidence == 1.0
