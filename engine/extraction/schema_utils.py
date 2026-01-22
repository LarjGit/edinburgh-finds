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


def get_extraction_fields() -> List[FieldSpec]:
    """
    Get schema fields that should be extracted (universal LISTING_FIELDS only).

    Engine-Lens Architecture:
    - All entity types use LISTING_FIELDS (vertical-agnostic)
    - Vertical-specific data goes into modules JSON field
    """
    # Always return universal entity fields regardless of entity type
    return entity.get_extraction_fields()


def is_field_in_schema(field_name: str) -> bool:
    """
    Check whether a field is part of the extraction schema.
    """
    return any(field.name == field_name for field in get_extraction_fields())


def get_llm_config() -> List[Dict]:
    """
    Build a lightweight LLM config from schema field specs.
    """
    config: List[Dict] = []
    for field in get_extraction_fields():
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

