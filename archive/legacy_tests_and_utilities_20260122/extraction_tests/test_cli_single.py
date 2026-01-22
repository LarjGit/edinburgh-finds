"""
Tests for CLI single record extraction mode.

Tests the --raw-id flag for extracting and displaying a single RawIngestion record.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from engine.extraction.run import run_single_extraction


@pytest.mark.asyncio
async def test_single_extraction_with_valid_id():
    """Test successful single record extraction with verbose output."""
    # Mock RawIngestion record
    mock_raw = MagicMock()
    mock_raw.id = "test-raw-id-123"
    mock_raw.source = "google_places"
    mock_raw.file_path = "engine/data/raw/google_places/test.json"
    mock_raw.status = "success"
    mock_raw.ingested_at = "2026-01-17T00:00:00Z"

    # Mock raw data file
    mock_raw_data = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue"},
        "formattedAddress": "123 Test St, Edinburgh, EH1 1AA, UK",
        "location": {"latitude": 55.953251, "longitude": -3.188267},
        "internationalPhoneNumber": "+44 131 123 4567",
    }

    # Mock extracted listing
    mock_extracted = MagicMock()
    mock_extracted.id = "extracted-123"
    mock_extracted.source = "google_places"
    mock_extracted.entity_type = "VENUE"
    mock_extracted.attributes = json.dumps({
        "entity_name": "Test Venue",
        "street_address": "123 Test St, Edinburgh, EH1 1AA, UK",
        "latitude": 55.953251,
        "longitude": -3.188267,
        "phone": "+441311234567",
    })
    mock_extracted.discovered_attributes = json.dumps({})
    mock_extracted.external_ids = json.dumps({"google_place_id": "ChIJtest123"})

    # Mock database
    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)  # Not extracted yet
    mock_db.extractedlisting.create = AsyncMock(return_value=mock_extracted)

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
        mock_open.return_value = mock_file

        result = await run_single_extraction(
            mock_db,
            raw_id="test-raw-id-123",
            verbose=True,
        )

    assert result["status"] == "success"
    assert result["raw_id"] == "test-raw-id-123"
    assert result["source"] == "google_places"
    assert result["extracted_id"] == "extracted-123"
    assert "entity_name" in result["fields"]
    assert result["fields"]["entity_name"] == "Test Venue"


@pytest.mark.asyncio
async def test_single_extraction_raw_id_not_found():
    """Test error handling when raw_id doesn't exist."""
    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=None)

    result = await run_single_extraction(
        mock_db,
        raw_id="nonexistent-id",
        verbose=True,
    )

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_single_extraction_already_extracted():
    """Test handling of already-extracted record."""
    # Mock RawIngestion record
    mock_raw = MagicMock()
    mock_raw.id = "test-raw-id-123"
    mock_raw.source = "google_places"

    # Mock existing extracted listing
    mock_existing = MagicMock()
    mock_existing.id = "existing-extracted-123"
    mock_existing.attributes = json.dumps({"entity_name": "Existing Venue"})
    mock_existing.discovered_attributes = json.dumps({"extra_field": "value"})

    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=mock_existing)

    result = await run_single_extraction(
        mock_db,
        raw_id="test-raw-id-123",
        verbose=True,
    )

    assert result["status"] == "already_extracted"
    assert result["extracted_id"] == "existing-extracted-123"
    assert result["fields"]["entity_name"] == "Existing Venue"
    assert result["discovered"]["extra_field"] == "value"


@pytest.mark.asyncio
async def test_single_extraction_with_extraction_error():
    """Test error handling when extraction fails."""
    # Mock RawIngestion record
    mock_raw = MagicMock()
    mock_raw.id = "test-raw-id-123"
    mock_raw.source = "google_places"
    mock_raw.file_path = "engine/data/raw/google_places/test.json"

    # Mock raw data file with invalid content
    mock_raw_data = {"invalid": "data"}

    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
        mock_open.return_value = mock_file

        # Extractor will raise an exception
        with patch("engine.extraction.run.get_extractor_for_source") as mock_get_extractor:
            mock_extractor = MagicMock()
            mock_extractor.extract.side_effect = ValueError("Invalid data format")
            mock_get_extractor.return_value = mock_extractor

            result = await run_single_extraction(
                mock_db,
                raw_id="test-raw-id-123",
                verbose=True,
            )

    assert result["status"] == "error"
    assert "extraction failed" in result["error"].lower()


@pytest.mark.asyncio
async def test_single_extraction_verbose_output_format():
    """Test that verbose mode outputs field-by-field details."""
    # Mock RawIngestion record
    mock_raw = MagicMock()
    mock_raw.id = "test-raw-id-123"
    mock_raw.source = "google_places"
    mock_raw.file_path = "engine/data/raw/google_places/test.json"

    # Mock raw data
    mock_raw_data = {
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

    # Create a variable to capture what was actually saved
    saved_data = {}

    async def mock_create(data):
        saved_data.update(data)
        mock_extracted = MagicMock()
        mock_extracted.id = "extracted-123"
        mock_extracted.attributes = data["attributes"]
        mock_extracted.discovered_attributes = data["discovered_attributes"]
        mock_extracted.external_ids = data["external_ids"]
        return mock_extracted

    mock_db.extractedlisting.create = mock_create

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
        mock_open.return_value = mock_file

        result = await run_single_extraction(
            mock_db,
            raw_id="test-raw-id-123",
            verbose=True,
        )

    # Verify verbose output includes field breakdown
    assert "fields" in result
    assert "discovered" in result
    # Google Places extractor doesn't produce discovered attributes from this simple data
    assert len(result["fields"]) >= 2  # At least entity_name and location fields


@pytest.mark.asyncio
async def test_single_extraction_non_verbose_mode():
    """Test that non-verbose mode outputs minimal summary."""
    # Mock RawIngestion record
    mock_raw = MagicMock()
    mock_raw.id = "test-raw-id-123"
    mock_raw.source = "google_places"
    mock_raw.file_path = "engine/data/raw/google_places/test.json"

    # Mock raw data
    mock_raw_data = {"displayName": {"text": "Test Venue"}}

    # Mock extracted listing
    mock_extracted = MagicMock()
    mock_extracted.id = "extracted-123"
    mock_extracted.attributes = json.dumps({"entity_name": "Test Venue"})

    mock_db = AsyncMock()
    mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.extractedlisting.create = AsyncMock(return_value=mock_extracted)

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_raw_data)
        mock_open.return_value = mock_file

        result = await run_single_extraction(
            mock_db,
            raw_id="test-raw-id-123",
            verbose=False,
        )

    assert result["status"] == "success"
    assert "extracted_id" in result
    # Non-verbose mode should not include detailed field breakdown
    assert "fields" not in result or result["fields"] is None
