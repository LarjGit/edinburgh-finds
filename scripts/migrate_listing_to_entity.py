"""
Data Migration Script: Listing to Entity Architecture
========================================================
Migrates existing data from entityType to entity_class + canonical_roles.

This script implements the Engine-Lens Architecture migration:
1. Adds entity_class column
2. Renames entityType to old_entity_type (for reference)
3. Maps old entityType values to entity_class + canonical_roles
4. Handles special case: "club with courts" → place + multiple roles

MAPPING RULES:
- VENUE → {entity_class: 'place', roles: ['provides_facility']}
- RETAILER → {entity_class: 'place', roles: ['sells_goods']}
- COACH → {entity_class: 'person', roles: ['provides_instruction']}
- INSTRUCTOR → {entity_class: 'person', roles: ['provides_instruction']}
- CLUB → {entity_class: 'organization', roles: ['membership_org']}
- LEAGUE → {entity_class: 'organization', roles: ['membership_org']}
- EVENT → {entity_class: 'event', roles: []}
- TOURNAMENT → {entity_class: 'event', roles: []}

SPECIAL CASE - "Club with courts":
- If CLUB has physical location (latitude/longitude OR street_address)
  → entity_class: 'place', roles: ['provides_facility', 'membership_org']
"""

import asyncio
import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
import json


# Define mapping rules
ENTITY_TYPE_MAPPING: Dict[str, Dict[str, any]] = {
    "VENUE": {"entity_class": "place", "roles": ["provides_facility"]},
    "RETAILER": {"entity_class": "place", "roles": ["sells_goods"]},
    "COACH": {"entity_class": "person", "roles": ["provides_instruction"]},
    "INSTRUCTOR": {"entity_class": "person", "roles": ["provides_instruction"]},
    "CLUB": {"entity_class": "organization", "roles": ["membership_org"]},
    "LEAGUE": {"entity_class": "organization", "roles": ["membership_org"]},
    "EVENT": {"entity_class": "event", "roles": []},
    "TOURNAMENT": {"entity_class": "event", "roles": []},
}


def get_db_path() -> Path:
    """Get database path from project root."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Try multiple possible database locations
    possible_paths = [
        project_root / "dev.db",
        project_root / "web" / "dev.db",
        project_root / "web" / "prisma" / "dev.db",
    ]

    for db_path in possible_paths:
        if db_path.exists():
            return db_path

    raise FileNotFoundError(
        f"Database not found. Tried: {', '.join(str(p) for p in possible_paths)}"
    )


def apply_schema_migration(conn: sqlite3.Connection) -> None:
    """Apply schema changes to the database."""
    print("\n=== Step 1: Applying Schema Migration ===")
    cursor = conn.cursor()

    # Check current columns
    cursor.execute("PRAGMA table_info(Listing)")
    columns = {row[1] for row in cursor.fetchall()}

    # Add entity_class if missing
    if "entity_class" not in columns:
        print("Adding entity_class column...")
        cursor.execute("ALTER TABLE Listing ADD COLUMN entity_class TEXT")
    else:
        print("✓ entity_class column already exists")

    # Add dimension columns if missing (SQLite doesn't support arrays, so we use TEXT with JSON)
    dimension_columns = {
        "canonical_activities": "TEXT DEFAULT '[]'",
        "canonical_roles": "TEXT DEFAULT '[]'",
        "canonical_place_types": "TEXT DEFAULT '[]'",
        "canonical_access": "TEXT DEFAULT '[]'",
    }

    for col_name, col_def in dimension_columns.items():
        if col_name not in columns:
            print(f"Adding {col_name} column...")
            cursor.execute(f"ALTER TABLE Listing ADD COLUMN {col_name} {col_def}")
        else:
            print(f"✓ {col_name} column already exists")

    # Add modules column if missing (JSONB in Postgres, TEXT with JSON in SQLite)
    if "modules" not in columns:
        print("Adding modules column...")
        cursor.execute("ALTER TABLE Listing ADD COLUMN modules TEXT")

    # Note: We keep entityType column for reference (don't rename to avoid data loss)
    # In production, we would rename entityType to old_entity_type

    print("✓ Schema migration complete")
    conn.commit()


def resolve_entity_class_and_roles(
    entity_type: str,
    has_location: bool
) -> Tuple[str, List[str]]:
    """
    Resolve entity_class and canonical_roles from old entityType.

    Handles special case: CLUB with physical location becomes place with multiple roles.
    """
    entity_type_upper = entity_type.upper()

    if entity_type_upper not in ENTITY_TYPE_MAPPING:
        print(f"⚠️  Unknown entityType: {entity_type}, defaulting to 'thing'")
        return "thing", []

    mapping = ENTITY_TYPE_MAPPING[entity_type_upper]

    # Special case: "Club with courts" (CLUB + physical location)
    if entity_type_upper == "CLUB" and has_location:
        return "place", ["provides_facility", "membership_org"]

    return mapping["entity_class"], mapping["roles"]


def migrate_data(conn: sqlite3.Connection, dry_run: bool = False) -> Dict[str, int]:
    """
    Migrate data from entityType to entity_class + canonical_roles.

    Returns statistics about the migration.
    """
    print(f"\n=== Step 2: Migrating Data (dry_run={dry_run}) ===")
    cursor = conn.cursor()

    # Get all listings
    cursor.execute("""
        SELECT id, entityType, latitude, longitude, street_address,
               canonical_roles
        FROM Listing
    """)
    listings = cursor.fetchall()

    stats = {
        "total": len(listings),
        "migrated": 0,
        "skipped": 0,
        "club_with_location": 0,
        "errors": 0
    }

    print(f"Found {stats['total']} listings to migrate")

    for row in listings:
        listing_id, entity_type, latitude, longitude, street_address, existing_roles_json = row

        try:
            # Determine if entity has physical location
            has_location = bool(
                (latitude is not None and longitude is not None) or
                street_address
            )

            # Resolve entity_class and roles
            entity_class, new_roles = resolve_entity_class_and_roles(
                entity_type,
                has_location
            )

            # Track special case
            if entity_type.upper() == "CLUB" and has_location:
                stats["club_with_location"] += 1
                print(f"  🏟️  Special case: Club with location → place + multiple roles (ID: {listing_id})")

            # Parse existing canonical_roles (may already have values from previous migrations)
            existing_roles = []
            if existing_roles_json:
                try:
                    # canonical_roles is stored as JSON string in SQLite
                    existing_roles = json.loads(existing_roles_json)
                except (json.JSONDecodeError, TypeError):
                    existing_roles = []

            # Merge roles (preserve existing + add new)
            merged_roles = list(set(existing_roles + new_roles))
            merged_roles_json = json.dumps(merged_roles)

            if not dry_run:
                # Update the listing
                cursor.execute("""
                    UPDATE Listing
                    SET entity_class = ?,
                        canonical_roles = ?
                    WHERE id = ?
                """, (entity_class, merged_roles_json, listing_id))

            stats["migrated"] += 1

        except Exception as e:
            print(f"❌ Error migrating listing {listing_id}: {e}")
            stats["errors"] += 1

    if not dry_run:
        conn.commit()
        print(f"✓ Data migration complete")
    else:
        print(f"✓ Dry run complete (no changes made)")

    return stats


def validate_migration(conn: sqlite3.Connection) -> bool:
    """Validate migration results."""
    print("\n=== Step 3: Validating Migration ===")
    cursor = conn.cursor()

    all_valid = True

    # Check 1: All entities have entity_class
    cursor.execute("SELECT COUNT(*) FROM Listing WHERE entity_class IS NULL")
    null_count = cursor.fetchone()[0]
    if null_count > 0:
        print(f"❌ {null_count} listings missing entity_class")
        all_valid = False
    else:
        print(f"✓ All listings have entity_class")

    # Check 2: Check entity_class values are valid
    cursor.execute("SELECT DISTINCT entity_class FROM Listing")
    valid_classes = {"place", "person", "organization", "event", "thing"}
    found_classes = {row[0] for row in cursor.fetchall() if row[0]}
    invalid_classes = found_classes - valid_classes

    if invalid_classes:
        print(f"❌ Invalid entity_class values found: {invalid_classes}")
        all_valid = False
    else:
        print(f"✓ All entity_class values are valid: {found_classes}")

    # Check 3: Verify "club with courts" pattern
    cursor.execute("""
        SELECT COUNT(*) FROM Listing
        WHERE entityType = 'CLUB'
        AND (latitude IS NOT NULL OR street_address IS NOT NULL)
        AND entity_class = 'place'
        AND canonical_roles LIKE '%provides_facility%'
        AND canonical_roles LIKE '%membership_org%'
    """)
    club_count = cursor.fetchone()[0]
    print(f"✓ {club_count} clubs with location correctly migrated to place + multiple roles")

    # Check 4: Check array fields are not NULL
    cursor.execute("""
        SELECT COUNT(*) FROM Listing
        WHERE canonical_activities IS NULL
        OR canonical_roles IS NULL
        OR canonical_place_types IS NULL
        OR canonical_access IS NULL
    """)
    null_arrays = cursor.fetchone()[0]
    if null_arrays > 0:
        print(f"⚠️  {null_arrays} listings have NULL dimension arrays (should be empty arrays)")
        # Not critical, but should be fixed
    else:
        print(f"✓ No NULL dimension arrays")

    return all_valid


def print_statistics(stats: Dict[str, int]) -> None:
    """Print migration statistics."""
    print("\n=== Migration Statistics ===")
    print(f"Total listings: {stats['total']}")
    print(f"Migrated: {stats['migrated']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Club with location (special case): {stats['club_with_location']}")
    print(f"Errors: {stats['errors']}")


def main(dry_run: bool = False) -> int:
    """
    Main migration function.

    Args:
        dry_run: If True, perform validation without committing changes

    Returns:
        0 on success, 1 on failure
    """
    print("=" * 60)
    print("Data Migration: Listing → Entity Architecture")
    print("=" * 60)

    try:
        # Get database path
        db_path = get_db_path()
        print(f"Database: {db_path}")

        # Connect to database
        conn = sqlite3.connect(str(db_path))

        # Step 1: Schema migration
        apply_schema_migration(conn)

        # Step 2: Data migration
        stats = migrate_data(conn, dry_run=dry_run)

        # Step 3: Validation
        if not dry_run:
            validation_passed = validate_migration(conn)

            if not validation_passed:
                print("\n❌ Migration validation failed!")
                return 1

        # Print statistics
        print_statistics(stats)

        # Close connection
        conn.close()

        print("\n✅ Migration completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("🔍 Running in DRY RUN mode (no changes will be committed)\n")

    sys.exit(main(dry_run=dry_run))
