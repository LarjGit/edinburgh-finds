"""Tests for Edinburgh Finds lens configuration."""
import pytest
from pathlib import Path
from engine.lenses.loader import VerticalLens, LensConfigError


def test_edinburgh_finds_lens_loads_without_errors():
    """Lens configuration should load and validate successfully."""
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")

    # Should not raise LensConfigError
    lens = VerticalLens(lens_path)

    # Should have basic structure
    assert lens.facets is not None
    assert lens.values is not None
    assert lens.mapping_rules is not None


def test_lens_has_padel_mapping_rule():
    """Lens should have mapping rule for 'padel' keyword."""
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    lens = VerticalLens(lens_path)

    # Find padel mapping rule
    padel_rules = [
        rule for rule in lens.mapping_rules
        if rule.get("canonical") == "padel"
    ]

    assert len(padel_rules) > 0, "Should have at least one padel mapping rule"

    # Verify rule structure
    rule = padel_rules[0]
    assert "pattern" in rule
    assert "canonical" in rule
    assert rule["canonical"] == "padel"


def test_lens_has_sports_facility_module():
    """Lens should define sports_facility module with field rules."""
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    lens = VerticalLens(lens_path)

    # Should have modules
    assert "modules" in lens.config
    assert "sports_facility" in lens.config["modules"]

    # Module should have field rules
    module = lens.config["modules"]["sports_facility"]
    assert "field_rules" in module
    assert len(module["field_rules"]) > 0


def test_lens_has_sports_facility_trigger():
    """Lens should have trigger for sports_facility module."""
    lens_path = Path("engine/lenses/edinburgh_finds/lens.yaml")
    lens = VerticalLens(lens_path)

    # Find sports_facility trigger
    triggers = [
        t for t in lens.module_triggers
        if "sports_facility" in t.get("add_modules", [])
    ]

    assert len(triggers) > 0, "Should have sports_facility trigger"
