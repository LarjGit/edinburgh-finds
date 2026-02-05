"""Test entity_classifier refactor (generic fields, TDD)."""

import pytest
import inspect
from engine.extraction import entity_classifier
from engine.extraction.entity_classifier import (
    extract_roles,
    has_location,
    resolve_entity_class,
)


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


# ============================================================
# CL-001 Invariant Guards
# Protect the single-classifier and canonical-schema invariants
# rather than policing specific deleted symbols.  Robust to
# renames; break if the architectural pattern is re-introduced.
# ============================================================


async def test_classification_routes_through_single_entry_point():
    """
    Invariant: every entity on the live extraction path is classified
    exactly once, via resolve_entity_class, with no alternate classifier.

    Patches resolve_entity_class at its definition site, drives a minimal
    extraction through the Phase-2 code path (lens contract present),
    and asserts exactly one classification call was made.

    Also verifies the entity_classifier module surface exports no other
    classification function beyond resolve_entity_class and its companion
    validator validate_entity_class.
    """
    from unittest.mock import patch, AsyncMock, Mock
    from pathlib import Path as _Path
    from engine.orchestration.extraction_integration import extract_entity
    from engine.orchestration.execution_context import ExecutionContext

    # --- minimal stubs to reach the Phase-2 classification call ---
    fake_record = Mock()
    fake_record.source = "sport_scotland"
    fake_record.file_path = "/fake/path.json"

    mock_db = Mock()
    mock_db.rawingestion = Mock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=fake_record)

    mock_extractor = Mock()
    mock_extractor.extract.return_value = {"entity_name": "Test Venue", "latitude": 55.9}
    mock_extractor.validate.return_value = {"entity_name": "Test Venue", "latitude": 55.9}
    mock_extractor.split_attributes.return_value = ({"entity_name": "Test Venue"}, {})

    ctx = ExecutionContext(
        lens_id="test_lens",
        lens_contract={"facets": {}, "values": [], "mapping_rules": [], "modules": {}, "module_triggers": []},
        lens_hash="test_hash",
    )

    classification_stub = {
        "entity_class": "place",
        "canonical_roles": [],
        "canonical_activities": [],
        "canonical_place_types": [],
    }

    with (
        patch("engine.extraction.entity_classifier.resolve_entity_class",
              return_value=classification_stub) as mock_classify,
        patch("engine.orchestration.extraction_integration.get_extractor_for_source",
              return_value=mock_extractor),
        patch.object(_Path, "read_text", return_value='{"entity_name": "Test Venue"}'),
        patch("engine.extraction.lens_integration.apply_lens_contract",
              return_value={"canonical_activities": [], "canonical_roles": [],
                            "canonical_place_types": [], "canonical_access": [], "modules": {}}),
    ):
        await extract_entity("fake_id", mock_db, ctx)

        # resolve_entity_class is the sole classification call on the live path
        mock_classify.assert_called_once()

    # No alternate classifier may exist on the module surface.
    # Match callable names containing "entity_class" or "classif";
    # callable() excludes the VALID_ENTITY_CLASSES constant.
    permitted = {"resolve_entity_class", "validate_entity_class"}
    found = {
        name for name in dir(entity_classifier)
        if not name.startswith("_")
        and callable(getattr(entity_classifier, name))
        and ("entity_class" in name.lower() or "classif" in name.lower())
    }
    assert found == permitted, (
        f"Unexpected classification functions: {found - permitted}. "
        f"Only resolve_entity_class (entry point) and validate_entity_class (validator) are permitted."
    )


def test_classification_uses_no_legacy_field_names():
    """
    Classification logic must reference only canonical field names.

    The superseded classify_entity() used location_lat, location_lng,
    address_full and entity_type as dict-key lookups.  If any of those
    reappear as quoted string literals in the classifier module the
    canonical-schema contract is broken.

    Checks quoted occurrences only (the pattern in .get("…") calls) so
    that coincidental local variable names are not flagged.
    """
    source = inspect.getsource(entity_classifier)

    legacy_fields = ["location_lat", "location_lng", "address_full", "entity_type"]

    violations = [
        field for field in legacy_fields
        if f'"{field}"' in source or f"'{field}'" in source
    ]

    assert len(violations) == 0, (
        f"Classifier references legacy field names as dict keys: {violations}. "
        f"Canonical equivalents: latitude, longitude, street_address/address, type"
    )


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


# ============================================================
# LA-009: Geographic Anchoring Tests
# ============================================================
# Tests for has_location() to include city/postcode as
# geographic anchoring fields (not just coordinates/address)
# ============================================================


def test_has_location_with_coordinates():
    """Test that coordinates alone trigger has_location (existing behavior)."""
    raw_data = {
        "latitude": 55.9533,
        "longitude": -3.1883,
    }

    assert has_location(raw_data) is True


def test_has_location_with_street_address():
    """Test that street_address alone triggers has_location (existing behavior)."""
    raw_data = {
        "street_address": "123 Main Street",
    }

    assert has_location(raw_data) is True


def test_has_location_with_city_only():
    """
    Test that city alone triggers has_location (LA-009 fix).

    Serper often provides city (e.g., "Stevenston") without coordinates.
    City is a geographic anchoring field that indicates a physical place.
    """
    raw_data = {
        "city": "Stevenston",
    }

    assert has_location(raw_data) is True


def test_has_location_with_postcode_only():
    """
    Test that postcode alone triggers has_location (LA-009 fix).

    Postcode is a geographic anchoring field that indicates a physical place.
    """
    raw_data = {
        "postcode": "KA20 3LR",
    }

    assert has_location(raw_data) is True


def test_has_location_with_no_geographic_fields():
    """Test that entities without any geographic fields return False."""
    raw_data = {
        "entity_name": "Some Organization",
        "website": "https://example.com",
    }

    assert has_location(raw_data) is False


def test_resolve_entity_class_serper_with_city():
    """
    Integration test: Serper entity with city but no coordinates → place (LA-009).

    This is the real-world scenario from LA-008d validation test:
    - Serper provides: title="West of Scotland Padel | Stevenston"
    - LLM extracts: city="Stevenston", but NO coordinates
    - Expected: entity_class="place" (not "thing")
    """
    raw_data = {
        "entity_name": "West of Scotland Padel",
        "city": "Stevenston",
        # NO coordinates
        # NO street_address
    }

    result = resolve_entity_class(raw_data)

    assert result["entity_class"] == "place", \
        "Entities with city should be classified as 'place' even without coordinates"


def test_resolve_entity_class_priority_order_not_affected():
    """
    Test that adding city/postcode to has_location doesn't break priority order.

    Priority order (classification_rules.md):
    1. Time-bounded → event (HIGHEST)
    2. Physical location → place
    3. Organization → organization
    4. Person → person
    5. Fallback → thing

    An event with a city should still be classified as event, not place.
    """
    raw_data = {
        "entity_name": "Annual Tournament",
        "city": "Edinburgh",
        "start_date": "2026-06-01",
        "end_date": "2026-06-02",
    }

    result = resolve_entity_class(raw_data)

    assert result["entity_class"] == "event", \
        "Time-bounded entities should be classified as 'event' even if they have city"
