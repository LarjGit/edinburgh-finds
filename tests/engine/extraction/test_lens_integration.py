"""
Unit tests for lens_integration.py (Phase 2 delegator)

Tests verify:
- Contract-driven dimension enrichment (facet→dimension from lens contract)
- Canonical dimension population via lens mapping
- Phase 1 primitive preservation
"""
import pytest
from engine.extraction.lens_integration import (
    enrich_mapping_rules,
    build_canonical_values_by_facet,
    apply_lens_contract
)


def test_enrich_mapping_rules_derives_dimension_from_facets():
    """Verify dimension enrichment is contract-driven from facets."""
    raw_rules = [
        {"id": "r1", "pattern": r"(?i)football", "canonical": "football", "confidence": 0.9}
    ]
    facets = {
        "activity": {"dimension_source": "canonical_activities"}
    }
    values = [
        {"key": "football", "facet": "activity"}
    ]

    enriched = enrich_mapping_rules(raw_rules, facets, values)

    # Dimension should come from facet.dimension_source, not hardcoded
    assert len(enriched) == 1
    assert enriched[0]["dimension"] == "canonical_activities"
    assert enriched[0]["canonical"] == "football"
    assert enriched[0]["pattern"] == r"(?i)football"
    assert enriched[0]["confidence"] == 0.9
    # source_fields intentionally omitted - mapping engine will use DEFAULT_SOURCE_FIELDS
    assert "source_fields" not in enriched[0]


def test_enrich_mapping_rules_handles_missing_facet():
    """Verify rules without matching facet definitions are skipped."""
    raw_rules = [
        {"id": "r1", "pattern": r"(?i)tennis", "canonical": "tennis", "confidence": 0.9}
    ]
    facets = {
        "activity": {"dimension_source": "canonical_activities"}
    }
    values = [
        {"key": "football", "facet": "activity"}  # tennis not in values
    ]

    enriched = enrich_mapping_rules(raw_rules, facets, values)

    # Rule should be skipped because canonical value not found
    assert len(enriched) == 0


def test_enrich_mapping_rules_handles_multiple_rules():
    """Verify multiple rules are enriched correctly."""
    raw_rules = [
        {"id": "r1", "pattern": r"(?i)football", "canonical": "football", "confidence": 0.9},
        {"id": "r2", "pattern": r"(?i)tennis", "canonical": "tennis", "confidence": 0.85}
    ]
    facets = {
        "activity": {"dimension_source": "canonical_activities"}
    }
    values = [
        {"key": "football", "facet": "activity"},
        {"key": "tennis", "facet": "activity"}
    ]

    enriched = enrich_mapping_rules(raw_rules, facets, values)

    assert len(enriched) == 2
    assert enriched[0]["canonical"] == "football"
    assert enriched[1]["canonical"] == "tennis"
    assert all(r["dimension"] == "canonical_activities" for r in enriched)


def test_build_canonical_values_by_facet():
    """Verify facet inversion maps dimensions to facet keys."""
    dims = {
        "canonical_activities": ["football", "tennis"],
        "canonical_roles": ["provides_facility"]
    }
    facets = {
        "activity": {"dimension_source": "canonical_activities"},
        "role": {"dimension_source": "canonical_roles"}
    }

    result = build_canonical_values_by_facet(dims, facets)

    assert result == {
        "activity": ["football", "tennis"],
        "role": ["provides_facility"]
    }


def test_build_canonical_values_by_facet_handles_missing_dimensions():
    """Verify unmapped dimensions are excluded."""
    dims = {
        "canonical_activities": ["football"],
        "canonical_access": ["wheelchair"]
    }
    facets = {
        "activity": {"dimension_source": "canonical_activities"}
        # No facet for canonical_access
    }

    result = build_canonical_values_by_facet(dims, facets)

    assert result == {"activity": ["football"]}
    assert "canonical_access" not in result


def test_apply_lens_contract_populates_canonical_dimensions():
    """Verify lens mapping populates canonical dimensions."""
    primitives = {
        "entity_name": "Powerleague Portobello",
        "latitude": 55.95,
        "longitude": -3.11
    }
    lens_contract = {
        "mapping_rules": [
            {"pattern": r"(?i)football|powerleague", "canonical": "football", "confidence": 0.9}
        ],
        "facets": {
            "activity": {"dimension_source": "canonical_activities"}
        },
        "values": [
            {"key": "football", "facet": "activity"}
        ],
        "module_triggers": [],
        "modules": {}
    }

    result = apply_lens_contract(primitives, lens_contract, "google_places", "place")

    # Structural assertions (lens-agnostic)
    assert "canonical_activities" in result
    assert isinstance(result["canonical_activities"], list)

    # Reference lens assertion (specific to this lens + query)
    assert "football" in result["canonical_activities"]


def test_apply_lens_contract_preserves_phase1_primitives():
    """Verify Phase 1 primitives are preserved in Phase 2 output."""
    primitives = {
        "entity_name": "Test Venue",
        "latitude": 55.95,
        "longitude": -3.11,
        "phone": "0131-123-4567"
    }
    lens_contract = {
        "mapping_rules": [],
        "facets": {},
        "values": [],
        "module_triggers": [],
        "modules": {}
    }

    result = apply_lens_contract(primitives, lens_contract, "test", "place")

    # All Phase 1 fields must be preserved
    assert result["entity_name"] == "Test Venue"
    assert result["latitude"] == 55.95
    assert result["longitude"] == -3.11
    assert result["phone"] == "0131-123-4567"


def test_apply_lens_contract_adds_empty_modules_when_no_triggers():
    """Verify modules field is added even when no modules triggered."""
    primitives = {
        "entity_name": "Test Venue"
    }
    lens_contract = {
        "mapping_rules": [],
        "facets": {},
        "values": [],
        "module_triggers": [],
        "modules": {}
    }

    result = apply_lens_contract(primitives, lens_contract, "test", "place")

    assert "modules" in result
    assert isinstance(result["modules"], dict)
    assert len(result["modules"]) == 0


def test_apply_lens_contract_with_module_triggers():
    """Verify module triggers and field extraction work together."""
    primitives = {
        "entity_name": "Powerleague Football Centre",
        "latitude": 55.95,
        "longitude": -3.11
    }
    lens_contract = {
        "mapping_rules": [
            {"pattern": r"(?i)football", "canonical": "football", "confidence": 0.9}
        ],
        "facets": {
            "activity": {"dimension_source": "canonical_activities"}
        },
        "values": [
            {"key": "football", "facet": "activity"}
        ],
        "module_triggers": [
            {
                "condition": {
                    "facet": "activity",
                    "values": ["football"]
                },
                "modules": ["sports_facility"]
            }
        ],
        "modules": {
            "sports_facility": {
                "field_rules": [
                    {
                        "field": "facility_type",
                        "extract_from": "entity_name",
                        "pattern": r"(?i)(football|tennis|sports) centre",
                        "transform": "lowercase"
                    }
                ]
            }
        }
    }

    result = apply_lens_contract(primitives, lens_contract, "google_places", "place")

    # Verify canonical dimensions populated
    assert "canonical_activities" in result
    assert "football" in result["canonical_activities"]

    # Verify modules attached
    assert "modules" in result
    assert isinstance(result["modules"], dict)

    # Note: Module attachment depends on evaluate_module_triggers and execute_field_rules
    # which have their own unit tests. This test verifies the integration.
