"""
Lens Integration for Extraction Phase 2

This is a THIN DELEGATOR that coordinates lens application after Phase 1 extraction.
All lens and domain semantics live in the functions it calls (mapping_engine, module_extractor)
and the lens contract itself. This file contains only structural adapter logic where lens.yaml
omits required fields (e.g., source_fields defaults).

Per docs/target-architecture.md Section 4.2 (Extraction Boundary):
- Phase 1 (extractors): Primitives + raw observations ONLY
- Phase 2 (this file): Canonical dimensions + modules ONLY

Input Contract:
    - extracted_primitives: Phase 1 output (universal fields + raw observations)
    - lens_contract: Plain dict (mapping_rules, module_triggers, modules, facets, values)
    - source: Connector name (for applicability filtering)
    - entity_class: Entity classification (for module triggers)

Output Contract:
    - Dict with Phase 1 primitives preserved + Phase 2 additions:
      - canonical_activities, canonical_roles, canonical_place_types, canonical_access
      - modules (Dict with populated module fields)
"""
from typing import Dict, Any, List

from engine.lenses.mapping_engine import execute_mapping_rules, stabilize_canonical_dimensions
from engine.extraction.module_extractor import evaluate_module_triggers, execute_field_rules


def enrich_mapping_rules(
    mapping_rules: List[Dict[str, Any]],
    facets: Dict[str, Any],
    values: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Enrich mapping rules with dimension and source_fields from facet definitions.

    This is CONTRACT-DRIVEN structural adapter logic: derives dimension from
    lens_contract.facets[facet_key].dimension_source, NOT from hardcoded literals.

    Lens.yaml mapping rules contain only: id, pattern, canonical, confidence
    Engine needs: pattern, canonical, dimension, source_fields

    This function bridges the gap by looking up facet→dimension mapping from lens contract.

    Args:
        mapping_rules: Raw rules from lens.yaml (pattern, canonical, confidence)
        facets: Facet definitions from lens (key → {dimension_source, ...})
        values: Canonical value registry (key, facet, ...)

    Returns:
        Enriched rules with dimension and source_fields added
    """
    enriched_rules = []

    for rule in mapping_rules:
        canonical = rule.get("canonical")
        if not canonical:
            continue

        # Find value definition to get facet
        value_obj = next((v for v in values if v.get("key") == canonical), None)
        if not value_obj:
            continue

        facet_key = value_obj.get("facet")
        if not facet_key:
            continue

        # Get dimension from facet definition (CONTRACT-DRIVEN)
        facet_def = facets.get(facet_key)
        if not facet_def:
            continue

        dimension = facet_def.get("dimension_source")
        if not dimension:
            continue

        # Add dimension to rule (source_fields omitted - mapping engine will use defaults)
        # Per architecture.md: when source_fields is omitted, mapping engine searches
        # all available text fields (entity_name, description, raw_categories, etc.)
        enriched_rule = {
            "pattern": rule.get("pattern"),
            "canonical": canonical,
            "dimension": dimension,
            "confidence": rule.get("confidence", 1.0)
            # source_fields intentionally omitted - delegated to mapping engine default
        }
        enriched_rules.append(enriched_rule)

    return enriched_rules


def build_canonical_values_by_facet(
    canonical_dims: Dict[str, List[str]],
    facets: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Build facet-indexed canonical values for module trigger evaluation.

    CONTRACT-DRIVEN: Maps dimension arrays to facet keys by inverting the
    lens_contract.facets[facet_key].dimension_source relationship.

    Args:
        canonical_dims: Dict with canonical_activities, canonical_roles, etc.
        facets: Facet definitions (key → {dimension_source, ...})

    Returns:
        Dict mapping facet keys to canonical value lists

    Example:
        >>> dims = {"canonical_activities": ["football"]}
        >>> facets = {"activity": {"dimension_source": "canonical_activities"}}
        >>> build_canonical_values_by_facet(dims, facets)
        {"activity": ["football"]}
    """
    # Invert facet→dimension mapping to dimension→facet
    dimension_to_facet = {}
    for facet_key, facet_def in facets.items():
        dimension = facet_def.get("dimension_source")
        if dimension:
            dimension_to_facet[dimension] = facet_key

    # Map canonical dimension values to facet keys
    values_by_facet = {}
    for dimension, values in canonical_dims.items():
        facet_key = dimension_to_facet.get(dimension)
        if facet_key:
            values_by_facet[facet_key] = values

    return values_by_facet


def apply_lens_contract(
    extracted_primitives: Dict[str, Any],
    lens_contract: Dict[str, Any],
    source: str,
    entity_class: str
) -> Dict[str, Any]:
    """
    Apply lens mapping and module extraction (Phase 2).

    This is a THIN DELEGATOR that coordinates calls to existing lens functions.
    No new lens or domain semantics - all logic lives in called functions and the
    lens contract. Only structural adapter defaults where lens.yaml omits required fields.

    Args:
        extracted_primitives: Phase 1 output (universal primitives + raw observations)
        lens_contract: Compiled lens contract (mapping_rules, modules, facets, values)
        source: Connector name (e.g., "google_places")
        entity_class: Entity classification (place, person, organization, event, thing)

    Returns:
        Augmented dict with Phase 1 primitives + Phase 2 canonical dimensions + modules
    """
    # Step 1: Enrich mapping rules with dimension and source_fields (contract-driven)
    raw_rules = lens_contract.get("mapping_rules", [])
    facets = lens_contract.get("facets", {})
    values = lens_contract.get("values", [])
    enriched_rules = enrich_mapping_rules(raw_rules, facets, values)

    # Step 2: Execute mapping rules → canonical dimensions
    canonical_dims = execute_mapping_rules(enriched_rules, extracted_primitives)
    canonical_dims = stabilize_canonical_dimensions(canonical_dims)

    # Step 3: Build canonical_values_by_facet for module triggers (contract-driven)
    canonical_values_by_facet = build_canonical_values_by_facet(canonical_dims, facets)

    # Step 4: Evaluate module triggers → module list
    module_triggers = lens_contract.get("module_triggers", [])
    entity_for_triggers = {
        "entity_class": entity_class,
        "canonical_values_by_facet": canonical_values_by_facet
    }
    required_modules = evaluate_module_triggers(module_triggers, entity_for_triggers)
    print(f"[DEBUG lens_integration.py] required_modules: {required_modules}")
    print(f"[DEBUG lens_integration.py] canonical_values_by_facet: {canonical_values_by_facet}")

    # Step 5: Execute field rules for each required module
    modules_config = lens_contract.get("modules", {})
    modules_data = {}
    print(f"[DEBUG lens_integration.py] modules_config keys: {list(modules_config.keys())}")

    for module_name in required_modules:
        print(f"[DEBUG lens_integration.py] Processing module: {module_name}")
        if module_name not in modules_config:
            print(f"[DEBUG lens_integration.py] WARNING: {module_name} not in modules_config!")
            continue

        module_def = modules_config[module_name]
        field_rules = module_def.get("field_rules", [])
        print(f"[DEBUG lens_integration.py] field_rules count: {len(field_rules)}")

        if not field_rules:
            print(f"[DEBUG lens_integration.py] WARNING: No field_rules for {module_name}")
            continue

        # Execute field rules (deterministic extractors only for v1)
        # Add entity_class to extracted_primitives for applicability filtering
        entity_with_class = {**extracted_primitives, "entity_class": entity_class}
        module_fields = execute_field_rules(field_rules, entity_with_class, source)
        print(f"[DEBUG lens_integration.py] module_fields result: {module_fields}")

        # Only include module if it has populated fields
        if module_fields:
            modules_data[module_name] = module_fields
            print(f"[DEBUG lens_integration.py] Added {module_name} to modules_data")
        else:
            print(f"[DEBUG lens_integration.py] WARNING: module_fields empty for {module_name}, not adding to modules_data")

    # Step 6: Return augmented entity (Phase 1 + Phase 2)
    return {
        **extracted_primitives,  # Preserve all Phase 1 primitives
        **canonical_dims,        # Add canonical dimensions
        "modules": modules_data  # Add populated modules
    }
