"""
Sport Scotland Extractor

Transforms raw Sport Scotland WFS GeoJSON responses into structured entity fields.
Uses deterministic extraction (clean, structured WFS data).

Sport Scotland provides official sports facility data via WFS (Web Feature Service)
in GeoJSON format, including various sports facilities across Scotland.
"""

from typing import Dict, Tuple, Optional
from engine.extraction.base import BaseExtractor
from engine.extraction.schema_utils import get_extraction_fields, is_field_in_schema
from engine.extraction.extractors.google_places_extractor import format_phone_uk, format_postcode_uk
from engine.extraction.utils.opening_hours import parse_opening_hours
from engine.orchestration.execution_context import ExecutionContext


class SportScotlandExtractor(BaseExtractor):
    """
    Extractor for Sport Scotland WFS data.

    This extractor transforms raw Sport Scotland WFS GeoJSON responses into
    structured entity fields. Sport Scotland provides clean, structured data
    via WFS, so this uses deterministic extraction (no LLM required).

    GeoJSON Structure:
    {
      "type": "Feature",
      "id": "sports_facility.1",
      "geometry": {
        "type": "Point",
        "coordinates": [longitude, latitude]  # Note: GeoJSON order
      },
      "properties": {
        "name": "Facility Name",
        "facility_type": "Sports Facility",
        "address": "Street Address",
        ...
      }
    }

    Fields extracted:
    - entity_name: from properties.name
    - street_address: from properties.address
    - latitude, longitude: from geometry.coordinates (reversed from GeoJSON [lng,lat] order)
    - phone: from properties.phone (formatted to E.164)
    - website: from properties.website
    - postcode: from properties.postcode
    - external_id: from feature id
    - facility_type: stored in discovered_attributes
    - surface_type: stored in discovered_attributes
    - ownership: stored in discovered_attributes
    - number_of_courts: stored in discovered_attributes
    - indoor_outdoor: stored in discovered_attributes
    - floodlit: stored in discovered_attributes

    Per architecture.md Section 4.2 (Extraction Boundary Contract), this extractor
    outputs ONLY schema primitives and raw observations. Domain interpretation
    (e.g., facility-specific fields) is handled by Phase 2 (Lens Application).
    """

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "sport_scotland"
        """
        return "sport_scotland"

    def extract(self, raw_data: Dict, *, ctx: ExecutionContext) -> Dict:
        """
        Transform raw Sport Scotland GeoJSON feature into extracted entity fields.

        Args:
            raw_data: Single GeoJSON feature from Sport Scotland WFS response

        Returns:
            Dict: Extracted fields mapped to schema names
        """
        extracted = {}

        # Get properties from GeoJSON feature
        properties = raw_data.get("properties", {})

        # Required fields
        extracted["entity_name"] = properties.get("name", "")

        # Address
        if "address" in properties:
            extracted["street_address"] = properties["address"]

        # Postcode
        if "postcode" in properties:
            formatted_postcode = format_postcode_uk(properties["postcode"])
            if formatted_postcode:
                extracted["postcode"] = formatted_postcode

        # Coordinates from GeoJSON geometry
        # NOTE: GeoJSON uses [longitude, latitude] order
        geometry = raw_data.get("geometry", {})
        if geometry.get("type") == "Point" and "coordinates" in geometry:
            coords = geometry["coordinates"]
            if len(coords) >= 2:
                extracted["longitude"] = coords[0]  # First element is longitude
                extracted["latitude"] = coords[1]   # Second element is latitude

        # Contact information
        if "phone" in properties:
            formatted_phone = format_phone_uk(properties["phone"])
            if formatted_phone:
                extracted["phone"] = formatted_phone

        if "website" in properties:
            extracted["website"] = properties["website"]

        # External ID (Sport Scotland feature ID)
        if "id" in raw_data:
            extracted["external_id"] = raw_data["id"]

        # Sport Scotland-specific fields
        facility_type = properties.get("facility_type", "")
        extracted["facility_type"] = facility_type

        if "surface_type" in properties:
            extracted["surface_type"] = properties["surface_type"]

        if "ownership" in properties:
            extracted["ownership"] = properties["ownership"]

        # Capture connector-native fields as raw observations
        # These fields (number_of_courts, indoor_outdoor, floodlit) will be stored
        # in discovered_attributes and interpreted by Phase 2 (Lens Application)
        # per architecture.md Section 4.2 - Extraction Boundary Contract
        if "number_of_courts" in properties:
            extracted["number_of_courts"] = properties["number_of_courts"]

        if "indoor_outdoor" in properties:
            extracted["indoor_outdoor"] = properties["indoor_outdoor"]

        if "floodlit" in properties:
            extracted["floodlit"] = properties["floodlit"]

        # Opening hours
        # Check various possible field names for opening hours
        opening_hours_raw = (
            properties.get("opening_hours") or
            properties.get("open_hours") or
            properties.get("hours")
        )
        if opening_hours_raw:
            parsed_hours = parse_opening_hours(opening_hours_raw)
            if parsed_hours:
                extracted["opening_hours"] = parsed_hours

        return extracted

    def validate(self, extracted: Dict) -> Dict:
        """
        Validate extracted fields against schema rules.

        Ensures:
        - Required fields are present (entity_name)
        - Phone is in E.164 format
        - Coordinates are valid
        - Types are appropriate

        Args:
            extracted: Extracted fields to validate

        Returns:
            Dict: Validated (and possibly normalized) fields
        """
        validated = extracted.copy()

        # Ensure required fields exist
        if "entity_name" not in validated or not validated["entity_name"]:
            raise ValueError("Missing required field: entity_name")

        # Validate phone format (should already be E.164, but double-check)
        if "phone" in validated and validated["phone"]:
            if not validated["phone"].startswith("+"):
                # Try to format again
                formatted = format_phone_uk(validated["phone"])
                if formatted:
                    validated["phone"] = formatted
                else:
                    # Remove invalid phone
                    del validated["phone"]

        # Validate coordinates
        if "latitude" in validated:
            lat = validated["latitude"]
            if lat is not None and (lat < -90 or lat > 90):
                del validated["latitude"]

        if "longitude" in validated:
            lng = validated["longitude"]
            if lng is not None and (lng < -180 or lng > 180):
                del validated["longitude"]

        return validated

    def split_attributes(self, extracted: Dict) -> Tuple[Dict, Dict]:
        """
        Split extracted fields into schema-defined and discovered attributes.

        Schema-defined fields go into attributes (main fields).
        Non-schema fields go into discovered_attributes (flexible bucket).

        Sport Scotland-specific fields like facility_type, surface_type, and
        ownership go into discovered_attributes.

        Args:
            extracted: Extracted fields to split

        Returns:
            Tuple[Dict, Dict]: (attributes, discovered_attributes)
        """
        attributes = {}
        discovered = {}

        for key, value in extracted.items():
            if is_field_in_schema(key):
                attributes[key] = value
            else:
                discovered[key] = value

        return attributes, discovered
