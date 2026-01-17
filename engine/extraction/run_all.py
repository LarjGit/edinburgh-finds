"""
CLI for batch extraction of all unprocessed records.

This script processes all unprocessed RawIngestion records in source-grouped batches.
"""

import argparse
import asyncio
from prisma import Prisma

from engine.extraction.run import run_all_extraction, format_all_summary_report
from engine.extraction.logging_config import get_extraction_logger


logger = get_extraction_logger()


async def main_async(
    limit: int = None,
    dry_run: bool = False,
    force_retry: bool = False,
) -> int:
    """
    Run batch extraction for all unprocessed records.

    Args:
        limit: Optional limit on total number of records to process
        dry_run: If True, simulate extraction without saving to database
        force_retry: If True, re-extract even if already processed

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
        # Run batch extraction for all unprocessed records
        result = await run_all_extraction(
            db,
            limit=limit,
            dry_run=dry_run,
            force_retry=force_retry,
        )

        # Print summary report
        print(format_all_summary_report(result))

        # Return 0 if at least some records were successful
        return 0 if result["successful"] > 0 or result["total_records"] == 0 else 1

    finally:
        await db.disconnect()
        logger.info("Database disconnected")


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Batch All Extraction - Extract all unprocessed records",
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the total number of records to process (for testing)",
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

    return asyncio.run(
        main_async(
            limit=args.limit,
            dry_run=args.dry_run,
            force_retry=args.force_retry,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
