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
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from prisma import Prisma

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

    async def execute(
        self,
        request: IngestRequest,
        query_features: QueryFeatures,
        context: ExecutionContext,
        state: "OrchestratorState",
        db: Optional[Prisma] = None,
    ) -> None:
        """
        Execute connector and write results to state.

        This is the main entry point called by the Orchestrator. It:
        1. Checks rate limit (PL-004) - skips if at/over limit
        2. Translates query for connector-specific requirements
        3. Calls connector.fetch() directly (async)
        4. Extracts items from connector response
        5. Maps each item to canonical candidate schema
        6. Appends candidates to state.candidates
        7. Records metrics in state.metrics
        8. Handles errors gracefully (logs to state.errors)

        Args:
            request: The ingestion request (contains query)
            query_features: Extracted query features (used for query translation)
            context: Immutable execution context (lens contract)
            state: Mutable orchestrator state (candidates, metrics, errors)
            db: Database connection for rate limit tracking (PL-004)
        """
        start_time = time.time()
        items_received = 0
        candidates_added = 0
        mapping_failures = 0

        try:
            # Check rate limit before executing (PL-004)
            if db is not None and not await self._check_rate_limit(db):
                # At/over limit: skip connector, record error
                error_msg = f"Rate limit exceeded ({self.spec.rate_limit_per_day}/day)"
                state.errors.append({
                    "connector": self.spec.name,
                    "error": error_msg,
                    "rate_limited": True
                })
                state.metrics[self.spec.name] = {
                    "executed": False,
                    "error": error_msg,
                    "rate_limited": True,
                    "cost_usd": 0.0
                }
                return

            # Increment usage counter before execution (PL-004)
            if db is not None:
                await self._increment_usage(db)
            # Translate query for connector-specific requirements
            # (e.g., Sport Scotland needs layer names, not natural language)
            translated_query = self._translate_query(request.query, query_features)

            # Call connector.fetch() with timeout enforcement (PL-002)
            results = await asyncio.wait_for(
                self.connector.fetch(translated_query),
                timeout=self.spec.timeout_seconds
            )

            # Extract items from connector-specific response format
            items = self._extract_items(results)
            items_received = len(items)

            # Map each item to canonical candidate schema
            for item in items:
                try:
                    candidate = self._map_to_candidate(item)
                    state.candidates.append(candidate)
                    candidates_added += 1
                except Exception as e:
                    # Track mapping failures for observability
                    mapping_failures += 1
                    # Don't raise - continue processing other items

            # Record success metrics
            elapsed_ms = int((time.time() - start_time) * 1000)
            state.metrics[self.spec.name] = {
                "executed": True,
                "items_received": items_received,
                "candidates_added": candidates_added,
                "mapping_failures": mapping_failures,
                "execution_time_ms": elapsed_ms,
                "cost_usd": self.spec.estimated_cost_usd,
            }

        except asyncio.TimeoutError:
            # Timeout error: Connector exceeded timeout_seconds (PL-002)
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Connector timed out after {self.spec.timeout_seconds}s"

            state.errors.append(
                {
                    "connector": self.spec.name,
                    "error": error_msg,
                    "execution_time_ms": elapsed_ms,
                }
            )

            # Record failure metrics
            state.metrics[self.spec.name] = {
                "executed": False,
                "error": error_msg,
                "execution_time_ms": elapsed_ms,
                "cost_usd": 0.0,  # No cost on timeout
            }

        except Exception as e:
            # Non-fatal error handling: Log error, don't crash orchestration
            elapsed_ms = int((time.time() - start_time) * 1000)

            state.errors.append(
                {
                    "connector": self.spec.name,
                    "error": str(e),
                    "execution_time_ms": elapsed_ms,
                }
            )

            # Record failure metrics
            state.metrics[self.spec.name] = {
                "executed": False,
                "error": str(e),
                "execution_time_ms": elapsed_ms,
                "cost_usd": 0.0,  # No cost if failed
            }

    def _translate_query(
        self, query: str, query_features: QueryFeatures
    ) -> str:
        """
        Translate natural language query to connector-specific format.

        Different connectors have different input requirements:
        - Most connectors: Accept natural language queries directly
        - Sport Scotland: Requires WFS layer names (e.g., "tennis_courts", "pitches")

        Args:
            query: Natural language query from user
            query_features: Extracted query features (for sports detection)

        Returns:
            Translated query appropriate for this connector
        """
        source = self.connector.source_name

        # Sport Scotland requires layer name translation
        if source == "sport_scotland":
            return self._translate_to_sport_scotland_layer(query, query_features)

        # All other connectors accept natural language queries
        return query

    def _translate_to_sport_scotland_layer(
        self, query: str, query_features: QueryFeatures
    ) -> str:
        """
        Translate natural language sports query to Sport Scotland WFS layer name.

        Sport Scotland WFS architecture: ALL sports facilities are in a single
        unified layer called "pub_sptk" (public sports toolkit). There are no
        sport-specific layers.

        The WFS returns all facility types, and filtering by sport happens
        through WFS filter parameters or post-processing the results.

        Args:
            query: Natural language query (e.g., "padel courts Edinburgh")
            query_features: Extracted query features (unused - all queries use same layer)

        Returns:
            Always returns "pub_sptk" - the unified Sport Scotland facilities layer
        """
        # Sport Scotland uses a single unified layer for all sports facilities
        # Query returns 187 facilities in Edinburgh across all sports types
        return "pub_sptk"

    def _extract_items(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract items from connector-specific response format.

        Different connectors return results in different formats:
        - Serper: {"organic": [...]}
        - Google Places (old API): {"results": [...]}
        - Google Places (new API v1): {"places": [...]}
        - OSM: {"elements": [...]}
        - SportScotland: {"features": [...]}  # GeoJSON FeatureCollection

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

        # SportScotland format (GeoJSON FeatureCollection)
        if "features" in results:
            return results["features"]

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
        - OpenStreetMap: id+type→ids.osm, lat/lon→lat/lng, tags.name→name
        - SportScotland: id→ids.sport_scotland, geometry.coordinates→lng/lat, properties.name→name

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
        elif source == "openstreetmap":
            return self._map_openstreetmap(raw_item)
        elif source == "sport_scotland":
            return self._map_sport_scotland(raw_item)
        elif source == "overture_release":
            return self._map_overture_release(raw_item)
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

    def _map_openstreetmap(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map OpenStreetMap result to canonical schema.

        OSM provides:
        - id (unique OSM ID)
        - type (node, way, or relation)
        - lat/lon (flat coordinates)
        - tags object with name and other attributes

        Args:
            item: OSM element

        Returns:
            Canonical candidate dict
        """
        # Normalize raw payload
        raw = normalize_for_json(item)

        # Build OSM ID (format: type/id, e.g., "node/123456789")
        osm_id = f"{item.get('type', 'node')}/{item.get('id', 'unknown')}"

        # Extract name from tags
        tags = item.get("tags", {})
        name = tags.get("name", "Unknown")

        # Extract coordinates
        lat = item.get("lat")
        lon = item.get("lon")

        return {
            "ids": {"osm": osm_id},
            "lat": lat,
            "lng": lon,
            "name": name,
            "source": "openstreetmap",
            "raw": raw,
        }

    def _map_sport_scotland(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map SportScotland GeoJSON feature to canonical schema.

        SportScotland provides:
        - id (feature ID)
        - properties object with name and facility attributes
        - geometry object with coordinates (GeoJSON format: [lng, lat])

        Args:
            item: GeoJSON Feature

        Returns:
            Canonical candidate dict
        """
        # Normalize raw payload
        raw = normalize_for_json(item)

        # Extract ID
        feature_id = item.get("id", "unknown")

        # Extract name from properties
        properties = item.get("properties", {})
        name = properties.get("name", "Unknown")

        # Extract coordinates from GeoJSON geometry
        # GeoJSON format: coordinates = [longitude, latitude]
        lat = None
        lng = None
        geometry = item.get("geometry", {})
        if geometry and geometry.get("type") == "Point":
            coords = geometry.get("coordinates", [])
            if len(coords) >= 2:
                lng = coords[0]  # Longitude first in GeoJSON
                lat = coords[1]  # Latitude second

        return {
            "ids": {"sport_scotland": feature_id},
            "lat": lat,
            "lng": lng,
            "name": name,
            "source": "sport_scotland",
            "raw": raw,
        }

    def _map_overture_release(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Overture row-style place record to canonical candidate schema.

        Overture row records provide:
        - id (stable Overture place ID)
        - names.primary (display name)
        - geometry.coordinates in GeoJSON [lng, lat] order (optional)
        """
        raw = normalize_for_json(item)

        ids = {}
        if item.get("id") is not None:
            ids["overture"] = str(item["id"])

        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            names = item.get("names")
            if isinstance(names, dict):
                primary_name = names.get("primary")
                if isinstance(primary_name, str):
                    name = primary_name
                elif isinstance(primary_name, dict):
                    primary_value = primary_name.get("value")
                    if isinstance(primary_value, str):
                        name = primary_value

        if not isinstance(name, str) or not name.strip():
            raise KeyError("Missing required Overture field: names.primary")
        name = name.strip()

        lat = None
        lng = None
        geometry = item.get("geometry")
        if isinstance(geometry, dict) and geometry.get("type") == "Point":
            coordinates = geometry.get("coordinates")
            if isinstance(coordinates, list) and len(coordinates) >= 2:
                try:
                    lng = float(coordinates[0])
                    lat = float(coordinates[1])
                except (TypeError, ValueError):
                    lat = None
                    lng = None

        return {
            "ids": ids,
            "lat": lat,
            "lng": lng,
            "name": name,
            "source": "overture_release",
            "raw": raw,
        }

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

    async def _check_rate_limit(self, db: Prisma) -> bool:
        """
        Check if connector is within rate limit for today.

        Queries ConnectorUsage table for today's request count and compares
        against spec.rate_limit_per_day.

        Args:
            db: Database connection

        Returns:
            True if under limit (can execute), False if at/over limit (skip)
        """
        # Use datetime at midnight for date comparison (Prisma expects datetime, not date)
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # Query ConnectorUsage for today's count
        usage = await db.connectorusage.find_first(
            where={
                "connector_name": self.spec.name,
                "date": today
            }
        )

        current_count = usage.request_count if usage else 0
        return current_count < self.spec.rate_limit_per_day

    async def _increment_usage(self, db: Prisma) -> None:
        """
        Increment usage count for connector for today.

        Uses upsert to handle both first request (create) and subsequent
        requests (increment) atomically.

        Args:
            db: Database connection
        """
        # Use datetime at midnight for date comparison (Prisma expects datetime, not date)
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        await db.connectorusage.upsert(
            where={
                "connector_name_date": {
                    "connector_name": self.spec.name,
                    "date": today
                }
            },
            data={
                "create": {
                    "connector_name": self.spec.name,
                    "date": today,
                    "request_count": 1
                },
                "update": {
                    "request_count": {"increment": 1}
                }
            }
        )
