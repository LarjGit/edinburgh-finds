"""
Tests for diagnostic logging and error visibility in orchestration persistence.

These tests verify that:
1. Extraction attempts are logged with entry/exit messages
2. Errors include full context (source, raw_id, exception details)
3. CLI displays extraction pipeline section with success/failure counts
4. Extraction errors are tracked in planner report
5. API key warnings are displayed upfront for Serper queries
"""

import pytest
import json
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from io import StringIO

from engine.orchestration.persistence import PersistenceManager
from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.orchestration.cli import format_report
from prisma import Prisma


@pytest.fixture
async def db():
    """Provide a connected Prisma database client."""
    client = Prisma()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
def mock_candidate():
    """Mock candidate entity for testing."""
    return {
        "name": "Test Venue",
        "source": "google_places",
        "raw": {
            "place_id": "ChIJ123",
            "name": "Test Venue",
            "geometry": {
                "location": {"lat": 55.9533, "lng": -3.1883}
            },
            "formatted_address": "Edinburgh EH1 1AA",
        },
    }


class TestExtractionLogging:
    """Test that extraction operations produce detailed diagnostic logs."""

    @pytest.mark.asyncio
    async def test_extraction_entry_log_contains_source_and_raw_id(self, db, caplog):
        """Test that extraction entry log includes source and raw_ingestion_id for LLM sources."""
        # GIVEN a candidate entity from an unstructured source (requires LLM extraction)
        candidate = {
            "name": "Test Venue",
            "source": "serper",  # Serper requires LLM extraction
            "raw": {
                "title": "Test Venue",
                "snippet": "A great place for padel",
                "link": "https://example.com",
            },
        }

        # WHEN we persist the entity
        with caplog.at_level(logging.DEBUG):
            async with PersistenceManager(db=db) as persistence:
                # This will fail extraction but should still log entry
                await persistence.persist_entities([candidate], [])

        # THEN we should see entry log with [PERSIST] prefix
        log_messages = [rec.message for rec in caplog.records]
        entry_logs = [msg for msg in log_messages if "[PERSIST]" in msg and "Extracting entity" in msg]

        assert len(entry_logs) > 0, "No extraction entry log found"
        entry_log = entry_logs[0]
        assert "serper" in entry_log, f"Source not in log: {entry_log}"
        assert "raw_ingestion_id=" in entry_log, f"Raw ingestion ID not in log: {entry_log}"

    @pytest.mark.asyncio
    async def test_structured_source_log_contains_source_and_raw_id(self, db, caplog):
        """Test that structured sources log processing with source and raw_ingestion_id."""
        # GIVEN a candidate entity from a structured source
        candidate = {
            "name": "Test Venue",
            "source": "google_places",  # Structured source (no LLM extraction)
            "raw": {
                "place_id": "ChIJ123",
                "name": "Test Venue",
                "geometry": {"location": {"lat": 55.9533, "lng": -3.1883}},
                "formatted_address": "Edinburgh EH1 1AA",
            },
        }

        # WHEN we persist the entity
        with caplog.at_level(logging.DEBUG):
            async with PersistenceManager(db=db) as persistence:
                await persistence.persist_entities([candidate], [])

        # THEN we should see structured source processing log
        log_messages = [rec.message for rec in caplog.records]
        processing_logs = [msg for msg in log_messages if "[PERSIST]" in msg and "Processing structured source" in msg]

        assert len(processing_logs) > 0, "No structured source processing log found"
        processing_log = processing_logs[0]
        assert "google_places" in processing_log, f"Source not in log: {processing_log}"
        assert "raw_ingestion_id=" in processing_log, f"Raw ingestion ID not in log: {processing_log}"


class TestExtractionErrorHandling:
    """Test that extraction errors include full context and stack traces."""

    @pytest.mark.asyncio
    async def test_extraction_error_includes_full_stack_trace(self, db, caplog):
        """Test that extraction errors log full stack trace with context."""
        # GIVEN a candidate that will fail extraction (invalid data)
        candidate = {
            "name": "Bad Venue",
            "source": "serper",  # Requires LLM extraction
            "raw": {
                "invalid": "data structure"
            },
        }

        # WHEN we persist the entity (should fail)
        errors = []
        with caplog.at_level(logging.ERROR):
            async with PersistenceManager(db=db) as persistence:
                result = await persistence.persist_entities([candidate], errors)

        # THEN error log should include full context
        error_logs = [rec for rec in caplog.records if rec.levelname == "ERROR"]
        assert len(error_logs) > 0, "No error logs found"

        error_log = error_logs[0]
        assert "[PERSIST]" in error_log.message, "Error log missing [PERSIST] prefix"
        assert "serper" in error_log.message, "Source not in error log"
        assert "raw_ingestion_id=" in error_log.message, "Raw ingestion ID not in error log"
        # Stack trace should be in exc_info
        assert error_log.exc_info is not None, "Stack trace not logged"

    @pytest.mark.asyncio
    async def test_extraction_errors_tracked_in_persistence_result(self, db):
        """Test that extraction errors are captured in persistence result."""
        # GIVEN a candidate that will fail extraction
        candidate = {
            "name": "Bad Venue",
            "source": "serper",
            "raw": {"invalid": "data"},
        }

        # WHEN we persist the entity
        errors = []
        async with PersistenceManager(db=db) as persistence:
            result = await persistence.persist_entities([candidate], errors)

        # THEN result should contain extraction error details
        assert "persistence_errors" in result
        assert len(result["persistence_errors"]) > 0

        error = result["persistence_errors"][0]
        assert "source" in error
        assert error["source"] == "serper"
        assert "error" in error
        assert "entity_name" in error
        assert error["entity_name"] == "Bad Venue"


class TestPlannerExtractionTracking:
    """Test that planner tracks extraction success/failure counts."""

    @pytest.mark.asyncio
    async def test_planner_report_includes_extraction_counts(self):
        """Test that orchestration report includes extraction success/failure counts."""
        # GIVEN a query that will trigger connectors
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="test padel venue",
            persist=True,
        )

        # WHEN we run orchestration
        with patch("engine.orchestration.planner.select_connectors") as mock_select:
            # Mock connector selection to return no connectors (avoid real API calls)
            mock_select.return_value = []
            report = await orchestrate(request)

        # THEN report should include extraction counts
        assert "extraction_total" in report, "Report missing extraction_total"
        assert "extraction_success" in report, "Report missing extraction_success"
        assert "extraction_errors" in report, "Report missing extraction_errors"

    @pytest.mark.asyncio
    async def test_extraction_errors_include_required_fields(self, db):
        """Test that extraction errors include source, entity_name, error, timestamp."""
        # GIVEN a candidate that will fail extraction
        mock_candidate = {
            "name": "Bad Entity",
            "source": "serper",
            "raw": {"invalid": "data"},
        }

        # WHEN we persist with extraction failure
        errors = []
        async with PersistenceManager(db=db) as persistence:
            result = await persistence.persist_entities([mock_candidate], errors)

        # THEN extraction errors should have all required fields
        if result.get("persistence_errors"):
            error = result["persistence_errors"][0]
            assert "source" in error, "Extraction error missing 'source'"
            assert "entity_name" in error, "Extraction error missing 'entity_name'"
            assert "error" in error, "Extraction error missing 'error'"
            assert "timestamp" in error, "Extraction error missing 'timestamp'"


class TestCLIExtractionDisplay:
    """Test that CLI displays extraction pipeline section."""

    def test_cli_shows_extraction_pipeline_section(self):
        """Test that CLI report includes 'Extraction Pipeline' section."""
        # GIVEN a report with extraction data
        report = {
            "query": "test query",
            "candidates_found": 5,
            "accepted_entities": 3,
            "persisted_count": 3,
            "extraction_total": 5,
            "extraction_success": 3,
            "extraction_errors": [
                {
                    "source": "serper",
                    "entity_name": "Failed Entity",
                    "error": "Extraction failed",
                    "timestamp": "2026-01-27T12:00:00Z",
                }
            ],
            "connectors": {},
            "errors": [],
        }

        # WHEN we format the report
        formatted = format_report(report)

        # THEN it should include Extraction Pipeline section
        assert "Extraction Pipeline" in formatted, "Report missing 'Extraction Pipeline' section"
        # Check for success count (may have spaces around /)
        assert "3/5" in formatted or "3 /5" in formatted or "3/ 5" in formatted, \
            "Extraction success count not displayed"

    def test_cli_shows_extraction_success_with_green_color(self):
        """Test that successful extractions are color-coded green."""
        # GIVEN a report with all successful extractions
        report = {
            "query": "test query",
            "candidates_found": 5,
            "accepted_entities": 5,
            "persisted_count": 5,
            "extraction_total": 5,
            "extraction_success": 5,
            "extraction_errors": [],
            "connectors": {},
            "errors": [],
        }

        # WHEN we format the report
        formatted = format_report(report)

        # THEN success count should be green
        assert "\033[92m" in formatted, "Green color code not found in output"
        assert "5/5" in formatted or "5 / 5" in formatted, "Success count not displayed"

    def test_cli_lists_extraction_failures_with_details(self):
        """Test that extraction failures are listed with source and error."""
        # GIVEN a report with extraction errors
        report = {
            "query": "test query",
            "candidates_found": 5,
            "accepted_entities": 3,
            "persisted_count": 3,
            "extraction_total": 5,
            "extraction_success": 3,
            "extraction_errors": [
                {
                    "source": "serper",
                    "entity_name": "Bad Entity 1",
                    "error": "Invalid data structure",
                    "timestamp": "2026-01-27T12:00:00Z",
                },
                {
                    "source": "openstreetmap",
                    "entity_name": "Bad Entity 2",
                    "error": "Missing required fields",
                    "timestamp": "2026-01-27T12:01:00Z",
                },
            ],
            "connectors": {},
            "errors": [],
        }

        # WHEN we format the report
        formatted = format_report(report)

        # THEN both errors should be listed
        assert "serper" in formatted, "Serper error not displayed"
        assert "Bad Entity 1" in formatted, "First entity name not displayed"
        assert "Invalid data structure" in formatted, "First error message not displayed"
        assert "openstreetmap" in formatted, "OSM error not displayed"
        assert "Bad Entity 2" in formatted, "Second entity name not displayed"
        assert "Missing required fields" in formatted, "Second error message not displayed"


class TestAPIKeyValidation:
    """Test upfront API key validation for Serper queries."""

    @pytest.mark.asyncio
    async def test_cli_warns_if_serper_needed_without_api_key(self):
        """Test that CLI displays warning if Serper will be used without ANTHROPIC_API_KEY."""
        import os

        # GIVEN Serper will be selected but API key is missing
        original_key = os.environ.get("ANTHROPIC_API_KEY")
        try:
            if original_key:
                del os.environ["ANTHROPIC_API_KEY"]

            request = IngestRequest(
                ingestion_mode=IngestionMode.DISCOVER_MANY,
                query="test padel courts",  # Should trigger Serper
                persist=True,
            )

            # WHEN we run orchestration (mock connector execution to avoid real API calls)
            with patch("engine.orchestration.planner.select_connectors") as mock_select:
                mock_select.return_value = ["serper"]

                # Mock ConnectorAdapter to avoid actual connector execution
                with patch("engine.orchestration.planner.ConnectorAdapter") as mock_adapter_class:
                    mock_adapter = AsyncMock()
                    mock_adapter.execute.return_value = []
                    mock_adapter_class.return_value = mock_adapter

                    report = await orchestrate(request)

            # THEN report should include API key warning
            assert "warnings" in report or "errors" in report, "No warnings in report"

            # Check if warning exists in either warnings or errors
            all_messages = report.get("warnings", []) + report.get("errors", [])
            warning_found = any(
                "ANTHROPIC_API_KEY" in str(msg) and "Serper" in str(msg)
                for msg in all_messages
            )
            assert warning_found, "API key warning not found in report"

        finally:
            # Restore original API key
            if original_key:
                os.environ["ANTHROPIC_API_KEY"] = original_key

    def test_cli_displays_api_key_warning_prominently(self):
        """Test that API key warning is displayed prominently in CLI output."""
        # GIVEN a report with API key warning
        report = {
            "query": "test query",
            "candidates_found": 0,
            "accepted_entities": 0,
            "persisted_count": 0,
            "extraction_total": 0,
            "extraction_success": 0,
            "extraction_errors": [],
            "connectors": {},
            "errors": [],
            "warnings": [
                {
                    "type": "missing_api_key",
                    "message": "⚠ Serper extraction will fail without ANTHROPIC_API_KEY",
                }
            ],
        }

        # WHEN we format the report
        formatted = format_report(report)

        # THEN warning should be prominently displayed
        assert "⚠" in formatted or "WARNING" in formatted.upper(), "Warning symbol not found"
        assert "ANTHROPIC_API_KEY" in formatted, "API key not mentioned in warning"
        assert "Serper" in formatted, "Serper not mentioned in warning"
