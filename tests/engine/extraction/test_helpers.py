"""
Test-only convenience functions for extraction testing.

This module contains helper functions that combine multiple extraction phases
for testing and utility scripts. These functions should NOT be used in production
code - the production pipeline uses a proper Phase 1/Phase 2 split for better
separation of concerns.

PRODUCTION PATH (use this instead):
    Phase 1: extractor.extract(raw_data, ctx=ctx)
             → Returns ONLY schema primitives (entity_name, lat/lng, phone, etc.)

    Phase 2: lens_integration.apply_lens_contract(primitives, lens_contract, source, entity_class)
             → Adds canonical dimensions (canonical_activities, etc.) and modules

    See: engine/orchestration/extraction_integration.py lines 161-196 for production implementation
"""

from typing import Dict, Any, List

from engine.lenses.mapping_engine import execute_mapping_rules, stabilize_canonical_dimensions
from engine.extraction.entity_classifier import resolve_entity_class, get_engine_modules
from engine.extraction.module_extractor import execute_field_rules


def dedupe_preserve_order(values: List[str]) -> List[str]:
    """
    Deduplicate list while preserving insertion order.

    Used to avoid repeated module trigger evaluation and ensure
    deterministic output in the extraction pipeline.

    Args:
        values: List of strings (potentially with duplicates)

    Returns:
        List with duplicates removed, preserving first occurrence order

    Example:
        >>> dedupe_preserve_order(["padel", "tennis", "padel"])
        ["padel", "tennis"]
    """
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def extract_with_lens_for_testing(raw_data: Dict[str, Any], lens_contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    ⚠️ TEST-ONLY CONVENIENCE FUNCTION - For testing and utility scripts only.

    DO NOT USE IN PRODUCTION CODE.

    This function combines Phase 1 (primitive extraction) + Phase 2 (lens application)
    into a single monolithic call. The production pipeline uses a two-phase split for
    better separation of concerns and testability.

    PRODUCTION PATH (use this instead):
        Phase 1: extractor.extract(raw_data, ctx=ctx)
                 → Returns ONLY schema primitives (entity_name, lat/lng, phone, etc.)

        Phase 2: lens_integration.apply_lens_contract(primitives, lens_contract, source, entity_class)
                 → Adds canonical dimensions (canonical_activities, etc.) and modules

        See: engine/orchestration/extraction_integration.py lines 161-196 for production implementation

    VALID USE CASES FOR THIS FUNCTION:
        ✅ Quick testing of lens configurations
        ✅ Utility scripts (run_lens_aware_extraction.py, validate_wine_lens.py)
        ✅ Integration tests (test_lens_integration_validation.py)
        ❌ Production orchestration pipeline (uses Phase 1/Phase 2 split)

    LensContract boundary: Engine receives lens_contract (plain dict), NEVER imports from lenses/
    Application bootstrap loads lens and injects LensContract into engine.

    This function implements the complete extraction pipeline:
    1. Extract raw categories from source
    2. Map to canonical values using LensContract mapping rules
    3. Dedupe canonical_values to avoid repeated trigger evaluation
    4. Distribute canonical values to dimensions by facet
    5. Resolve entity_class (deterministic, engine rules)
    6. Compute required modules (engine + lens triggers)
    7. Extract module attributes
    8. Build modules JSONB with namespacing
    9. Return structured entity with deduplicated text[] arrays

    Args:
        raw_data: Raw entity data from source (dict with categories, attributes, etc.)
        lens_contract: Plain dict (LensContract) containing:
            - facets: Dict mapping facet keys to {dimension_source, ...}
            - values: List of value dicts with {key, facet, display_name, ...}
            - mapping_rules: List of {pattern, canonical, confidence}
            - modules: Dict of module definitions
            - module_triggers: List of {when: {facet, value}, add_modules, conditions}

    Returns:
        Dict with extracted entity data:
            - entity_class: Single entity_class value
            - canonical_activities: List[str] (Postgres text[] array)
            - canonical_roles: List[str] (Postgres text[] array)
            - canonical_place_types: List[str] (Postgres text[] array)
            - canonical_access: List[str] (Postgres text[] array)
            - modules: Dict with namespaced JSONB structure {module_key: {fields}}

    Example:
        >>> lens_contract = {
        ...     "facets": {"activity": {"dimension_source": "canonical_activities"}},
        ...     "values": [{"key": "padel", "facet": "activity", "display_name": "Padel"}],
        ...     "mapping_rules": [{"pattern": r"(?i)\\bpadel\\b", "canonical": "padel", "confidence": 1.0}],
        ...     "modules": {},
        ...     "module_triggers": []
        ... }
        >>> extract_with_lens_for_testing({"categories": ["Padel Court"]}, lens_contract)
        {
            'entity_class': 'place',
            'canonical_activities': ['padel'],
            'canonical_roles': [],
            'canonical_place_types': ['sports_centre'],
            'canonical_access': [],
            'modules': {'core': {...}, 'location': {...}}
        }
    """
    # Step 1: Extract raw categories from source
    raw_categories = raw_data.get("categories", [])
    if not isinstance(raw_categories, list):
        raw_categories = [raw_categories] if raw_categories else []

    # Step 2: Map to canonical values using NEW mapping engine
    mapping_rules = lens_contract.get("mapping_rules", [])

    # Build entity dict for mapping engine
    entity_for_mapping = {
        "entity_name": raw_data.get("entity_name", ""),
        "description": raw_data.get("description", ""),
        "raw_categories": raw_categories
    }

    # Build enhanced rules with dimension and source_fields
    facets_config = lens_contract.get("facets", {})
    values_list = lens_contract.get("values", [])
    values_by_key = {value["key"]: value for value in values_list if "key" in value}

    enhanced_rules = []
    for rule in mapping_rules:
        canonical = rule.get("canonical")
        value_obj = values_by_key.get(canonical)

        if not value_obj:
            continue

        facet = value_obj.get("facet")
        facet_def = facets_config.get(facet)

        if not facet_def:
            continue

        dimension = facet_def.get("dimension_source")

        enhanced_rule = dict(rule)
        enhanced_rule["dimension"] = dimension
        if "source_fields" not in enhanced_rule:
            enhanced_rule["source_fields"] = ["entity_name", "description", "raw_categories"]

        enhanced_rules.append(enhanced_rule)

    # Execute mapping rules
    dimensions = execute_mapping_rules(enhanced_rules, entity_for_mapping)

    # Stabilize dimensions
    dimensions = stabilize_canonical_dimensions(dimensions)

    # Build canonical_values_by_facet for module trigger matching
    # Build facet_to_dimension lookup
    facet_to_dimension = {}
    for facet_key, facet_data in facets_config.items():
        dimension_source = facet_data.get("dimension_source")
        if dimension_source:
            facet_to_dimension[facet_key] = dimension_source

    # Initialize canonical_values_by_facet with EMPTY LISTS
    canonical_values_by_facet = {facet_key: [] for facet_key in facets_config.keys()}

    # Populate canonical_values_by_facet from dimensions
    for facet_key, dimension_source in facet_to_dimension.items():
        if dimension_source in dimensions:
            canonical_values_by_facet[facet_key] = dimensions[dimension_source][:]

    # Step 4: Resolve entity_class (deterministic, engine rules - no lens dependency)
    classification_result = resolve_entity_class(raw_data)
    entity_class = classification_result["entity_class"]

    # Merge classification results into dimensions
    # The classifier returns canonical_roles, canonical_activities, canonical_place_types
    # We need to merge these with what we extracted from lens mapping
    for dim_name in ["canonical_activities", "canonical_roles", "canonical_place_types"]:
        classifier_values = classification_result.get(dim_name, [])
        if classifier_values:
            # Merge and dedupe
            combined = dimensions[dim_name] + classifier_values
            dimensions[dim_name] = dedupe_preserve_order(combined)

            # Also update canonical_values_by_facet for trigger matching
            # Need to map dimension name back to facet key
            for facet_key, dim_source in facet_to_dimension.items():
                if dim_source == dim_name:
                    combined_facet = canonical_values_by_facet.get(facet_key, []) + classifier_values
                    canonical_values_by_facet[facet_key] = dedupe_preserve_order(combined_facet)

    # Step 5: Compute required modules
    # Get engine modules (entity_class-based, from engine config)
    engine_modules = get_engine_modules(entity_class)
    required_modules = set(engine_modules)

    # Get lens modules from lens_contract["module_triggers"]
    module_triggers = lens_contract.get("module_triggers", [])
    for trigger in module_triggers:
        # Check if trigger matches using canonical_values_by_facet
        when_clause = trigger.get("when", {})
        facet = when_clause.get("facet")
        value = when_clause.get("value")

        if not facet or not value:
            continue

        # Check if entity has this value in the specified facet
        facet_values = canonical_values_by_facet.get(facet, [])
        if value not in facet_values:
            continue

        # Check entity_class conditions
        conditions = trigger.get("conditions", [])
        conditions_met = True
        for condition in conditions:
            if "entity_class" in condition:
                if condition["entity_class"] != entity_class:
                    conditions_met = False
                    break

        if not conditions_met:
            continue

        # Add triggered modules to required_modules
        add_modules = trigger.get("add_modules", [])
        required_modules.update(add_modules)

    # Step 6: Extract module attributes (using lens_contract["modules"] definitions)
    # Step 7: Build modules JSONB with namespacing
    modules_data = {}
    modules_config = lens_contract.get("modules", {})

    for module_name in required_modules:
        module_def = modules_config.get(module_name, {})

        # Get field rules for module
        field_rules = module_def.get("field_rules", [])

        # Execute field rules to extract module data
        # Pass source from raw_data metadata
        source = raw_data.get("source", "unknown")

        # Build entity dict for field extraction
        entity_for_extraction = dict(raw_data)
        entity_for_extraction["entity_class"] = entity_class

        module_fields = execute_field_rules(field_rules, entity_for_extraction, source)

        # Store module data
        modules_data[module_name] = module_fields

    # Step 8: Return structured entity with deduplicated text[] arrays for dimensions
    return {
        "entity_class": entity_class,
        "canonical_activities": dimensions["canonical_activities"],
        "canonical_roles": dimensions["canonical_roles"],
        "canonical_place_types": dimensions["canonical_place_types"],
        "canonical_access": dimensions["canonical_access"],
        "modules": modules_data
    }
