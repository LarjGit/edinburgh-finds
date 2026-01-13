"""
Deduplication Logic

This module provides hash-based deduplication to prevent re-ingesting the same
content from external sources. It uses SHA-256 hashing to create unique
fingerprints of data and queries the database to check for existing records.

Key Features:
- Deterministic hashing (same content always produces same hash)
- Order-independent hashing (dict key order doesn't matter)
- Efficient database lookups using hash indexes
- Works across all data sources (global deduplication)

Usage:
    from engine.ingestion.deduplication import compute_content_hash, check_duplicate

    # Hash the content
    data = {"query": "padel edinburgh", "results": [...]}
    content_hash = compute_content_hash(data)

    # Check if already ingested
    if await check_duplicate(db, content_hash):
        print("Already have this data, skipping")
    else:
        # Save new data...
"""

import json
import hashlib
from typing import Any, Dict
from prisma import Prisma


def compute_content_hash(data: Dict[str, Any]) -> str:
    """
    Compute a SHA-256 hash of the data content.

    Creates a deterministic hash that uniquely identifies the content.
    The hash is order-independent for dictionary keys, meaning the same
    data will always produce the same hash regardless of key ordering.

    Args:
        data: Dictionary containing the data to hash

    Returns:
        str: 64-character hexadecimal SHA-256 hash

    Example:
        >>> data = {"query": "padel", "count": 10}
        >>> hash1 = compute_content_hash(data)
        >>> hash2 = compute_content_hash({"count": 10, "query": "padel"})
        >>> hash1 == hash2
        True
        >>> len(hash1)
        64
    """
    # Convert to JSON with sorted keys for consistency
    # This ensures {"a": 1, "b": 2} and {"b": 2, "a": 1} produce the same hash
    json_string = json.dumps(data, sort_keys=True, ensure_ascii=False)

    # Encode to bytes and compute SHA-256 hash
    hash_bytes = hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    return hash_bytes


async def check_duplicate(db: Prisma, content_hash: str) -> bool:
    """
    Check if content with this hash has already been ingested.

    Queries the RawIngestion table to see if a record with the given
    hash already exists. This prevents duplicate ingestion of the same
    content from any source.

    Args:
        db: Prisma database client instance
        content_hash: SHA-256 hash of the content to check

    Returns:
        bool: True if content already exists, False otherwise

    Example:
        >>> db = Prisma()
        >>> await db.connect()
        >>> is_dup = await check_duplicate(db, "abc123...")
        >>> if is_dup:
        ...     print("Already have this content")
        >>> await db.disconnect()
    """
    # Query database for existing record with this hash
    existing = await db.rawingestion.find_first(
        where={"hash": content_hash}
    )

    # Return True if found, False if not
    return existing is not None
