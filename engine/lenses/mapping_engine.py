"""
Lens Mapping Engine

Applies lens mapping rules to populate canonical dimensions from raw entity data.
Phase 2 extraction: Runs after source extractors (Phase 1).

Architecture: Per architecture.md Section 6.4
- Rules execute over union of declared source_fields
- First match wins per rule
- Multiple rules may contribute to same dimension
- Deduplication + deterministic lexicographic ordering
"""
import re
from typing import Dict, List, Optional, Any


def match_rule_against_entity(rule: Dict[str, Any], entity: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Match a single mapping rule against entity fields.

    Searches pattern across union of source_fields. First match wins.

    Args:
        rule: Mapping rule with pattern, canonical, dimension, source_fields
        entity: Entity dict with raw field values

    Returns:
        Dict with dimension and value if match found, None otherwise

    Example:
        >>> rule = {"pattern": r"(?i)padel", "canonical": "padel",
        ...         "dimension": "canonical_activities", "source_fields": ["entity_name"]}
        >>> entity = {"entity_name": "Padel Club"}
        >>> match_rule_against_entity(rule, entity)
        {"dimension": "canonical_activities", "value": "padel"}
    """
    pattern = rule.get("pattern")
    canonical = rule.get("canonical")
    dimension = rule.get("dimension")
    source_fields = rule.get("source_fields", [])

    if not pattern or not canonical or not dimension:
        return None

    # Search pattern across union of source_fields
    for field_name in source_fields:
        field_value = entity.get(field_name)

        if field_value is None:
            continue

        # Convert to string for pattern matching
        field_str = str(field_value)

        # Check if pattern matches
        if re.search(pattern, field_str):
            return {
                "dimension": dimension,
                "value": canonical
            }

    return None
