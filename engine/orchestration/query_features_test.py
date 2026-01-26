"""
Unit tests for QueryFeatures extraction.

Tests verify:
- Deterministic feature extraction from query strings
- Boolean signal generation (category search, geo intent, etc.)
- Immutability of QueryFeatures dataclass
"""

import pytest
from dataclasses import FrozenInstanceError
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.types import IngestRequest, IngestionMode


class TestQueryFeatures:
    """Tests for QueryFeatures dataclass and extraction logic."""

    def test_query_features_is_frozen(self):
        """QueryFeatures should be immutable."""
        features = QueryFeatures(
            looks_like_category_search=True,
            has_geo_intent=False,
        )
        with pytest.raises(FrozenInstanceError):
            features.looks_like_category_search = False  # type: ignore

    def test_extract_category_search_signal(self):
        """Should detect category-like queries."""
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY, query="test")

        # Category patterns
        features = QueryFeatures.extract("tennis courts", request)
        assert features.looks_like_category_search is True

        features = QueryFeatures.extract("padel", request)
        assert features.looks_like_category_search is True

        features = QueryFeatures.extract("sports facilities", request)
        assert features.looks_like_category_search is True

    def test_extract_non_category_search_signal(self):
        """Should not flag specific venue names as category searches."""
        request = IngestRequest(ingestion_mode=IngestionMode.RESOLVE_ONE, query="test")

        # Specific venue names
        features = QueryFeatures.extract("Oriam Scotland", request)
        assert features.looks_like_category_search is False

        features = QueryFeatures.extract("Edinburgh Leisure Centre", request)
        assert features.looks_like_category_search is False

    def test_extract_geo_intent_signal(self):
        """Should detect geographic intent in queries."""
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY, query="test")

        # Geo patterns
        features = QueryFeatures.extract("tennis courts in Edinburgh", request)
        assert features.has_geo_intent is True

        features = QueryFeatures.extract("near Leith", request)
        assert features.has_geo_intent is True

        features = QueryFeatures.extract("tennis near me", request)
        assert features.has_geo_intent is True

    def test_extract_no_geo_intent_signal(self):
        """Should not flag queries without geographic markers."""
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY, query="test")

        features = QueryFeatures.extract("tennis courts", request)
        assert features.has_geo_intent is False

        features = QueryFeatures.extract("padel", request)
        assert features.has_geo_intent is False

    def test_extract_is_deterministic(self):
        """Extraction should produce identical results for same input."""
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY, query="test")

        features1 = QueryFeatures.extract("tennis courts in Edinburgh", request)
        features2 = QueryFeatures.extract("tennis courts in Edinburgh", request)

        assert features1 == features2
        assert features1.looks_like_category_search == features2.looks_like_category_search
        assert features1.has_geo_intent == features2.has_geo_intent

    def test_extract_handles_empty_query(self):
        """Should handle empty query gracefully."""
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY, query="test")

        features = QueryFeatures.extract("", request)
        assert features.looks_like_category_search is False
        assert features.has_geo_intent is False

    def test_extract_handles_whitespace_only_query(self):
        """Should handle whitespace-only query gracefully."""
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY, query="test")

        features = QueryFeatures.extract("   ", request)
        assert features.looks_like_category_search is False
        assert features.has_geo_intent is False

    def test_extract_is_case_insensitive(self):
        """Feature extraction should be case insensitive."""
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY, query="test")

        features_lower = QueryFeatures.extract("tennis courts in edinburgh", request)
        features_upper = QueryFeatures.extract("TENNIS COURTS IN EDINBURGH", request)
        features_mixed = QueryFeatures.extract("Tennis Courts In Edinburgh", request)

        assert features_lower == features_upper == features_mixed
