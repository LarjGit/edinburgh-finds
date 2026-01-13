"""
Base Connector Interface

This module defines the abstract BaseConnector class that serves as the
interface contract for all data source connectors in the ingestion pipeline.

All concrete connector implementations (e.g., Serper, Google Places, OSM)
must inherit from BaseConnector and implement its abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.

    This class defines the interface that all connectors must implement,
    ensuring consistency across different data sources while allowing
    source-specific customization.

    Key Responsibilities:
    - Fetch data from external sources (APIs, web scraping, etc.)
    - Save raw data to filesystem with proper organization
    - Check for duplicate content to prevent re-ingestion
    - Provide source identification for metadata tracking

    Concrete implementations must define:
    - source_name: Unique identifier for the data source
    - fetch(): Source-specific logic to retrieve data
    - save(): Persist raw data to filesystem and database
    - is_duplicate(): Check if content has already been ingested
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Unique identifier for this data source.

        Returns:
            str: Source name (e.g., "serper", "google_places", "osm")

        Example:
            @property
            def source_name(self) -> str:
                return "serper"
        """
        pass

    @abstractmethod
    async def fetch(self, query: str) -> dict:
        """
        Fetch data from the external source.

        This method implements the source-specific logic for retrieving
        data. It should handle API authentication, request formatting,
        and response parsing.

        Args:
            query: Search query or identifier for data retrieval

        Returns:
            dict: Raw response data from the source

        Raises:
            Exception: Source-specific errors (network, auth, rate limiting, etc.)

        Example:
            async def fetch(self, query: str) -> dict:
                response = await self.api_client.search(query)
                return response.json()
        """
        pass

    @abstractmethod
    async def save(self, data: dict, source_url: str) -> str:
        """
        Save raw data to filesystem and create metadata record.

        This method should:
        1. Generate appropriate file path based on source and timestamp
        2. Save raw JSON data to filesystem
        3. Create RawIngestion database record with metadata
        4. Return the file path for reference

        Args:
            data: Raw data dictionary to save
            source_url: Original URL or identifier where data was fetched from

        Returns:
            str: File path where data was saved (e.g., "engine/data/raw/serper/20260113_123.json")

        Raises:
            IOError: If file cannot be written
            Exception: If database record cannot be created

        Example:
            async def save(self, data: dict, source_url: str) -> str:
                file_path = self._generate_file_path()
                self._write_json(file_path, data)
                await self._create_db_record(file_path, source_url)
                return file_path
        """
        pass

    @abstractmethod
    async def is_duplicate(self, content_hash: str) -> bool:
        """
        Check if content with this hash has already been ingested.

        This method prevents duplicate ingestion by checking the RawIngestion
        table for existing records with the same content hash.

        Args:
            content_hash: Hash of the content to check (e.g., SHA-256)

        Returns:
            bool: True if content already exists, False otherwise

        Example:
            async def is_duplicate(self, content_hash: str) -> bool:
                existing = await self.db.rawingestion.find_first(
                    where={"hash": content_hash}
                )
                return existing is not None
        """
        pass
