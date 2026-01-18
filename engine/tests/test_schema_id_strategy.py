"""
Tests for Prisma schema ID strategy consistency.

This test ensures that all models in schema.prisma use a consistent ID strategy
(either cuid or uuid, but never mixed). Mixing ID strategies can lead to:
- Type confusion in foreign key relationships
- Migration issues when moving to production databases
- Debugging complexity when IDs have different formats

Rule: All @id fields and @default() functions must use the SAME strategy.
"""

import re
from pathlib import Path


def get_prisma_schema_path():
    """Get the path to the Prisma schema file."""
    # Assuming this test runs from project root or engine/tests
    project_root = Path(__file__).parent.parent.parent
    schema_path = project_root / "web" / "prisma" / "schema.prisma"
    return schema_path


def extract_id_strategies(schema_content):
    """
    Extract all ID strategies from the schema.

    Returns a dict with model names as keys and their ID strategies as values.
    Example: {"Category": "cuid", "Listing": "cuid"}
    """
    strategies = {}

    # Pattern to match model definitions and their id fields
    # Matches: id String @id @default(cuid()) or id String @id @default(uuid())
    model_pattern = r'model\s+(\w+)\s*\{'
    id_pattern = r'id\s+String\s+@id\s+@default\((cuid|uuid)\(\)\)'

    lines = schema_content.split('\n')
    current_model = None

    for line in lines:
        model_match = re.search(model_pattern, line)
        if model_match:
            current_model = model_match.group(1)
            continue

        if current_model:
            id_match = re.search(id_pattern, line)
            if id_match:
                strategy = id_match.group(1)
                strategies[current_model] = strategy
                current_model = None  # Reset after finding ID

    return strategies


def test_all_models_use_consistent_id_strategy():
    """
    Verify that all models use the same ID strategy (no mixing).

    This test will FAIL if:
    - Some models use cuid() while others use uuid()
    - Any model uses a different ID strategy

    This test will PASS if:
    - All models consistently use cuid() OR
    - All models consistently use uuid()
    """
    schema_path = get_prisma_schema_path()
    assert schema_path.exists(), f"Schema file not found at {schema_path}"

    schema_content = schema_path.read_text(encoding='utf-8')
    strategies = extract_id_strategies(schema_content)

    # Ensure we found at least some models with IDs
    assert len(strategies) > 0, "No models with @id @default() found in schema"

    # Get unique strategies
    unique_strategies = set(strategies.values())

    # CRITICAL: All models must use the SAME strategy
    assert len(unique_strategies) == 1, (
        f"Mixed ID strategies detected! Found {len(unique_strategies)} different strategies.\n"
        f"Models and their strategies: {strategies}\n"
        f"Unique strategies: {unique_strategies}\n"
        f"RULE: All models must use either 'cuid' OR 'uuid', never mixed."
    )

    # Document which strategy is being used
    chosen_strategy = unique_strategies.pop()
    print(f"\n✓ ID Strategy Validation PASSED")
    print(f"  All {len(strategies)} models consistently use: {chosen_strategy}()")
    print(f"  Models checked: {', '.join(strategies.keys())}")


def test_no_autoincrement_ids():
    """
    Verify that no models use autoincrement IDs (Int @id @default(autoincrement())).

    Autoincrement IDs are not suitable for distributed systems or Supabase.
    All models should use String IDs with cuid() or uuid().
    """
    schema_path = get_prisma_schema_path()
    schema_content = schema_path.read_text(encoding='utf-8')

    # Pattern to detect autoincrement IDs
    autoincrement_pattern = r'@default\(autoincrement\(\)\)'
    matches = re.findall(autoincrement_pattern, schema_content)

    assert len(matches) == 0, (
        f"Found {len(matches)} autoincrement ID(s) in schema.\n"
        f"RULE: Use String IDs with cuid() or uuid() for distributed systems."
    )

    print(f"\n✓ No autoincrement IDs detected (distributed-system ready)")


def test_foreign_keys_match_id_type():
    """
    Verify that all foreign key fields use String type (matching cuid/uuid IDs).

    If IDs are String @default(cuid/uuid), then foreign keys must also be String.
    """
    schema_path = get_prisma_schema_path()
    schema_content = schema_path.read_text(encoding='utf-8')

    # Find all foreign key field definitions (ending with Id, ListingId, etc.)
    # Pattern: fieldName String (where fieldName ends with 'Id')
    fk_pattern = r'(\w+Id)\s+(String|Int)'
    matches = re.findall(fk_pattern, schema_content)

    non_string_fks = [(field, fk_type) for field, fk_type in matches if fk_type != 'String']

    assert len(non_string_fks) == 0, (
        f"Found {len(non_string_fks)} foreign key(s) with non-String type.\n"
        f"Foreign keys with issues: {non_string_fks}\n"
        f"RULE: If @id fields use String (cuid/uuid), all foreign keys must be String."
    )

    print(f"\n✓ All {len(matches)} foreign keys use String type (matching ID strategy)")
