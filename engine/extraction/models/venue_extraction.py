"""
Pydantic models for venue extraction with LLM.

These models define the structured output format for LLM-based extraction.
They align with the schema defined in engine/schema/listing.py and venue.py,
but are optimized for LLM extraction with clear field descriptions and
proper null semantics.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class VenueExtraction(BaseModel):
    """
    Structured output model for venue extraction from unstructured data.

    This model represents the fields that should be extracted from raw data
    sources (Serper, OSM, etc.) and validated before storage in ExtractedListing.

    IMPORTANT NULL SEMANTICS:
    - Use null for missing information (not "Unknown" or empty strings)
    - For booleans: null means "unknown", True means "yes", False means "no"
    - For strings: null means "not found", empty string "" is not allowed
    """

    # ------------------------------------------------------------------
    # IDENTIFICATION (Required)
    # ------------------------------------------------------------------
    entity_name: str = Field(
        description="Official name of the venue. REQUIRED. Must be the actual business name, not a description."
    )

    # ------------------------------------------------------------------
    # LOCATION (Highly Important)
    # ------------------------------------------------------------------
    street_address: Optional[str] = Field(
        default=None,
        description="Full street address including building number, street name, city, and postcode. Null if not found in context."
    )

    city: Optional[str] = Field(
        default=None,
        description="City or town name. Null if not found in context."
    )

    postcode: Optional[str] = Field(
        default=None,
        description="Full UK postcode with correct spacing (e.g., 'SW1A 0AA'). Null if not found in context."
    )

    country: Optional[str] = Field(
        default=None,
        description="Country name. Null if not found in context."
    )

    latitude: Optional[float] = Field(
        default=None,
        description="WGS84 Latitude coordinate (decimal degrees). Null if not found in context.",
        ge=-90.0,
        le=90.0
    )

    longitude: Optional[float] = Field(
        default=None,
        description="WGS84 Longitude coordinate (decimal degrees). Null if not found in context.",
        ge=-180.0,
        le=180.0
    )

    # ------------------------------------------------------------------
    # CONTACT
    # ------------------------------------------------------------------
    phone: Optional[str] = Field(
        default=None,
        description="Primary contact phone number. MUST be E.164 UK format (e.g., '+441315397071'). Null if not found."
    )

    email: Optional[str] = Field(
        default=None,
        description="Primary contact email address. Null if not found in context."
    )

    website: Optional[str] = Field(
        default=None,
        description="Official website URL. Null if not found in context."
    )

    # ------------------------------------------------------------------
    # CLASSIFICATION
    # ------------------------------------------------------------------
    categories: Optional[List[str]] = Field(
        default=None,
        description="Free-form categories that describe the venue (e.g., ['Padel Club', 'Sports Facility']). Null if not found."
    )

    # ------------------------------------------------------------------
    # RATINGS & REVIEWS
    # ------------------------------------------------------------------
    rating: Optional[float] = Field(
        default=None,
        description="Average rating (typically 0-5 scale). Null if not found in context.",
        ge=0.0,
        le=5.0
    )

    user_rating_count: Optional[int] = Field(
        default=None,
        description="Number of user ratings/reviews. Null if not found in context.",
        ge=0
    )

    # ------------------------------------------------------------------
    # SUMMARY / DESCRIPTION
    # ------------------------------------------------------------------
    summary: Optional[str] = Field(
        default=None,
        description="A short overall description of the venue (100-200 characters). Null if not found or cannot be synthesized."
    )

    # ------------------------------------------------------------------
    # OPERATIONAL
    # ------------------------------------------------------------------
    opening_hours: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Opening hours in structured format. Null if not found in context."
    )

    currently_open: Optional[bool] = Field(
        default=None,
        description="Whether the venue is currently open. null = unknown, True = yes, False = no."
    )

    # ------------------------------------------------------------------
    # EXTERNAL IDs (for deduplication)
    # ------------------------------------------------------------------
    external_id: Optional[str] = Field(
        default=None,
        description="External identifier from source system (e.g., Google Place ID, OSM ID). Null if not applicable."
    )

    # ------------------------------------------------------------------
    # DISCOVERED ATTRIBUTES (Catch-all)
    # ------------------------------------------------------------------
    discovered_attributes: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Dictionary of additional attributes discovered but not in the core schema. "
            "Examples: facilities offered, equipment available, membership info. Null if none discovered."
        )
    )

    @field_validator('entity_name')
    @classmethod
    def validate_entity_name_not_empty(cls, v: str) -> str:
        """Ensure entity_name is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError("entity_name cannot be empty")
        return v.strip()

    @field_validator('phone')
    @classmethod
    def validate_phone_e164_format(cls, v: Optional[str]) -> Optional[str]:
        """Ensure phone is in E.164 format if provided"""
        if v is None:
            return None

        # Must start with +44 for UK
        if not v.startswith('+'):
            raise ValueError("Phone number must be in E.164 format (starting with +)")

        # No spaces or dashes allowed in E.164
        if ' ' in v or '-' in v:
            raise ValueError("Phone number must not contain spaces or dashes in E.164 format")

        return v

    @field_validator('website')
    @classmethod
    def validate_website_url(cls, v: Optional[str]) -> Optional[str]:
        """Ensure website is a valid URL if provided"""
        if v is None:
            return None

        if not v.startswith(('http://', 'https://')):
            raise ValueError("Website must be a valid URL starting with http:// or https://")

        return v

    @field_validator('postcode')
    @classmethod
    def validate_postcode_format(cls, v: Optional[str]) -> Optional[str]:
        """Ensure postcode follows UK format if provided"""
        if v is None:
            return None

        # UK postcodes should have a space
        # Pattern: "XX## #XX" or variations
        if ' ' not in v:
            raise ValueError("UK postcode should contain a space (e.g., 'EH12 9GR')")

        # Should be uppercase
        if v != v.upper():
            raise ValueError("Postcode should be uppercase")

        return v

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "entity_name": "Game4Padel Edinburgh Park",
                "street_address": "1 New Park Square, Edinburgh Park, Edinburgh EH12 9GR",
                "city": "Edinburgh",
                "postcode": "EH12 9GR",
                "country": "United Kingdom",
                "latitude": 55.930189,
                "longitude": -3.315341,
                "phone": "+441315397071",
                "email": None,
                "website": "https://www.game4padel.co.uk/edinburgh-park",
                "categories": ["Padel Club", "Sports Facility"],
                "rating": 4.4,
                "user_rating_count": 15,
                "summary": "Indoor padel facility in Edinburgh Park with multiple courts",
                "opening_hours": None,
                "currently_open": None,
                "external_id": "ChIJhwNDsAjFh0gRDARGLR5vtdI",
                "discovered_attributes": {
                    "has_parking": True,
                    "equipment_rental": True
                }
            }
        }
