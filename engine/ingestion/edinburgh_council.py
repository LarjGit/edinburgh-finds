"""
Edinburgh Council ArcGIS Connector

This module implements the EdinburghCouncilConnector for fetching civic and
facility data from the City of Edinburgh Council's Open Spatial Data Portal.
This is an enrichment connector that supplements venue data with official
Edinburgh civic facility information.

The Edinburgh Council portal provides comprehensive data including:
- Community facilities (sports centers, libraries, community centers)
- Parks and green spaces
- Education facilities (schools, nurseries)
- Planning and property information
- Transportation infrastructure
- Public services and amenities

This connector enables cross-referencing venue listings with official
Edinburgh Council records, enriching profiles with civic context (ward,
neighborhood) and discovering publicly-owned facilities.

Portal: https://data.edinburghcouncilmaps.info/
Platform: ArcGIS Hub (ESRI)
License: Open Government License v3.0
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


class EdinburghCouncilConnector(BaseConnector):
    """
    Connector for Edinburgh Council Open Spatial Data Portal (ArcGIS Hub).

    This enrichment connector fetches official civic facility data from
    Edinburgh Council via ArcGIS REST API Feature Service queries, storing
    GeoJSON FeatureCollections for later processing and cross-referencing
    with venue listings.

    Configuration:
        Loads settings from engine/config/sources.yaml including:
        - Base URL (ArcGIS Hub portal)
        - Timeout settings
        - Query parameters (outFields, f, returnGeometry)
        - No API key required (public data)

    Available Datasets:
        The portal provides numerous datasets. Common examples:
        - Sports and leisure facilities
        - Community centers
        - Libraries
        - Parks and green spaces
        - Schools and education facilities
        - Planning applications
        - Property information

    Usage:
        connector = EdinburghCouncilConnector()
        await connector.db.connect()

        # Fetch sports facilities dataset
        data = await connector.fetch("sports_leisure_facilities_dataset_id")

        # Check if already ingested
        content_hash = compute_content_hash(data)
        if not await connector.is_duplicate(content_hash):
            # Save new data
            file_path = await connector.save(
                data,
                "https://data.edinburghcouncilmaps.info/datasets/..."
            )
            print(f"Saved {len(data['features'])} features to {file_path}")

        await connector.db.disconnect()
    """

    def __init__(self, config_path: str = "engine/config/sources.yaml"):
        """
        Initialize the Edinburgh Council connector with configuration.

        Args:
            config_path: Path to the sources.yaml configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required configuration is missing
        """
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if 'edinburgh_council' not in config:
            raise ValueError("Edinburgh Council configuration not found in sources.yaml")

        ec_config = config['edinburgh_council']

        # Load configuration (API key optional for public data)
        self.api_key = ec_config.get('api_key')  # May be None for public portal
        self.base_url = ec_config.get('base_url', 'https://data.edinburghcouncilmaps.info/datasets')
        self.timeout = ec_config.get('timeout_seconds', 30)
        self.default_params = ec_config.get('default_params', {})

        # Initialize database connection
        self.db = Prisma()

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "edinburgh_council"
        """
        return "edinburgh_council"

    async def fetch(self, query: str) -> Dict[str, Any]:
        """
        Fetch civic facility data from Edinburgh Council ArcGIS REST API.

        Makes an HTTP GET request to the ArcGIS Feature Service query endpoint,
        requesting GeoJSON format for easy parsing. The query parameter should be
        the dataset ID or feature service identifier.

        Args:
            query: Dataset ID or feature service name (e.g., "sports_facilities")

        Returns:
            dict: GeoJSON FeatureCollection containing facility data

        Raises:
            ValueError: If query (dataset ID) is empty
            aiohttp.ClientError: For network errors
            asyncio.TimeoutError: If request exceeds timeout
            Exception: For HTTP errors (4xx, 5xx status codes)

        Example:
            >>> connector = EdinburghCouncilConnector()
            >>> await connector.db.connect()
            >>> features = await connector.fetch("sports_facilities")
            >>> print(f"Found {len(features['features'])} facilities")
            Found 25 facilities
            >>> await connector.db.disconnect()
        """
        # Validate dataset ID
        if not query or query.strip() == "":
            raise ValueError("Dataset ID cannot be empty")

        dataset_id = query.strip()

        # Build ArcGIS REST API query parameters
        params = {
            **self.default_params,  # outFields, f, returnGeometry
            'where': '1=1'  # Get all records (can be customized for filtering)
        }

        # Add API token if configured (for premium/restricted datasets)
        if self.api_key:
            params['token'] = self.api_key

        # Build Feature Service query URL
        # Format: {base_url}/{dataset_id}/query
        query_url = f"{self.base_url}/{dataset_id}/query"

        # Make ArcGIS REST API request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                query_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                # Check for HTTP errors
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Edinburgh Council API request failed with status {response.status}: {error_text}"
                    )

                # Parse and return GeoJSON FeatureCollection
                return await response.json()

    async def save(self, data: Dict[str, Any], source_url: str) -> str:
        """
        Save raw civic facility data to filesystem and create database record.

        This method:
        1. Computes content hash for deduplication
        2. Generates unique file path based on dataset and feature count
        3. Saves GeoJSON FeatureCollection to filesystem
        4. Creates RawIngestion database record with metadata

        Args:
            data: GeoJSON FeatureCollection from Edinburgh Council
            source_url: Original query URL

        Returns:
            str: File path where data was saved

        Raises:
            IOError: If file cannot be written
            Exception: If database record cannot be created

        Example:
            >>> data = await connector.fetch("sports_facilities")
            >>> file_path = await connector.save(
            ...     data,
            ...     "https://data.edinburghcouncilmaps.info/datasets/sports_facilities/query"
            ... )
            >>> print(file_path)
            'engine/data/raw/edinburgh_council/20260114_sports_facilities_25_12345678.json'
        """
        # Compute content hash for deduplication
        content_hash = compute_content_hash(data)

        # Extract metadata from FeatureCollection
        features = data.get('features', [])
        feature_count = len(features)

        # Determine dataset type from URL or data
        dataset_type = 'facilities'  # default
        if '/datasets/' in source_url:
            # Extract from URL: .../datasets/sports_facilities/query
            try:
                url_parts = source_url.split('/datasets/')[1].split('/')[0]
                dataset_type = url_parts.replace('-', '_')[:50]  # Limit length
            except (IndexError, AttributeError):
                pass

        # Generate unique file path
        record_id = f"{dataset_type}_{feature_count}_{content_hash[:8]}"
        file_path = generate_file_path(self.source_name, record_id)

        # Save GeoJSON to filesystem
        save_json(file_path, data)

        # Prepare metadata as JSON string
        metadata = {
            'feature_count': feature_count,
            'dataset_type': dataset_type,
            'portal': 'ArcGIS Hub - City of Edinburgh Council'
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
            >>> data = await connector.fetch("sports_facilities")
            >>> content_hash = compute_content_hash(data)
            >>> if await connector.is_duplicate(content_hash):
            ...     print("Already have this data")
            ... else:
            ...     await connector.save(data, source_url)
        """
        return await check_duplicate(self.db, content_hash)
