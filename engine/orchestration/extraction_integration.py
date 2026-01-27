"""
Extraction Integration Bridge for Orchestration.

Bridges the orchestration layer to the extraction engine, enabling intelligent
extraction of entities from RawIngestion records. Distinguishes between structured
sources (which skip LLM extraction) and unstructured sources (which require it).
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from prisma import Prisma
from engine.extraction.run import get_extractor_for_source


# Structured sources with deterministic extractors (skip LLM extraction)
STRUCTURED_SOURCES = {
    "google_places",      # Google Places API - well-defined JSON schema
    "sport_scotland",     # Sport Scotland GeoJSON - structured properties
    "edinburgh_council",  # Edinburgh Council API - structured government data
    "open_charge_map",    # Open Charge Map API - structured EV charging data
}

# Unstructured sources requiring LLM extraction
UNSTRUCTURED_SOURCES = {
    "serper",            # Web search snippets - varying HTML fragments
    "openstreetmap",     # OSM - free-form tags with no standard schema
}


def needs_extraction(source: str) -> bool:
    """
    Determine if a source requires LLM extraction.

    Structured sources (google_places, sport_scotland, etc.) have well-defined
    APIs with predictable schemas, so they can be processed deterministically
    without LLM extraction. This saves cost and latency.

    Unstructured sources (serper, openstreetmap) have varying formats and
    require LLM extraction to parse and structure the data.

    Args:
        source: Source connector name (e.g., "google_places", "serper")

    Returns:
        bool: True if source needs LLM extraction, False if it can be processed deterministically

    Examples:
        >>> needs_extraction("google_places")
        False
        >>> needs_extraction("serper")
        True
        >>> needs_extraction("unknown_source")  # Conservative: assume needs extraction
        True
    """
    # If source is in structured list, it doesn't need extraction
    if source in STRUCTURED_SOURCES:
        return False

    # If source is in unstructured list, it needs extraction
    if source in UNSTRUCTURED_SOURCES:
        return True

    # Unknown sources: conservative approach - assume they need extraction
    # This prevents data loss from skipping extraction when it's actually needed
    return True


async def extract_entity(raw_ingestion_id: str, db: Prisma) -> Dict[str, Any]:
    """
    Extract entity data from a RawIngestion record using the hybrid extraction engine.

    Loads the raw data from disk, selects the appropriate extractor for the source,
    and runs the complete extraction pipeline: extract -> validate -> split_attributes.

    Args:
        raw_ingestion_id: ID of the RawIngestion record to extract
        db: Prisma database client

    Returns:
        Dict with extracted entity data:
            - entity_class: Entity classification
            - attributes: Schema-defined attributes dict
            - discovered_attributes: Non-schema attributes dict
            - external_ids: External IDs dict (optional)
            - model_used: Model name if LLM was used (optional)

    Raises:
        ValueError: If RawIngestion record not found
        IOError: If raw data file cannot be read
        Exception: If extraction fails (with source context)

    Example:
        >>> async with Prisma() as db:
        >>>     result = await extract_entity("raw_123", db)
        >>>     print(result["entity_class"])  # "place"
        >>>     print(result["attributes"]["name"])  # "Test Venue"
    """
    # Step 1: Load RawIngestion record
    raw_ingestion = await db.rawingestion.find_unique(
        where={"id": raw_ingestion_id}
    )

    if not raw_ingestion:
        raise ValueError(f"RawIngestion record not found: {raw_ingestion_id}")

    source = raw_ingestion.source
    file_path = raw_ingestion.file_path

    # Step 2: Load raw data from file
    try:
        raw_data_path = Path(file_path)
        raw_data_str = raw_data_path.read_text(encoding="utf-8")
        raw_data = json.loads(raw_data_str)
    except (FileNotFoundError, OSError) as e:
        raise IOError(
            f"Failed to load raw data from {file_path}: {str(e)}"
        ) from e
    except json.JSONDecodeError as e:
        raise IOError(
            f"Failed to parse JSON from {file_path}: {str(e)}"
        ) from e

    # Step 3: Get appropriate extractor for source
    try:
        extractor = get_extractor_for_source(source)
    except ValueError as e:
        raise ValueError(
            f"No extractor found for source: {source}"
        ) from e

    # Step 4: Run extraction pipeline
    try:
        # Extract raw fields
        extracted = extractor.extract(raw_data)

        # Validate fields
        validated = extractor.validate(extracted)

        # Split into schema-defined and discovered attributes
        attributes, discovered_attributes = extractor.split_attributes(validated)

        # Get entity_class from validated data
        entity_class = validated.get("entity_class")

        # Prepare external IDs if present
        external_ids = {}
        if "external_id" in validated:
            external_ids[f"{source}_id"] = validated["external_id"]

        # Get model_used if present (indicates LLM extraction)
        model_used = validated.get("model_used")

        # Build result
        result = {
            "entity_class": entity_class,
            "attributes": attributes,
            "discovered_attributes": discovered_attributes,
        }

        if external_ids:
            result["external_ids"] = external_ids

        if model_used:
            result["model_used"] = model_used

        return result

    except Exception as e:
        raise Exception(
            f"Extraction failed for source {source} (raw_id: {raw_ingestion_id}): {str(e)}"
        ) from e
