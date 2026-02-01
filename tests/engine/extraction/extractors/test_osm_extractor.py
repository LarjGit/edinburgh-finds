"""
Tests for OSM Extractor

Validates compliance with:
- system-vision.md Invariant 1 (Engine Purity)
- architecture.md Section 4.2 (Extraction Boundary Contract)
"""

import inspect
import pytest
from engine.extraction.extractors.osm_extractor import OSMExtractor


class TestEnginePurity:
    """Validates system-vision.md Invariant 1: Engine Purity"""

    def test_extractor_contains_no_domain_literals(self):
        """
        Validates: system-vision.md Invariant 1 (Engine Purity)

        The engine must contain zero domain knowledge. No domain-specific
        terms may exist in engine code.

        Forbidden terms: tennis, padel, wine, restaurant (and variations)
        """
        source = inspect.getsource(OSMExtractor)

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
    """Validates architecture.md Section 4.2: Extraction Boundary Contract"""

    def test_extractor_outputs_only_primitives_and_raw_observations(self, mock_ctx):
        """
        Validates: architecture.md Section 4.2 (Extraction Boundary)

        Phase 1 extractors must output ONLY:
        - Schema primitives (entity_name, latitude, longitude, etc.)
        - Raw observations (OSM tags, connector-native fields)

        FORBIDDEN outputs:
        - canonical_* dimensions
        - modules or module fields
        - domain-specific interpreted fields (e.g., tennis_*, padel_*)
        """
        # Create mock LLM client that returns a valid EntityExtraction
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                # Return minimal valid EntityExtraction
                return EntityExtraction(
                    entity_name="Test Sports Centre",
                    entity_class="place",
                    street_address="123 Test Road",
                    city="Edinburgh",
                    postcode="EH1 1AA",
                    latitude=55.9533,
                    longitude=-3.1883,
                    phone="+441312345678",
                    summary="Test sports facility",
                    discovered_attributes={"osm_tags": {"leisure": "sports_centre"}}
                )

        extractor = OSMExtractor(llm_client=MockLLMClient())

        # Mock OSM Overpass API response with elements array
        raw_data = {
            "version": 0.6,
            "elements": [
                {
                    "type": "node",
                    "id": 123456789,
                    "lat": 55.9533,
                    "lon": -3.1883,
                    "tags": {
                        "name": "Test Sports Centre",
                        "leisure": "sports_centre",
                        "addr:city": "Edinburgh",
                        "addr:postcode": "EH1 1AA",
                        "phone": "+44 131 234 5678"
                    }
                }
            ]
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

    def test_extractor_outputs_no_canonical_roles_after_ex001_fix(self, mock_ctx):
        """
        Validates EX-001 fix: canonical_roles removed from LLM prompts

        This test specifically validates that the EX-001 fix (commit 4737945)
        is working correctly. The LLM should NOT be instructed to determine
        canonical_roles, and the extractor should NOT emit it.
        """
        # Create mock LLM client
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                # Verify prompts don't mention canonical_roles
                if system_message:
                    assert "canonical_roles" not in system_message.lower(), (
                        "EX-001 violation: LLM prompt still requests canonical_roles. "
                        "This field should have been removed in commit 4737945."
                    )

                return EntityExtraction(
                    entity_name="Test Venue",
                    entity_class="place",
                    latitude=55.9533,
                    longitude=-3.1883
                )

        extractor = OSMExtractor(llm_client=MockLLMClient())

        raw_data = {
            "version": 0.6,
            "elements": [
                {
                    "type": "node",
                    "id": 987654321,
                    "lat": 55.9533,
                    "lon": -3.1883,
                    "tags": {"name": "Test Venue"}
                }
            ]
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Verify canonical_roles NOT in output
        assert "canonical_roles" not in extracted, (
            "EX-001 violation: Extractor emitted canonical_roles. "
            "This field should have been removed in commit 4737945."
        )


class TestExtractionCorrectness:
    """Validates extractor correctly extracts primitives and raw observations"""

    @pytest.fixture
    def sample_osm_response(self):
        """Sample OSM Overpass API response for testing"""
        return {
            "version": 0.6,
            "elements": [
                {
                    "type": "node",
                    "id": 123456789,
                    "lat": 55.9533,
                    "lon": -3.1883,
                    "tags": {
                        "name": "Meadowbank Sports Centre",
                        "leisure": "sports_centre",
                        "addr:street": "London Road",
                        "addr:housenumber": "139",
                        "addr:city": "Edinburgh",
                        "addr:postcode": "EH7 6AE",
                        "phone": "+44 131 661 5351",
                        "website": "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre",
                        "opening_hours": "Mo-Su 06:00-22:00"
                    }
                }
            ]
        }

    def test_extract_schema_primitives(self, sample_osm_response, mock_ctx):
        """
        Validates extractor outputs schema primitives correctly

        Schema primitives: entity_name, latitude, longitude, street_address,
        city, postcode, phone, website
        """
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                return EntityExtraction(
                    entity_name="Meadowbank Sports Centre",
                    entity_class="place",
                    street_address="139 London Road",
                    city="Edinburgh",
                    postcode="EH7 6AE",
                    latitude=55.9533,
                    longitude=-3.1883,
                    phone="+441316615351",
                    website="https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre"
                )

        extractor = OSMExtractor(llm_client=MockLLMClient())
        extracted = extractor.extract(sample_osm_response, ctx=mock_ctx)

        # Verify schema primitives extracted
        assert extracted["entity_name"] == "Meadowbank Sports Centre"
        assert extracted["street_address"] == "139 London Road"
        assert extracted["city"] == "Edinburgh"
        assert extracted["postcode"] == "EH7 6AE"
        assert extracted["latitude"] == 55.9533
        assert extracted["longitude"] == -3.1883
        assert extracted["phone"] == "+441316615351"
        assert extracted["website"] == "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre"

    def test_extract_raw_observations(self, sample_osm_response, mock_ctx):
        """
        Validates extractor captures raw observations for Phase 2 interpretation

        Raw observations (OSM tags) go into discovered_attributes field
        These will be interpreted by Lens Application in Phase 2
        """
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                return EntityExtraction(
                    entity_name="Meadowbank Sports Centre",
                    entity_class="place",
                    summary="Sports centre in Edinburgh",
                    discovered_attributes={
                        "osm_tags": {
                            "leisure": "sports_centre",
                            "opening_hours": "Mo-Su 06:00-22:00"
                        }
                    }
                )

        extractor = OSMExtractor(llm_client=MockLLMClient())
        extracted = extractor.extract(sample_osm_response, ctx=mock_ctx)

        # Verify raw observations captured in summary and discovered_attributes
        assert extracted["summary"] == "Sports centre in Edinburgh"
        assert extracted["discovered_attributes"] is not None
        assert "osm_tags" in extracted["discovered_attributes"]

        # These raw observations will be interpreted by lens mapping rules in Phase 2
        # e.g., mapping "leisure=sports_centre" → canonical_place_types: ["sports_facility"]

    def test_extract_osm_id_for_deduplication(self, mock_ctx):
        """
        Validates extractor adds OSM ID to external_ids for deduplication

        OSM ID format: "type/id" (e.g., "node/123456789")
        """
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                return EntityExtraction(
                    entity_name="Test Venue",
                    entity_class="place",
                    latitude=55.9533,
                    longitude=-3.1883
                )

        extractor = OSMExtractor(llm_client=MockLLMClient())

        raw_data = {
            "version": 0.6,
            "elements": [
                {
                    "type": "node",
                    "id": 123456789,
                    "lat": 55.9533,
                    "lon": -3.1883,
                    "tags": {"name": "Test Venue"}
                }
            ]
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Verify OSM ID added to external_ids
        assert "external_ids" in extracted
        assert "osm" in extracted["external_ids"]
        assert extracted["external_ids"]["osm"] == "node/123456789"

    def test_aggregate_osm_elements_helper(self):
        """
        Validates _aggregate_osm_elements() helper aggregates multiple elements correctly

        Helper should combine multiple OSM elements (nodes, ways, relations)
        into a single context string for LLM extraction
        """
        # Create mock LLM client to avoid API key requirement
        class MockLLMClient:
            def extract(self, *args, **kwargs):
                pass

        extractor = OSMExtractor(llm_client=MockLLMClient())

        elements = [
            {
                "type": "node",
                "id": 123,
                "lat": 55.95,
                "lon": -3.18,
                "tags": {"name": "Venue A", "leisure": "sports_centre"}
            },
            {
                "type": "way",
                "id": 456,
                "tags": {"name": "Venue A", "building": "yes"}
            }
        ]

        aggregated = extractor._aggregate_osm_elements(elements)

        # Verify aggregation includes both elements
        assert "Element 1 (node #123)" in aggregated
        assert "Element 2 (way #456)" in aggregated
        assert "Lat 55.95, Lon -3.18" in aggregated
        assert "name: Venue A" in aggregated
        assert "leisure: sports_centre" in aggregated
        assert "building: yes" in aggregated

    def test_validate_requires_entity_name(self):
        """
        Validates validation fails when entity_name is missing or empty

        entity_name is a required field and must be present for validation to pass.
        """
        # Create mock LLM client to avoid API key requirement
        class MockLLMClient:
            def extract(self, *args, **kwargs):
                pass

        extractor = OSMExtractor(llm_client=MockLLMClient())

        # Missing entity_name
        with pytest.raises(ValueError, match="entity_name is required"):
            extractor.validate({})

        # Empty entity_name
        with pytest.raises(ValueError, match="entity_name is required"):
            extractor.validate({"entity_name": ""})

    def test_split_attributes_separates_schema_and_discovered(self, mock_ctx):
        """
        Validates split_attributes() correctly separates schema fields from discovered attributes

        Schema-defined fields → attributes dict
        Non-schema fields (OSM-specific) → discovered_attributes dict
        """
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                return EntityExtraction(
                    entity_name="Test Venue",
                    entity_class="place",
                    street_address="123 Test St",
                    city="Edinburgh",
                    latitude=55.9533,
                    longitude=-3.1883,
                    discovered_attributes={
                        "osm_tags": {"leisure": "sports_centre"},
                        "osm_specific_field": "custom value"
                    }
                )

        extractor = OSMExtractor(llm_client=MockLLMClient())

        raw_data = {
            "version": 0.6,
            "elements": [
                {
                    "type": "node",
                    "id": 999,
                    "lat": 55.9533,
                    "lon": -3.1883,
                    "tags": {"name": "Test Venue"}
                }
            ]
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)
        attributes, discovered = extractor.split_attributes(extracted)

        # Schema fields should be in attributes
        assert "entity_name" in attributes
        assert "street_address" in attributes
        assert "city" in attributes
        assert "latitude" in attributes
        assert "longitude" in attributes

        # Non-schema fields should be in discovered (unwrapped from discovered_attributes)
        # The split_attributes() function unwraps discovered_attributes content
        assert "osm_specific_field" in discovered
        assert "osm_tags" in discovered

        # Verify no canonical fields in either dict
        for field in ["canonical_activities", "canonical_roles", "canonical_place_types"]:
            assert field not in attributes
            assert field not in discovered
