"""
End-to-end validation tests for complete pipeline (Query → Entity DB).

Per system-vision.md Section 6.3: "One Perfect Entity" validation requirement.

Tests prove that the complete 11-stage pipeline (architecture.md 4.1) works:
1. Input
2. Lens Resolution and Validation
3. Planning
4. Connector Execution
5. Raw Ingestion Persistence
6. Source Extraction
7. Lens Application (mapping rules + modules)
8. Classification
9. Cross-Source Deduplication Grouping
10. Deterministic Merge
11. Finalization and Persistence

Validates that canonical dimensions and modules flow end-to-end through
orchestration to final Entity persistence in database.
"""

import pytest
from prisma import Prisma
from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.orchestration.cli import bootstrap_lens


@pytest.mark.slow
@pytest.mark.asyncio
async def test_one_perfect_entity_end_to_end_validation():
    """
    End-to-end validation: Query → Orchestration → Extraction → Lens → Entity DB.

    Per system-vision.md Section 6.3: "One Perfect Entity" validation requirement.
    Per docs/target-architecture.md Section 4.1: Complete 11-stage pipeline validation.

    Validates:
    1. Orchestration executes with explicit lens resolution (--lens edinburgh_finds)
    2. Entity persists to database with generated slug
    3. canonical_activities array is populated (non-empty)
    4. canonical_place_types array is populated (non-empty)
    5. modules field contains at least one module entry
    6. Entity data is retrievable and correct

    This is THE critical proof that the architecture works end-to-end.
    If this test passes, we have "at least one real-world entity" with
    "non-empty canonical dimensions" and "at least one module field populated"
    in the entity store (system-vision.md 6.3 requirement).
    """
    # Bootstrap lens with explicit resolution (required for validation entity)
    ctx = bootstrap_lens("edinburgh_finds")

    # Connect to database
    db = Prisma()
    await db.connect()

    try:
        # Clean test data before run (idempotent cleanup)
        await db.entity.delete_many(
            where={
                "OR": [
                    {"entity_name": {"contains": "West of Scotland Padel"}},
                    {"entity_name": {"contains": "west of scotland padel"}},
                ]
            }
        )

        # Create orchestration request with persistence enabled
        # Use RESOLVE_ONE to limit results for faster validation
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="west of scotland padel glasgow",
            persist=True,  # CRITICAL: Enable database persistence
        )

        # Execute complete orchestration pipeline
        report = await orchestrate(request, ctx=ctx)

        # Debug: Print report to understand what happened
        print("\n" + "=" * 80)
        print("ORCHESTRATION REPORT")
        print("=" * 80)
        print(f"Query: {report['query']}")
        print(f"Candidates Found: {report['candidates_found']}")
        print(f"Accepted Entities: {report['accepted_entities']}")
        print(f"Connectors: {list(report['connectors'].keys())}")
        print(f"Errors: {report.get('errors', [])}")
        if report.get('warnings'):
            print(f"Warnings: {report['warnings']}")
        print("=" * 80)

        # Verify orchestration succeeded
        assert report["candidates_found"] > 0, (
            "Orchestration should find candidates for validation entity"
        )

        # Verify persistence succeeded
        assert "persisted_count" in report, "Report should include persistence metrics"
        assert report["persisted_count"] > 0, (
            "At least one entity should be persisted to database"
        )

        # Query database to retrieve persisted entity
        # Search by name (case-insensitive) to find West of Scotland Padel entity
        entities = await db.entity.find_many(
            where={
                "OR": [
                    {"entity_name": {"contains": "West of Scotland Padel"}},
                    {"entity_name": {"contains": "west of scotland padel"}},
                ]
            }
        )

        assert len(entities) > 0, (
            "At least one West of Scotland Padel entity should exist in database after orchestration"
        )

        # Get first entity for validation (should be the validation entity)
        entity = entities[0]

        # === CRITICAL VALIDATION: "One Perfect Entity" Requirements ===

        # 1. Entity basics
        assert entity.entity_name, "entity_name should be populated"
        assert entity.entity_class, "entity_class should be populated"
        assert entity.slug, "slug should be generated"

        # 2. Canonical dimensions populated (Stage 7: Lens Application)
        # Per system-vision.md 6.3: "non-empty canonical dimensions"
        assert entity.canonical_activities is not None, (
            "canonical_activities should be populated by lens application"
        )
        assert len(entity.canonical_activities) > 0, (
            f"canonical_activities should contain at least one value (got: {entity.canonical_activities}). "
            "This proves Stage 7 (Lens Application) mapping rules executed."
        )

        assert entity.canonical_place_types is not None, (
            "canonical_place_types should be populated by lens application"
        )
        assert len(entity.canonical_place_types) > 0, (
            f"canonical_place_types should contain at least one value (got: {entity.canonical_place_types}). "
            "This proves Stage 7 (Lens Application) mapping rules executed."
        )

        # Debug: Print entity data for inspection
        print("\n" + "=" * 80)
        print("ENTITY DEBUG INFO")
        print("=" * 80)
        print(f"entity_name: {entity.entity_name}")
        print(f"entity_class: {entity.entity_class}")
        print(f"summary: {entity.summary}")
        print(f"canonical_activities: {entity.canonical_activities}")
        print(f"canonical_place_types: {entity.canonical_place_types}")
        print(f"modules: {entity.modules}")
        print("=" * 80)

        # 3. Modules field populated (Stage 7: Module Extraction)
        # Per system-vision.md 6.3: "at least one module field populated"
        assert entity.modules is not None, (
            "modules field should be populated"
        )
        assert isinstance(entity.modules, dict), (
            "modules should be a JSON object"
        )
        assert len(entity.modules) > 0, (
            f"modules should contain at least one module (got: {entity.modules}). "
            "This proves Stage 7 (Module Extraction) executed and modules triggered."
        )

        # Validate sports_facility module structure
        assert "sports_facility" in entity.modules, (
            f"sports_facility module should be present for padel activity (got modules: {list(entity.modules.keys())})"
        )
        assert isinstance(entity.modules["sports_facility"], dict), (
            "sports_facility module should be a structured object"
        )
        assert "padel_courts" in entity.modules["sports_facility"], (
            f"sports_facility module should contain padel_courts field (got: {list(entity.modules['sports_facility'].keys())})"
        )
        assert "total" in entity.modules["sports_facility"]["padel_courts"], (
            f"padel_courts should contain total field (got: {list(entity.modules['sports_facility']['padel_courts'].keys())})"
        )
        assert entity.modules["sports_facility"]["padel_courts"]["total"] > 0, (
            f"padel_courts.total should be populated with count > 0 (got: {entity.modules['sports_facility']['padel_courts']['total']})"
        )

        # === SUCCESS: "One Perfect Entity" Validation Passed ===
        # Constitutional requirements (system-vision.md 6.3) are satisfied:
        # - Non-empty canonical dimensions ✅
        # - At least one module field populated ✅
        # Note: latitude/longitude extraction is tracked separately (LA-011)
        # and is NOT a constitutional OPE requirement.
        print("\n" + "=" * 80)
        print("✅ ONE PERFECT ENTITY VALIDATION PASSED")
        print("=" * 80)
        print(f"Entity Name: {entity.entity_name}")
        print(f"Entity Class: {entity.entity_class}")
        print(f"Slug: {entity.slug}")
        print(f"Canonical Activities: {entity.canonical_activities}")
        print(f"Canonical Place Types: {entity.canonical_place_types}")
        print(f"Modules: {list(entity.modules.keys())}")
        print(f"Location: ({entity.latitude}, {entity.longitude})")
        print("=" * 80)

    finally:
        # Clean up test data after run
        await db.entity.delete_many(
            where={
                "OR": [
                    {"entity_name": {"contains": "West of Scotland Padel"}},
                    {"entity_name": {"contains": "west of scotland padel"}},
                ]
            }
        )
        await db.disconnect()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_canonical_dimensions_coverage():
    """
    Validate that all 4 canonical dimension arrays are supported.

    Per docs/target-architecture.md 4.1 Stage 7: Lens Application should populate:
    - canonical_activities
    - canonical_roles
    - canonical_place_types
    - canonical_access

    This test verifies that the schema and pipeline support all 4 dimensions,
    even if a specific entity doesn't populate all of them.
    """
    # Bootstrap lens
    ctx = bootstrap_lens("edinburgh_finds")

    # Connect to database
    db = Prisma()
    await db.connect()

    try:
        # Query any existing entity to verify schema structure
        entity = await db.entity.find_first()

        if entity is not None:
            # Verify all 4 canonical dimension arrays exist in schema
            assert hasattr(entity, "canonical_activities"), (
                "Entity schema should have canonical_activities field"
            )
            assert hasattr(entity, "canonical_roles"), (
                "Entity schema should have canonical_roles field"
            )
            assert hasattr(entity, "canonical_place_types"), (
                "Entity schema should have canonical_place_types field"
            )
            assert hasattr(entity, "canonical_access"), (
                "Entity schema should have canonical_access field"
            )

            # Verify all are list types (can be empty)
            assert isinstance(entity.canonical_activities, list), (
                "canonical_activities should be a list"
            )
            assert isinstance(entity.canonical_roles, list), (
                "canonical_roles should be a list"
            )
            assert isinstance(entity.canonical_place_types, list), (
                "canonical_place_types should be a list"
            )
            assert isinstance(entity.canonical_access, list), (
                "canonical_access should be a list"
            )

    finally:
        await db.disconnect()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_modules_field_structure():
    """
    Validate that modules field follows correct JSON structure.

    Per docs/target-architecture.md 4.1 Stage 7: Module Extraction should populate
    modules field as JSON object with module-specific data.

    This test verifies the modules field structure is correct for
    any entity that has modules populated.
    """
    # Bootstrap lens
    ctx = bootstrap_lens("edinburgh_finds")

    # Connect to database
    db = Prisma()
    await db.connect()

    try:
        # Query entities that have modules populated
        entities = await db.entity.find_many(
            where={
                "NOT": {
                    "modules": {}
                }
            },
            take=5  # Check first 5 entities with modules
        )

        if len(entities) > 0:
            for entity in entities:
                # Verify modules is dict/object type
                assert isinstance(entity.modules, dict), (
                    f"Entity {entity.entity_name}: modules should be a JSON object"
                )

                # Verify modules has at least one key
                assert len(entity.modules) > 0, (
                    f"Entity {entity.entity_name}: modules should not be empty if populated"
                )

                # Verify module values are dicts (not primitives)
                for module_name, module_data in entity.modules.items():
                    assert isinstance(module_data, dict), (
                        f"Entity {entity.entity_name}: module '{module_name}' should be a dict"
                    )

    finally:
        await db.disconnect()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_ope_geo_coordinate_validation():
    """
    OPE+Geo gate: prove coordinates flow end-to-end when a coordinate-rich
    source (Google Places) is in the execution plan.

    This is NOT a constitutional requirement (system-vision.md 6.3 does not
    mandate lat/lng).  It is a data-quality gate for downstream features
    (directions, mapping, geo-search).  Tracked separately from LA-003.

    Validation entity: Meadowbank Sports Centre, Edinburgh.
      - Long-standing Edinburgh landmark (Commonwealth Games 1970).
      - Reliably present in Google Places with authoritative coordinates.
      - RESOLVE_ONE + category-search routing → Serper + Google Places
        (planner.py lines 79-81: "sports centre" is a facility keyword).
      - Google Places extractor populates latitude/longitude from
        geometry.location (google_places_extractor.py:191-198).

    Assertions (coordinates only — no canonical-dimension checks):
      1. At least one "Meadowbank" entity persists.
      2. latitude is not None.
      3. longitude is not None.
    """
    ctx = bootstrap_lens("edinburgh_finds")

    db = Prisma()
    await db.connect()

    try:
        # Idempotent pre-clean
        await db.entity.delete_many(
            where={"entity_name": {"contains": "Meadowbank"}}
        )

        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="Meadowbank Sports Centre Edinburgh",
            persist=True,
        )

        report = await orchestrate(request, ctx=ctx)

        # Debug: show which connectors fired
        print("\n" + "=" * 80)
        print("OPE+Geo: ORCHESTRATION REPORT")
        print("=" * 80)
        print(f"Query: {report['query']}")
        print(f"Candidates found: {report['candidates_found']}")
        print(f"Persisted: {report.get('persisted_count', 'N/A')}")
        for name, info in report.get("connectors", {}).items():
            print(f"  {name}: items={info['items_received']}")
        print("=" * 80)

        # Retrieve persisted entity
        entities = await db.entity.find_many(
            where={"entity_name": {"contains": "Meadowbank"}}
        )

        assert len(entities) > 0, (
            "At least one Meadowbank entity must persist. "
            "Google Places Text Search should match "
            "'Meadowbank Sports Centre Edinburgh'."
        )

        entity = entities[0]

        print("\n" + "=" * 80)
        print("OPE+Geo: COORDINATE EXTRACTION STATE")
        print("=" * 80)
        print(f"entity_name:    {entity.entity_name}")
        print(f"latitude:       {entity.latitude}")
        print(f"longitude:      {entity.longitude}")
        print(f"city:           {entity.city}")
        print(f"street_address: {entity.street_address}")
        print("=" * 80)

        # OPE+Geo assertions — coordinates only
        assert entity.latitude is not None, (
            f"latitude must be populated for '{entity.entity_name}'. "
            "Google Places is the coordinate source; check that the GP adapter "
            "maps geometry.location into the raw ingestion payload."
        )
        assert entity.longitude is not None, (
            f"longitude must be populated for '{entity.entity_name}'. "
            "Google Places is the coordinate source; check that the GP adapter "
            "maps geometry.location into the raw ingestion payload."
        )

    finally:
        await db.entity.delete_many(
            where={"entity_name": {"contains": "Meadowbank"}}
        )
        await db.disconnect()
