"""
Tests for Serper Extractor

Validates compliance with:
- system-vision.md Invariant 1 (Engine Purity)
- architecture.md Section 4.2 (Extraction Boundary Contract)
"""

import inspect
import pytest
from engine.extraction.extractors.serper_extractor import SerperExtractor


class TestEnginePurity:
    """Validates system-vision.md Invariant 1: Engine Purity"""

    def test_extractor_contains_no_domain_literals(self):
        """
        Validates: system-vision.md Invariant 1 (Engine Purity)

        The engine must contain zero domain knowledge. No domain-specific
        terms may exist in engine code.

        Forbidden terms: tennis, padel, wine, restaurant (and variations)
        """
        source = inspect.getsource(SerperExtractor)

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
        - Raw observations (raw_categories, description, connector-native fields)

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
                    entity_name="Test Venue",
                    street_address="123 Test Street",
                    city="Edinburgh",
                    postcode="EH1 1AA",
                    latitude=55.9533,
                    longitude=-3.1883,
                    phone="+441312345678",
                    website="https://example.com",
                    summary="A test venue for validation",
                    discovered_attributes={"categories": ["Sports Facility"]}
                )

        extractor = SerperExtractor(llm_client=MockLLMClient())

        # Mock Serper API response with organic search results
        raw_data = {
            "searchParameters": {"q": "test query"},
            "organic": [
                {
                    "title": "Test Venue Edinburgh",
                    "link": "https://example.com",
                    "snippet": "Test venue at 123 Test Street, Edinburgh EH1 1AA. Sports facility."
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
                    street_address="123 Test Street",
                    city="Edinburgh"
                )

        extractor = SerperExtractor(llm_client=MockLLMClient())

        raw_data = {
            "searchParameters": {"q": "test query"},
            "organic": [
                {
                    "title": "Test Venue",
                    "link": "https://example.com",
                    "snippet": "Test venue information"
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
    def sample_serper_response(self):
        """Sample Serper API response for testing"""
        return {
            "searchParameters": {"q": "meadowbank sports centre edinburgh"},
            "organic": [
                {
                    "title": "Meadowbank Sports Centre - Edinburgh Leisure",
                    "link": "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre",
                    "snippet": "Meadowbank Sports Centre, 139 London Road, Edinburgh EH7 6AE. Phone: 0131 661 5351. Premier sports facility."
                }
            ]
        }

    def test_extract_schema_primitives(self, sample_serper_response, mock_ctx):
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

        extractor = SerperExtractor(llm_client=MockLLMClient())
        extracted = extractor.extract(sample_serper_response, ctx=mock_ctx)

        # Verify schema primitives extracted
        assert extracted["entity_name"] == "Meadowbank Sports Centre"
        assert extracted["street_address"] == "139 London Road"
        assert extracted["city"] == "Edinburgh"
        assert extracted["postcode"] == "EH7 6AE"
        assert extracted["latitude"] == 55.9533
        assert extracted["longitude"] == -3.1883
        assert extracted["phone"] == "+441316615351"
        assert extracted["website"] == "https://www.edinburghleisure.co.uk/venues/meadowbank-sports-centre"

    def test_extract_raw_observations(self, sample_serper_response, mock_ctx):
        """
        Validates extractor captures raw observations for Phase 2 interpretation

        Raw observations go into summary and discovered_attributes fields
        These will be interpreted by Lens Application in Phase 2
        """
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                return EntityExtraction(
                    entity_name="Meadowbank Sports Centre",
                    summary="Premier sports facility in Edinburgh",
                    discovered_attributes={
                        "categories": ["Sports Centre", "Recreation"],
                        "facility_info": "Multi-sport venue"
                    }
                )

        extractor = SerperExtractor(llm_client=MockLLMClient())
        extracted = extractor.extract(sample_serper_response, ctx=mock_ctx)

        # Verify raw observations captured in summary and discovered_attributes
        assert extracted["summary"] == "Premier sports facility in Edinburgh"
        assert extracted["discovered_attributes"] is not None
        assert "categories" in extracted["discovered_attributes"]

        # These raw observations will be interpreted by lens mapping rules in Phase 2

    def test_extract_single_item_format_orchestration_persisted_mode(self, mock_ctx):
        """
        Validates extractor handles single organic result format (orchestration persisted mode).

        When orchestration persists one RawIngestion per Serper organic result,
        the extractor receives individual result items without the "organic" wrapper:
        {"title": "...", "link": "...", "snippet": "..."}

        The extractor must detect this format and process it correctly.
        """
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                return EntityExtraction(
                    entity_name="West of Scotland Padel",
                    entity_class="place",
                    street_address="Unit 10 Stevenson Industrial Estate",
                    city="Stevenston",
                    postcode="KA20 3LR",
                    summary="Fantastic facility with 3 great indoor padel courts"
                )

        extractor = SerperExtractor(llm_client=MockLLMClient())

        # Single organic result format (no "organic" wrapper)
        single_item_data = {
            "title": "West of Scotland Padel Tennis Club - Irvine",
            "link": "https://kaleisure.com/community_sports/west-of-scotland-padel-tennis-club/",
            "snippet": "Fantastic facility with 3 great indoor padel courts for players of all abilities.",
            "position": 9
        }

        # Extract should succeed with single-item format
        extracted = extractor.extract(single_item_data, ctx=mock_ctx)

        # Verify extraction succeeded
        assert extracted["entity_name"] == "West of Scotland Padel"
        assert "padel courts" in extracted["summary"].lower()

    def test_extract_full_wrapper_format_backwards_compatible(self, mock_ctx):
        """
        Validates extractor still handles full API response format (backwards compatibility).

        Legacy/batch mode uses full API response: {"organic": [...]}
        This test ensures backwards compatibility is maintained.
        """
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                return EntityExtraction(
                    entity_name="Test Venue",
                    entity_class="place",
                    summary="Test description"
                )

        extractor = SerperExtractor(llm_client=MockLLMClient())

        # Full API response format (with "organic" wrapper)
        full_response_data = {
            "searchParameters": {"q": "test query"},
            "organic": [
                {
                    "title": "Test Venue",
                    "link": "https://example.com",
                    "snippet": "Test description"
                }
            ]
        }

        # Extract should succeed with full wrapper format
        extracted = extractor.extract(full_response_data, ctx=mock_ctx)

        # Verify extraction succeeded
        assert extracted["entity_name"] == "Test Venue"

    def test_extract_empty_data_fails_gracefully(self, mock_ctx):
        """
        Validates extractor fails gracefully when given empty/invalid data.

        Neither format detected → should raise ValueError with clear message.
        """
        from engine.extraction.models.entity_extraction import EntityExtraction

        class MockLLMClient:
            def extract(self, prompt, response_model, context, system_message=None, **kwargs):
                # This shouldn't be called if validation fails early
                return EntityExtraction(entity_name="Should not reach here")

        extractor = SerperExtractor(llm_client=MockLLMClient())

        # Empty dict (no "organic", no single-item keys)
        empty_data = {}

        # Should raise ValueError
        with pytest.raises(ValueError, match="No organic search results found"):
            extractor.extract(empty_data, ctx=mock_ctx)
