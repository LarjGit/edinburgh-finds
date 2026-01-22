"""
Tests for Google Places Extractor

This module tests the GooglePlacesExtractor which transforms raw Google Places
API responses into structured listing fields following the extraction schema.

Test Coverage:
- Extractor initialization and source_name property
- Basic field extraction (name, address, location, rating)
- External ID capture (Google Place ID)
- Phone number formatting (national → E.164 format)
- Postcode extraction and formatting
- Website extraction
- Opening hours extraction
- Handling missing/optional fields gracefully
- Attribute splitting (schema-defined vs discovered)
"""

import pytest
import json
from pathlib import Path


@pytest.fixture
def google_places_fixture():
    """Load the Google Places test fixture"""
    fixture_path = Path(__file__).parent / "fixtures" / "google_places_venue_response.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def google_places_single_venue(google_places_fixture):
    """Extract the first venue from the fixtures for single-record tests"""
    return google_places_fixture["places"][0]


class TestGooglePlacesExtractorInitialization:
    """Test Google Places extractor initialization and basic properties"""

    def test_google_places_extractor_can_be_imported(self):
        """Test that GooglePlacesExtractor class can be imported"""
        try:
            from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor
            assert GooglePlacesExtractor is not None
        except ImportError:
            pytest.fail("Failed to import GooglePlacesExtractor - implementation not yet created")

    def test_google_places_extractor_can_be_instantiated(self):
        """Test that GooglePlacesExtractor can be instantiated"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        assert extractor is not None

    def test_google_places_extractor_has_correct_source_name(self):
        """Test that source_name property returns 'google_places'"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        assert extractor.source_name == "google_places"


class TestGooglePlacesExtraction:
    """Test extraction of fields from Google Places data"""

    def test_extract_basic_fields(self, google_places_single_venue):
        """Test extraction of basic venue fields (name, address, coordinates)"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)

        # Verify basic fields
        assert extracted["entity_name"] == "Game4Padel | Edinburgh Park"
        assert extracted["street_address"] == "1, New Park Square, Edinburgh Park, Edinburgh EH12 9GR, UK"
        assert extracted["latitude"] == pytest.approx(55.930189299999995, rel=1e-6)
        assert extracted["longitude"] == pytest.approx(-3.3153414999999997, rel=1e-6)

    def test_extract_external_id(self, google_places_single_venue):
        """Test that Google Place ID is captured as external_id"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)

        assert "external_id" in extracted
        assert extracted["external_id"] == "ChIJhwNDsAjFh0gRDARGLR5vtdI"

    def test_extract_rating_fields(self, google_places_single_venue):
        """Test extraction of rating and user rating count"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)

        assert extracted["rating"] == 4.4
        assert extracted["user_rating_count"] == 15

    def test_extract_website(self, google_places_single_venue):
        """Test extraction of website URL"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)

        assert extracted["website"] == "https://www.game4padel.co.uk/edinburgh-park"

    def test_extract_postcode_from_address(self, google_places_single_venue):
        """Test that postcode is extracted and formatted from formattedAddress"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)

        # Should extract EH12 9GR with correct spacing
        assert extracted["postcode"] == "EH12 9GR"

    def test_extract_phone_as_e164(self, google_places_single_venue):
        """Test that phone number is formatted to E.164 UK format"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)

        # Should convert "0131 539 7071" to "+441315397071"
        assert extracted["phone"] == "+441315397071"

    def test_extract_entity_type_is_not_defaulted(self, google_places_single_venue):
        """Test that entity_type is NOT defaulted to VENUE (decoupled logic)"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)

        # Entity type should not be present or should be None
        assert extracted.get("entity_type") is None

    def test_extract_handles_missing_optional_fields(self, google_places_single_venue):
        """Test that extractor gracefully handles missing optional fields"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        # Create venue data without optional fields
        minimal_venue = {
            "id": "test_id",
            "displayName": {
                "text": "Test Venue"
            },
            "formattedAddress": "123 Test St, Edinburgh EH1 1AA, UK",
            "location": {
                "latitude": 55.9533,
                "longitude": -3.1883
            }
        }

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(minimal_venue)

        # Basic fields should be present
        assert extracted["entity_name"] == "Test Venue"
        assert extracted["street_address"] == "123 Test St, Edinburgh EH1 1AA, UK"

        # Optional fields should be None or absent
        assert extracted.get("phone") is None
        assert extracted.get("website") is None
        assert extracted.get("rating") is None


class TestGooglePlacesValidation:
    """Test validation of extracted fields"""

    def test_validate_required_fields_present(self, google_places_single_venue):
        """Test that validation ensures required fields are present"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)
        validated = extractor.validate(extracted)

        # Required fields must be present
        assert "entity_name" in validated
        # entity_type is no longer required at validation stage
        # assert "entity_type" in validated

    def test_validate_normalizes_phone_format(self, google_places_single_venue):
        """Test that validation ensures phone is in E.164 format"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)
        validated = extractor.validate(extracted)

        # Phone should be E.164 format
        assert validated["phone"].startswith("+44")
        assert " " not in validated["phone"]  # No spaces
        assert "-" not in validated["phone"]  # No dashes


class TestGooglePlacesAttributeSplitting:
    """Test splitting of extracted fields into attributes and discovered_attributes"""

    def test_split_attributes_separates_schema_fields(self, google_places_single_venue):
        """Test that schema-defined fields go into attributes"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)
        attributes, discovered = extractor.split_attributes(extracted)

        # Schema-defined fields should be in attributes
        assert "entity_name" in attributes
        assert "street_address" in attributes
        assert "latitude" in attributes
        assert "longitude" in attributes
        assert "phone" in attributes

    def test_split_attributes_puts_extra_fields_in_discovered(self, google_places_single_venue):
        """Test that non-schema fields go into discovered_attributes"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(google_places_single_venue)

        # Add some custom fields that aren't in schema
        extracted["google_maps_uri"] = google_places_single_venue["googleMapsUri"]
        extracted["types"] = google_places_single_venue["types"]

        attributes, discovered = extractor.split_attributes(extracted)

        # Non-schema fields should be in discovered_attributes
        assert "google_maps_uri" in discovered
        assert "types" in discovered


class TestPhoneNumberFormatting:
    """Test phone number formatting utility"""

    def test_format_phone_uk_converts_national_to_e164(self):
        """Test conversion of UK national format to E.164"""
        from engine.extraction.extractors.google_places_extractor import format_phone_uk

        # Various UK national formats
        assert format_phone_uk("0131 539 7071") == "+441315397071"
        assert format_phone_uk("01315397071") == "+441315397071"
        assert format_phone_uk("0131-539-7071") == "+441315397071"
        assert format_phone_uk("(0131) 539 7071") == "+441315397071"

    def test_format_phone_uk_handles_mobile_numbers(self):
        """Test conversion of UK mobile numbers"""
        from engine.extraction.extractors.google_places_extractor import format_phone_uk

        # Use valid UK mobile number patterns (07xxx numbers)
        assert format_phone_uk("07911 123456") == "+447911123456"
        assert format_phone_uk("07911123456") == "+447911123456"

    def test_format_phone_uk_preserves_already_formatted(self):
        """Test that already E.164 formatted numbers are preserved"""
        from engine.extraction.extractors.google_places_extractor import format_phone_uk

        assert format_phone_uk("+441315397071") == "+441315397071"
        assert format_phone_uk("+447911123456") == "+447911123456"

    def test_format_phone_uk_handles_international_format(self):
        """Test handling of international format with country code"""
        from engine.extraction.extractors.google_places_extractor import format_phone_uk

        assert format_phone_uk("+44 131 539 7071") == "+441315397071"
        assert format_phone_uk("+44 (0) 131 539 7071") == "+441315397071"

    def test_format_phone_uk_returns_none_for_invalid(self):
        """Test that invalid phone numbers return None"""
        from engine.extraction.extractors.google_places_extractor import format_phone_uk

        assert format_phone_uk("not a phone") is None
        assert format_phone_uk("123") is None
        assert format_phone_uk("") is None
        assert format_phone_uk(None) is None


class TestPostcodeFormatting:
    """Test postcode extraction and formatting utility"""

    def test_format_postcode_uk_adds_correct_spacing(self):
        """Test that postcodes are formatted with correct spacing"""
        from engine.extraction.extractors.google_places_extractor import format_postcode_uk

        # Various formats, should all become "EH12 9GR"
        assert format_postcode_uk("EH129GR") == "EH12 9GR"
        assert format_postcode_uk("EH12 9GR") == "EH12 9GR"
        assert format_postcode_uk("eh12 9gr") == "EH12 9GR"
        assert format_postcode_uk("eh129gr") == "EH12 9GR"

    def test_format_postcode_uk_handles_various_valid_formats(self):
        """Test formatting of various valid UK postcode formats"""
        from engine.extraction.extractors.google_places_extractor import format_postcode_uk

        # Different UK postcode patterns
        assert format_postcode_uk("SW1A 1AA") == "SW1A 1AA"
        assert format_postcode_uk("M1 1AA") == "M1 1AA"
        assert format_postcode_uk("B33 8TH") == "B33 8TH"
        assert format_postcode_uk("CR2 6XH") == "CR2 6XH"
        assert format_postcode_uk("DN55 1PT") == "DN55 1PT"

    def test_format_postcode_uk_extracts_from_full_address(self):
        """Test extraction of postcode from full address string"""
        from engine.extraction.extractors.google_places_extractor import extract_postcode_from_address

        address = "1, New Park Square, Edinburgh Park, Edinburgh EH12 9GR, UK"
        assert extract_postcode_from_address(address) == "EH12 9GR"

        address2 = "123 Main Street, London, SW1A 1AA, United Kingdom"
        assert extract_postcode_from_address(address2) == "SW1A 1AA"

    def test_format_postcode_uk_returns_none_for_invalid(self):
        """Test that invalid postcodes return None"""
        from engine.extraction.extractors.google_places_extractor import format_postcode_uk

        assert format_postcode_uk("not a postcode") is None
        assert format_postcode_uk("12345") is None
        assert format_postcode_uk("") is None
        assert format_postcode_uk(None) is None
