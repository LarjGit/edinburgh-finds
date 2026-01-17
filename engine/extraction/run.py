"""
CLI for running extraction workflows.

Supports single record extraction, per-source batch extraction, and batch all modes.
"""

import argparse
import asyncio
import json
import time
from typing import Dict, Optional
from pathlib import Path

from prisma import Prisma

from engine.extraction.extractors import (
    GooglePlacesExtractor,
    SportScotlandExtractor,
    EdinburghCouncilExtractor,
    OpenChargeMapExtractor,
    SerperExtractor,
    OSMExtractor,
)
from engine.extraction.base import BaseExtractor
from engine.extraction.logging_config import (
    get_extraction_logger,
    log_extraction_start,
    log_extraction_success,
    log_extraction_failure,
)
from engine.extraction.quarantine import record_failed_extraction


logger = get_extraction_logger()


def get_extractor_for_source(source: str) -> BaseExtractor:
    """
    Get the appropriate extractor for a given source.

    Args:
        source: Source name (e.g., "google_places", "osm")

    Returns:
        BaseExtractor: Extractor instance for the source

    Raises:
        ValueError: If source is not recognized
    """
    extractors = {
        "google_places": GooglePlacesExtractor,
        "sport_scotland": SportScotlandExtractor,
        "edinburgh_council": EdinburghCouncilExtractor,
        "open_charge_map": OpenChargeMapExtractor,
        "serper": SerperExtractor,
        "osm": OSMExtractor,
    }

    extractor_class = extractors.get(source)
    if not extractor_class:
        raise ValueError(
            f"No extractor found for source: {source}. "
            f"Available sources: {', '.join(extractors.keys())}"
        )

    return extractor_class()


async def run_single_extraction(
    db: Prisma,
    raw_id: str,
    verbose: bool = True,
) -> Dict:
    """
    Extract a single RawIngestion record and display results.

    Args:
        db: Prisma database client
        raw_id: ID of the RawIngestion record to extract
        verbose: If True, display field-by-field extraction results

    Returns:
        Dict: Extraction result with status and details
    """
    logger.info(f"Starting single record extraction for raw_id: {raw_id}")

    # Fetch the RawIngestion record
    raw = await db.rawingestion.find_unique(where={"id": raw_id})

    if not raw:
        error_msg = f"RawIngestion record not found: {raw_id}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error": error_msg,
        }

    logger.info(f"Found RawIngestion record: source={raw.source}, status={raw.status}")

    # Check if already extracted
    existing_extraction = await db.extractedlisting.find_first(
        where={"raw_ingestion_id": raw_id}
    )

    if existing_extraction:
        logger.info(f"Record already extracted: {existing_extraction.id}")
        result = {
            "status": "already_extracted",
            "raw_id": raw_id,
            "source": raw.source,
            "extracted_id": existing_extraction.id,
        }

        if verbose:
            attributes = json.loads(existing_extraction.attributes or "{}")
            discovered = json.loads(existing_extraction.discovered_attributes or "{}")
            result["fields"] = attributes
            result["discovered"] = discovered

        return result

    # Load raw data from file
    try:
        raw_data_path = Path(raw.file_path)
        with open(raw_data_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        logger.info(f"Loaded raw data from: {raw.file_path}")
    except Exception as e:
        error_msg = f"Failed to load raw data from {raw.file_path}: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "error": error_msg,
        }

    # Get the appropriate extractor
    try:
        extractor = get_extractor_for_source(raw.source)
        logger.info(f"Using extractor: {extractor.__class__.__name__}")
    except ValueError as e:
        error_msg = str(e)
        logger.error(error_msg)
        return {
            "status": "error",
            "error": error_msg,
        }

    # Perform extraction
    start_time = time.time()
    extractor_name = extractor.__class__.__name__

    try:
        log_extraction_start(logger, raw.source, raw_id, extractor_name)

        # Extract fields
        extracted = extractor.extract(raw_data)
        logger.info(f"Extracted {len(extracted)} fields")

        # Validate fields
        validated = extractor.validate(extracted)
        logger.info("Validation complete")

        # Split into schema-defined and discovered attributes
        attributes, discovered_attributes = extractor.split_attributes(validated)
        logger.info(
            f"Split attributes: {len(attributes)} schema-defined, "
            f"{len(discovered_attributes)} discovered"
        )

        # Prepare external IDs
        external_ids = {}
        if "external_id" in validated:
            external_ids[f"{raw.source}_id"] = validated["external_id"]

        # Get entity type (default to VENUE if not specified)
        entity_type = validated.get("entity_type", "VENUE")

        # Create ExtractedListing record
        extracted_listing = await db.extractedlisting.create(
            data={
                "raw_ingestion_id": raw_id,
                "source": raw.source,
                "entity_type": entity_type,
                "attributes": json.dumps(attributes),
                "discovered_attributes": json.dumps(discovered_attributes),
                "external_ids": json.dumps(external_ids),
                "model_used": validated.get("model_used"),
            }
        )

        duration = time.time() - start_time
        log_extraction_success(
            logger,
            raw.source,
            raw_id,
            extractor_name,
            duration,
            len(attributes) + len(discovered_attributes),
        )

        result = {
            "status": "success",
            "raw_id": raw_id,
            "source": raw.source,
            "extracted_id": extracted_listing.id,
            "entity_type": entity_type,
        }

        if verbose:
            result["fields"] = attributes
            result["discovered"] = discovered_attributes
            result["external_ids"] = external_ids

        return result

    except Exception as e:
        error_msg = f"Extraction failed: {str(e)}"
        duration = time.time() - start_time
        log_extraction_failure(logger, raw.source, raw_id, extractor_name, error_msg, duration)

        # Record the failed extraction
        await record_failed_extraction(
            db,
            raw_ingestion_id=raw_id,
            source=raw.source,
            error_message=error_msg,
        )

        return {
            "status": "error",
            "error": error_msg,
            "raw_id": raw_id,
            "source": raw.source,
        }


def format_verbose_output(result: Dict) -> str:
    """
    Format extraction result for verbose CLI output.

    Args:
        result: Extraction result dictionary

    Returns:
        str: Formatted output string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("EXTRACTION RESULT")
    lines.append("=" * 80)
    lines.append(f"Status:       {result['status'].upper()}")

    if result["status"] == "error":
        lines.append(f"Error:        {result['error']}")
        return "\n".join(lines)

    lines.append(f"Raw ID:       {result['raw_id']}")
    lines.append(f"Source:       {result['source']}")
    lines.append(f"Extracted ID: {result['extracted_id']}")

    if "entity_type" in result:
        lines.append(f"Entity Type:  {result['entity_type']}")

    if "fields" in result and result["fields"]:
        lines.append("")
        lines.append("-" * 80)
        lines.append("SCHEMA-DEFINED FIELDS")
        lines.append("-" * 80)

        for field, value in result["fields"].items():
            # Truncate long values for display
            value_str = str(value)
            if len(value_str) > 70:
                value_str = value_str[:67] + "..."
            lines.append(f"  {field:20} = {value_str}")

    if "discovered" in result and result["discovered"]:
        lines.append("")
        lines.append("-" * 80)
        lines.append("DISCOVERED ATTRIBUTES")
        lines.append("-" * 80)

        for field, value in result["discovered"].items():
            value_str = str(value)
            if len(value_str) > 70:
                value_str = value_str[:67] + "..."
            lines.append(f"  {field:20} = {value_str}")

    if "external_ids" in result and result["external_ids"]:
        lines.append("")
        lines.append("-" * 80)
        lines.append("EXTERNAL IDs")
        lines.append("-" * 80)

        for key, value in result["external_ids"].items():
            lines.append(f"  {key:20} = {value}")

    lines.append("=" * 80)
    return "\n".join(lines)


async def run_cli(args) -> int:
    """
    Run the CLI with parsed arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    db = Prisma()

    try:
        await db.connect()
        logger.info("Database connected")
    except Exception as exc:
        print(f"Database connection failed: {exc}")
        return 1

    try:
        if args.raw_id:
            # Single record extraction mode
            result = await run_single_extraction(
                db,
                raw_id=args.raw_id,
                verbose=args.verbose,
            )

            if args.verbose:
                print(format_verbose_output(result))
            else:
                # Non-verbose: just print status
                if result["status"] == "success":
                    print(f"✓ Extraction successful: {result['extracted_id']}")
                elif result["status"] == "already_extracted":
                    print(f"✓ Already extracted: {result['extracted_id']}")
                else:
                    print(f"✗ Extraction failed: {result['error']}")

            return 0 if result["status"] in ["success", "already_extracted"] else 1

        else:
            print("Error: --raw-id is required")
            return 1

    finally:
        await db.disconnect()
        logger.info("Database disconnected")


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extraction CLI - Extract and transform raw ingestion data",
    )

    parser.add_argument(
        "--raw-id",
        type=str,
        help="Extract a single RawIngestion record by ID",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Display detailed field-by-field extraction results (default: True)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (overrides --verbose)",
    )

    args = parser.parse_args()

    # Handle quiet flag
    if args.quiet:
        args.verbose = False

    return asyncio.run(run_cli(args))


if __name__ == "__main__":
    raise SystemExit(main())
