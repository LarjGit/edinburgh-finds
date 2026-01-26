"""
Tests for connector registry and factory.

Validates that:
1. ConnectorSpec holds correct metadata for each connector
2. Registry contains expected connectors with correct attributes
3. Factory creates correct connector instances
4. Invalid connector names raise appropriate errors
"""

import pytest
from engine.orchestration.registry import (
    ConnectorSpec,
    CONNECTOR_REGISTRY,
    get_connector_instance,
)
from engine.ingestion.connectors.serper import SerperConnector
from engine.ingestion.connectors.google_places import GooglePlacesConnector


class TestConnectorSpec:
    """Test ConnectorSpec dataclass."""

    def test_connector_spec_immutable(self):
        """ConnectorSpec instances should be immutable (frozen)."""
        spec = ConnectorSpec(
            name="test",
            connector_class="test.TestConnector",
            phase="discovery",
            cost_per_call_usd=0.01,
            trust_level=0.9,
            timeout_seconds=30,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            spec.name = "modified"

    def test_connector_spec_all_fields(self):
        """ConnectorSpec should hold all required metadata fields."""
        spec = ConnectorSpec(
            name="serper",
            connector_class="engine.ingestion.connectors.serper.SerperConnector",
            phase="discovery",
            cost_per_call_usd=0.01,
            trust_level=0.85,
            timeout_seconds=30,
        )

        assert spec.name == "serper"
        assert spec.connector_class == "engine.ingestion.connectors.serper.SerperConnector"
        assert spec.phase == "discovery"
        assert spec.cost_per_call_usd == 0.01
        assert spec.trust_level == 0.85
        assert spec.timeout_seconds == 30


class TestConnectorRegistry:
    """Test the global connector registry."""

    def test_registry_contains_serper(self):
        """Registry should contain Serper connector spec."""
        assert "serper" in CONNECTOR_REGISTRY
        spec = CONNECTOR_REGISTRY["serper"]

        assert spec.name == "serper"
        assert spec.phase == "discovery"
        assert spec.cost_per_call_usd > 0
        assert 0 <= spec.trust_level <= 1.0
        assert spec.timeout_seconds > 0

    def test_registry_contains_google_places(self):
        """Registry should contain Google Places connector spec."""
        assert "google_places" in CONNECTOR_REGISTRY
        spec = CONNECTOR_REGISTRY["google_places"]

        assert spec.name == "google_places"
        assert spec.phase == "enrichment"
        assert spec.cost_per_call_usd > 0
        assert 0 <= spec.trust_level <= 1.0
        assert spec.timeout_seconds > 0

    def test_registry_has_all_phase_2_connectors(self):
        """Phase 2 registry should contain 4 connectors: Serper, GooglePlaces, OSM, SportScotland."""
        assert len(CONNECTOR_REGISTRY) == 4
        assert set(CONNECTOR_REGISTRY.keys()) == {
            "serper",
            "google_places",
            "openstreetmap",
            "sport_scotland",
        }

    def test_serper_has_correct_metadata(self):
        """Serper spec should have discovery phase and appropriate trust."""
        spec = CONNECTOR_REGISTRY["serper"]
        assert spec.phase == "discovery"
        # Serper is web search, moderate trust
        assert spec.trust_level < 1.0

    def test_google_places_has_correct_metadata(self):
        """Google Places spec should have enrichment phase and high trust."""
        spec = CONNECTOR_REGISTRY["google_places"]
        assert spec.phase == "enrichment"
        # Google Places is authoritative, high trust
        assert spec.trust_level >= 0.9


class TestGetConnectorInstance:
    """Test connector factory function."""

    def test_get_serper_connector_instance(self):
        """Factory should create SerperConnector instance."""
        connector = get_connector_instance("serper")
        assert isinstance(connector, SerperConnector)
        assert connector.source_name == "serper"

    def test_get_google_places_connector_instance(self):
        """Factory should create GooglePlacesConnector instance."""
        connector = get_connector_instance("google_places")
        assert isinstance(connector, GooglePlacesConnector)
        assert connector.source_name == "google_places"

    def test_get_unknown_connector_raises_error(self):
        """Factory should raise KeyError for unknown connector names."""
        with pytest.raises(KeyError, match="Unknown connector"):
            get_connector_instance("unknown_connector")

    def test_get_connector_returns_fresh_instance(self):
        """Factory should return new instance each time (not singleton)."""
        connector1 = get_connector_instance("serper")
        connector2 = get_connector_instance("serper")

        # Should be different instances
        assert connector1 is not connector2
        # But same type
        assert type(connector1) == type(connector2)

    def test_connector_instance_has_db_client(self):
        """Created connector instances should have Prisma db client."""
        connector = get_connector_instance("serper")
        assert hasattr(connector, "db")
        # db should be Prisma instance (not connected yet)
        from prisma import Prisma

        assert isinstance(connector.db, Prisma)
