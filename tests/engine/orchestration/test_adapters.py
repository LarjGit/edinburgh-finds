"""
Tests for Connector Adapter Layer.

Validates:
- normalize_for_json function for JSON serialization
- ConnectorAdapter initialization
- _extract_items method for different connector formats
- _map_to_candidate method for canonical schema mapping
- execute method with error handling
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from engine.orchestration.adapters import ConnectorAdapter, normalize_for_json
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.ingestion.base import BaseConnector


class TestNormalizeForJson:
    """Test JSON normalization function."""

    def test_normalizes_datetime_to_iso_string(self):
        """datetime objects should be converted to ISO format strings."""
        dt = datetime(2024, 1, 15, 14, 30, 0)
        result = normalize_for_json(dt)

        assert isinstance(result, str)
        assert result == "2024-01-15T14:30:00"

    def test_normalizes_decimal_to_float(self):
        """Decimal objects should be converted to float."""
        decimal_val = Decimal("123.45")
        result = normalize_for_json(decimal_val)

        assert isinstance(result, float)
        assert result == 123.45

    def test_normalizes_set_to_sorted_list(self):
        """Sets should be converted to deterministic sorted lists."""
        set_val = {3, 1, 2}
        result = normalize_for_json(set_val)

        assert isinstance(result, list)
        assert result == [1, 2, 3]  # Sorted

    def test_normalizes_tuple_to_list(self):
        """Tuples should be converted to lists."""
        tuple_val = (1, 2, 3)
        result = normalize_for_json(tuple_val)

        assert isinstance(result, list)
        assert result == [1, 2, 3]

    def test_preserves_primitive_types(self):
        """Primitive types should pass through unchanged."""
        assert normalize_for_json("string") == "string"
        assert normalize_for_json(42) == 42
        assert normalize_for_json(3.14) == 3.14
        assert normalize_for_json(True) is True
        assert normalize_for_json(None) is None

    def test_normalizes_nested_dict(self):
        """Should recursively normalize nested dictionaries."""
        data = {"timestamp": datetime(2024, 1, 15), "count": Decimal("10.5")}
        result = normalize_for_json(data)

        assert result["timestamp"] == "2024-01-15T00:00:00"
        assert result["count"] == 10.5

    def test_normalizes_nested_list(self):
        """Should recursively normalize nested lists."""
        data = [datetime(2024, 1, 15), Decimal("99.99"), {1, 2, 3}]
        result = normalize_for_json(data)

        assert result[0] == "2024-01-15T00:00:00"
        assert result[1] == 99.99
        assert result[2] == [1, 2, 3]

    def test_normalizes_complex_nested_structure(self):
        """Should handle deeply nested structures."""
        data = {
            "metadata": {
                "created": datetime(2024, 1, 15),
                "tags": {"python", "testing"},
                "stats": {"price": Decimal("49.99")},
            },
            "items": [{"id": 1, "timestamp": datetime(2024, 1, 16)}],
        }
        result = normalize_for_json(data)

        assert result["metadata"]["created"] == "2024-01-15T00:00:00"
        assert result["metadata"]["tags"] == ["python", "testing"]
        assert result["metadata"]["stats"]["price"] == 49.99
        assert result["items"][0]["timestamp"] == "2024-01-16T00:00:00"

    def test_custom_object_fallback_to_string(self):
        """Custom objects should fallback to str() representation."""

        class CustomObject:
            def __str__(self):
                return "custom_repr"

        result = normalize_for_json(CustomObject())
        assert result == "custom_repr"


class TestConnectorAdapterInitialization:
    """Test ConnectorAdapter initialization."""

    def test_adapter_stores_connector_and_spec(self):
        """Adapter should store connector and spec references."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "test"

        spec = ConnectorSpec(
            name="test",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=80,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        assert adapter.connector is mock_connector
        assert adapter.spec is spec


class TestExtractItems:
    """Test _extract_items method for different connector response formats."""

    def setup_method(self):
        """Create test adapter for each test."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "test"

        spec = ConnectorSpec(
            name="test",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=80,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        self.adapter = ConnectorAdapter(mock_connector, spec)

    def test_extracts_serper_organic_results(self):
        """Should extract items from Serper organic results format."""
        results = {"organic": [{"title": "Item 1"}, {"title": "Item 2"}]}

        items = self.adapter._extract_items(results)

        assert len(items) == 2
        assert items[0]["title"] == "Item 1"
        assert items[1]["title"] == "Item 2"

    def test_extracts_google_places_results(self):
        """Should extract items from Google Places results format (old API)."""
        results = {
            "results": [{"name": "Place 1", "place_id": "abc"}, {"name": "Place 2"}]
        }

        items = self.adapter._extract_items(results)

        assert len(items) == 2
        assert items[0]["name"] == "Place 1"
        assert items[1]["name"] == "Place 2"

    def test_extracts_google_places_new_api(self):
        """Should extract items from Google Places API v1 'places' format."""
        results = {
            "places": [
                {"displayName": {"text": "Place 1"}, "id": "abc"},
                {"displayName": {"text": "Place 2"}, "id": "def"},
            ]
        }

        items = self.adapter._extract_items(results)

        assert len(items) == 2
        assert items[0]["displayName"]["text"] == "Place 1"
        assert items[1]["displayName"]["text"] == "Place 2"

    def test_extracts_osm_elements(self):
        """Should extract items from OpenStreetMap elements format."""
        results = {"elements": [{"id": 1, "tags": {}}, {"id": 2, "tags": {}}]}

        items = self.adapter._extract_items(results)

        assert len(items) == 2
        assert items[0]["id"] == 1
        assert items[1]["id"] == 2

    def test_extracts_sport_scotland_features(self):
        """Should extract items from SportScotland GeoJSON features format."""
        results = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"name": "Court 1"}},
                {"type": "Feature", "properties": {"name": "Court 2"}},
            ],
        }

        items = self.adapter._extract_items(results)

        assert len(items) == 2
        assert items[0]["properties"]["name"] == "Court 1"
        assert items[1]["properties"]["name"] == "Court 2"

    def test_handles_list_response(self):
        """Should handle response that is directly a list."""
        results = [{"item": 1}, {"item": 2}]

        items = self.adapter._extract_items(results)

        assert len(items) == 2
        assert items[0]["item"] == 1

    def test_returns_empty_list_for_no_results(self):
        """Should return empty list when no results found."""
        results = {"other_field": "value"}

        items = self.adapter._extract_items(results)

        assert items == []

    def test_returns_empty_list_for_empty_organic(self):
        """Should handle empty organic results."""
        results = {"organic": []}

        items = self.adapter._extract_items(results)

        assert items == []


class TestMapToCandidate:
    """Test _map_to_candidate method for canonical schema mapping."""

    def test_maps_serper_result(self):
        """Should map Serper result to canonical candidate schema."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "serper"

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=75,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        raw_item = {"title": "Tennis Club Edinburgh", "link": "https://example.com"}

        candidate = adapter._map_to_candidate(raw_item)

        assert candidate["name"] == "Tennis Club Edinburgh"
        assert candidate["source"] == "serper"
        assert candidate["ids"] == {}  # Serper has no strong IDs
        assert candidate["lat"] is None
        assert candidate["lng"] is None
        assert "raw" in candidate

    def test_maps_google_places_result(self):
        """Should map Google Places result to canonical candidate schema (old API)."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "google_places"

        spec = ConnectorSpec(
            name="google_places",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=95,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.017,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        raw_item = {
            "name": "Powerleague Portobello",
            "place_id": "ChIJXYZ123",
            "geometry": {"location": {"lat": 55.9533, "lng": -3.1883}},
            "formatted_address": "123 Street, Edinburgh",
        }

        candidate = adapter._map_to_candidate(raw_item)

        assert candidate["name"] == "Powerleague Portobello"
        assert candidate["source"] == "google_places"
        assert candidate["ids"] == {"google": "ChIJXYZ123"}
        assert candidate["lat"] == 55.9533
        assert candidate["lng"] == -3.1883
        assert candidate["address"] == "123 Street, Edinburgh"
        assert "raw" in candidate

    def test_maps_google_places_new_api_result(self):
        """Should map Google Places API v1 result to canonical candidate schema."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "google_places"

        spec = ConnectorSpec(
            name="google_places",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=95,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.017,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        raw_item = {
            "displayName": {"text": "Powerleague Portobello"},
            "id": "ChIJXYZ123",
            "location": {"latitude": 55.9533, "longitude": -3.1883},
            "formattedAddress": "123 Street, Edinburgh",
        }

        candidate = adapter._map_to_candidate(raw_item)

        assert candidate["name"] == "Powerleague Portobello"
        assert candidate["source"] == "google_places"
        assert candidate["ids"] == {"google": "ChIJXYZ123"}
        assert candidate["lat"] == 55.9533
        assert candidate["lng"] == -3.1883
        assert candidate["address"] == "123 Street, Edinburgh"
        assert "raw" in candidate

    def test_serper_raises_key_error_if_title_missing(self):
        """Serper mapping should raise KeyError if title field missing."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "serper"

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=75,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        raw_item = {"link": "https://example.com"}  # Missing title

        with pytest.raises(KeyError):
            adapter._map_to_candidate(raw_item)

    def test_google_places_handles_missing_optional_fields(self):
        """Google Places mapping should handle missing optional fields gracefully."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "google_places"

        spec = ConnectorSpec(
            name="google_places",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=95,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.017,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        raw_item = {"name": "Simple Place"}  # Missing optional fields

        candidate = adapter._map_to_candidate(raw_item)

        assert candidate["name"] == "Simple Place"
        assert candidate["ids"] == {}
        assert candidate["lat"] is None
        assert candidate["lng"] is None
        assert "address" not in candidate

    def test_normalizes_raw_payload(self):
        """Should normalize raw payload for JSON serialization."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "serper"

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=75,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        raw_item = {
            "title": "Test",
            "timestamp": datetime(2024, 1, 15),
            "price": Decimal("99.99"),
        }

        candidate = adapter._map_to_candidate(raw_item)

        # Raw payload should be normalized
        assert candidate["raw"]["timestamp"] == "2024-01-15T00:00:00"
        assert candidate["raw"]["price"] == 99.99

    def test_maps_openstreetmap_result(self):
        """Should map OpenStreetMap result to canonical candidate schema."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "openstreetmap"

        spec = ConnectorSpec(
            name="openstreetmap",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=70,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.0,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        raw_item = {
            "id": 123456789,
            "type": "node",
            "lat": 55.9533,
            "lon": -3.1883,
            "tags": {"name": "Edinburgh Tennis Centre", "sport": "tennis"},
        }

        candidate = adapter._map_to_candidate(raw_item)

        assert candidate["name"] == "Edinburgh Tennis Centre"
        assert candidate["source"] == "openstreetmap"
        assert candidate["ids"] == {"osm": "node/123456789"}
        assert candidate["lat"] == 55.9533
        assert candidate["lng"] == -3.1883
        assert "raw" in candidate

    def test_maps_sport_scotland_result(self):
        """Should map SportScotland GeoJSON feature to canonical candidate schema."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "sport_scotland"

        spec = ConnectorSpec(
            name="sport_scotland",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=90,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.0,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        raw_item = {
            "type": "Feature",
            "id": "tennis_courts.123",
            "properties": {
                "name": "Craiglockhart Tennis Centre",
                "facility_type": "tennis",
            },
            "geometry": {"type": "Point", "coordinates": [-3.1883, 55.9533]},
        }

        candidate = adapter._map_to_candidate(raw_item)

        assert candidate["name"] == "Craiglockhart Tennis Centre"
        assert candidate["source"] == "sport_scotland"
        assert candidate["ids"] == {"sport_scotland": "tennis_courts.123"}
        assert candidate["lat"] == 55.9533
        assert candidate["lng"] == -3.1883
        assert "raw" in candidate


class TestConnectorAdapterExecute:
    """Test execute method with async bridge and error handling."""

    def test_execute_calls_connector_fetch_via_asyncio_run(self):
        """execute should call connector.fetch() via asyncio.run bridge."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "serper"

        # Mock async fetch method
        async def mock_fetch(query):
            return {"organic": [{"title": "Result 1"}]}

        mock_connector.fetch = AsyncMock(side_effect=mock_fetch)

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=75,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY, query="test query"
        )
        query_features = QueryFeatures.extract(query="test query", request=request)
        context = ExecutionContext()

        adapter.execute(request, query_features, context)

        # Verify fetch was called with query
        mock_connector.fetch.assert_called_once_with("test query")

    def test_execute_adds_candidates_to_context(self):
        """execute should append mapped candidates to context.candidates."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "serper"

        async def mock_fetch(query):
            return {"organic": [{"title": "Result 1"}, {"title": "Result 2"}]}

        mock_connector.fetch = AsyncMock(side_effect=mock_fetch)

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=75,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY, query="test query"
        )
        query_features = QueryFeatures.extract(query="test query", request=request)
        context = ExecutionContext()

        adapter.execute(request, query_features, context)

        # Should have 2 candidates added
        assert len(context.candidates) == 2
        assert context.candidates[0]["name"] == "Result 1"
        assert context.candidates[1]["name"] == "Result 2"

    def test_execute_records_success_metrics(self):
        """execute should record success metrics in context.metrics."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "serper"

        async def mock_fetch(query):
            return {"organic": [{"title": "Result 1"}]}

        mock_connector.fetch = AsyncMock(side_effect=mock_fetch)

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=75,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY, query="test query"
        )
        query_features = QueryFeatures.extract(query="test query", request=request)
        context = ExecutionContext()

        adapter.execute(request, query_features, context)

        # Check metrics recorded
        assert "serper" in context.metrics
        metrics = context.metrics["serper"]
        assert metrics["executed"] is True
        assert metrics["items_received"] == 1
        assert metrics["candidates_added"] == 1
        assert metrics["mapping_failures"] == 0
        assert "execution_time_ms" in metrics
        assert metrics["cost_usd"] == 0.01

    def test_execute_handles_connector_error_gracefully(self):
        """execute should handle connector errors gracefully (non-fatal)."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "serper"

        async def mock_fetch(query):
            raise RuntimeError("API timeout")

        mock_connector.fetch = AsyncMock(side_effect=mock_fetch)

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=75,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY, query="test query"
        )
        query_features = QueryFeatures.extract(query="test query", request=request)
        context = ExecutionContext()

        # Should not raise exception
        adapter.execute(request, query_features, context)

        # Check error recorded
        assert len(context.errors) == 1
        error = context.errors[0]
        assert error["connector"] == "serper"
        assert "API timeout" in error["error"]

        # Check failure metrics
        assert "serper" in context.metrics
        metrics = context.metrics["serper"]
        assert metrics["executed"] is False
        assert "error" in metrics
        assert metrics["cost_usd"] == 0.0  # No cost on failure

    def test_execute_tracks_mapping_failures(self):
        """execute should track mapping failures without crashing."""
        mock_connector = Mock(spec=BaseConnector)
        mock_connector.source_name = "serper"

        async def mock_fetch(query):
            # Return results where some items are missing required fields
            return {
                "organic": [
                    {"title": "Good Result"},
                    {"link": "bad_result"},  # Missing title
                    {"title": "Another Good Result"},
                ]
            }

        mock_connector.fetch = AsyncMock(side_effect=mock_fetch)

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=75,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY, query="test query"
        )
        query_features = QueryFeatures.extract(query="test query", request=request)
        context = ExecutionContext()

        adapter.execute(request, query_features, context)

        # Should add only the 2 good results
        assert len(context.candidates) == 2
        assert context.candidates[0]["name"] == "Good Result"
        assert context.candidates[1]["name"] == "Another Good Result"

        # Metrics should track the failure
        metrics = context.metrics["serper"]
        assert metrics["items_received"] == 3
        assert metrics["candidates_added"] == 2
        assert metrics["mapping_failures"] == 1
