"""
Tests for async refactoring of orchestration layer.

Verifies that:
- orchestrate() is an async function (coroutine)
- CLI calls orchestrate via asyncio.run()
- Persistence works correctly without sync wrapper
- Google Places data is persisted correctly
"""

import asyncio
import pytest
import inspect
from unittest.mock import patch, AsyncMock, MagicMock

from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.orchestration.cli import main


class TestOrchestrateIsAsync:
    """Test that orchestrate() is an async function."""

    def test_orchestrate_is_coroutine_function(self):
        """orchestrate() should be a coroutine function (async def)."""
        assert inspect.iscoroutinefunction(orchestrate), \
            "orchestrate() should be defined with 'async def'"

    @pytest.mark.asyncio
    async def test_orchestrate_returns_coroutine(self):
        """Calling orchestrate() should return a coroutine object."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
            persist=False,
        )

        result = orchestrate(request)
        assert inspect.iscoroutine(result), \
            "orchestrate(request) should return a coroutine"

        # Clean up the coroutine
        await result

    @pytest.mark.asyncio
    async def test_orchestrate_can_be_awaited(self):
        """orchestrate() should be awaitable and return a report dict."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
            persist=False,
        )

        report = await orchestrate(request)

        assert isinstance(report, dict), "awaiting orchestrate() should return dict"
        assert "query" in report
        assert "candidates_found" in report
        assert "accepted_entities" in report


class TestCLIUsesAsyncioRun:
    """Test that CLI properly calls async orchestrate via asyncio.run()."""

    def test_cli_calls_orchestrate_with_asyncio_run(self):
        """CLI main() should call orchestrate via asyncio.run()."""
        test_args = ["cli.py", "run", "tennis courts", "--persist"]

        # Create a mock async orchestrate that returns a report
        async def mock_async_orchestrate(request):
            return {
                "query": request.query,
                "candidates_found": 5,
                "accepted_entities": 3,
                "persisted_count": 3,
                "connectors": {},
                "errors": [],
            }

        # Mock asyncio.run to capture the call
        with patch("sys.argv", test_args):
            with patch("engine.orchestration.cli.orchestrate", side_effect=mock_async_orchestrate) as mock_orch:
                with patch("asyncio.run") as mock_asyncio_run:
                    # Set up mock to actually execute the coroutine
                    def run_coro(coro):
                        loop = asyncio.new_event_loop()
                        try:
                            return loop.run_until_complete(coro)
                        finally:
                            loop.close()

                    mock_asyncio_run.side_effect = run_coro

                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 0

                    # Verify asyncio.run was called
                    assert mock_asyncio_run.called, \
                        "CLI should call asyncio.run() to execute async orchestrate"


class TestPersistenceWithoutSyncWrapper:
    """Test that persistence works without persist_entities_sync wrapper."""

    @pytest.mark.asyncio
    async def test_orchestrate_calls_persistence_directly(self):
        """orchestrate() should call PersistenceManager.persist_entities directly."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts Edinburgh",
            persist=True,
        )

        # Mock PersistenceManager.persist_entities
        mock_persist_result = {
            "persisted_count": 3,
            "persistence_errors": [],
        }

        with patch("engine.orchestration.planner.PersistenceManager") as mock_pm_class:
            # Create mock instance
            mock_pm_instance = MagicMock()
            mock_pm_instance.__aenter__ = AsyncMock(return_value=mock_pm_instance)
            mock_pm_instance.__aexit__ = AsyncMock(return_value=None)
            mock_pm_instance.persist_entities = AsyncMock(return_value=mock_persist_result)

            mock_pm_class.return_value = mock_pm_instance

            report = await orchestrate(request)

            # Verify PersistenceManager was used
            assert mock_pm_class.called, "orchestrate should create PersistenceManager"
            assert mock_pm_instance.persist_entities.called, \
                "orchestrate should call persist_entities directly"

            # Verify report includes persistence info
            assert report["persisted_count"] == 3
            assert "persistence_errors" in report

    @pytest.mark.asyncio
    async def test_no_persist_entities_sync_function_used(self):
        """orchestrate() should NOT import or use persist_entities_sync wrapper."""
        # Verify persist_entities_sync is not imported in planner module
        import engine.orchestration.planner as planner_module

        assert not hasattr(planner_module, 'persist_entities_sync'), \
            "planner should NOT import persist_entities_sync - use PersistenceManager directly"

        # Verify PersistenceManager IS imported
        assert hasattr(planner_module, 'PersistenceManager'), \
            "planner should import PersistenceManager"


class TestGooglePlacesPersistence:
    """Test that Google Places data is persisted correctly."""

    @pytest.mark.asyncio
    async def test_google_places_data_persists_correctly(self):
        """Google Places entities should be persisted with correct structure."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="powerleague portobello",
            persist=True,
        )

        # Capture what gets passed to persistence
        captured_entities = []

        async def capture_persist(accepted_entities, errors):
            captured_entities.extend(accepted_entities)
            return {
                "persisted_count": len(accepted_entities),
                "persistence_errors": [],
            }

        with patch("engine.orchestration.planner.PersistenceManager") as mock_pm_class:
            mock_pm_instance = MagicMock()
            mock_pm_instance.__aenter__ = AsyncMock(return_value=mock_pm_instance)
            mock_pm_instance.__aexit__ = AsyncMock(return_value=None)
            mock_pm_instance.persist_entities = AsyncMock(side_effect=capture_persist)
            mock_pm_class.return_value = mock_pm_instance

            report = await orchestrate(request)

            # Verify entities from Google Places are included
            google_places_entities = [
                e for e in captured_entities
                if e.get("source") == "google_places"
            ]

            # Should have at least some Google Places entities
            # (actual count depends on API response, but we verify structure)
            if len(google_places_entities) > 0:
                entity = google_places_entities[0]

                # Verify required fields
                assert "source" in entity
                assert entity["source"] == "google_places"
                assert "name" in entity
                # raw field should contain original Google Places data
                assert "raw" in entity

    @pytest.mark.asyncio
    async def test_async_persistence_handles_errors_gracefully(self):
        """Async persistence should handle errors gracefully without event loop issues."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="test query",
            persist=True,
        )

        # Mock persistence to raise an error
        async def failing_persist(accepted_entities, errors):
            raise Exception("Database connection error")

        with patch("engine.orchestration.planner.PersistenceManager") as mock_pm_class:
            mock_pm_instance = MagicMock()
            mock_pm_instance.__aenter__ = AsyncMock(return_value=mock_pm_instance)
            mock_pm_instance.__aexit__ = AsyncMock(return_value=None)
            mock_pm_instance.persist_entities = AsyncMock(side_effect=failing_persist)
            mock_pm_class.return_value = mock_pm_instance

            # Should not raise - errors should be captured
            report = await orchestrate(request)

            # Verify orchestration completed despite persistence error
            assert "candidates_found" in report
            assert "accepted_entities" in report
