"""
Tests for Sport Scotland Extractor

This module tests the SportScotlandExtractor which transforms raw Sport Scotland
WFS GeoJSON responses into structured listing fields following the extraction schema.

Sport Scotland data comes from WFS (Web Feature Service) in GeoJSON format, providing
official sports facility data including tennis courts, pitches, swimming pools, etc.

Test Coverage:
- Extractor initialization and source_name property
- GeoJSON feature parsing (geometry and properties)
- Basic field extraction (name, address, location, facility type)
- External ID capture (Sport Scotland feature ID)
- Sport Scotland-specific attributes (facility types, sports offered, surface types)
- Handling missing/optional fields gracefully
- Attribute splitting (schema-defined vs discovered)
"""

import pytest
import json
from pathlib import Path


@pytest.fixture
def sport_scotland_fixture():
    """Load the Sport Scotland test fixture"""
    fixture_path = Path(__file__).parent / "fixtures" / "sport_scotland_facility_response.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def sport_scotland_single_feature(sport_scotland_fixture):
    """Extract the first feature from the fixtures for single-record tests"""
    return sport_scotland_fixture["features"][0]


class TestSportScotlandExtractorInitialization:
    """Test Sport Scotland extractor initialization and basic properties"""

    def test_sport_scotland_extractor_can_be_imported(self):
        """Test that SportScotlandExtractor class can be imported"""
        try:
            from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor
            assert SportScotlandExtractor is not None
        except ImportError:
            pytest.fail("Failed to import SportScotlandExtractor - implementation not yet created")

    def test_sport_scotland_extractor_can_be_instantiated(self):
        """Test that SportScotlandExtractor can be instantiated"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        assert extractor is not None

    def test_sport_scotland_extractor_has_correct_source_name(self):
        """Test that source_name property returns 'sport_scotland'"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        assert extractor.source_name == "sport_scotland"


class TestSportScotlandGeoJSONParsing:
    """Test parsing of GeoJSON feature structure"""

    def test_extract_geometry_coordinates(self, sport_scotland_single_feature):
        """Test extraction of coordinates from GeoJSON geometry"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        # GeoJSON coordinates are [longitude, latitude]
        assert extracted["latitude"] == pytest.approx(55.9533, rel=1e-4)
        assert extracted["longitude"] == pytest.approx(-3.1883, rel=1e-4)

    def test_extract_properties_from_feature(self, sport_scotland_single_feature):
        """Test extraction of properties from GeoJSON feature"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        # Verify properties are extracted
        assert "entity_name" in extracted
        assert extracted["entity_name"] == "Craiglockhart Tennis Centre"


class TestSportScotlandExtraction:
    """Test extraction of fields from Sport Scotland data"""

    def test_extract_basic_fields(self, sport_scotland_single_feature):
        """Test extraction of basic venue fields (name, address, coordinates)"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        # Verify basic fields
        assert extracted["entity_name"] == "Craiglockhart Tennis Centre"
        assert extracted["street_address"] == "177 Colinton Road, Edinburgh"
        assert extracted["latitude"] == pytest.approx(55.9533, rel=1e-4)
        assert extracted["longitude"] == pytest.approx(-3.1883, rel=1e-4)

    def test_extract_external_id(self, sport_scotland_single_feature):
        """Test that Sport Scotland feature ID is captured as external_id"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        assert "external_id" in extracted
        assert extracted["external_id"] == "tennis_courts.1"

    def test_extract_postcode(self, sport_scotland_single_feature):
        """Test extraction of postcode"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        assert extracted["postcode"] == "EH14 1BH"

    def test_extract_phone(self, sport_scotland_single_feature):
        """Test extraction and formatting of phone number"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        # Should be formatted to E.164
        assert extracted["phone"] == "+441314441969"

    def test_extract_website(self, sport_scotland_single_feature):
        """Test extraction of website URL"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        assert extracted["website"] == "http://www.edinburghleisure.co.uk"

    def test_extract_entity_type_defaults_to_venue(self, sport_scotland_single_feature):
        """Test that entity_type defaults to VENUE for Sport Scotland results"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        assert extracted["entity_type"] == "VENUE"

    def test_extract_handles_missing_optional_fields(self, sport_scotland_single_feature):
        """Test that extractor gracefully handles missing optional fields"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        # Create minimal feature data without optional fields
        minimal_feature = {
            "type": "Feature",
            "id": "test.1",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.1883, 55.9533]
            },
            "properties": {
                "name": "Test Facility"
            }
        }

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(minimal_feature)

        # Basic fields should be present
        assert extracted["entity_name"] == "Test Facility"
        assert extracted["latitude"] == pytest.approx(55.9533, rel=1e-4)
        assert extracted["longitude"] == pytest.approx(-3.1883, rel=1e-4)

        # Optional fields should be None or absent
        assert extracted.get("phone") is None
        assert extracted.get("website") is None
        assert extracted.get("postcode") is None


class TestSportScotlandFacilitySpecificFields:
    """Test extraction of Sport Scotland-specific facility attributes"""

    def test_extract_facility_type(self, sport_scotland_single_feature):
        """Test extraction of facility type"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        # Facility type goes to discovered_attributes as it's source-specific
        assert "facility_type" in extracted
        assert extracted["facility_type"] == "Tennis Courts"

    def test_extract_tennis_specific_attributes(self, sport_scotland_single_feature):
        """Test extraction of tennis-specific attributes"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        # Tennis-specific fields
        assert extracted["tennis"] is True
        assert extracted["tennis_total_courts"] == 6
        assert extracted["tennis_outdoor_courts"] == 6
        assert extracted["tennis_floodlit_courts"] == 6

    def test_extract_surface_type(self, sport_scotland_single_feature):
        """Test extraction of surface type attribute"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        assert "surface_type" in extracted
        assert extracted["surface_type"] == "Hard Court"

    def test_extract_ownership(self, sport_scotland_single_feature):
        """Test extraction of ownership attribute"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)

        assert "ownership" in extracted
        assert extracted["ownership"] == "Local Authority"


class TestSportScotlandValidation:
    """Test validation of extracted fields"""

    def test_validate_required_fields_present(self, sport_scotland_single_feature):
        """Test that validation ensures required fields are present"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)
        validated = extractor.validate(extracted)

        # Required fields must be present
        assert "entity_name" in validated
        assert "entity_type" in validated
        assert "latitude" in validated
        assert "longitude" in validated

    def test_validate_normalizes_phone_format(self, sport_scotland_single_feature):
        """Test that validation ensures phone is in E.164 format"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)
        validated = extractor.validate(extracted)

        # Phone should be E.164 format
        if validated.get("phone"):
            assert validated["phone"].startswith("+44")
            assert " " not in validated["phone"]  # No spaces
            assert "-" not in validated["phone"]  # No dashes


class TestSportScotlandAttributeSplitting:
    """Test splitting of extracted fields into attributes and discovered_attributes"""

    def test_split_attributes_separates_schema_fields(self, sport_scotland_single_feature):
        """Test that schema-defined fields go into attributes"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)
        attributes, discovered = extractor.split_attributes(extracted)

        # Schema-defined fields should be in attributes
        assert "entity_name" in attributes
        assert "street_address" in attributes
        assert "latitude" in attributes
        assert "longitude" in attributes
        assert "phone" in attributes
        assert "tennis" in attributes
        assert "tennis_total_courts" in attributes

    def test_split_attributes_puts_extra_fields_in_discovered(self, sport_scotland_single_feature):
        """Test that non-schema fields go into discovered_attributes"""
        from engine.extraction.extractors.sport_scotland_extractor import SportScotlandExtractor

        extractor = SportScotlandExtractor()
        extracted = extractor.extract(sport_scotland_single_feature)
        attributes, discovered = extractor.split_attributes(extracted)

        # Source-specific fields should be in discovered_attributes
        assert "facility_type" in discovered
        assert "surface_type" in discovered
        assert "ownership" in discovered
