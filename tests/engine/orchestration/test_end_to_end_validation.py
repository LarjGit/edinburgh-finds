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
    Per architecture.md Section 4.1: Complete 11-stage pipeline validation.

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
                    {"entity_name": {"contains": "Powerleague"}},
                    {"entity_name": {"contains": "powerleague"}},
                ]
            }
        )

        # Create orchestration request with persistence enabled
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="powerleague portobello edinburgh",
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
        # Search by name (case-insensitive) to find Powerleague entity
        entities = await db.entity.find_many(
            where={
                "OR": [
                    {"entity_name": {"contains": "Powerleague"}},
                    {"entity_name": {"contains": "powerleague"}},
                ]
            }
        )

        assert len(entities) > 0, (
            "At least one Powerleague entity should exist in database after orchestration"
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

        # 4. Location data (for sports facility)
        # Not strictly required by system-vision.md but good validation for Powerleague
        assert entity.latitude is not None, "latitude should be extracted"
        assert entity.longitude is not None, "longitude should be extracted"

        # === SUCCESS: "One Perfect Entity" Validation Passed ===
        # Print validation success for audit trail
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
                    {"entity_name": {"contains": "Powerleague"}},
                    {"entity_name": {"contains": "powerleague"}},
                ]
            }
        )
        await db.disconnect()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_canonical_dimensions_coverage():
    """
    Validate that all 4 canonical dimension arrays are supported.

    Per architecture.md 4.1 Stage 7: Lens Application should populate:
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

    Per architecture.md 4.1 Stage 7: Module Extraction should populate
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
