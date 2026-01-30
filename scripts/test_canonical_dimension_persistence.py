"""
Manual validation that canonical dimensions can be persisted to database.

Tests that Entity table schema supports canonical dimension arrays and
that Prisma client can insert/query them correctly.
"""
import asyncio
from prisma import Prisma
import json


async def main():
    """Test canonical dimension persistence."""
    db = Prisma()
    await db.connect()

    print("=" * 80)
    print("CANONICAL DIMENSION PERSISTENCE VALIDATION")
    print("=" * 80)
    print()

    # Create test entity with canonical dimensions
    test_entity = {
        "entity_name": "Test Padel Club (Validation)",
        "entity_class": "place",
        "slug": "test-padel-club-validation",
        "canonical_activities": ["padel", "tennis"],
        "canonical_place_types": ["sports_facility"],
        "canonical_roles": ["provides_facility"],
        "canonical_access": ["public"],
        "discovered_attributes": json.dumps({}),  # Required Json field (must be JSON string)
        "modules": json.dumps({
            "core": {
                "entity_name": "Test Padel Club (Validation)",
                "slug": "test-padel-club-validation"
            }
        }),
        "opening_hours": json.dumps({}),  # Required Json field (must be JSON string)
        "source_info": json.dumps({}),  # Required Json field (must be JSON string)
        "field_confidence": json.dumps({}),  # Required Json field (must be JSON string)
        "external_ids": json.dumps({})  # Required Json field (must be JSON string)
    }

    try:
        # Insert test entity
        print("Inserting test entity...")
        created = await db.entity.create(data=test_entity)
        print(f"✓ Entity created with ID: {created.id}")
        print()

        # Query back from database
        print("Querying entity from database...")
        fetched = await db.entity.find_unique(where={"id": created.id})

        if not fetched:
            print("✗ FAIL: Entity not found after creation")
            await db.disconnect()
            return

        print(f"✓ Entity retrieved: {fetched.entity_name}")
        print()

        # Verify canonical dimensions
        print("Verifying canonical dimensions...")
        checks_passed = 0
        checks_total = 4

        # Check canonical_activities
        if fetched.canonical_activities == test_entity["canonical_activities"]:
            print(f"✓ canonical_activities: {fetched.canonical_activities}")
            checks_passed += 1
        else:
            print(f"✗ canonical_activities mismatch:")
            print(f"  Expected: {test_entity['canonical_activities']}")
            print(f"  Got: {fetched.canonical_activities}")

        # Check canonical_place_types
        if fetched.canonical_place_types == test_entity["canonical_place_types"]:
            print(f"✓ canonical_place_types: {fetched.canonical_place_types}")
            checks_passed += 1
        else:
            print(f"✗ canonical_place_types mismatch:")
            print(f"  Expected: {test_entity['canonical_place_types']}")
            print(f"  Got: {fetched.canonical_place_types}")

        # Check canonical_roles
        if fetched.canonical_roles == test_entity["canonical_roles"]:
            print(f"✓ canonical_roles: {fetched.canonical_roles}")
            checks_passed += 1
        else:
            print(f"✗ canonical_roles mismatch:")
            print(f"  Expected: {test_entity['canonical_roles']}")
            print(f"  Got: {fetched.canonical_roles}")

        # Check canonical_access
        if fetched.canonical_access == test_entity["canonical_access"]:
            print(f"✓ canonical_access: {fetched.canonical_access}")
            checks_passed += 1
        else:
            print(f"✗ canonical_access mismatch:")
            print(f"  Expected: {test_entity['canonical_access']}")
            print(f"  Got: {fetched.canonical_access}")

        print()
        print(f"Checks passed: {checks_passed}/{checks_total}")
        print()

        # Cleanup
        print("Cleaning up test entity...")
        await db.entity.delete(where={"id": created.id})
        print("✓ Test entity deleted")
        print()

        # Final verdict
        if checks_passed == checks_total:
            print("=" * 80)
            print("✅ DATABASE PERSISTENCE VALIDATION PASSED")
            print("=" * 80)
            print()
            print("Entity table schema supports canonical dimension arrays.")
            print("Prisma client can insert and query canonical dimensions correctly.")
        else:
            print("=" * 80)
            print("✗ DATABASE PERSISTENCE VALIDATION FAILED")
            print("=" * 80)
            print()
            print(f"{checks_total - checks_passed} checks failed.")

    except Exception as e:
        print()
        print("✗ ERROR during validation:")
        print(f"  {type(e).__name__}: {str(e)}")
        print()
        import traceback
        traceback.print_exc()

    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
