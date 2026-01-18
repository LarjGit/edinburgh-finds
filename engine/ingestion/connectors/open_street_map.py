"""
OpenStreetMap Overpass API Connector

This module implements the OSMConnector for fetching sports facility and venue
data from the OpenStreetMap Overpass API. The Overpass API provides powerful
querying capabilities for OpenStreetMap data using Overpass QL.

The connector handles:
- Overpass QL query construction with spatial filters
- API request formatting and execution
- Response parsing and validation
- Raw data persistence to filesystem and database
- Deduplication to prevent re-ingesting identical queries

API Documentation: https://wiki.openstreetmap.org/wiki/Overpass_API
Overpass QL: https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL
"""

import os
import json
import yaml
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
from prisma import Prisma

from engine.ingestion.base import BaseConnector
from engine.ingestion.storage import generate_file_path, save_json
from engine.ingestion.deduplication import compute_content_hash, check_duplicate


class OSMConnector(BaseConnector):
    """
    Connector for the OpenStreetMap Overpass API.

    This connector fetches geographic and facility data from OpenStreetMap
    using the Overpass API and stores it as raw JSON for later processing.

    The Overpass API allows querying OSM data using Overpass QL:
    - Query for nodes, ways, and relations
    - Filter by tags (sport, leisure, amenity, etc.)
    - Apply spatial filters (around, bounding box)
    - Returns comprehensive OSM element data

    Configuration:
        Loads settings from engine/config/sources.yaml including:
        - Base URL (no API key required)
        - Timeout settings
        - Rate limits (be respectful - it's a public API)
        - Default search parameters (location, radius)

    Usage:
        connector = OSMConnector()
        await connector.db.connect()

        # Fetch sports facilities
        data = await connector.fetch("padel")

        # Check if already ingested
        content_hash = compute_content_hash(data)
        if not await connector.is_duplicate(content_hash):
            # Save new data
            file_path = await connector.save(
                data,
                "https://overpass-api.de/api/interpreter?query=padel"
            )
            print(f"Saved to {file_path}")

        await connector.db.disconnect()
    """

    def __init__(self, config_path: str = "engine/config/sources.yaml"):
        """
        Initialize the OSM Overpass connector with configuration.

        Args:
            config_path: Path to the sources.yaml configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If base URL is missing or invalid
        """
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if 'openstreetmap' not in config:
            raise ValueError("OpenStreetMap configuration not found in sources.yaml")

        osm_config = config['openstreetmap']

        # Validate base URL
        self.base_url = osm_config.get('base_url')
        if not self.base_url:
            raise ValueError(
                "OpenStreetMap base URL not configured. "
                "Please set a valid base_url in engine/config/sources.yaml"
            )

        # Load other configuration
        self.timeout_seconds = osm_config.get('timeout_seconds', 60)
        self.default_params = osm_config.get('default_params', {})

        # Extract default location and radius for spatial queries
        location_str = self.default_params.get('location', '55.9533,-3.1883')
        lat, lon = map(float, location_str.split(','))
        self.default_lat = lat
        self.default_lon = lon
        self.default_radius = self.default_params.get('radius', 50000)

        # Initialize database connection
        self.db = Prisma()

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "openstreetmap"
        """
        return "openstreetmap"

    def _build_overpass_query(self, query: str, lat: Optional[float] = None,
                              lon: Optional[float] = None, radius: Optional[int] = None) -> str:
        """
        Build an Overpass QL query for sports facilities.

        Constructs a query that searches for OSM elements (nodes, ways, relations)
        matching the query term with spatial filtering.

        Args:
            query: Search term (e.g., "padel", "tennis", "sports")
            lat: Latitude for spatial filter (uses default if not provided)
            lon: Longitude for spatial filter (uses default if not provided)
            radius: Radius in meters for spatial filter (uses default if not provided)

        Returns:
            str: Overpass QL query string

        Example query output:
            [out:json];
            (
              node["sport"="padel"](around:50000,55.9533,-3.1883);
              way["sport"="padel"](around:50000,55.9533,-3.1883);
              relation["sport"="padel"](around:50000,55.9533,-3.1883);
            );
            out body;
            >;
            out skel qt;
        """
        # Use defaults if not provided
        lat = lat or self.default_lat
        lon = lon or self.default_lon
        radius = radius or self.default_radius

        # Build Overpass QL query
        # Search for nodes, ways, and relations with the query term in various tags
        overpass_query = f"""[out:json];
(
  node["sport"="{query}"](around:{radius},{lat},{lon});
  way["sport"="{query}"](around:{radius},{lat},{lon});
  relation["sport"="{query}"](around:{radius},{lat},{lon});
  node["leisure"~"{query}"](around:{radius},{lat},{lon});
  way["leisure"~"{query}"](around:{radius},{lat},{lon});
  relation["leisure"~"{query}"](around:{radius},{lat},{lon});
);
out body;
>;
out skel qt;"""

        return overpass_query

    async def fetch(self, query: str, lat: Optional[float] = None,
                   lon: Optional[float] = None, radius: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch sports facility data from OpenStreetMap Overpass API.

        Makes an HTTP POST request to the Overpass API with an Overpass QL query.
        Returns the raw JSON response containing OSM elements.

        Args:
            query: Search query (e.g., "padel", "tennis")
            lat: Optional latitude for spatial filter
            lon: Optional longitude for spatial filter
            radius: Optional radius in meters for spatial filter

        Returns:
            dict: Raw API response containing OSM elements

        Raises:
            aiohttp.ClientError: For network errors
            asyncio.TimeoutError: If request exceeds timeout
            Exception: For HTTP errors (4xx, 5xx status codes)

        Example:
            >>> connector = OSMConnector()
            >>> await connector.db.connect()
            >>> results = await connector.fetch("padel")
            >>> print(f"Found {len(results['elements'])} facilities")
            >>> await connector.db.disconnect()
        """
        # Build Overpass QL query
        overpass_query = self._build_overpass_query(query, lat, lon, radius)

        # Make API request (POST with query in body)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                data=overpass_query,
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
            ) as response:
                # Check for HTTP errors
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Overpass API request failed with status {response.status}: {error_text}"
                    )

                # Parse and return JSON response
                return await response.json()

    async def save(self, data: Dict[str, Any], source_url: str) -> str:
        """
        Save raw OSM data to filesystem and create database record.

        This method:
        1. Computes content hash for deduplication
        2. Generates unique file path based on element count and hash
        3. Saves JSON data to filesystem
        4. Creates RawIngestion database record with metadata

        Args:
            data: Raw OSM response dictionary from Overpass API
            source_url: Original API endpoint URL

        Returns:
            str: File path where data was saved

        Raises:
            IOError: If file cannot be written
            Exception: If database record cannot be created

        Example:
            >>> data = await connector.fetch("padel")
            >>> file_path = await connector.save(
            ...     data,
            ...     "https://overpass-api.de/api/interpreter?query=padel"
            ... )
            >>> print(file_path)
            'engine/data/raw/openstreetmap/20260113_elements_5_abc12345.json'
        """
        # Compute content hash for deduplication
        content_hash = compute_content_hash(data)

        # Extract element count for metadata
        element_count = len(data.get('elements', []))

        # Generate a simple record ID based on element count and hash
        record_id = f"elements_{element_count}_{content_hash[:8]}"

        # Generate unique file path
        file_path = generate_file_path(self.source_name, record_id)

        # Save JSON to filesystem
        save_json(file_path, data)

        # Prepare metadata as JSON string
        metadata = {
            'element_count': element_count,
            'api_version': '0.6'  # OSM API version
        }
        metadata_json_str = json.dumps(metadata)

        # Create database record
        await self.db.rawingestion.create(
            data={
                'source': self.source_name,
                'source_url': source_url,
                'file_path': file_path,
                'hash': content_hash,
                'status': 'success',
                'ingested_at': datetime.now(),
                'metadata_json': metadata_json_str
            }
        )

        return file_path

    async def is_duplicate(self, content_hash: str) -> bool:
        """
        Check if content with this hash has already been ingested.

        Queries the RawIngestion table to determine if we've already
        ingested data with this exact content hash. This prevents
        duplicate API calls and storage of identical query results.

        Args:
            content_hash: SHA-256 hash of the content to check

        Returns:
            bool: True if content already exists, False otherwise

        Example:
            >>> data = await connector.fetch("padel")
            >>> content_hash = compute_content_hash(data)
            >>> if await connector.is_duplicate(content_hash):
            ...     print("Already have this data")
            ... else:
            ...     await connector.save(data, source_url)
        """
        return await check_duplicate(self.db, content_hash)
