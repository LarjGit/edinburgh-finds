# ============================================================
# GENERATED FILE - DO NOT EDIT
# ============================================================
#
# Generated from: engine/config/schemas/winery.yaml
# Generated at: 2026-01-19 15:35:52
#
# To make changes:
# 1. Edit engine/config/schemas/winery.yaml
# 2. Run: python -m engine.schema.generate
#
# ============================================================

from typing import List, Optional
from .core import FieldSpec
from .listing import LISTING_FIELDS

# ============================================================
# WINERY-SPECIFIC FIELDS
# ============================================================
#
# Winery-specific fields for wine venues and vineyards
# Extends: Listing
#
# ============================================================

WINERY_SPECIFIC_FIELDS: List[FieldSpec] = [
    FieldSpec(
        name="listing_id",
        type_annotation="str",
        description="Foreign key to parent Listing",
        nullable=False,
        required=False,
        primary_key=True,
        foreign_key="listings.listing_id",
        exclude=True,
    ),
    FieldSpec(
        name="grape_varieties",
        type_annotation="Optional[List[str]]",
        description="Grape varieties grown or featured at this winery",
        nullable=True,
        required=False,
        search_category="viticulture",
        search_keywords=["grapes", "varieties", "cultivars"],
        sa_column="Column(ARRAY(String))",
    ),
    FieldSpec(
        name="appellation",
        type_annotation="Optional[str]",
        description="Wine appellation or region (e.g., Bordeaux, Napa Valley)",
        nullable=True,
        required=False,
        search_category="viticulture",
        search_keywords=["appellation", "region", "AOC"],
    ),
    FieldSpec(
        name="vineyard_size_hectares",
        type_annotation="Optional[float]",
        description="Size of vineyard in hectares",
        nullable=True,
        required=False,
    ),
    FieldSpec(
        name="organic_certified",
        type_annotation="Optional[bool]",
        description="Whether the winery is certified organic",
        nullable=True,
        required=False,
        search_category="viticulture",
        search_keywords=["organic", "certified"],
    ),
    FieldSpec(
        name="wine_types",
        type_annotation="Optional[List[str]]",
        description="Types of wine produced (red, white, rosé, sparkling, dessert)",
        nullable=True,
        required=False,
        search_category="wine_production",
        search_keywords=["wine", "types", "red", "white", "sparkling"],
        sa_column="Column(ARRAY(String))",
    ),
    FieldSpec(
        name="annual_production_bottles",
        type_annotation="Optional[int]",
        description="Annual production volume in bottles",
        nullable=True,
        required=False,
    ),
    FieldSpec(
        name="tasting_room",
        type_annotation="Optional[bool]",
        description="Whether a tasting room is available",
        nullable=True,
        required=False,
        search_category="visitor_experience",
        search_keywords=["tasting", "room"],
    ),
    FieldSpec(
        name="tours_available",
        type_annotation="Optional[bool]",
        description="Whether vineyard or winery tours are offered",
        nullable=True,
        required=False,
        search_category="visitor_experience",
        search_keywords=["tours", "visits"],
    ),
    FieldSpec(
        name="reservation_required",
        type_annotation="Optional[bool]",
        description="Whether reservations are required for tastings/tours",
        nullable=True,
        required=False,
    ),
    FieldSpec(
        name="event_space",
        type_annotation="Optional[bool]",
        description="Whether the winery has event space for weddings, corporate events, etc.",
        nullable=True,
        required=False,
        search_category="visitor_experience",
        search_keywords=["events", "weddings", "venue"],
    ),
    FieldSpec(
        name="winery_summary",
        type_annotation="Optional[str]",
        description="A short overall description of the winery and its offerings",
        nullable=True,
        required=False,
    )
]

WINERY_FIELDS: List[FieldSpec] = LISTING_FIELDS + WINERY_SPECIFIC_FIELDS


def get_field_by_name(name: str) -> Optional[FieldSpec]:
    """Get field spec by name."""
    for field_spec in WINERY_FIELDS:
        if field_spec.name == name:
            return field_spec
    return None


def get_fields_with_search_metadata() -> List[FieldSpec]:
    """Get all Winery fields that have search metadata."""
    return [f for f in WINERY_FIELDS if f.search_category is not None]


def get_extraction_fields() -> List[FieldSpec]:
    """Get all Winery fields for LLM extraction (excludes internal fields)."""
    return [f for f in WINERY_FIELDS if not f.exclude]


def get_database_fields() -> List[FieldSpec]:
    """Get all Winery fields for database (includes internal/excluded fields)."""
    return WINERY_FIELDS
