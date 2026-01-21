"""
Google Places Extractor

Transforms raw Google Places API responses into structured listing fields.
Uses deterministic extraction (clean, structured API data).
"""

import re
from typing import Dict, Tuple, Optional, List
import phonenumbers
from phonenumbers import NumberParseException

from engine.extraction.base import BaseExtractor
from engine.extraction.schema_utils import get_extraction_fields, is_field_in_schema
from engine.extraction.utils.opening_hours import parse_opening_hours


def format_phone_uk(phone: Optional[str]) -> Optional[str]:
    """
    Format a UK phone number to E.164 format (+44...).

    Args:
        phone: Phone number in various formats (national, international, etc.)

    Returns:
        str: Phone number in E.164 format (+441234567890) or None if invalid

    Examples:
        >>> format_phone_uk("0131 539 7071")
        '+441315397071'
        >>> format_phone_uk("+44 131 539 7071")
        '+441315397071'
        >>> format_phone_uk("invalid")
        None
    """
    if not phone:
        return None

    try:
        # Parse the phone number assuming it's a UK number
        # If it starts with +, parse without region
        if phone.strip().startswith('+'):
            parsed = phonenumbers.parse(phone, None)
        else:
            parsed = phonenumbers.parse(phone, "GB")

        # Validate the number
        if not phonenumbers.is_valid_number(parsed):
            return None

        # Format to E.164
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    except NumberParseException:
        return None


def format_postcode_uk(postcode: Optional[str]) -> Optional[str]:
    """
    Format a UK postcode with correct spacing and capitalization.

    Args:
        postcode: Postcode in various formats

    Returns:
        str: Properly formatted UK postcode (e.g., "EH12 9GR") or None if invalid

    Examples:
        >>> format_postcode_uk("EH129GR")
        'EH12 9GR'
        >>> format_postcode_uk("eh12 9gr")
        'EH12 9GR'
    """
    if not postcode:
        return None

    # Remove all whitespace and convert to uppercase
    cleaned = postcode.strip().upper().replace(" ", "")

    # UK postcode regex pattern
    # Format: A(A)9(9) 9AA or A(A)99 9AA
    # Examples: EH12 9GR, SW1A 1AA, M1 1AA
    pattern = r'^([A-Z]{1,2}\d{1,2}[A-Z]?)(\d[A-Z]{2})$'

    match = re.match(pattern, cleaned)
    if not match:
        return None

    # Add space between outward and inward codes
    outward = match.group(1)
    inward = match.group(2)
    return f"{outward} {inward}"


def extract_postcode_from_address(address: Optional[str]) -> Optional[str]:
    """
    Extract and format UK postcode from a full address string.

    Args:
        address: Full address string potentially containing a postcode

    Returns:
        str: Formatted UK postcode or None if not found

    Examples:
        >>> extract_postcode_from_address("123 Main St, London, SW1A 1AA, UK")
        'SW1A 1AA'
    """
    if not address:
        return None

    # UK postcode pattern within address text
    # More permissive pattern to find postcodes in various formats
    pattern = r'\b([A-Z]{1,2}\d{1,2}[A-Z]?)\s?(\d[A-Z]{2})\b'

    match = re.search(pattern, address.upper())
    if match:
        outward = match.group(1)
        inward = match.group(2)
        postcode = f"{outward}{inward}"
        return format_postcode_uk(postcode)

    return None


class GooglePlacesExtractor(BaseExtractor):
    """
    Extractor for Google Places API data.

    This extractor transforms raw Google Places API v1 responses into
    structured listing fields. Google Places provides clean, structured data,
    so this uses deterministic extraction (no LLM required).

    Fields extracted:
    - entity_name: from displayName.text
    - street_address: from formattedAddress
    - latitude, longitude: from location
    - phone: from internationalPhoneNumber (formatted to E.164)
    - website: from websiteUri
    - rating, user_rating_count: from rating and userRatingCount
    - postcode: extracted from formattedAddress
    - external_id: from id (Google Place ID)
    - entity_type: defaults to VENUE
    """

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "google_places"
        """
        return "google_places"

    def extract(self, raw_data: Dict) -> Dict:
        """
        Transform raw Google Places data into extracted listing fields.

        Args:
            raw_data: Single place object from Google Places API v1 response

        Returns:
            Dict: Extracted fields mapped to schema names
        """
        extracted = {}

        # Required fields
        extracted["entity_name"] = raw_data.get("displayName", {}).get("text", "")
        # entity_type is not assigned here; inferred from types or validated later if needed

        # Address and location
        if "formattedAddress" in raw_data:
            extracted["street_address"] = raw_data["formattedAddress"]

            # Extract postcode from address
            postcode = extract_postcode_from_address(raw_data["formattedAddress"])
            if postcode:
                extracted["postcode"] = postcode

        if "location" in raw_data:
            extracted["latitude"] = raw_data["location"].get("latitude")
            extracted["longitude"] = raw_data["location"].get("longitude")

        # Contact information
        # Prefer internationalPhoneNumber, fallback to nationalPhoneNumber
        phone_raw = raw_data.get("internationalPhoneNumber") or raw_data.get("nationalPhoneNumber")
        if phone_raw:
            formatted_phone = format_phone_uk(phone_raw)
            if formatted_phone:
                extracted["phone"] = formatted_phone

        if "websiteUri" in raw_data:
            extracted["website"] = raw_data["websiteUri"]

        # Rating information
        if "rating" in raw_data:
            extracted["rating"] = raw_data["rating"]

        if "userRatingCount" in raw_data:
            extracted["user_rating_count"] = raw_data["userRatingCount"]

        # Opening hours
        if "regularOpeningHours" in raw_data:
            opening_hours_raw = raw_data["regularOpeningHours"]

            # Google provides weekdayDescriptions which we can parse
            if "weekdayDescriptions" in opening_hours_raw:
                descriptions = opening_hours_raw["weekdayDescriptions"]
                # Join descriptions for parsing
                hours_text = " | ".join(descriptions)
                parsed_hours = parse_opening_hours(hours_text)
                if parsed_hours:
                    extracted["opening_hours"] = parsed_hours

        # External ID (Google Place ID)
        if "id" in raw_data:
            extracted["external_id"] = raw_data["id"]

        # Google-specific fields (will go to discovered_attributes)
        if "googleMapsUri" in raw_data:
            extracted["google_maps_uri"] = raw_data["googleMapsUri"]

        if "types" in raw_data:
            extracted["types"] = raw_data["types"]

        return extracted

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

        # entity_type is optional at this stage


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

    def extract_rich_text(self, raw_data: Dict) -> List[str]:
        """
        Extract rich text descriptions from Google Places data.

        Extracts:
        - editorialSummary: Google's editorial description of the place
        - reviews: User review texts (up to first 5 reviews)

        Args:
            raw_data: Single place object from Google Places API v1 response

        Returns:
            List[str]: List of text descriptions for summary synthesis
        """
        rich_text = []

        # Extract editorial summary
        if "editorialSummary" in raw_data:
            editorial = raw_data["editorialSummary"]
            # editorialSummary can be a dict with 'text' key or a direct string
            if isinstance(editorial, dict) and "text" in editorial:
                rich_text.append(editorial["text"])
            elif isinstance(editorial, str):
                rich_text.append(editorial)

        # Extract reviews (limit to first 5 to avoid overwhelming the synthesizer)
        if "reviews" in raw_data and isinstance(raw_data["reviews"], list):
            for review in raw_data["reviews"][:5]:
                if isinstance(review, dict) and "text" in review:
                    # Review text can be nested in 'text' dict or direct
                    review_text = review["text"]
                    if isinstance(review_text, dict) and "text" in review_text:
                        rich_text.append(review_text["text"])
                    elif isinstance(review_text, str):
                        rich_text.append(review_text)

        return rich_text
