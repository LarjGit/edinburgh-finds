"""
LLM Extraction Caching System

This module provides caching for LLM extraction results to reduce API costs
and improve performance. Caches are stored in the ExtractedListing table using
extraction_hash as the cache key.

Cache Strategy:
- Cache key = SHA-256(raw_data + prompt + model_name)
- Cache storage = ExtractedListing table (extraction_hash field)
- Cache hit = Return existing ExtractedListing without LLM call
- Cache miss = Make LLM call and store result

Benefits:
- Eliminates redundant LLM API calls for identical extractions
- Reduces costs (LLM calls are expensive)
- Improves performance (cached results are instant)
- Preserves full extraction history for audit
"""

import hashlib
import json
from typing import Dict, Any, Optional
from prisma import Prisma

try:
    from engine.extraction.logging_config import get_extraction_logger
    logger = get_extraction_logger()
except ImportError:
    from extraction.logging_config import get_extraction_logger
    logger = get_extraction_logger()


def compute_cache_key(raw_data: Dict[str, Any], prompt: str, model: str) -> str:
    """
    Compute deterministic cache key from extraction inputs.

    The cache key is a SHA-256 hash of:
    - Raw data (JSON-serialized with sorted keys for consistency)
    - Extraction prompt
    - Model name (different models may produce different results)

    Args:
        raw_data: The raw input data dictionary
        prompt: The extraction prompt text
        model: The LLM model name (e.g., "claude-haiku-20250318")

    Returns:
        64-character hex string (SHA-256 hash)

    Example:
        >>> raw = {"name": "Venue", "address": "123 St"}
        >>> key = compute_cache_key(raw, "Extract venue", "claude-haiku")
        >>> len(key)
        64
    """
    # Serialize raw data with sorted keys for consistency
    raw_json = json.dumps(raw_data, sort_keys=True, separators=(',', ':'))

    # Combine all inputs
    cache_input = f"{raw_json}|{prompt}|{model}"

    # Compute SHA-256 hash
    hash_obj = hashlib.sha256(cache_input.encode('utf-8'))
    return hash_obj.hexdigest()


async def check_llm_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Check if cached extraction exists for the given cache key.

    Args:
        cache_key: The extraction cache key (SHA-256 hash)

    Returns:
        Dictionary with cached extraction data if found, None otherwise.
        Contains keys: 'attributes', 'discovered_attributes', 'external_ids',
        'model_used', 'source', 'entity_type'

    Example:
        >>> cached = await check_llm_cache("abc123...")
        >>> if cached:
        ...     print(f"Cache hit! Saved ${cost}")
        ... else:
        ...     result = await llm_client.extract(...)
    """
    db = Prisma()
    await db.connect()

    try:
        # Look for ExtractedListing with matching extraction_hash
        record = await db.extractedlisting.find_first(
            where={"extraction_hash": cache_key}
        )

        if record is None:
            logger.debug(f"Cache miss for key: {cache_key[:16]}...")
            return None

        logger.info(f"Cache hit for key: {cache_key[:16]}... (saved LLM call)")

        # Parse JSON fields
        attributes = json.loads(record.attributes) if record.attributes else {}
        discovered_attributes = (
            json.loads(record.discovered_attributes)
            if record.discovered_attributes
            else {}
        )
        external_ids = (
            json.loads(record.external_ids) if record.external_ids else {}
        )

        return {
            "attributes": attributes,
            "discovered_attributes": discovered_attributes,
            "external_ids": external_ids,
            "model_used": record.model_used,
            "source": record.source,
            "entity_type": record.entity_type,
        }

    finally:
        await db.disconnect()


async def store_llm_cache(
    cache_key: str,
    source: str,
    entity_type: str,
    attributes: Dict[str, Any],
    model_used: str,
    raw_ingestion_id: str,
    discovered_attributes: Optional[Dict[str, Any]] = None,
    external_ids: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Store LLM extraction result in cache.

    Note: This function is primarily used internally by extractors.
    Cache entries are created as part of normal extraction flow,
    not as standalone records.

    Args:
        cache_key: The extraction cache key (SHA-256 hash)
        source: Data source name (e.g., "google_places", "serper")
        entity_type: Entity type (e.g., "VENUE", "COACH")
        attributes: Extracted structured attributes
        model_used: LLM model name used for extraction
        raw_ingestion_id: RawIngestion record ID (required)
        discovered_attributes: Optional discovered attributes
        external_ids: Optional external ID mappings

    Returns:
        Created ExtractedListing record ID

    Example:
        >>> cache_key = compute_cache_key(raw_data, prompt, model)
        >>> await store_llm_cache(
        ...     cache_key=cache_key,
        ...     source="google_places",
        ...     entity_type="VENUE",
        ...     attributes=extracted_data,
        ...     model_used="claude-haiku-20250318",
        ...     raw_ingestion_id="cmk123..."
        ... )
    """
    db = Prisma()
    await db.connect()

    try:
        # Serialize JSON fields
        attributes_json = json.dumps(attributes, separators=(',', ':'))
        discovered_json = (
            json.dumps(discovered_attributes, separators=(',', ':'))
            if discovered_attributes
            else None
        )
        external_ids_json = (
            json.dumps(external_ids, separators=(',', ':'))
            if external_ids
            else None
        )

        # Create ExtractedListing record with extraction_hash for caching
        record = await db.extractedlisting.create(
            data={
                "extraction_hash": cache_key,
                "source": source,
                "entity_type": entity_type,
                "attributes": attributes_json,
                "discovered_attributes": discovered_json,
                "external_ids": external_ids_json,
                "model_used": model_used,
                "raw_ingestion_id": raw_ingestion_id,
            }
        )

        logger.info(f"Stored extraction in cache: {cache_key[:16]}...")
        return record.id

    finally:
        await db.disconnect()


async def clear_llm_cache(cache_key: str) -> bool:
    """
    Remove cached extraction entry.

    Args:
        cache_key: The extraction cache key to delete

    Returns:
        True if entry was deleted, False if not found

    Example:
        >>> deleted = await clear_llm_cache("old_cache_key_...")
        >>> if deleted:
        ...     print("Cache cleared")
    """
    db = Prisma()
    await db.connect()

    try:
        # Find and delete
        record = await db.extractedlisting.find_first(
            where={"extraction_hash": cache_key}
        )

        if record is None:
            return False

        await db.extractedlisting.delete(where={"id": record.id})
        logger.info(f"Cleared cache entry: {cache_key[:16]}...")
        return True

    finally:
        await db.disconnect()


async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache metrics:
        - total_entries: Total cached extractions
        - entries_by_source: Count per data source
        - entries_by_model: Count per LLM model
        - cache_size_mb: Approximate cache size in MB

    Example:
        >>> stats = await get_cache_stats()
        >>> print(f"Cache has {stats['total_entries']} entries")
    """
    db = Prisma()
    await db.connect()

    try:
        # Count total cached entries (those with extraction_hash)
        total = await db.extractedlisting.count(
            where={"extraction_hash": {"not": None}}
        )

        # Group by source
        by_source = await db.extractedlisting.group_by(
            by=["source"],
            count=True,
            where={"extraction_hash": {"not": None}},
        )

        # Group by model
        by_model = await db.extractedlisting.group_by(
            by=["model_used"],
            count=True,
            where={"extraction_hash": {"not": None}},
        )

        return {
            "total_entries": total,
            "entries_by_source": {item["source"]: item["_count"] for item in by_source},
            "entries_by_model": {
                item["model_used"]: item["_count"]
                for item in by_model
                if item["model_used"]
            },
        }

    finally:
        await db.disconnect()
