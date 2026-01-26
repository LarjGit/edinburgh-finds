"""
Tests for Connector Adapter Layer.

Validates that adapters correctly bridge the BaseConnector async interface
to the Orchestrator sync interface, including:
- Async→sync bridging with asyncio.run
- Canonical candidate schema mapping
- JSON normalization for raw payloads
- Error handling and metrics tracking
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from decimal import Decimal

from engine.orchestration.adapters import ConnectorAdapter, normalize_for_json
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.types import IngestRequest, IngestionMode


class TestJSONNormalization:
    """Test JSON normalization for raw payloads."""

    def test_normalize_dict_with_serializable_values(self):
        """Should pass through already-serializable dicts."""
        data = {"name": "Test", "count": 42, "active": True}
        result = normalize_for_json(data)
        assert result == data

    def test_normalize_datetime_to_string(self):
        """Should convert datetime to ISO string."""
        dt = datetime(2026, 1, 26, 10, 30, 0)
        data = {"timestamp": dt}
        result = normalize_for_json(data)
        assert result["timestamp"] == "2026-01-26T10:30:00"

    def test_normalize_decimal_to_float(self):
        """Should convert Decimal to float."""
        data = {"price": Decimal("19.99")}
        result = normalize_for_json(data)
        assert result["price"] == 19.99
        assert isinstance(result["price"], float)

    def test_normalize_set_to_sorted_list(self):
        """Should convert set to sorted list for determinism."""
        data = {"tags": {"tennis", "padel", "sports"}}
        result = normalize_for_json(data)
        assert result["tags"] == ["padel", "sports", "tennis"]

    def test_normalize_tuple_to_list(self):
        """Should convert tuple to list."""
        data = {"coords": (55.9532, -3.1234)}
        result = normalize_for_json(data)
        assert result["coords"] == [55.9532, -3.1234]

    def test_normalize_nested_structures(self):
        """Should recursively normalize nested structures."""
        data = {
            "meta": {
                "created": datetime(2026, 1, 26),
                "tags": {"a", "b"},
                "coords": (1, 2),
            }
        }
        result = normalize_for_json(data)
        assert result["meta"]["created"] == "2026-01-26T00:00:00"
        assert result["meta"]["tags"] == ["a", "b"]
        assert result["meta"]["coords"] == [1, 2]

    def test_normalize_list_preserves_order(self):
        """Should preserve list order while normalizing elements."""
        data = {"items": [{"ts": datetime(2026, 1, 26)}, {"ts": datetime(2026, 1, 25)}]}
        result = normalize_for_json(data)
        assert len(result["items"]) == 2
        assert result["items"][0]["ts"] == "2026-01-26T00:00:00"
        assert result["items"][1]["ts"] == "2026-01-25T00:00:00"


class TestConnectorAdapterMapping:
    """Test canonical candidate schema mapping."""

    def test_map_serper_result_to_candidate(self):
        """Should map Serper result (no IDs, no coords) to canonical schema."""
        raw_result = {
            "title": "Edinburgh Padel Club",
            "link": "https://edinburghpadel.com",
            "snippet": "Premier padel facility in Edinburgh...",
        }

        # Create mock connector
        mock_connector = Mock()
        mock_connector.source_name = "serper"

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)
        candidate = adapter._map_to_candidate(raw_result)

        # Verify canonical schema
        assert candidate["name"] == "Edinburgh Padel Club"
        assert candidate["ids"] == {}  # Serper has no strong IDs
        assert candidate["lat"] is None  # Serper has no coords
        assert candidate["lng"] is None
        assert candidate["source"] == "serper"
        assert "raw" in candidate
        assert candidate["raw"]["title"] == "Edinburgh Padel Club"

    def test_map_google_places_result_to_candidate(self):
        """Should map Google Places result (with IDs and coords) to canonical schema."""
        raw_result = {
            "place_id": "ChIJ123abc456def",
            "name": "Powerleague Portobello",
            "geometry": {"location": {"lat": 55.9532, "lng": -3.1234}},
            "formatted_address": "123 Portobello Rd, Edinburgh",
            "types": ["sports_club", "point_of_interest"],
        }

        mock_connector = Mock()
        mock_connector.source_name = "google_places"

        spec = ConnectorSpec(
            name="google_places",
            phase=ExecutionPhase.STRUCTURED,
            trust_level=9,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.02,
        )

        adapter = ConnectorAdapter(mock_connector, spec)
        candidate = adapter._map_to_candidate(raw_result)

        # Verify canonical schema with strong IDs and flat coords
        assert candidate["name"] == "Powerleague Portobello"
        assert candidate["ids"] == {"google": "ChIJ123abc456def"}
        assert candidate["lat"] == 55.9532
        assert candidate["lng"] == -3.1234
        assert candidate["source"] == "google_places"
        assert candidate["address"] == "123 Portobello Rd, Edinburgh"
        assert "raw" in candidate

    def test_handles_missing_optional_fields(self):
        """Should handle missing optional fields gracefully."""
        raw_result = {
            "place_id": "ChIJ123",
            "name": "Test Place",
            # No geometry, no address, no types
        }

        mock_connector = Mock()
        mock_connector.source_name = "google_places"

        spec = ConnectorSpec(
            name="google_places",
            phase=ExecutionPhase.STRUCTURED,
            trust_level=9,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.02,
        )

        adapter = ConnectorAdapter(mock_connector, spec)
        candidate = adapter._map_to_candidate(raw_result)

        assert candidate["name"] == "Test Place"
        assert candidate["ids"] == {"google": "ChIJ123"}
        assert candidate["lat"] is None
        assert candidate["lng"] is None
        assert candidate.get("address") is None


class TestConnectorAdapterExecution:
    """Test adapter execution and context updates."""

    def test_execute_calls_connector_fetch(self):
        """Should call connector.fetch() with query from request."""
        # Mock connector
        mock_connector = Mock()
        mock_connector.source_name = "serper"
        mock_connector.fetch = AsyncMock(
            return_value={
                "organic": [
                    {"title": "Result 1", "link": "http://example.com/1"},
                    {"title": "Result 2", "link": "http://example.com/2"},
                ]
            }
        )

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        # Create request and context
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts edinburgh",
        )
        query_features = QueryFeatures.extract("padel courts edinburgh", request)
        context = ExecutionContext()

        # Execute adapter
        adapter.execute(request, query_features, context)

        # Verify connector.fetch was called with query
        mock_connector.fetch.assert_called_once_with("padel courts edinburgh")

    def test_execute_adds_candidates_to_context(self):
        """Should add mapped candidates to context.candidates."""
        # Mock connector with 2 results
        mock_connector = Mock()
        mock_connector.source_name = "serper"
        mock_connector.fetch = AsyncMock(
            return_value={
                "organic": [
                    {"title": "Result 1", "link": "http://example.com/1"},
                    {"title": "Result 2", "link": "http://example.com/2"},
                ]
            }
        )

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY, query="test query"
        )
        query_features = QueryFeatures.extract("test query", request)
        context = ExecutionContext()

        # Execute
        adapter.execute(request, query_features, context)

        # Verify candidates added
        assert len(context.candidates) == 2
        assert context.candidates[0]["name"] == "Result 1"
        assert context.candidates[1]["name"] == "Result 2"

    def test_execute_records_metrics(self):
        """Should record execution metrics in context.metrics."""
        mock_connector = Mock()
        mock_connector.source_name = "serper"
        mock_connector.fetch = AsyncMock(
            return_value={
                "organic": [
                    {"title": "Result 1", "link": "http://example.com/1"},
                ]
            }
        )

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY, query="test"
        )
        query_features = QueryFeatures.extract("test", request)
        context = ExecutionContext()

        # Execute
        adapter.execute(request, query_features, context)

        # Verify metrics
        assert "serper" in context.metrics
        metrics = context.metrics["serper"]
        assert metrics["executed"] is True
        assert metrics["items_received"] == 1
        assert metrics["candidates_added"] == 1
        assert metrics["mapping_failures"] == 0
        assert "execution_time_ms" in metrics
        assert metrics["cost_usd"] == 0.01

    def test_execute_handles_connector_failure(self):
        """Should handle connector failure and record error."""
        mock_connector = Mock()
        mock_connector.source_name = "serper"
        mock_connector.fetch = AsyncMock(
            side_effect=Exception("API timeout")
        )

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY, query="test"
        )
        query_features = QueryFeatures.extract("test", request)
        context = ExecutionContext()

        # Execute (should not raise)
        adapter.execute(request, query_features, context)

        # Verify error recorded
        assert len(context.errors) == 1
        error = context.errors[0]
        assert error["connector"] == "serper"
        assert "API timeout" in error["error"]

        # Verify no candidates added
        assert len(context.candidates) == 0

    def test_execute_tracks_mapping_failures(self):
        """Should track items that fail mapping separately."""
        mock_connector = Mock()
        mock_connector.source_name = "serper"
        mock_connector.fetch = AsyncMock(
            return_value={
                "organic": [
                    {"title": "Valid Result", "link": "http://example.com/1"},
                    {"malformed": "no title field"},  # Will fail mapping
                ]
            }
        )

        spec = ConnectorSpec(
            name="serper",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=0.01,
        )

        adapter = ConnectorAdapter(mock_connector, spec)

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY, query="test"
        )
        query_features = QueryFeatures.extract("test", request)
        context = ExecutionContext()

        # Execute
        adapter.execute(request, query_features, context)

        # Verify metrics track the failure
        metrics = context.metrics["serper"]
        assert metrics["items_received"] == 2
        assert metrics["candidates_added"] == 1
        assert metrics["mapping_failures"] == 1
