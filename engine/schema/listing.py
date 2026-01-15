from typing import Optional, List, Dict, Any
from .core import FieldSpec
from .types import EntityType

# ============================================================
# LISTING FIELDS (Common to all entity types)
# ============================================================
#
# These fields are shared by ALL entity types: Venue, Retailer, Club, etc.
# They form the base Listing class in the database.
# ============================================================

LISTING_FIELDS: List[FieldSpec] = [
    # ------------------------------------------------------------------
    # IDENTIFICATION
    # ------------------------------------------------------------------
    FieldSpec(
        name="listing_id",
        type_annotation="str",
        description="Unique identifier (auto-generated)",
        nullable=False,
        required=False,  # Auto-generated, so not required in input
        primary_key=True,
        exclude=True,  # Auto-generated, not for LLM extraction
        default="None"
    ),
    FieldSpec(
        name="entity_name",
        type_annotation="str",
        description="Official name of the entity",
        nullable=False,
        required=True,
        index=True,
        search_category="identity",
        search_keywords=["name", "called", "named"]
    ),
    FieldSpec(
        name="entity_type",
        type_annotation="EntityType",
        description="Type of entity (venue, retailer, cafe, event, members_club, etc)",
        nullable=False,
        required=True,
        index=True
    ),
    FieldSpec(
        name="slug",
        type_annotation="str",
        description="URL-safe version of entity name (auto-generated)",
        nullable=False,
        required=False,
        unique=True,
        index=True,
        exclude=True,  # Auto-generated
        default="None"
    ),

    # ------------------------------------------------------------------
    # SUMMARY / DESCRIPTION
    # ------------------------------------------------------------------
    FieldSpec(
        name="summary",
        type_annotation="Optional[str]",
        description="A short overall description of the entity summarising all gathered data",
        search_category="description",
        search_keywords=["description", "about", "overview"]
    ),

    # ------------------------------------------------------------------
    # CLASSIFICATION
    # ------------------------------------------------------------------
    FieldSpec(
        name="categories",
        type_annotation="Optional[List[str]]",
        description="Raw free-form categories detected by the LLM (uncontrolled labels)",
        sa_column="Column(ARRAY(String))",
        search_category="categories",
        search_keywords=["categories", "type", "kind"]
    ),
    FieldSpec(
        name="canonical_categories",
        type_annotation="Optional[List[str]]",
        description="Cleaned, controlled categories used for navigation and taxonomy",
        sa_column="Column(ARRAY(String))",
        exclude=True  # Auto-generated from categories
    ),

    # ------------------------------------------------------------------
    # FLEXIBLE ATTRIBUTE BUCKET
    # ------------------------------------------------------------------
    FieldSpec(
        name="discovered_attributes",
        type_annotation="Optional[Dict[str, Any]]",
        description="Dictionary containing any extra attributes not explicitly defined in Listing or Entity models",
        sa_column="Column(JSON)"
    ),

    # ------------------------------------------------------------------
    # LOCATION
    # ------------------------------------------------------------------
    FieldSpec(
        name="street_address",
        type_annotation="Optional[str]",
        description="Full street address including building number, street name, city and postcode",
        search_category="location",
        search_keywords=["address", "location", "street"]
    ),
    FieldSpec(
        name="city",
        type_annotation="Optional[str]",
        description="City or town",
        index=True,
        search_category="location",
        search_keywords=["city", "town"]
    ),
    FieldSpec(
        name="postcode",
        type_annotation="Optional[str]",
        description="Full UK postcode with correct spacing (e.g., 'SW1A 0AA')",
        index=True,
        search_category="location",
        search_keywords=["postcode", "postal code", "zip"]
    ),
    FieldSpec(
        name="country",
        type_annotation="Optional[str]",
        description="Country name",
        search_category="location",
        search_keywords=["country"]
    ),
    FieldSpec(
        name="latitude",
        type_annotation="Optional[float]",
        description="WGS84 Latitude coordinate (decimal degrees)"
    ),
    FieldSpec(
        name="longitude",
        type_annotation="Optional[float]",
        description="WGS84 Longitude coordinate (decimal degrees)"
    ),

    # ------------------------------------------------------------------
    # CONTACT
    # ------------------------------------------------------------------
    FieldSpec(
        name="phone",
        type_annotation="Optional[str]",
        description="Primary contact phone number with country code. MUST be E.164 UK format (e.g. '+441315397071')",
        search_category="contact",
        search_keywords=["phone", "telephone", "contact"]
    ),
    FieldSpec(
        name="email",
        type_annotation="Optional[str]",
        description="Primary public email address",
        search_category="contact",
        search_keywords=["email", "contact"]
    ),
    FieldSpec(
        name="website_url",
        type_annotation="Optional[str]",
        description="Official website URL",
        search_category="contact",
        search_keywords=["website", "url", "site"]
    ),

    # ------------------------------------------------------------------
    # SOCIAL MEDIA
    # ------------------------------------------------------------------
    FieldSpec(
        name="instagram_url",
        type_annotation="Optional[str]",
        description="Instagram profile URL or handle"
    ),
    FieldSpec(
        name="facebook_url",
        type_annotation="Optional[str]",
        description="Facebook page URL"
    ),
    FieldSpec(
        name="twitter_url",
        type_annotation="Optional[str]",
        description="Twitter/X profile URL or handle"
    ),
    FieldSpec(
        name="linkedin_url",
        type_annotation="Optional[str]",
        description="LinkedIn company page URL"
    ),

    # ------------------------------------------------------------------
    # OPENING HOURS
    # ------------------------------------------------------------------
    FieldSpec(
        name="opening_hours",
        type_annotation="Optional[Dict[str, Any]]",
        description=(
            "Opening hours per day. May contain strings or nested open/close times. "
            "Example: {'monday': {'open': '05:30', 'close': '22:00'}, "
            "'sunday': 'CLOSED'}"
        ),
        sa_column="Column(JSON)",
        search_category="hours",
        search_keywords=["hours", "opening", "times"]
    ),

    # ------------------------------------------------------------------
    # METADATA (excluded from extraction)
    # ------------------------------------------------------------------
    FieldSpec(
        name="source_info",
        type_annotation="Dict[str, Any]",
        description="Provenance metadata: URLs, method (tavily/manual), timestamps, notes",
        default="default_factory=dict",
        sa_column="Column(JSON)",
        exclude=True
    ),
    FieldSpec(
        name="field_confidence",
        type_annotation="Dict[str, float]",
        description="Per-field confidence scores used for overwrite decisions",
        default="default_factory=dict",
        sa_column="Column(JSON)",
        exclude=True
    ),
    FieldSpec(
        name="created_at",
        type_annotation="Optional[datetime]",
        description="Creation timestamp",
        sa_column='Column(DateTime(timezone=True), nullable=False, server_default=func.now())',
        exclude=True
    ),
    FieldSpec(
        name="updated_at",
        type_annotation="Optional[datetime]",
        description="Last update timestamp",
        sa_column='Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())',
        exclude=True
    ),
    FieldSpec(
        name="external_ids",
        type_annotation="Optional[Dict[str, Any]]",
        description="External system IDs (e.g., {'wordpress': 123, 'google': 'abc'})",
        sa_column="Column(JSON)",
        exclude=True
    ),
]


def get_field_by_name(name: str) -> Optional[FieldSpec]:
    """Get field spec by name."""
    for field_spec in LISTING_FIELDS:
        if field_spec.name == name:
            return field_spec
    return None


def get_fields_with_search_metadata() -> List[FieldSpec]:
    """Get all Listing fields that have search metadata."""
    return [f for f in LISTING_FIELDS if f.search_category is not None]


def get_required_fields() -> List[FieldSpec]:
    """Get all required (non-optional) Listing fields."""
    return [f for f in LISTING_FIELDS if f.required]


def get_database_fields() -> List[FieldSpec]:
    """Get all Listing fields for database (includes internal/excluded fields)."""
    return LISTING_FIELDS


def get_extraction_fields() -> List[FieldSpec]:
    """Get all Listing fields for LLM extraction (excludes internal fields)."""
    return [f for f in LISTING_FIELDS if not f.exclude]
