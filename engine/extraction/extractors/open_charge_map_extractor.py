"""
OpenChargeMap Extractor

Transforms raw OpenChargeMap API responses into structured listing fields.
Uses deterministic extraction (clean, structured API data).

OpenChargeMap is an enrichment source that provides EV charging infrastructure
data. This can supplement venue listings by showing nearby charging facilities.
"""

from typing import Dict, Tuple, Optional, List
from engine.extraction.base import BaseExtractor
from engine.extraction.schema_utils import is_field_in_schema
from engine.extraction.extractors.google_places_extractor import format_phone_uk, format_postcode_uk
from engine.schema.types import EntityType


class OpenChargeMapExtractor(BaseExtractor):
    """
    Extractor for OpenChargeMap API data.

    This extractor transforms raw OpenChargeMap API responses into
    structured listing fields. OpenChargeMap provides clean, structured data
    about EV charging stations, so this uses deterministic extraction (no LLM required).

    Fields extracted:
    - entity_name: from AddressInfo.Title
    - street_address: combined from AddressInfo fields
    - latitude, longitude: from AddressInfo
    - phone: from OperatorInfo.PhonePrimaryContact (formatted to E.164)
    - postcode: from AddressInfo.Postcode (formatted)
    - external_id: from UUID
    - entity_type: defaults to VENUE

    EV-specific fields (go to discovered_attributes):
    - operator_name: from OperatorInfo.Title
    - usage_type: from UsageType.Title
    - usage_cost: pricing information
    - is_operational: from StatusType.IsOperational
    - number_of_points: number of charging points
    - connections: list of connector details (type, power, quantity)
    - access_comments: from AddressInfo.AccessComments
    """

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "open_charge_map"
        """
        return "open_charge_map"

    def extract(self, raw_data: Dict) -> Dict:
        """
        Transform raw OpenChargeMap data into extracted listing fields.

        Args:
            raw_data: Single charging station object from OpenChargeMap API response

        Returns:
            Dict: Extracted fields mapped to schema names
        """
        extracted = {}

        # Extract from AddressInfo
        address_info = raw_data.get("AddressInfo", {})

        # Required fields
        extracted["entity_name"] = address_info.get("Title", "")
        extracted["entity_type"] = EntityType.VENUE.value  # Default to VENUE

        # Build street address from components
        address_parts = []
        if address_info.get("AddressLine1"):
            address_parts.append(address_info["AddressLine1"])
        if address_info.get("AddressLine2"):
            address_parts.append(address_info["AddressLine2"])
        if address_info.get("Town"):
            address_parts.append(address_info["Town"])
        if address_info.get("StateOrProvince"):
            address_parts.append(address_info["StateOrProvince"])

        if address_parts:
            extracted["street_address"] = ", ".join(address_parts)

        # Location coordinates
        if "Latitude" in address_info and address_info["Latitude"] is not None:
            extracted["latitude"] = address_info["Latitude"]

        if "Longitude" in address_info and address_info["Longitude"] is not None:
            extracted["longitude"] = address_info["Longitude"]

        # Postcode
        if "Postcode" in address_info and address_info["Postcode"]:
            formatted_postcode = format_postcode_uk(address_info["Postcode"])
            if formatted_postcode:
                extracted["postcode"] = formatted_postcode

        # Access comments (discovered field)
        if "AccessComments" in address_info and address_info["AccessComments"]:
            extracted["access_comments"] = address_info["AccessComments"]

        # External ID (OpenChargeMap UUID)
        if "UUID" in raw_data:
            extracted["external_id"] = raw_data["UUID"]

        # Operator information
        operator_info = raw_data.get("OperatorInfo", {})
        if operator_info:
            if "Title" in operator_info:
                extracted["operator_name"] = operator_info["Title"]

            # Phone number from operator
            phone_raw = operator_info.get("PhonePrimaryContact")
            if phone_raw:
                formatted_phone = format_phone_uk(phone_raw)
                if formatted_phone:
                    extracted["phone"] = formatted_phone

        # Usage type information
        usage_type = raw_data.get("UsageType", {})
        if usage_type and "Title" in usage_type:
            extracted["usage_type"] = usage_type["Title"]

        # Usage cost
        if "UsageCost" in raw_data and raw_data["UsageCost"]:
            extracted["usage_cost"] = raw_data["UsageCost"]

        # Operational status
        status_type = raw_data.get("StatusType", {})
        if status_type and "IsOperational" in status_type:
            extracted["is_operational"] = status_type["IsOperational"]

        # Number of charging points
        if "NumberOfPoints" in raw_data and raw_data["NumberOfPoints"]:
            extracted["number_of_points"] = raw_data["NumberOfPoints"]

        # Extract connection information
        connections = raw_data.get("Connections", [])
        if connections is not None:  # Include even if empty list
            extracted["connections"] = self._extract_connections(connections)

        # General comments
        if "GeneralComments" in raw_data and raw_data["GeneralComments"]:
            extracted["general_comments"] = raw_data["GeneralComments"]

        return extracted

    def _extract_connections(self, connections: List[Dict]) -> List[Dict]:
        """
        Extract charging connection details from Connections array.

        Args:
            connections: List of connection objects from OpenChargeMap

        Returns:
            List[Dict]: Simplified connection information
        """
        extracted_connections = []

        for conn in connections:
            connection_info = {}

            # Connection type
            conn_type = conn.get("ConnectionType", {})
            if conn_type and "Title" in conn_type:
                connection_info["type"] = conn_type["Title"]

            # Power output
            if "PowerKW" in conn and conn["PowerKW"]:
                connection_info["power_kw"] = conn["PowerKW"]

            # Quantity
            if "Quantity" in conn and conn["Quantity"]:
                connection_info["quantity"] = conn["Quantity"]

            # Charging level
            level = conn.get("Level", {})
            if level and "Title" in level:
                connection_info["level"] = level["Title"]

            # Current type
            current_type = conn.get("CurrentType", {})
            if current_type and "Title" in current_type:
                connection_info["current_type"] = current_type["Title"]

            # Voltage and amperage
            if "Voltage" in conn and conn["Voltage"]:
                connection_info["voltage"] = conn["Voltage"]

            if "Amps" in conn and conn["Amps"]:
                connection_info["amps"] = conn["Amps"]

            extracted_connections.append(connection_info)

        return extracted_connections

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
            validated["entity_type"] = EntityType.VENUE.value

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
        Non-schema fields (EV-specific) go into discovered_attributes (flexible bucket).

        Args:
            extracted: Extracted fields to split

        Returns:
            Tuple[Dict, Dict]: (attributes, discovered_attributes)
        """
        attributes = {}
        discovered = {}

        for key, value in extracted.items():
            if is_field_in_schema(key, entity_type=EntityType.VENUE):
                attributes[key] = value
            else:
                discovered[key] = value

        return attributes, discovered
