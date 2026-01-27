"""
Tests for orchestration extraction integration.

Verifies the bridge between orchestration persistence and the extraction engine,
ensuring that unstructured sources trigger LLM extraction while structured sources
skip it for efficiency.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import json
from pathlib import Path

from engine.orchestration.extraction_integration import (
    needs_extraction,
    extract_entity,
)


class TestNeedsExtraction:
    """Test the needs_extraction logic for determining which sources require LLM extraction."""

    def test_structured_sources_skip_extraction(self):
        """
        Test that structured sources (with deterministic extractors) return False.

        These sources have well-defined APIs with structured responses:
        - google_places: JSON API with known schema
        - sport_scotland: GeoJSON with properties
        - edinburgh_council: Structured government API
        - open_charge_map: JSON API for EV charging stations

        No LLM extraction needed - data can be mapped deterministically.
        """
        assert needs_extraction("google_places") is False
        assert needs_extraction("sport_scotland") is False
        assert needs_extraction("edinburgh_council") is False
        assert needs_extraction("open_charge_map") is False

    def test_unstructured_sources_need_extraction(self):
        """
        Test that unstructured sources (requiring LLM) return True.

        These sources have unstructured or semi-structured data:
        - serper: Web search snippets (HTML fragments, varying formats)
        - openstreetmap: Free-form tags with no standard schema

        LLM extraction needed to parse and structure the data.
        """
        assert needs_extraction("serper") is True
        assert needs_extraction("openstreetmap") is True
        # Note: OSM has tags but they're highly variable - safer to use extraction

    def test_unknown_source_returns_true(self):
        """
        Test that unknown sources default to needs_extraction=True.

        Conservative approach: if we don't know the source, assume it needs extraction.
        This prevents data loss from skipping extraction when it's actually needed.
        """
        assert needs_extraction("unknown_source") is True
        assert needs_extraction("new_connector") is True


class TestExtractEntity:
    """Test the extract_entity function for invoking the extraction engine."""

    @pytest.mark.asyncio
    async def test_extract_entity_with_structured_source(self):
        """
        Test extraction of a structured source (google_places).

        Acceptance Criteria:
        - Loads RawIngestion record
        - Reads raw data from file_path
        - Gets appropriate extractor for source
        - Runs extraction pipeline (extract -> validate -> split_attributes)
        - Returns structured entity data
        """
        # Arrange: Mock database and file system
        mock_db = MagicMock()
        mock_raw_ingestion = MagicMock()
        mock_raw_ingestion.id = "raw_123"
        mock_raw_ingestion.source = "google_places"
        mock_raw_ingestion.file_path = "engine/data/raw/google_places/test.json"

        mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw_ingestion)

        # Mock raw data file
        raw_data = {
            "name": "Test Venue",
            "formatted_address": "123 Test St, Edinburgh",
            "geometry": {"location": {"lat": 55.9533, "lng": -3.1883}},
        }

        # Mock extractor
        mock_extractor = Mock()
        mock_extractor.extract = Mock(return_value={
            "name": "Test Venue",
            "address": "123 Test St, Edinburgh",
            "latitude": 55.9533,
            "longitude": -3.1883,
            "entity_class": "place",
        })
        mock_extractor.validate = Mock(return_value={
            "name": "Test Venue",
            "address": "123 Test St, Edinburgh",
            "latitude": 55.9533,
            "longitude": -3.1883,
            "entity_class": "place",
        })
        mock_extractor.split_attributes = Mock(return_value=(
            {
                "name": "Test Venue",
                "address": "123 Test St, Edinburgh",
                "latitude": 55.9533,
                "longitude": -3.1883,
            },
            {},  # No discovered attributes for structured source
        ))

        # Act: Extract entity
        with patch("engine.orchestration.extraction_integration.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.read_text = Mock(return_value=json.dumps(raw_data))
            mock_path_class.return_value = mock_path

            with patch("engine.orchestration.extraction_integration.get_extractor_for_source") as mock_get_extractor:
                mock_get_extractor.return_value = mock_extractor

                result = await extract_entity("raw_123", mock_db)

        # Assert: Verify extraction pipeline executed
        assert result["entity_class"] == "place"
        assert result["attributes"]["name"] == "Test Venue"
        assert result["attributes"]["latitude"] == 55.9533
        assert result["discovered_attributes"] == {}

        # Verify extractor methods called in correct order
        mock_extractor.extract.assert_called_once()
        mock_extractor.validate.assert_called_once()
        mock_extractor.split_attributes.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_entity_with_unstructured_source(self):
        """
        Test extraction of an unstructured source (serper).

        Acceptance Criteria:
        - Uses LLM-based extractor
        - Extracts entity_class from snippets
        - Splits into attributes and discovered_attributes
        - Handles model_used tracking
        """
        # Arrange: Mock database and file system
        mock_db = MagicMock()
        mock_raw_ingestion = MagicMock()
        mock_raw_ingestion.id = "raw_456"
        mock_raw_ingestion.source = "serper"
        mock_raw_ingestion.file_path = "engine/data/raw/serper/test.json"

        mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw_ingestion)

        # Mock raw data file (serper search result)
        raw_data = {
            "title": "Powerleague Portobello",
            "snippet": "5-a-side football facility in Edinburgh...",
            "link": "https://www.powerleague.co.uk/portobello",
        }

        # Mock LLM extractor
        mock_extractor = Mock()
        mock_extractor.extract = Mock(return_value={
            "name": "Powerleague Portobello",
            "snippet": "5-a-side football facility in Edinburgh...",
            "entity_class": "place",
            "model_used": "claude-3-haiku-20240307",
        })
        mock_extractor.validate = Mock(return_value={
            "name": "Powerleague Portobello",
            "snippet": "5-a-side football facility in Edinburgh...",
            "entity_class": "place",
            "model_used": "claude-3-haiku-20240307",
        })
        mock_extractor.split_attributes = Mock(return_value=(
            {
                "name": "Powerleague Portobello",
            },
            {
                "snippet": "5-a-side football facility in Edinburgh...",
            },
        ))

        # Act: Extract entity
        with patch("engine.orchestration.extraction_integration.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.read_text = Mock(return_value=json.dumps(raw_data))
            mock_path_class.return_value = mock_path

            with patch("engine.orchestration.extraction_integration.get_extractor_for_source") as mock_get_extractor:
                mock_get_extractor.return_value = mock_extractor

                result = await extract_entity("raw_456", mock_db)

        # Assert: Verify LLM extraction
        assert result["entity_class"] == "place"
        assert result["attributes"]["name"] == "Powerleague Portobello"
        assert "snippet" in result["discovered_attributes"]
        assert result["model_used"] == "claude-3-haiku-20240307"

    @pytest.mark.asyncio
    async def test_extract_entity_handles_missing_raw_ingestion(self):
        """
        Test error handling when RawIngestion record not found.

        Acceptance Criteria:
        - Raises ValueError with clear error message
        - Does not attempt to read file or run extraction
        """
        # Arrange: Mock database returning None
        mock_db = MagicMock()
        mock_db.rawingestion.find_unique = AsyncMock(return_value=None)

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="RawIngestion record not found: raw_999"):
            await extract_entity("raw_999", mock_db)

    @pytest.mark.asyncio
    async def test_extract_entity_handles_file_not_found(self):
        """
        Test error handling when raw data file doesn't exist.

        Acceptance Criteria:
        - Raises IOError with clear error message
        - Includes file path in error message
        """
        # Arrange: Mock database but file doesn't exist
        mock_db = MagicMock()
        mock_raw_ingestion = MagicMock()
        mock_raw_ingestion.id = "raw_789"
        mock_raw_ingestion.source = "google_places"
        mock_raw_ingestion.file_path = "engine/data/raw/google_places/missing.json"

        mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw_ingestion)

        # Act & Assert: Should raise IOError
        with patch("engine.orchestration.extraction_integration.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.read_text = Mock(side_effect=FileNotFoundError("File not found"))
            mock_path_class.return_value = mock_path

            with pytest.raises(IOError, match="Failed to load raw data from"):
                await extract_entity("raw_789", mock_db)

    @pytest.mark.asyncio
    async def test_extract_entity_handles_extraction_failure(self):
        """
        Test error handling when extractor raises exception.

        Acceptance Criteria:
        - Catches extractor exceptions
        - Re-raises with context about which source failed
        - Preserves original error message
        """
        # Arrange: Mock database and file system
        mock_db = MagicMock()
        mock_raw_ingestion = MagicMock()
        mock_raw_ingestion.id = "raw_error"
        mock_raw_ingestion.source = "serper"
        mock_raw_ingestion.file_path = "engine/data/raw/serper/bad.json"

        mock_db.rawingestion.find_unique = AsyncMock(return_value=mock_raw_ingestion)

        raw_data = {"malformed": "data"}

        # Mock extractor that fails
        mock_extractor = Mock()
        mock_extractor.extract = Mock(side_effect=Exception("Invalid data format"))

        # Act & Assert: Should raise exception with source context
        with patch("engine.orchestration.extraction_integration.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.read_text = Mock(return_value=json.dumps(raw_data))
            mock_path_class.return_value = mock_path

            with patch("engine.orchestration.extraction_integration.get_extractor_for_source") as mock_get_extractor:
                mock_get_extractor.return_value = mock_extractor

                with pytest.raises(Exception, match="Extraction failed for source serper"):
                    await extract_entity("raw_error", mock_db)
