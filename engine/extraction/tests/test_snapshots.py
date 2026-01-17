"""
Snapshot tests for extraction engine.

Snapshot tests capture the output of extractors at a known-good state,
then verify that future extractions produce the same results.
This prevents regressions when modifying extraction logic.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from engine.extraction.extractors import (
    GooglePlacesExtractor,
    SportScotlandExtractor,
    EdinburghCouncilExtractor,
    OpenChargeMapExtractor,
    SerperExtractor,
    OSMExtractor,
)


class TestExtractionSnapshots:
    """
    Snapshot tests for all extractors.

    Each test loads a fixture file and compares the extraction result
    against a known-good snapshot.
    """

    def test_google_places_snapshot(self):
        """Test Google Places extractor produces consistent output."""
        # Load fixture
        fixture_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "google_places_venue_response.json"

        with open(fixture_path, 'r', encoding='utf-8') as f:
            fixture_data = json.load(f)

        # Extract first place from the places array
        raw_data = fixture_data["places"][0]

        # Extract
        extractor = GooglePlacesExtractor()
        result = extractor.extract(raw_data)
        validated = extractor.validate(result)

        # Verify key fields match expected snapshot
        assert validated["entity_name"] == "Game4Padel | Edinburgh Park"
        assert validated["latitude"] == 55.930189299999995
        assert validated["longitude"] == -3.3153414999999997
        assert validated["phone"] == "+441315397071"  # Formatted to E.164
        assert validated["street_address"] == "1, New Park Square, Edinburgh Park, Edinburgh EH12 9GR, UK"
        assert "external_id" in validated
        assert validated["external_id"] == "ChIJhwNDsAjFh0gRDARGLR5vtdI"

        # Verify structure matches snapshot
        assert "entity_type" in validated
        assert validated["entity_type"] == "VENUE"

        # Discovered attributes should include rating if present
        attributes, discovered = extractor.split_attributes(validated)
        if "rating" in raw_data:
            assert "rating" in discovered

    def test_sport_scotland_snapshot(self):
        """Test Sport Scotland extractor produces consistent output."""
        # Load fixture
        fixture_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "sport_scotland_facility_response.json"

        with open(fixture_path, 'r', encoding='utf-8') as f:
            fixture_data = json.load(f)

        # Sport Scotland data is a GeoJSON feature
        # Extract first feature if it's a FeatureCollection, otherwise use as-is
        if "features" in fixture_data:
            raw_data = fixture_data["features"][0]
        else:
            raw_data = fixture_data

        # Extract
        extractor = SportScotlandExtractor()
        result = extractor.extract(raw_data)
        validated = extractor.validate(result)

        # Verify key fields match expected snapshot
        assert "entity_name" in validated
        assert validated["entity_name"]  # Not empty
        assert "latitude" in validated
        assert "longitude" in validated
        assert validated["entity_type"] == "VENUE"

        # Sport Scotland data should have external ID
        assert "external_id" in validated

        # Verify coordinates are valid
        assert isinstance(validated["latitude"], (int, float))
        assert isinstance(validated["longitude"], (int, float))
        assert -90 <= validated["latitude"] <= 90
        assert -180 <= validated["longitude"] <= 180

    def test_edinburgh_council_snapshot(self):
        """Test Edinburgh Council extractor produces consistent output."""
        # Create a representative fixture based on Edinburgh Council GeoJSON format
        raw_data = {
            "type": "Feature",
            "id": "wfs_leisure_pitches.1",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.1883, 55.9533]  # Note: GeoJSON is [lng, lat]
            },
            "geometry_name": "SHAPE",
            "properties": {
                "NAME": "Edinburgh Padel Centre",
                "FACILITYTYPE": "Sports Centre",
                "ADDRESS": "123 Test Street",
                "POSTCODE": "EH1 1AA",
            }
        }

        # Extract
        extractor = EdinburghCouncilExtractor()
        result = extractor.extract(raw_data)
        validated = extractor.validate(result)

        # Verify key fields match expected snapshot
        assert validated["entity_name"] == "Edinburgh Padel Centre"
        assert validated["latitude"] == 55.9533
        assert validated["longitude"] == -3.1883
        assert validated["postcode"] == "EH1 1AA"
        assert validated["entity_type"] == "VENUE"

        # Verify external ID format
        assert "external_id" in validated
        assert validated["external_id"] == "wfs_leisure_pitches.1"

    def test_open_charge_map_snapshot(self):
        """Test OpenChargeMap extractor produces consistent output."""
        # Load fixture
        fixture_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "open_charge_map_response.json"

        with open(fixture_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Extract
        extractor = OpenChargeMapExtractor()
        result = extractor.extract(raw_data)
        validated = extractor.validate(result)

        # Verify key fields match expected snapshot
        assert "entity_name" in validated
        assert "latitude" in validated
        assert "longitude" in validated
        assert validated["entity_type"] == "VENUE"

        # OpenChargeMap should have external ID
        assert "external_id" in validated

        # EV-specific fields should be in discovered attributes
        attributes, discovered = extractor.split_attributes(validated)
        # Discovered attributes might include connection types, power levels, etc.
        assert isinstance(discovered, dict)

    def test_serper_snapshot(self):
        """Test Serper extractor produces consistent output (with mocked LLM)."""
        # Load fixture
        fixture_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "serper_padel_search.json"

        with open(fixture_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Mock the LLM client to return consistent results
        with patch("engine.extraction.llm_client.get_instructor_client") as mock_get_client:
            # Create mock LLM response
            mock_response = MagicMock()
            mock_response.entity_name = "Game4Padel Edinburgh"
            mock_response.entity_type = "VENUE"
            mock_response.phone = "+44 131 123 4567"
            mock_response.email = "info@game4padel.com"
            mock_response.website_url = "https://game4padel.com"
            mock_response.street_address = None
            mock_response.city = "Edinburgh"
            mock_response.postcode = None
            mock_response.country = "UK"
            mock_response.latitude = None
            mock_response.longitude = None
            mock_response.confidence = 0.8

            # Mock the client
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            # Extract
            extractor = SerperExtractor()
            result = extractor.extract(raw_data)
            validated = extractor.validate(result)

            # Verify key fields match expected snapshot
            assert validated["entity_name"] == "Game4Padel Edinburgh"
            assert validated["entity_type"] == "VENUE"
            assert validated.get("phone") == "+44 131 123 4567"
            assert validated.get("email") == "info@game4padel.com"
            assert validated.get("website_url") == "https://game4padel.com"

            # Serper data often has missing coordinates (expected)
            assert validated.get("latitude") is None or "latitude" not in validated
            assert validated.get("longitude") is None or "longitude" not in validated

    def test_osm_snapshot(self):
        """Test OSM extractor produces consistent output (with mocked LLM)."""
        # Load fixture
        fixture_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "osm_overpass_sports_facility.json"

        with open(fixture_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Mock the LLM client to return consistent results
        with patch("engine.extraction.llm_client.get_instructor_client") as mock_get_client:
            # Create mock LLM response
            mock_response = MagicMock()
            mock_response.entity_name = "Edinburgh Sports Centre"
            mock_response.entity_type = "VENUE"
            mock_response.phone = None
            mock_response.email = None
            mock_response.website_url = "https://example.com/sports"
            mock_response.street_address = "Test Street"
            mock_response.city = "Edinburgh"
            mock_response.postcode = None
            mock_response.country = "UK"
            mock_response.latitude = 55.9500
            mock_response.longitude = -3.1900
            mock_response.confidence = 0.8

            # Mock the client
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            # Extract
            extractor = OSMExtractor()
            result = extractor.extract(raw_data)
            validated = extractor.validate(result)

            # Verify key fields match expected snapshot
            assert validated["entity_name"] == "Edinburgh Sports Centre"
            assert validated["entity_type"] == "VENUE"
            assert validated["latitude"] == 55.9500
            assert validated["longitude"] == -3.1900

            # OSM should have external ID
            assert "external_id" in validated

    def test_snapshot_consistency_across_runs(self):
        """
        Verify that running the same extraction multiple times produces identical results.

        This test ensures extractors are deterministic (when not using LLM).
        """
        # Use Edinburgh Council as it's fully deterministic (no LLM)
        raw_data = {
            "type": "Feature",
            "id": "test.123",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.1883, 55.9533]
            },
            "properties": {
                "NAME": "Test Facility",
                "ADDRESS": "123 Test St",
                "POSTCODE": "EH1 1AA",
            }
        }

        extractor = EdinburghCouncilExtractor()

        # Run extraction 3 times
        results = []
        for _ in range(3):
            result = extractor.extract(raw_data)
            validated = extractor.validate(result)
            results.append(validated)

        # All results should be identical
        assert results[0] == results[1] == results[2]

    def test_snapshot_field_types(self):
        """Verify that extracted field types match expected types."""
        # Use Google Places as it has comprehensive field coverage
        fixture_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "google_places_venue_response.json"

        with open(fixture_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        extractor = GooglePlacesExtractor()
        result = extractor.extract(raw_data)
        validated = extractor.validate(result)

        # Verify field types
        assert isinstance(validated["entity_name"], str)
        assert isinstance(validated["latitude"], (int, float))
        assert isinstance(validated["longitude"], (int, float))
        assert isinstance(validated["phone"], str)
        assert isinstance(validated["street_address"], str)
        assert isinstance(validated["external_id"], str)
        assert isinstance(validated["entity_type"], str)

        # Verify latitude/longitude ranges
        assert -90 <= validated["latitude"] <= 90
        assert -180 <= validated["longitude"] <= 180

    def test_snapshot_null_handling(self):
        """Verify that extractors handle missing fields correctly (null semantics)."""
        # Create minimal data with many missing fields
        minimal_data = {
            "displayName": {"text": "Minimal Venue"},
            "location": {"latitude": 55.9533, "longitude": -3.1883},
        }

        extractor = GooglePlacesExtractor()
        result = extractor.extract(minimal_data)
        validated = extractor.validate(result)

        # Required fields should be present
        assert "entity_name" in validated
        assert "latitude" in validated
        assert "longitude" in validated

        # Optional fields should be absent (not null, but not in dict)
        # OR explicitly null if extractor includes them
        # This depends on implementation - verify it's consistent
        if "phone" in validated:
            assert validated["phone"] is None or validated["phone"] == ""

    def test_snapshot_json_serializable(self):
        """Verify that all extraction results are JSON serializable."""
        # This is important for database storage
        fixture_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "google_places_venue_response.json"

        with open(fixture_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        extractor = GooglePlacesExtractor()
        result = extractor.extract(raw_data)
        validated = extractor.validate(result)
        attributes, discovered = extractor.split_attributes(validated)

        # Should be able to serialize to JSON without errors
        try:
            json.dumps(attributes)
            json.dumps(discovered)
            json.dumps(validated)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Extraction result is not JSON serializable: {e}")
