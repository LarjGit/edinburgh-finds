"""Tests for lens integration in extraction pipeline."""
import pytest
from pathlib import Path
from engine.lenses.loader import VerticalLens
from engine.extraction.base import extract_with_lens_contract


def test_extract_with_lens_contract_populates_dimensions():
    """Extraction should populate canonical dimensions using lens mapping."""
    # Load Edinburgh Finds lens
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    lens = VerticalLens(lens_path)

    # Create lens contract (plain dict for engine)
    lens_contract = {
        "facets": lens.facets,
        "values": lens.values,
        "mapping_rules": lens.mapping_rules,
        "modules": {},
        "module_triggers": []
    }

    # Raw data from source
    raw_data = {
        "categories": ["Padel Court", "Sports Centre"],
        "entity_name": "Powerleague Edinburgh",
        "latitude": 55.9533,
        "longitude": -3.1883
    }

    # Extract with lens contract
    result = extract_with_lens_contract(raw_data, lens_contract)

    # Should populate canonical_activities from mapping
    assert "canonical_activities" in result
    assert "padel" in result["canonical_activities"]

    # Should populate canonical_place_types from mapping
    assert "canonical_place_types" in result
    # NOTE: "sports_facility" mapping rule needs to be in lens.yaml
