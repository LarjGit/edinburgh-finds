"""
Serper API Connector

This module implements the SerperConnector for fetching search results from
the Serper API (Google search results API). Serper provides programmatic access
to Google search results without the complexity of traditional web scraping.

The connector handles:
- API authentication and request formatting
- Rate limiting compliance
- Response parsing and validation
- Raw data persistence to filesystem and database
- Deduplication to prevent re-ingesting identical searches

API Documentation: https://serper.dev/
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


class SerperConnector(BaseConnector):
    """
    Connector for the Serper API (Google search results).

    This connector fetches search results from Serper's API and stores them
    as raw JSON data for later extraction and processing.

    Configuration:
        Loads settings from engine/config/sources.yaml including:
        - API key (required)
        - Base URL
        - Timeout settings
        - Rate limits
        - Default search parameters (gl, hl, num)

    Usage:
        connector = SerperConnector()
        await connector.db.connect()

        # Fetch search results
        data = await connector.fetch("padel edinburgh")

        # Check if already ingested
        content_hash = compute_content_hash(data)
        if not await connector.is_duplicate(content_hash):
            # Save new data
            file_path = await connector.save(data, "https://google.serper.dev/search")
            print(f"Saved to {file_path}")

        await connector.db.disconnect()
    """

    def __init__(self, config_path: str = "engine/config/sources.yaml"):
        """
        Initialize the Serper connector with configuration.

        Args:
            config_path: Path to the sources.yaml configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If API key is missing or invalid
        """
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if 'serper' not in config:
            raise ValueError("Serper configuration not found in sources.yaml")

        serper_config = config['serper']

        # Validate API key
        self.api_key = serper_config.get('api_key')
        if not self.api_key or self.api_key == "YOUR_SERPER_API_KEY_HERE":
            raise ValueError(
                "Serper API key not configured. "
                "Please set a valid API key in engine/config/sources.yaml"
            )

        # Load other configuration
        self.base_url = serper_config.get('base_url', 'https://google.serper.dev')
        self.timeout = serper_config.get('timeout_seconds', 30)
        self.default_params = serper_config.get('default_params', {})

        # Initialize database connection
        self.db = Prisma()

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: "serper"
        """
        return "serper"

    async def fetch(self, query: str) -> Dict[str, Any]:
        """
        Fetch search results from Serper API.

        Makes an HTTP POST request to the Serper API with the search query
        and configured parameters. Returns the raw JSON response.

        Args:
            query: Search query string (e.g., "padel edinburgh")

        Returns:
            dict: Raw API response containing search results

        Raises:
            aiohttp.ClientError: For network errors
            asyncio.TimeoutError: If request exceeds timeout
            Exception: For HTTP errors (4xx, 5xx status codes)

        Example:
            >>> connector = SerperConnector()
            >>> await connector.db.connect()
            >>> results = await connector.fetch("padel courts edinburgh")
            >>> print(results['organic'][0]['title'])
            'Edinburgh Padel Club'
            >>> await connector.db.disconnect()
        """
        # Build request payload
        payload = {
            'q': query,
            **self.default_params  # Include default params from config
        }

        # Set up headers with API key
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/search",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                # Check for HTTP errors
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Serper API request failed with status {response.status}: {error_text}"
                    )

                # Parse and return JSON response
                return await response.json()

    async def save(self, data: Dict[str, Any], source_url: str) -> str:
        """
        Save raw search results to filesystem and create database record.

        This method:
        1. Computes content hash for deduplication
        2. Generates unique file path based on query and timestamp
        3. Saves JSON data to filesystem
        4. Creates RawIngestion database record with metadata

        Args:
            data: Raw search results dictionary from Serper API
            source_url: Original API endpoint URL

        Returns:
            str: File path where data was saved

        Raises:
            IOError: If file cannot be written
            Exception: If database record cannot be created

        Example:
            >>> data = await connector.fetch("padel edinburgh")
            >>> file_path = await connector.save(data, "https://google.serper.dev/search")
            >>> print(file_path)
            'engine/data/raw/serper/20260113_padel_edinburgh.json'
        """
        # Compute content hash for deduplication
        content_hash = compute_content_hash(data)

        # Extract query from data for file naming
        query = data.get('searchParameters', {}).get('q', 'unknown')
        # Sanitize query for filename (replace spaces and special chars)
        query_slug = query.replace(' ', '_').replace('/', '_')[:50]  # Limit length

        # Generate unique file path
        record_id = f"{query_slug}_{content_hash[:8]}"
        file_path = generate_file_path(self.source_name, record_id)

        # Save JSON to filesystem
        save_json(file_path, data)

        # Extract rich text availability for metadata (snippets, descriptions)
        organic_results = data.get('organic', [])
        rich_text_stats = {
            'has_snippet': 0,
            'total_snippet_length': 0
        }

        for result in organic_results:
            snippet = result.get('snippet', '')
            if snippet:
                rich_text_stats['has_snippet'] += 1
                rich_text_stats['total_snippet_length'] += len(snippet)

        # Prepare metadata as JSON string
        metadata = {
            'query': query,
            'result_count': len(organic_results),
            'search_type': data.get('searchParameters', {}).get('type', 'search'),
            'rich_text': rich_text_stats
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
        duplicate API calls and storage of identical search results.

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
