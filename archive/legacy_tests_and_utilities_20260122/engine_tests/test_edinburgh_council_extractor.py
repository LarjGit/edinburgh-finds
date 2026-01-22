"""
Tests for Edinburgh Council Extractor

This module tests the EdinburghCouncilExtractor which transforms raw Edinburgh Council
GeoJSON responses into structured listing fields following the extraction schema.

Edinburgh Council data comes in GeoJSON format from ArcGIS, providing local facility
data including sports centers, community facilities, and other council-managed venues.

Test Coverage:
- Extractor initialization and source_name property
- GeoJSON feature parsing (geometry and properties)
- Basic field extraction (name, address, location, facility type)
- External ID capture (Edinburgh Council feature ID)
- Handling multiple name field formats (NAME, FACILITY_NAME, SITE_NAME)
- Category extraction from various fields (CATEGORY, TYPE, FACILITY_TYPE)
- Handling missing/optional fields gracefully
- Attribute splitting (schema-defined vs discovered)
"""

import pytest
import json
from pathlib import Path


@pytest.fixture
def edinburgh_council_fixture():
    """Load the Edinburgh Council test fixture"""
    fixture_path = Path(__file__).parent / "fixtures" / "edinburgh_council_feature_response.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def edinburgh_council_single_feature(edinburgh_council_fixture):
    """Extract the first feature from the fixtures for single-record tests"""
    return edinburgh_council_fixture["features"][0]


class TestEdinburghCouncilExtractorInitialization:
    """Test Edinburgh Council extractor initialization and basic properties"""

    def test_edinburgh_council_extractor_can_be_imported(self):
        """Test that EdinburghCouncilExtractor class can be imported"""
        try:
            from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor
            assert EdinburghCouncilExtractor is not None
        except ImportError:
            pytest.fail("Failed to import EdinburghCouncilExtractor - implementation not yet created")

    def test_edinburgh_council_extractor_can_be_instantiated(self):
        """Test that EdinburghCouncilExtractor can be instantiated"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        assert extractor is not None

    def test_edinburgh_council_extractor_has_correct_source_name(self):
        """Test that source_name property returns 'edinburgh_council'"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        assert extractor.source_name == "edinburgh_council"


class TestEdinburghCouncilGeoJSONParsing:
    """Test parsing of GeoJSON feature structure"""

    def test_extract_geometry_coordinates(self, edinburgh_council_single_feature):
        """Test extraction of coordinates from GeoJSON geometry"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        # GeoJSON coordinates are [longitude, latitude]
        assert extracted["latitude"] == pytest.approx(55.953, rel=1e-4)
        assert extracted["longitude"] == pytest.approx(-3.188, rel=1e-4)

    def test_extract_properties_from_feature(self, edinburgh_council_single_feature):
        """Test extraction of properties from GeoJSON feature"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        # Verify properties are extracted
        assert "entity_name" in extracted
        assert extracted["entity_name"] == "Portobello Swim Centre"


class TestEdinburghCouncilExtraction:
    """Test extraction of fields from Edinburgh Council data"""

    def test_extract_basic_fields(self, edinburgh_council_single_feature):
        """Test extraction of basic venue fields (name, address, coordinates)"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        # Verify basic fields
        assert extracted["entity_name"] == "Portobello Swim Centre"
        assert extracted["street_address"] == "57 The Promenade"
        assert extracted["latitude"] == pytest.approx(55.953, rel=1e-4)
        assert extracted["longitude"] == pytest.approx(-3.188, rel=1e-4)

    def test_extract_external_id(self, edinburgh_council_single_feature):
        """Test that Edinburgh Council feature ID is captured as external_id"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        assert "external_id" in extracted
        assert extracted["external_id"] == "facilities.123"

    def test_extract_postcode(self, edinburgh_council_single_feature):
        """Test extraction of postcode"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        assert extracted["postcode"] == "EH15 2BS"

    def test_extract_phone(self, edinburgh_council_single_feature):
        """Test extraction and formatting of phone number"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        # Should be formatted to E.164
        assert extracted["phone"] == "+441316696888"

    def test_extract_email(self, edinburgh_council_single_feature):
        """Test extraction of email"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        assert extracted["email"] == "portobello@edinburghleisure.co.uk"

    def test_extract_website(self, edinburgh_council_single_feature):
        """Test extraction of website URL"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        assert extracted["website"] == "http://www.edinburghleisure.co.uk"

    def test_extract_summary(self, edinburgh_council_single_feature):
        """Test extraction of description/summary"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        assert extracted["summary"] == "Modern swimming centre with 25m pool, learner pool, and gym facilities"

    def test_extract_categories(self, edinburgh_council_single_feature):
        """Test extraction of categories from multiple fields"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        # Should extract from FACILITY_TYPE and TYPE
        assert "categories" in extracted
        assert "Swimming Pool" in extracted["categories"]
        assert "Leisure Facility" in extracted["categories"]

    def test_extract_entity_type_defaults_to_venue(self, edinburgh_council_single_feature):
        """Test that entity_type defaults to VENUE for Edinburgh Council results"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        assert extracted["entity_type"] == "VENUE"

    def test_extract_city_defaults_to_edinburgh(self, edinburgh_council_single_feature):
        """Test that city defaults to Edinburgh for Edinburgh Council data"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        assert extracted["city"] == "Edinburgh"

    def test_extract_country_defaults_to_scotland(self, edinburgh_council_single_feature):
        """Test that country defaults to Scotland for Edinburgh Council data"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        assert extracted["country"] == "Scotland"

    def test_extract_handles_missing_optional_fields(self):
        """Test that extractor gracefully handles missing optional fields"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        # Create minimal feature data without optional fields
        minimal_feature = {
            "type": "Feature",
            "id": "test.1",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.188, 55.953]
            },
            "properties": {
                "NAME": "Test Facility"
            }
        }

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(minimal_feature)

        # Basic fields should be present
        assert extracted["entity_name"] == "Test Facility"
        assert extracted["latitude"] == pytest.approx(55.953, rel=1e-4)
        assert extracted["longitude"] == pytest.approx(-3.188, rel=1e-4)

        # Optional fields should be None or absent
        assert extracted.get("phone") is None
        assert extracted.get("website") is None
        assert extracted.get("email") is None

    def test_extract_handles_alternative_name_fields(self):
        """Test extraction of name from alternative fields (FACILITY_NAME, SITE_NAME)"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()

        # Test FACILITY_NAME
        feature_with_facility_name = {
            "type": "Feature",
            "id": "test.1",
            "geometry": {"type": "Point", "coordinates": [-3.188, 55.953]},
            "properties": {"FACILITY_NAME": "Test Facility"}
        }
        extracted = extractor.extract(feature_with_facility_name)
        assert extracted["entity_name"] == "Test Facility"

        # Test SITE_NAME
        feature_with_site_name = {
            "type": "Feature",
            "id": "test.2",
            "geometry": {"type": "Point", "coordinates": [-3.188, 55.953]},
            "properties": {"SITE_NAME": "Test Site"}
        }
        extracted = extractor.extract(feature_with_site_name)
        assert extracted["entity_name"] == "Test Site"


class TestEdinburghCouncilValidation:
    """Test validation of extracted fields"""

    def test_validate_required_fields_present(self, edinburgh_council_single_feature):
        """Test that validation ensures required fields are present"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)
        validated = extractor.validate(extracted)

        # Required fields must be present
        assert "entity_name" in validated
        assert "entity_type" in validated

    def test_validate_normalizes_phone_format(self, edinburgh_council_single_feature):
        """Test that validation ensures phone is in E.164 format"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)
        validated = extractor.validate(extracted)

        # Phone should be E.164 format
        if validated.get("phone"):
            assert validated["phone"].startswith("+44")
            assert " " not in validated["phone"]  # No spaces
            assert "-" not in validated["phone"]  # No dashes


class TestEdinburghCouncilAttributeSplitting:
    """Test splitting of extracted fields into attributes and discovered_attributes"""

    def test_split_attributes_separates_schema_fields(self, edinburgh_council_single_feature):
        """Test that schema-defined fields go into attributes"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)
        attributes, discovered = extractor.split_attributes(extracted)

        # Schema-defined fields should be in attributes
        assert "entity_name" in attributes
        assert "street_address" in attributes
        assert "latitude" in attributes
        assert "longitude" in attributes
        assert "phone" in attributes
        assert "email" in attributes

    def test_split_attributes_puts_extra_fields_in_discovered(self, edinburgh_council_single_feature):
        """Test that non-schema fields go into discovered_attributes"""
        from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor

        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(edinburgh_council_single_feature)

        # Add council-specific fields to test discovered attributes
        extracted["DATASET_NAME"] = edinburgh_council_single_feature["properties"]["DATASET_NAME"]
        extracted["CAPACITY"] = edinburgh_council_single_feature["properties"]["CAPACITY"]

        attributes, discovered = extractor.split_attributes(extracted)

        # Council-specific fields should be in discovered_attributes
        assert "DATASET_NAME" in discovered
        assert "CAPACITY" in discovered
