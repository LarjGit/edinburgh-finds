"""
Tests for full listing merging.

Listing merging combines multiple ExtractedListing records (from different sources)
into a single Listing record with optimal field values based on trust hierarchy.
"""

import pytest
from engine.extraction.merging import ListingMerger


class TestListingMerger:
    """Test full listing merging logic."""

    def test_merge_single_listing(self):
        """Should handle single listing (no merging needed)."""
        merger = ListingMerger()

        extracted_listings = [
            {
                "id": "ext1",
                "source": "google_places",
                "attributes": {
                    "entity_name": "Game4Padel Edinburgh",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "phone": "+44 131 123 4567"
                },
                "external_ids": {"google_places": "ChIJ123"}
            }
        ]

        merged = merger.merge_listings(extracted_listings)

        assert merged["entity_name"] == "Game4Padel Edinburgh"
        assert merged["latitude"] == 55.9533
        assert merged["phone"] == "+44 131 123 4567"
        assert merged["source_info"]["entity_name"] == "google_places"

    def test_merge_two_listings_no_conflicts(self):
        """Should merge two listings with complementary data."""
        merger = ListingMerger()

        extracted_listings = [
            {
                "id": "ext1",
                "source": "google_places",
                "attributes": {
                    "entity_name": "Game4Padel Edinburgh",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "phone": "+44 131 123 4567"
                },
                "external_ids": {"google_places": "ChIJ123"}
            },
            {
                "id": "ext2",
                "source": "osm",
                "attributes": {
                    "entity_name": "Game4Padel Edinburgh",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "website_url": "https://game4padel.com"
                },
                "external_ids": {"osm": "way/12345"}
            }
        ]

        merged = merger.merge_listings(extracted_listings)

        # Should have fields from both sources
        assert merged["entity_name"] == "Game4Padel Edinburgh"
        assert merged["phone"] == "+44 131 123 4567"  # From Google Places
        assert merged["website_url"] == "https://game4padel.com"  # From OSM
        assert merged["external_ids"]["google_places"] == "ChIJ123"
        assert merged["external_ids"]["osm"] == "way/12345"

    def test_merge_two_listings_with_conflicts(self):
        """Should resolve conflicts using trust hierarchy."""
        merger = ListingMerger()

        extracted_listings = [
            {
                "id": "ext1",
                "source": "google_places",  # Trust: 70
                "attributes": {
                    "entity_name": "Game4Padel Edinburgh",
                    "phone": "+44 131 123 4567",
                    "rating": 4.5
                },
                "external_ids": {"google_places": "ChIJ123"}
            },
            {
                "id": "ext2",
                "source": "serper",  # Trust: 50
                "attributes": {
                    "entity_name": "Game 4 Padel Edinburgh",
                    "phone": "+44 131 999 8888",  # Conflict
                    "email": "info@game4padel.com"
                },
                "external_ids": {}
            }
        ]

        merged = merger.merge_listings(extracted_listings)

        # Google Places should win conflicts due to higher trust
        assert merged["phone"] == "+44 131 123 4567"
        assert merged["rating"] == 4.5
        # Non-conflicting fields preserved
        assert merged["email"] == "info@game4padel.com"
        # Source tracking
        assert merged["source_info"]["phone"] == "google_places"
        assert merged["source_info"]["email"] == "serper"

    def test_merge_three_listings_complex_conflicts(self):
        """Should handle merging 3+ sources with complex conflicts."""
        merger = ListingMerger()

        extracted_listings = [
            {
                "id": "ext1",
                "source": "sport_scotland",  # Trust: 90
                "attributes": {
                    "entity_name": "Edinburgh Sports Centre",
                    "latitude": 55.9533,
                    "longitude": -3.1883
                },
                "external_ids": {}
            },
            {
                "id": "ext2",
                "source": "google_places",  # Trust: 70
                "attributes": {
                    "entity_name": "Edinburgh Sports Center",  # Spelling difference
                    "latitude": 55.9534,  # Slight difference
                    "longitude": -3.1884,
                    "phone": "+44 131 123 4567",
                    "rating": 4.2
                },
                "external_ids": {"google_places": "ChIJ123"}
            },
            {
                "id": "ext3",
                "source": "osm",  # Trust: 40
                "attributes": {
                    "entity_name": "Edinburgh Sports Centre",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "website_url": "https://edinburghsports.com"
                },
                "external_ids": {"osm": "way/999"}
            }
        ]

        merged = merger.merge_listings(extracted_listings)

        # Sport Scotland should win conflicts (highest trust)
        assert merged["entity_name"] == "Edinburgh Sports Centre"
        assert merged["latitude"] == 55.9533
        assert merged["longitude"] == -3.1883
        # Non-conflicting fields preserved
        assert merged["phone"] == "+44 131 123 4567"
        assert merged["website_url"] == "https://edinburghsports.com"
        assert merged["rating"] == 4.2
        # Source tracking
        assert merged["source_info"]["entity_name"] == "sport_scotland"
        assert merged["source_info"]["phone"] == "google_places"
        assert merged["source_info"]["website_url"] == "osm"

    def test_merge_manual_override_always_wins(self):
        """Manual override should override all other sources."""
        merger = ListingMerger()

        extracted_listings = [
            {
                "id": "ext1",
                "source": "sport_scotland",  # Trust: 90
                "attributes": {
                    "entity_name": "Wrong Name",
                    "phone": "+44 131 000 0000"
                },
                "external_ids": {}
            },
            {
                "id": "ext2",
                "source": "manual_override",  # Trust: 100
                "attributes": {
                    "entity_name": "Correct Official Name",
                    "phone": "+44 131 123 4567"
                },
                "external_ids": {}
            },
            {
                "id": "ext3",
                "source": "google_places",  # Trust: 70
                "attributes": {
                    "entity_name": "Another Wrong Name",
                    "phone": "+44 131 999 9999",
                    "email": "info@venue.com"
                },
                "external_ids": {"google_places": "ChIJ123"}
            }
        ]

        merged = merger.merge_listings(extracted_listings)

        # Manual override should win all conflicts
        assert merged["entity_name"] == "Correct Official Name"
        assert merged["phone"] == "+44 131 123 4567"
        # Non-overridden fields preserved
        assert merged["email"] == "info@venue.com"
        # Source tracking
        assert merged["source_info"]["entity_name"] == "manual_override"
        assert merged["source_info"]["phone"] == "manual_override"

    def test_merge_preserves_discovered_attributes(self):
        """Should merge discovered_attributes separately."""
        merger = ListingMerger()

        extracted_listings = [
            {
                "id": "ext1",
                "source": "google_places",
                "attributes": {
                    "entity_name": "Game4Padel"
                },
                "discovered_attributes": {
                    "has_parking": True,
                    "accepts_card": True
                },
                "external_ids": {}
            },
            {
                "id": "ext2",
                "source": "osm",
                "attributes": {
                    "entity_name": "Game4Padel"
                },
                "discovered_attributes": {
                    "has_wifi": True,
                    "has_parking": True
                },
                "external_ids": {}
            }
        ]

        merged = merger.merge_listings(extracted_listings)

        # Discovered attributes should be merged
        assert merged["discovered_attributes"]["has_parking"] is True
        assert merged["discovered_attributes"]["accepts_card"] is True
        assert merged["discovered_attributes"]["has_wifi"] is True

    def test_merge_combines_external_ids(self):
        """Should combine external IDs from all sources."""
        merger = ListingMerger()

        extracted_listings = [
            {
                "id": "ext1",
                "source": "google_places",
                "attributes": {"entity_name": "Venue"},
                "external_ids": {"google_places": "ChIJ123"},
            },
            {
                "id": "ext2",
                "source": "osm",
                "attributes": {"entity_name": "Venue"},
                "external_ids": {"osm": "way/12345"},
            },
            {
                "id": "ext3",
                "source": "open_charge_map",
                "attributes": {"entity_name": "Venue"},
                "external_ids": {"open_charge_map": "poi/999"},
            }
        ]

        merged = merger.merge_listings(extracted_listings)

        # All external IDs should be preserved
        assert merged["external_ids"]["google_places"] == "ChIJ123"
        assert merged["external_ids"]["osm"] == "way/12345"
        assert merged["external_ids"]["open_charge_map"] == "poi/999"

    def test_merge_calculates_field_confidence(self):
        """Should calculate overall confidence for merged fields."""
        merger = ListingMerger()

        extracted_listings = [
            {
                "id": "ext1",
                "source": "google_places",
                "attributes": {
                    "entity_name": "Game4Padel",
                    "phone": "+44 131 123 4567"
                },
                "external_ids": {}
            },
            {
                "id": "ext2",
                "source": "osm",
                "attributes": {
                    "entity_name": "Game4Padel",  # Agreement
                    "phone": "+44 131 999 8888"  # Disagreement
                },
                "external_ids": {}
            }
        ]

        merged = merger.merge_listings(extracted_listings)

        # Field confidence should reflect agreement/disagreement
        assert merged["field_confidence"]["entity_name"] > merged["field_confidence"]["phone"]

    def test_merge_empty_listings_list(self):
        """Should handle empty listings list."""
        merger = ListingMerger()

        result = merger.merge_listings([])

        assert result is None

    def test_merge_tracks_source_count(self):
        """Should track how many sources contributed to the merge."""
        merger = ListingMerger()

        extracted_listings = [
            {"id": "1", "source": "google_places", "attributes": {"entity_name": "A"}, "external_ids": {}},
            {"id": "2", "source": "osm", "attributes": {"entity_name": "A"}, "external_ids": {}},
            {"id": "3", "source": "serper", "attributes": {"entity_name": "A"}, "external_ids": {}},
        ]

        merged = merger.merge_listings(extracted_listings)

        assert merged["source_count"] == 3
        assert "google_places" in merged["sources"]
        assert "osm" in merged["sources"]
        assert "serper" in merged["sources"]
