"""
Filesystem Storage Helpers

This module provides utility functions for managing raw data storage on the
filesystem. It handles directory creation, file path generation, and JSON
persistence following a consistent organizational structure.

Storage Organization:
    engine/data/raw/
    ├── serper/
    │   ├── 20260113_query1.json
    │   └── 20260113_query2.json
    ├── google_places/
    │   └── 20260113_place1.json
    └── osm/
        └── 20260113_facility1.json

All raw data is stored as JSON files with timestamps for easy chronological
organization and debugging.
"""

import os
import json
from datetime import datetime
from typing import Any, Dict


def get_raw_data_dir() -> str:
    """
    Get the base directory for all raw ingestion data.

    Returns:
        str: Base directory path "engine/data/raw"

    Example:
        >>> base_dir = get_raw_data_dir()
        >>> print(base_dir)
        'engine/data/raw'
    """
    # Use forward slashes for cross-platform consistency
    return os.path.join("engine", "data", "raw").replace(os.sep, "/")


def get_source_dir(source: str) -> str:
    """
    Get the directory path for a specific data source.

    Args:
        source: Name of the data source (e.g., "serper", "google_places")

    Returns:
        str: Source-specific directory path

    Example:
        >>> source_dir = get_source_dir("serper")
        >>> print(source_dir)
        'engine/data/raw/serper'
    """
    # Use forward slashes for cross-platform consistency
    return os.path.join(get_raw_data_dir(), source).replace(os.sep, "/")


def generate_file_path(source: str, record_id: str) -> str:
    """
    Generate a unique file path for storing raw data.

    Creates a path following the convention:
    engine/data/raw/<source>/<YYYYMMDD>_<record_id>.json

    The timestamp helps organize files chronologically and the record_id
    ensures uniqueness within a single day.

    Args:
        source: Name of the data source (e.g., "serper", "osm")
        record_id: Unique identifier for this record (e.g., query hash, place ID)

    Returns:
        str: Complete file path for storing the data

    Example:
        >>> path = generate_file_path("serper", "padel_edinburgh")
        >>> print(path)
        'engine/data/raw/serper/20260113_padel_edinburgh.json'
    """
    # Get current date in YYYYMMDD format
    timestamp = datetime.now().strftime("%Y%m%d")

    # Create filename: <timestamp>_<record_id>.json
    filename = f"{timestamp}_{record_id}.json"

    # Build full path with forward slashes for cross-platform consistency
    return os.path.join(get_source_dir(source), filename).replace(os.sep, "/")


def ensure_directory_exists(file_path: str) -> None:
    """
    Ensure the directory for a file path exists, creating it if necessary.

    This function is idempotent - it's safe to call multiple times.
    It creates all intermediate directories as needed.

    Args:
        file_path: Complete file path (directory will be extracted)

    Example:
        >>> file_path = "engine/data/raw/serper/data.json"
        >>> ensure_directory_exists(file_path)
        # Directory engine/data/raw/serper/ now exists
    """
    directory = os.path.dirname(file_path)
    if directory:  # Only create if there's a directory component
        os.makedirs(directory, exist_ok=True)


def save_json(file_path: str, data: Dict[str, Any]) -> None:
    """
    Save data as a formatted JSON file.

    The JSON is saved with indentation for human readability and debugging.
    The directory is created automatically if it doesn't exist.

    Args:
        file_path: Complete path where JSON file should be saved
        data: Dictionary to serialize as JSON

    Raises:
        IOError: If file cannot be written
        TypeError: If data cannot be serialized to JSON

    Example:
        >>> data = {"query": "padel edinburgh", "results": []}
        >>> save_json("engine/data/raw/serper/test.json", data)
        # File created with pretty-printed JSON
    """
    # Ensure directory exists
    ensure_directory_exists(file_path)

    # Write JSON with indentation for readability
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
