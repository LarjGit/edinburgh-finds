"""Test entity_classifier refactor (generic fields, TDD)."""

import pytest
import inspect
from engine.extraction import entity_classifier
from engine.extraction.entity_classifier import extract_roles


def test_extract_roles_provides_equipment():
    """Test that provides_equipment flag triggers provides_facility role."""
    raw_data = {
        "provides_equipment": True
    }

    roles = extract_roles(raw_data)

    assert "provides_facility" in roles


def test_extract_roles_equipment_count():
    """Test that equipment_count > 0 triggers provides_facility role."""
    raw_data = {
        "equipment_count": 4  # 4 tennis courts or 4 tasting rooms
    }

    roles = extract_roles(raw_data)

    assert "provides_facility" in roles


def test_extract_roles_no_equipment_no_facility():
    """Test that no equipment means no provides_facility role."""
    raw_data = {
        "membership_required": True
        # No equipment fields
    }

    roles = extract_roles(raw_data)

    assert "provides_facility" not in roles
    assert "membership_org" in roles


def test_extract_roles_provides_instruction():
    """Test provides_instruction role (already generic)."""
    raw_data = {
        "provides_instruction": True
    }

    roles = extract_roles(raw_data)

    assert "provides_instruction" in roles


def test_extract_roles_is_members_only():
    """Test is_members_only alternative membership indicator."""
    raw_data = {
        "is_members_only": True
    }

    roles = extract_roles(raw_data)

    assert "membership_org" in roles


def test_classifier_contains_no_domain_literals():
    """
    Classifier must not contain domain-specific terms (engine purity).

    Per system-vision.md Invariant 1: Engine is vertical-agnostic.
    All domain semantics belong in lens contracts.
    """
    # Get classifier source code
    source = inspect.getsource(entity_classifier)
    source_lower = source.lower()

    # Forbidden domain terms
    forbidden_terms = [
        "padel",
        "tennis",
        "wine",
        "restaurant",
        "league",
        "club",
        "retail",
        "shop",
        "business",
        "chain"
    ]

    violations = []
    for term in forbidden_terms:
        if term in source_lower:
            violations.append(term)

    assert len(violations) == 0, \
        f"Classifier contains forbidden domain terms: {violations}. " \
        f"Domain logic must live in lens contracts only."
