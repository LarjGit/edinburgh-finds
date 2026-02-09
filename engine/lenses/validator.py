"""
Lens configuration validator.

Enforces all 7 validation gates required by docs/target-architecture.md 6.7:

GATE 1: Schema validation - Required top-level sections must be present
GATE 2: Canonical reference integrity - All references must be valid
GATE 3: Connector reference validation - Connectors must exist in registry
GATE 4: Identifier uniqueness - Keys must be unique
GATE 5: Regex compilation validation - Patterns must be valid regex
GATE 6: Smoke coverage validation - Every facet must have values
GATE 7: Fail-fast enforcement - Errors abort immediately at load time

All validation is fail-fast: configuration errors raise ValidationError immediately
at lens load time (not at runtime).
"""

import re
from typing import Any, Dict, List, Set


class ValidationError(Exception):
    """Raised when lens configuration violates architectural contracts."""
    pass


# GATE 1: Required top-level sections in lens.yaml
REQUIRED_LENS_SECTIONS: Set[str] = {
    "schema",
    "facets",
    "values",
    "mapping_rules",
}

# GATE 2: Engine supports exactly 4 canonical dimension columns (Postgres text[] arrays)
ALLOWED_DIMENSION_SOURCES: Set[str] = {
    "canonical_activities",
    "canonical_roles",
    "canonical_place_types",
    "canonical_access"
}

# GATE 2: Valid entity_class values (from entity_classifier.py)
VALID_ENTITY_CLASSES: Set[str] = {
    "place",
    "person",
    "organization",
    "event",
    "thing"
}


def validate_lens_config(config: Dict[str, Any]) -> None:
    """
    Validate lens configuration against all 7 architectural validation gates.

    Implements docs/target-architecture.md 6.7 validation gates:
        GATE 1: Schema validation
        GATE 2: Canonical reference integrity
        GATE 3: Connector reference validation
        GATE 4: Identifier uniqueness
        GATE 5: Regex compilation validation
        GATE 6: Smoke coverage validation
        GATE 7: Fail-fast enforcement (implicit in all gates)

    Args:
        config: Parsed lens.yaml configuration dictionary

    Raises:
        ValidationError: If any gate fails (fail-fast)
    """
    # GATE 1: Schema validation - Required sections
    _validate_required_sections(config)

    # Extract sections (guaranteed to exist after gate 1)
    facets = config.get("facets", {})
    values = config.get("values", [])
    mapping_rules = config.get("mapping_rules", [])
    modules = config.get("modules", {})
    module_triggers = config.get("module_triggers", [])
    derived_groupings = config.get("derived_groupings", [])
    connector_rules = config.get("connector_rules", {})

    # GATE 2: Canonical reference integrity
    _validate_dimension_sources(facets)
    _validate_value_facet_references(values, facets)
    _validate_mapping_rule_references(mapping_rules, values)
    _validate_module_trigger_references(module_triggers, facets, modules)
    _validate_derived_grouping_references(derived_groupings)

    # GATE 3: Connector reference validation
    _validate_connector_references(connector_rules)

    # GATE 4: Identifier uniqueness
    _validate_unique_value_keys(values)
    # Facet key uniqueness implicitly enforced by dict structure

    # GATE 5: Regex compilation validation
    _validate_regex_patterns(mapping_rules)

    # GATE 6: Smoke coverage validation
    _validate_facet_coverage(facets, values)

    # GATE 7: Fail-fast enforcement
    # Implemented by raising ValidationError immediately on any violation above


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


def _validate_required_sections(config: Dict[str, Any]) -> None:
    """
    GATE 1: Schema validation - Validate required top-level sections exist.

    Args:
        config: Parsed lens.yaml configuration dictionary

    Raises:
        ValidationError: If any required section is missing
    """
    for required_section in REQUIRED_LENS_SECTIONS:
        if required_section not in config:
            raise ValidationError(
                f"Missing required section: {required_section}"
            )


def _validate_module_trigger_references(
    module_triggers: List[Dict[str, Any]],
    facets: Dict[str, Any],
    modules: Dict[str, Any]
) -> None:
    """
    GATE 2: Canonical reference integrity - Validate module trigger references.

    Ensures:
    - module_triggers.when.facet references existing facet
    - module_triggers.add_modules references existing modules

    Args:
        module_triggers: Module triggers section of lens config
        facets: Facets section of lens config
        modules: Modules section of lens config

    Raises:
        ValidationError: If trigger references non-existent facet or module
    """
    for trigger in module_triggers:
        when = trigger.get("when", {})
        facet_ref = when.get("facet")
        add_modules = trigger.get("add_modules", [])

        # Validate facet reference
        if facet_ref and facet_ref not in facets:
            available_facets = ", ".join(sorted(facets.keys()))
            raise ValidationError(
                f"Module trigger references non-existent facet '{facet_ref}'. "
                f"Available facets: {available_facets}"
            )

        # Validate module references
        for module_name in add_modules:
            if module_name not in modules:
                available_modules = ", ".join(sorted(modules.keys())) if modules else "(none)"
                raise ValidationError(
                    f"Module trigger references non-existent module '{module_name}'. "
                    f"Available modules: {available_modules}"
                )


def _validate_derived_grouping_references(
    derived_groupings: List[Dict[str, Any]]
) -> None:
    """
    GATE 2: Canonical reference integrity - Validate derived grouping references.

    Ensures:
    - derived_groupings.rules.entity_class contains valid entity_class values

    Args:
        derived_groupings: Derived groupings section of lens config

    Raises:
        ValidationError: If grouping rule contains invalid entity_class
    """
    for grouping in derived_groupings:
        grouping_id = grouping.get("id", "(unknown)")
        rules = grouping.get("rules", [])

        for rule in rules:
            entity_class = rule.get("entity_class")

            if entity_class and entity_class not in VALID_ENTITY_CLASSES:
                allowed_list = ", ".join(sorted(VALID_ENTITY_CLASSES))
                raise ValidationError(
                    f"Derived grouping '{grouping_id}' has invalid entity_class '{entity_class}'. "
                    f"entity_class must be one of: {allowed_list}"
                )


def _validate_connector_references(connector_rules: Dict[str, Any]) -> None:
    """
    GATE 3: Connector reference validation.

    All connector names in connector_rules must exist in CONNECTOR_REGISTRY.

    Args:
        connector_rules: Connector rules section of lens config

    Raises:
        ValidationError: If connector_rules references non-existent connector
    """
    # Import here to avoid circular dependency
    from engine.orchestration.registry import CONNECTOR_REGISTRY

    for connector_name in connector_rules.keys():
        if connector_name not in CONNECTOR_REGISTRY:
            available_connectors = ", ".join(sorted(CONNECTOR_REGISTRY.keys()))
            raise ValidationError(
                f"Connector rules references non-existent connector '{connector_name}'. "
                f"Available connectors: {available_connectors}"
            )


def _validate_regex_patterns(mapping_rules: List[Dict[str, Any]]) -> None:
    """
    GATE 5: Regex compilation validation.

    All mapping_rules.pattern must be valid regex patterns.

    Args:
        mapping_rules: Mapping rules section of lens config

    Raises:
        ValidationError: If any pattern is an invalid regex
    """
    for rule in mapping_rules:
        pattern = rule.get("pattern")
        canonical = rule.get("canonical", "(unknown)")

        if not pattern:
            continue  # Skip rules without pattern

        # Attempt to compile regex
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValidationError(
                f"Invalid regex pattern in mapping rule for '{canonical}': {pattern}. "
                f"Regex error: {e}"
            )


def _validate_facet_coverage(facets: Dict[str, Any], values: List[Dict[str, Any]]) -> None:
    """
    GATE 6: Smoke coverage validation.

    Every facet must have at least one value.

    Args:
        facets: Facets section of lens config
        values: Values section of lens config

    Raises:
        ValidationError: If any facet has no values
    """
    # Build set of facets that have at least one value
    facets_with_values: Set[str] = set()
    for value in values:
        facet = value.get("facet")
        if facet:
            facets_with_values.add(facet)

    # Check that every facet has at least one value
    for facet_key in facets.keys():
        if facet_key not in facets_with_values:
            raise ValidationError(
                f"Facet '{facet_key}' has no values. "
                f"Every facet must have at least one value defined in the values section."
            )
