"""Test EntityFinalizer (TDD)."""

import pytest
import json
from prisma import Prisma
from engine.orchestration.entity_finalizer import EntityFinalizer


@pytest.mark.slow
@pytest.mark.asyncio
async def test_finalize_single_entity():
    """Test finalization of single ExtractedEntity (no merging)."""
    db = Prisma()
    await db.connect()

    # Setup: Create OrchestrationRun
    orchestration_run = await db.orchestrationrun.create(
        data={
            "query": "test query",
            "status": "completed",
            "ingestion_mode": "DISCOVER_MANY"
        }
    )

    # Setup: Create RawIngestion
    raw_ingestion = await db.rawingestion.create(
        data={
            "orchestration_run_id": orchestration_run.id,
            "source": "test_source",
            "source_url": "https://test.com/123",
            "file_path": "test/path.json",
            "status": "success",
            "hash": "test-hash-123"
        }
    )

    # Setup: Create ExtractedEntity
    attributes = {
        "name": "Test Venue",
        "location_lat": 55.9533,
        "location_lng": -3.1883,
        "canonical_activities": ["padel"],
        "canonical_roles": ["provides_facility"]
    }

    extracted = await db.extractedentity.create(
        data={
            "raw_ingestion_id": raw_ingestion.id,
            "source": "test_source",
            "entity_class": "place",
            "attributes": json.dumps(attributes),
            "external_ids": json.dumps({"test": "test-123"})
        }
    )

    # Act: Finalize entities
    finalizer = EntityFinalizer(db)
    stats = await finalizer.finalize_entities(orchestration_run.id)

    # Assert: Stats
    assert stats["entities_created"] == 1
    assert stats["entities_updated"] == 0

    # Assert: Entity created
    entities = await db.entity.find_many(
        where={"entity_name": "Test Venue"}
    )
    assert len(entities) == 1

    entity = entities[0]
    assert entity.slug == "test-venue"
    assert entity.entity_class == "place"
    assert entity.entity_name == "Test Venue"
    assert entity.latitude == 55.9533
    assert "padel" in entity.canonical_activities

    # Cleanup
    await db.entity.delete(where={"id": entity.id})
    await db.extractedentity.delete(where={"id": extracted.id})
    await db.rawingestion.delete(where={"id": raw_ingestion.id})
    await db.orchestrationrun.delete(where={"id": orchestration_run.id})
    await db.disconnect()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_finalize_idempotent():
    """Test that re-finalizing updates existing Entity (idempotent)."""
    db = Prisma()
    await db.connect()

    # Setup: Create test data
    orchestration_run = await db.orchestrationrun.create(
        data={
            "query": "test query",
            "status": "completed",
            "ingestion_mode": "DISCOVER_MANY"
        }
    )

    raw_ingestion = await db.rawingestion.create(
        data={
            "orchestration_run_id": orchestration_run.id,
            "source": "test_source",
            "source_url": "https://test.com/456",
            "file_path": "test/path2.json",
            "status": "success",
            "hash": "test-hash-456"
        }
    )

    attributes = {
        "name": "Idempotent Venue",
        "location_lat": 55.9533,
        "location_lng": -3.1883
    }

    extracted = await db.extractedentity.create(
        data={
            "raw_ingestion_id": raw_ingestion.id,
            "source": "test_source",
            "entity_class": "place",
            "attributes": json.dumps(attributes),
            "external_ids": json.dumps({})
        }
    )

    # Act: First finalization
    finalizer = EntityFinalizer(db)
    stats1 = await finalizer.finalize_entities(orchestration_run.id)

    entities_after_first = await db.entity.find_many(
        where={"entity_name": "Idempotent Venue"}
    )
    assert len(entities_after_first) == 1
    first_entity_id = entities_after_first[0].id

    # Act: Second finalization (idempotent)
    stats2 = await finalizer.finalize_entities(orchestration_run.id)

    # Assert: Updated, not duplicated
    assert stats2["entities_created"] == 0
    assert stats2["entities_updated"] == 1

    entities_after_second = await db.entity.find_many(
        where={"entity_name": "Idempotent Venue"}
    )
    assert len(entities_after_second) == 1
    assert entities_after_second[0].id == first_entity_id

    # Cleanup
    await db.entity.delete(where={"id": first_entity_id})
    await db.extractedentity.delete(where={"id": extracted.id})
    await db.rawingestion.delete(where={"id": raw_ingestion.id})
    await db.orchestrationrun.delete(where={"id": orchestration_run.id})
    await db.disconnect()
