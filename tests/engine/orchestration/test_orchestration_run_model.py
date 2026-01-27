"""
Tests for OrchestrationRun model and database schema.

Verifies that the OrchestrationRun tracking table exists and can be
used to track orchestration sessions with linked RawIngestion records.
"""

import pytest
from prisma import Prisma


@pytest.mark.asyncio
async def test_orchestration_run_model_exists():
    """
    Test that OrchestrationRun model exists in database schema.

    Acceptance Criteria:
    - OrchestrationRun model is accessible via Prisma client
    - Model has all required fields
    """
    db = Prisma()
    await db.connect()

    try:
        # Test: Create an OrchestrationRun record
        run = await db.orchestrationrun.create(
            data={
                "query": "padel courts Edinburgh",
                "ingestion_mode": "discover_many",
                "status": "completed",
                "candidates_found": 15,
                "accepted_entities": 10,
                "budget_spent_usd": 0.05,
            }
        )

        # Assert: Record was created successfully
        assert run.id is not None
        assert run.query == "padel courts Edinburgh"
        assert run.status == "completed"
        assert run.candidates_found == 15
        assert run.accepted_entities == 10
        assert run.budget_spent_usd == 0.05

    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_raw_ingestion_links_to_orchestration_run():
    """
    Test that RawIngestion can be linked to OrchestrationRun.

    Acceptance Criteria:
    - RawIngestion has orchestration_run_id foreign key
    - Relation can be queried via Prisma
    """
    db = Prisma()
    await db.connect()

    try:
        # Step 1: Create an OrchestrationRun
        run = await db.orchestrationrun.create(
            data={
                "query": "tennis courts",
                "ingestion_mode": "discover_many",
                "status": "completed",
                "candidates_found": 5,
                "accepted_entities": 3,
            }
        )

        # Step 2: Create a RawIngestion linked to the run
        ingestion = await db.rawingestion.create(
            data={
                "source": "serper",
                "source_url": "https://example.com",
                "file_path": "engine/data/raw/serper/test.json",
                "status": "success",
                "hash": "test_hash_123",
                "orchestration_run_id": run.id,  # NEW: Link to orchestration run
            }
        )

        # Assert: Verify link was created
        assert ingestion.orchestration_run_id == run.id

        # Step 3: Query orchestration run and verify linked ingestions
        run_with_ingestions = await db.orchestrationrun.find_unique(
            where={"id": run.id},
            include={"raw_ingestions": True},
        )

        assert run_with_ingestions is not None
        assert len(run_with_ingestions.raw_ingestions) == 1
        assert run_with_ingestions.raw_ingestions[0].id == ingestion.id

    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_orchestration_run_has_all_required_fields():
    """
    Test that OrchestrationRun has all required tracking fields.

    Acceptance Criteria:
    - Model tracks query, mode, status, counts, budget, timestamps
    - Timestamps are auto-generated
    """
    db = Prisma()
    await db.connect()

    try:
        # Create a run with all fields
        run = await db.orchestrationrun.create(
            data={
                "query": "golf courses Edinburgh",
                "ingestion_mode": "verify_one",
                "status": "in_progress",
                "candidates_found": 0,
                "accepted_entities": 0,
                "budget_spent_usd": 0.0,
                "metadata_json": '{"test": "value"}',
            }
        )

        # Verify all fields exist
        assert run.query == "golf courses Edinburgh"
        assert run.ingestion_mode == "verify_one"
        assert run.status == "in_progress"
        assert run.candidates_found == 0
        assert run.accepted_entities == 0
        assert run.budget_spent_usd == 0.0
        assert run.metadata_json == '{"test": "value"}'
        assert run.createdAt is not None  # Auto-generated
        assert run.updatedAt is not None  # Auto-generated

    finally:
        await db.disconnect()
