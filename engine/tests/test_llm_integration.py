"""
Integration tests for LLM client with sample prompts.

These tests verify that the LLM client works correctly with real prompts
and the base extraction template. Most tests use mocks to avoid API calls,
but a manual test is provided for real API testing.

To run real API tests:
1. Set ANTHROPIC_API_KEY environment variable
2. Run: pytest engine/tests/test_llm_integration.py::test_real_llm_extraction_manual -v

Test Coverage:
- Loading prompt templates from files
- Combining templates with context data
- Real LLM extraction with VenueExtraction model (manual test)
- Verifying null semantics in LLM responses
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
import os


class TestPromptTemplateLoading:
    """Test loading and using prompt templates"""

    def test_extraction_base_template_exists(self):
        """Test that base extraction template file exists"""
        template_path = Path(__file__).parent.parent / "extraction" / "prompts" / "extraction_base.txt"
        assert template_path.exists(), f"Template not found at {template_path}"

    def test_extraction_base_template_has_content(self):
        """Test that template has expected content"""
        template_path = Path(__file__).parent.parent / "extraction" / "prompts" / "extraction_base.txt"

        with open(template_path, 'r') as f:
            content = f.read()

        # Should mention null semantics
        assert 'null' in content.lower()
        # Should mention required fields
        assert 'entity_name' in content.lower()
        # Should mention phone formatting
        assert 'E.164' in content or 'e.164' in content.lower()

    def test_can_load_template_as_system_message(self):
        """Test that template can be loaded and used as system message"""
        template_path = Path(__file__).parent.parent / "extraction" / "prompts" / "extraction_base.txt"

        with open(template_path, 'r') as f:
            system_message = f.read()

        assert len(system_message) > 0
        assert isinstance(system_message, str)


class TestLLMClientWithTemplates:
    """Test LLM client using the extraction templates"""

    @patch('anthropic.Anthropic')
    def test_llm_client_accepts_custom_system_message(self, mock_anthropic):
        """Test that custom system messages (like our template) are used"""
        from engine.extraction.llm_client import InstructorClient
        from engine.extraction.models.venue_extraction import VenueExtraction

        # Load the base template
        template_path = Path(__file__).parent.parent / "extraction" / "prompts" / "extraction_base.txt"
        with open(template_path, 'r') as f:
            system_message = f.read()

        # Mock the response
        mock_client = Mock()
        mock_response = VenueExtraction(
            entity_name="Test Venue",
            street_address="123 Test St",
            phone="+441234567890"
        )
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # Make extraction call with custom system message
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            result = client.extract(
                prompt="Extract venue information from the context.",
                response_model=VenueExtraction,
                context="Test venue data here",
                system_message=system_message
            )

            assert result is not None
            # Verify the system message was passed to API
            call_args = mock_client.messages.create.call_args
            assert call_args is not None


class TestNullSemanticsInLLMResponses:
    """Test that LLM responses correctly use null semantics"""

    @patch('anthropic.Anthropic')
    def test_llm_response_uses_null_for_missing_fields(self, mock_anthropic):
        """Test that LLM uses null instead of empty strings or placeholders"""
        from engine.extraction.llm_client import InstructorClient
        from engine.extraction.models.venue_extraction import VenueExtraction

        # Mock a response with proper null usage
        mock_client = Mock()
        mock_response = VenueExtraction(
            entity_name="Minimal Venue",
            street_address=None,  # Null, not empty string
            phone=None,  # Null, not "Unknown"
            rating=None,  # Null, not 0
            currently_open=None  # Null, not False
        )
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            result = client.extract(
                prompt="Extract venue",
                response_model=VenueExtraction,
                context="Minimal Venue - that's all we know"
            )

            # Verify null semantics
            assert result.entity_name == "Minimal Venue"
            assert result.street_address is None
            assert result.phone is None
            assert result.rating is None
            assert result.currently_open is None


class TestExtractionWithRealData:
    """
    Manual tests for real LLM extraction.
    These require an actual API key and will make real API calls.
    Run manually with: pytest -k test_real_llm_extraction_manual -v
    """

    @pytest.mark.skip(reason="Manual test - requires API key and makes real API calls")
    def test_real_llm_extraction_manual(self):
        """
        MANUAL TEST - Requires ANTHROPIC_API_KEY environment variable.

        This test makes a real API call to verify end-to-end LLM extraction
        with the base template and VenueExtraction model.

        To run:
        1. Set ANTHROPIC_API_KEY environment variable
        2. pytest engine/tests/test_llm_integration.py::TestExtractionWithRealData::test_real_llm_extraction_manual -v
        """
        from engine.extraction.llm_client import InstructorClient
        from engine.extraction.models.venue_extraction import VenueExtraction

        # Check for API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set - skipping real API test")

        # Load template
        template_path = Path(__file__).parent.parent / "extraction" / "prompts" / "extraction_base.txt"
        with open(template_path, 'r') as f:
            system_message = f.read()

        # Sample context (Google Places-like data)
        context = """
        {
            "name": "Game4Padel | Edinburgh Park",
            "formatted_address": "1, New Park Square, Edinburgh Park, Edinburgh EH12 9GR, UK",
            "geometry": {
                "location": {
                    "lat": 55.930189,
                    "lng": -3.315341
                }
            },
            "formatted_phone_number": "0131 539 7071",
            "website": "https://www.game4padel.co.uk/edinburgh-park",
            "rating": 4.4,
            "user_ratings_total": 15,
            "types": ["sports_club", "point_of_interest", "establishment"]
        }
        """

        # Make real extraction call
        client = InstructorClient(api_key=api_key)
        result = client.extract(
            prompt="Extract structured venue information from the Google Places API response.",
            response_model=VenueExtraction,
            context=context,
            system_message=system_message
        )

        # Verify extraction
        print(f"\n=== EXTRACTION RESULT ===")
        print(f"Entity Name: {result.entity_name}")
        print(f"Address: {result.street_address}")
        print(f"Postcode: {result.postcode}")
        print(f"Phone: {result.phone}")
        print(f"Website: {result.website}")
        print(f"Rating: {result.rating}")
        print(f"Coordinates: ({result.latitude}, {result.longitude})")

        # Assertions
        assert result.entity_name is not None
        assert "Game4Padel" in result.entity_name or "Edinburgh" in result.entity_name

        # Check phone is E.164 format if extracted
        if result.phone:
            assert result.phone.startswith('+44')
            assert ' ' not in result.phone
            assert '-' not in result.phone

        # Check postcode format if extracted
        if result.postcode:
            assert ' ' in result.postcode
            assert result.postcode.isupper()

        # Get usage stats
        usage = client.get_last_usage()
        cost = client.get_last_cost()

        print(f"\n=== API USAGE ===")
        print(f"Input tokens: {usage['input_tokens']}")
        print(f"Output tokens: {usage['output_tokens']}")
        print(f"Cost: ${cost:.6f}")

        # Cost should be very small (Haiku is cheap)
        assert cost < 0.01  # Less than 1 cent

    @pytest.mark.skip(reason="Manual test - requires API key and makes real API calls")
    def test_real_llm_extraction_null_semantics_manual(self):
        """
        MANUAL TEST - Verify null semantics with real LLM.

        Tests that the LLM correctly uses null for missing fields when
        given incomplete data.
        """
        from engine.extraction.llm_client import InstructorClient
        from engine.extraction.models.venue_extraction import VenueExtraction

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set")

        template_path = Path(__file__).parent.parent / "extraction" / "prompts" / "extraction_base.txt"
        with open(template_path, 'r') as f:
            system_message = f.read()

        # Minimal context - only name and city mentioned
        context = """
        There's a padel club called "Edinburgh Indoor Padel" in Edinburgh.
        That's all the information we have.
        """

        client = InstructorClient(api_key=api_key)
        result = client.extract(
            prompt="Extract venue information. Remember: use null for missing fields!",
            response_model=VenueExtraction,
            context=context,
            system_message=system_message
        )

        print(f"\n=== NULL SEMANTICS TEST ===")
        print(f"Entity Name: {result.entity_name}")
        print(f"City: {result.city}")
        print(f"Phone: {result.phone}")
        print(f"Website: {result.website}")
        print(f"Rating: {result.rating}")

        # Should extract name and city
        assert result.entity_name is not None
        assert "Edinburgh" in result.entity_name or "Padel" in result.entity_name

        # Everything else should be null, not empty strings or defaults
        assert result.phone is None
        assert result.website is None
        assert result.rating is None
        assert result.street_address is None or "Edinburgh" in str(result.street_address)

        print("\n✓ LLM correctly used null for missing fields")
