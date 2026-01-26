"""
Connector Adapter Layer for Orchestration Integration.

Bridges the async BaseConnector interface to the sync Orchestrator interface.
Handles:
- Async→sync execution bridge using asyncio.run
- Connector-specific response mapping to canonical candidate schema
- JSON normalization for raw payloads
- Error handling and metrics tracking
"""

import asyncio
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from engine.ingestion.base import BaseConnector
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import ConnectorSpec
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.types import IngestRequest


def normalize_for_json(data: Any) -> Any:
    """
    Recursively normalize data structures for JSON serialization.

    Handles non-JSON-serializable types commonly found in API responses:
    - datetime → ISO string
    - Decimal → float
    - set → sorted list (deterministic)
    - tuple → list
    - Custom objects → str() fallback

    Args:
        data: The data structure to normalize

    Returns:
        JSON-serializable version of the data
    """
    if isinstance(data, dict):
        return {key: normalize_for_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [normalize_for_json(item) for item in data]
    elif isinstance(data, set):
        # Sort for deterministic output
        return sorted([normalize_for_json(item) for item in data])
    elif isinstance(data, tuple):
        return [normalize_for_json(item) for item in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        # Fallback for custom objects
        return str(data)


class ConnectorAdapter:
    """
    Adapts BaseConnector (async) to Orchestrator interface (sync).

    Responsibilities:
    - Execute async connector.fetch() via asyncio.run bridge
    - Map connector-specific responses to canonical candidate schema
    - Normalize raw payloads for JSON serialization
    - Track execution metrics (latency, cost, candidates added)
    - Handle errors gracefully (non-fatal)

    Canonical Candidate Schema:
        {
            "ids": {"google": "ChIJ..."} or {},  # Strong IDs (Tier 1 dedupe)
            "lat": 55.9532 or None,              # Flat coords (Tier 2 dedupe)
            "lng": -3.1234 or None,
            "name": "Entity Name",
            "source": "connector_name",
            "address": "123 Street" or None,     # Optional
            "raw": {...}                         # Normalized original response
        }
    """

    def __init__(self, connector: BaseConnector, spec: ConnectorSpec):
        """
        Initialize ConnectorAdapter.

        Args:
            connector: BaseConnector instance to adapt
            spec: ConnectorSpec with metadata (name, phase, trust_level, cost)
        """
        self.connector = connector
        self.spec = spec

    def execute(
        self,
        request: IngestRequest,
        query_features: QueryFeatures,
        context: ExecutionContext,
    ) -> None:
        """
        Execute connector and write results to context.

        This is the main entry point called by the Orchestrator. It:
        1. Calls connector.fetch() via asyncio.run bridge
        2. Extracts items from connector response
        3. Maps each item to canonical candidate schema
        4. Appends candidates to context.candidates
        5. Records metrics in context.metrics
        6. Handles errors gracefully (logs to context.errors)

        Args:
            request: The ingestion request (contains query)
            query_features: Extracted query features (unused in Phase A)
            context: Shared execution context (mutable)
        """
        start_time = time.time()
        items_received = 0
        candidates_added = 0
        mapping_failures = 0

        try:
            # Async→sync bridge: Run connector.fetch() in asyncio.run
            # NOTE: This is Phase A compromise. Works for CLI, fails for async contexts.
            # If async orchestrator needed (Phase D), make execute() async and remove asyncio.run
            results = asyncio.run(self.connector.fetch(request.query))

            # Extract items from connector-specific response format
            items = self._extract_items(results)
            items_received = len(items)

            # Map each item to canonical candidate schema
            for item in items:
                try:
                    candidate = self._map_to_candidate(item)
                    context.candidates.append(candidate)
                    candidates_added += 1
                except Exception as e:
                    # Track mapping failures for observability
                    mapping_failures += 1
                    # Don't raise - continue processing other items

            # Record success metrics
            elapsed_ms = int((time.time() - start_time) * 1000)
            context.metrics[self.spec.name] = {
                "executed": True,
                "items_received": items_received,
                "candidates_added": candidates_added,
                "mapping_failures": mapping_failures,
                "execution_time_ms": elapsed_ms,
                "cost_usd": self.spec.estimated_cost_usd,
            }

        except Exception as e:
            # Non-fatal error handling: Log error, don't crash orchestration
            elapsed_ms = int((time.time() - start_time) * 1000)

            context.errors.append(
                {
                    "connector": self.spec.name,
                    "error": str(e),
                    "execution_time_ms": elapsed_ms,
                }
            )

            # Record failure metrics
            context.metrics[self.spec.name] = {
                "executed": False,
                "error": str(e),
                "execution_time_ms": elapsed_ms,
                "cost_usd": 0.0,  # No cost if failed
            }

    def _extract_items(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract items from connector-specific response format.

        Different connectors return results in different formats:
        - Serper: {"organic": [...]}
        - Google Places (old API): {"results": [...]}
        - Google Places (new API v1): {"places": [...]}
        - OSM: {"elements": [...]}

        Args:
            results: Raw connector response dict

        Returns:
            List of result items (connector-specific format)
        """
        # Serper format
        if "organic" in results:
            return results["organic"]

        # Google Places format (new API v1)
        if "places" in results:
            return results["places"]

        # Google Places format (old API - legacy)
        if "results" in results:
            return results["results"]

        # OSM format
        if "elements" in results:
            return results["elements"]

        # Fallback: assume results is the list itself
        if isinstance(results, list):
            return results

        # No results found
        return []

    def _map_to_candidate(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map connector-specific result to canonical candidate schema.

        Handles connector-specific field naming and structure:
        - Serper: title→name, no IDs, no coords
        - Google Places: place_id→ids.google, geometry.location→lat/lng, formatted_address→address

        Args:
            raw_item: Raw result item from connector

        Returns:
            Canonical candidate dict

        Raises:
            KeyError: If required fields (e.g., name) are missing
        """
        source = self.connector.source_name

        if source == "serper":
            return self._map_serper(raw_item)
        elif source == "google_places":
            return self._map_google_places(raw_item)
        else:
            # Fallback for unknown connectors
            return self._map_generic(raw_item)

    def _map_serper(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Serper result to canonical schema.

        Serper provides:
        - title (required)
        - link, snippet (optional)
        - NO strong IDs
        - NO coordinates

        Args:
            item: Serper organic result

        Returns:
            Canonical candidate dict
        """
        # Normalize raw payload
        raw = normalize_for_json(item)

        return {
            "ids": {},  # Serper has no strong IDs
            "lat": None,
            "lng": None,
            "name": item["title"],  # May raise KeyError if missing
            "source": "serper",
            "raw": raw,
        }

    def _map_google_places(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Google Places result to canonical schema.

        Supports both old and new Google Places API formats:

        Old API:
        - place_id (strong ID)
        - name (required)
        - geometry.location.lat/lng (flat coords)
        - formatted_address (optional)

        New API (v1):
        - id (strong ID)
        - displayName.text (required)
        - location.latitude/longitude (flat coords)
        - formattedAddress (optional)

        Args:
            item: Google Places result

        Returns:
            Canonical candidate dict
        """
        # Normalize raw payload
        raw = normalize_for_json(item)

        # Extract IDs (handle both old and new API)
        ids = {}
        if "place_id" in item:
            ids["google"] = item["place_id"]
        elif "id" in item:
            ids["google"] = item["id"]

        # Extract flat coordinates (handle both old and new API)
        lat = None
        lng = None

        # New API format: location.latitude/longitude
        if "location" in item and isinstance(item["location"], dict):
            lat = item["location"].get("latitude")
            lng = item["location"].get("longitude")

        # Old API format: geometry.location.lat/lng
        elif "geometry" in item and "location" in item["geometry"]:
            location = item["geometry"]["location"]
            lat = location.get("lat")
            lng = location.get("lng")

        # Extract name (handle both old and new API)
        name = None
        if "displayName" in item and isinstance(item["displayName"], dict):
            # New API format: displayName.text
            name = item["displayName"].get("text")
        elif "name" in item:
            # Old API format: name
            name = item["name"]

        if not name:
            raise KeyError("Missing required 'name' or 'displayName' field")

        # Build candidate
        candidate = {
            "ids": ids,
            "lat": lat,
            "lng": lng,
            "name": name,
            "source": "google_places",
            "raw": raw,
        }

        # Optional fields (handle both old and new API)
        if "formattedAddress" in item:
            candidate["address"] = item["formattedAddress"]
        elif "formatted_address" in item:
            candidate["address"] = item["formatted_address"]

        return candidate

    def _map_generic(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback mapping for unknown connectors.

        Assumes:
        - "name" field exists
        - No strong IDs
        - No coordinates

        Args:
            item: Generic result item

        Returns:
            Canonical candidate dict
        """
        raw = normalize_for_json(item)

        return {
            "ids": {},
            "lat": None,
            "lng": None,
            "name": item.get("name", "Unknown"),
            "source": self.connector.source_name,
            "raw": raw,
        }
