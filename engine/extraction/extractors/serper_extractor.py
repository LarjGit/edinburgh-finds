"""
Serper Extractor - LLM-based extraction from Google search results

This extractor transforms raw Serper API responses (Google search snippets)
into structured venue information using the Instructor LLM client.

Serper provides unstructured text snippets from search results, which requires
intelligent parsing to extract venue details. The LLM handles:
- Entity name identification from mixed search results
- Address extraction from fragments across multiple snippets
- Contact information parsing and formatting
- Handling ambiguity and missing data with appropriate null values

Example input (Serper API response):
{
    "searchParameters": {"q": "padel edinburgh"},
    "organic": [
        {
            "title": "Game4Padel Edinburgh",
            "link": "https://...",
            "snippet": "Premier padel facility at New Park Square..."
        },
        ...
    ]
}

Example output:
{
    "entity_name": "Game4Padel Edinburgh Park",
    "street_address": "1 New Park Square, Edinburgh",
    "city": "Edinburgh",
    "phone": "+441315397071",
    "website": "https://www.game4padel.co.uk/edinburgh-park",
    ...
}
"""

from typing import Dict, List, Tuple
from pathlib import Path

from engine.extraction.base import BaseExtractor
from engine.extraction.llm_client import InstructorClient
from engine.extraction.models.venue_extraction import VenueExtraction
from engine.extraction.attribute_splitter import split_attributes as split_attrs
from engine.extraction.schema_utils import get_extraction_fields
from engine.extraction.utils.opening_hours import parse_opening_hours


class SerperExtractor(BaseExtractor):
    """
    Extractor for Serper API search results.

    Uses LLM-based extraction to parse unstructured search snippets into
    structured venue data. Handles snippet aggregation, null semantics,
    and validation.
    """

    def __init__(self, llm_client=None):
        """
        Initialize Serper extractor with LLM client and prompt template.

        Args:
            llm_client: Optional InstructorClient instance. If not provided,
                       creates a new instance (requires ANTHROPIC_API_KEY env var).
                       Tests can inject a mock client.
        """
        # Initialize LLM client
        if llm_client is None:
            self.llm_client = InstructorClient()
        else:
            self.llm_client = llm_client

        # Load Serper-specific prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "serper_extraction.txt"
        with open(prompt_path, 'r') as f:
            self.system_message = f.read()

        # Get schema fields for attribute splitting
        self.schema_fields = get_extraction_fields(entity_type="VENUE")

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this extractor's data source.

        Returns:
            str: "serper"
        """
        return "serper"

    def _aggregate_snippets(self, organic_results: List[Dict]) -> str:
        """
        Aggregate search snippets into single context string for LLM.

        Combines title, snippet, and link from multiple search results to provide
        comprehensive context for extraction. The LLM will identify the primary venue
        and extract relevant information across all snippets.

        Args:
            organic_results: List of organic search results from Serper

        Returns:
            str: Aggregated text containing all snippet information

        Example:
            >>> results = [
            ...     {"title": "Venue A", "snippet": "Info about venue", "link": "..."},
            ...     {"title": "Venue A Reviews", "snippet": "More info", "link": "..."}
            ... ]
            >>> aggregated = extractor._aggregate_snippets(results)
            >>> print(aggregated)
            '''
            Result 1:
            Title: Venue A
            Link: ...
            Snippet: Info about venue

            Result 2:
            Title: Venue A Reviews
            ...
            '''
        """
        if not organic_results:
            return ""

        aggregated_parts = []

        for idx, result in enumerate(organic_results, 1):
            title = result.get('title', '')
            link = result.get('link', '')
            snippet = result.get('snippet', '')

            result_text = f"Result {idx}:\n"
            if title:
                result_text += f"Title: {title}\n"
            if link:
                result_text += f"Link: {link}\n"
            if snippet:
                result_text += f"Snippet: {snippet}\n"

            aggregated_parts.append(result_text)

        return "\n".join(aggregated_parts)

    def extract(self, raw_data: Dict) -> Dict:
        """
        Transform raw Serper search results into extracted listing fields.

        This method:
        1. Extracts organic search results from Serper response
        2. Aggregates snippets from multiple results
        3. Uses LLM to extract structured venue information
        4. Converts Pydantic model to dictionary

        Args:
            raw_data: Raw Serper API response containing search results

        Returns:
            Dict: Extracted fields mapped to schema names

        Raises:
            ValueError: If organic results are empty or missing
            ValidationError: If LLM extraction fails after retries

        Example:
            >>> serper_data = {
            ...     "searchParameters": {"q": "padel edinburgh"},
            ...     "organic": [...]
            ... }
            >>> extracted = extractor.extract(serper_data)
            >>> print(extracted["entity_name"])
            'Game4Padel Edinburgh Park'
        """
        # Extract organic results
        organic_results = raw_data.get('organic', [])

        if not organic_results:
            raise ValueError("No organic search results found in Serper data")

        # Aggregate snippets for LLM context
        aggregated_context = self._aggregate_snippets(organic_results)

        # Extract using LLM
        extraction_result = self.llm_client.extract(
            prompt="Extract structured venue information from the search results below. "
                   "Identify the primary venue and extract all available information. "
                   "Use null for any information not found in the snippets.",
            response_model=VenueExtraction,
            context=aggregated_context,
            system_message=self.system_message
        )

        # Convert Pydantic model to dictionary
        extracted_dict = extraction_result.model_dump()

        # Add entity_type default
        extracted_dict['entity_type'] = 'VENUE'

        # Parse and normalize opening hours if present
        if 'opening_hours' in extracted_dict and extracted_dict['opening_hours'] is not None:
            parsed_hours = parse_opening_hours(extracted_dict['opening_hours'])
            extracted_dict['opening_hours'] = parsed_hours

        return extracted_dict

    def validate(self, extracted: Dict) -> Dict:
        """
        Validate extracted fields against schema rules.

        For Serper extraction, validation focuses on:
        - Ensuring entity_name is present (required field)
        - Preserving null values (expected for unstructured search data)
        - Basic type checking

        Args:
            extracted: Extracted fields to validate

        Returns:
            Dict: Validated (and possibly normalized) fields

        Raises:
            ValueError: If required fields are missing
        """
        # Ensure entity_name is present
        if not extracted.get('entity_name'):
            raise ValueError("entity_name is required but was not extracted")

        # Validation passed - return as-is
        # (Pydantic validation already happened in LLM extraction)
        return extracted

    def split_attributes(self, extracted: Dict) -> Tuple[Dict, Dict]:
        """
        Split extracted fields into schema-defined and discovered attributes.

        Uses the attribute splitter utility to separate fields that belong in the
        core schema vs. fields that should go into discovered_attributes.

        Args:
            extracted: Extracted fields to split

        Returns:
            Tuple[Dict, Dict]: (attributes, discovered_attributes)

        Example:
            >>> extracted = {
            ...     "entity_name": "Venue",
            ...     "city": "Edinburgh",
            ...     "custom_field": "custom value"
            ... }
            >>> attrs, discovered = extractor.split_attributes(extracted)
            >>> print(attrs.keys())
            dict_keys(['entity_name', 'city'])
            >>> print(discovered.keys())
            dict_keys(['custom_field'])
        """
        return split_attrs(extracted, self.schema_fields)

    def extract_rich_text(self, raw_data: Dict) -> List[str]:
        """
        Extract rich text descriptions from Serper search results.

        Extracts snippets from organic search results which provide contextual
        descriptions of venues from various web sources.

        Args:
            raw_data: Serper API response with organic search results

        Returns:
            List[str]: List of snippets from search results
        """
        rich_text = []

        # Extract snippets from organic search results
        organic_results = raw_data.get("organic", [])
        for result in organic_results:
            if isinstance(result, dict):
                snippet = result.get("snippet", "")
                if snippet and isinstance(snippet, str):
                    rich_text.append(snippet)

        return rich_text
