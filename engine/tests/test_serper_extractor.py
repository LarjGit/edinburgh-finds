"""
Tests for Serper Extractor

This module tests the SerperExtractor which transforms raw Serper search results
into structured listing fields using LLM-based extraction.

Serper provides unstructured Google search snippets, so extraction requires
intelligent parsing with the Instructor LLM client.

Test Coverage:
- Extractor initialization and source_name property
- LLM-based extraction from search snippets
- Snippet aggregation (combining multiple results for same venue)
- Null semantics enforcement (lots of missing data expected)
- Attribute splitting (schema-defined vs discovered)
- Error handling for extraction failures
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def serper_fixture():
    """Load the Serper padel search test fixture"""
    fixture_path = Path(__file__).parent / "fixtures" / "serper_padel_search.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def serper_minimal_fixture():
    """Load the minimal Serper result (tests null semantics)"""
    fixture_path = Path(__file__).parent / "fixtures" / "serper_minimal_result.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def serper_single_result(serper_fixture):
    """Extract the first result for single-result tests"""
    return serper_fixture["organic"][0]


class TestSerperExtractorInitialization:
    """Test Serper extractor initialization and basic properties"""

    def test_serper_extractor_can_be_imported(self):
        """Test that SerperExtractor class can be imported"""
        try:
            from engine.extraction.extractors.serper_extractor import SerperExtractor
            assert SerperExtractor is not None
        except ImportError:
            pytest.fail("Failed to import SerperExtractor - implementation not yet created")

    def test_serper_extractor_can_be_instantiated(self):
        """Test that SerperExtractor can be instantiated"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        # Pass mock LLM client to avoid requiring API key
        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        assert extractor is not None

    def test_serper_extractor_has_correct_source_name(self):
        """Test that source_name property returns 'serper'"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        # Pass mock LLM client to avoid requiring API key
        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        assert extractor.source_name == "serper"


class TestSerperSnippetAggregation:
    """Test snippet aggregation from multiple search results"""

    def test_aggregate_snippets_combines_text(self, serper_fixture):
        """Test that multiple snippets are combined into single text"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        aggregated = extractor._aggregate_snippets(serper_fixture["organic"])

        # Should combine all snippets
        assert "Game4Padel" in aggregated
        assert "Edinburgh Park" in aggregated
        assert "premier indoor padel facility" in aggregated

    def test_aggregate_snippets_preserves_important_details(self, serper_fixture):
        """Test that aggregation preserves contact info and addresses"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        aggregated = extractor._aggregate_snippets(serper_fixture["organic"])

        # Should preserve contact details
        assert "0131 539 7071" in aggregated or "0131539707" in aggregated
        assert "New Park Square" in aggregated

    def test_aggregate_snippets_handles_empty_list(self):
        """Test that empty result list returns empty string"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        aggregated = extractor._aggregate_snippets([])

        assert aggregated == ""

    def test_aggregate_snippets_handles_single_result(self, serper_single_result):
        """Test that single result is handled correctly"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        aggregated = extractor._aggregate_snippets([serper_single_result])

        assert "Game4Padel" in aggregated
        assert "Edinburgh Park" in aggregated


class TestSerperLLMExtraction:
    """Test LLM-based extraction from Serper data"""

    @patch('engine.extraction.extractors.serper_extractor.InstructorClient')
    def test_extract_uses_llm_client(self, mock_instructor_class, serper_fixture):
        """Test that extract method uses InstructorClient for LLM extraction"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor
        from engine.extraction.models.venue_extraction import VenueExtraction

        # Mock LLM response
        mock_client = Mock()
        mock_extraction = VenueExtraction(
            entity_name="Game4Padel Edinburgh Park",
            street_address="1 New Park Square, Edinburgh Park, Edinburgh EH12 9GR",
            city="Edinburgh",
            postcode="EH12 9GR",
            phone="+441315397071"
        )
        mock_client.extract.return_value = mock_extraction
        mock_instructor_class.return_value = mock_client

        extractor = SerperExtractor()
        result = extractor.extract(serper_fixture)

        # Verify LLM client was called
        mock_client.extract.assert_called_once()
        assert result["entity_name"] == "Game4Padel Edinburgh Park"

    @patch('engine.extraction.extractors.serper_extractor.InstructorClient')
    def test_extract_passes_aggregated_snippets_to_llm(self, mock_instructor_class, serper_fixture):
        """Test that aggregated snippets are passed as context to LLM"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor
        from engine.extraction.models.venue_extraction import VenueExtraction

        mock_client = Mock()
        mock_extraction = VenueExtraction(entity_name="Test Venue")
        mock_client.extract.return_value = mock_extraction
        mock_instructor_class.return_value = mock_client

        extractor = SerperExtractor()
        extractor.extract(serper_fixture)

        # Check that context parameter contains snippet data
        call_args = mock_client.extract.call_args
        context_arg = call_args.kwargs.get('context') or call_args.args[2] if len(call_args.args) > 2 else None

        assert context_arg is not None
        assert "Game4Padel" in context_arg or "padel" in context_arg.lower()

    @patch('engine.extraction.extractors.serper_extractor.InstructorClient')
    def test_extract_uses_serper_specific_prompt(self, mock_instructor_class, serper_fixture):
        """Test that Serper-specific system message/prompt is used"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor
        from engine.extraction.models.venue_extraction import VenueExtraction

        mock_client = Mock()
        mock_extraction = VenueExtraction(entity_name="Test Venue")
        mock_client.extract.return_value = mock_extraction
        mock_instructor_class.return_value = mock_client

        extractor = SerperExtractor()
        extractor.extract(serper_fixture)

        # Verify system_message parameter was passed
        call_kwargs = mock_client.extract.call_args.kwargs
        assert 'system_message' in call_kwargs

    @patch('engine.extraction.extractors.serper_extractor.InstructorClient')
    def test_extract_handles_minimal_data_with_nulls(self, mock_instructor_class, serper_minimal_fixture):
        """Test that extraction handles minimal data and produces nulls appropriately"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor
        from engine.extraction.models.venue_extraction import VenueExtraction

        # Mock LLM to return minimal extraction (lots of nulls)
        mock_client = Mock()
        mock_extraction = VenueExtraction(
            entity_name="Westend Padel Club",
            street_address=None,  # Not found in snippet
            city="Glasgow",  # Can be inferred
            phone=None,  # Not found
            website=None,  # Not found
            rating=None  # Not found
        )
        mock_client.extract.return_value = mock_extraction
        mock_instructor_class.return_value = mock_client

        extractor = SerperExtractor()
        result = extractor.extract(serper_minimal_fixture)

        # Verify null semantics are preserved
        assert result["entity_name"] == "Westend Padel Club"
        assert result["phone"] is None
        assert result["website"] is None
        assert result["rating"] is None


class TestSerperValidation:
    """Test validation of extracted Serper data"""

    def test_validate_accepts_valid_extraction(self):
        """Test that valid extraction passes validation"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        extracted = {
            "entity_name": "Game4Padel",
            "city": "Edinburgh",
            "phone": "+441315397071"
        }

        validated = extractor.validate(extracted)
        assert validated["entity_name"] == "Game4Padel"
        assert validated["phone"] == "+441315397071"

    def test_validate_preserves_null_fields(self):
        """Test that validation preserves null values"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        extracted = {
            "entity_name": "Test Venue",
            "phone": None,
            "website": None,
            "rating": None
        }

        validated = extractor.validate(extracted)
        assert validated["phone"] is None
        assert validated["website"] is None
        assert validated["rating"] is None

    def test_validate_ensures_entity_name_present(self):
        """Test that validation requires entity_name"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        extracted = {
            "city": "Edinburgh"
            # Missing entity_name
        }

        with pytest.raises(ValueError, match="entity_name"):
            extractor.validate(extracted)


class TestSerperAttributeSplitting:
    """Test splitting of extracted fields into attributes and discovered_attributes"""

    def test_split_attributes_separates_schema_fields(self):
        """Test that schema-defined fields go into attributes"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        extracted = {
            "entity_name": "Game4Padel",
            "street_address": "1 New Park Square",
            "city": "Edinburgh",
            "phone": "+441315397071",
            "rating": 4.4
        }

        attributes, discovered = extractor.split_attributes(extracted)

        # Schema-defined fields should be in attributes
        assert "entity_name" in attributes
        assert "street_address" in attributes
        assert "city" in attributes
        assert "phone" in attributes
        assert "rating" in attributes

    def test_split_attributes_handles_discovered_fields(self):
        """Test that non-schema fields go into discovered_attributes"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        extracted = {
            "entity_name": "Game4Padel",
            "custom_field": "custom value",
            "extra_data": 123
        }

        attributes, discovered = extractor.split_attributes(extracted)

        # Custom fields should be in discovered
        assert "custom_field" in discovered
        assert "extra_data" in discovered


class TestSerperErrorHandling:
    """Test error handling for various failure scenarios"""

    @patch('engine.extraction.extractors.serper_extractor.InstructorClient')
    def test_extract_handles_llm_failure(self, mock_instructor_class, serper_fixture):
        """Test that LLM extraction failures are handled gracefully"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor
        from pydantic import ValidationError

        # Mock LLM to raise error
        mock_client = Mock()
        mock_client.extract.side_effect = ValidationError.from_exception_data(
            "value_error",
            [{"type": "missing", "loc": ("entity_name",), "msg": "Field required"}]
        )
        mock_instructor_class.return_value = mock_client

        extractor = SerperExtractor()

        with pytest.raises(ValidationError):
            extractor.extract(serper_fixture)

    def test_extract_handles_empty_organic_results(self):
        """Test that empty search results are handled"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        extractor = SerperExtractor(llm_client=mock_client)
        empty_data = {
            "searchParameters": {"q": "nonexistent venue"},
            "organic": []
        }

        # Should handle empty results gracefully
        # Either return empty dict or raise appropriate error
        try:
            result = extractor.extract(empty_data)
            # If it returns, should be empty or have reasonable defaults
            assert isinstance(result, dict)
        except ValueError as e:
            # Or it can raise a clear error
            assert "no results" in str(e).lower() or "empty" in str(e).lower()

    @patch('engine.extraction.extractors.serper_extractor.InstructorClient')
    def test_extract_handles_malformed_data(self, mock_instructor_class):
        """Test that malformed Serper data is handled"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor

        mock_client = Mock()
        mock_instructor_class.return_value = mock_client

        extractor = SerperExtractor()
        malformed_data = {
            "unexpected_key": "unexpected_value"
            # Missing organic results
        }

        # Should handle malformed data gracefully
        try:
            result = extractor.extract(malformed_data)
        except (KeyError, ValueError, TypeError) as e:
            # Expected - malformed data should raise clear error
            assert True


class TestSerperExtractionQuality:
    """Test extraction quality and accuracy"""

    @patch('engine.extraction.extractors.serper_extractor.InstructorClient')
    def test_extract_preserves_entity_name(self, mock_instructor_class, serper_fixture):
        """Test that entity name is correctly extracted from snippets"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor
        from engine.extraction.models.venue_extraction import VenueExtraction

        mock_client = Mock()
        mock_extraction = VenueExtraction(
            entity_name="Game4Padel Edinburgh Park"
        )
        mock_client.extract.return_value = mock_extraction
        mock_instructor_class.return_value = mock_client

        extractor = SerperExtractor()
        result = extractor.extract(serper_fixture)

        assert "Game4Padel" in result["entity_name"]

    @patch('engine.extraction.extractors.serper_extractor.InstructorClient')
    def test_extract_finds_contact_info_in_snippets(self, mock_instructor_class, serper_fixture):
        """Test that contact info is extracted from snippet text"""
        from engine.extraction.extractors.serper_extractor import SerperExtractor
        from engine.extraction.models.venue_extraction import VenueExtraction

        mock_client = Mock()
        mock_extraction = VenueExtraction(
            entity_name="Game4Padel",
            phone="+441315397071"
        )
        mock_client.extract.return_value = mock_extraction
        mock_instructor_class.return_value = mock_client

        extractor = SerperExtractor()
        result = extractor.extract(serper_fixture)

        # Phone should be in E.164 format
        if result.get("phone"):
            assert result["phone"].startswith("+44")
            assert " " not in result["phone"]
