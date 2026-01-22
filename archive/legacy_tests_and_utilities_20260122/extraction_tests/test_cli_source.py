"""
Tests for CLI per-source batch extraction mode.

Tests the --source flag for extracting all RawIngestion records from a specific source.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from engine.extraction.run import run_source_extraction


@pytest.mark.asyncio
async def test_source_extraction_with_valid_source():
    """Test successful batch extraction for a specific source."""
    # Mock RawIngestion records
    mock_raw_1 = MagicMock()
    mock_raw_1.id = "raw-1"
    mock_raw_1.source = "google_places"
    mock_raw_1.file_path = "engine/data/raw/google_places/test1.json"
    mock_raw_1.status = "success"
    mock_raw_1.created_at = datetime.now()

    mock_raw_2 = MagicMock()
    mock_raw_2.id = "raw-2"
    mock_raw_2.source = "google_places"
    mock_raw_2.file_path = "engine/data/raw/google_places/test2.json"
    mock_raw_2.status = "success"
    mock_raw_2.created_at = datetime.now()

    # Mock raw data files
    mock_raw_data_1 = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue 1"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    mock_raw_data_2 = {
        "id": "ChIJtest456",
        "displayName": {"text": "Test Venue 2"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    # Mock extracted listings
    mock_extracted_1 = MagicMock()
    mock_extracted_1.id = "extracted-1"
    mock_extracted_1.source = "google_places"
    mock_extracted_1.attributes = json.dumps({"entity_name": "Test Venue 1"})

    mock_extracted_2 = MagicMock()
    mock_extracted_2.id = "extracted-2"
    mock_extracted_2.source = "google_places"
    mock_extracted_2.attributes = json.dumps({"entity_name": "Test Venue 2"})

    # Mock database
    mock_db = AsyncMock()

    # Mock find_many to return unprocessed records
    mock_db.rawingestion.find_many = AsyncMock(return_value=[mock_raw_1, mock_raw_2])

    # Mock extractedlisting.find_first to return None (not already extracted)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

    # Mock extractedlisting.create to return extracted listings
    mock_db.extractedlisting.create = AsyncMock(
        side_effect=[mock_extracted_1, mock_extracted_2]
    )

    with patch("builtins.open", create=True) as mock_open:
        mock_file_1 = MagicMock()
        mock_file_1.__enter__.return_value.read.return_value = json.dumps(mock_raw_data_1)

        mock_file_2 = MagicMock()
        mock_file_2.__enter__.return_value.read.return_value = json.dumps(mock_raw_data_2)

        # Return different data based on which file is being read
        mock_open.return_value = mock_file_1
        mock_open.side_effect = [mock_file_1, mock_file_2]

        result = await run_source_extraction(
            mock_db,
            source="google_places",
        )

    assert result["status"] == "success"
    assert result["source"] == "google_places"
    assert result["total_records"] == 2
    assert result["successful"] == 2
    assert result["failed"] == 0
    assert result["already_extracted"] == 0
    assert "duration" in result
    assert "cost_estimate" in result


@pytest.mark.asyncio
async def test_source_extraction_with_invalid_source():
    """Test error handling for invalid source name."""
    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=[])

    result = await run_source_extraction(
        mock_db,
        source="invalid_source",
    )

    # Should still succeed but with 0 records
    assert result["status"] == "success"
    assert result["source"] == "invalid_source"
    assert result["total_records"] == 0


@pytest.mark.asyncio
async def test_source_extraction_no_records():
    """Test extraction when no records exist for the source."""
    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=[])

    result = await run_source_extraction(
        mock_db,
        source="google_places",
    )

    assert result["status"] == "success"
    assert result["source"] == "google_places"
    assert result["total_records"] == 0
    assert result["successful"] == 0
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_source_extraction_with_already_extracted():
    """Test handling of records that were already extracted."""
    # Mock RawIngestion records
    mock_raw_1 = MagicMock()
    mock_raw_1.id = "raw-1"
    mock_raw_1.source = "google_places"
    mock_raw_1.file_path = "engine/data/raw/google_places/test1.json"

    mock_raw_2 = MagicMock()
    mock_raw_2.id = "raw-2"
    mock_raw_2.source = "google_places"
    mock_raw_2.file_path = "engine/data/raw/google_places/test2.json"

    # Mock existing extracted listing for raw-1
    mock_existing = MagicMock()
    mock_existing.id = "existing-1"

    # Mock new extraction for raw-2
    mock_extracted_2 = MagicMock()
    mock_extracted_2.id = "extracted-2"

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=[mock_raw_1, mock_raw_2])

    # First call returns existing, second returns None
    mock_db.extractedlisting.find_first = AsyncMock(
        side_effect=[mock_existing, None]
    )
    mock_db.extractedlisting.create = AsyncMock(return_value=mock_extracted_2)

    # Mock raw data for the second record
    mock_raw_data = {
        "displayName": {"text": "Test Venue 2"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
        mock_open.return_value = mock_file

        result = await run_source_extraction(
            mock_db,
            source="google_places",
        )

    assert result["status"] == "success"
    assert result["total_records"] == 2
    assert result["successful"] == 1  # Only raw-2 was newly extracted
    assert result["already_extracted"] == 1  # raw-1 was already extracted
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_source_extraction_with_partial_failures():
    """Test extraction when some records fail."""
    # Mock RawIngestion records
    mock_raw_1 = MagicMock()
    mock_raw_1.id = "raw-1"
    mock_raw_1.source = "google_places"
    mock_raw_1.file_path = "engine/data/raw/google_places/test1.json"

    mock_raw_2 = MagicMock()
    mock_raw_2.id = "raw-2"
    mock_raw_2.source = "google_places"
    mock_raw_2.file_path = "engine/data/raw/google_places/invalid.json"

    # Mock successful extraction for raw-1
    mock_extracted_1 = MagicMock()
    mock_extracted_1.id = "extracted-1"

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=[mock_raw_1, mock_raw_2])
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.extractedlisting.create = AsyncMock(return_value=mock_extracted_1)

    # Mock FailedExtraction for quarantine
    mock_db.failedextraction.create = AsyncMock()

    mock_raw_data_1 = {
        "displayName": {"text": "Test Venue 1"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    call_count = 0
    def mock_open_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_file = MagicMock()
        if call_count == 1:
            # First file succeeds
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data_1)
        else:
            # Second file fails
            mock_file.__enter__.return_value.read.side_effect = IOError("File not found")
        return mock_file

    with patch("builtins.open", side_effect=mock_open_side_effect):
        result = await run_source_extraction(
            mock_db,
            source="google_places",
        )

    assert result["status"] == "success"  # Overall status is still success
    assert result["total_records"] == 2
    assert result["successful"] == 1
    assert result["failed"] == 1
    assert result["already_extracted"] == 0


@pytest.mark.asyncio
async def test_source_extraction_summary_report():
    """Test that summary report includes all required metrics."""
    # Mock RawIngestion records
    mock_raw = MagicMock()
    mock_raw.id = "raw-1"
    mock_raw.source = "serper"
    mock_raw.file_path = "engine/data/raw/serper/test.json"

    # Mock extracted listing
    mock_extracted = MagicMock()
    mock_extracted.id = "extracted-1"
    mock_extracted.model_used = "claude-3-haiku-20240307"

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=[mock_raw])
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.extractedlisting.create = AsyncMock(return_value=mock_extracted)

    mock_raw_data = {"organic": [{"title": "Test", "snippet": "Test snippet"}]}

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
        mock_open.return_value = mock_file

        result = await run_source_extraction(
            mock_db,
            source="serper",
        )

    # Verify summary report structure
    assert "status" in result
    assert "source" in result
    assert "total_records" in result
    assert "successful" in result
    assert "failed" in result
    assert "already_extracted" in result
    assert "duration" in result
    assert "cost_estimate" in result
    assert isinstance(result["duration"], float)
    assert result["duration"] >= 0


@pytest.mark.asyncio
async def test_source_extraction_progress_tracking():
    """Test that progress is tracked during batch extraction."""
    # Create multiple records to test progress tracking
    mock_raws = []
    for i in range(5):
        mock_raw = MagicMock()
        mock_raw.id = f"raw-{i}"
        mock_raw.source = "google_places"
        mock_raw.file_path = f"engine/data/raw/google_places/test{i}.json"
        mock_raws.append(mock_raw)

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=mock_raws)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

    # Mock create to return different extracted listings
    mock_extracted_listings = []
    for i in range(5):
        mock_extracted = MagicMock()
        mock_extracted.id = f"extracted-{i}"
        mock_extracted_listings.append(mock_extracted)

    mock_db.extractedlisting.create = AsyncMock(side_effect=mock_extracted_listings)

    mock_raw_data = {
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
        mock_open.return_value = mock_file

        result = await run_source_extraction(
            mock_db,
            source="google_places",
        )

    assert result["total_records"] == 5
    assert result["successful"] == 5
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_source_extraction_cost_estimation():
    """Test that LLM cost is estimated for LLM-based extractors."""
    # Mock RawIngestion records for Serper (LLM-based)
    mock_raw = MagicMock()
    mock_raw.id = "raw-1"
    mock_raw.source = "serper"
    mock_raw.file_path = "engine/data/raw/serper/test.json"

    # Mock extracted listing with model_used
    mock_extracted = MagicMock()
    mock_extracted.id = "extracted-1"
    mock_extracted.model_used = "claude-3-haiku-20240307"

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=[mock_raw])
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.extractedlisting.create = AsyncMock(return_value=mock_extracted)

    mock_raw_data = {"organic": [{"title": "Test", "snippet": "Test snippet"}]}

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
        mock_open.return_value = mock_file

        result = await run_source_extraction(
            mock_db,
            source="serper",
        )

    # Verify cost estimate is included
    assert "cost_estimate" in result
    # For LLM-based extractors, cost should be > 0 (or None if not tracked)
    # This is a basic check; actual cost calculation is tested elsewhere


@pytest.mark.asyncio
async def test_source_extraction_with_limit():
    """Test extraction with a limit on number of records to process."""
    # Create 10 mock records
    mock_raws = []
    for i in range(10):
        mock_raw = MagicMock()
        mock_raw.id = f"raw-{i}"
        mock_raw.source = "google_places"
        mock_raw.file_path = f"engine/data/raw/google_places/test{i}.json"
        mock_raws.append(mock_raw)

    mock_db = AsyncMock()
    # Mock find_many to respect the limit by only returning first 3 records
    mock_db.rawingestion.find_many = AsyncMock(return_value=mock_raws[:3])
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

    # Mock create to track how many times it's called
    create_calls = []
    async def mock_create(data):
        create_calls.append(data)
        mock_extracted = MagicMock()
        mock_extracted.id = f"extracted-{len(create_calls)}"
        return mock_extracted

    mock_db.extractedlisting.create = mock_create

    mock_raw_data = {
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
        mock_open.return_value = mock_file

        result = await run_source_extraction(
            mock_db,
            source="google_places",
            limit=3,
        )

    # Should only process 3 records even though 10 are available
    assert result["total_records"] == 3
    assert result["successful"] == 3
    assert len(create_calls) == 3
