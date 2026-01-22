"""
Tests for OpenChargeMap Extractor

This module tests the OpenChargeMapExtractor which transforms raw OpenChargeMap
API responses into structured listing fields for EV charging stations.

OpenChargeMap is an enrichment source - it provides EV charging infrastructure
data that can supplement venue listings (e.g., showing nearby charging for padel courts).

Test Coverage:
- Extractor initialization and source_name property
- Basic field extraction (name, address, location, operator)
- External ID capture (OpenChargeMap UUID)
- EV-specific fields extraction (connector types, power levels, usage type)
- Phone number formatting
- Postcode formatting
- Handling missing/optional fields gracefully
- Attribute splitting (schema-defined vs discovered)
- Multiple charging connections handling
"""

import pytest
import json
from pathlib import Path


@pytest.fixture
def open_charge_map_fixture():
    """Load the OpenChargeMap test fixture"""
    fixture_path = Path(__file__).parent / "fixtures" / "open_charge_map_response.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def open_charge_map_single_station(open_charge_map_fixture):
    """Extract the first charging station from the fixtures for single-record tests"""
    return open_charge_map_fixture[0]


@pytest.fixture
def open_charge_map_fast_charger(open_charge_map_fixture):
    """Extract the second charging station (fast charger) for specific tests"""
    return open_charge_map_fixture[1]


class TestOpenChargeMapExtractorInitialization:
    """Test OpenChargeMap extractor initialization and basic properties"""

    def test_open_charge_map_extractor_can_be_imported(self):
        """Test that OpenChargeMapExtractor class can be imported"""
        try:
            from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor
            assert OpenChargeMapExtractor is not None
        except ImportError:
            pytest.fail("Failed to import OpenChargeMapExtractor - implementation not yet created")

    def test_open_charge_map_extractor_can_be_instantiated(self):
        """Test that OpenChargeMapExtractor can be instantiated"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        assert extractor is not None

    def test_open_charge_map_extractor_has_correct_source_name(self):
        """Test that source_name property returns 'open_charge_map'"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        assert extractor.source_name == "open_charge_map"


class TestOpenChargeMapExtraction:
    """Test extraction of fields from OpenChargeMap data"""

    def test_extract_basic_fields(self, open_charge_map_single_station):
        """Test extraction of basic charging station fields (name, address, coordinates)"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        # Verify basic fields
        assert extracted["entity_name"] == "St James Quarter-Level B1"
        assert extracted["street_address"] == "St James Square, Quarter, Edinburgh"
        assert extracted["latitude"] == pytest.approx(55.95479, rel=1e-6)
        assert extracted["longitude"] == pytest.approx(-3.1885916, rel=1e-6)

    def test_extract_external_id(self, open_charge_map_single_station):
        """Test that OpenChargeMap UUID is captured as external_id"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        assert "external_id" in extracted
        assert extracted["external_id"] == "EDB7E25B-6D34-477F-ADA9-0945380ECD65"

    def test_extract_postcode(self, open_charge_map_single_station):
        """Test extraction of UK postcode with correct formatting"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        assert extracted["postcode"] == "EH1 3AD"

    def test_extract_operator_phone_formatted(self, open_charge_map_single_station):
        """Test that operator phone number is formatted to E.164 UK format"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        # Should convert "020 7247 4114" to "+442072474114"
        assert extracted["phone"] == "+442072474114"

    def test_extract_entity_type_defaults_to_venue(self, open_charge_map_single_station):
        """Test that entity_type defaults to VENUE for charging stations"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        assert extracted["entity_type"] == "VENUE"

    def test_extract_ev_specific_fields_to_discovered_attributes(self, open_charge_map_single_station):
        """Test that EV-specific fields are extracted (for discovered_attributes)"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        # These should be extracted for discovered_attributes
        assert "operator_name" in extracted
        assert extracted["operator_name"] == "POD Point (UK)"

        assert "usage_type" in extracted
        assert extracted["usage_type"] == "Public - Membership Required"

        assert "is_operational" in extracted
        assert extracted["is_operational"] is True

        assert "number_of_points" in extracted
        assert extracted["number_of_points"] == 2

    def test_extract_connector_information(self, open_charge_map_single_station):
        """Test that charging connector information is extracted"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        # Should extract connection details as list
        assert "connections" in extracted
        assert isinstance(extracted["connections"], list)
        assert len(extracted["connections"]) == 1

        # Check connection details
        connection = extracted["connections"][0]
        assert connection["type"] == "Type 2 (Socket Only)"
        assert connection["power_kw"] == 7.4
        assert connection["quantity"] == 2

    def test_extract_fast_charger_details(self, open_charge_map_fast_charger):
        """Test extraction of fast charging station with different connector types"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_fast_charger)

        assert extracted["entity_name"] == "Ocean Terminal Car Park"
        assert extracted["operator_name"] == "ChargePlace Scotland"

        # Check fast charging details
        assert "connections" in extracted
        connection = extracted["connections"][0]
        assert connection["type"] == "CCS (Type 2)"
        assert connection["power_kw"] == 50.0
        assert connection["level"] == "Level 3: DC Fast Charging"

    def test_extract_usage_cost_information(self, open_charge_map_single_station):
        """Test extraction of usage cost information"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        assert "usage_cost" in extracted
        assert extracted["usage_cost"] == "Complicated tariff structure,£0.45/kWh,£0.75/kWh"

    def test_extract_access_comments(self, open_charge_map_single_station):
        """Test extraction of access comments"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        assert "access_comments" in extracted
        assert extracted["access_comments"] == "24/7 access"

    def test_extract_handles_missing_optional_fields(self):
        """Test that extractor gracefully handles missing optional fields"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        # Create minimal charging station data
        minimal_station = {
            "ID": 12345,
            "UUID": "TEST-UUID-123",
            "AddressInfo": {
                "Title": "Test Charging Station",
                "Latitude": 55.9533,
                "Longitude": -3.1883,
                "Postcode": "EH1 1AA"
            },
            "StatusType": {
                "IsOperational": True,
                "Title": "Operational"
            }
        }

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(minimal_station)

        # Should extract basic fields without crashing
        assert extracted["entity_name"] == "Test Charging Station"
        assert extracted["latitude"] == 55.9533
        assert extracted["longitude"] == -3.1883

    def test_extract_handles_missing_connections(self):
        """Test that extractor handles stations with no connection data"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        station_no_connections = {
            "ID": 12345,
            "UUID": "TEST-UUID-456",
            "AddressInfo": {
                "Title": "Test Station",
                "Latitude": 55.9533,
                "Longitude": -3.1883,
                "Postcode": "EH1 1AA"
            },
            "StatusType": {
                "IsOperational": True
            },
            "Connections": []
        }

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(station_no_connections)

        # Should handle empty connections list
        assert "connections" in extracted
        assert extracted["connections"] == []


class TestOpenChargeMapValidation:
    """Test validation of extracted OpenChargeMap data"""

    def test_validate_ensures_required_fields(self, open_charge_map_single_station):
        """Test that validation ensures required fields are present"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)
        validated = extractor.validate(extracted)

        # Required fields should be present
        assert "entity_name" in validated
        assert "entity_type" in validated

    def test_validate_phone_format(self, open_charge_map_single_station):
        """Test that validation ensures phone is in E.164 format"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)
        validated = extractor.validate(extracted)

        # Phone should be E.164 format
        if "phone" in validated:
            assert validated["phone"].startswith("+")

    def test_validate_coordinates_within_bounds(self, open_charge_map_single_station):
        """Test that validation checks coordinates are within valid ranges"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)

        # Inject invalid coordinates
        extracted["latitude"] = 999.0  # Invalid
        extracted["longitude"] = -999.0  # Invalid

        validated = extractor.validate(extracted)

        # Invalid coordinates should be removed
        assert "latitude" not in validated or validated["latitude"] != 999.0
        assert "longitude" not in validated or validated["longitude"] != -999.0

    def test_validate_raises_error_without_entity_name(self):
        """Test that validation raises error if entity_name is missing"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()

        # Empty extraction
        extracted = {"entity_type": "VENUE"}

        with pytest.raises(ValueError, match="entity_name"):
            extractor.validate(extracted)


class TestOpenChargeMapAttributeSplitting:
    """Test splitting of OpenChargeMap fields into attributes and discovered_attributes"""

    def test_split_attributes_separates_schema_and_discovered_fields(self, open_charge_map_single_station):
        """Test that split_attributes correctly separates schema-defined vs discovered fields"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)
        validated = extractor.validate(extracted)
        attributes, discovered = extractor.split_attributes(validated)

        # Schema-defined fields should be in attributes
        assert "entity_name" in attributes
        assert "latitude" in attributes
        assert "longitude" in attributes
        assert "postcode" in attributes

        # EV-specific fields should be in discovered_attributes
        assert "operator_name" in discovered
        assert "usage_type" in discovered
        assert "connections" in discovered
        assert "number_of_points" in discovered

    def test_split_attributes_preserves_all_data(self, open_charge_map_single_station):
        """Test that no data is lost during attribute splitting"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_single_station)
        validated = extractor.validate(extracted)
        attributes, discovered = extractor.split_attributes(validated)

        # Total fields should be preserved
        total_fields = len(attributes) + len(discovered)
        original_fields = len(validated)
        assert total_fields == original_fields


class TestOpenChargeMapEndToEnd:
    """End-to-end tests for complete extraction workflow"""

    def test_complete_extraction_workflow(self, open_charge_map_single_station):
        """Test complete extraction workflow: extract → validate → split"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()

        # Step 1: Extract
        extracted = extractor.extract(open_charge_map_single_station)
        assert "entity_name" in extracted
        assert "operator_name" in extracted

        # Step 2: Validate
        validated = extractor.validate(extracted)
        assert "entity_name" in validated
        assert validated["entity_name"] == "St James Quarter-Level B1"

        # Step 3: Split attributes
        attributes, discovered = extractor.split_attributes(validated)
        assert "entity_name" in attributes
        assert "operator_name" in discovered
        assert "connections" in discovered

    def test_extraction_preserves_critical_ev_data(self, open_charge_map_fast_charger):
        """Test that extraction preserves all critical EV charging data"""
        from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor

        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(open_charge_map_fast_charger)

        # Critical EV data should be preserved
        assert extracted["operator_name"] == "ChargePlace Scotland"
        assert extracted["usage_type"] == "Public - Membership Required"
        assert len(extracted["connections"]) > 0
        assert extracted["connections"][0]["power_kw"] == 50.0
        assert extracted["is_operational"] is True
