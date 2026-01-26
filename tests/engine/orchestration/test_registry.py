"""
Tests for Connector Registry and Factory.

Validates:
- CONNECTOR_REGISTRY structure and metadata
- get_connector_instance factory function
- Error handling for unknown connectors
"""

import pytest
from engine.orchestration.registry import (
    ConnectorSpec,
    CONNECTOR_REGISTRY,
    get_connector_instance,
)
from engine.ingestion.base import BaseConnector
from engine.ingestion.connectors.serper import SerperConnector
from engine.ingestion.connectors.google_places import GooglePlacesConnector


class TestConnectorSpec:
    """Test ConnectorSpec dataclass structure."""

    def test_connector_spec_is_frozen(self):
        """ConnectorSpec should be immutable (frozen dataclass)."""
        spec = ConnectorSpec(
            name="test",
            connector_class="test.TestConnector",
            phase="discovery",
            cost_per_call_usd=0.01,
            trust_level=0.8,
            timeout_seconds=30,
        )

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(AttributeError):
            spec.name = "modified"

    def test_connector_spec_has_all_required_fields(self):
        """ConnectorSpec should have all required metadata fields."""
        spec = ConnectorSpec(
            name="serper",
            connector_class="engine.ingestion.connectors.serper.SerperConnector",
            phase="discovery",
            cost_per_call_usd=0.01,
            trust_level=0.75,
            timeout_seconds=30,
        )

        assert spec.name == "serper"
        assert spec.connector_class == "engine.ingestion.connectors.serper.SerperConnector"
        assert spec.phase == "discovery"
        assert spec.cost_per_call_usd == 0.01
        assert spec.trust_level == 0.75
        assert spec.timeout_seconds == 30


class TestConnectorRegistry:
    """Test CONNECTOR_REGISTRY structure and contents."""

    def test_registry_is_dict(self):
        """CONNECTOR_REGISTRY should be a dictionary."""
        assert isinstance(CONNECTOR_REGISTRY, dict)

    def test_registry_contains_serper(self):
        """Registry should contain serper connector for Phase 1."""
        assert "serper" in CONNECTOR_REGISTRY
        assert isinstance(CONNECTOR_REGISTRY["serper"], ConnectorSpec)

    def test_registry_contains_google_places(self):
        """Registry should contain google_places connector for Phase 1."""
        assert "google_places" in CONNECTOR_REGISTRY
        assert isinstance(CONNECTOR_REGISTRY["google_places"], ConnectorSpec)

    def test_serper_spec_metadata(self):
        """Serper spec should have correct metadata."""
        spec = CONNECTOR_REGISTRY["serper"]

        assert spec.name == "serper"
        assert spec.phase == "discovery"
        assert spec.cost_per_call_usd > 0
        assert 0.0 <= spec.trust_level <= 1.0
        assert spec.timeout_seconds > 0

    def test_google_places_spec_metadata(self):
        """Google Places spec should have correct metadata."""
        spec = CONNECTOR_REGISTRY["google_places"]

        assert spec.name == "google_places"
        assert spec.phase == "enrichment"
        assert spec.cost_per_call_usd > 0
        assert 0.0 <= spec.trust_level <= 1.0
        assert spec.timeout_seconds > 0

    def test_google_places_has_higher_trust_than_serper(self):
        """Google Places should have higher trust level than Serper (authoritative data)."""
        serper_trust = CONNECTOR_REGISTRY["serper"].trust_level
        google_trust = CONNECTOR_REGISTRY["google_places"].trust_level

        assert google_trust > serper_trust

    def test_all_specs_have_valid_phases(self):
        """All connector specs should have valid phase values."""
        valid_phases = {"discovery", "enrichment"}

        for connector_name, spec in CONNECTOR_REGISTRY.items():
            assert (
                spec.phase in valid_phases
            ), f"{connector_name} has invalid phase: {spec.phase}"


class TestGetConnectorInstance:
    """Test get_connector_instance factory function."""

    def test_can_instantiate_serper(self):
        """Should be able to instantiate SerperConnector."""
        connector = get_connector_instance("serper")

        assert isinstance(connector, BaseConnector)
        assert isinstance(connector, SerperConnector)
        assert connector.source_name == "serper"

    def test_can_instantiate_google_places(self):
        """Should be able to instantiate GooglePlacesConnector."""
        connector = get_connector_instance("google_places")

        assert isinstance(connector, BaseConnector)
        assert isinstance(connector, GooglePlacesConnector)
        assert connector.source_name == "google_places"

    def test_each_call_creates_new_instance(self):
        """Each factory call should create a fresh instance."""
        connector1 = get_connector_instance("serper")
        connector2 = get_connector_instance("serper")

        assert connector1 is not connector2

    def test_unknown_connector_raises_key_error(self):
        """Unknown connector name should raise KeyError with helpful message."""
        with pytest.raises(KeyError) as exc_info:
            get_connector_instance("nonexistent_connector")

        error_message = str(exc_info.value)
        assert "nonexistent_connector" in error_message
        assert "Available connectors" in error_message

    def test_error_message_lists_available_connectors(self):
        """KeyError should list all available connectors."""
        with pytest.raises(KeyError) as exc_info:
            get_connector_instance("invalid")

        error_message = str(exc_info.value)
        assert "serper" in error_message
        assert "google_places" in error_message


class TestRegistryConnectorCoverage:
    """Test that registry covers all Phase 1 connectors."""

    def test_phase1_has_exactly_two_connectors(self):
        """Phase 1 should include exactly 2 connectors: Serper and GooglePlaces."""
        assert len(CONNECTOR_REGISTRY) == 2
        assert set(CONNECTOR_REGISTRY.keys()) == {"serper", "google_places"}

    def test_has_one_discovery_connector(self):
        """Phase 1 should have exactly one discovery connector."""
        discovery_connectors = [
            spec for spec in CONNECTOR_REGISTRY.values() if spec.phase == "discovery"
        ]
        assert len(discovery_connectors) == 1
        assert discovery_connectors[0].name == "serper"

    def test_has_one_enrichment_connector(self):
        """Phase 1 should have exactly one enrichment connector."""
        enrichment_connectors = [
            spec for spec in CONNECTOR_REGISTRY.values() if spec.phase == "enrichment"
        ]
        assert len(enrichment_connectors) == 1
        assert enrichment_connectors[0].name == "google_places"
