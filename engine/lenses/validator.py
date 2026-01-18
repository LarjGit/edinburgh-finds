"""
Lens configuration validator.

Enforces architectural contracts between engine and lens layers:
- CONTRACT 1: Every facet.dimension_source MUST be one of 4 allowed dimensions
- CONTRACT 2: Every value.facet MUST exist in facets section
- CONTRACT 3: Every mapping_rules.canonical MUST exist in values section
- CONTRACT 4: No duplicate value.key across all values
- CONTRACT 5: No duplicate facet keys

All validation is fail-fast: configuration errors raise ValidationError immediately
at lens load time (not at runtime).
"""

from typing import Any, Dict, List, Set


class ValidationError(Exception):
    """Raised when lens configuration violates architectural contracts."""
    pass


# CONTRACT: Engine supports exactly 4 canonical dimension columns (Postgres text[] arrays)
ALLOWED_DIMENSION_SOURCES: Set[str] = {
    "canonical_activities",
    "canonical_roles",
    "canonical_place_types",
    "canonical_access"
}


def validate_lens_config(config: Dict[str, Any]) -> None:
    """
    Validate lens configuration against all architectural contracts.

    Args:
        config: Parsed lens.yaml configuration dictionary

    Raises:
        ValidationError: If any contract is violated

    Contracts validated:
        1. Every facet.dimension_source must be one of ALLOWED_DIMENSION_SOURCES
        2. Every value.facet must exist in facets section
        3. Every mapping_rules.canonical must exist in values section
        4. No duplicate value.key across all values
        5. No duplicate facet keys (implicitly enforced by dict structure)
    """
    facets = config.get("facets", {})
    values = config.get("values", [])
    mapping_rules = config.get("mapping_rules", [])

    # CONTRACT 1: Validate dimension_source for every facet
    _validate_dimension_sources(facets)

    # CONTRACT 2: Validate value.facet references
    _validate_value_facet_references(values, facets)

    # CONTRACT 3: Validate mapping_rules.canonical references
    _validate_mapping_rule_references(mapping_rules, values)

    # CONTRACT 4: Validate no duplicate value.key
    _validate_unique_value_keys(values)

    # CONTRACT 5: No duplicate facet keys
    # Python dict inherently prevents duplicate keys, so this is structurally enforced
    # No additional validation needed


def _validate_dimension_sources(facets: Dict[str, Any]) -> None:
    """
    CONTRACT 1: Every facet.dimension_source must be one of ALLOWED_DIMENSION_SOURCES.

    Args:
        facets: Facets section of lens config

    Raises:
        ValidationError: If facet uses invalid dimension_source
    """
    for facet_key, facet_config in facets.items():
        dimension_source = facet_config.get("dimension_source")

        if not dimension_source:
            raise ValidationError(
                f"Facet '{facet_key}' missing required field 'dimension_source'"
            )

        if dimension_source not in ALLOWED_DIMENSION_SOURCES:
            allowed_list = ", ".join(sorted(ALLOWED_DIMENSION_SOURCES))
            raise ValidationError(
                f"Facet '{facet_key}' has invalid dimension_source '{dimension_source}'. "
                f"dimension_source must be one of: {allowed_list}"
            )


def _validate_value_facet_references(values: List[Dict[str, Any]], facets: Dict[str, Any]) -> None:
    """
    CONTRACT 2: Every value.facet must exist in facets section.

    Args:
        values: Values section of lens config
        facets: Facets section of lens config

    Raises:
        ValidationError: If value.facet references non-existent facet
    """
    for value in values:
        value_key = value.get("key")
        facet_ref = value.get("facet")

        if not facet_ref:
            raise ValidationError(
                f"Value '{value_key}' missing required field 'facet'"
            )

        if facet_ref not in facets:
            available_facets = ", ".join(sorted(facets.keys()))
            raise ValidationError(
                f"Value '{value_key}' references non-existent facet '{facet_ref}'. "
                f"value.facet must exist in facets section. Available facets: {available_facets}"
            )


def _validate_mapping_rule_references(mapping_rules: List[Dict[str, Any]], values: List[Dict[str, Any]]) -> None:
    """
    CONTRACT 3: Every mapping_rules.canonical must exist in values section.

    Args:
        mapping_rules: Mapping rules section of lens config
        values: Values section of lens config

    Raises:
        ValidationError: If mapping_rules.canonical references non-existent value
    """
    # Build set of valid value keys
    valid_value_keys = {value.get("key") for value in values if value.get("key")}

    for rule in mapping_rules:
        canonical = rule.get("canonical")
        raw_values = rule.get("raw", [])

        if not canonical:
            raise ValidationError(
                f"Mapping rule with raw values {raw_values} missing required field 'canonical'"
            )

        if canonical not in valid_value_keys:
            available_values = ", ".join(sorted(valid_value_keys))
            raise ValidationError(
                f"Mapping rule references non-existent value '{canonical}'. "
                f"mapping_rules.canonical must exist in values section. Available values: {available_values}"
            )


def _validate_unique_value_keys(values: List[Dict[str, Any]]) -> None:
    """
    CONTRACT 4: No duplicate value.key across all values.

    Args:
        values: Values section of lens config

    Raises:
        ValidationError: If duplicate value.key found
    """
    seen_keys: Set[str] = set()
    duplicate_keys: List[str] = []

    for value in values:
        key = value.get("key")

        if not key:
            raise ValidationError(
                f"Value missing required field 'key': {value}"
            )

        if key in seen_keys:
            duplicate_keys.append(key)
        else:
            seen_keys.add(key)

    if duplicate_keys:
        raise ValidationError(
            f"Duplicate value.key found: {', '.join(duplicate_keys)}. "
            f"Each value.key must be unique across all values."
        )
