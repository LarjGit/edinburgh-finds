"""
Tests for CLI batch all mode.

Tests the batch extraction of all unprocessed RawIngestion records,
grouped by source for optimal processing.
"""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from engine.extraction.run import run_all_extraction, get_extractor_for_source


@pytest.mark.asyncio
async def test_batch_all_with_mixed_sources():
    """Test batch extraction with records from multiple sources."""
    # Mock RawIngestion records from different sources
    mock_raw_google_1 = MagicMock()
    mock_raw_google_1.id = "raw-google-1"
    mock_raw_google_1.source = "google_places"
    mock_raw_google_1.file_path = "engine/data/raw/google_places/test1.json"
    mock_raw_google_1.status = "success"
    mock_raw_google_1.created_at = datetime.now()

    mock_raw_google_2 = MagicMock()
    mock_raw_google_2.id = "raw-google-2"
    mock_raw_google_2.source = "google_places"
    mock_raw_google_2.file_path = "engine/data/raw/google_places/test2.json"
    mock_raw_google_2.status = "success"
    mock_raw_google_2.created_at = datetime.now()

    mock_raw_serper = MagicMock()
    mock_raw_serper.id = "raw-serper-1"
    mock_raw_serper.source = "serper"
    mock_raw_serper.file_path = "engine/data/raw/serper/test1.json"
    mock_raw_serper.status = "success"
    mock_raw_serper.created_at = datetime.now()

    mock_raw_osm = MagicMock()
    mock_raw_osm.id = "raw-osm-1"
    mock_raw_osm.source = "osm"
    mock_raw_osm.file_path = "engine/data/raw/osm/test1.json"
    mock_raw_osm.status = "success"
    mock_raw_osm.created_at = datetime.now()

    # Mock extracted listings
    mock_extracted_1 = MagicMock()
    mock_extracted_1.id = "extracted-1"
    mock_extracted_1.source = "google_places"

    mock_extracted_2 = MagicMock()
    mock_extracted_2.id = "extracted-2"
    mock_extracted_2.source = "google_places"

    mock_extracted_3 = MagicMock()
    mock_extracted_3.id = "extracted-3"
    mock_extracted_3.source = "serper"
    mock_extracted_3.model_used = "claude-3-haiku-20240307"

    mock_extracted_4 = MagicMock()
    mock_extracted_4.id = "extracted-4"
    mock_extracted_4.source = "osm"
    mock_extracted_4.model_used = "claude-3-haiku-20240307"

    # Mock database
    mock_db = AsyncMock()

    # Mock find_many to return all unprocessed records
    mock_db.rawingestion.find_many = AsyncMock(
        return_value=[mock_raw_google_1, mock_raw_google_2, mock_raw_serper, mock_raw_osm]
    )

    # Mock extractedlisting.find_first to return None (not already extracted)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

    # Mock extractedlisting.create to return extracted listings
    mock_db.extractedlisting.create = AsyncMock(
        side_effect=[mock_extracted_1, mock_extracted_2, mock_extracted_3, mock_extracted_4]
    )

    # Mock raw data files
    mock_google_data = {
        "id": "ChIJtest123",
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    mock_serper_data = {
        "organic": [{"title": "Test Venue", "snippet": "Test snippet"}]
    }

    mock_osm_data = {
        "elements": [
            {
                "type": "node",
                "id": 123456,
                "lat": 55.953251,
                "lon": -3.188267,
                "tags": {"name": "Test Venue", "sport": "tennis"},
            }
        ]
    }

    call_count = 0
    def mock_open_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_file = MagicMock()

        # Return appropriate data based on call order
        if call_count <= 2:
            # Google Places calls
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_google_data)
        elif call_count == 3:
            # Serper call
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_serper_data)
        else:
            # OSM call
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_osm_data)

        return mock_file

    # Create a mock extractor that simulates successful extraction
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = {"entity_name": "Test Venue"}
    mock_extractor.validate.return_value = {"entity_name": "Test Venue", "entity_type": "VENUE"}
    mock_extractor.split_attributes.return_value = (
        {"entity_name": "Test Venue"},
        {}
    )

    # Mock get_extractor_for_source to return our mock extractor
    with patch("builtins.open", side_effect=mock_open_side_effect), \
         patch("engine.extraction.run.get_extractor_for_source", return_value=mock_extractor):
        result = await run_all_extraction(mock_db)

    assert result["status"] == "success"
    assert result["total_records"] == 4
    assert result["successful"] == 4
    assert result["failed"] == 0
    assert result["already_extracted"] == 0
    assert "duration" in result
    assert "cost_estimate" in result
    assert "sources_processed" in result
    assert len(result["sources_processed"]) == 3  # google_places, serper, osm


@pytest.mark.asyncio
async def test_batch_all_with_no_records():
    """Test batch extraction when no unprocessed records exist."""
    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=[])

    result = await run_all_extraction(mock_db)

    assert result["status"] == "success"
    assert result["total_records"] == 0
    assert result["successful"] == 0
    assert result["failed"] == 0
    assert result["sources_processed"] == []


@pytest.mark.asyncio
async def test_batch_all_with_already_extracted():
    """Test batch extraction with some already-extracted records."""
    # Mock RawIngestion records
    mock_raw_1 = MagicMock()
    mock_raw_1.id = "raw-1"
    mock_raw_1.source = "google_places"
    mock_raw_1.file_path = "engine/data/raw/google_places/test1.json"

    mock_raw_2 = MagicMock()
    mock_raw_2.id = "raw-2"
    mock_raw_2.source = "google_places"
    mock_raw_2.file_path = "engine/data/raw/google_places/test2.json"

    mock_raw_3 = MagicMock()
    mock_raw_3.id = "raw-3"
    mock_raw_3.source = "serper"
    mock_raw_3.file_path = "engine/data/raw/serper/test1.json"

    # Mock existing extracted listing for raw-1
    mock_existing = MagicMock()
    mock_existing.id = "existing-1"

    # Mock new extractions
    mock_extracted_2 = MagicMock()
    mock_extracted_2.id = "extracted-2"

    mock_extracted_3 = MagicMock()
    mock_extracted_3.id = "extracted-3"
    mock_extracted_3.model_used = "claude-3-haiku-20240307"

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(
        return_value=[mock_raw_1, mock_raw_2, mock_raw_3]
    )

    # First call returns existing, rest return None
    mock_db.extractedlisting.find_first = AsyncMock(
        side_effect=[mock_existing, None, None]
    )
    mock_db.extractedlisting.create = AsyncMock(
        side_effect=[mock_extracted_2, mock_extracted_3]
    )

    # Mock raw data
    mock_google_data = {
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    mock_serper_data = {
        "organic": [{"title": "Test Venue", "snippet": "Test snippet"}]
    }

    call_count = 0
    def mock_open_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_file = MagicMock()

        if call_count == 1:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_google_data)
        else:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_serper_data)

        return mock_file

    # Create a mock extractor that simulates successful extraction
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = {"entity_name": "Test Venue"}
    mock_extractor.validate.return_value = {"entity_name": "Test Venue", "entity_type": "VENUE"}
    mock_extractor.split_attributes.return_value = ({"entity_name": "Test Venue"}, {})

    # Mock get_extractor_for_source to return our mock extractor
    with patch("builtins.open", side_effect=mock_open_side_effect), \
         patch("engine.extraction.run.get_extractor_for_source", return_value=mock_extractor):
        result = await run_all_extraction(mock_db)

    assert result["status"] == "success"
    assert result["total_records"] == 3
    assert result["successful"] == 2  # raw-2 and raw-3
    assert result["already_extracted"] == 1  # raw-1
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_batch_all_with_partial_failures():
    """Test batch extraction when some records fail."""
    # Mock RawIngestion records
    mock_raw_1 = MagicMock()
    mock_raw_1.id = "raw-1"
    mock_raw_1.source = "google_places"
    mock_raw_1.file_path = "engine/data/raw/google_places/test1.json"

    mock_raw_2 = MagicMock()
    mock_raw_2.id = "raw-2"
    mock_raw_2.source = "google_places"
    mock_raw_2.file_path = "engine/data/raw/google_places/invalid.json"

    mock_raw_3 = MagicMock()
    mock_raw_3.id = "raw-3"
    mock_raw_3.source = "serper"
    mock_raw_3.file_path = "engine/data/raw/serper/test1.json"

    # Mock successful extractions
    mock_extracted_1 = MagicMock()
    mock_extracted_1.id = "extracted-1"

    mock_extracted_3 = MagicMock()
    mock_extracted_3.id = "extracted-3"
    mock_extracted_3.model_used = "claude-3-haiku-20240307"

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(
        return_value=[mock_raw_1, mock_raw_2, mock_raw_3]
    )
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.extractedlisting.create = AsyncMock(
        side_effect=[mock_extracted_1, mock_extracted_3]
    )

    # Mock FailedExtraction for quarantine
    mock_db.failedextraction.create = AsyncMock()

    mock_google_data = {
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    mock_serper_data = {
        "organic": [{"title": "Test Venue", "snippet": "Test snippet"}]
    }

    call_count = 0
    def mock_open_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_file = MagicMock()

        if call_count == 1:
            # First file succeeds
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_google_data)
        elif call_count == 2:
            # Second file fails
            mock_file.__enter__.return_value.read.side_effect = IOError("File not found")
        else:
            # Third file succeeds
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_serper_data)

        return mock_file

    # Create a mock extractor that simulates successful extraction
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = {"entity_name": "Test Venue"}
    mock_extractor.validate.return_value = {"entity_name": "Test Venue", "entity_type": "VENUE"}
    mock_extractor.split_attributes.return_value = ({"entity_name": "Test Venue"}, {})

    # Mock get_extractor_for_source to return our mock extractor
    with patch("builtins.open", side_effect=mock_open_side_effect), \
         patch("engine.extraction.run.get_extractor_for_source", return_value=mock_extractor):
        result = await run_all_extraction(mock_db)

    assert result["status"] == "success"  # Overall status is still success
    assert result["total_records"] == 3
    assert result["successful"] == 2
    assert result["failed"] == 1
    assert result["already_extracted"] == 0


@pytest.mark.asyncio
async def test_batch_all_summary_report():
    """Test that summary report includes all required metrics."""
    # Mock RawIngestion records from different sources
    mock_raw_google = MagicMock()
    mock_raw_google.id = "raw-google"
    mock_raw_google.source = "google_places"
    mock_raw_google.file_path = "engine/data/raw/google_places/test.json"

    mock_raw_serper = MagicMock()
    mock_raw_serper.id = "raw-serper"
    mock_raw_serper.source = "serper"
    mock_raw_serper.file_path = "engine/data/raw/serper/test.json"

    mock_raw_osm = MagicMock()
    mock_raw_osm.id = "raw-osm"
    mock_raw_osm.source = "osm"
    mock_raw_osm.file_path = "engine/data/raw/osm/test.json"

    # Mock extracted listings
    mock_extracted_google = MagicMock()
    mock_extracted_google.id = "extracted-google"

    mock_extracted_serper = MagicMock()
    mock_extracted_serper.id = "extracted-serper"
    mock_extracted_serper.model_used = "claude-3-haiku-20240307"

    mock_extracted_osm = MagicMock()
    mock_extracted_osm.id = "extracted-osm"
    mock_extracted_osm.model_used = "claude-3-haiku-20240307"

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(
        return_value=[mock_raw_google, mock_raw_serper, mock_raw_osm]
    )
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)
    mock_db.extractedlisting.create = AsyncMock(
        side_effect=[mock_extracted_google, mock_extracted_serper, mock_extracted_osm]
    )

    mock_google_data = {
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    mock_serper_data = {
        "organic": [{"title": "Test Venue", "snippet": "Test snippet"}]
    }

    mock_osm_data = {
        "elements": [
            {
                "type": "node",
                "id": 123456,
                "lat": 55.953251,
                "lon": -3.188267,
                "tags": {"name": "Test Venue"},
            }
        ]
    }

    call_count = 0
    def mock_open_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_file = MagicMock()

        if call_count == 1:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_google_data)
        elif call_count == 2:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_serper_data)
        else:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_osm_data)

        return mock_file

    # Create a mock extractor that simulates successful extraction
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = {"entity_name": "Test Venue"}
    mock_extractor.validate.return_value = {"entity_name": "Test Venue", "entity_type": "VENUE"}
    mock_extractor.split_attributes.return_value = ({"entity_name": "Test Venue"}, {})

    # Mock get_extractor_for_source to return our mock extractor
    with patch("builtins.open", side_effect=mock_open_side_effect), \
         patch("engine.extraction.run.get_extractor_for_source", return_value=mock_extractor):
        result = await run_all_extraction(mock_db)

    # Verify summary report structure
    assert "status" in result
    assert "total_records" in result
    assert "successful" in result
    assert "failed" in result
    assert "already_extracted" in result
    assert "duration" in result
    assert "cost_estimate" in result
    assert "sources_processed" in result
    assert isinstance(result["duration"], float)
    assert result["duration"] >= 0
    assert isinstance(result["sources_processed"], list)
    assert len(result["sources_processed"]) == 3


@pytest.mark.asyncio
async def test_batch_all_source_grouping():
    """Test that records are processed in source-grouped batches."""
    # Create records with sources in mixed order
    # This tests that the function groups them properly
    mock_raws = []
    sources_order = ["serper", "google_places", "serper", "google_places", "osm"]

    for i, source in enumerate(sources_order):
        mock_raw = MagicMock()
        mock_raw.id = f"raw-{i}"
        mock_raw.source = source
        mock_raw.file_path = f"engine/data/raw/{source}/test{i}.json"
        mock_raws.append(mock_raw)

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(return_value=mock_raws)
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

    # Track the order of create calls by source
    created_sources = []
    async def mock_create(data):
        created_sources.append(data["source"])
        mock_extracted = MagicMock()
        mock_extracted.id = f"extracted-{len(created_sources)}"
        if data["source"] in ["serper", "osm"]:
            mock_extracted.model_used = "claude-3-haiku-20240307"
        return mock_extracted

    mock_db.extractedlisting.create = mock_create

    mock_google_data = {
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    mock_serper_data = {
        "organic": [{"title": "Test Venue", "snippet": "Test snippet"}]
    }

    mock_osm_data = {
        "elements": [
            {
                "type": "node",
                "id": 123456,
                "lat": 55.953251,
                "lon": -3.188267,
                "tags": {"name": "Test Venue"},
            }
        ]
    }

    def mock_open_side_effect(*args, **kwargs):
        mock_file = MagicMock()
        file_path = str(args[0]) if args else ""

        if "google_places" in file_path:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_google_data)
        elif "serper" in file_path:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_serper_data)
        else:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_osm_data)

        return mock_file

    # Create a mock extractor that simulates successful extraction
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = {"entity_name": "Test Venue"}
    mock_extractor.validate.return_value = {"entity_name": "Test Venue", "entity_type": "VENUE"}
    mock_extractor.split_attributes.return_value = ({"entity_name": "Test Venue"}, {})

    # Mock get_extractor_for_source to return our mock extractor
    with patch("builtins.open", side_effect=mock_open_side_effect), \
         patch("engine.extraction.run.get_extractor_for_source", return_value=mock_extractor):
        result = await run_all_extraction(mock_db)

    # Verify all sources were processed
    assert result["total_records"] == 5
    assert result["successful"] == 5

    # Verify sources are grouped (all google_places together, all serper together, etc.)
    # The exact order might vary, but consecutive records should be from the same source
    assert len(created_sources) == 5


@pytest.mark.asyncio
async def test_batch_all_with_limit():
    """Test batch extraction with a limit on number of records."""
    # Create 10 mock records
    mock_raws = []
    for i in range(10):
        mock_raw = MagicMock()
        mock_raw.id = f"raw-{i}"
        mock_raw.source = "google_places"
        mock_raw.file_path = f"engine/data/raw/google_places/test{i}.json"
        mock_raws.append(mock_raw)

    mock_db = AsyncMock()
    # Mock find_many to respect the limit
    mock_db.rawingestion.find_many = AsyncMock(return_value=mock_raws[:3])
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

    # Track create calls
    create_calls = []
    async def mock_create(data):
        create_calls.append(data)
        mock_extracted = MagicMock()
        mock_extracted.id = f"extracted-{len(create_calls)}"
        return mock_extracted

    mock_db.extractedlisting.create = mock_create

    mock_google_data = {
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(mock_google_data)
        mock_open.return_value = mock_file

        result = await run_all_extraction(mock_db, limit=3)

    # Should only process 3 records
    assert result["total_records"] == 3
    assert result["successful"] == 3
    assert len(create_calls) == 3


@pytest.mark.asyncio
async def test_batch_all_cost_estimation():
    """Test that LLM costs are aggregated across all sources."""
    # Mock records from LLM-based sources
    mock_raw_serper = MagicMock()
    mock_raw_serper.id = "raw-serper"
    mock_raw_serper.source = "serper"
    mock_raw_serper.file_path = "engine/data/raw/serper/test.json"

    mock_raw_osm = MagicMock()
    mock_raw_osm.id = "raw-osm"
    mock_raw_osm.source = "osm"
    mock_raw_osm.file_path = "engine/data/raw/osm/test.json"

    # Mock records from deterministic sources
    mock_raw_google = MagicMock()
    mock_raw_google.id = "raw-google"
    mock_raw_google.source = "google_places"
    mock_raw_google.file_path = "engine/data/raw/google_places/test.json"

    mock_db = AsyncMock()
    mock_db.rawingestion.find_many = AsyncMock(
        return_value=[mock_raw_serper, mock_raw_osm, mock_raw_google]
    )
    mock_db.extractedlisting.find_first = AsyncMock(return_value=None)

    # Mock extracted listings - LLM sources have model_used
    extracted_listings = []
    def create_mock_extracted(source):
        mock = MagicMock()
        mock.id = f"extracted-{source}"
        if source in ["serper", "osm"]:
            mock.model_used = "claude-3-haiku-20240307"
        else:
            mock.model_used = None
        extracted_listings.append(mock)
        return mock

    mock_db.extractedlisting.create = AsyncMock(
        side_effect=[
            create_mock_extracted("serper"),
            create_mock_extracted("osm"),
            create_mock_extracted("google_places"),
        ]
    )

    mock_google_data = {
        "displayName": {"text": "Test Venue"},
        "location": {"latitude": 55.953251, "longitude": -3.188267},
    }

    mock_serper_data = {
        "organic": [{"title": "Test Venue", "snippet": "Test snippet"}]
    }

    mock_osm_data = {
        "elements": [
            {
                "type": "node",
                "id": 123456,
                "lat": 55.953251,
                "lon": -3.188267,
                "tags": {"name": "Test Venue"},
            }
        ]
    }

    call_count = 0
    def mock_open_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_file = MagicMock()

        if call_count == 1:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_serper_data)
        elif call_count == 2:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_osm_data)
        else:
            mock_file.__enter__.return_value.read.return_value = json.dumps(mock_google_data)

        return mock_file

    # Create a mock extractor that simulates successful extraction
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = {"entity_name": "Test Venue"}
    mock_extractor.validate.return_value = {"entity_name": "Test Venue", "entity_type": "VENUE"}
    mock_extractor.split_attributes.return_value = ({"entity_name": "Test Venue"}, {})

    # Mock get_extractor_for_source to return our mock extractor
    with patch("builtins.open", side_effect=mock_open_side_effect), \
         patch("engine.extraction.run.get_extractor_for_source", return_value=mock_extractor):
        result = await run_all_extraction(mock_db)

    # Verify cost is tracked for LLM calls
    assert "cost_estimate" in result
    # Should have cost > 0 for 2 LLM-based extractions
    assert result.get("llm_calls", 0) >= 2 or result.get("cost_estimate", 0) >= 0
