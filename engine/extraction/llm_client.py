"""
LLM Client for Structured Extraction

This module provides a wrapper around the Anthropic API using the Instructor
library for structured output extraction with Pydantic models.

Features:
- Structured extraction with automatic Pydantic validation
- Retry logic with validation feedback (max 2 retries)
- Token usage and cost tracking
- Configurable model selection from extraction.yaml
"""

import os
from typing import TypeVar, Type, Optional, Dict, Any
from pydantic import BaseModel, ValidationError
import anthropic
import instructor
from pathlib import Path
import yaml

from engine.extraction.llm_cost import get_usage_tracker, calculate_cost
from engine.extraction.logging_config import get_extraction_logger, log_llm_call


T = TypeVar('T', bound=BaseModel)


class InstructorClient:
    """
    Client for making structured LLM extraction calls using Anthropic Claude
    with Instructor for Pydantic model validation.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Instructor client.

        Args:
            api_key: Anthropic API key. If not provided, reads from ANTHROPIC_API_KEY env var.

        Raises:
            ValueError: If no API key is available
        """
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "API key required. Provide via parameter or set ANTHROPIC_API_KEY environment variable."
            )

        # Load configuration
        self._load_config()

        # Initialize Anthropic client with Instructor
        self.anthropic_client = anthropic.Anthropic(api_key=self.api_key)
        self.client = instructor.from_anthropic(self.anthropic_client)

        # Token tracking
        self._last_usage: Optional[Dict[str, int]] = None
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost = 0.0

        # Haiku pricing (per million tokens) as of Jan 2025
        # Input: $0.80 per MTok, Output: $4.00 per MTok
        self._input_cost_per_million = 0.80
        self._output_cost_per_million = 4.00

    def _load_config(self):
        """Load model configuration from extraction.yaml"""
        config_path = Path(__file__).parent.parent / "config" / "extraction.yaml"

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.model_name = config.get('llm', {}).get('model', 'claude-haiku-20250318')

    def extract(
        self,
        prompt: str,
        response_model: Type[T],
        context: str,
        system_message: Optional[str] = None,
        max_retries: int = 2,
        source: Optional[str] = None,
        record_id: Optional[str] = None,
    ) -> T:
        """
        Extract structured data using LLM with automatic retry on validation failure.

        Args:
            prompt: The extraction instruction prompt
            response_model: Pydantic model class for structured output
            context: The raw data context to extract from
            system_message: Optional custom system message
            max_retries: Maximum number of retry attempts (default: 2)
            source: Optional data source name for tracking
            record_id: Optional record ID for tracking

        Returns:
            Instance of response_model with extracted data

        Raises:
            ValidationError: If extraction fails after max retries
            anthropic.APIError: If API call fails
        """
        # Build user message
        user_message = f"{prompt}\n\nContext:\n{context}"

        # Default system message
        if system_message is None:
            system_message = (
                "You are a data extraction assistant. Extract structured information "
                "from the provided context. Follow these rules:\n"
                "- Only extract information explicitly present in the context\n"
                "- Use null for missing optional fields (null ≠ false for booleans)\n"
                "- Ensure all required fields are populated\n"
                "- Be precise and factual"
            )

        validation_feedback = None
        attempt = 0

        while attempt <= max_retries:
            try:
                # Add validation feedback to subsequent attempts
                if validation_feedback:
                    user_message_with_feedback = (
                        f"{user_message}\n\n"
                        f"PREVIOUS ATTEMPT FAILED VALIDATION:\n{validation_feedback}\n"
                        f"Please correct the issues and try again."
                    )
                else:
                    user_message_with_feedback = user_message

                # Make API call with Instructor
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=4096,
                    system=system_message,
                    messages=[
                        {
                            "role": "user",
                            "content": user_message_with_feedback
                        }
                    ],
                    response_model=response_model
                )

                # Track token usage
                if hasattr(response, '_raw_response') and hasattr(response._raw_response, 'usage'):
                    usage = response._raw_response.usage
                    self._last_usage = {
                        'input_tokens': usage.input_tokens,
                        'output_tokens': usage.output_tokens
                    }
                    self._total_input_tokens += usage.input_tokens
                    self._total_output_tokens += usage.output_tokens

                    # Calculate cost
                    input_cost = (usage.input_tokens / 1_000_000) * self._input_cost_per_million
                    output_cost = (usage.output_tokens / 1_000_000) * self._output_cost_per_million
                    call_cost = input_cost + output_cost
                    self._total_cost += call_cost

                    # Record usage in global tracker
                    if source and record_id:
                        tracker = get_usage_tracker()
                        tracker.record_usage(
                            model=self.model_name,
                            tokens_in=usage.input_tokens,
                            tokens_out=usage.output_tokens,
                            source=source,
                            record_id=record_id,
                        )

                        # Log the LLM call
                        logger = get_extraction_logger()
                        log_llm_call(
                            logger=logger,
                            source=source,
                            record_id=record_id,
                            model=self.model_name,
                            tokens_in=usage.input_tokens,
                            tokens_out=usage.output_tokens,
                            duration_seconds=0.0,  # Duration tracked by caller
                            cost_usd=call_cost,
                        )

                return response

            except ValidationError as e:
                attempt += 1
                if attempt > max_retries:
                    # Max retries exceeded, raise the error
                    raise e

                # Build validation feedback for retry
                validation_feedback = self._format_validation_error(e)

        # Should never reach here, but just in case
        raise ValidationError("Extraction failed after max retries")

    def _format_validation_error(self, error: ValidationError) -> str:
        """
        Format validation error into human-readable feedback for LLM.

        Args:
            error: The Pydantic ValidationError

        Returns:
            Formatted error message string
        """
        errors = error.errors()
        feedback_lines = []

        for err in errors:
            field = '.'.join(str(loc) for loc in err['loc'])
            msg = err['msg']
            feedback_lines.append(f"- Field '{field}': {msg}")

        return '\n'.join(feedback_lines)

    def get_last_usage(self) -> Optional[Dict[str, int]]:
        """
        Get token usage from the last API call.

        Returns:
            Dictionary with 'input_tokens' and 'output_tokens', or None if no calls made
        """
        return self._last_usage

    def get_last_cost(self) -> Optional[float]:
        """
        Get estimated cost of the last API call.

        Returns:
            Cost in USD, or None if no calls made
        """
        if self._last_usage is None:
            return None

        input_cost = (self._last_usage['input_tokens'] / 1_000_000) * self._input_cost_per_million
        output_cost = (self._last_usage['output_tokens'] / 1_000_000) * self._output_cost_per_million

        return input_cost + output_cost

    def get_total_usage(self) -> Dict[str, Any]:
        """
        Get cumulative token usage and cost across all API calls.

        Returns:
            Dictionary with total input_tokens, output_tokens, and total_cost
        """
        return {
            'input_tokens': self._total_input_tokens,
            'output_tokens': self._total_output_tokens,
            'total_cost': self._total_cost
        }
