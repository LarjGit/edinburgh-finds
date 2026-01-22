"""
OSM Extractor - LLM-based extraction from OpenStreetMap Overpass API

This extractor transforms raw OSM Overpass API responses (nodes, ways, relations
with free-form tags) into structured venue information using the Instructor LLM client.

OSM provides structured but free-form key-value tag data (e.g., sport=padel,
addr:city=Edinburgh, name:en=...), which requires intelligent parsing to extract
venue details. The LLM handles:
- Tag mapping to schema fields (sport=* → facilities, amenity=* → categories)
- Multi-lingual tag extraction (name:en, name:fr, etc.)
- Address assembly from OSM addr:* tags
- Contact information parsing and formatting
- Handling ambiguity and missing data with appropriate null values

Example input (OSM Overpass API response):
{
    "version": 0.6,
    "elements": [
        {
            "type": "node",
            "id": 123456789,
            "lat": 55.9533,
            "lon": -3.1883,
            "tags": {
                "name": "Edinburgh Padel Club",
                "sport": "padel",
                "leisure": "sports_centre",
                "addr:city": "Edinburgh",
                "addr:postcode": "EH14 4TZ",
                "phone": "+44 131 539 7071",
                "capacity:courts": "4"
            }
        },
        ...
    ]
}

Example output:
{
    "entity_name": "Edinburgh Padel Club",
    "city": "Edinburgh",
    "postcode": "EH14 4TZ",
    "latitude": 55.9533,
    "longitude": -3.1883,
    "phone": "+441315397071",
    "padel": true,
    "padel_total_courts": 4,
    "external_ids": {"osm": "node/123456789"},
    ...
}
"""

from typing import Dict, List, Tuple
from pathlib import Path

from engine.extraction.base import BaseExtractor
from engine.extraction.llm_client import InstructorClient
from engine.extraction.models.entity_extraction import EntityExtraction
from engine.extraction.attribute_splitter import split_attributes as split_attrs
from engine.extraction.schema_utils import get_extraction_fields
from engine.extraction.utils.opening_hours import parse_opening_hours


class OSMExtractor(BaseExtractor):
    """
    Extractor for OpenStreetMap Overpass API responses.

    Uses LLM-based extraction to parse OSM tag data into structured venue
    information. Handles tag mapping, multi-lingual data, and OSM ID tracking.
    """

    def __init__(self, llm_client=None):
        """
        Initialize OSM extractor with LLM client and prompt template.

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

        # Load OSM-specific prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "osm_extraction.txt"
        with open(prompt_path, 'r') as f:
            prompt_template = f.read()

        # Inject classification rules dynamically
        classification_rules = self._get_classification_rules()
        self.system_message = prompt_template.replace("{classification_rules}", classification_rules)

        # Get schema fields for attribute splitting (universal entity fields)
        self.schema_fields = get_extraction_fields()

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this extractor's data source.

        Returns:
            str: "openstreetmap"
        """
        return "openstreetmap"

    def _get_classification_rules(self) -> str:
        """
        Generate classification rules text for injection into prompt.

        Returns:
            str: Formatted classification rules for LLM prompt
        """
        return """   Use the following priority order to determine entity_class:

   1. **Time-bounded** (has start/end times) → entity_class = "event"
   2. **Physical location** (has coordinates or street address) → entity_class = "place"
   3. **Named individual** → entity_class = "person"
   4. **Membership/group entity** → entity_class = "organization"
   5. **Fallback** → entity_class = "thing"

   Additionally, determine canonical_roles (optional, multi-valued array):
   - What the entity DOES (functions/capabilities)
   - Examples: ["provides_facility", "provides_instruction", "sells_goods", "membership_org"]

   Classification examples:
   - Sports centre with courts → entity_class="place", canonical_roles=["provides_facility"]
   - Individual coach → entity_class="person", canonical_roles=["provides_instruction"]
   - Tournament with dates → entity_class="event", canonical_roles=[]
   - Retail chain → entity_class="organization", canonical_roles=["sells_goods"]"""

    def _aggregate_osm_elements(self, elements: List[Dict]) -> str:
        """
        Aggregate OSM elements into single context string for LLM.

        Combines type, ID, coordinates, and tags from multiple OSM elements
        (nodes, ways, relations) to provide comprehensive context for extraction.
        The LLM will identify the primary venue and extract relevant information
        across all elements.

        Args:
            elements: List of OSM elements from Overpass API

        Returns:
            str: Aggregated text containing all element information

        Example:
            >>> elements = [
            ...     {
            ...         "type": "node",
            ...         "id": 123,
            ...         "lat": 55.95,
            ...         "lon": -3.18,
            ...         "tags": {"name": "Venue A", "sport": "padel"}
            ...     },
            ...     {
            ...         "type": "way",
            ...         "id": 456,
            ...         "tags": {"name": "Venue A", "building": "yes"}
            ...     }
            ... ]
            >>> aggregated = extractor._aggregate_osm_elements(elements)
            >>> print(aggregated)
            '''
            Element 1 (node #123):
            Coordinates: Lat 55.95, Lon -3.18
            Tags:
              - name: Venue A
              - sport: padel

            Element 2 (way #456):
            Tags:
              - name: Venue A
              - building: yes
            '''
        """
        if not elements:
            return ""

        aggregated_parts = []

        for idx, element in enumerate(elements, 1):
            element_type = element.get('type', 'unknown')
            element_id = element.get('id', 'unknown')
            lat = element.get('lat')
            lon = element.get('lon')
            tags = element.get('tags', {})

            element_text = f"Element {idx} ({element_type} #{element_id}):\n"

            # Add coordinates if available (nodes have them, ways/relations might not)
            if lat is not None and lon is not None:
                element_text += f"Coordinates: Lat {lat}, Lon {lon}\n"

            # Add all tags
            if tags:
                element_text += "Tags:\n"
                for key, value in tags.items():
                    element_text += f"  - {key}: {value}\n"

            aggregated_parts.append(element_text)

        return "\n".join(aggregated_parts)

    def _extract_primary_osm_id(self, elements: List[Dict]) -> str:
        """
        Extract the primary OSM ID for deduplication.

        Uses the first element's type and ID to create a unique identifier
        in the format "type/id" (e.g., "node/123456789").

        Args:
            elements: List of OSM elements

        Returns:
            str: OSM identifier in format "type/id"

        Example:
            >>> elements = [{"type": "node", "id": 123456789}]
            >>> osm_id = extractor._extract_primary_osm_id(elements)
            >>> print(osm_id)
            'node/123456789'
        """
        if not elements:
            return "unknown/unknown"

        primary = elements[0]
        element_type = primary.get('type', 'unknown')
        element_id = primary.get('id', 'unknown')

        return f"{element_type}/{element_id}"

    def extract(self, raw_data: Dict) -> Dict:
        """
        Transform raw OSM Overpass API response into extracted listing fields.

        This method:
        1. Extracts OSM elements from Overpass response
        2. Aggregates element data (tags, coordinates, metadata)
        3. Uses LLM to extract structured venue information
        4. Converts Pydantic model to dictionary
        5. Adds OSM ID to external_ids for deduplication

        Args:
            raw_data: Raw OSM Overpass API response containing elements

        Returns:
            Dict: Extracted fields mapped to schema names

        Raises:
            ValueError: If elements array is empty or missing
            ValidationError: If LLM extraction fails after retries

        Example:
            >>> osm_data = {
            ...     "version": 0.6,
            ...     "elements": [...]
            ... }
            >>> extracted = extractor.extract(osm_data)
            >>> print(extracted["entity_name"])
            'Edinburgh Padel Club'
            >>> print(extracted["external_ids"]["osm"])
            'node/123456789'
        """
        # Extract OSM elements
        elements = raw_data.get('elements', [])

        if not elements:
            raise ValueError("No OSM elements found in Overpass API data")

        # Aggregate element data for LLM context
        aggregated_context = self._aggregate_osm_elements(elements)

        # Extract using LLM
        extraction_result = self.llm_client.extract(
            prompt="Extract structured venue information from the OpenStreetMap elements below. "
                   "Map OSM tags to venue fields (e.g., sport=padel → padel: true, "
                   "addr:city → city, capacity:courts → padel_total_courts). "
                   "Use null for any information not found in the tags.",
            response_model=EntityExtraction,
            context=aggregated_context,
            system_message=self.system_message
        )

        # Convert Pydantic model to dictionary
        extracted_dict = extraction_result.model_dump()

        # Parse and normalize opening hours if present
        if 'opening_hours' in extracted_dict and extracted_dict['opening_hours'] is not None:
            parsed_hours = parse_opening_hours(extracted_dict['opening_hours'])
            extracted_dict['opening_hours'] = parsed_hours

        # Extract and add OSM ID for deduplication
        osm_id = self._extract_primary_osm_id(elements)
        if 'external_ids' not in extracted_dict:
            extracted_dict['external_ids'] = {}
        extracted_dict['external_ids']['osm'] = osm_id

        return extracted_dict

    def validate(self, extracted: Dict) -> Dict:
        """
        Validate extracted fields against schema rules.

        For OSM extraction, validation focuses on:
        - Ensuring entity_name is present (required field)
        - Preserving null values (expected for sparse OSM data)
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
            ...     "entity_name": "Edinburgh Padel Club",
            ...     "city": "Edinburgh",
            ...     "osm_specific_tag": "custom value"
            ... }
            >>> attrs, discovered = extractor.split_attributes(extracted)
            >>> print(attrs.keys())
            dict_keys(['entity_name', 'city'])
            >>> print(discovered.keys())
            dict_keys(['osm_specific_tag'])
        """
        return split_attrs(extracted, self.schema_fields)
