"""
CLI for running extraction workflows.

Supports single record extraction, per-source batch extraction, and batch all modes.
"""

import argparse
import asyncio
import json
import time
from typing import Dict, Optional, List
from pathlib import Path

from prisma import Prisma
from tqdm import tqdm

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
    dry_run: bool = False,
    force_retry: bool = False,
) -> Dict:
    """
    Extract a single RawIngestion record and display results.

    Args:
        db: Prisma database client
        raw_id: ID of the RawIngestion record to extract
        verbose: If True, display field-by-field extraction results
        dry_run: If True, simulate extraction without saving to database
        force_retry: If True, re-extract even if already processed

    Returns:
        Dict: Extraction result with status and details
    """
    log_prefix = "[DRY RUN] " if dry_run else ""
    logger.info(f"{log_prefix}Starting single record extraction for raw_id: {raw_id}")

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

    # Check if already extracted (unless force_retry is set)
    existing_extraction = None
    if not force_retry:
        existing_extraction = await db.extractedlisting.find_first(
            where={"raw_ingestion_id": raw_id}
        )

    if existing_extraction and not force_retry:
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

    if force_retry and existing_extraction:
        logger.info(f"Force retry enabled, re-extracting record: {raw_id}")

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

        # Create ExtractedListing record (unless dry_run)
        extracted_listing_id = None
        if not dry_run:
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
            extracted_listing_id = extracted_listing.id
        else:
            logger.info(f"[DRY RUN] Would create ExtractedListing for raw_id: {raw_id}")
            extracted_listing_id = "dry-run-simulation"

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
            "extracted_id": extracted_listing_id,
            "entity_type": entity_type,
            "dry_run": dry_run,
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

        # Record the failed extraction (unless dry_run)
        if not dry_run:
            await record_failed_extraction(
                db,
                raw_ingestion_id=raw_id,
                source=raw.source,
                error_message=error_msg,
            )
        else:
            logger.info(f"[DRY RUN] Would record failed extraction for raw_id: {raw_id}")

        return {
            "status": "error",
            "error": error_msg,
            "raw_id": raw_id,
            "source": raw.source,
            "dry_run": dry_run,
        }


async def run_source_extraction(
    db: Prisma,
    source: str,
    limit: Optional[int] = None,
    dry_run: bool = False,
    force_retry: bool = False,
) -> Dict:
    """
    Extract all RawIngestion records from a specific source.

    Args:
        db: Prisma database client
        source: Source name (e.g., "google_places", "serper")
        limit: Optional limit on number of records to process
        dry_run: If True, simulate extraction without saving to database
        force_retry: If True, re-extract even if already processed

    Returns:
        Dict: Summary report with counts, duration, and cost estimate
    """
    logger.info(f"Starting batch extraction for source: {source}")

    # Query for unprocessed records from this source
    query_params = {
        "where": {
            "source": source,
        },
        "order_by": {"created_at": "asc"},
    }

    if limit is not None:
        query_params["take"] = limit

    raw_records = await db.rawingestion.find_many(**query_params)

    total_records = len(raw_records)
    logger.info(f"Found {total_records} records for source: {source}")

    if total_records == 0:
        return {
            "status": "success",
            "source": source,
            "total_records": 0,
            "successful": 0,
            "failed": 0,
            "already_extracted": 0,
            "duration": 0.0,
            "cost_estimate": 0.0,
        }

    # Track metrics
    successful = 0
    failed = 0
    already_extracted = 0
    start_time = time.time()
    llm_calls = 0
    total_cost = 0.0

    # Process each record with progress bar
    desc_prefix = "[DRY RUN] " if dry_run else ""
    with tqdm(total=total_records, desc=f"{desc_prefix}Extracting {source}", unit="record") as pbar:
        for raw_record in raw_records:
            try:
                # Check if already extracted (unless force_retry)
                existing = None
                if not force_retry:
                    existing = await db.extractedlisting.find_first(
                        where={"raw_ingestion_id": raw_record.id}
                    )

                if existing and not force_retry:
                    already_extracted += 1
                    pbar.update(1)
                    pbar.set_postfix(
                        success=successful,
                        failed=failed,
                        skipped=already_extracted,
                    )
                    continue

                # Load raw data
                raw_data_path = Path(raw_record.file_path)
                with open(raw_data_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                # Get extractor
                extractor = get_extractor_for_source(raw_record.source)

                # Extract
                extracted = extractor.extract(raw_data)
                validated = extractor.validate(extracted)
                attributes, discovered_attributes = extractor.split_attributes(validated)

                # Prepare external IDs
                external_ids = {}
                if "external_id" in validated:
                    external_ids[f"{raw_record.source}_id"] = validated["external_id"]

                # Get entity type
                entity_type = validated.get("entity_type", "VENUE")

                # Track LLM usage if model_used is present
                model_used = validated.get("model_used")
                if model_used:
                    llm_calls += 1
                    # Estimate cost (simplified - actual cost varies by model)
                    # Haiku: ~$0.25 per 1M input tokens, ~$1.25 per 1M output tokens
                    # Rough estimate: ~2000 tokens per call, ~$0.002 per call
                    total_cost += 0.002

                # Create ExtractedListing (unless dry_run)
                if not dry_run:
                    await db.extractedlisting.create(
                        data={
                            "raw_ingestion_id": raw_record.id,
                            "source": raw_record.source,
                            "entity_type": entity_type,
                            "attributes": json.dumps(attributes),
                            "discovered_attributes": json.dumps(discovered_attributes),
                            "external_ids": json.dumps(external_ids),
                            "model_used": model_used,
                        }
                    )

                successful += 1

            except Exception as e:
                # Log error and record failed extraction
                logger.error(f"Failed to extract {raw_record.id}: {str(e)}")

                # Record the failed extraction (unless dry_run)
                if not dry_run:
                    await record_failed_extraction(
                        db,
                        raw_ingestion_id=raw_record.id,
                        source=raw_record.source,
                        error_message=str(e),
                    )

                failed += 1

            # Update progress bar
            pbar.update(1)
            pbar.set_postfix(
                success=successful,
                failed=failed,
                skipped=already_extracted,
            )

    duration = time.time() - start_time

    logger.info(
        f"Batch extraction complete for {source}: "
        f"{successful} successful, {failed} failed, "
        f"{already_extracted} already extracted, "
        f"duration: {duration:.2f}s"
    )

    return {
        "status": "success",
        "source": source,
        "total_records": total_records,
        "successful": successful,
        "failed": failed,
        "already_extracted": already_extracted,
        "duration": duration,
        "cost_estimate": total_cost,
        "llm_calls": llm_calls,
        "dry_run": dry_run,
    }


async def run_all_extraction(
    db: Prisma,
    limit: Optional[int] = None,
    dry_run: bool = False,
    force_retry: bool = False,
) -> Dict:
    """
    Extract all unprocessed RawIngestion records, grouped by source.

    This function queries all unprocessed records, groups them by source,
    and processes each source batch sequentially. This approach is efficient
    because it allows for better progress tracking and error isolation per source.

    Args:
        db: Prisma database client
        limit: Optional limit on total number of records to process
        dry_run: If True, simulate extraction without saving to database
        force_retry: If True, re-extract even if already processed

    Returns:
        Dict: Overall summary report with aggregated metrics across all sources
    """
    logger.info("Starting batch extraction for all unprocessed records")

    # Query for all unprocessed records
    query_params = {
        "order_by": {"created_at": "asc"},
    }

    if limit is not None:
        query_params["take"] = limit

    raw_records = await db.rawingestion.find_many(**query_params)

    total_records = len(raw_records)
    logger.info(f"Found {total_records} total records")

    if total_records == 0:
        return {
            "status": "success",
            "total_records": 0,
            "successful": 0,
            "failed": 0,
            "already_extracted": 0,
            "duration": 0.0,
            "cost_estimate": 0.0,
            "llm_calls": 0,
            "sources_processed": [],
        }

    # Group records by source
    from collections import defaultdict
    records_by_source: Dict[str, List] = defaultdict(list)

    for record in raw_records:
        records_by_source[record.source].append(record)

    logger.info(
        f"Grouped records into {len(records_by_source)} sources: "
        f"{', '.join(records_by_source.keys())}"
    )

    # Track overall metrics
    overall_successful = 0
    overall_failed = 0
    overall_already_extracted = 0
    overall_llm_calls = 0
    overall_cost = 0.0
    start_time = time.time()
    sources_processed = []

    # Process each source batch
    for source, source_records in records_by_source.items():
        log_prefix = "[DRY RUN] " if dry_run else ""
        logger.info(f"{log_prefix}Processing {len(source_records)} records from {source}")

        source_successful = 0
        source_failed = 0
        source_already_extracted = 0
        source_llm_calls = 0
        source_cost = 0.0

        # Process each record in this source with progress bar
        desc_prefix = "[DRY RUN] " if dry_run else ""
        with tqdm(
            total=len(source_records),
            desc=f"{desc_prefix}Extracting {source}",
            unit="record",
        ) as pbar:
            for raw_record in source_records:
                try:
                    # Check if already extracted (unless force_retry)
                    existing = None
                    if not force_retry:
                        existing = await db.extractedlisting.find_first(
                            where={"raw_ingestion_id": raw_record.id}
                        )

                    if existing and not force_retry:
                        source_already_extracted += 1
                        pbar.update(1)
                        pbar.set_postfix(
                            success=source_successful,
                            failed=source_failed,
                            skipped=source_already_extracted,
                        )
                        continue

                    # Load raw data
                    raw_data_path = Path(raw_record.file_path)
                    with open(raw_data_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)

                    # Get extractor
                    extractor = get_extractor_for_source(raw_record.source)

                    # Extract
                    extracted = extractor.extract(raw_data)
                    validated = extractor.validate(extracted)
                    attributes, discovered_attributes = extractor.split_attributes(validated)

                    # Prepare external IDs
                    external_ids = {}
                    if "external_id" in validated:
                        external_ids[f"{raw_record.source}_id"] = validated["external_id"]

                    # Get entity type
                    entity_type = validated.get("entity_type", "VENUE")

                    # Track LLM usage if model_used is present
                    model_used = validated.get("model_used")
                    if model_used:
                        source_llm_calls += 1
                        # Estimate cost (simplified)
                        source_cost += 0.002

                    # Create ExtractedListing (unless dry_run)
                    if not dry_run:
                        await db.extractedlisting.create(
                            data={
                                "raw_ingestion_id": raw_record.id,
                                "source": raw_record.source,
                                "entity_type": entity_type,
                                "attributes": json.dumps(attributes),
                                "discovered_attributes": json.dumps(discovered_attributes),
                                "external_ids": json.dumps(external_ids),
                                "model_used": model_used,
                            }
                        )

                    source_successful += 1

                except Exception as e:
                    # Log error and record failed extraction
                    logger.error(f"Failed to extract {raw_record.id}: {str(e)}")

                    # Record the failed extraction (unless dry_run)
                    if not dry_run:
                        await record_failed_extraction(
                            db,
                            raw_ingestion_id=raw_record.id,
                            source=raw_record.source,
                            error_message=str(e),
                        )

                    source_failed += 1

                # Update progress bar
                pbar.update(1)
                pbar.set_postfix(
                    success=source_successful,
                    failed=source_failed,
                    skipped=source_already_extracted,
                )

        # Aggregate source metrics to overall metrics
        overall_successful += source_successful
        overall_failed += source_failed
        overall_already_extracted += source_already_extracted
        overall_llm_calls += source_llm_calls
        overall_cost += source_cost

        sources_processed.append(
            {
                "source": source,
                "total": len(source_records),
                "successful": source_successful,
                "failed": source_failed,
                "already_extracted": source_already_extracted,
                "llm_calls": source_llm_calls,
                "cost": source_cost,
            }
        )

        logger.info(
            f"Completed {source}: {source_successful} successful, "
            f"{source_failed} failed, {source_already_extracted} skipped"
        )

    duration = time.time() - start_time

    logger.info(
        f"Batch extraction complete for all sources: "
        f"{overall_successful} successful, {overall_failed} failed, "
        f"{overall_already_extracted} already extracted, "
        f"duration: {duration:.2f}s"
    )

    return {
        "status": "success",
        "total_records": total_records,
        "successful": overall_successful,
        "failed": overall_failed,
        "already_extracted": overall_already_extracted,
        "duration": duration,
        "cost_estimate": overall_cost,
        "llm_calls": overall_llm_calls,
        "sources_processed": sources_processed,
        "dry_run": dry_run,
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
    dry_run_marker = " [DRY RUN]" if result.get("dry_run", False) else ""
    lines.append(f"EXTRACTION RESULT{dry_run_marker}")
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


def format_summary_report(result: Dict) -> str:
    """
    Format extraction summary for batch mode.

    Args:
        result: Extraction summary dictionary

    Returns:
        str: Formatted summary string
    """
    lines = []
    lines.append("")
    lines.append("=" * 80)
    dry_run_marker = " [DRY RUN]" if result.get("dry_run", False) else ""
    lines.append(f"BATCH EXTRACTION SUMMARY{dry_run_marker}")
    lines.append("=" * 80)
    lines.append(f"Source:            {result['source']}")
    lines.append(f"Total Records:     {result['total_records']}")
    lines.append(f"✓ Successful:      {result['successful']}")
    lines.append(f"✗ Failed:          {result['failed']}")
    lines.append(f"⊙ Already Extracted: {result['already_extracted']}")
    lines.append(f"Duration:          {result['duration']:.2f}s")

    if result['total_records'] > 0:
        avg_time = result['duration'] / result['total_records']
        lines.append(f"Avg per record:    {avg_time:.2f}s")

    if result.get('llm_calls', 0) > 0:
        lines.append(f"LLM Calls:         {result['llm_calls']}")
        lines.append(f"Estimated Cost:    ${result['cost_estimate']:.4f}")

    # Success rate
    if result['total_records'] > 0:
        success_rate = (result['successful'] / result['total_records']) * 100
        lines.append(f"Success Rate:      {success_rate:.1f}%")

    lines.append("=" * 80)
    lines.append("")

    return "\n".join(lines)


def format_all_summary_report(result: Dict) -> str:
    """
    Format extraction summary for batch all mode.

    Args:
        result: Extraction summary dictionary with sources_processed list

    Returns:
        str: Formatted summary string
    """
    lines = []
    lines.append("")
    lines.append("=" * 80)
    dry_run_marker = " [DRY RUN]" if result.get("dry_run", False) else ""
    lines.append(f"BATCH ALL EXTRACTION SUMMARY{dry_run_marker}")
    lines.append("=" * 80)
    lines.append(f"Total Records:       {result['total_records']}")
    lines.append(f"✓ Successful:        {result['successful']}")
    lines.append(f"✗ Failed:            {result['failed']}")
    lines.append(f"⊙ Already Extracted:  {result['already_extracted']}")
    lines.append(f"Duration:            {result['duration']:.2f}s")

    if result['total_records'] > 0:
        avg_time = result['duration'] / result['total_records']
        lines.append(f"Avg per record:      {avg_time:.2f}s")

    if result.get('llm_calls', 0) > 0:
        lines.append(f"LLM Calls:           {result['llm_calls']}")
        lines.append(f"Estimated Cost:      ${result['cost_estimate']:.4f}")

    # Success rate
    if result['total_records'] > 0:
        success_rate = (result['successful'] / result['total_records']) * 100
        lines.append(f"Success Rate:        {success_rate:.1f}%")

    # Per-source breakdown
    if result.get('sources_processed'):
        lines.append("")
        lines.append("-" * 80)
        lines.append("PER-SOURCE BREAKDOWN")
        lines.append("-" * 80)

        for source_result in result['sources_processed']:
            source = source_result['source']
            total = source_result['total']
            successful = source_result['successful']
            failed = source_result['failed']
            already = source_result['already_extracted']

            lines.append(f"\n{source}:")
            lines.append(f"  Total:      {total}")
            lines.append(f"  ✓ Success:  {successful}")
            lines.append(f"  ✗ Failed:   {failed}")
            lines.append(f"  ⊙ Skipped:  {already}")

            if source_result.get('llm_calls', 0) > 0:
                lines.append(f"  LLM Calls:  {source_result['llm_calls']}")
                lines.append(f"  Cost:       ${source_result['cost']:.4f}")

    lines.append("")
    lines.append("=" * 80)
    lines.append("")

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
        # Get dry_run and force_retry flags
        dry_run = getattr(args, "dry_run", False)
        force_retry = getattr(args, "force_retry", False)

        if args.raw_id:
            # Single record extraction mode
            result = await run_single_extraction(
                db,
                raw_id=args.raw_id,
                verbose=args.verbose,
                dry_run=dry_run,
                force_retry=force_retry,
            )

            if args.verbose:
                print(format_verbose_output(result))
            else:
                # Non-verbose: just print status
                dry_run_prefix = "[DRY RUN] " if dry_run else ""
                if result["status"] == "success":
                    print(f"{dry_run_prefix}✓ Extraction successful: {result['extracted_id']}")
                elif result["status"] == "already_extracted":
                    print(f"{dry_run_prefix}✓ Already extracted: {result['extracted_id']}")
                else:
                    print(f"{dry_run_prefix}✗ Extraction failed: {result['error']}")

            return 0 if result["status"] in ["success", "already_extracted"] else 1

        elif args.source:
            # Per-source batch extraction mode
            result = await run_source_extraction(
                db,
                source=args.source,
                limit=args.limit,
                dry_run=dry_run,
                force_retry=force_retry,
            )

            # Always print summary report for batch mode
            print(format_summary_report(result))

            # Return 0 if at least some records were successful
            return 0 if result["successful"] > 0 or result["total_records"] == 0 else 1

        else:
            print("Error: Either --raw-id or --source is required")
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
        "--source",
        type=str,
        help="Extract all records from a specific source (e.g., google_places, serper)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of records to process (for testing)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Display detailed field-by-field extraction results (default: True, only for --raw-id)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (overrides --verbose)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate extraction without saving to database",
    )
    parser.add_argument(
        "--force-retry",
        action="store_true",
        help="Re-extract even if already processed",
    )

    args = parser.parse_args()

    # Handle quiet flag
    if args.quiet:
        args.verbose = False

    return asyncio.run(run_cli(args))


if __name__ == "__main__":
    raise SystemExit(main())
