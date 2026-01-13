"""
Data Ingestion Module

This module provides a modular, extensible framework for ingesting raw data from
multiple external sources (APIs, web scraping, open data feeds) and storing it
with metadata for later structured extraction.

Key Components:
- BaseConnector: Abstract base class defining the interface for all data source connectors
- Storage Helpers: Filesystem utilities for organizing and saving raw data
- Deduplication: Hash-based logic to prevent duplicate ingestion
- Configuration: Source-specific settings (API keys, rate limits, etc.)

Architecture:
Raw data is stored in the filesystem at `engine/data/raw/<source>/` while
metadata (source, URL, file path, status, hash) is tracked in the RawIngestion
database table. This hybrid approach separates concerns and maintains portability
for future migrations (e.g., to Supabase storage).

Usage:
Each source connector extends BaseConnector and implements source-specific
fetching logic while leveraging shared infrastructure for storage, deduplication,
and error handling.
"""

from engine.ingestion.base import BaseConnector
from engine.ingestion import storage
from engine.ingestion import deduplication

__version__ = "0.1.0"
__all__ = ["BaseConnector", "storage", "deduplication"]
