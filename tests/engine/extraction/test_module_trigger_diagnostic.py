"""
Diagnostic test for LA-014: Module trigger evaluation

This test isolates the module trigger evaluation pipeline to identify
why modules aren't being populated despite correct canonical dimensions.
"""
import pytest
from pathlib import Path
from engine.extraction.module_extractor import evaluate_module_triggers
from engine.extraction.lens_integration import build_canonical_values_by_facet, apply_lens_contract
from engine.lenses.loader import VerticalLens


def test_build_canonical_values_by_facet_maps_correctly():
    """Test that canonical dimensions map to facets correctly."""
    # Setup: canonical dimensions from Phase 2
    canonical_dims = {
        "canonical_activities": ["padel"],
        "canonical_place_types": ["sports_facility"],
        "canonical_roles": [],
        "canonical_access": []
    }

    # Setup: facets from lens config
    facets = {
        "activity": {"dimension_source": "canonical_activities"},
        "place_type": {"dimension_source": "canonical_place_types"}
    }

    # Execute
    result = build_canonical_values_by_facet(canonical_dims, facets)

    # Verify
    print(f"\nDEBUG: build_canonical_values_by_facet result: {result}")
    assert "activity" in result, "activity facet should be in result"
    assert result["activity"] == ["padel"], f"activity facet should contain ['padel'], got {result.get('activity')}"
    assert "place_type" in result, "place_type facet should be in result"
    assert result["place_type"] == ["sports_facility"], f"place_type facet should contain ['sports_facility'], got {result.get('place_type')}"


def test_evaluate_module_triggers_fires_for_padel():
    """Test that module trigger fires for padel + place entity."""
    # Setup: trigger config from lens.yaml
    triggers = [
        {
            "when": {"facet": "activity", "value": "padel"},
            "add_modules": ["sports_facility"],
            "conditions": [{"entity_class": "place"}]
        }
    ]

    # Setup: entity with correct facet values
    entity = {
        "entity_class": "place",
        "canonical_values_by_facet": {
            "activity": ["padel"]
        }
    }

    # Execute
    result = evaluate_module_triggers(triggers, entity)

    # Verify
    print(f"\nDEBUG: evaluate_module_triggers result: {result}")
    assert "sports_facility" in result, f"sports_facility module should be triggered, got {result}"


def test_apply_lens_contract_full_pipeline():
    """Test full lens application pipeline with real lens config."""
    # Load real lens
    lens = VerticalLens(Path("engine/lenses/edinburgh_finds/lens.yaml"))

    # Build lens contract (same as bootstrap_lens in cli.py)
    lens_contract = {
        "mapping_rules": list(lens.mapping_rules),
        "module_triggers": list(lens.module_triggers),
        "modules": dict(lens.domain_modules),
        "facets": dict(lens.facets),
        "values": list(lens.values),
    }

    # Setup: Phase 1 primitives (minimal entity with padel indicators)
    extracted_primitives = {
        "entity_name": "Test Padel Club",
        "description": "A padel sports facility with courts",
        "raw_categories": ["sports club", "padel venue"],
        "entity_class": "place"
    }

    # Execute
    result = apply_lens_contract(
        extracted_primitives=extracted_primitives,
        lens_contract=lens_contract,
        source="test_source",
        entity_class="place"
    )

    # Debug output
    print(f"\nDEBUG: apply_lens_contract result:")
    print(f"  canonical_activities: {result.get('canonical_activities')}")
    print(f"  canonical_place_types: {result.get('canonical_place_types')}")
    print(f"  modules: {result.get('modules')}")

    # Verify Phase 2 outputs
    assert result.get("canonical_activities"), "canonical_activities should be populated"
    assert "padel" in result.get("canonical_activities", []), "padel should be in canonical_activities"

    # CRITICAL: Verify modules populated
    modules = result.get("modules", {})
    assert isinstance(modules, dict), f"modules should be dict, got {type(modules)}"

    # This is where LA-014 fails - modules should contain sports_facility
    print(f"\nDEBUG: Module keys: {list(modules.keys())}")
    if "sports_facility" in modules:
        print(f"DEBUG: sports_facility module content: {modules['sports_facility']}")
    else:
        print("DEBUG: sports_facility module NOT FOUND in modules dict")
        print(f"DEBUG: Available modules: {list(modules.keys())}")


if __name__ == "__main__":
    # Run tests individually for debugging
    print("=" * 80)
    print("TEST 1: build_canonical_values_by_facet")
    print("=" * 80)
    test_build_canonical_values_by_facet_maps_correctly()

    print("\n" + "=" * 80)
    print("TEST 2: evaluate_module_triggers")
    print("=" * 80)
    test_evaluate_module_triggers_fires_for_padel()

    print("\n" + "=" * 80)
    print("TEST 3: apply_lens_contract (full pipeline)")
    print("=" * 80)
    test_apply_lens_contract_full_pipeline()

    print("\n" + "=" * 80)
    print("ALL DIAGNOSTIC TESTS PASSED")
    print("=" * 80)
