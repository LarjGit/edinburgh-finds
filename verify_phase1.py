"""Quick script to verify Phase 1 lens mapping results in database."""
import os
from prisma import Prisma

async def verify_phase1():
    """Check if Powerleague entities have canonical dimensions populated."""
    db = Prisma()
    await db.connect()

    try:
        # Check raw ingestions
        raw_count = await db.rawingestion.count()
        print(f"Total raw ingestions: {raw_count}")

        # Check extracted entities
        extracted_count = await db.extractedentity.count()
        print(f"Total extracted entities: {extracted_count}")

        # First check total entity count
        total_count = await db.entity.count()
        print(f"Total finalized entities: {total_count}")

        # Query for extracted entities with activity or location keywords
        extracted_entities = await db.extractedentity.find_many(
            where={
                "OR": [
                    {"entity_name": {"contains": "padel", "mode": "insensitive"}},
                    {"entity_name": {"contains": "power", "mode": "insensitive"}},
                    {"entity_name": {"contains": "portobello", "mode": "insensitive"}},
                ]
            },
            take=3
        )

        print(f"\nFound {len(extracted_entities)} extracted entities matching search:")
        print("=" * 80)

        for entity in extracted_entities:
            print(f"\nEntity: {entity.entity_name}")
            print(f"  Class: {entity.entity_class}")
            print(f"  Activities: {entity.canonical_activities}")
            print(f"  Place Types: {entity.canonical_place_types}")
            print(f"  Roles: {entity.canonical_roles}")

        # Check validation criteria
        if extracted_entities:
            entity = extracted_entities[0]
            print("\n" + "=" * 80)
            print("VALIDATION RESULTS:")
            print(f"  ✓ ExtractedEntity exists: {entity.entity_name}")
            print(f"  ✓ entity_class = '{entity.entity_class}'")

            has_activities = entity.canonical_activities and len(entity.canonical_activities) > 0
            has_place_types = entity.canonical_place_types and len(entity.canonical_place_types) > 0

            print(f"  {'✓' if has_activities else '✗'} canonical_activities populated: {entity.canonical_activities}")
            print(f"  {'✓' if has_place_types else '✗'} canonical_place_types populated: {entity.canonical_place_types}")

            if has_activities and has_place_types:
                print("\n✅ PHASE 1 VALIDATION PASSED!")
                print("   Lens mapping successfully populated canonical dimensions!")
            else:
                print("\n❌ PHASE 1 VALIDATION FAILED - Missing canonical dimensions")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(verify_phase1())
