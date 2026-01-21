"""
Edinburgh Council Extractor

Transforms raw Edinburgh Council GeoJSON responses into structured listing fields.
Uses deterministic extraction (clean, structured GeoJSON data from ArcGIS).

Edinburgh Council provides local facility data via ArcGIS in GeoJSON format,
including sports centers, community facilities, and other council-managed venues.
"""

from typing import Dict, Tuple, Optional, List
from engine.extraction.base import BaseExtractor
from engine.extraction.schema_utils import get_extraction_fields, is_field_in_schema
from engine.extraction.extractors.google_places_extractor import format_phone_uk, format_postcode_uk
from engine.extraction.utils.opening_hours import parse_opening_hours


class EdinburghCouncilExtractor(BaseExtractor):
    """
    Extractor for Edinburgh Council GeoJSON data.

    This extractor transforms raw Edinburgh Council ArcGIS GeoJSON responses into
    structured listing fields. Edinburgh Council provides clean, structured data
    via ArcGIS, so this uses deterministic extraction (no LLM required).

    GeoJSON Structure (Edinburgh Council uses various field naming conventions):
    {
      "type": "Feature",
      "id": "facilities.123",
      "geometry": {
        "type": "Point",
        "coordinates": [longitude, latitude]
      },
      "properties": {
        "NAME": "Facility Name" (or FACILITY_NAME, SITE_NAME),
        "ADDRESS": "Street Address" (or STREET_ADDRESS),
        "POSTCODE": "EH12 3AB",
        "PHONE": "0131 123 4567" (or CONTACT_NUMBER),
        "EMAIL": "contact@example.com" (or CONTACT_EMAIL),
        "WEBSITE": "http://example.com" (or URL),
        "DESCRIPTION": "..." (or SUMMARY),
        "FACILITY_TYPE": "Swimming Pool" (or TYPE, CATEGORY),
        "CAPACITY": 150,
        "ACCESSIBLE": "Yes",
        ...
      }
    }

    Fields extracted:
    - entity_name: from NAME, FACILITY_NAME, or SITE_NAME
    - street_address: from ADDRESS or STREET_ADDRESS
    - city: defaults to "Edinburgh"
    - country: defaults to "Scotland"
    - latitude, longitude: from geometry.coordinates (reversed from GeoJSON [lng,lat] order)
    - phone: from PHONE or CONTACT_NUMBER (formatted to E.164)
    - email: from EMAIL or CONTACT_EMAIL
    - website: from WEBSITE or URL
    - postcode: from POSTCODE
    - summary: from DESCRIPTION or SUMMARY
    - categories: from FACILITY_TYPE, TYPE, CATEGORY
    - external_id: from feature id or OBJECTID or FID
    - entity_type: defaults to VENUE
    - capacity: from CAPACITY
    - wheelchair_accessible: from ACCESSIBLE
    - opening_hours: from OPENING_HOURS
    """

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "edinburgh_council"
        """
        return "edinburgh_council"

    def extract(self, raw_data: Dict) -> Dict:
        """
        Transform raw Edinburgh Council GeoJSON feature into extracted listing fields.

        Args:
            raw_data: Single GeoJSON feature from Edinburgh Council ArcGIS response

        Returns:
            Dict: Extracted fields mapped to schema names
        """
        extracted = {}

        # Get properties from GeoJSON feature
        properties = raw_data.get("properties", {})

        # Required fields - handle multiple possible field names
        entity_name = (
            properties.get("NAME") or
            properties.get("FACILITY_NAME") or
            properties.get("SITE_NAME") or
            "Unknown"
        )
        extracted["entity_name"] = entity_name

        # Address - Edinburgh Council defaults
        street_address = properties.get("ADDRESS") or properties.get("STREET_ADDRESS")
        if street_address:
            extracted["street_address"] = street_address

        extracted["city"] = "Edinburgh"  # All Edinburgh Council data is in Edinburgh
        extracted["country"] = "Scotland"

        # Postcode
        if "POSTCODE" in properties:
            formatted_postcode = format_postcode_uk(properties["POSTCODE"])
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
        phone = properties.get("PHONE") or properties.get("CONTACT_NUMBER")
        if phone:
            formatted_phone = format_phone_uk(phone)
            if formatted_phone:
                extracted["phone"] = formatted_phone

        email = properties.get("EMAIL") or properties.get("CONTACT_EMAIL")
        if email:
            extracted["email"] = email

        website = properties.get("WEBSITE") or properties.get("URL")
        if website:
            extracted["website"] = website

        # Summary/Description
        summary = properties.get("DESCRIPTION") or properties.get("SUMMARY")
        if summary:
            extracted["summary"] = summary

        # Categories - collect from multiple fields
        categories = self._extract_categories(properties)
        if categories:
            extracted["categories"] = categories

        # External ID
        external_id = (
            raw_data.get("id") or
            properties.get("OBJECTID") or
            properties.get("FID")
        )
        if external_id:
            extracted["external_id"] = str(external_id)

        # Structured attributes
        if "CAPACITY" in properties and properties["CAPACITY"]:
            try:
                extracted["capacity"] = int(properties["CAPACITY"])
            except (ValueError, TypeError):
                pass

        # Accessibility
        accessible = properties.get("ACCESSIBLE", "").lower()
        if accessible in ["yes", "y", "true", "1"]:
            extracted["wheelchair_accessible"] = True
        elif accessible in ["no", "n", "false", "0"]:
            extracted["wheelchair_accessible"] = False

        # Opening hours
        if "OPENING_HOURS" in properties and properties["OPENING_HOURS"]:
            parsed_hours = parse_opening_hours(properties["OPENING_HOURS"])
            if parsed_hours:
                extracted["opening_hours"] = parsed_hours

        # Store dataset name for provenance
        if "DATASET_NAME" in properties:
            extracted["DATASET_NAME"] = properties["DATASET_NAME"]

        return extracted

    def _extract_categories(self, properties: Dict) -> List[str]:
        """
        Extract categories from Edinburgh Council properties.

        Checks CATEGORY, TYPE, and FACILITY_TYPE fields.

        Args:
            properties: Feature properties dictionary

        Returns:
            List of category strings
        """
        categories = []

        # Check various category fields
        if "CATEGORY" in properties and properties["CATEGORY"]:
            categories.append(properties["CATEGORY"])
        if "TYPE" in properties and properties["TYPE"]:
            categories.append(properties["TYPE"])
        if "FACILITY_TYPE" in properties and properties["FACILITY_TYPE"]:
            categories.append(properties["FACILITY_TYPE"])

        # Remove duplicates while preserving order
        seen = set()
        unique_categories = []
        for cat in categories:
            if cat not in seen:
                seen.add(cat)
                unique_categories.append(cat)

        return unique_categories

    def validate(self, extracted: Dict) -> Dict:
        """
        Validate extracted fields against schema rules.

        Ensures:
        - Required fields are present (entity_name, entity_type)
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

        if "entity_type" not in validated:

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

        Edinburgh Council-specific fields like DATASET_NAME and CAPACITY
        (if not in schema) go into discovered_attributes.

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
