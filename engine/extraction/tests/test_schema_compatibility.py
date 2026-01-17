"""
Test that extraction output is compatible with the Listing Prisma schema.

Verifies that ExtractedListing data can be properly transformed into Listing records
without schema mismatches or missing required fields.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from engine.extraction.merging import ListingMerger


class TestSchemaCompatibility:
    """Test extraction compatibility with Prisma schema."""

    def test_extracted_listing_fields_match_listing_schema(self):
        """
        Verify that ExtractedListing attributes align with Listing schema fields.

        This test ensures that the fields extracted from sources match the
        expected Listing model structure in Prisma.
        """
        # Create sample ExtractedListing data
        extracted_listings = [
            {
                "id": "ext-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Test Venue",
                    "slug": "test-venue",
                    "street_address": "123 Test St",
                    "city": "Edinburgh",
                    "postcode": "EH1 1AA",
                    "country": "UK",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "phone": "+441311234567",
                    "email": "test@venue.com",
                    "website_url": "https://testvenue.com",
                    "instagram_url": "https://instagram.com/testvenue",
                    "facebook_url": "https://facebook.com/testvenue",
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

        # Merge to create Listing-ready data
        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Verify all required Listing fields are present
        assert "entity_name" in merged, "entity_name is required for Listing"
        assert merged["entity_name"] is not None

        # Verify optional fields are structured correctly
        if "street_address" in merged:
            assert isinstance(merged["street_address"], str)

        if "latitude" in merged:
            assert isinstance(merged["latitude"], (int, float))

        if "longitude" in merged:
            assert isinstance(merged["longitude"], (int, float))

        # Verify JSON fields are properly structured
        assert "discovered_attributes" in merged
        assert isinstance(merged["discovered_attributes"], dict)

        assert "external_ids" in merged
        assert isinstance(merged["external_ids"], dict)

        # Verify source tracking fields exist
        assert "source_info" in merged
        assert isinstance(merged["source_info"], dict)

    def test_entity_type_values_are_valid(self):
        """
        Verify that entity_type values match the valid EntityType enum values.

        Prisma schema validates entity_type in application layer, so we need
        to ensure extracted values match the allowed enum values.
        """
        from engine.schema.types import EntityType

        # Test each valid entity type
        valid_types = [
            "VENUE", "RETAILER", "COACH", "INSTRUCTOR",
            "CLUB", "LEAGUE", "EVENT", "TOURNAMENT"
        ]

        for entity_type in valid_types:
            extracted_listings = [
                {
                    "id": f"ext-{entity_type.lower()}-001",
                    "source": "serper",
                    "entity_type": entity_type,
                    "attributes": {
                        "entity_name": f"Test {entity_type}",
                    },
                    "discovered_attributes": {},
                    "external_ids": {},
                }
            ]

            merger = ListingMerger()
            merged = merger.merge_listings(extracted_listings)

            # Verify entity_type is preserved and valid
            assert merged["entity_type"] == entity_type
            # Verify it matches an EntityType enum value
            assert merged["entity_type"] in [e.value for e in EntityType]

    def test_json_fields_are_serializable(self):
        """
        Verify that JSON fields (attributes, discovered_attributes, external_ids, etc.)
        are properly serializable for Prisma storage.

        Prisma stores JSON as String, so we need to ensure all data is JSON-serializable.
        """
        extracted_listings = [
            {
                "id": "ext-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Test Venue",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "categories": ["padel", "sports"],  # Array field
                },
                "discovered_attributes": {
                    "rating": 4.5,
                    "review_count": 100,
                    "features": {  # Nested object
                        "parking": True,
                        "wifi": True,
                    },
                },
                "external_ids": {
                    "google_place_id": "ChIJTest123",
                },
            }
        ]

        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Verify all JSON fields can be serialized
        try:
            json.dumps(merged["discovered_attributes"])
            json.dumps(merged["external_ids"])
            json.dumps(merged["source_info"])
        except (TypeError, ValueError) as e:
            pytest.fail(f"JSON fields are not serializable: {e}")

    def test_opening_hours_json_format(self):
        """
        Verify that opening_hours field is properly formatted as JSON.

        The opening_hours field is stored as String in Prisma and should contain
        valid JSON with the expected structure.
        """
        extracted_listings = [
            {
                "id": "ext-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Test Venue",
                    "opening_hours": {
                        "monday": {"open": "09:00", "close": "17:00"},
                        "tuesday": {"open": "09:00", "close": "17:00"},
                        "wednesday": {"open": "09:00", "close": "17:00"},
                        "thursday": {"open": "09:00", "close": "17:00"},
                        "friday": {"open": "09:00", "close": "17:00"},
                        "saturday": "CLOSED",
                        "sunday": "CLOSED",
                    },
                },
                "discovered_attributes": {},
                "external_ids": {},
            }
        ]

        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Verify opening_hours is present and serializable
        if "opening_hours" in merged and merged["opening_hours"] is not None:
            try:
                # Should be able to serialize to JSON string
                json_str = json.dumps(merged["opening_hours"])
                # Should be able to deserialize back
                parsed = json.loads(json_str)
                assert isinstance(parsed, dict)
            except (TypeError, ValueError) as e:
                pytest.fail(f"opening_hours is not valid JSON: {e}")

    @pytest.mark.asyncio
    async def test_create_listing_from_extracted_data(self):
        """
        Integration test: Create a Listing record from ExtractedListing data.

        This test simulates the full flow of:
        1. Merge ExtractedListings
        2. Create Listing record in database
        3. Verify Listing is stored correctly
        """
        extracted_listings = [
            {
                "id": "ext-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Game4Padel Edinburgh",
                    "slug": "game4padel-edinburgh",
                    "street_address": "123 Leith Walk",
                    "city": "Edinburgh",
                    "postcode": "EH6 8NP",
                    "country": "UK",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "phone": "+441311234567",
                    "website_url": "https://game4padel.com",
                },
                "discovered_attributes": {
                    "rating": 4.5,
                },
                "external_ids": {
                    "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                },
            }
        ]

        # Merge the extracted data
        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Mock database
        mock_db = AsyncMock()
        mock_listing = MagicMock()
        mock_listing.id = "listing-001"
        mock_listing.entity_name = merged["entity_name"]
        mock_listing.slug = merged.get("slug", "game4padel-edinburgh")
        mock_listing.entityType = merged["entity_type"]

        mock_db.listing.create = AsyncMock(return_value=mock_listing)

        # Prepare data for Listing creation
        listing_data = {
            "entity_name": merged["entity_name"],
            "slug": merged.get("slug", "game4padel-edinburgh"),
            "entityType": merged["entity_type"],
            "street_address": merged.get("street_address"),
            "city": merged.get("city"),
            "postcode": merged.get("postcode"),
            "country": merged.get("country"),
            "latitude": merged.get("latitude"),
            "longitude": merged.get("longitude"),
            "phone": merged.get("phone"),
            "email": merged.get("email"),
            "website_url": merged.get("website_url"),
            "discovered_attributes": json.dumps(merged.get("discovered_attributes", {})),
            "external_ids": json.dumps(merged.get("external_ids", {})),
            "source_info": json.dumps(merged.get("source_info", {})),
        }

        # Create Listing
        listing = await mock_db.listing.create(data=listing_data)

        # Verify Listing was created
        assert listing is not None
        assert listing.entity_name == "Game4Padel Edinburgh"
        assert listing.entityType == "VENUE"

        # Verify database call was made with correct data
        mock_db.listing.create.assert_called_once()
        create_call_args = mock_db.listing.create.call_args
        created_data = create_call_args[1]["data"]

        # Verify all required fields are present
        assert "entity_name" in created_data
        assert "slug" in created_data
        assert "entityType" in created_data

        # Verify JSON fields are serialized
        assert isinstance(created_data["discovered_attributes"], str)
        assert isinstance(created_data["external_ids"], str)
        assert isinstance(created_data["source_info"], str)

    def test_null_handling_in_optional_fields(self):
        """
        Verify that optional fields can be null without breaking schema.

        Many Listing fields are optional (nullable), so we need to ensure
        extraction handles missing data correctly.
        """
        # Create minimal ExtractedListing with only required fields
        extracted_listings = [
            {
                "id": "ext-minimal-001",
                "source": "serper",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Minimal Venue",
                    # All other fields are missing/null
                },
                "discovered_attributes": {},
                "external_ids": {},
            }
        ]

        merger = ListingMerger()
        merged = merger.merge_listings(extracted_listings)

        # Verify required fields are present
        assert "entity_name" in merged
        assert merged["entity_name"] is not None

        # Verify optional fields can be None or missing
        optional_fields = [
            "street_address", "city", "postcode", "country",
            "latitude", "longitude", "phone", "email", "website_url",
            "instagram_url", "facebook_url", "twitter_url", "linkedin_url",
            "opening_hours"
        ]

        for field in optional_fields:
            # Field can be missing or None
            if field in merged:
                # If present, should be valid type or None
                assert merged[field] is None or isinstance(merged[field], (str, int, float))
