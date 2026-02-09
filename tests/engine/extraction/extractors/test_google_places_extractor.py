"""
Tests for Google Places Extractor

Validates compliance with:
- system-vision.md Invariant 1 (Engine Purity)
- docs/target-architecture.md Section 4.2 (Extraction Boundary Contract)
"""

import inspect
import pytest
from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor


class TestEnginePurity:
    """Validates system-vision.md Invariant 1: Engine Purity"""

    def test_extractor_contains_no_domain_literals(self):
        """
        Validates: system-vision.md Invariant 1 (Engine Purity)

        The engine must contain zero domain knowledge. No domain-specific
        terms may exist in engine code.

        Forbidden terms: tennis, padel, wine, restaurant (and variations)
        """
        source = inspect.getsource(GooglePlacesExtractor)

        # Forbidden domain-specific terms
        forbidden = ["tennis", "padel", "wine", "restaurant"]

        violations = []
        for term in forbidden:
            if term.lower() in source.lower():
                violations.append(term)

        assert not violations, (
            f"Engine Purity violation (system-vision.md Invariant 1): "
            f"Found forbidden domain terms in extractor: {violations}. "
            f"Engine code must contain zero domain knowledge."
        )


class TestExtractionBoundary:
    """Validates docs/target-architecture.md Section 4.2: Extraction Boundary Contract"""

    def test_extractor_outputs_only_primitives_and_raw_observations(self, mock_ctx):
        """
        Validates: docs/target-architecture.md Section 4.2 (Extraction Boundary)

        Phase 1 extractors must output ONLY:
        - Schema primitives (entity_name, latitude, longitude, etc.)
        - Raw observations (categories, google_maps_uri, connector-native fields)

        FORBIDDEN outputs:
        - canonical_* dimensions
        - modules or module fields
        - domain-specific interpreted fields (e.g., tennis_*, padel_*)
        """
        extractor = GooglePlacesExtractor()

        # Mock Google Places API v1 response
        raw_data = {
            "id": "ChIJ_TEST_PLACE_ID",
            "displayName": {"text": "Test Sports Facility"},
            "formattedAddress": "123 Test Street, Edinburgh EH1 1AA, UK",
            "location": {
                "latitude": 55.9533,
                "longitude": -3.1883
            },
            "internationalPhoneNumber": "+44 131 234 5678",
            "websiteUri": "https://example.com",
            "rating": 4.5,
            "userRatingCount": 100,
            "types": ["sports_complex", "gym"],
            "googleMapsUri": "https://maps.google.com/?cid=123"
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Forbidden: canonical_* dimensions
        canonical_fields = [
            "canonical_activities", "canonical_roles",
            "canonical_place_types", "canonical_access"
        ]

        violations = []
        for field in canonical_fields:
            if field in extracted:
                violations.append(field)

        assert not violations, (
            f"Extraction Boundary violation (architecture.md 4.2): "
            f"Extractor emitted forbidden canonical dimensions: {violations}. "
            f"Phase 1 extractors must output ONLY schema primitives + raw observations. "
            f"Canonical dimensions belong in Phase 2 (Lens Application)."
        )

        # Forbidden: modules field
        assert "modules" not in extracted, (
            "Extraction Boundary violation: 'modules' field belongs in Phase 2 "
            "(Lens Application), not Phase 1 extraction."
        )

        # Forbidden: Domain-specific interpreted fields
        forbidden_prefixes = ["tennis_", "padel_", "wine_", "restaurant_"]
        domain_violations = []

        for key in extracted.keys():
            for prefix in forbidden_prefixes:
                if key.startswith(prefix):
                    domain_violations.append(key)

        assert not domain_violations, (
            f"Extraction Boundary violation (architecture.md 4.2): "
            f"Extractor emitted forbidden domain-specific fields: {domain_violations}. "
            f"Phase 1 extractors must output ONLY schema primitives + raw observations. "
            f"Domain interpretation belongs in Phase 2 (Lens Application)."
        )

    def test_split_attributes_separates_schema_and_discovered(self, mock_ctx):
        """
        Validates split_attributes() correctly separates schema fields from discovered attributes

        Schema-defined fields → attributes dict
        Non-schema fields (Google-specific) → discovered_attributes dict
        """
        extractor = GooglePlacesExtractor()

        # Mock response with both schema and non-schema fields
        raw_data = {
            "displayName": {"text": "Test Place"},
            "formattedAddress": "123 Test St, Edinburgh EH1 1AA",
            "location": {"latitude": 55.9533, "longitude": -3.1883},
            "internationalPhoneNumber": "+44 131 234 5678",
            "websiteUri": "https://example.com",
            "googleMapsUri": "https://maps.google.com/?cid=123",  # Non-schema field
            "types": ["sports_complex"]  # Mapped to categories (non-schema)
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)
        attributes, discovered = extractor.split_attributes(extracted)

        # Schema fields should be in attributes
        assert "entity_name" in attributes
        assert "street_address" in attributes
        assert "latitude" in attributes
        assert "longitude" in attributes
        assert "phone" in attributes
        assert "postcode" in attributes

        # Non-schema fields should be in discovered_attributes
        # Note: "website" goes to discovered because schema field is "website_url"
        # Note: "raw_categories" excluded from schema but extractors can populate it
        assert "website" in discovered
        assert "google_maps_uri" in discovered
        assert "raw_categories" in discovered

        # Verify no canonical fields in either dict
        for field in ["canonical_activities", "canonical_roles", "canonical_place_types"]:
            assert field not in attributes
            assert field not in discovered


class TestExtractionCorrectness:
    """Validates extractor correctly extracts primitives and raw observations"""

    @pytest.fixture
    def sample_google_places_v1_response(self):
        """Sample Google Places API v1 response for testing"""
        return {
            "id": "ChIJNWKj_TEST_ID",
            "displayName": {"text": "Meadowbank Sports Centre"},
            "formattedAddress": "139 London Road, Edinburgh EH7 6AE, UK",
            "location": {
                "latitude": 55.9533,
                "longitude": -3.1883
            },
            "internationalPhoneNumber": "+44 131 661 5351",
            "websiteUri": "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre",
            "rating": 4.3,
            "userRatingCount": 250,
            "types": ["sports_complex", "gym", "point_of_interest"],
            "googleMapsUri": "https://maps.google.com/?cid=123456789"
        }

    def test_extract_schema_primitives_from_v1_api(self, sample_google_places_v1_response, mock_ctx):
        """
        Validates extractor outputs schema primitives correctly from Google Places API v1

        Schema primitives: entity_name, latitude, longitude, street_address,
        postcode, phone, website, rating, user_rating_count, external_id
        """
        extractor = GooglePlacesExtractor()
        extracted = extractor.extract(sample_google_places_v1_response, ctx=mock_ctx)

        # Verify schema primitives extracted
        assert extracted["entity_name"] == "Meadowbank Sports Centre"
        assert extracted["street_address"] == "139 London Road, Edinburgh EH7 6AE, UK"
        assert extracted["postcode"] == "EH7 6AE"  # Extracted from address
        assert extracted["latitude"] == 55.9533
        assert extracted["longitude"] == -3.1883
        assert extracted["phone"] == "+441316615351"  # E.164 format
        assert extracted["website"] == "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre"
        assert extracted["rating"] == 4.3
        assert extracted["user_rating_count"] == 250
        assert extracted["external_id"] == "ChIJNWKj_TEST_ID"

        # Verify raw observations captured
        assert "raw_categories" in extracted
        assert extracted["raw_categories"] == ["sports_complex", "gym", "point_of_interest"]
        assert "google_maps_uri" in extracted

    def test_extract_handles_legacy_format(self, mock_ctx):
        """
        Validates extractor handles legacy Google Places API format

        Legacy format uses:
        - name instead of displayName.text
        - formatted_address instead of formattedAddress
        - geometry.location.lat/lng instead of location.latitude/longitude
        """
        extractor = GooglePlacesExtractor()

        # Legacy format response
        # Note: Extractor supports both v1 (camelCase) and legacy (some snake_case) formats
        legacy_raw_data = {
            "place_id": "ChIJ_LEGACY_ID",
            "name": "Legacy Sports Centre",
            "formatted_address": "456 Old Street, Edinburgh EH2 2BB, UK",
            "geometry": {
                "location": {
                    "lat": 55.9500,
                    "lng": -3.1900
                }
            },
            "internationalPhoneNumber": "+44 131 661 5351",  # Valid UK number
            "types": ["gym", "health"]
        }

        extracted = extractor.extract(legacy_raw_data, ctx=mock_ctx)

        # Verify legacy fields extracted correctly
        assert extracted["entity_name"] == "Legacy Sports Centre"
        assert extracted["street_address"] == "456 Old Street, Edinburgh EH2 2BB, UK"
        assert extracted["postcode"] == "EH2 2BB"
        assert extracted["latitude"] == 55.9500
        assert extracted["longitude"] == -3.1900
        assert extracted["phone"] == "+441316615351"  # E.164 format
        assert "raw_categories" in extracted
        assert extracted["raw_categories"] == ["gym", "health"]

    def test_extract_raw_observations_for_phase2_interpretation(self, mock_ctx):
        """
        Validates extractor captures raw observations for Phase 2 interpretation

        Raw observations (types, google_maps_uri) will be interpreted
        by Lens Application in Phase 2 using mapping rules
        """
        extractor = GooglePlacesExtractor()

        raw_data = {
            "displayName": {"text": "Test Facility"},
            "formattedAddress": "Test Address",
            "location": {"latitude": 55.95, "longitude": -3.18},
            "types": ["sports_complex", "gym", "fitness_center"],
            "googleMapsUri": "https://maps.google.com/?cid=999"
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Verify raw observations captured
        assert "raw_categories" in extracted
        assert extracted["raw_categories"] == ["sports_complex", "gym", "fitness_center"]
        assert "google_maps_uri" in extracted
        assert extracted["google_maps_uri"] == "https://maps.google.com/?cid=999"

        # These raw observations will be interpreted by lens mapping rules in Phase 2
        # e.g., mapping "sports_complex" → canonical_place_types: ["sports_facility"]
        # e.g., mapping "gym" → canonical_activities: ["fitness"]

    def test_extract_prefers_display_name_over_name(self, mock_ctx):
        """
        Validates extractor prefers displayName.text over name when both present

        This ensures API v1 format takes precedence for consistency.
        """
        extractor = GooglePlacesExtractor()

        raw_data = {
            "id": "ChIJ_TEST123",
            "name": "Old Name",
            "displayName": {"text": "Correct Name"},
            "location": {"latitude": 55.9504, "longitude": -3.1115}
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)
        assert extracted["entity_name"] == "Correct Name"

    def test_validate_requires_entity_name(self):
        """
        Validates validation fails when entity_name is missing or empty

        entity_name is a required field and must be present for validation to pass.
        """
        extractor = GooglePlacesExtractor()

        # Missing entity_name
        with pytest.raises(ValueError, match="Missing required field: entity_name"):
            extractor.validate({})

        # Empty entity_name
        with pytest.raises(ValueError, match="Missing required field: entity_name"):
            extractor.validate({"entity_name": ""})
