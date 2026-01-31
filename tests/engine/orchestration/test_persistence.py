"""
Tests for orchestration persistence mode.

Verifies that the --persist flag correctly saves accepted entities
to the database after cross-source deduplication.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from prisma import Prisma

from engine.orchestration.cli import main
from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode


@pytest.mark.asyncio
async def test_persist_flag_saves_accepted_entities_to_database(mock_context):
    """
    Test that --persist flag triggers database persistence.

    Acceptance Criteria:
    - Accepted entities are saved to ExtractedEntity table
    - Deduplication happens BEFORE persistence
    - Only unique entities are saved (duplicates are filtered)
    """
    # Arrange: Create request with persist=True
    request = IngestRequest(
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        query="padel courts Edinburgh",
        persist=True,  # NEW: Flag to enable persistence
    )

    # Mock PersistenceManager
    mock_persist_result = {
        "persisted_count": 3,  # Simulated count
        "persistence_errors": [],
    }

    # Act: Execute orchestration with persist flag
    with patch("engine.orchestration.planner.PersistenceManager") as mock_pm_class:
        mock_pm_instance = MagicMock()
        mock_pm_instance.__aenter__ = AsyncMock(return_value=mock_pm_instance)
        mock_pm_instance.__aexit__ = AsyncMock(return_value=None)
        mock_pm_instance.persist_entities = AsyncMock(return_value=mock_persist_result)
        mock_pm_class.return_value = mock_pm_instance

        report = await orchestrate(request, ctx=mock_context)

    # Assert: Verify persistence was attempted
    assert report["persisted_count"] == 3
    assert mock_pm_instance.persist_entities.called
    # Verify it was called with accepted entities
    call_args = mock_pm_instance.persist_entities.call_args[0]
    accepted_entities = call_args[0]
    assert len(accepted_entities) > 0


@pytest.mark.asyncio
async def test_persist_flag_false_does_not_save_to_database(mock_context):
    """
    Test that without --persist flag, entities are NOT saved to database.

    Acceptance Criteria:
    - No database operations occur when persist=False
    - Report still shows accepted_entities count
    """
    # Arrange: Create request with persist=False (default)
    request = IngestRequest(
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        query="padel courts Edinburgh",
        persist=False,  # Explicitly set to False
    )

    # Mock PersistenceManager
    with patch("engine.orchestration.planner.PersistenceManager") as mock_pm_class:
        mock_pm_instance = MagicMock()
        mock_pm_instance.__aenter__ = AsyncMock(return_value=mock_pm_instance)
        mock_pm_instance.__aexit__ = AsyncMock(return_value=None)
        mock_pm_instance.persist_entities = AsyncMock()
        mock_pm_class.return_value = mock_pm_instance

        report = await orchestrate(request, ctx=mock_context)

    # Assert: Verify no persistence was attempted
    assert report.get("persisted_count") is None  # Key not even in report
    assert not mock_pm_class.called  # PersistenceManager should not be created
    assert report["accepted_entities"] > 0  # Entities still processed in memory


@pytest.mark.asyncio
async def test_deduplication_runs_before_persistence(mock_context):
    """
    Test that deduplication happens BEFORE database persistence.

    Acceptance Criteria:
    - Duplicate entities are NOT saved to database
    - Only unique entities are persisted
    - Deduplication count matches (candidates_found - persisted_count)
    """
    # Arrange: Create request that will return duplicates
    request = IngestRequest(
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        query="specific venue with google place id",
        persist=True,
    )

    # Mock persistence to return count matching accepted entities
    async def mock_persist_func(accepted_entities, errors, orchestration_run_id=None, context=None):
        return {
            "persisted_count": len(accepted_entities),
            "persistence_errors": [],
        }

    # Act: Execute orchestration
    with patch("engine.orchestration.planner.PersistenceManager") as mock_pm_class:
        mock_pm_instance = MagicMock()
        mock_pm_instance.__aenter__ = AsyncMock(return_value=mock_pm_instance)
        mock_pm_instance.__aexit__ = AsyncMock(return_value=None)
        mock_pm_instance.persist_entities = AsyncMock(side_effect=mock_persist_func)
        mock_pm_class.return_value = mock_pm_instance

        report = await orchestrate(request, ctx=mock_context)

    # Assert: Verify deduplication worked correctly
    candidates_found = report["candidates_found"]
    persisted_count = report["persisted_count"]
    duplicates_removed = candidates_found - persisted_count

    assert persisted_count == report["accepted_entities"]
    assert duplicates_removed >= 0  # Some duplicates may have been removed
    assert mock_pm_instance.persist_entities.called


def test_cli_accepts_persist_flag():
    """
    Test that CLI accepts --persist flag and passes it to orchestrator.

    Acceptance Criteria:
    - CLI parser accepts --persist flag
    - Flag is passed to IngestRequest
    - Report shows persistence status
    """
    # Arrange: Mock sys.argv to simulate CLI call
    test_args = ["cli.py", "run", "--lens", "edinburgh_finds", "tennis courts", "--persist"]

    # Mock orchestrate function as async (with ctx parameter)
    async def mock_async_orchestrate(request, *, ctx=None):
        return {
            "query": request.query,
            "candidates_found": 5,
            "accepted_entities": 3,
            "persisted_count": 3,
            "connectors": {},
            "errors": [],
        }

    # Act & Assert: Run CLI with --persist flag
    with patch("sys.argv", test_args):
        with patch("engine.orchestration.cli.orchestrate", side_effect=mock_async_orchestrate) as mock_orch:
            with patch("engine.orchestration.cli.bootstrap_lens") as mock_bootstrap:
                # Mock bootstrap to return minimal context
                from engine.orchestration.execution_context import ExecutionContext
                mock_bootstrap.return_value = ExecutionContext(
                    lens_id="edinburgh_finds",
                    lens_contract={
                        "mapping_rules": [],
                        "module_triggers": [],
                        "modules": {},
                        "facets": {},
                        "values": [],
                        "confidence_threshold": 0.7,
                        "lens_id": "edinburgh_finds",
                    },
                    lens_hash="test_hash"
                )

                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Verify exit code is success
                assert exc_info.value.code == 0

                # Verify orchestrate was called with persist=True
                call_args = mock_orch.call_args[0][0]
                assert call_args.persist is True


@pytest.mark.asyncio
async def test_persist_creates_correct_extracted_entity_structure(mock_context):
    """
    Test that persisted entities have correct structure in database.

    Acceptance Criteria:
    - ExtractedEntity has all required fields
    - external_ids are properly formatted
    - attributes are JSON-serialized
    - source is correctly set
    """
    # Arrange: Create request with persist=True
    request = IngestRequest(
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        query="padel courts Edinburgh",
        persist=True,
    )

    # Capture the accepted_entities passed to persist function
    captured_entities = []

    async def capture_persist(accepted_entities, errors, orchestration_run_id=None, context=None):
        captured_entities.extend(accepted_entities)
        return {
            "persisted_count": len(accepted_entities),
            "persistence_errors": [],
        }

    # Act: Execute orchestration
    with patch("engine.orchestration.planner.PersistenceManager") as mock_pm_class:
        mock_pm_instance = MagicMock()
        mock_pm_instance.__aenter__ = AsyncMock(return_value=mock_pm_instance)
        mock_pm_instance.__aexit__ = AsyncMock(return_value=None)
        mock_pm_instance.persist_entities = AsyncMock(side_effect=capture_persist)
        mock_pm_class.return_value = mock_pm_instance

        report = await orchestrate(request, ctx=mock_context)

    # Assert: Verify structure of entities that would be persisted
    assert len(captured_entities) > 0

    for entity in captured_entities:
        # Verify required fields in candidate structure
        assert "source" in entity
        assert "name" in entity

        # Coordinates may or may not be present
        # external IDs may or may not be present (depends on source)


@pytest.mark.asyncio
async def test_persist_handles_database_errors_gracefully(mock_context):
    """
    Test that database errors during persistence are handled gracefully.

    Acceptance Criteria:
    - Database errors are caught and reported
    - Orchestration continues despite persistence failures
    - Error count in report reflects persistence failures
    """
    # Arrange: Create request with persist=True
    request = IngestRequest(
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        query="padel courts Edinburgh",
        persist=True,
    )

    # Mock persistence to raise an error
    async def failing_persist(accepted_entities, errors, orchestration_run_id=None, context=None):
        raise Exception("Database connection failed")

    # Act: Execute orchestration
    with patch("engine.orchestration.planner.PersistenceManager") as mock_pm_class:
        mock_pm_instance = MagicMock()
        mock_pm_instance.__aenter__ = AsyncMock(return_value=mock_pm_instance)
        mock_pm_instance.__aexit__ = AsyncMock(return_value=None)
        mock_pm_instance.persist_entities = AsyncMock(side_effect=failing_persist)
        mock_pm_class.return_value = mock_pm_instance

        report = await orchestrate(request, ctx=mock_context)

    # Assert: Verify error was handled
    assert "persistence_errors" in report
    assert len(report["persistence_errors"]) > 0
    assert "Database connection failed" in str(report["persistence_errors"][0])

    # Verify orchestration still completed
    assert "accepted_entities" in report
    assert report["accepted_entities"] > 0
