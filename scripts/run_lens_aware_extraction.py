"""
Re-extraction script using lens-aware pipeline.

This script:
1. Loads the Edinburgh Finds lens and produces LensContract (plain dict)
2. Re-runs extraction on all RawIngestion records using extract_with_lens_contract
3. Stores results in the Listing table with lens-aware dimensions
4. Validates results against expected schema

Usage:
    python scripts/run_lens_aware_extraction.py [--limit N] [--dry-run] [--source SOURCE]
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set default DATABASE_URL if not set
# Use web/dev.db which contains all tables (Listing, RawIngestion, ExtractedListing, etc.)
if "DATABASE_URL" not in os.environ:
    # Priority order: web/dev.db, web/prisma/dev.db, engine/test.db
    possible_paths = [
        project_root / "web" / "dev.db",
        project_root / "web" / "prisma" / "dev.db",
        project_root / "engine" / "test.db",
    ]

    for db_path in possible_paths:
        if db_path.exists() and db_path.stat().st_size > 0:
            os.environ["DATABASE_URL"] = f"file:{db_path}"
            print(f"Using database: {db_path}")
            break
    else:
        raise FileNotFoundError(f"No valid database found. Tried: {possible_paths}")

import asyncio
import json
import argparse
from typing import Dict, Any, Optional
from datetime import datetime

from prisma import Prisma
from tqdm import tqdm

from engine.lenses.loader import VerticalLens
from engine.extraction.base import extract_with_lens_contract


async def load_lens_contract() -> Dict[str, Any]:
    """
    Load Edinburgh Finds lens and produce LensContract (plain dict).

    Returns:
        Dict: LensContract (plain dict) with facets, values, mapping_rules, modules, module_triggers
    """
    lens_path = Path("lenses/edinburgh_finds/lens.yaml")

    if not lens_path.exists():
        raise FileNotFoundError(f"Lens configuration not found: {lens_path}")

    print(f"Loading lens from {lens_path}...")
    lens = VerticalLens(lens_path)

    # LensContract is the lens.config (plain dict)
    lens_contract = lens.config

    print(f"✓ Lens loaded successfully")
    print(f"  Facets: {list(lens_contract.get('facets', {}).keys())}")
    print(f"  Values: {len(lens_contract.get('values', []))}")
    print(f"  Mapping rules: {len(lens_contract.get('mapping_rules', []))}")
    print(f"  Module triggers: {len(lens_contract.get('module_triggers', []))}")
    print()

    return lens_contract


async def run_extraction(
    db: Prisma,
    lens_contract: Dict[str, Any],
    limit: Optional[int] = None,
    dry_run: bool = False,
    source_filter: Optional[str] = None
) -> Dict[str, int]:
    """
    Run lens-aware extraction on RawIngestion records.

    Args:
        db: Prisma database client
        lens_contract: LensContract (plain dict)
        limit: Maximum number of records to process (None = all)
        dry_run: If True, don't save to database
        source_filter: Optional source name filter (e.g., "google_places")

    Returns:
        Dict with stats: processed, succeeded, failed, skipped
    """
    stats = {
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "validation_errors": []
    }

    # Build query filter
    where_clause: Dict[str, Any] = {}
    if source_filter:
        where_clause["source"] = source_filter

    # Fetch RawIngestion records
    print(f"Fetching RawIngestion records{' for source=' + source_filter if source_filter else ''}...")
    raw_records = await db.rawingestion.find_many(
        where=where_clause if where_clause else None,
        take=limit
    )

    print(f"Found {len(raw_records)} records to process")
    print(f"Mode: {'DRY RUN (no database writes)' if dry_run else 'LIVE (will update database)'}")
    print()

    # Process each record
    for raw in tqdm(raw_records, desc="Extracting entities"):
        stats["processed"] += 1

        try:
            # Load raw data from file
            raw_data_path = Path(raw.file_path)
            if not raw_data_path.exists():
                stats["failed"] += 1
                stats["validation_errors"].append({
                    "raw_id": raw.id,
                    "error": f"File not found: {raw.file_path}"
                })
                continue

            with open(raw_data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # Extract with lens contract
            extracted = extract_with_lens_contract(raw_data, lens_contract)

            # Validate required fields
            required_fields = [
                "entity_class",
                "canonical_activities",
                "canonical_roles",
                "canonical_place_types",
                "canonical_access",
                "modules"
            ]

            missing_fields = [f for f in required_fields if f not in extracted]
            if missing_fields:
                stats["failed"] += 1
                stats["validation_errors"].append({
                    "raw_id": raw.id,
                    "error": f"Missing required fields: {missing_fields}"
                })
                continue

            # Validate dimension arrays are lists
            for dim in ["canonical_activities", "canonical_roles", "canonical_place_types", "canonical_access"]:
                if not isinstance(extracted[dim], list):
                    stats["failed"] += 1
                    stats["validation_errors"].append({
                        "raw_id": raw.id,
                        "error": f"Dimension {dim} is not a list: {type(extracted[dim])}"
                    })
                    continue

            # Validate modules is dict
            if not isinstance(extracted["modules"], dict):
                stats["failed"] += 1
                stats["validation_errors"].append({
                    "raw_id": raw.id,
                    "error": f"Modules is not a dict: {type(extracted['modules'])}"
                })
                continue

            if not dry_run:
                # Store extracted entity in Listing table
                # For SQLite: Serialize arrays and modules as JSON strings
                # For Postgres/Supabase: These will be native types

                # Extract core fields from raw_data
                # NOTE: Full module field extraction not yet implemented (Task 3.1 deferred)
                # For now, extract from raw_data directly
                entity_name = raw_data.get("name") or raw_data.get("entity_name") or "Unknown Entity"

                # Generate slug from entity_name
                slug = entity_name.lower().replace(" ", "-").replace("'", "").replace('"', "")
                # Add source prefix to avoid conflicts across sources
                slug = f"{raw.source}-{slug}"

                # Serialize dimensions as JSON strings for SQLite
                canonical_activities_json = json.dumps(extracted["canonical_activities"])
                canonical_roles_json = json.dumps(extracted["canonical_roles"])
                canonical_place_types_json = json.dumps(extracted["canonical_place_types"])
                canonical_access_json = json.dumps(extracted["canonical_access"])

                # Serialize modules as JSON string for SQLite
                modules_json = json.dumps(extracted["modules"])

                # Create or update Listing
                # Use upsert to handle duplicates (based on slug or external_id)
                await db.listing.upsert(
                    where={"slug": slug},
                    data={
                        "create": {
                            "entity_name": entity_name,
                            "entityType": "VENUE",  # Temporary fallback, will be removed in Supabase
                            "entity_class": extracted["entity_class"],
                            "slug": slug,
                            "canonical_activities": canonical_activities_json,
                            "canonical_roles": canonical_roles_json,
                            "canonical_place_types": canonical_place_types_json,
                            "canonical_access": canonical_access_json,
                            "modules": modules_json,
                            # Add other fields from raw_data if available
                            "summary": raw_data.get("summary"),
                            "street_address": raw_data.get("street_address"),
                            "city": raw_data.get("city"),
                            "postcode": raw_data.get("postcode"),
                            "country": raw_data.get("country", "United Kingdom"),
                            "latitude": raw_data.get("latitude"),
                            "longitude": raw_data.get("longitude"),
                            "phone": raw_data.get("phone"),
                            "email": raw_data.get("email"),
                            "website_url": raw_data.get("website_url"),
                            "instagram_url": raw_data.get("instagram_url"),
                            "facebook_url": raw_data.get("facebook_url"),
                            "twitter_url": raw_data.get("twitter_url"),
                        },
                        "update": {
                            "entity_class": extracted["entity_class"],
                            "canonical_activities": canonical_activities_json,
                            "canonical_roles": canonical_roles_json,
                            "canonical_place_types": canonical_place_types_json,
                            "canonical_access": canonical_access_json,
                            "modules": modules_json,
                            # Update other fields if present
                            "summary": raw_data.get("summary"),
                            "street_address": raw_data.get("street_address"),
                            "city": raw_data.get("city"),
                            "postcode": raw_data.get("postcode"),
                            "latitude": raw_data.get("latitude"),
                            "longitude": raw_data.get("longitude"),
                        }
                    }
                )

            stats["succeeded"] += 1

        except Exception as e:
            stats["failed"] += 1
            stats["validation_errors"].append({
                "raw_id": raw.id,
                "error": str(e)
            })

    return stats


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run lens-aware extraction on RawIngestion records"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of records to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without saving to database"
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Filter by source (e.g., google_places, osm)"
    )

    args = parser.parse_args()

    # Load lens contract
    try:
        lens_contract = await load_lens_contract()
    except Exception as e:
        print(f"✗ Failed to load lens: {e}")
        return 1

    # Connect to database
    db = Prisma()
    try:
        await db.connect()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return 1

    try:
        # Run extraction
        stats = await run_extraction(
            db,
            lens_contract,
            limit=args.limit,
            dry_run=args.dry_run,
            source_filter=args.source
        )

        # Print summary
        print()
        print("=" * 60)
        print("EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Processed:  {stats['processed']}")
        print(f"Succeeded:  {stats['succeeded']}")
        print(f"Failed:     {stats['failed']}")
        print(f"Skipped:    {stats['skipped']}")

        if stats["validation_errors"]:
            print()
            print("Validation Errors (first 10):")
            for error in stats["validation_errors"][:10]:
                print(f"  - {error['raw_id']}: {error['error']}")

            if len(stats["validation_errors"]) > 10:
                print(f"  ... and {len(stats['validation_errors']) - 10} more")

        print("=" * 60)

        return 0 if stats["failed"] == 0 else 1

    finally:
        await db.disconnect()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
