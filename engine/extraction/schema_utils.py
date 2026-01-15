"""
Schema utilities for extraction.

Provides helpers to access schema field specs for extraction and
build LLM-facing configs.
"""

from typing import Dict, List, Optional

from engine.schema import listing, venue
from engine.schema.core import FieldSpec
from engine.schema.types import EntityType


def _normalize_entity_type(entity_type: Optional[object]) -> EntityType:
    if entity_type is None:
        return EntityType.VENUE
    if isinstance(entity_type, EntityType):
        return entity_type
    if isinstance(entity_type, str):
        normalized = entity_type.strip().upper()
        if normalized in EntityType.__members__:
            return EntityType[normalized]
        for member in EntityType:
            if member.value == normalized:
                return member
    return EntityType.VENUE


def get_extraction_fields(entity_type: Optional[object] = None) -> List[FieldSpec]:
    """
    Get schema fields that should be extracted for the given entity type.
    """
    normalized = _normalize_entity_type(entity_type)
    if normalized == EntityType.VENUE:
        return venue.get_extraction_fields()
    return listing.get_extraction_fields()


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

