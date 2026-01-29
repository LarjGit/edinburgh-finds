"""Tests for module extraction engine."""
import pytest
from engine.extraction.module_extractor import evaluate_module_triggers, execute_field_rules


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


def test_execute_field_rules_extracts_using_regex_capture():
    """Should extract field using regex_capture extractor."""
    rules = [
        {
            "rule_id": "extract_padel_court_count",
            "target_path": "padel_courts.total",
            "extractor": "regex_capture",
            "pattern": r"(?i)(\d+)\s*padel\s*courts?",
            "source_fields": ["description"],
            "normalizers": ["round_integer"]
        }
    ]

    entity = {
        "description": "Premier facility with 5 padel courts",
        "source": "serper"
    }

    result = execute_field_rules(rules, entity, source="serper")

    assert result == {"padel_courts": {"total": 5}}


def test_execute_field_rules_skips_on_source_mismatch():
    """Should skip rule when source doesn't match applicability."""
    rules = [
        {
            "rule_id": "extract_court_count",
            "target_path": "courts.total",
            "extractor": "regex_capture",
            "pattern": r"(\d+)\s*courts?",
            "source_fields": ["description"],
            "applicability": {
                "source": ["google_places"]  # Only Google Places
            }
        }
    ]

    entity = {
        "description": "5 courts available",
        "source": "serper"  # Mismatch
    }

    result = execute_field_rules(rules, entity, source="serper")

    # Should not extract (source mismatch)
    assert result == {}
