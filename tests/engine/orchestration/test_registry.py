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
from engine.ingestion.connectors.open_street_map import OSMConnector
from engine.ingestion.connectors.overture_maps import OvertureMapsConnector
from engine.ingestion.connectors.sport_scotland import SportScotlandConnector
from engine.ingestion.connectors.edinburgh_council import EdinburghCouncilConnector
from engine.ingestion.connectors.open_charge_map import OpenChargeMapConnector


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
            rate_limit_per_day=1000,
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
            rate_limit_per_day=2500,
        )

        assert spec.name == "serper"
        assert spec.connector_class == "engine.ingestion.connectors.serper.SerperConnector"
        assert spec.phase == "discovery"
        assert spec.cost_per_call_usd == 0.01
        assert spec.trust_level == 0.75
        assert spec.timeout_seconds == 30
        assert spec.rate_limit_per_day == 2500


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

    def test_registry_contains_openstreetmap(self):
        """Registry should contain openstreetmap connector for Phase 2."""
        assert "openstreetmap" in CONNECTOR_REGISTRY
        assert isinstance(CONNECTOR_REGISTRY["openstreetmap"], ConnectorSpec)

    def test_registry_contains_overture_maps(self):
        """Registry should contain overture_maps connector for Tier 1 baseline."""
        assert "overture_maps" in CONNECTOR_REGISTRY
        assert isinstance(CONNECTOR_REGISTRY["overture_maps"], ConnectorSpec)

    def test_registry_contains_sport_scotland(self):
        """Registry should contain sport_scotland connector for Phase 2."""
        assert "sport_scotland" in CONNECTOR_REGISTRY
        assert isinstance(CONNECTOR_REGISTRY["sport_scotland"], ConnectorSpec)

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

    def test_openstreetmap_spec_metadata(self):
        """OpenStreetMap spec should have correct metadata."""
        spec = CONNECTOR_REGISTRY["openstreetmap"]

        assert spec.name == "openstreetmap"
        assert spec.phase == "discovery"
        assert spec.cost_per_call_usd == 0.0  # Free API
        assert 0.0 <= spec.trust_level <= 1.0
        assert spec.timeout_seconds > 0

    def test_overture_maps_spec_metadata(self):
        """Overture Maps spec should have correct metadata."""
        spec = CONNECTOR_REGISTRY["overture_maps"]

        assert spec.name == "overture_maps"
        assert spec.phase == "discovery"
        assert spec.cost_per_call_usd == 0.0  # Free baseline dataset
        assert 0.0 <= spec.trust_level <= 1.0
        assert spec.timeout_seconds > 0

    def test_sport_scotland_spec_metadata(self):
        """SportScotland spec should have correct metadata."""
        spec = CONNECTOR_REGISTRY["sport_scotland"]

        assert spec.name == "sport_scotland"
        assert spec.phase == "enrichment"
        assert spec.cost_per_call_usd == 0.0  # Free API
        assert 0.0 <= spec.trust_level <= 1.0
        assert spec.timeout_seconds > 0

    def test_registry_contains_edinburgh_council(self):
        """Registry should contain edinburgh_council connector for Phase 3."""
        assert "edinburgh_council" in CONNECTOR_REGISTRY
        assert isinstance(CONNECTOR_REGISTRY["edinburgh_council"], ConnectorSpec)

    def test_edinburgh_council_spec_metadata(self):
        """Edinburgh Council spec should have correct metadata."""
        spec = CONNECTOR_REGISTRY["edinburgh_council"]

        assert spec.name == "edinburgh_council"
        assert spec.phase == "enrichment"
        assert spec.cost_per_call_usd == 0.0  # Free government API
        assert 0.0 <= spec.trust_level <= 1.0
        assert spec.trust_level >= 0.85  # High trust for official government data
        assert spec.timeout_seconds > 0

    def test_registry_contains_open_charge_map(self):
        """Registry should contain open_charge_map connector for Phase 3."""
        assert "open_charge_map" in CONNECTOR_REGISTRY
        assert isinstance(CONNECTOR_REGISTRY["open_charge_map"], ConnectorSpec)

    def test_open_charge_map_spec_metadata(self):
        """OpenChargeMap spec should have correct metadata."""
        spec = CONNECTOR_REGISTRY["open_charge_map"]

        assert spec.name == "open_charge_map"
        assert spec.phase == "enrichment"
        assert spec.cost_per_call_usd == 0.0  # Free API
        assert 0.0 <= spec.trust_level <= 1.0
        assert spec.timeout_seconds > 0

    def test_all_specs_have_valid_phases(self):
        """All connector specs should have valid phase values."""
        valid_phases = {"discovery", "enrichment"}

        for connector_name, spec in CONNECTOR_REGISTRY.items():
            assert (
                spec.phase in valid_phases
            ), f"{connector_name} has invalid phase: {spec.phase}"


class TestRateLimitMetadata:
    """Test rate limit metadata for PL-004 implementation."""

    def test_all_connectors_have_rate_limit_per_day(self):
        """All connectors should have rate_limit_per_day field defined (PL-004)."""
        for connector_name, spec in CONNECTOR_REGISTRY.items():
            assert hasattr(spec, 'rate_limit_per_day'), \
                f"{connector_name} missing rate_limit_per_day field"
            assert isinstance(spec.rate_limit_per_day, int), \
                f"{connector_name} rate_limit_per_day should be int, got {type(spec.rate_limit_per_day)}"
            assert spec.rate_limit_per_day > 0, \
                f"{connector_name} rate_limit_per_day should be positive, got {spec.rate_limit_per_day}"

    def test_serper_rate_limit_reflects_api_tier(self):
        """Serper rate limit should reflect free tier limit (2500 req/day)."""
        spec = CONNECTOR_REGISTRY["serper"]
        assert spec.rate_limit_per_day == 2500

    def test_google_places_rate_limit_is_conservative(self):
        """Google Places rate limit should be conservative (1000 req/day)."""
        spec = CONNECTOR_REGISTRY["google_places"]
        assert spec.rate_limit_per_day == 1000

    def test_free_apis_have_generous_rate_limits(self):
        """Free APIs (OSM, Sport Scotland, etc.) should have generous rate limits."""
        free_connectors = [
            "openstreetmap",
            "overture_maps",
            "sport_scotland",
            "edinburgh_council",
            "open_charge_map",
        ]

        for connector_name in free_connectors:
            spec = CONNECTOR_REGISTRY[connector_name]
            # Free APIs should have at least 10k/day for fair use
            assert spec.rate_limit_per_day >= 10000, \
                f"{connector_name} should have generous rate limit, got {spec.rate_limit_per_day}"


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

    def test_can_instantiate_openstreetmap(self):
        """Should be able to instantiate OSMConnector."""
        connector = get_connector_instance("openstreetmap")

        assert isinstance(connector, BaseConnector)
        assert isinstance(connector, OSMConnector)
        assert connector.source_name == "openstreetmap"

    def test_can_instantiate_overture_maps(self):
        """Should be able to instantiate OvertureMapsConnector."""
        connector = get_connector_instance("overture_maps")

        assert isinstance(connector, BaseConnector)
        assert isinstance(connector, OvertureMapsConnector)
        assert connector.source_name == "overture_maps"

    def test_can_instantiate_sport_scotland(self):
        """Should be able to instantiate SportScotlandConnector."""
        connector = get_connector_instance("sport_scotland")

        assert isinstance(connector, BaseConnector)
        assert isinstance(connector, SportScotlandConnector)
        assert connector.source_name == "sport_scotland"

    def test_can_instantiate_edinburgh_council(self):
        """Should be able to instantiate EdinburghCouncilConnector."""
        connector = get_connector_instance("edinburgh_council")

        assert isinstance(connector, BaseConnector)
        assert isinstance(connector, EdinburghCouncilConnector)
        assert connector.source_name == "edinburgh_council"

    def test_can_instantiate_open_charge_map(self):
        """Should be able to instantiate OpenChargeMapConnector."""
        connector = get_connector_instance("open_charge_map")

        assert isinstance(connector, BaseConnector)
        assert isinstance(connector, OpenChargeMapConnector)
        assert connector.source_name == "open_charge_map"

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

    def test_phase4_has_seven_connectors(self):
        """Registry should include 7 connectors after adding Overture Maps baseline."""
        assert len(CONNECTOR_REGISTRY) == 7
        assert set(CONNECTOR_REGISTRY.keys()) == {
            "serper",
            "google_places",
            "openstreetmap",
            "overture_maps",
            "sport_scotland",
            "edinburgh_council",
            "open_charge_map",
        }

    def test_has_three_discovery_connectors(self):
        """Registry should have three discovery connectors including Overture Maps baseline."""
        discovery_connectors = [
            spec for spec in CONNECTOR_REGISTRY.values() if spec.phase == "discovery"
        ]
        assert len(discovery_connectors) == 3
        discovery_names = {spec.name for spec in discovery_connectors}
        assert discovery_names == {"serper", "openstreetmap", "overture_maps"}

    def test_has_four_enrichment_connectors(self):
        """Phase 3 should have four enrichment connectors."""
        enrichment_connectors = [
            spec for spec in CONNECTOR_REGISTRY.values() if spec.phase == "enrichment"
        ]
        assert len(enrichment_connectors) == 4
        enrichment_names = {spec.name for spec in enrichment_connectors}
        assert enrichment_names == {"google_places", "sport_scotland", "edinburgh_council", "open_charge_map"}
