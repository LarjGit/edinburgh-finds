"""
OpenChargeMap API Connector

This module implements the OpenChargeMapConnector for fetching EV charging
station data from the OpenChargeMap API. This is an enrichment connector
that supplements venue data with nearby charging infrastructure information.

The OpenChargeMap API provides comprehensive EV charging station information:
- Location data (latitude, longitude, address)
- Charging point details (connectors, power output, network)
- Availability and access information
- Pricing and payment methods

This connector enables us to enrich venue listings with nearby charging
facilities, which is valuable for venues (e.g., Padel courts) where users
may travel by electric vehicle.

API Documentation: https://openchargemap.org/site/develop/api
"""

import os
import json
import yaml
import aiohttp
from typing import Dict, Any, List
from datetime import datetime
from prisma import Prisma

from engine.ingestion.base import BaseConnector
from engine.ingestion.storage import generate_file_path, save_json
from engine.ingestion.deduplication import compute_content_hash, check_duplicate


class OpenChargeMapConnector(BaseConnector):
    """
    Connector for the OpenChargeMap API (EV charging station data).

    This enrichment connector fetches nearby EV charging stations based on
    latitude/longitude coordinates and stores them as raw JSON data for
    later processing and association with venue listings.

    Configuration:
        Loads settings from engine/config/sources.yaml including:
        - API key (required)
        - Base URL
        - Timeout settings
        - Rate limits
        - Default search parameters (countrycode, maxresults)

    Usage:
        connector = OpenChargeMapConnector()
        await connector.db.connect()

        # Fetch charging stations near Edinburgh city center
        data = await connector.fetch("55.9533,-3.1883")

        # Check if already ingested
        content_hash = compute_content_hash(data)
        if not await connector.is_duplicate(content_hash):
            # Save new data
            file_path = await connector.save(
                data,
                "https://api.openchargemap.io/v3/poi/?latitude=55.9533&longitude=-3.1883"
            )
            print(f"Saved to {file_path}")

        await connector.db.disconnect()
    """

    def __init__(self, config_path: str = "engine/config/sources.yaml"):
        """
        Initialize the OpenChargeMap connector with configuration.

        Args:
            config_path: Path to the sources.yaml configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If API key is missing or invalid
        """
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if 'open_charge_map' not in config:
            raise ValueError("OpenChargeMap configuration not found in sources.yaml")

        ocm_config = config['open_charge_map']

        # Validate API key
        self.api_key = ocm_config.get('api_key')
        if not self.api_key or self.api_key == "YOUR_OPENCHARGEMAP_API_KEY_HERE":
            raise ValueError(
                "OpenChargeMap API key not configured. "
                "Please set a valid API key in engine/config/sources.yaml"
            )

        # Load other configuration
        self.base_url = ocm_config.get('base_url', 'https://api.openchargemap.io/v3')
        self.timeout = ocm_config.get('timeout_seconds', 30)
        self.default_params = ocm_config.get('default_params', {})

        # Initialize database connection
        self.db = Prisma()

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "open_charge_map"
        """
        return "open_charge_map"

    async def fetch(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch nearby EV charging stations from OpenChargeMap API.

        Makes an HTTP GET request to the OpenChargeMap API with latitude
        and longitude coordinates. Returns the raw JSON response containing
        charging station data.

        Args:
            query: Coordinates as "latitude,longitude" (e.g., "55.9533,-3.1883")

        Returns:
            list: Raw API response containing charging station data

        Raises:
            ValueError: If query format is invalid (not "lat,lng")
            aiohttp.ClientError: For network errors
            asyncio.TimeoutError: If request exceeds timeout
            Exception: For HTTP errors (4xx, 5xx status codes)

        Example:
            >>> connector = OpenChargeMapConnector()
            >>> await connector.db.connect()
            >>> stations = await connector.fetch("55.9533,-3.1883")
            >>> print(f"Found {len(stations)} charging stations")
            Found 15 charging stations
            >>> await connector.db.disconnect()
        """
        # Parse latitude and longitude from query
        try:
            lat, lng = query.split(',')
            latitude = lat.strip()
            longitude = lng.strip()
        except ValueError:
            raise ValueError(
                f"Invalid coordinates format: '{query}'. "
                "Expected format: 'latitude,longitude' (e.g., '55.9533,-3.1883')"
            )

        # Build request parameters
        params = {
            'key': self.api_key,
            'latitude': latitude,
            'longitude': longitude,
            **self.default_params  # Include default params from config
        }

        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/poi/",
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                # Check for HTTP errors
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"OpenChargeMap API request failed with status {response.status}: {error_text}"
                    )

                # Parse and return JSON response
                return await response.json()

    async def save(self, data: List[Dict[str, Any]], source_url: str) -> str:
        """
        Save raw charging station data to filesystem and create database record.

        This method:
        1. Computes content hash for deduplication
        2. Generates unique file path based on coordinates and timestamp
        3. Saves JSON data to filesystem
        4. Creates RawIngestion database record with metadata

        Args:
            data: Raw charging station list from OpenChargeMap API
            source_url: Original API endpoint URL

        Returns:
            str: File path where data was saved

        Raises:
            IOError: If file cannot be written
            Exception: If database record cannot be created

        Example:
            >>> data = await connector.fetch("55.9533,-3.1883")
            >>> file_path = await connector.save(
            ...     data,
            ...     "https://api.openchargemap.io/v3/poi/?latitude=55.9533&longitude=-3.1883"
            ... )
            >>> print(file_path)
            'engine/data/raw/open_charge_map/20260114_edinburgh_12345678.json'
        """
        # Compute content hash for deduplication
        content_hash = compute_content_hash(data)

        # Extract location info for file naming (if available)
        if data and len(data) > 0:
            # Use first station's location as identifier
            first_station = data[0]
            address_info = first_station.get('AddressInfo', {})
            town = address_info.get('Town', 'unknown')
            location_slug = town.replace(' ', '_').lower()[:30]
        else:
            location_slug = 'empty'

        # Generate unique file path
        record_id = f"{location_slug}_{content_hash[:8]}"
        file_path = generate_file_path(self.source_name, record_id)

        # Save JSON to filesystem
        save_json(file_path, data)

        # Prepare metadata as JSON string
        metadata = {
            'station_count': len(data),
            'location': location_slug if location_slug != 'empty' else None,
            'query_url': source_url
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
        duplicate API calls and storage of identical charging station data.

        Args:
            content_hash: SHA-256 hash of the content to check

        Returns:
            bool: True if content already exists, False otherwise

        Example:
            >>> data = await connector.fetch("55.9533,-3.1883")
            >>> content_hash = compute_content_hash(data)
            >>> if await connector.is_duplicate(content_hash):
            ...     print("Already have this data")
            ... else:
            ...     await connector.save(data, source_url)
        """
        return await check_duplicate(self.db, content_hash)
