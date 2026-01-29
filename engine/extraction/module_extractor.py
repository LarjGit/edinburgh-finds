"""
Module Extraction Engine

Applies module triggers and extracts module fields using deterministic extractors.
Phase 2 extraction: Runs after lens mapping.

Architecture: Per architecture.md Section 7.5
- Deterministic extractors execute first
- Source-aware applicability filtering
- Normalizer pipeline applied after extraction
"""
from typing import Dict, List, Any

from engine.lenses.extractors.regex_capture import extract_regex_capture
from engine.lenses.extractors.numeric_parser import extract_numeric
from engine.lenses.extractors.normalizers import apply_normalizers


def evaluate_module_triggers(triggers: List[Dict[str, Any]], entity: Dict[str, Any]) -> List[str]:
    """
    Determine which modules to attach based on facet values and conditions.

    Per architecture.md 7.2: Module triggers fire when:
    - Entity has required facet value
    - All conditions match (entity_class, etc.)

    Args:
        triggers: List of module trigger definitions from lens
        entity: Entity dict with entity_class and canonical_values_by_facet

    Returns:
        List of module names to attach

    Example:
        >>> triggers = [{"when": {"facet": "activity", "value": "padel"},
        ...              "add_modules": ["sports_facility"],
        ...              "conditions": [{"entity_class": "place"}]}]
        >>> entity = {"entity_class": "place",
        ...           "canonical_values_by_facet": {"activity": ["padel"]}}
        >>> evaluate_module_triggers(triggers, entity)
        ["sports_facility"]
    """
    modules = []
    entity_class = entity.get("entity_class")
    canonical_values_by_facet = entity.get("canonical_values_by_facet", {})

    for trigger in triggers:
        # Check when clause
        when = trigger.get("when", {})
        facet = when.get("facet")
        value = when.get("value")

        if not facet or not value:
            continue

        # Check if entity has required value in facet
        facet_values = canonical_values_by_facet.get(facet, [])
        if value not in facet_values:
            continue

        # Check conditions
        conditions = trigger.get("conditions", [])
        conditions_met = True

        for condition in conditions:
            if "entity_class" in condition:
                if entity_class != condition["entity_class"]:
                    conditions_met = False
                    break

        if not conditions_met:
            continue

        # Add modules
        add_modules = trigger.get("add_modules", [])
        modules.extend(add_modules)

    # Deduplicate
    return list(set(modules))


def execute_field_rules(
    rules: List[Dict[str, Any]],
    entity: Dict[str, Any],
    source: str
) -> Dict[str, Any]:
    """
    Execute field extraction rules with applicability filtering.

    Per architecture.md 7.5:
    - Deterministic extractors only (Phase 2 scope)
    - Source-aware applicability filtering
    - Normalizers applied after extraction

    Args:
        rules: List of field rule definitions from module config
        entity: Entity dict with raw field values
        source: Data source name (e.g., "serper", "google_places")

    Returns:
        Dict with extracted module fields (nested structure from target_path)

    Example:
        >>> rules = [{"target_path": "courts.total", "extractor": "regex_capture",
        ...           "pattern": r"(\\d+)\\s*courts", "source_fields": ["description"]}]
        >>> entity = {"description": "5 courts available"}
        >>> execute_field_rules(rules, entity, source="serper")
        {"courts": {"total": 5}}
    """
    result = {}

    for rule in rules:
        # Check applicability
        applicability = rule.get("applicability", {})

        # Filter by source
        allowed_sources = applicability.get("source", [])
        if allowed_sources and source not in allowed_sources:
            continue

        # Filter by entity_class
        allowed_classes = applicability.get("entity_class", [])
        if allowed_classes and entity.get("entity_class") not in allowed_classes:
            continue

        # Execute extractor
        extractor = rule.get("extractor")
        source_fields = rule.get("source_fields", [])

        extracted_value = None

        if extractor == "regex_capture":
            pattern = rule.get("pattern")

            # Search across source fields
            for field_name in source_fields:
                field_value = entity.get(field_name)
                if field_value:
                    extracted_value = extract_regex_capture(str(field_value), pattern)
                    if extracted_value:
                        break

        elif extractor == "numeric_parser":
            # Search across source fields
            for field_name in source_fields:
                field_value = entity.get(field_name)
                if field_value:
                    extracted_value = extract_numeric(str(field_value))
                    if extracted_value:
                        break

        # Apply normalizers
        if extracted_value is not None:
            normalizers = rule.get("normalizers", [])
            if normalizers:
                extracted_value = apply_normalizers(extracted_value, normalizers)

        # Set value at target_path
        if extracted_value is not None:
            target_path = rule.get("target_path")
            _set_nested_value(result, target_path, extracted_value)

    return result


def _set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set value at nested path in dict.

    Args:
        data: Target dictionary
        path: Dot-separated path (e.g., "courts.total")
        value: Value to set

    Example:
        >>> data = {}
        >>> _set_nested_value(data, "courts.total", 5)
        >>> data
        {"courts": {"total": 5}}
    """
    keys = path.split(".")
    current = data

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
