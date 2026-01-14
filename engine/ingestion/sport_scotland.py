"""
SportScotland WFS Connector

This module implements the SportScotlandConnector for fetching sports facility
data from SportScotland's WFS (Web Feature Service) via the Spatial Hub Scotland
portal. This is an enrichment connector that supplements venue data with official
Scottish sports facility information.

SportScotland provides comprehensive sports facility data including:
- 11 themed facility layers (pitches, tennis courts, pools, athletics tracks, etc.)
- Location data with accurate coordinates (validated against Google Maps)
- Facility attributes (type, surface, size, capacity, ownership)
- Operational status and accessibility information

This connector enables cross-referencing venue listings with official SportScotland
records, enriching profiles with verified facility details and discovering venues
not yet in our system.

API Documentation: https://data.spatialhub.scot/dataset/sports_facilities-unknown
WFS Standard: OGC Web Feature Service 2.0.0
"""

import os
import json
import yaml
import aiohttp
from typing import Dict, Any
from datetime import datetime
from prisma import Prisma

from engine.ingestion.base import BaseConnector
from engine.ingestion.storage import generate_file_path, save_json
from engine.ingestion.deduplication import compute_content_hash, check_duplicate


class SportScotlandConnector(BaseConnector):
    """
    Connector for SportScotland WFS (Web Feature Service) - sports facility data.

    This enrichment connector fetches official sports facility data from
    SportScotland via WFS GetFeature requests, storing GeoJSON FeatureCollections
    for later processing and cross-referencing with venue listings.

    Configuration:
        Loads settings from engine/config/sources.yaml including:
        - Base WFS URL
        - Timeout settings
        - WFS parameters (service, version, request, outputFormat, srsName)
        - Edinburgh bounding box for spatial filtering
        - Rate limits

    Available Layers:
        - pitches: Sports pitches (football, rugby, hockey, etc.)
        - tennis_courts: Indoor and outdoor tennis facilities
        - swimming_pools: Swimming and diving pools
        - sports_halls: Indoor sports halls and gyms
        - golf_courses: Golf facilities
        - athletics_tracks: Running tracks and velodromes
        - bowling_greens: Bowling, croquet, petanque
        - fitness_suites: Fitness centers
        - ice_rinks: Ice skating and curling
        - squash_courts: Squash facilities

    Usage:
        connector = SportScotlandConnector()
        await connector.db.connect()

        # Fetch tennis courts in Edinburgh
        data = await connector.fetch("tennis_courts")

        # Check if already ingested
        content_hash = compute_content_hash(data)
        if not await connector.is_duplicate(content_hash):
            # Save new data
            file_path = await connector.save(
                data,
                "https://data.spatialhub.scot/geoserver/sport_scotland/wfs?..."
            )
            print(f"Saved {len(data['features'])} features to {file_path}")

        await connector.db.disconnect()
    """

    def __init__(self, config_path: str = "engine/config/sources.yaml"):
        """
        Initialize the SportScotland WFS connector with configuration.

        Args:
            config_path: Path to the sources.yaml configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required configuration is missing
        """
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if 'sport_scotland' not in config:
            raise ValueError("SportScotland configuration not found in sources.yaml")

        ss_config = config['sport_scotland']

        # Load configuration
        self.api_key = ss_config.get('api_key')  # WFS typically doesn't need key
        self.base_url = ss_config.get('base_url', 'https://data.spatialhub.scot/geoserver/sport_scotland/wfs')
        self.timeout = ss_config.get('timeout_seconds', 60)
        self.default_params = ss_config.get('default_params', {})

        # Load Edinburgh bounding box for spatial filtering
        self.edinburgh_bbox = ss_config.get('edinburgh_bbox', {
            'minx': -3.4,
            'miny': 55.85,
            'maxx': -3.0,
            'maxy': 56.0
        })

        # Initialize database connection
        self.db = Prisma()

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "sport_scotland"
        """
        return "sport_scotland"

    def _build_bbox_string(self) -> str:
        """
        Build WFS bbox parameter string from Edinburgh boundaries.

        Returns:
            str: Comma-separated bbox (minx,miny,maxx,maxy)

        Example:
            "-3.4,55.85,-3.0,56.0"
        """
        bbox = self.edinburgh_bbox
        return f"{bbox['minx']},{bbox['miny']},{bbox['maxx']},{bbox['maxy']}"

    async def fetch(self, query: str) -> Dict[str, Any]:
        """
        Fetch sports facilities from SportScotland WFS by layer name.

        Makes an HTTP GET request to the WFS endpoint with GetFeature parameters,
        requesting GeoJSON format for easy parsing. Filters results to Edinburgh
        area using bounding box spatial filter.

        Args:
            query: WFS layer name (e.g., "pitches", "tennis_courts", "swimming_pools")

        Returns:
            dict: GeoJSON FeatureCollection containing facility data

        Raises:
            ValueError: If query (layer name) is empty
            aiohttp.ClientError: For network errors
            asyncio.TimeoutError: If request exceeds timeout
            Exception: For HTTP errors (4xx, 5xx status codes)

        Example:
            >>> connector = SportScotlandConnector()
            >>> await connector.db.connect()
            >>> features = await connector.fetch("tennis_courts")
            >>> print(f"Found {len(features['features'])} tennis courts")
            Found 15 tennis courts
            >>> await connector.db.disconnect()
        """
        # Validate layer name
        if not query or query.strip() == "":
            raise ValueError("Layer name cannot be empty")

        layer_name = query.strip()

        # Build WFS GetFeature request parameters
        params = {
            **self.default_params,  # service, version, request, outputFormat, srsName
            'typeName': f'sh_sptk:{layer_name}',  # Namespaced layer name (Spatial Hub SportScotland workspace)
            'bbox': self._build_bbox_string()  # Edinburgh spatial filter
        }

        # Add API token if configured (Spatial Hub uses 'authkey' parameter)
        if self.api_key:
            params['authkey'] = self.api_key

        # Make WFS request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.base_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                # Check for HTTP errors
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"SportScotland WFS request failed with status {response.status}: {error_text}"
                    )

                # Parse and return GeoJSON FeatureCollection
                return await response.json()

    async def save(self, data: Dict[str, Any], source_url: str) -> str:
        """
        Save raw sports facility data to filesystem and create database record.

        This method:
        1. Computes content hash for deduplication
        2. Generates unique file path based on layer and feature count
        3. Saves GeoJSON FeatureCollection to filesystem
        4. Creates RawIngestion database record with metadata

        Args:
            data: GeoJSON FeatureCollection from SportScotland WFS
            source_url: Original WFS request URL

        Returns:
            str: File path where data was saved

        Raises:
            IOError: If file cannot be written
            Exception: If database record cannot be created

        Example:
            >>> data = await connector.fetch("pitches")
            >>> file_path = await connector.save(
            ...     data,
            ...     "https://data.spatialhub.scot/geoserver/sport_scotland/wfs?..."
            ... )
            >>> print(file_path)
            'engine/data/raw/sport_scotland/20260114_pitches_25_12345678.json'
        """
        # Compute content hash for deduplication
        content_hash = compute_content_hash(data)

        # Extract metadata from FeatureCollection
        features = data.get('features', [])
        feature_count = len(features)

        # Determine layer type from features or URL
        layer_type = 'facilities'  # default
        if 'typeName=' in source_url:
            # Extract from URL: typeName=sport_scotland:pitches
            try:
                type_param = source_url.split('typeName=')[1].split('&')[0]
                if ':' in type_param:
                    layer_type = type_param.split(':')[1]
                else:
                    layer_type = type_param
            except (IndexError, AttributeError):
                pass

        # Generate unique file path
        record_id = f"{layer_type}_{feature_count}_{content_hash[:8]}"
        file_path = generate_file_path(self.source_name, record_id)

        # Save GeoJSON to filesystem
        save_json(file_path, data)

        # Prepare metadata as JSON string
        metadata = {
            'feature_count': feature_count,
            'layer_type': layer_type,
            'total_features': data.get('totalFeatures', feature_count),
            'crs': data.get('crs', {}).get('properties', {}).get('name', 'EPSG:4326')
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
        duplicate API calls and storage of identical facility data.

        Args:
            content_hash: SHA-256 hash of the content to check

        Returns:
            bool: True if content already exists, False otherwise

        Example:
            >>> data = await connector.fetch("tennis_courts")
            >>> content_hash = compute_content_hash(data)
            >>> if await connector.is_duplicate(content_hash):
            ...     print("Already have this data")
            ... else:
            ...     await connector.save(data, source_url)
        """
        return await check_duplicate(self.db, content_hash)
