# ============================================================
# GENERATED FILE - DO NOT EDIT
# ============================================================
#
# Generated from: engine/config/schemas/entity.yaml
# Generated at: 2026-02-03 09:13:47
#
# To make changes:
# 1. Edit engine/config/schemas/entity.yaml
# 2. Run: python -m engine.schema.generate
#
# ============================================================

from typing import Any, Dict, List, Optional
from datetime import datetime
from .core import FieldSpec

# ============================================================
# ENTITY FIELDS
# ============================================================
#
# Base schema for all entity types (venues, retailers, coaches, etc.)
#
# ============================================================

ENTITY_FIELDS: List[FieldSpec] = [
    FieldSpec(
        name="entity_id",
        type_annotation="str",
        description="Unique identifier (auto-generated)",
        nullable=False,
        required=False,
        primary_key=True,
        exclude=True,
        default="None",
    ),
    FieldSpec(
        name="entity_name",
        type_annotation="str",
        description="Official name of the entity",
        nullable=False,
        required=True,
        index=True,
        search_category="identity",
        search_keywords=["name", "called", "named"],
    ),
    FieldSpec(
        name="entity_class",
        type_annotation="Optional[str]",
        description="Universal entity classification (place, person, organization, event, thing)",
        nullable=True,
        required=False,
        index=True,
        exclude=True,
    ),
    FieldSpec(
        name="slug",
        type_annotation="str",
        description="URL-safe version of entity name (auto-generated)",
        nullable=False,
        required=False,
        index=True,
        unique=True,
        exclude=True,
    ),
    FieldSpec(
        name="summary",
        type_annotation="Optional[str]",
        description="A short overall description of the entity summarising all gathered data",
        nullable=True,
        required=False,
        search_category="description",
        search_keywords=["description", "about", "overview"],
    ),
    FieldSpec(
        name="description",
        type_annotation="Optional[str]",
        description="Long-form aggregated evidence from multiple sources (reviews, snippets, editorial summaries)",
        nullable=True,
        required=False,
        search_category="description",
        search_keywords=["description", "details", "about", "information"],
    ),
    FieldSpec(
        name="raw_categories",
        type_annotation="Optional[List[str]]",
        description="Raw free-form categories detected by the LLM (uncontrolled observational labels - NOT indexed, NOT used for filtering)",
        nullable=True,
        required=False,
        exclude=True,
        default="default_factory=list",
        sa_column="Column(ARRAY(String))",
    ),
    FieldSpec(
        name="canonical_activities",
        type_annotation="Optional[List[str]]",
        description="Activities provided/supported (opaque values, lens-interpreted)",
        nullable=True,
        required=False,
        exclude=True,
        default="default_factory=list",
        sa_column="Column(ARRAY(String))",
    ),
    FieldSpec(
        name="canonical_roles",
        type_annotation="Optional[List[str]]",
        description="Roles this entity plays (opaque values, universal function-style keys)",
        nullable=True,
        required=False,
        exclude=True,
        default="default_factory=list",
        sa_column="Column(ARRAY(String))",
    ),
    FieldSpec(
        name="canonical_place_types",
        type_annotation="Optional[List[str]]",
        description="Physical place classifications (opaque values, lens-interpreted)",
        nullable=True,
        required=False,
        exclude=True,
        default="default_factory=list",
        sa_column="Column(ARRAY(String))",
    ),
    FieldSpec(
        name="canonical_access",
        type_annotation="Optional[List[str]]",
        description="Access requirements (opaque values, lens-interpreted)",
        nullable=True,
        required=False,
        exclude=True,
        default="default_factory=list",
        sa_column="Column(ARRAY(String))",
    ),
    FieldSpec(
        name="discovered_attributes",
        type_annotation="Optional[Dict[str, Any]]",
        description="Dictionary containing any extra attributes not explicitly defined in Listing or Entity models",
        nullable=True,
        required=False,
        sa_column="Column(JSON)",
    ),
    FieldSpec(
        name="modules",
        type_annotation="Optional[Dict[str, Any]]",
        description="Namespaced module data (JSONB) organized by module key",
        nullable=True,
        required=False,
        exclude=True,
        sa_column="Column(JSON)",
    ),
    FieldSpec(
        name="street_address",
        type_annotation="Optional[str]",
        description="Full street address including building number, street name, city and postcode",
        nullable=True,
        required=False,
        search_category="location",
        search_keywords=["address", "location", "street"],
    ),
    FieldSpec(
        name="city",
        type_annotation="Optional[str]",
        description="City or town",
        nullable=True,
        required=False,
        index=True,
        search_category="location",
        search_keywords=["city", "town"],
    ),
    FieldSpec(
        name="postcode",
        type_annotation="Optional[str]",
        description="Full UK postcode with correct spacing (e.g., 'SW1A 0AA')",
        nullable=True,
        required=False,
        index=True,
        search_category="location",
        search_keywords=["postcode", "postal code", "zip"],
    ),
    FieldSpec(
        name="country",
        type_annotation="Optional[str]",
        description="Country name",
        nullable=True,
        required=False,
        search_category="location",
        search_keywords=["country"],
    ),
    FieldSpec(
        name="latitude",
        type_annotation="Optional[float]",
        description="WGS84 Latitude coordinate (decimal degrees)",
        nullable=True,
        required=False,
    ),
    FieldSpec(
        name="longitude",
        type_annotation="Optional[float]",
        description="WGS84 Longitude coordinate (decimal degrees)",
        nullable=True,
        required=False,
    ),
    FieldSpec(
        name="phone",
        type_annotation="Optional[str]",
        description="Primary contact phone number with country code. MUST be E.164 UK format (e.g. '+441315397071')",
        nullable=True,
        required=False,
        search_category="contact",
        search_keywords=["phone", "telephone", "contact"],
    ),
    FieldSpec(
        name="email",
        type_annotation="Optional[str]",
        description="Primary public email address",
        nullable=True,
        required=False,
        search_category="contact",
        search_keywords=["email", "contact"],
    ),
    FieldSpec(
        name="website_url",
        type_annotation="Optional[str]",
        description="Official website URL",
        nullable=True,
        required=False,
        search_category="contact",
        search_keywords=["website", "url", "site"],
    ),
    FieldSpec(
        name="instagram_url",
        type_annotation="Optional[str]",
        description="Instagram profile URL or handle",
        nullable=True,
        required=False,
    ),
    FieldSpec(
        name="facebook_url",
        type_annotation="Optional[str]",
        description="Facebook page URL",
        nullable=True,
        required=False,
    ),
    FieldSpec(
        name="twitter_url",
        type_annotation="Optional[str]",
        description="Twitter/X profile URL or handle",
        nullable=True,
        required=False,
    ),
    FieldSpec(
        name="linkedin_url",
        type_annotation="Optional[str]",
        description="LinkedIn company page URL",
        nullable=True,
        required=False,
    ),
    FieldSpec(
        name="opening_hours",
        type_annotation="Optional[Dict[str, Any]]",
        description="Opening hours per day. May contain strings or nested open/close times. Example: {'monday': {'open': '05:30', 'close': '22:00'}, 'sunday': 'CLOSED'}",
        nullable=True,
        required=False,
        search_category="hours",
        search_keywords=["hours", "opening", "times"],
        sa_column="Column(JSON)",
    ),
    FieldSpec(
        name="source_info",
        type_annotation="Optional[Dict[str, Any]]",
        description="Provenance metadata: URLs, method (tavily/manual), timestamps, notes",
        nullable=True,
        required=False,
        exclude=True,
        default="default_factory=dict",
        sa_column="Column(JSON)",
    ),
    FieldSpec(
        name="field_confidence",
        type_annotation="Optional[Dict[str, float]]",
        description="Per-field confidence scores used for overwrite decisions",
        nullable=True,
        required=False,
        exclude=True,
        default="default_factory=dict",
        sa_column="Column(JSON)",
    ),
    FieldSpec(
        name="created_at",
        type_annotation="Optional[datetime]",
        description="Creation timestamp",
        nullable=True,
        required=False,
        exclude=True,
        sa_column="Column(DateTime(timezone=True), nullable=False, server_default=func.now())",
    ),
    FieldSpec(
        name="updated_at",
        type_annotation="Optional[datetime]",
        description="Last update timestamp",
        nullable=True,
        required=False,
        exclude=True,
        sa_column="Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())",
    ),
    FieldSpec(
        name="external_ids",
        type_annotation="Optional[Dict[str, Any]]",
        description="External system IDs (e.g., {'wordpress': 123, 'google': 'abc'})",
        nullable=True,
        required=False,
        exclude=True,
        sa_column="Column(JSON)",
    )
]

def get_field_by_name(name: str) -> Optional[FieldSpec]:
    """Get field spec by name."""
    for field_spec in ENTITY_FIELDS:
        if field_spec.name == name:
            return field_spec
    return None


def get_fields_with_search_metadata() -> List[FieldSpec]:
    """Get all Entity fields that have search metadata."""
    return [f for f in ENTITY_FIELDS if f.search_category is not None]


def get_extraction_fields() -> List[FieldSpec]:
    """Get all Entity fields for LLM extraction (excludes internal fields)."""
    return [f for f in ENTITY_FIELDS if not f.exclude]


def get_database_fields() -> List[FieldSpec]:
    """Get all Entity fields for database (includes internal/excluded fields)."""
    return ENTITY_FIELDS
