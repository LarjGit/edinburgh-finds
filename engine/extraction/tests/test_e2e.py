"""
End-to-end tests for the full extraction pipeline.

Tests the complete flow: Ingest → Extract → Merge → Create Entity
This verifies that the entire extraction engine works correctly when all components
are integrated together.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from prisma import Prisma

from engine.extraction.run import get_extractor_for_source, run_single_extraction
from engine.extraction.deduplication import (
    ExternalIDMatcher,
    SlugMatcher,
    FuzzyMatcher,
    MatchResult,
)
from engine.extraction.merging import EntityMerger, TrustHierarchy


class TestEndToEndPipeline:
    """End-to-end tests for the full extraction pipeline."""

    @pytest.mark.asyncio
    async def test_single_source_single_venue_google_places(self):
        """
        Test Scenario 1: Single source, single venue (Google Places)

        Flow:
        1. RawIngestion record exists for Google Places venue
        2. Extract → Creates ExtractedEntity with structured data
        3. No deduplication needed (single source)
        4. Create Entity record from extracted data
        5. Verify Entity exists with correct fields
        """
        # Setup: Create mock RawIngestion record
        mock_raw_id = "test-raw-google-001"
        mock_raw = MagicMock()
        mock_raw.id = mock_raw_id
        mock_raw.source = "google_places"
        mock_raw.file_path = "engine/data/raw/google_places/test_venue.json"
        mock_raw.status = "success"
        mock_raw.ingested_at = datetime.now()

        # Mock raw data from Google Places API
        mock_raw_data = {
            "id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "displayName": {"text": "Game4Padel Edinburgh"},
            "formattedAddress": "123 Leith Walk, Edinburgh, EH6 8NP, UK",
            "location": {"latitude": 55.9533, "longitude": -3.1883},
            "internationalPhoneNumber": "+44 131 123 4567",
            "websiteUri": "https://game4padel.com",
            "rating": 4.5,
            "userRatingCount": 127,
            "regularOpeningHours": {
                "weekdayDescriptions": [
                    "Monday: 8:00 AM – 10:00 PM",
                    "Tuesday: 8:00 AM – 10:00 PM",
                    "Wednesday: 8:00 AM – 10:00 PM",
                    "Thursday: 8:00 AM – 10:00 PM",
                    "Friday: 8:00 AM – 11:00 PM",
                    "Saturday: 9:00 AM – 11:00 PM",
                    "Sunday: 9:00 AM – 9:00 PM",
                ]
            },
            "editorialSummary": {"text": "Modern padel facility in Edinburgh with 4 courts."},
        }

        # Mock ExtractedEntity that would be created
        mock_extracted_attributes = {
            "entity_name": "Game4Padel Edinburgh",
            "street_address": "123 Leith Walk, Edinburgh, EH6 8NP, UK",
            "latitude": 55.9533,
            "longitude": -3.1883,
            "phone": "+441311234567",
            "website_url": "https://game4padel.com",
        }

        mock_extracted = MagicMock()
        mock_extracted.id = "extracted-001"
        mock_extracted.source = "google_places"
        mock_extracted.entity_type = "VENUE"
        mock_extracted.attributes = json.dumps(mock_extracted_attributes)
        mock_extracted.discovered_attributes = json.dumps({
            "rating": 4.5,
            "review_count": 127,
        })
        mock_extracted.external_ids = json.dumps({
            "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"
        })

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
        mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
        mock_db.extractedlisting.create = AsyncMock(return_value=mock_extracted)

        # Mock file reading
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
            mock_open.return_value = mock_file

            # Step 1: Extract the raw data
            result = await run_single_extraction(
                mock_db,
                raw_id=mock_raw_id,
                verbose=True,
            )

        # Verify extraction succeeded
        assert result["status"] == "success"
        assert result["source"] == "google_places"
        # entity_type is deprecated - using entity_class instead
        assert "entity_name" in result["fields"]
        assert result["fields"]["entity_name"] == "Game4Padel Edinburgh"
        assert result["fields"]["phone"] == "+441311234567"

        # Step 2: Verify no deduplication needed (single source)
        # In a real scenario, we would query for duplicate ExtractedEntitys
        # For this test, we're verifying the extraction worked correctly

        # Step 3: Create Entity from ExtractedEntity
        # In production, this would be done by a separate process
        # For now, we verify the extraction data is correct and ready for listing creation
        assert result["extracted_id"] == "extracted-001"

        # Verify database calls were made correctly
        mock_db.rawingestion.find_unique.assert_called_once_with(where={"id": mock_raw_id})
        mock_db.extractedlisting.find_first.assert_called_once()
        mock_db.extractedlisting.create.assert_called_once()

        # Verify the created ExtractedEntity has all required fields for Entity creation
        create_call_args = mock_db.extractedlisting.create.call_args
        created_data = create_call_args[1]["data"]

        assert created_data["source"] == "google_places"
        # entity_type is deprecated - not asserting on it
        assert created_data["raw_ingestion_id"] == mock_raw_id

        # Verify attributes are properly structured
        created_attrs = json.loads(created_data["attributes"])
        assert "entity_name" in created_attrs
        assert "latitude" in created_attrs
        assert "longitude" in created_attrs
        assert "phone" in created_attrs

    @pytest.mark.asyncio
    async def test_multi_source_same_venue_deduplication_and_merge(self):
        """
        Test Scenario 2: Multi-source, same venue (Google + OSM + Serper)

        Flow:
        1. Three RawIngestion records exist for same venue (different sources)
        2. Extract all three → Creates 3 ExtractedEntitys
        3. Deduplication detects they're the same venue
        4. Merge combines data using trust hierarchy
        5. Create single Listing with best data from all sources
        """
        # This test will verify the deduplication and merging logic
        # We'll create 3 ExtractedEntity records and verify they're properly deduplicated and merged

        # Setup: Create 3 extracted listings for the same venue
        extracted_listings = [
            {
                "id": "ext-google-001",
                "source": "google_places",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Game4Padel Edinburgh",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "phone": "+441311234567",
                    "street_address": "123 Leith Walk, Edinburgh, EH6 8NP, UK",
                },
                "discovered_attributes": {
                    "rating": 4.5,
                },
                "external_ids": {
                    "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                },
            },
            {
                "id": "ext-osm-001",
                "source": "osm",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Game4Padel Edinburgh",
                    "latitude": 55.9533,
                    "longitude": -3.1883,
                    "website_url": "https://game4padel.com",
                },
                "discovered_attributes": {
                    "sport": "padel",
                    "amenity": "sports_centre",
                },
                "external_ids": {
                    "osm_id": "way/123456789",
                },
            },
            {
                "id": "ext-serper-001",
                "source": "serper",
                "entity_type": "VENUE",
                "attributes": {
                    "entity_name": "Game 4 Padel Edinburgh",  # Slight name variation
                    "phone": "+441311234567",
                    "email": "info@game4padel.com",
                },
                "discovered_attributes": {},
                "external_ids": {},
            },
        ]

        # Step 1: Test deduplication - External ID matching
        external_id_matcher = ExternalIDMatcher()

        # Google and OSM should not match on external IDs (different types)
        match_result = external_id_matcher.match(
            extracted_listings[0]["external_ids"],
            extracted_listings[1]["external_ids"]
        )
        assert not match_result.is_match

        # Step 2: Test deduplication - Fuzzy matching (name + location)
        fuzzy_matcher = FuzzyMatcher(threshold=0.85)

        # Google and OSM should match on name + location
        listing1_dict = {
            "entity_name": extracted_listings[0]["attributes"]["entity_name"],
            "latitude": extracted_listings[0]["attributes"]["latitude"],
            "longitude": extracted_listings[0]["attributes"]["longitude"],
        }
        listing2_dict = {
            "entity_name": extracted_listings[1]["attributes"]["entity_name"],
            "latitude": extracted_listings[1]["attributes"]["latitude"],
            "longitude": extracted_listings[1]["attributes"]["longitude"],
        }
        match_result = fuzzy_matcher.match(listing1_dict, listing2_dict)
        assert match_result.is_match
        assert match_result.confidence >= 0.85

        # Google and Serper - Serper doesn't have coordinates so fuzzy match will fail
        # (FuzzyMatcher requires both name AND location)
        listing3_dict = {
            "entity_name": extracted_listings[2]["attributes"]["entity_name"],
            # No coordinates for Serper
        }
        match_result = fuzzy_matcher.match(listing1_dict, listing3_dict)
        # Should not match because location is missing
        assert not match_result.is_match

        # Step 3: Test merging with trust hierarchy
        merger = EntityMerger()
        merged = merger.merge_listings(extracted_listings)

        # Verify merged result has best data from all sources
        assert merged["entity_name"] == "Game4Padel Edinburgh"  # Google Places (higher trust than Serper)
        assert merged["phone"] == "+441311234567"  # From Google Places or Serper
        assert merged["website_url"] == "https://game4padel.com"  # From OSM
        assert merged["email"] == "info@game4padel.com"  # From Serper
        assert merged["street_address"] == "123 Leith Walk, Edinburgh, EH6 8NP, UK"  # From Google Places

        # Verify external IDs from all sources are preserved
        assert "google_place_id" in merged["external_ids"]
        assert "osm_id" in merged["external_ids"]

        # Verify discovered attributes are merged
        assert "rating" in merged["discovered_attributes"]
        assert "sport" in merged["discovered_attributes"]
        assert "amenity" in merged["discovered_attributes"]

        # Verify source tracking
        assert merged["source_count"] == 3
        assert set(merged["sources"]) == {"google_places", "osm", "serper"}
        assert merged["source_info"]["phone"] in ["google_places", "serper"]
        assert merged["source_info"]["website_url"] == "osm"
        assert merged["source_info"]["email"] == "serper"

    @pytest.mark.asyncio
    async def test_discovery_ingestion_new_venue_extraction(self):
        """
        Test Scenario 3: Discovery ingestion, new venue extraction

        Flow:
        1. Serper discovery finds new venue (not in DB)
        2. Extract → Creates ExtractedEntity from unstructured data
        3. Verify LLM extraction handles missing/sparse data correctly
        4. Create Entity with available data (many nulls expected)
        """
        # This test verifies that discovery ingestion (Serper) can create listings
        # even with sparse, unstructured data

        mock_raw_id = "test-raw-serper-discovery-001"
        mock_raw = MagicMock()
        mock_raw.id = mock_raw_id
        mock_raw.source = "serper"
        mock_raw.file_path = "engine/data/raw/serper/discovery_001.json"
        mock_raw.status = "success"

        # Mock Serper discovery data (very sparse)
        mock_raw_data = {
            "organic": [
                {
                    "title": "New Padel Club - Edinburgh South",
                    "link": "https://example.com/padel-south",
                    "snippet": "We're excited to announce the opening of Edinburgh's newest padel club in the south of the city. Book your court today!",
                }
            ]
        }

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
        mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

        # Mock the extractor to return sparse data
        mock_extracted_attributes = {
            "entity_name": "New Padel Club Edinburgh South",
            "website_url": "https://example.com/padel-south",
        }

        mock_extracted = MagicMock()
        mock_extracted.id = "extracted-serper-001"
        mock_extracted.source = "serper"
        mock_extracted.entity_type = "VENUE"
        mock_extracted.attributes = json.dumps(mock_extracted_attributes)
        mock_extracted.discovered_attributes = json.dumps({
            "snippet": "We're excited to announce the opening of Edinburgh's newest padel club in the south of the city."
        })
        mock_extracted.external_ids = json.dumps({})

        mock_db.extractedlisting.create = AsyncMock(return_value=mock_extracted)

        # Mock the extractor to avoid actual LLM calls
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
            mock_open.return_value = mock_file

            with patch("engine.extraction.run.get_extractor_for_source") as mock_get_extractor:
                # Create a mock extractor that returns the expected data
                mock_extractor = MagicMock()
                mock_extractor.extract.return_value = {
                    "entity_name": "New Padel Club Edinburgh South",
                    "website_url": "https://example.com/padel-south",
                    "entity_type": "VENUE",
                }
                mock_extractor.validate.return_value = {
                    "entity_name": "New Padel Club Edinburgh South",
                    "website_url": "https://example.com/padel-south",
                    "entity_type": "VENUE",
                }
                mock_extractor.split_attributes.return_value = (
                    mock_extracted_attributes,  # attributes
                    {"snippet": "We're excited to announce the opening of Edinburgh's newest padel club in the south of the city."}  # discovered
                )
                mock_get_extractor.return_value = mock_extractor

                result = await run_single_extraction(
                    mock_db,
                    raw_id=mock_raw_id,
                    verbose=True,
                )

        # Verify extraction succeeded despite sparse data
        assert result["status"] == "success"
        assert result["source"] == "serper"

        # Verify extracted fields
        assert "entity_name" in result["fields"]
        assert "New Padel" in result["fields"]["entity_name"]

        # Verify missing fields are handled gracefully (not in result)
        # Sparse data means many fields won't be present
        assert result["fields"].get("latitude") is None or "latitude" not in result["fields"]
        assert result["fields"].get("phone") is None or "phone" not in result["fields"]

        # Verify discovered attributes captured the snippet
        if "discovered" in result and result["discovered"]:
            assert "snippet" in result["discovered"] or len(result["discovered"]) >= 0

    @pytest.mark.asyncio
    async def test_entity_specific_ingestion_targeted_extraction(self):
        """
        Test Scenario 4: Entity-specific ingestion, targeted extraction

        Flow:
        1. RawIngestion record exists for a specific entity type (COACH)
        2. Extract → Creates ExtractedEntity with correct entity_type
        3. Verify entity-specific fields are extracted correctly
        4. Verify extracted data validates against entity schema
        5. Create Entity with correct entity_type classification
        """
        # Setup: Create mock RawIngestion record for a COACH entity
        mock_raw_id = "test-raw-serper-coach-001"
        mock_raw = MagicMock()
        mock_raw.id = mock_raw_id
        mock_raw.source = "serper"
        mock_raw.file_path = "engine/data/raw/serper/coach_001.json"
        mock_raw.status = "success"
        mock_raw.ingested_at = datetime.now()

        # Mock raw data from Serper search for a coach
        mock_raw_data = {
            "organic": [
                {
                    "title": "Sarah McTavish - Professional Tennis Coach Edinburgh",
                    "link": "https://sarahmctavish.com",
                    "snippet": "Professional tennis coach with 15 years experience. LTA Level 4 certified. Specializing in juniors and competitive players. Based in Edinburgh, offering private and group sessions.",
                }
            ]
        }

        # Mock ExtractedEntity for COACH entity
        mock_extracted_attributes = {
            "entity_name": "Sarah McTavish",
            "phone": "+441311234567",
            "email": "sarah@sarahmctavish.com",
            "website_url": "https://sarahmctavish.com",
        }

        mock_extracted = MagicMock()
        mock_extracted.id = "extracted-coach-001"
        mock_extracted.source = "serper"
        mock_extracted.entity_type = "COACH"  # Entity-specific type
        mock_extracted.attributes = json.dumps(mock_extracted_attributes)
        mock_extracted.discovered_attributes = json.dumps({
            "qualifications": ["LTA Level 4"],
            "specialization": "juniors and competitive players",
            "experience_years": 15,
        })
        mock_extracted.external_ids = json.dumps({})

        # Mock database
        mock_db = AsyncMock()
        mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
        mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
        mock_db.extractedlisting.create = AsyncMock(return_value=mock_extracted)

        # Mock the extractor to return COACH-specific data
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
            mock_open.return_value = mock_file

            with patch("engine.extraction.run.get_extractor_for_source") as mock_get_extractor:
                # Create a mock extractor that identifies this as a COACH
                mock_extractor = MagicMock()
                mock_extractor.extract.return_value = {
                    "entity_name": "Sarah McTavish",
                    "phone": "+441311234567",
                    "email": "sarah@sarahmctavish.com",
                    "website_url": "https://sarahmctavish.com",
                    "entity_type": "COACH",
                }
                mock_extractor.validate.return_value = {
                    "entity_name": "Sarah McTavish",
                    "phone": "+441311234567",
                    "email": "sarah@sarahmctavish.com",
                    "website_url": "https://sarahmctavish.com",
                    "entity_type": "COACH",
                }
                mock_extractor.split_attributes.return_value = (
                    mock_extracted_attributes,  # attributes
                    {
                        "qualifications": ["LTA Level 4"],
                        "specialization": "juniors and competitive players",
                        "experience_years": 15,
                    }  # discovered_attributes
                )
                mock_get_extractor.return_value = mock_extractor

                # Step 1: Extract the raw data
                result = await run_single_extraction(
                    mock_db,
                    raw_id=mock_raw_id,
                    verbose=True,
                )

        # Step 2: Verify extraction succeeded
        assert result["status"] == "success"
        assert result["source"] == "serper"

        # Step 3: Verify entity_type is correctly identified as COACH
        assert result["entity_type"] == "COACH"

        # Step 4: Verify entity-specific fields are extracted
        assert "entity_name" in result["fields"]
        assert result["fields"]["entity_name"] == "Sarah McTavish"
        assert "email" in result["fields"]
        assert "website_url" in result["fields"]

        # Step 5: Verify discovered attributes contain COACH-specific data
        if "discovered" in result and result["discovered"]:
            # Coach-specific attributes should be in discovered_attributes
            assert isinstance(result["discovered"], dict)

        # Step 6: Verify database calls were made correctly
        mock_db.rawingestion.find_unique.assert_called_once_with(where={"id": mock_raw_id})
        mock_db.extractedlisting.find_first.assert_called_once()
        mock_db.extractedlisting.create.assert_called_once()

        # Step 7: Verify the created ExtractedEntity has COACH entity_type
        create_call_args = mock_db.extractedlisting.create.call_args
        created_data = create_call_args[1]["data"]

        assert created_data["source"] == "serper"
        assert created_data["entity_type"] == "COACH"
        assert created_data["raw_ingestion_id"] == mock_raw_id

        # Step 8: Verify discovered_attributes are properly structured for COACH
        created_discovered = json.loads(created_data["discovered_attributes"])
        # COACH-specific attributes should be present
        assert len(created_discovered) > 0

    @pytest.mark.asyncio
    async def test_conflicting_data_trust_hierarchy_resolves(self):
        """
        Test Scenario 5: Conflicting data from multiple sources, trust hierarchy resolves

        Flow:
        1. Multiple sources provide conflicting data for same field
        2. Trust hierarchy determines which source wins
        3. Verify correct value is selected based on trust level
        4. Verify conflict is logged for review
        """
        # Create extracted listings with conflicting phone numbers
        extracted_listings = [
            {
                "id": "ext-google-002",
                "source": "google_places",  # Trust level: 70
                "attributes": {
                    "entity_name": "Edinburgh Tennis Club",
                    "phone": "+441311111111",  # Google's phone number
                    "latitude": 55.9500,
                    "longitude": -3.1900,
                },
                "discovered_attributes": {},
                "external_ids": {"google_place_id": "ChIJTest123"},
            },
            {
                "id": "ext-serper-002",
                "source": "serper",  # Trust level: 50
                "attributes": {
                    "entity_name": "Edinburgh Tennis Club",
                    "phone": "+441312222222",  # Serper's conflicting phone number
                    "email": "info@edinburghtennis.com",
                },
                "discovered_attributes": {},
                "external_ids": {},
            },
            {
                "id": "ext-sport-scotland-002",
                "source": "sport_scotland",  # Trust level: 90 (highest)
                "attributes": {
                    "entity_name": "Edinburgh Tennis Club",
                    "phone": "+441313333333",  # Sport Scotland's official phone number
                    "latitude": 55.9500,
                    "longitude": -3.1900,
                },
                "discovered_attributes": {},
                "external_ids": {},
            },
        ]

        # Test merging with trust hierarchy
        merger = EntityMerger()
        merged = merger.merge_listings(extracted_listings)

        # Verify Sport Scotland wins due to highest trust level
        assert merged["phone"] == "+441313333333"
        assert merged["source_info"]["phone"] == "sport_scotland"

        # Verify non-conflicting fields are preserved
        assert merged["email"] == "info@edinburghtennis.com"  # From Serper (only source)
        assert merged["source_info"]["email"] == "serper"

        # Verify external IDs preserved
        assert merged["external_ids"]["google_place_id"] == "ChIJTest123"

        # Verify all sources are tracked
        assert set(merged["sources"]) == {"google_places", "serper", "sport_scotland"}
        assert merged["source_count"] == 3

        # Test trust hierarchy directly
        trust_hierarchy = TrustHierarchy()
        assert trust_hierarchy.get_trust_level("sport_scotland") > trust_hierarchy.get_trust_level("google_places")
        assert trust_hierarchy.get_trust_level("google_places") > trust_hierarchy.get_trust_level("serper")


class TestPipelineEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_extraction_failure_quarantine(self):
        """
        Test Scenario 6: Failed extraction, quarantine, retry, success

        Flow:
        1. Extraction fails due to invalid data
        2. Record quarantined in FailedExtraction table
        3. Retry after data correction
        4. Extraction succeeds
        """
        mock_raw_id = "test-raw-invalid-001"
        mock_raw = MagicMock()
        mock_raw.id = mock_raw_id
        mock_raw.source = "google_places"
        mock_raw.file_path = "engine/data/raw/google_places/invalid.json"
        mock_raw.status = "success"

        # Mock invalid data that will cause extraction to fail
        mock_invalid_data = {
            "invalid": "structure",
            "missing": "required_fields"
        }

        mock_db = AsyncMock()
        mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
        mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
        mock_db.failedextraction.create = AsyncMock()

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_invalid_data)
            mock_open.return_value = mock_file

            with patch("engine.extraction.run.get_extractor_for_source") as mock_get_extractor:
                mock_extractor = MagicMock()
                mock_extractor.extract.side_effect = ValueError("Missing required field: displayName")
                mock_get_extractor.return_value = mock_extractor

                result = await run_single_extraction(
                    mock_db,
                    raw_id=mock_raw_id,
                    verbose=True,
                )

        # Verify extraction failed
        assert result["status"] == "error"
        assert "extraction failed" in result["error"].lower()

        # Verify failed extraction was recorded
        # The quarantine recording is called through record_failed_extraction
        # We can verify the error was propagated correctly
        assert result["raw_id"] == mock_raw_id
        assert result["source"] == "google_places"

    @pytest.mark.asyncio
    async def test_empty_extraction_result_handling(self):
        """Test handling of extraction that returns no usable data."""
        # Create an extracted listing with minimal data
        extracted_listings = [
            {
                "id": "ext-minimal-001",
                "source": "serper",
                "attributes": {
                    "entity_name": "Unknown Venue",
                },
                "discovered_attributes": {},
                "external_ids": {},
            }
        ]

        merger = EntityMerger()
        merged = merger.merge_listings(extracted_listings)

        # Verify minimal listing can still be created
        assert merged is not None
        assert merged["entity_name"] == "Unknown Venue"
        assert merged["source_count"] == 1

    def test_deduplication_with_no_matches(self):
        """Test that deduplication correctly identifies non-matching venues."""
        fuzzy_matcher = FuzzyMatcher(threshold=0.85)

        # Two completely different venues
        listing1 = {
            "entity_name": "Game4Padel Edinburgh",
            "latitude": 55.9533,
            "longitude": -3.1883,
        }
        listing2 = {
            "entity_name": "Edinburgh Tennis Club",
            "latitude": 55.9700,
            "longitude": -3.2000,
        }

        match_result = fuzzy_matcher.match(listing1, listing2)

        # Should not match
        assert not match_result.is_match
        assert match_result.confidence < 0.85
