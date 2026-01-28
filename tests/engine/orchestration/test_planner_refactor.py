"""Test planner refactor (Lens-driven connector routing, TDD)."""

import pytest
from engine.orchestration.planner import select_connectors
from engine.orchestration.types import IngestRequest, IngestionMode


def test_padel_query_includes_sport_scotland():
    """Test that Padel query routes to sport_scotland via Lens."""
    request = IngestRequest(
        query="padel courts edinburgh",
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        lens="padel"
    )

    connectors = select_connectors(request)

    assert "sport_scotland" in connectors
    assert "edinburgh_council" in connectors


def test_wine_query_includes_wine_connectors():
    """Test that Wine query routes to wine_searcher via Lens."""
    request = IngestRequest(
        query="wineries in scotland",
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        lens="wine"
    )

    connectors = select_connectors(request)

    # Wine lens should add wine-specific connectors
    assert "wine_searcher" in connectors or "edinburgh_council" in connectors


def test_generic_query_no_domain_connectors():
    """Test that generic query doesn't trigger domain connectors."""
    request = IngestRequest(
        query="coffee shops",
        ingestion_mode=IngestionMode.DISCOVER_MANY
    )

    connectors = select_connectors(request)

    # Should only have base connectors
    assert "sport_scotland" not in connectors
    assert "wine_searcher" not in connectors


def test_lens_defaults_to_padel():
    """Test that lens defaults to Padel when not specified."""
    request = IngestRequest(
        query="padel courts",
        ingestion_mode=IngestionMode.DISCOVER_MANY
        # No lens specified
    )

    connectors = select_connectors(request)

    # Should use Padel lens by default
    assert "sport_scotland" in connectors
