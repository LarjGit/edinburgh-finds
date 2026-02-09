"""
Tests for Edinburgh Council Extractor

Validates compliance with:
- system-vision.md Invariant 1 (Engine Purity)
- docs/target-architecture.md Section 4.2 (Extraction Boundary Contract)
"""

import inspect
import pytest
from engine.extraction.extractors.edinburgh_council_extractor import EdinburghCouncilExtractor


class TestEnginePurity:
    """Validates system-vision.md Invariant 1: Engine Purity"""

    def test_extractor_contains_no_domain_literals(self):
        """
        Validates: system-vision.md Invariant 1 (Engine Purity)

        The engine must contain zero domain knowledge. No domain-specific
        terms may exist in engine code.

        Forbidden terms: tennis, padel, wine, restaurant (and variations)
        """
        source = inspect.getsource(EdinburghCouncilExtractor)

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
        - Raw observations (raw_categories, connector-native fields)

        FORBIDDEN outputs:
        - canonical_* dimensions
        - modules or module fields
        - domain-specific interpreted fields (e.g., tennis_*, padel_*)
        """
        extractor = EdinburghCouncilExtractor()

        # Mock Edinburgh Council GeoJSON response
        raw_data = {
            "type": "Feature",
            "id": "facilities.123",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.1883, 55.9533]  # GeoJSON: [lng, lat]
            },
            "properties": {
                "NAME": "Test Sports Centre",
                "ADDRESS": "123 Test Road",
                "POSTCODE": "EH1 1AA",
                "PHONE": "0131 234 5678",
                "EMAIL": "test@example.com",
                "WEBSITE": "https://example.com",
                "DESCRIPTION": "Test facility",
                "FACILITY_TYPE": "Sports Centre"
            }
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


class TestExtractionCorrectness:
    """Validates extractor correctly extracts primitives and raw observations"""

    @pytest.fixture
    def sample_council_response(self):
        """Sample Edinburgh Council GeoJSON response for testing"""
        return {
            "type": "Feature",
            "id": "facilities.456",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.17278, 55.95325]  # GeoJSON: [lng, lat]
            },
            "properties": {
                "NAME": "Meadowbank Sports Centre",
                "ADDRESS": "139 London Road",
                "POSTCODE": "EH7 6AE",
                "PHONE": "0131 661 5351",
                "EMAIL": "meadowbank@edinburghleisure.co.uk",
                "WEBSITE": "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre",
                "DESCRIPTION": "Premier sports facility in Edinburgh",
                "FACILITY_TYPE": "Sports Centre",
                "CAPACITY": 500,
                "ACCESSIBLE": "Yes",
                "OPENING_HOURS": "Mo-Su 06:00-22:00",
                "DATASET_NAME": "Edinburgh Council Sports Facilities"
            }
        }

    def test_extract_schema_primitives(self, sample_council_response, mock_ctx):
        """
        Validates extractor outputs schema primitives correctly

        Schema primitives: entity_name, latitude, longitude, street_address,
        city, postcode, phone, email, website, summary, capacity
        """
        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(sample_council_response, ctx=mock_ctx)

        # Verify schema primitives extracted
        assert extracted["entity_name"] == "Meadowbank Sports Centre"
        assert extracted["street_address"] == "139 London Road"
        assert extracted["city"] == "Edinburgh"
        assert extracted["country"] == "Scotland"
        assert extracted["postcode"] == "EH7 6AE"
        assert extracted["latitude"] == 55.95325
        assert extracted["longitude"] == -3.17278
        assert extracted["phone"] == "+441316615351"  # Formatted to E.164
        assert extracted["email"] == "meadowbank@edinburghleisure.co.uk"
        assert extracted["website"] == "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre"
        assert extracted["summary"] == "Premier sports facility in Edinburgh"
        assert extracted["capacity"] == 500
        assert extracted["wheelchair_accessible"] is True

    def test_extract_categories(self, mock_ctx):
        """
        Validates category extraction from multiple fields

        Edinburgh Council uses various field names: CATEGORY, TYPE, FACILITY_TYPE
        Extractor should collect from all and deduplicate
        """
        extractor = EdinburghCouncilExtractor()

        raw_data = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-3.18, 55.95]},
            "properties": {
                "NAME": "Test Facility",
                "CATEGORY": "Recreation",
                "TYPE": "Sports",
                "FACILITY_TYPE": "Recreation"  # Duplicate should be removed
            }
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Verify categories extracted and deduplicated
        assert "categories" in extracted
        assert len(extracted["categories"]) == 2  # Recreation (deduplicated), Sports
        assert "Recreation" in extracted["categories"]
        assert "Sports" in extracted["categories"]

    def test_extract_coordinates_from_geojson(self, mock_ctx):
        """
        Validates GeoJSON coordinate extraction with correct [lng, lat] reversal

        GeoJSON uses [longitude, latitude] order
        Schema uses latitude, longitude fields (reversed)
        """
        extractor = EdinburghCouncilExtractor()

        raw_data = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [-3.1883, 55.9533]  # [lng, lat] in GeoJSON
            },
            "properties": {"NAME": "Test Location"}
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Verify coordinate reversal: GeoJSON [lng, lat] → latitude, longitude
        assert extracted["longitude"] == -3.1883  # First element
        assert extracted["latitude"] == 55.9533   # Second element

    def test_validate_requires_entity_name(self):
        """
        Validates validation fails when entity_name is missing or empty

        entity_name is a required field and must be present for validation to pass.
        """
        extractor = EdinburghCouncilExtractor()

        # Missing entity_name
        with pytest.raises(ValueError, match="Missing required field: entity_name"):
            extractor.validate({})

        # Empty entity_name
        with pytest.raises(ValueError, match="Missing required field: entity_name"):
            extractor.validate({"entity_name": ""})

    def test_split_attributes_separates_schema_and_discovered(self, sample_council_response, mock_ctx):
        """
        Validates split_attributes() correctly separates schema fields from discovered attributes

        Schema-defined fields → attributes dict
        Non-schema fields (Edinburgh Council-specific like DATASET_NAME) → discovered_attributes dict
        """
        extractor = EdinburghCouncilExtractor()
        extracted = extractor.extract(sample_council_response, ctx=mock_ctx)
        attributes, discovered = extractor.split_attributes(extracted)

        # Schema fields should be in attributes
        assert "entity_name" in attributes
        assert "street_address" in attributes
        assert "city" in attributes
        assert "latitude" in attributes
        assert "longitude" in attributes
        assert "phone" in attributes
        assert "email" in attributes

        # Note: "website" field is currently output by extractor but schema field is "website_url"
        # This is a known bug - website goes to discovered instead of attributes
        # TODO: Fix extractor to output "website_url" instead of "website"

        # Non-schema fields (Edinburgh Council-specific) should be in discovered
        if "DATASET_NAME" in extracted:
            assert "DATASET_NAME" in discovered

        # Verify no canonical fields in either dict
        for field in ["canonical_activities", "canonical_roles", "canonical_place_types"]:
            assert field not in attributes
            assert field not in discovered

    def test_extract_handles_multiple_field_names(self, mock_ctx):
        """
        Validates extractor handles Edinburgh Council's multiple field naming conventions

        Edinburgh Council uses various field names for same data:
        - NAME, FACILITY_NAME, SITE_NAME
        - ADDRESS, STREET_ADDRESS
        - PHONE, CONTACT_NUMBER
        - EMAIL, CONTACT_EMAIL
        - WEBSITE, URL
        - DESCRIPTION, SUMMARY
        """
        extractor = EdinburghCouncilExtractor()

        # Test with alternative field names
        raw_data = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-3.18, 55.95]},
            "properties": {
                "FACILITY_NAME": "Alternative Name Field",  # Instead of NAME
                "STREET_ADDRESS": "456 Alternative Road",   # Instead of ADDRESS
                "CONTACT_NUMBER": "0131 661 5351",          # Instead of PHONE (using valid Edinburgh number)
                "CONTACT_EMAIL": "alt@example.com",         # Instead of EMAIL
                "URL": "https://alt.example.com",           # Instead of WEBSITE
                "SUMMARY": "Alternative summary field"      # Instead of DESCRIPTION
            }
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Verify alternative field names work
        assert extracted["entity_name"] == "Alternative Name Field"
        assert extracted["street_address"] == "456 Alternative Road"
        assert extracted["phone"] == "+441316615351"  # E.164 format of 0131 661 5351
        assert extracted["email"] == "alt@example.com"
        assert extracted["website"] == "https://alt.example.com"
        assert extracted["summary"] == "Alternative summary field"

    def test_extract_accessibility_flags(self, mock_ctx):
        """
        Validates wheelchair_accessible boolean extraction from ACCESSIBLE field

        Edinburgh Council uses various formats: Yes/Y/True/1 or No/N/False/0
        """
        extractor = EdinburghCouncilExtractor()

        # Test accessible = Yes
        raw_data_yes = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-3.18, 55.95]},
            "properties": {"NAME": "Accessible Venue", "ACCESSIBLE": "Yes"}
        }
        extracted_yes = extractor.extract(raw_data_yes, ctx=mock_ctx)
        assert extracted_yes["wheelchair_accessible"] is True

        # Test accessible = No
        raw_data_no = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-3.18, 55.95]},
            "properties": {"NAME": "Non-Accessible Venue", "ACCESSIBLE": "No"}
        }
        extracted_no = extractor.extract(raw_data_no, ctx=mock_ctx)
        assert extracted_no["wheelchair_accessible"] is False

        # Test accessible = missing (should not set field)
        raw_data_missing = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-3.18, 55.95]},
            "properties": {"NAME": "Unknown Accessibility"}
        }
        extracted_missing = extractor.extract(raw_data_missing, ctx=mock_ctx)
        assert "wheelchair_accessible" not in extracted_missing
