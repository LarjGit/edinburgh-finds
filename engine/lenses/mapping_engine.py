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


def execute_mapping_rules(rules: List[Dict[str, Any]], entity: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Execute all mapping rules against entity, collect matches.

    Per architecture.md 6.4:
    - First match wins per rule (within source_fields)
    - Multiple rules may contribute to same dimension

    Args:
        rules: List of mapping rules from lens config
        entity: Entity dict with raw field values

    Returns:
        Dict mapping dimension names to lists of canonical values

    Example:
        >>> rules = [{"pattern": r"(?i)padel", "canonical": "padel",
        ...           "dimension": "canonical_activities", "source_fields": ["entity_name"]}]
        >>> entity = {"entity_name": "Padel Club"}
        >>> execute_mapping_rules(rules, entity)
        {"canonical_activities": ["padel"], "canonical_roles": [], ...}
    """
    # Initialize all dimension arrays
    dimensions = {
        "canonical_activities": [],
        "canonical_roles": [],
        "canonical_place_types": [],
        "canonical_access": []
    }

    # Execute each rule
    for rule in rules:
        match = match_rule_against_entity(rule, entity)

        if match:
            dimension = match["dimension"]
            value = match["value"]

            # Append to dimension array
            if dimension in dimensions:
                dimensions[dimension].append(value)

    return dimensions


def stabilize_canonical_dimensions(dimensions: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Deduplicate values and apply lexicographic ordering for determinism.

    Per architecture.md: System must be deterministic (Invariant 4)

    Args:
        dimensions: Dict mapping dimension names to value lists

    Returns:
        Dict with deduplicated, sorted value lists

    Example:
        >>> dims = {"canonical_activities": ["tennis", "padel", "tennis"]}
        >>> stabilize_canonical_dimensions(dims)
        {"canonical_activities": ["padel", "tennis"]}
    """
    stabilized = {}

    for dimension, values in dimensions.items():
        # Deduplicate while preserving type
        unique_values = list(set(values))

        # Sort lexicographically for determinism
        unique_values.sort()

        stabilized[dimension] = unique_values

    return stabilized


def apply_lens_mapping(entity: Dict[str, Any], ctx: Any) -> Dict[str, Any]:
    """
    Main entry point: Apply lens mapping rules to populate canonical dimensions.

    Called after Phase 1 extraction (primitives), before classification.

    Per architecture.md Section 4.2 (Extraction Boundary):
    - Phase 1: Source extractors return primitives only
    - Phase 2: Lens application populates canonical_* dimensions

    Args:
        entity: Entity dict with raw field values (from Phase 1 extractor)
        ctx: ExecutionContext with lens configuration

    Returns:
        Entity dict with canonical dimensions populated

    Example:
        >>> entity = {"entity_name": "Padel Club", "description": "..."}
        >>> ctx = ExecutionContext(lens=vertical_lens)
        >>> result = apply_lens_mapping(entity, ctx)
        >>> result["canonical_activities"]
        ["padel"]
    """
    # Get lens from context
    lens = ctx.lens

    # Get mapping rules from lens config
    mapping_rules = lens.mapping_rules

    # Build enhanced rules with dimension and source_fields
    enhanced_rules = []
    for rule in mapping_rules:
        # Determine dimension from canonical value's facet
        canonical = rule.get("canonical")

        # Find value definition in lens
        value_obj = None
        for value in lens.values:
            if value.get("key") == canonical:
                value_obj = value
                break

        if not value_obj:
            continue

        # Get facet
        facet = value_obj.get("facet")

        # Get dimension from facet definition
        facet_def = lens.facets.get(facet)
        if not facet_def:
            continue

        dimension = facet_def.get("dimension_source")

        # Add dimension and default source_fields to rule
        enhanced_rule = dict(rule)
        enhanced_rule["dimension"] = dimension
        if "source_fields" not in enhanced_rule:
            enhanced_rule["source_fields"] = ["entity_name", "description", "raw_categories"]

        enhanced_rules.append(enhanced_rule)

    # Execute mapping rules
    dimensions = execute_mapping_rules(enhanced_rules, entity)

    # Stabilize dimensions (dedupe + sort)
    dimensions = stabilize_canonical_dimensions(dimensions)

    # Merge dimensions into entity
    result = dict(entity)
    result.update(dimensions)

    return result
