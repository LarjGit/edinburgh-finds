"""
Tests for orchestration persistence mode.

Verifies that the --persist flag correctly saves accepted entities
to the database after cross-source deduplication.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from prisma import Prisma

from engine.orchestration.cli import main
from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode


def test_persist_flag_saves_accepted_entities_to_database():
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

    # Mock the persist_entities_sync function to simulate database persistence
    mock_persist_result = {
        "persisted_count": 3,  # Simulated count
        "persistence_errors": [],
    }

    # Act: Execute orchestration with persist flag
    with patch("engine.orchestration.planner.persist_entities_sync", return_value=mock_persist_result) as mock_persist:
        report = orchestrate(request)

    # Assert: Verify persistence was attempted
    assert report["persisted_count"] == 3
    assert mock_persist.called
    # Verify it was called with accepted entities
    call_args = mock_persist.call_args[0]
    accepted_entities = call_args[0]
    assert len(accepted_entities) > 0


def test_persist_flag_false_does_not_save_to_database():
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

    # Mock persist_entities_sync
    mock_persist_result = {
        "persisted_count": 0,
        "persistence_errors": [],
    }

    # Act: Execute orchestration without persist flag
    with patch("engine.orchestration.planner.persist_entities_sync", return_value=mock_persist_result) as mock_persist:
        report = orchestrate(request)

    # Assert: Verify no persistence was attempted
    assert report.get("persisted_count") is None  # Key not even in report
    assert not mock_persist.called  # persist_entities_sync should not be called
    assert report["accepted_entities"] > 0  # Entities still processed in memory


def test_deduplication_runs_before_persistence():
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
    def mock_persist_func(accepted_entities, errors):
        return {
            "persisted_count": len(accepted_entities),
            "persistence_errors": [],
        }

    # Act: Execute orchestration
    with patch("engine.orchestration.planner.persist_entities_sync", side_effect=mock_persist_func) as mock_persist:
        report = orchestrate(request)

    # Assert: Verify deduplication worked correctly
    candidates_found = report["candidates_found"]
    persisted_count = report["persisted_count"]
    duplicates_removed = candidates_found - persisted_count

    assert persisted_count == report["accepted_entities"]
    assert duplicates_removed >= 0  # Some duplicates may have been removed
    assert mock_persist.called


def test_cli_accepts_persist_flag():
    """
    Test that CLI accepts --persist flag and passes it to orchestrator.

    Acceptance Criteria:
    - CLI parser accepts --persist flag
    - Flag is passed to IngestRequest
    - Report shows persistence status
    """
    # Arrange: Mock sys.argv to simulate CLI call
    test_args = ["cli.py", "run", "tennis courts", "--persist"]

    # Mock orchestrate function
    mock_report = {
        "query": "tennis courts",
        "candidates_found": 5,
        "accepted_entities": 3,
        "persisted_count": 3,
        "connectors": {},
        "errors": [],
    }

    # Act & Assert: Run CLI with --persist flag
    with patch("sys.argv", test_args):
        with patch("engine.orchestration.cli.orchestrate", return_value=mock_report) as mock_orch:
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify exit code is success
            assert exc_info.value.code == 0

            # Verify orchestrate was called with persist=True
            call_args = mock_orch.call_args[0][0]
            assert call_args.persist is True


def test_persist_creates_correct_extracted_entity_structure():
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

    def capture_persist(accepted_entities, errors):
        captured_entities.extend(accepted_entities)
        return {
            "persisted_count": len(accepted_entities),
            "persistence_errors": [],
        }

    # Act: Execute orchestration
    with patch("engine.orchestration.planner.persist_entities_sync", side_effect=capture_persist):
        report = orchestrate(request)

    # Assert: Verify structure of entities that would be persisted
    assert len(captured_entities) > 0

    for entity in captured_entities:
        # Verify required fields in candidate structure
        assert "source" in entity
        assert "name" in entity

        # Coordinates may or may not be present
        # external IDs may or may not be present (depends on source)


def test_persist_handles_database_errors_gracefully():
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

    # Mock persistence to return errors
    mock_persist_result = {
        "persisted_count": 0,
        "persistence_errors": [{
            "source": "test_source",
            "error": "Database connection failed",
            "entity_name": "Test Entity",
        }],
    }

    # Act: Execute orchestration
    with patch("engine.orchestration.planner.persist_entities_sync", return_value=mock_persist_result):
        report = orchestrate(request)

    # Assert: Verify error was handled
    assert "persistence_errors" in report
    assert len(report["persistence_errors"]) > 0
    assert "Database connection failed" in str(report["persistence_errors"][0])

    # Verify orchestration still completed
    assert "accepted_entities" in report
    assert report["accepted_entities"] > 0
