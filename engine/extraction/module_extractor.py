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
