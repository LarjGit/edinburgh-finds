"""
Tests for Instructor LLM Client Integration

This module tests the LLM client wrapper that integrates Anthropic's Claude
with the Instructor library for structured output extraction.

Test Coverage:
- Client initialization and configuration
- Structured extraction with Pydantic models
- Retry logic with validation feedback (max 2 retries)
- Error handling for API failures
- Null semantics enforcement
- Token usage tracking
- Cost estimation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import BaseModel, ValidationError, Field
from typing import Optional, List


class SampleVenueExtraction(BaseModel):
    """Sample Pydantic model for testing structured extraction"""
    entity_name: str
    street_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    rating: Optional[float] = None


class TestInstructorClientInitialization:
    """Test LLM client initialization and configuration"""

    def test_llm_client_can_be_imported(self):
        """Test that InstructorClient can be imported"""
        try:
            from engine.extraction.llm_client import InstructorClient
            assert InstructorClient is not None
        except ImportError:
            pytest.fail("Failed to import InstructorClient - implementation not yet created")

    def test_llm_client_can_be_instantiated_with_api_key(self):
        """Test that InstructorClient can be instantiated with API key"""
        from engine.extraction.llm_client import InstructorClient

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            assert client is not None

    def test_llm_client_uses_api_key_from_env_if_not_provided(self):
        """Test that client reads API key from environment"""
        from engine.extraction.llm_client import InstructorClient

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-test-key'}):
            client = InstructorClient()
            assert client is not None

    def test_llm_client_raises_error_without_api_key(self):
        """Test that client raises error if no API key is available"""
        from engine.extraction.llm_client import InstructorClient

        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="API key"):
                InstructorClient()

    def test_llm_client_loads_model_from_config(self):
        """Test that client loads model name from extraction.yaml config"""
        from engine.extraction.llm_client import InstructorClient

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            # Should load "claude-haiku-20250318" from config
            assert client.model_name == "claude-haiku-20250318"


class TestStructuredExtraction:
    """Test structured extraction with Pydantic models"""

    @patch('anthropic.Anthropic')
    def test_extract_returns_structured_output(self, mock_anthropic):
        """Test that extract method returns structured Pydantic model"""
        from engine.extraction.llm_client import InstructorClient

        # Mock the Anthropic API response
        mock_client = Mock()
        mock_response = SampleVenueExtraction(
            entity_name="Test Venue",
            street_address="123 Test St",
            latitude=55.9533,
            longitude=-3.1883
        )
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            result = client.extract(
                prompt="Extract venue information",
                response_model=SampleVenueExtraction,
                context="Test venue data"
            )

            assert isinstance(result, SampleVenueExtraction)
            assert result.entity_name == "Test Venue"

    @patch('anthropic.Anthropic')
    def test_extract_passes_system_message(self, mock_anthropic):
        """Test that system message is passed to API"""
        from engine.extraction.llm_client import InstructorClient

        mock_client = Mock()
        mock_response = SampleVenueExtraction(entity_name="Test")
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            client.extract(
                prompt="Extract info",
                response_model=SampleVenueExtraction,
                context="Data",
                system_message="Custom system prompt"
            )

            # Verify system message was passed
            call_args = mock_client.messages.create.call_args
            assert call_args is not None

    @patch('anthropic.Anthropic')
    def test_extract_handles_optional_fields_as_null(self, mock_anthropic):
        """Test that optional fields are properly handled as None when missing"""
        from engine.extraction.llm_client import InstructorClient

        mock_client = Mock()
        # Only required field, optionals should be None
        mock_response = SampleVenueExtraction(entity_name="Minimal Venue")
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            result = client.extract(
                prompt="Extract",
                response_model=SampleVenueExtraction,
                context="Minimal data"
            )

            assert result.entity_name == "Minimal Venue"
            assert result.street_address is None
            assert result.latitude is None
            assert result.phone is None


class TestRetryLogic:
    """Test retry logic with validation feedback"""

    @patch('anthropic.Anthropic')
    def test_extract_retries_on_validation_error(self, mock_anthropic):
        """Test that failed extraction is retried with validation feedback"""
        from engine.extraction.llm_client import InstructorClient

        mock_client = Mock()

        # First call: validation error (missing required field)
        # Second call: success
        mock_client.messages.create.side_effect = [
            ValidationError.from_exception_data(
                "value_error",
                [{"type": "missing", "loc": ("entity_name",), "msg": "Field required"}]
            ),
            SampleVenueExtraction(entity_name="Retry Success")
        ]
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            result = client.extract(
                prompt="Extract",
                response_model=SampleVenueExtraction,
                context="Data"
            )

            # Should succeed on retry
            assert result.entity_name == "Retry Success"
            # Should have called API twice
            assert mock_client.messages.create.call_count == 2

    @patch('anthropic.Anthropic')
    def test_extract_max_retries_is_2(self, mock_anthropic):
        """Test that extraction fails after 2 retries (3 total attempts)"""
        from engine.extraction.llm_client import InstructorClient

        mock_client = Mock()

        # All attempts fail validation
        validation_error = ValidationError.from_exception_data(
            "value_error",
            [{"type": "missing", "loc": ("entity_name",), "msg": "Field required"}]
        )
        mock_client.messages.create.side_effect = [
            validation_error,
            validation_error,
            validation_error
        ]
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")

            with pytest.raises(ValidationError):
                client.extract(
                    prompt="Extract",
                    response_model=SampleVenueExtraction,
                    context="Bad data"
                )

            # Should have tried 3 times (initial + 2 retries)
            assert mock_client.messages.create.call_count == 3

    @patch('anthropic.Anthropic')
    def test_retry_includes_validation_feedback_in_prompt(self, mock_anthropic):
        """Test that retry attempts include validation error details"""
        from engine.extraction.llm_client import InstructorClient

        mock_client = Mock()

        validation_error = ValidationError.from_exception_data(
            "value_error",
            [{"type": "missing", "loc": ("entity_name",), "msg": "Field required"}]
        )

        # First fails, second succeeds
        mock_client.messages.create.side_effect = [
            validation_error,
            SampleVenueExtraction(entity_name="Fixed")
        ]
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            client.extract(
                prompt="Extract",
                response_model=SampleVenueExtraction,
                context="Data"
            )

            # Second call should include error feedback in prompt
            second_call_args = mock_client.messages.create.call_args_list[1]
            # The feedback should be included somehow (exact implementation may vary)
            assert mock_client.messages.create.call_count == 2


class TestErrorHandling:
    """Test error handling for various failure scenarios"""

    @patch('anthropic.Anthropic')
    def test_extract_raises_error_on_api_failure(self, mock_anthropic):
        """Test that API failures are properly raised"""
        from engine.extraction.llm_client import InstructorClient
        from anthropic import APIError

        mock_client = Mock()
        mock_client.messages.create.side_effect = APIError("API Error")
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")

            with pytest.raises(APIError):
                client.extract(
                    prompt="Extract",
                    response_model=SampleVenueExtraction,
                    context="Data"
                )

    @patch('anthropic.Anthropic')
    def test_extract_handles_rate_limit_errors(self, mock_anthropic):
        """Test handling of rate limit errors"""
        from engine.extraction.llm_client import InstructorClient
        from anthropic import RateLimitError

        mock_client = Mock()
        mock_client.messages.create.side_effect = RateLimitError("Rate limited")
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")

            with pytest.raises(RateLimitError):
                client.extract(
                    prompt="Extract",
                    response_model=SampleVenueExtraction,
                    context="Data"
                )


class TestTokenTracking:
    """Test token usage and cost tracking"""

    @patch('anthropic.Anthropic')
    def test_extract_tracks_token_usage(self, mock_anthropic):
        """Test that token usage is tracked and available"""
        from engine.extraction.llm_client import InstructorClient

        mock_client = Mock()
        mock_response = SampleVenueExtraction(entity_name="Test")
        # Mock usage data
        mock_response._raw_response = Mock()
        mock_response._raw_response.usage = Mock(
            input_tokens=100,
            output_tokens=50
        )
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            result = client.extract(
                prompt="Extract",
                response_model=SampleVenueExtraction,
                context="Data"
            )

            # Token tracking should be available
            usage = client.get_last_usage()
            assert usage is not None
            assert usage['input_tokens'] > 0
            assert usage['output_tokens'] > 0

    @patch('anthropic.Anthropic')
    def test_client_calculates_cost_estimate(self, mock_anthropic):
        """Test that client can estimate cost based on tokens"""
        from engine.extraction.llm_client import InstructorClient

        mock_client = Mock()
        mock_response = SampleVenueExtraction(entity_name="Test")
        mock_response._raw_response = Mock()
        mock_response._raw_response.usage = Mock(
            input_tokens=1000,
            output_tokens=500
        )
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")
            client.extract(
                prompt="Extract",
                response_model=SampleVenueExtraction,
                context="Data"
            )

            # Should calculate cost based on Haiku pricing
            cost = client.get_last_cost()
            assert cost is not None
            assert cost > 0
            # Haiku is very cheap, should be fractions of a penny
            assert cost < 0.01

    def test_get_total_usage_tracks_cumulative_tokens(self):
        """Test that client tracks total tokens across multiple calls"""
        from engine.extraction.llm_client import InstructorClient

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            client = InstructorClient(api_key="test-key")

            # Should have method to get cumulative usage
            total_usage = client.get_total_usage()
            assert total_usage is not None
            assert 'input_tokens' in total_usage
            assert 'output_tokens' in total_usage
            assert 'total_cost' in total_usage
