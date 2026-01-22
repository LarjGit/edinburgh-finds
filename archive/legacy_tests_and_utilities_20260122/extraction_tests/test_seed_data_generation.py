"""
Test that extracted listings can be used to generate seed data.

Verifies that the extraction output format is compatible with seed data
generation scripts and can be used to populate the database.
"""

import json
import pytest
from engine.extraction.merging import ListingMerger


class TestSeedDataGeneration:
    """Test extraction compatibility with seed data generation."""

    def test_extracted_listing_to_seed_data_format(self):
        """
        Verify that extracted listing data can be converted to seed data format.

        The seed_data.py script expects data in a specific format. This test
        verifies that extracted listings match that format.
        """
        # Simulate extracted listings
        extracted_listings = [
            {
                "id": "ext-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Test Padel Club",
                    "street_address": "123 Test St",
                    "city": "Edinburgh",
                    "postcode": "EH1 1AA",
                    "country": "UK",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "phone": "+441311234567",
                    "email": "info@testpadel.com",
                    "website_url": "https://testpadel.com",
                    "padel": True,
                    "padel_total_courts": 4,
                    "padel_summary": "4 outdoor padel courts",
                },
                "discovered_attributes": {
                    "rating": 4.5,
                    "review_count": 100,
                },
                "external_ids": {
                    "google_place_id": "ChIJTest123",
                },
            }
        ]

        # Merge
        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Convert to seed data format
        seed_data_format = {
            "entity_name": merged["entity_name"],
            "entity_type": merged["entity_type"],
            "data": {
                "entity_name": merged["entity_name"],
                "entity_type": merged["entity_type"],
                "street_address": merged.get("street_address"),
                "city": merged.get("city"),
                "postcode": merged.get("postcode"),
                "country": merged.get("country"),
                "latitude": merged.get("latitude"),
                "longitude": merged.get("longitude"),
                "phone": merged.get("phone"),
                "email": merged.get("email"),
                "website_url": merged.get("website_url"),
                # Sport-specific fields
                "padel": merged.get("padel"),
                "padel_total_courts": merged.get("padel_total_courts"),
                "padel_summary": merged.get("padel_summary"),
                # Other attributes
                "other_attributes": merged.get("discovered_attributes", {}),
            }
        }

        # Verify seed data format is valid
        assert "entity_name" in seed_data_format
        assert "entity_type" in seed_data_format
        assert "data" in seed_data_format

        # Verify nested data structure
        data = seed_data_format["data"]
        assert data["entity_name"] == "Test Padel Club"
        assert data["entity_type"] == "VENUE"
        assert data["street_address"] == "123 Test St"
        assert data["city"] == "Edinburgh"
        assert data["latitude"] == 55.9533
        assert data["padel"] is True
        assert data["padel_total_courts"] == 4

        # Verify other_attributes (discovered_attributes)
        assert "rating" in data["other_attributes"]
        assert "review_count" in data["other_attributes"]

    def test_multiple_extracted_listings_to_seed_data(self):
        """
        Verify that multiple extracted listings can be converted to seed data.

        This simulates generating seed data from a batch of extractions.
        """
        extracted_listings = [
            {
                "id": "ext-venue-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Padel Club 1",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                },
                "discovered_attributes": {},
                "external_ids": {},
            },
            {
                "id": "ext-venue-002",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Padel Club 2",
                    "latitude": 55.9600,
                    "longitude": -3.2000,
                },
                "discovered_attributes": {},
                "external_ids": {},
            },
        ]

        merger = ListingMerger()
        seed_data_list = []

        for listing in extracted_listings:
            merged = merger.merge_listings([listing])
            seed_data = {
                "entity_name": merged["entity_name"],
                "entity_type": merged["entity_type"],
                "data": merged,
            }
            seed_data_list.append(seed_data)

        # Verify we have seed data for both venues
        assert len(seed_data_list) == 2
        assert seed_data_list[0]["entity_name"] == "Padel Club 1"
        assert seed_data_list[1]["entity_name"] == "Padel Club 2"

        # Verify each can be serialized (for JSON storage)
        for seed_data in seed_data_list:
            try:
                json.dumps(seed_data, default=str)
            except (TypeError, ValueError) as e:
                pytest.fail(f"Seed data is not JSON serializable: {e}")

    def test_opening_hours_format_for_seed_data(self):
        """
        Verify that opening_hours from extraction matches seed data format.

        Seed data expects opening_hours as a JSON object with day keys.
        """
        extracted_listings = [
            {
                "id": "ext-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Test Venue",
                    "opening_hours": {
                        "monday": {"open": "09:00", "close": "22:00"},
                        "tuesday": {"open": "09:00", "close": "22:00"},
                        "wednesday": {"open": "09:00", "close": "22:00"},
                        "thursday": {"open": "09:00", "close": "22:00"},
                        "friday": {"open": "09:00", "close": "23:00"},
                        "saturday": {"open": "10:00", "close": "23:00"},
                        "sunday": "CLOSED",
                    },
                },
                "discovered_attributes": {},
                "external_ids": {},
            }
        ]

        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Verify opening_hours structure matches seed data expectations
        opening_hours = merged.get("opening_hours")
        assert opening_hours is not None
        assert isinstance(opening_hours, dict)

        # Verify day keys exist
        assert "monday" in opening_hours
        assert "friday" in opening_hours
        assert "sunday" in opening_hours

        # Verify format is compatible with seed data script
        # (seed_data.py serializes this as JSON)
        try:
            opening_hours_json = json.dumps(opening_hours)
            parsed = json.loads(opening_hours_json)
            assert parsed["monday"]["open"] == "09:00"
            assert parsed["sunday"] == "CLOSED"
        except (TypeError, ValueError, KeyError) as e:
            pytest.fail(f"opening_hours format incompatible with seed data: {e}")

    def test_social_media_fields_for_seed_data(self):
        """
        Verify that social media URLs from extraction match seed data format.

        Seed data includes instagram_url, facebook_url, twitter_url, linkedin_url.
        """
        extracted_listings = [
            {
                "id": "ext-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Test Venue",
                    "instagram_url": "https://instagram.com/testvenue",
                    "facebook_url": "https://facebook.com/testvenue",
                    "twitter_url": "https://twitter.com/testvenue",
                    "linkedin_url": "https://linkedin.com/company/testvenue",
                },
                "discovered_attributes": {},
                "external_ids": {},
            }
        ]

        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Verify all social URLs present
        assert merged.get("instagram_url") == "https://instagram.com/testvenue"
        assert merged.get("facebook_url") == "https://facebook.com/testvenue"
        assert merged.get("twitter_url") == "https://twitter.com/testvenue"
        assert merged.get("linkedin_url") == "https://linkedin.com/company/testvenue"

        # Verify format matches seed data expectations
        seed_data_social = {
            "instagram_url": merged.get("instagram_url"),
            "facebook_url": merged.get("facebook_url"),
            "twitter_url": merged.get("twitter_url"),
            "linkedin_url": merged.get("linkedin_url"),
        }

        # All should be valid URLs or None
        for url in seed_data_social.values():
            if url is not None:
                assert isinstance(url, str)
                assert url.startswith("http")

    def test_attributes_json_serialization_for_seed_data(self):
        """
        Verify that attributes can be serialized to JSON for seed data.

        Seed data stores attributes as a JSON string in the database.
        """
        extracted_listings = [
            {
                "id": "ext-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Test Venue",
                    "padel": True,
                    "padel_total_courts": 4,
                    "padel_summary": "4 outdoor courts",
                    "tennis": False,
                    "tennis_total_courts": None,
                },
                "discovered_attributes": {
                    "floodlights": True,
                    "parking_available": True,
                },
                "external_ids": {},
            }
        ]

        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Build attributes dict as seed_data.py does
        attributes = {
            "padel": merged.get("padel"),
            "padel_total_courts": merged.get("padel_total_courts"),
            "padel_summary": merged.get("padel_summary"),
            "tennis": merged.get("tennis"),
            "tennis_total_courts": merged.get("tennis_total_courts"),
        }

        # Remove None values (as seed_data.py does)
        attributes = {k: v for k, v in attributes.items() if v is not None}

        # Serialize to JSON
        try:
            attributes_json = json.dumps(attributes)
            # Verify can be deserialized
            parsed = json.loads(attributes_json)
            assert parsed["padel"] is True
            assert parsed["padel_total_courts"] == 4
            assert "tennis_total_courts" not in parsed  # Was None, should be filtered
        except (TypeError, ValueError) as e:
            pytest.fail(f"Attributes JSON serialization failed: {e}")

        # Also test discovered_attributes serialization
        discovered = merged.get("discovered_attributes", {})
        try:
            discovered_json = json.dumps(discovered)
            parsed_discovered = json.loads(discovered_json)
            assert parsed_discovered["floodlights"] is True
        except (TypeError, ValueError) as e:
            pytest.fail(f"Discovered attributes JSON serialization failed: {e}")

    def test_complete_seed_data_structure(self):
        """
        Verify that a complete extracted listing produces valid seed data structure.

        This test creates a fully-populated listing and verifies all fields
        can be converted to seed data format.
        """
        extracted_listings = [
            {
                "id": "ext-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Complete Venue",
                    "summary": "A complete venue with all fields",
                    "street_address": "123 Complete St",
                    "city": "Edinburgh",
                    "postcode": "EH1 1AA",
                    "country": "UK",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "phone": "+441311234567",
                    "email": "info@complete.com",
                    "website_url": "https://complete.com",
                    "instagram_url": "https://instagram.com/complete",
                    "facebook_url": "https://facebook.com/complete",
                    "opening_hours": {
                        "monday": {"open": "09:00", "close": "22:00"},
                        "sunday": "CLOSED",
                    },
                    "padel": True,
                    "padel_total_courts": 4,
                },
                "discovered_attributes": {
                    "rating": 4.5,
                    "review_count": 100,
                },
                "external_ids": {
                    "google_place_id": "ChIJTest123",
                },
            }
        ]

        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Create complete seed data structure
        seed_data = {
            "entity_name": merged["entity_name"],
            "entity_type": merged["entity_type"],
            "data": {
                "entity_name": merged["entity_name"],
                "entity_type": merged["entity_type"],
                "summary": merged.get("summary"),
                "street_address": merged.get("street_address"),
                "city": merged.get("city"),
                "postcode": merged.get("postcode"),
                "country": merged.get("country"),
                "latitude": merged.get("latitude"),
                "longitude": merged.get("longitude"),
                "phone": merged.get("phone"),
                "email": merged.get("email"),
                "website_url": merged.get("website_url"),
                "instagram_url": merged.get("instagram_url"),
                "facebook_url": merged.get("facebook_url"),
                "opening_hours": merged.get("opening_hours"),
                "padel": merged.get("padel"),
                "padel_total_courts": merged.get("padel_total_courts"),
                "other_attributes": merged.get("discovered_attributes", {}),
            }
        }

        # Verify complete structure is valid
        assert seed_data["entity_name"] == "Complete Venue"
        assert seed_data["entity_type"] == "VENUE"

        data = seed_data["data"]
        assert data["entity_name"] == "Complete Venue"
        assert data["summary"] == "A complete venue with all fields"
        assert data["street_address"] == "123 Complete St"
        assert data["city"] == "Edinburgh"
        assert data["latitude"] == 55.9533
        assert data["phone"] == "+441311234567"
        assert data["padel"] is True

        # Verify JSON serialization works for entire structure
        try:
            json.dumps(seed_data, default=str)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Complete seed data structure is not JSON serializable: {e}")
