"""
Tests for CLI flags (--dry-run, --force-retry, --limit).

These tests verify that CLI flags work as expected:
- --dry-run: Simulates extraction without database writes
- --force-retry: Re-extracts even if already processed
- --limit: Limits the number of records processed
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
from pathlib import Path

from engine.extraction.run import (
    run_single_extraction,
    run_source_extraction,
    run_all_extraction,
)


@pytest.mark.asyncio
async def test_dry_run_flag_single_extraction():
    """Test that --dry-run flag prevents database writes in single extraction."""
    # Setup mock data
    mock_raw = MagicMock()
    mock_raw.id = "raw-1"
    mock_raw.source = "google_places"
    mock_raw.file_path = "test.json"
    mock_raw.status = "success"

    mock_data = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    # Setup mock database
    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.extractedlisting.create = AsyncMock()

    # Mock file reading
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        # Run extraction with dry_run=True
        result = await run_single_extraction(
            mock_db,
            raw_id="raw-1",
            verbose=True,
            dry_run=True,
        )

    # Verify extraction was successful
    assert result["status"] == "success"
    assert result["dry_run"] is True
    assert result["extracted_id"] == "dry-run-simulation"

    # Verify no database write was called
    mock_db.extractedlisting.create.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_flag_source_extraction():
    """Test that --dry-run flag prevents database writes in source extraction."""
    # Setup mock data
    mock_raw = MagicMock()
    mock_raw.id = "raw-1"
    mock_raw.source = "google_places"
    mock_raw.file_path = "test.json"
    mock_raw.status = "success"

    mock_data = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    # Setup mock database
    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=[mock_raw])
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.extractedlisting.create = AsyncMock()

    # Mock file reading
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        # Run source extraction with dry_run=True
        result = await run_source_extraction(
            mock_db,
            source="google_places",
            limit=1,
            dry_run=True,
        )

    # Verify extraction was successful
    assert result["status"] == "success"
    assert result["dry_run"] is True
    assert result["successful"] == 1

    # Verify no database write was called
    mock_db.extractedlisting.create.assert_not_called()


@pytest.mark.asyncio
async def test_force_retry_flag_single_extraction():
    """Test that --force-retry flag re-extracts already processed records."""
    # Setup mock data
    mock_raw = MagicMock()
    mock_raw.id = "raw-1"
    mock_raw.source = "google_places"
    mock_raw.file_path = "test.json"
    mock_raw.status = "success"

    mock_existing = MagicMock()
    mock_existing.id = "extracted-1"
    mock_existing.attributes = "{}"
    mock_existing.discovered_attributes = "{}"

    mock_data = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    # Setup mock database
    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)

    # Test 1: Without force_retry (should return already_extracted)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=mock_existing)

    result1 = await run_single_extraction(
        mock_db,
        raw_id="raw-1",
        verbose=False,
        dry_run=False,
        force_retry=False,
    )

    assert result1["status"] == "already_extracted"
    assert result1["extracted_id"] == "extracted-1"

    # Test 2: With force_retry (should re-extract)
    mock_db.extractedlisting.create = AsyncMock(return_value=MagicMock(id="extracted-2"))

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        result2 = await run_single_extraction(
            mock_db,
            raw_id="raw-1",
            verbose=False,
            dry_run=False,
            force_retry=True,
        )

    assert result2["status"] == "success"
    assert result2["extracted_id"] == "extracted-2"

    # Verify database write was called
    mock_db.extractedlisting.create.assert_called_once()


@pytest.mark.asyncio
async def test_force_retry_flag_source_extraction():
    """Test that --force-retry flag works in source extraction."""
    # Setup mock data
    mock_raw = MagicMock()
    mock_raw.id = "raw-1"
    mock_raw.source = "google_places"
    mock_raw.file_path = "test.json"
    mock_raw.status = "success"

    mock_existing = MagicMock()
    mock_existing.id = "extracted-1"

    mock_data = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    # Setup mock database
    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=[mock_raw])

    # Test 1: Without force_retry (should skip already extracted)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=mock_existing)
    mock_db.extractedlisting.create = AsyncMock()

    result1 = await run_source_extraction(
        mock_db,
        source="google_places",
        limit=1,
        dry_run=False,
        force_retry=False,
    )

    assert result1["status"] == "success"
    assert result1["already_extracted"] == 1
    assert result1["successful"] == 0
    mock_db.extractedlisting.create.assert_not_called()

    # Test 2: With force_retry (should re-extract)
    mock_db.extractedlisting.create = AsyncMock(return_value=MagicMock(id="extracted-2"))

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        result2 = await run_source_extraction(
            mock_db,
            source="google_places",
            limit=1,
            dry_run=False,
            force_retry=True,
        )

    assert result2["status"] == "success"
    assert result2["successful"] == 1
    assert result2["already_extracted"] == 0

    # Verify database write was called
    mock_db.extractedlisting.create.assert_called_once()


@pytest.mark.asyncio
async def test_limit_flag_source_extraction():
    """Test that --limit flag correctly limits the number of records processed."""
    # Create multiple mock raw records
    mock_raws = []
    for i in range(5):
        mock_raw = MagicMock()
        mock_raw.id = f"raw-{i}"
        mock_raw.source = "google_places"
        mock_raw.file_path = f"test{i}.json"
        mock_raw.status = "success"
        mock_raws.append(mock_raw)

    mock_data = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    # Setup mock database - limit should be passed to find_many
    mock_db = AsyncMock()
    # When limit=3, find_many should only return 3 records
    mock_db.rawingestion.find_many = AsyncMock(return_value=mock_raws[:3])
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.extractedlisting.create = AsyncMock(
        side_effect=[MagicMock(id=f"extracted-{i}") for i in range(3)]
    )

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        # Run extraction with limit=3
        result = await run_source_extraction(
            mock_db,
            source="google_places",
            limit=3,
            dry_run=False,
            force_retry=False,
        )

    # Verify only 3 records were processed
    assert result["total_records"] == 3
    assert result["successful"] == 3


@pytest.mark.asyncio
async def test_dry_run_with_force_retry_combination():
    """Test that --dry-run and --force-retry can be used together."""
    # Setup mock data
    mock_raw = MagicMock()
    mock_raw.id = "raw-1"
    mock_raw.source = "google_places"
    mock_raw.file_path = "test.json"
    mock_raw.status = "success"

    mock_existing = MagicMock()
    mock_existing.id = "extracted-1"

    mock_data = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    # Setup mock database
    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=mock_existing)
    mock_db.extractedlisting.create = AsyncMock()

    # Run with both dry_run=True and force_retry=True
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        result = await run_single_extraction(
            mock_db,
            raw_id="raw-1",
            verbose=False,
            dry_run=True,
            force_retry=True,
        )

    # Should re-extract but not save
    assert result["status"] == "success"
    assert result["dry_run"] is True
    assert result["extracted_id"] == "dry-run-simulation"

    # Verify no database write was called
    mock_db.extractedlisting.create.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_prevents_failed_extraction_recording():
    """Test that --dry-run prevents recording failed extractions."""
    # Setup mock data
    mock_raw = MagicMock()
    mock_raw.id = "raw-1"
    mock_raw.source = "google_places"
    mock_raw.file_path = "test.json"
    mock_raw.status = "success"

    # Invalid data that will cause extraction to fail
    mock_data = {"invalid": "data"}

    # Setup mock database
    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.failedextraction.create = AsyncMock()

    # Mock the record_failed_extraction function
    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        with patch("engine.extraction.run.record_failed_extraction", AsyncMock()) as mock_record_failed:
            # Run extraction with dry_run=True (should fail but not record failure)
            result = await run_single_extraction(
                mock_db,
                raw_id="raw-1",
                verbose=False,
                dry_run=True,
            )

    # Should fail
    assert result["status"] == "error"
    assert result["dry_run"] is True

    # Verify failed extraction was not recorded
    mock_record_failed.assert_not_called()


@pytest.mark.asyncio
async def test_all_flags_together():
    """Test using --limit, --dry-run, and --force-retry together."""
    # Create multiple mock raw records
    mock_raws = []
    for i in range(5):
        mock_raw = MagicMock()
        mock_raw.id = f"raw-{i}"
        mock_raw.source = "google_places"
        mock_raw.file_path = f"test{i}.json"
        mock_raw.status = "success"
        mock_raws.append(mock_raw)

    mock_existing = MagicMock()
    mock_existing.id = "extracted-old"

    mock_data = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    # Setup mock database
    mock_db = AsyncMock()
    # limit=2 means only 2 records returned
    mock_db.rawingestion.find_many = AsyncMock(return_value=mock_raws[:2])
    # force_retry=True means this check is skipped, but still returns existing
    mock_db.extractedlisting.find_first = AsyncMock(return_value=mock_existing)
    mock_db.extractedlisting.create = AsyncMock()

    with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        # Run with all flags
        result = await run_source_extraction(
            mock_db,
            source="google_places",
            limit=2,
            dry_run=True,
            force_retry=True,
        )

    # Verify behavior
    assert result["status"] == "success"
    assert result["dry_run"] is True
    assert result["total_records"] == 2  # Limited by limit flag
    assert result["successful"] == 2  # force_retry means all processed
    assert result["already_extracted"] == 0  # force_retry bypasses check

    # Verify no database write was called (dry_run)
    mock_db.extractedlisting.create.assert_not_called()
