"""
CLI for extraction maintenance tasks.

Currently supports retrying failed extractions from quarantine.
"""

import argparse
import asyncio
from typing import Optional

from prisma import Prisma

from engine.extraction.quarantine import retry_failed_extractions


async def run_retry_failed(max_retries: int, limit: Optional[int]) -> int:
    """Run the failed extraction retry workflow."""
    db = Prisma()

    try:
        await db.connect()
    except Exception as exc:
        print(f"Database connection failed: {exc}")
        return 1

    try:
        summary = await retry_failed_extractions(
            db,
            max_retries=max_retries,
            limit=limit,
        )

        print("Retry Summary")
        print(f"  Retried:   {summary['retried']}")
        print(f"  Succeeded: {summary['succeeded']}")
        print(f"  Failed:    {summary['failed']}")

        return 0 if summary["failed"] == 0 else 1

    finally:
        await db.disconnect()


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extraction maintenance CLI",
    )

    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry failed extractions in quarantine",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum failed retries allowed before skipping",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of failed extractions to retry",
    )

    args = parser.parse_args()

    if args.retry_failed:
        return asyncio.run(run_retry_failed(args.max_retries, args.limit))

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
