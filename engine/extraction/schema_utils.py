"""
Schema utilities for extraction.

Provides helpers to access schema field specs for extraction and
build LLM-facing configs.

Engine-Lens Architecture:
- Engine uses universal LISTING_FIELDS only (vertical-agnostic)
- Vertical-specific fields are stored in modules JSON field
- Lens layer defines modules and triggers via lens.yaml
"""

from typing import Dict, List, Optional

from engine.schema import entity
from engine.schema.core import FieldSpec
from engine.schema.types import EntityType


def _normalize_entity_type(entity_type: Optional[object]) -> EntityType:
    """
    Normalize entity_type to EntityType enum.
    Note: VENUE is deprecated - use entity_class (place/person/organization/event/thing)
    """
    if entity_type is None:
        return EntityType.PLACE  # Default to PLACE (was VENUE)
    if isinstance(entity_type, EntityType):
        return entity_type
    if isinstance(entity_type, str):
        normalized = entity_type.strip().upper()
        # Handle legacy VENUE -> PLACE mapping
        if normalized == "VENUE":
            return EntityType.PLACE
        if normalized in EntityType.__members__:
            return EntityType[normalized]
        for member in EntityType:
            if member.value == normalized:
                return member
    return EntityType.PLACE  # Default to PLACE (was VENUE)


def get_extraction_fields(entity_type: Optional[object] = None) -> List[FieldSpec]:
    """
    Get schema fields that should be extracted (universal LISTING_FIELDS only).

    Engine-Lens Architecture:
    - All entity types use LISTING_FIELDS (vertical-agnostic)
    - Vertical-specific data goes into modules JSON field
    """
    # Always return universal entity fields regardless of entity type
    return entity.get_extraction_fields()


def is_field_in_schema(field_name: str, entity_type: Optional[object] = None) -> bool:
    """
    Check whether a field is part of the extraction schema.
    """
    return any(field.name == field_name for field in get_extraction_fields(entity_type))


def get_llm_config(entity_type: Optional[object] = None) -> List[Dict]:
    """
    Build a lightweight LLM config from schema field specs.
    """
    config: List[Dict] = []
    for field in get_extraction_fields(entity_type):
        config.append(
            {
                "name": field.name,
                "type": field.type_annotation,
                "description": field.description,
                "required": field.required,
                "search_category": field.search_category,
                "search_keywords": field.search_keywords or [],
            }
        )
    return config

