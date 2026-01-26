"""
Connector Registry and Factory.

Provides centralized metadata for all available connectors and a factory
function to instantiate them. This registry serves as the single source of
truth for connector capabilities, costs, and trust levels used by the planner
to make intelligent selection decisions.

Phase 1 includes: Serper (discovery) and GooglePlaces (enrichment).
"""

from dataclasses import dataclass
from typing import Dict, Type

from engine.ingestion.base import BaseConnector
from engine.ingestion.connectors.serper import SerperConnector
from engine.ingestion.connectors.google_places import GooglePlacesConnector


@dataclass(frozen=True)
class ConnectorSpec:
    """
    Immutable metadata specification for a connector.

    Defines all the metadata needed by the planner to make intelligent
    connector selection decisions.

    Attributes:
        name: Unique identifier for the connector (e.g., "serper")
        connector_class: Fully qualified class path for dynamic import
        phase: Orchestration phase ("discovery" or "enrichment")
        cost_per_call_usd: Average cost in USD per API call
        trust_level: Trust score from 0.0 to 1.0 (1.0 = authoritative)
        timeout_seconds: Maximum execution timeout for this connector
    """

    name: str
    connector_class: str
    phase: str  # "discovery" or "enrichment"
    cost_per_call_usd: float
    trust_level: float  # 0.0 to 1.0
    timeout_seconds: int


# Global connector registry - Phase 1 includes Serper and GooglePlaces
CONNECTOR_REGISTRY: Dict[str, ConnectorSpec] = {
    "serper": ConnectorSpec(
        name="serper",
        connector_class="engine.ingestion.connectors.serper.SerperConnector",
        phase="discovery",
        cost_per_call_usd=0.01,  # Serper API pricing
        trust_level=0.75,  # Web search results, moderate trust
        timeout_seconds=30,
    ),
    "google_places": ConnectorSpec(
        name="google_places",
        connector_class="engine.ingestion.connectors.google_places.GooglePlacesConnector",
        phase="enrichment",
        cost_per_call_usd=0.017,  # Google Places API pricing (Text Search)
        trust_level=0.95,  # Authoritative Google data, very high trust
        timeout_seconds=30,
    ),
}


# Map connector names to their implementation classes
# Extracted to module level to avoid recreating on every factory call
_CONNECTOR_CLASSES: Dict[str, Type[BaseConnector]] = {
    "serper": SerperConnector,
    "google_places": GooglePlacesConnector,
}


def get_connector_instance(connector_name: str) -> BaseConnector:
    """
    Factory function to create connector instances.

    Creates a fresh instance of the specified connector. Each connector
    initializes its own Prisma database client. Caller is responsible for
    connecting to the database via await connector.db.connect().

    Args:
        connector_name: Name of the connector (must exist in CONNECTOR_REGISTRY)

    Returns:
        BaseConnector: Fresh instance of the requested connector

    Raises:
        KeyError: If connector_name is not in CONNECTOR_REGISTRY

    Example:
        connector = get_connector_instance("serper")
        await connector.db.connect()
        results = await connector.fetch("tennis courts Edinburgh")
        await connector.db.disconnect()
    """
    if connector_name not in CONNECTOR_REGISTRY:
        raise KeyError(
            f"Unknown connector: {connector_name}. "
            f"Available connectors: {list(CONNECTOR_REGISTRY.keys())}"
        )

    connector_class = _CONNECTOR_CLASSES[connector_name]

    # Instantiate connector (it will create its own Prisma client)
    return connector_class()
