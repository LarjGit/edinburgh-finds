"""Unit test for module extraction via lens integration (LA-008)."""
import pytest
from pathlib import Path
from engine.extraction.lens_integration import apply_lens_contract
from engine.lenses.loader import VerticalLens


def test_module_extraction_for_padel_entity():
    """Test that modules field is populated for padel entity with West of Scotland data."""
    # Load lens contract (same way as orchestrator CLI does)
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    vertical_lens = VerticalLens(lens_path)
    lens_contract = {
        "mapping_rules": list(vertical_lens.mapping_rules),
        "module_triggers": list(vertical_lens.module_triggers),
        "modules": dict(vertical_lens.domain_modules),
        "facets": dict(vertical_lens.facets),
        "values": list(vertical_lens.values)
    }

    # Simulated Phase 1 extraction output (primitives only)
    extracted_primitives = {
        "entity_name": "West of Scotland Padel",
        "entity_class": "place",
        "summary": "Padel court venue in Stevenston with 3 fully covered, heated courts available for year-round play with membership options.",
        "description": "West of Scotland Padel Club offers premium padel facilities",
        "source": "serper"
    }

    # Apply lens contract (Phase 2)
    enriched = apply_lens_contract(
        extracted_primitives=extracted_primitives,
        lens_contract=lens_contract,
        source="serper",
        entity_class="place"
    )

    # Assertions
    assert "canonical_activities" in enriched
    assert "padel" in enriched["canonical_activities"], (
        f"Expected 'padel' in canonical_activities, got: {enriched['canonical_activities']}"
    )

    assert "modules" in enriched
    assert len(enriched["modules"]) > 0, (
        f"Expected modules to be populated, got: {enriched['modules']}"
    )

    assert "sports_facility" in enriched["modules"], (
        f"Expected 'sports_facility' module, got modules: {list(enriched['modules'].keys())}"
    )

    assert "padel_courts" in enriched["modules"]["sports_facility"], (
        f"Expected 'padel_courts' field, got: {list(enriched['modules']['sports_facility'].keys())}"
    )

    assert enriched["modules"]["sports_facility"]["padel_courts"]["total"] == 3, (
        f"Expected 3 courts, got: {enriched['modules']['sports_facility']['padel_courts']['total']}"
    )


def test_module_extraction_for_overture_entity():
    """Test Overture category evidence maps place type and populates module fields."""
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    vertical_lens = VerticalLens(lens_path)
    lens_contract = {
        "mapping_rules": list(vertical_lens.mapping_rules),
        "module_triggers": list(vertical_lens.module_triggers),
        "modules": dict(vertical_lens.domain_modules),
        "facets": dict(vertical_lens.facets),
        "values": list(vertical_lens.values),
    }

    extracted_primitives = {
        "entity_name": "Meadowbank",
        "entity_class": "place",
        "raw_categories": ["sports_centre"],
        "source": "overture_local",
    }

    enriched = apply_lens_contract(
        extracted_primitives=extracted_primitives,
        lens_contract=lens_contract,
        source="overture_local",
        entity_class="place",
    )

    assert "sports_facility" in enriched["canonical_place_types"], (
        "Expected Overture category token to map into canonical_place_types"
    )
    assert "sports_facility" in enriched["modules"], (
        "Expected sports_facility module to be triggered from place_type mapping"
    )
    assert enriched["modules"]["sports_facility"]["source_signals"]["primary_category"] == "sports_centre", (
        "Expected at least one deterministic module field populated from raw_categories"
    )
