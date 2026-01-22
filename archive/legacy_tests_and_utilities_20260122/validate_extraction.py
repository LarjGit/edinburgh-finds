#!/usr/bin/env python3
"""
Validation script for Engine-Lens Architecture extraction results.
Checks that extracted entities follow the new architecture patterns.
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from collections import Counter

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set default DATABASE_URL if not set
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

from prisma import Prisma

async def validate_extraction():
    """Run validation checks on extracted entities."""

    print("=" * 80)
    print("ENGINE-LENS ARCHITECTURE EXTRACTION VALIDATION")
    print("=" * 80)
    print()

    db = Prisma()
    await db.connect()

    # ==============================================================================
    # 1. Entity counts
    # ==============================================================================
    print("1. ENTITY COUNTS")
    print("-" * 80)

    total_count = await db.listing.count()
    print(f"Total entities: {total_count}")

    # Fetch all entities and count by entity_class in Python
    all_entities = await db.listing.find_many()
    entity_class_counts = {}
    for entity in all_entities:
        entity_class = entity.entity_class or 'NULL'
        entity_class_counts[entity_class] = entity_class_counts.get(entity_class, 0) + 1

    print("\nBy entity_class:")
    for entity_class, count in sorted(entity_class_counts.items()):
        print(f"  {entity_class}: {count}")

    print()

    # ==============================================================================
    # 2. Dimension arrays
    # ==============================================================================
    print("2. DIMENSION ARRAYS")
    print("-" * 80)

    # Sample 10 entities with dimension data
    sample_entities = await db.listing.find_many(
        where={
            'OR': [
                {'canonical_activities': {'not': None}},
                {'canonical_roles': {'not': None}},
                {'canonical_place_types': {'not': None}},
                {'canonical_access': {'not': None}}
            ]
        },
        take=10
    )

    print(f"Sampling {len(sample_entities)} entities with dimension data:")
    print()

    activities_values = []
    roles_values = []
    place_types_values = []
    access_values = []

    for entity in sample_entities:
        print(f"Entity: {entity.entity_name} (class: {entity.entity_class})")

        # Parse JSON strings (SQLite storage format)
        if entity.canonical_activities:
            try:
                activities = json.loads(entity.canonical_activities) if isinstance(entity.canonical_activities, str) else entity.canonical_activities
                activities_values.extend(activities)
                print(f"  Activities: {activities}")
            except:
                print(f"  Activities: ERROR parsing {entity.canonical_activities}")

        if entity.canonical_roles:
            try:
                roles = json.loads(entity.canonical_roles) if isinstance(entity.canonical_roles, str) else entity.canonical_roles
                roles_values.extend(roles)
                print(f"  Roles: {roles}")
            except:
                print(f"  Roles: ERROR parsing {entity.canonical_roles}")

        if entity.canonical_place_types:
            try:
                place_types = json.loads(entity.canonical_place_types) if isinstance(entity.canonical_place_types, str) else entity.canonical_place_types
                place_types_values.extend(place_types)
                print(f"  Place types: {place_types}")
            except:
                print(f"  Place types: ERROR parsing {entity.canonical_place_types}")

        if entity.canonical_access:
            try:
                access = json.loads(entity.canonical_access) if isinstance(entity.canonical_access, str) else entity.canonical_access
                access_values.extend(access)
                print(f"  Access: {access}")
            except:
                print(f"  Access: ERROR parsing {entity.canonical_access}")

        print()

    # Show unique values found
    print("Unique dimension values found:")
    if activities_values:
        print(f"  Activities: {sorted(set(activities_values))[:10]}...")
    if roles_values:
        print(f"  Roles: {sorted(set(roles_values))}")
    if place_types_values:
        print(f"  Place types: {sorted(set(place_types_values))}")
    if access_values:
        print(f"  Access: {sorted(set(access_values))}")

    print()

    # ==============================================================================
    # 3. Role values validation
    # ==============================================================================
    print("3. ROLE VALUES (Universal function-style keys)")
    print("-" * 80)

    entities_with_roles = await db.listing.find_many(
        where={'canonical_roles': {'not': None}},
        take=20
    )

    all_roles = []
    for entity in entities_with_roles:
        if entity.canonical_roles:
            try:
                roles = json.loads(entity.canonical_roles) if isinstance(entity.canonical_roles, str) else entity.canonical_roles
                all_roles.extend(roles)
            except:
                pass

    role_counter = Counter(all_roles)
    print(f"Found {len(role_counter)} unique role values:")
    for role, count in role_counter.most_common():
        print(f"  {role}: {count} entities")

    # Check for function-style keys (should contain underscores, e.g., provides_facility)
    function_style_roles = [r for r in role_counter.keys() if '_' in r]
    print(f"\n✓ Function-style roles: {len(function_style_roles)}/{len(role_counter)}")

    print()

    # ==============================================================================
    # 4. Modules JSONB structure
    # ==============================================================================
    print("4. MODULES JSONB STRUCTURE (Namespaced)")
    print("-" * 80)

    entities_with_modules = await db.listing.find_many(
        where={'modules': {'not': None}},
        take=5
    )

    print(f"Sampling {len(entities_with_modules)} entities with modules:")
    print()

    for entity in entities_with_modules:
        print(f"Entity: {entity.entity_name} (class: {entity.entity_class})")

        if entity.modules:
            try:
                modules = json.loads(entity.modules) if isinstance(entity.modules, str) else entity.modules

                # Check if modules is a dict with module names as keys
                if isinstance(modules, dict):
                    module_keys = list(modules.keys())
                    print(f"  Module keys: {module_keys}")

                    # Show first module structure
                    if module_keys:
                        first_module = module_keys[0]
                        first_module_data = modules[first_module]
                        if isinstance(first_module_data, dict):
                            field_keys = list(first_module_data.keys())[:5]
                            print(f"  {first_module} fields: {field_keys}")
                        else:
                            print(f"  {first_module}: {type(first_module_data)} (unexpected structure)")
                else:
                    print(f"  ERROR: modules is not a dict, got {type(modules)}")

            except Exception as e:
                print(f"  ERROR parsing modules: {e}")

        print()

    # ==============================================================================
    # 5. Sports facility module inventory check
    # ==============================================================================
    print("5. SPORTS_FACILITY MODULE (Inventory JSON structure)")
    print("-" * 80)

    entities_with_sports = await db.listing.find_many(
        where={'modules': {'not': None}},
        take=20
    )

    sports_facility_count = 0
    for entity in entities_with_sports:
        if entity.modules:
            try:
                modules = json.loads(entity.modules) if isinstance(entity.modules, str) else entity.modules
                if isinstance(modules, dict) and 'sports_facility' in modules:
                    sports_facility_count += 1
                    if sports_facility_count <= 3:  # Show first 3
                        print(f"Entity: {entity.entity_name}")
                        sports_data = modules['sports_facility']
                        print(f"  sports_facility keys: {list(sports_data.keys()) if isinstance(sports_data, dict) else 'NOT A DICT'}")

                        # Check for inventory structure
                        if isinstance(sports_data, dict) and 'inventory' in sports_data:
                            inventory = sports_data['inventory']
                            print(f"  inventory type: {type(inventory)}")
                            if isinstance(inventory, list):
                                print(f"  inventory items: {len(inventory)}")
                                if inventory:
                                    print(f"  Sample item: {inventory[0]}")
                        print()
            except:
                pass

    print(f"Total entities with sports_facility module: {sports_facility_count}")
    print()

    # ==============================================================================
    # Summary
    # ==============================================================================
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"✓ Total entities: {total_count}")
    print(f"✓ Entity classes found: {len(entity_class_counts)}")
    print(f"✓ Entities with dimension data: {len(sample_entities)}")
    print(f"✓ Function-style roles: {len(function_style_roles)}/{len(role_counter)}")
    print(f"✓ Entities with modules: {len(entities_with_modules)}")
    print(f"✓ Entities with sports_facility module: {sports_facility_count}")
    print()

    await db.disconnect()

if __name__ == '__main__':
    asyncio.run(validate_extraction())
