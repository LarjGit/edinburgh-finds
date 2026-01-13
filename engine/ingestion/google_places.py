"""
Google Places API Connector

This module implements the GooglePlacesConnector for fetching venue and business
data from the Google Places API. The API provides comprehensive information about
places including name, location, contact details, ratings, and more.

The connector handles:
- API authentication and request formatting
- Rate limiting compliance
- Response parsing and validation
- Raw data persistence to filesystem and database
- Deduplication to prevent re-ingesting identical searches

API Documentation: https://developers.google.com/maps/documentation/places/web-service
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


class GooglePlacesConnector(BaseConnector):
    """
    Connector for the Google Places API.

    This connector fetches place data from Google Places API and stores it
    as raw JSON data for later extraction and processing.

    The Google Places API provides two main endpoints:
    1. Place Search (Text/Nearby) - Find places matching criteria
    2. Place Details - Get detailed information about a specific place

    Configuration:
        Loads settings from engine/config/sources.yaml including:
        - API key (required)
        - Base URL
        - Timeout settings
        - Rate limits
        - Default search parameters (location, radius)

    Usage:
        connector = GooglePlacesConnector()
        await connector.db.connect()

        # Fetch place search results
        data = await connector.fetch("padel edinburgh")

        # Check if already ingested
        content_hash = compute_content_hash(data)
        if not await connector.is_duplicate(content_hash):
            # Save new data
            file_path = await connector.save(data, "https://maps.googleapis.com/maps/api/place/textsearch/json")
            print(f"Saved to {file_path}")

        await connector.db.disconnect()
    """

    def __init__(self, config_path: str = "engine/config/sources.yaml"):
        """
        Initialize the Google Places connector with configuration.

        Args:
            config_path: Path to the sources.yaml configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If API key is missing or invalid
        """
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if 'google_places' not in config:
            raise ValueError("Google Places configuration not found in sources.yaml")

        google_places_config = config['google_places']

        # Validate API key
        self.api_key = google_places_config.get('api_key')
        if not self.api_key or self.api_key == "YOUR_GOOGLE_PLACES_API_KEY_HERE":
            raise ValueError(
                "Google Places API key not configured. "
                "Please set a valid API key in engine/config/sources.yaml"
            )

        # Load other configuration
        self.base_url = google_places_config.get('base_url', 'https://maps.googleapis.com/maps/api/place')
        self.timeout = google_places_config.get('timeout_seconds', 30)
        self.default_params = google_places_config.get('default_params', {})

        # Initialize database connection
        self.db = Prisma()

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "google_places"
        """
        return "google_places"

    async def fetch(self, query: str) -> Dict[str, Any]:
        """
        Fetch place search results from Google Places API.

        Makes an HTTP GET request to the Google Places Text Search API with
        the search query and configured parameters. Returns the raw JSON response.

        Args:
            query: Search query string (e.g., "padel edinburgh")

        Returns:
            dict: Raw API response containing place results

        Raises:
            aiohttp.ClientError: For network errors
            asyncio.TimeoutError: If request exceeds timeout
            Exception: For HTTP errors (4xx, 5xx status codes)

        Example:
            >>> connector = GooglePlacesConnector()
            >>> await connector.db.connect()
            >>> results = await connector.fetch("padel courts edinburgh")
            >>> print(results['results'][0]['name'])
            'Edinburgh Padel Club'
            >>> await connector.db.disconnect()
        """
        # Build request parameters
        params = {
            'query': query,
            'key': self.api_key,
            **self.default_params  # Include default params from config
        }

        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/textsearch/json",
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                # Check for HTTP errors
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Google Places API request failed with status {response.status}: {error_text}"
                    )

                # Parse and return JSON response
                return await response.json()

    async def save(self, data: Dict[str, Any], source_url: str) -> str:
        """
        Save raw place results to filesystem and create database record.

        This method:
        1. Computes content hash for deduplication
        2. Generates unique file path based on query and timestamp
        3. Saves JSON data to filesystem
        4. Creates RawIngestion database record with metadata

        Args:
            data: Raw place results dictionary from Google Places API
            source_url: Original API endpoint URL

        Returns:
            str: File path where data was saved

        Raises:
            IOError: If file cannot be written
            Exception: If database record cannot be created

        Example:
            >>> data = await connector.fetch("padel edinburgh")
            >>> file_path = await connector.save(data, "https://maps.googleapis.com/maps/api/place/textsearch/json")
            >>> print(file_path)
            'engine/data/raw/google_places/20260113_padel_edinburgh.json'
        """
        # Compute content hash for deduplication
        content_hash = compute_content_hash(data)

        # Extract result count for metadata
        result_count = len(data.get('results', []))

        # Generate a simple record ID based on status and hash
        status = data.get('status', 'unknown')
        record_id = f"{status.lower()}_{content_hash[:8]}"

        # Generate unique file path
        file_path = generate_file_path(self.source_name, record_id)

        # Save JSON to filesystem
        save_json(file_path, data)

        # Prepare metadata as JSON string
        metadata = {
            'result_count': result_count,
            'status': status
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
        duplicate API calls and storage of identical place results.

        Args:
            content_hash: SHA-256 hash of the content to check

        Returns:
            bool: True if content already exists, False otherwise

        Example:
            >>> data = await connector.fetch("padel edinburgh")
            >>> content_hash = compute_content_hash(data)
            >>> if await connector.is_duplicate(content_hash):
            ...     print("Already have this data")
            ... else:
            ...     await connector.save(data, source_url)
        """
        return await check_duplicate(self.db, content_hash)
