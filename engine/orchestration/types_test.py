"""
Unit tests for core orchestration types.

Tests verify:
- Immutability of IngestRequest, BoundingBox, GeoPoint
- Default value handling
- Enum behavior for IngestionMode
"""

import pytest
from dataclasses import FrozenInstanceError
from engine.orchestration.types import (
    IngestRequest,
    IngestionMode,
    BoundingBox,
    GeoPoint,
)


class TestIngestionMode:
    """Tests for IngestionMode enum."""

    def test_has_resolve_one(self):
        """RESOLVE_ONE mode should exist."""
        assert IngestionMode.RESOLVE_ONE is not None

    def test_has_discover_many(self):
        """DISCOVER_MANY mode should exist."""
        assert IngestionMode.DISCOVER_MANY is not None

    def test_enum_values_are_unique(self):
        """Enum values should be unique."""
        assert IngestionMode.RESOLVE_ONE != IngestionMode.DISCOVER_MANY


class TestGeoPoint:
    """Tests for GeoPoint value object."""

    def test_create_geo_point(self):
        """Should create GeoPoint with lat/lng."""
        point = GeoPoint(lat=55.9533, lng=-3.1883)
        assert point.lat == 55.9533
        assert point.lng == -3.1883

    def test_geo_point_is_frozen(self):
        """GeoPoint should be immutable."""
        point = GeoPoint(lat=55.9533, lng=-3.1883)
        with pytest.raises(FrozenInstanceError):
            point.lat = 56.0  # type: ignore

    def test_geo_point_handles_zero(self):
        """GeoPoint should accept 0.0 as valid coordinate."""
        point = GeoPoint(lat=0.0, lng=0.0)
        assert point.lat == 0.0
        assert point.lng == 0.0

    def test_geo_point_equality(self):
        """GeoPoints with same coordinates should be equal."""
        point1 = GeoPoint(lat=55.9533, lng=-3.1883)
        point2 = GeoPoint(lat=55.9533, lng=-3.1883)
        assert point1 == point2


class TestBoundingBox:
    """Tests for BoundingBox value object."""

    def test_create_bounding_box(self):
        """Should create BoundingBox with two GeoPoints."""
        sw = GeoPoint(lat=55.9000, lng=-3.2000)
        ne = GeoPoint(lat=56.0000, lng=-3.1000)
        bbox = BoundingBox(southwest=sw, northeast=ne)
        assert bbox.southwest == sw
        assert bbox.northeast == ne

    def test_bounding_box_is_frozen(self):
        """BoundingBox should be immutable."""
        sw = GeoPoint(lat=55.9000, lng=-3.2000)
        ne = GeoPoint(lat=56.0000, lng=-3.1000)
        bbox = BoundingBox(southwest=sw, northeast=ne)
        with pytest.raises(FrozenInstanceError):
            bbox.southwest = GeoPoint(lat=55.8000, lng=-3.3000)  # type: ignore


class TestIngestRequest:
    """Tests for IngestRequest immutable dataclass."""

    def test_create_minimal_request(self):
        """Should create request with required fields only."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE, query="test query"
        )
        assert request.ingestion_mode == IngestionMode.RESOLVE_ONE
        assert request.query == "test query"
        assert request.target_entity_count is None
        assert request.min_confidence is None

    def test_create_full_request(self):
        """Should create request with all fields."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts",
            target_entity_count=50,
            min_confidence=0.8,
        )
        assert request.ingestion_mode == IngestionMode.DISCOVER_MANY
        assert request.query == "padel courts"
        assert request.target_entity_count == 50
        assert request.min_confidence == 0.8

    def test_ingest_request_is_frozen(self):
        """IngestRequest should be immutable."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE, query="test"
        )
        with pytest.raises(FrozenInstanceError):
            request.ingestion_mode = IngestionMode.DISCOVER_MANY  # type: ignore

    def test_optional_fields_default_to_none(self):
        """Optional fields should default to None."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE, query="test"
        )
        assert request.target_entity_count is None
        assert request.min_confidence is None

    def test_target_entity_count_can_be_set(self):
        """Should allow setting target_entity_count."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="venues",
            target_entity_count=100,
        )
        assert request.target_entity_count == 100

    def test_min_confidence_can_be_set(self):
        """Should allow setting min_confidence."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="test",
            min_confidence=0.9,
        )
        assert request.min_confidence == 0.9
