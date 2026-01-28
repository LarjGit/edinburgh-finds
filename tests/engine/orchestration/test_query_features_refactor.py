"""Test query_features refactor (Lens-driven, TDD)."""

import pytest
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.types import IngestRequest, IngestionMode


def test_query_features_uses_padel_lens_by_default():
    """Test that query features uses Padel lens when no lens specified."""
    request = IngestRequest(
        query="padel courts edinburgh",
        ingestion_mode=IngestionMode.DISCOVER_MANY
    )

    features = QueryFeatures.extract("padel courts edinburgh", request)

    # Should detect as category search using Padel lens keywords
    assert features.looks_like_category_search is True
    assert features.has_geo_intent is True


def test_query_features_uses_wine_lens():
    """Test that query features uses Wine lens when specified."""
    request = IngestRequest(
        query="wineries in scotland",
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        lens="wine"
    )

    features = QueryFeatures.extract("wineries in scotland", request, lens_name="wine")

    # Should detect as category search using Wine lens keywords
    assert features.looks_like_category_search is True
    assert features.has_geo_intent is True


def test_query_features_generic_query_no_category():
    """Test that generic query doesn't match category search."""
    request = IngestRequest(
        query="coffee shops",
        ingestion_mode=IngestionMode.DISCOVER_MANY
    )

    features = QueryFeatures.extract("coffee shops", request)

    # "coffee" not in Padel lens keywords
    assert features.looks_like_category_search is False


def test_query_features_location_detection():
    """Test location detection using Lens indicators."""
    request = IngestRequest(
        query="facilities in leith",
        ingestion_mode=IngestionMode.DISCOVER_MANY
    )

    features = QueryFeatures.extract("facilities in leith", request)

    # "in" and "leith" are location indicators
    assert features.has_geo_intent is True
