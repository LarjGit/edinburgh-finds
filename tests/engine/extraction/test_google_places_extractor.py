"""
Tests for Google Places Extractor

Verifies correct extraction of entity fields from Google Places API responses.
Tests both API v1 format (displayName.text) and legacy format (name).
"""

import pytest
from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor


def test_extract_entity_name_from_legacy_format(mock_ctx):
    """
    Verify extractor maps 'name' field to 'entity_name' (legacy/v0 API format).

    This ensures backward compatibility with older Google Places API responses
    or simplified test data that uses 'name' instead of 'displayName.text'.
    """
    extractor = GooglePlacesExtractor()

    raw_data = {
        'place_id': 'ChIJ_TEST123',
        'name': 'Powerleague Portobello',
        'geometry': {
            'location': {
                'lat': 55.9504,
                'lng': -3.1115
            }
        },
        'formatted_address': '15 Stanley St, Edinburgh EH6 4SW, UK'
    }

    extracted = extractor.extract(raw_data, ctx=mock_ctx)

    assert 'entity_name' in extracted
    assert extracted['entity_name'] == 'Powerleague Portobello'


def test_extract_entity_name_from_api_v1_format(mock_ctx):
    """
    Verify extractor maps 'displayName.text' to 'entity_name' (API v1 format).

    Google Places API v1 uses nested displayName object with text field.
    """
    extractor = GooglePlacesExtractor()

    raw_data = {
        'id': 'ChIJ_TEST123',
        'displayName': {
            'text': 'Powerleague Portobello',
            'languageCode': 'en'
        },
        'location': {
            'latitude': 55.9504,
            'longitude': -3.1115
        },
        'formattedAddress': '15 Stanley St, Edinburgh EH6 4SW, UK'
    }

    extracted = extractor.extract(raw_data, ctx=mock_ctx)

    assert 'entity_name' in extracted
    assert extracted['entity_name'] == 'Powerleague Portobello'


def test_extract_prefers_display_name_over_name(mock_ctx):
    """
    Verify extractor prefers displayName.text over name when both present.

    This ensures API v1 format takes precedence for consistency.
    """
    extractor = GooglePlacesExtractor()

    raw_data = {
        'id': 'ChIJ_TEST123',
        'name': 'Old Name',
        'displayName': {
            'text': 'Correct Name'
        },
        'location': {
            'latitude': 55.9504,
            'longitude': -3.1115
        }
    }

    extracted = extractor.extract(raw_data, ctx=mock_ctx)

    assert extracted['entity_name'] == 'Correct Name'


def test_validate_requires_entity_name():
    """
    Verify validation fails when entity_name is missing or empty.

    entity_name is a required field and must be present for validation to pass.
    """
    extractor = GooglePlacesExtractor()

    # Missing entity_name
    with pytest.raises(ValueError, match="Missing required field: entity_name"):
        extractor.validate({})

    # Empty entity_name
    with pytest.raises(ValueError, match="Missing required field: entity_name"):
        extractor.validate({'entity_name': ''})


def test_extract_and_validate_complete_legacy_payload(mock_ctx):
    """
    Verify complete extraction and validation pipeline for legacy format.

    This is the integration test that ensures Phase 1 completes successfully
    with real-world legacy format data.
    """
    extractor = GooglePlacesExtractor()

    raw_data = {
        'place_id': 'ChIJ_TEST123',
        'name': 'Powerleague Portobello',
        'geometry': {
            'location': {
                'lat': 55.9504,
                'lng': -3.1115
            }
        },
        'formatted_address': '15 Stanley St, Edinburgh EH6 4SW, UK',
        'international_phone_number': '+44 131 669 0040',
        'website': 'https://www.powerleague.co.uk/portobello',
        'rating': 4.5,
        'user_ratings_total': 120
    }

    # Phase 1: Extract
    extracted = extractor.extract(raw_data, ctx=mock_ctx)

    # Phase 1: Validate
    validated = extractor.validate(extracted)

    # Assertions: Phase 1 must produce valid entity_name
    assert 'entity_name' in validated
    assert validated['entity_name'] == 'Powerleague Portobello'
    assert validated['entity_name']  # Non-empty

    # Additional fields should be present
    assert 'latitude' in validated
    assert 'longitude' in validated
    assert validated['latitude'] == 55.9504
    assert validated['longitude'] == -3.1115
