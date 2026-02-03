# ============================================================
# GENERATED FILE - DO NOT EDIT
# ============================================================
#
# Generated from: engine/config/schemas/entity.yaml
# Generated at: 2026-02-03 09:13:44
#
# To make changes:
# 1. Edit engine/config/schemas/entity.yaml
# 2. Run: python -m engine.schema.generate
#
# ============================================================

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

class EntityExtraction(BaseModel):
    """Extraction model for Base schema for all entity types (venues, retailers, coaches, etc.)."""

    entity_name: str = Field(description="Official name of the entity REQUIRED.")

    summary: Optional[str] = Field(default=None, description="A short overall description of the entity summarising all gathered data Null if not found.")

    description: Optional[str] = Field(default=None, description="Long-form aggregated evidence from multiple sources (reviews, snippets, editorial summaries) Null if not found.")

    discovered_attributes: Optional[Dict[str, Any]] = Field(default=None, description="Dictionary containing any extra attributes not explicitly defined in Listing or Entity models Null if not found.")

    street_address: Optional[str] = Field(default=None, description="Full street address including building number, street name, city and postcode Null if not found.")

    city: Optional[str] = Field(default=None, description="City or town Null if not found.")

    postcode: Optional[str] = Field(default=None, description="Full UK postcode with correct spacing (e.g., 'SW1A 0AA') Null if not found.")

    country: Optional[str] = Field(default=None, description="Country name Null if not found.")

    latitude: Optional[float] = Field(default=None, description="WGS84 Latitude coordinate (decimal degrees) Null if not found.")

    longitude: Optional[float] = Field(default=None, description="WGS84 Longitude coordinate (decimal degrees) Null if not found.")

    phone: Optional[str] = Field(default=None, description="Primary contact phone number with country code. MUST be E.164 UK format (e.g. '+441315397071') Null if not found.")

    email: Optional[str] = Field(default=None, description="Primary public email address Null if not found.")

    website: Optional[str] = Field(default=None, description="Official website URL Null if not found.")

    instagram_url: Optional[str] = Field(default=None, description="Instagram profile URL or handle Null if not found.")

    facebook_url: Optional[str] = Field(default=None, description="Facebook page URL Null if not found.")

    twitter_url: Optional[str] = Field(default=None, description="Twitter/X profile URL or handle Null if not found.")

    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn company page URL Null if not found.")

    opening_hours: Optional[Dict[str, Any]] = Field(default=None, description="Opening hours per day. May contain strings or nested open/close times. Example: {'monday': {'open': '05:30', 'close': '22:00'}, 'sunday': 'CLOSED'} Null if not found.")

    rating: Optional[float] = Field(default=None, description="Average rating (typically 0-5 scale) Null if not found.")

    user_rating_count: Optional[int] = Field(default=None, description="Number of user ratings/reviews Null if not found.")

    currently_open: Optional[bool] = Field(default=None, description="Whether the entity is currently open Null means unknown.")

    external_id: Optional[str] = Field(default=None, description="External identifier from source system (e.g., Google Place ID, OSM ID) Null if not found.")

    @field_validator("entity_name")
    @classmethod
    def validate_entity_name_not_empty(cls, v: str) -> str:
        """Ensure entity_name is not empty or just whitespace"""
        if not v.strip():
            raise ValueError("entity_name cannot be empty")
        return v.strip()

    @field_validator("postcode")
    @classmethod
    def validate_postcode_format(cls, v: Optional[str]) -> Optional[str]:
        """Ensure postcode follows UK format if provided"""
        if v is None:
            return None
        if ' ' not in v:
            raise ValueError("UK postcode should contain a space (e.g., 'EH12 9GR')")
        if v != v.upper():
            raise ValueError("Postcode should be uppercase")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone_e164_format(cls, v: Optional[str]) -> Optional[str]:
        """Ensure phone is in E.164 format if provided"""
        if v is None:
            return None
        if not v.startswith('+'):
            raise ValueError("Phone number must be in E.164 format (starting with +)")
        if ' ' in v or '-' in v:
            raise ValueError("Phone number must not contain spaces or dashes in E.164 format")
        return v

    @field_validator("website")
    @classmethod
    def validate_website_url(cls, v: Optional[str]) -> Optional[str]:
        """Ensure website is a valid URL if provided"""
        if v is None:
            return None
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Website must be a valid URL starting with http:// or https://")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_name": "Example"
            }
        }
    )
