"""Tests for module extraction engine."""
import pytest
from engine.extraction.module_extractor import evaluate_module_triggers


def test_module_trigger_attaches_module_when_facet_matches():
    """Should attach module when facet value matches trigger."""
    triggers = [
        {
            "when": {"facet": "activity", "value": "padel"},
            "add_modules": ["sports_facility"],
            "conditions": [{"entity_class": "place"}]
        }
    ]

    entity = {
        "entity_class": "place",
        "canonical_values_by_facet": {
            "activity": ["padel", "tennis"]
        }
    }

    result = evaluate_module_triggers(triggers, entity)

    assert "sports_facility" in result


def test_module_trigger_skips_when_entity_class_mismatch():
    """Should not attach module when entity_class doesn't match."""
    triggers = [
        {
            "when": {"facet": "activity", "value": "padel"},
            "add_modules": ["sports_facility"],
            "conditions": [{"entity_class": "place"}]
        }
    ]

    entity = {
        "entity_class": "organization",  # Mismatch
        "canonical_values_by_facet": {
            "activity": ["padel"]
        }
    }

    result = evaluate_module_triggers(triggers, entity)

    assert "sports_facility" not in result


def test_module_trigger_skips_when_facet_value_missing():
    """Should not attach module when required facet value missing."""
    triggers = [
        {
            "when": {"facet": "activity", "value": "padel"},
            "add_modules": ["sports_facility"],
            "conditions": []
        }
    ]

    entity = {
        "entity_class": "place",
        "canonical_values_by_facet": {
            "activity": ["tennis"]  # No "padel"
        }
    }

    result = evaluate_module_triggers(triggers, entity)

    assert "sports_facility" not in result
