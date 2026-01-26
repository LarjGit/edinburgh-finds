"""
Tests for orchestration types modifications.

Validates that IngestRequest includes the query field:
- query: str - raw query string for connector execution
"""

import pytest
from engine.orchestration.types import IngestRequest, IngestionMode


class TestIngestRequestQueryField:
    """Test IngestRequest query field addition."""

    def test_ingest_request_has_query_field(self):
        """IngestRequest should have a query field."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="Powerleague Portobello"
        )
        assert hasattr(request, "query"), "IngestRequest missing 'query' attribute"
        assert request.query == "Powerleague Portobello"

    def test_query_field_is_required(self):
        """query field should be required (not optional)."""
        # This should raise TypeError because query is missing
        with pytest.raises(TypeError):
            IngestRequest(ingestion_mode=IngestionMode.RESOLVE_ONE)

    def test_query_can_be_any_string(self):
        """query field should accept any string value."""
        test_queries = [
            "Powerleague Portobello",
            "padel courts edinburgh",
            "climbing gyms",
            "sports facilities near me",
            ""  # Empty string should be valid
        ]

        for query in test_queries:
            request = IngestRequest(
                ingestion_mode=IngestionMode.DISCOVER_MANY,
                query=query
            )
            assert request.query == query

    def test_ingest_request_is_still_frozen(self):
        """IngestRequest should remain immutable (frozen dataclass)."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="test query"
        )

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(AttributeError):
            request.query = "new query"

    def test_existing_fields_still_present(self):
        """IngestRequest should maintain all existing fields."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="test query",
            target_entity_count=10,
            min_confidence=0.8,
            budget_usd=5.0
        )

        assert request.ingestion_mode == IngestionMode.DISCOVER_MANY
        assert request.query == "test query"
        assert request.target_entity_count == 10
        assert request.min_confidence == 0.8
        assert request.budget_usd == 5.0

    def test_optional_fields_default_to_none(self):
        """Optional fields should still default to None."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="test query"
        )

        assert request.target_entity_count is None
        assert request.min_confidence is None
        assert request.budget_usd is None


class TestIngestRequestFieldOrder:
    """Test field ordering in IngestRequest dataclass."""

    def test_query_field_comes_after_ingestion_mode(self):
        """query field should be positioned after ingestion_mode for logical grouping."""
        # Create with positional arguments to validate order
        request = IngestRequest(
            IngestionMode.RESOLVE_ONE,
            "test query"
        )

        assert request.ingestion_mode == IngestionMode.RESOLVE_ONE
        assert request.query == "test query"

    def test_can_create_with_all_fields(self):
        """Should be able to create IngestRequest with all fields specified."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts",
            target_entity_count=20,
            min_confidence=0.75,
            budget_usd=10.0
        )

        assert request.ingestion_mode == IngestionMode.DISCOVER_MANY
        assert request.query == "padel courts"
        assert request.target_entity_count == 20
        assert request.min_confidence == 0.75
        assert request.budget_usd == 10.0


class TestIngestRequestUsagePatterns:
    """Test realistic usage patterns for IngestRequest."""

    def test_resolve_one_mode_with_specific_query(self):
        """RESOLVE_ONE mode typically used with specific entity queries."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="Powerleague Portobello",
            min_confidence=0.9
        )

        assert request.ingestion_mode == IngestionMode.RESOLVE_ONE
        assert request.query == "Powerleague Portobello"
        assert request.min_confidence == 0.9

    def test_discover_many_mode_with_category_query(self):
        """DISCOVER_MANY mode typically used with category/broad queries."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts edinburgh",
            target_entity_count=50,
            budget_usd=5.0
        )

        assert request.ingestion_mode == IngestionMode.DISCOVER_MANY
        assert request.query == "padel courts edinburgh"
        assert request.target_entity_count == 50
        assert request.budget_usd == 5.0
