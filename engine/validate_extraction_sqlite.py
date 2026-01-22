#!/usr/bin/env python3
"""
Validation script for Engine-Lens Architecture extraction results using SQLite directly.
Checks that extracted entities follow the new architecture patterns.
"""

import sqlite3
import json
from pathlib import Path
from collections import Counter

# Database path
project_root = Path(__file__).parent.parent
db_path = project_root / "web" / "dev.db"

print("=" * 80)
print("ENGINE-LENS ARCHITECTURE EXTRACTION VALIDATION")
print("=" * 80)
print()
print(f"Using database: {db_path}")
print()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ==============================================================================
# 1. Entity counts
# ==============================================================================
print("1. ENTITY COUNTS")
print("-" * 80)

cursor.execute("SELECT COUNT(*) FROM Entity")
total_count = cursor.fetchone()[0]
print(f"Total entities: {total_count}")

# Count by entity_class
cursor.execute("SELECT entity_class, COUNT(*) FROM Entity GROUP BY entity_class")
entity_class_counts = cursor.fetchall()

print("\nBy entity_class:")
for entity_class, count in sorted(entity_class_counts):
    entity_class_display = entity_class or 'NULL'
    print(f"  {entity_class_display}: {count}")

print()

# ==============================================================================
# 2. Dimension arrays
# ==============================================================================
print("2. DIMENSION ARRAYS")
print("-" * 80)

cursor.execute("""
    SELECT entity_name, entity_class,
           canonical_activities, canonical_roles,
           canonical_place_types, canonical_access
    FROM Entity
    WHERE canonical_activities IS NOT NULL
       OR canonical_roles IS NOT NULL
       OR canonical_place_types IS NOT NULL
       OR canonical_access IS NOT NULL
""")

sample_entities = cursor.fetchall()
print(f"Found {len(sample_entities)} entities with dimension data:")
print()

activities_values = []
roles_values = []
place_types_values = []
access_values = []

for row in sample_entities[:10]:  # Sample first 10
    entity_name, entity_class, activities_str, roles_str, place_types_str, access_str = row

    print(f"Entity: {entity_name} (class: {entity_class})")

    if activities_str:
        try:
            activities = json.loads(activities_str)
            activities_values.extend(activities)
            print(f"  Activities: {activities}")
        except:
            print(f"  Activities: ERROR parsing")

    if roles_str:
        try:
            roles = json.loads(roles_str)
            roles_values.extend(roles)
            print(f"  Roles: {roles}")
        except:
            print(f"  Roles: ERROR parsing")

    if place_types_str:
        try:
            place_types = json.loads(place_types_str)
            place_types_values.extend(place_types)
            print(f"  Place types: {place_types}")
        except:
            print(f"  Place types: ERROR parsing")

    if access_str:
        try:
            access = json.loads(access_str)
            access_values.extend(access)
            print(f"  Access: {access}")
        except:
            print(f"  Access: ERROR parsing")

    print()

# Show unique values found
print("Unique dimension values found:")
if activities_values:
    unique_activities = sorted(set(activities_values))
    print(f"  Activities ({len(unique_activities)}): {unique_activities[:10]}{'...' if len(unique_activities) > 10 else ''}")
if roles_values:
    unique_roles = sorted(set(roles_values))
    print(f"  Roles ({len(unique_roles)}): {unique_roles}")
if place_types_values:
    unique_place_types = sorted(set(place_types_values))
    print(f"  Place types ({len(unique_place_types)}): {unique_place_types}")
if access_values:
    unique_access = sorted(set(access_values))
    print(f"  Access ({len(unique_access)}): {unique_access}")

print()

# ==============================================================================
# 3. Role values validation
# ==============================================================================
print("3. ROLE VALUES (Universal function-style keys)")
print("-" * 80)

cursor.execute("SELECT canonical_roles FROM Entity WHERE canonical_roles IS NOT NULL")
role_rows = cursor.fetchall()

all_roles = []
for row in role_rows:
    roles_str = row[0]
    if roles_str:
        try:
            roles = json.loads(roles_str)
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

cursor.execute("SELECT entity_name, entity_class, modules FROM Entity WHERE modules IS NOT NULL LIMIT 10")
module_rows = cursor.fetchall()

print(f"Found {len(module_rows)} entities with modules:")
print()

for row in module_rows:
    entity_name, entity_class, modules_str = row
    print(f"Entity: {entity_name} (class: {entity_class})")

    if modules_str:
        try:
            modules = json.loads(modules_str)

            # Check if modules is a dict with module names as keys
            if isinstance(modules, dict):
                module_keys = list(modules.keys())
                print(f"  Module keys: {module_keys}")

                # Show first module structure
                if module_keys:
                    first_module = module_keys[0]
                    first_module_data = modules[first_module]
                    if isinstance(first_module_data, dict):
                        field_keys = list(first_module_data.keys())[:10]
                        print(f"  {first_module} fields: {field_keys}")

                        # Show a sample field value
                        if field_keys:
                            sample_key = field_keys[0]
                            sample_value = first_module_data[sample_key]
                            print(f"    Sample: {sample_key} = {sample_value}")
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

cursor.execute("SELECT entity_name, modules FROM Entity WHERE modules IS NOT NULL")
sports_rows = cursor.fetchall()

sports_facility_count = 0
for row in sports_rows:
    entity_name, modules_str = row
    if modules_str:
        try:
            modules = json.loads(modules_str)
            if isinstance(modules, dict) and 'sports_facility' in modules:
                sports_facility_count += 1
                if sports_facility_count <= 3:  # Show first 3
                    print(f"Entity: {entity_name}")
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
print(f"✓ Unique role values: {len(role_counter)}")
print(f"✓ Function-style roles: {len(function_style_roles)}/{len(role_counter)}")
print(f"✓ Entities with modules: {len(module_rows)}")
print(f"✓ Entities with sports_facility module: {sports_facility_count}")
print()

# ==============================================================================
# Validation Checks
# ==============================================================================
print("=" * 80)
print("VALIDATION CHECKS")
print("=" * 80)

checks_passed = []
checks_failed = []

# Check 1: Entity count > 0
if total_count > 0:
    checks_passed.append("Entity count > 0")
else:
    checks_failed.append("Entity count is 0")

# Check 2: Entity classes are valid
valid_classes = ['place', 'person', 'organization', 'event', 'thing']
invalid_classes = [ec for ec, _ in entity_class_counts if ec and ec not in valid_classes]
if not invalid_classes:
    checks_passed.append("All entity classes are valid")
else:
    checks_failed.append(f"Invalid entity classes found: {invalid_classes}")

# Check 3: Roles use function-style keys
if len(function_style_roles) == len(role_counter) and len(role_counter) > 0:
    checks_passed.append("All roles use function-style keys")
elif len(role_counter) == 0:
    checks_passed.append("No roles to validate (acceptable)")
else:
    non_function_roles = [r for r in role_counter.keys() if '_' not in r]
    checks_failed.append(f"Non-function-style roles found: {non_function_roles}")

# Check 4: Modules are namespaced (dict structure)
if len(module_rows) > 0:
    all_namespaced = True
    for row in module_rows:
        _, _, modules_str = row
        if modules_str:
            try:
                modules = json.loads(modules_str)
                if not isinstance(modules, dict):
                    all_namespaced = False
                    break
            except:
                all_namespaced = False
                break

    if all_namespaced:
        checks_passed.append("All modules are properly namespaced")
    else:
        checks_failed.append("Some modules are not namespaced correctly")
else:
    checks_passed.append("No modules to validate (acceptable)")

print("\n✓ PASSED:")
for check in checks_passed:
    print(f"  - {check}")

if checks_failed:
    print("\n✗ FAILED:")
    for check in checks_failed:
        print(f"  - {check}")
else:
    print("\n✓ ALL CHECKS PASSED!")

print()

conn.close()
