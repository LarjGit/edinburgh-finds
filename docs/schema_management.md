# Schema Management Guide

## Overview

Edinburgh Finds uses **YAML-based schema generation** to maintain a single source of truth for all database schemas and field definitions. This eliminates schema drift and enables rapid horizontal scaling across new entity types.

## Architecture

```
engine/config/schemas/*.yaml  →  [Parser]  →  [Generators]  →  Output
                                                    ↓
                                              - Python FieldSpecs
                                              - Prisma schemas
                                              - TypeScript types (future)
```

**Key Principle**: YAML is the single source of truth. Never edit generated files directly.

## CLI Tool

The schema generation CLI tool provides commands for generating, validating, and managing schemas.

### Installation

The CLI is built-in - no installation needed. Just use Python's module execution:

```bash
python -m engine.schema.generate [options]
```

### Commands

#### Generate All Schemas

Generate Python FieldSpec files for all schemas:

```bash
python -m engine.schema.generate
```

#### Generate Specific Schema

Generate only one schema:

```bash
python -m engine.schema.generate --schema listing
python -m engine.schema.generate --schema venue
```

#### Validate Schema Sync

Check if generated files match YAML (CI/CD integration):

```bash
python -m engine.schema.generate --validate
```

Exit codes:
- `0`: All schemas in sync
- `1`: Schema drift detected

#### Dry Run

Preview what would be generated without writing files:

```bash
python -m engine.schema.generate --dry-run
```

#### Force Overwrite

Skip confirmation prompts:

```bash
python -m engine.schema.generate --force
```

#### Format Output

Auto-format generated files with Black:

```bash
python -m engine.schema.generate --format
```

### Options Reference

| Flag | Description | Example |
|------|-------------|---------|
| `--validate` | Check for schema drift | `--validate` |
| `--schema SCHEMA` | Generate specific schema | `--schema listing` |
| `--output-dir DIR` | Custom output directory | `--output-dir ./generated` |
| `--schema-dir DIR` | Custom YAML directory | `--schema-dir ./schemas` |
| `--force` | Overwrite without prompt | `--force` |
| `--dry-run` | Preview only | `--dry-run` |
| `--format` | Format with Black | `--format` |
| `--no-color` | Disable colored output | `--no-color` |

### Examples

**Development workflow:**
```bash
# 1. Edit YAML schema
vim engine/config/schemas/listing.yaml

# 2. Preview changes
python -m engine.schema.generate --dry-run

# 3. Generate and format
python -m engine.schema.generate --force --format

# 4. Validate
python -m engine.schema.generate --validate
```

**CI/CD validation:**
```bash
# In your CI pipeline
python -m engine.schema.generate --validate --no-color
if [ $? -ne 0 ]; then
  echo "Schema drift detected! Regenerate schemas."
  exit 1
fi
```

## YAML Schema Format

### Basic Structure

```yaml
schema:
  name: EntityName
  description: Entity description
  extends: null  # or ParentSchema for inheritance

fields:
  - name: field_name
    type: string  # string, integer, float, boolean, datetime, json, list[string]
    description: Field description
    nullable: true  # true or false
    required: false  # true or false

    # Optional constraints
    index: true
    unique: true
    primary_key: true
    foreign_key: "table.column"
    exclude: true  # Exclude from LLM extraction
    default: value

    # Search metadata
    search:
      category: location
      keywords:
        - address
        - street

    # Generator-specific overrides
    python:
      type_annotation: "Dict[str, Any]"
      default: "default_factory=dict"
      sa_column: "Column(JSON)"

    prisma:
      type: "String"
      skip: true
      attributes:
        - "@id"
        - "@default(cuid())"
```

### Supported Types

| YAML Type | Python Type | Prisma Type |
|-----------|-------------|-------------|
| `string` | `str` / `Optional[str]` | `String` / `String?` |
| `integer` | `int` / `Optional[int]` | `Int` / `Int?` |
| `float` | `float` / `Optional[float]` | `Float` / `Float?` |
| `boolean` | `bool` / `Optional[bool]` | `Boolean` / `Boolean?` |
| `datetime` | `datetime` / `Optional[datetime]` | `DateTime` / `DateTime?` |
| `json` | `Dict[str, Any]` | `String` (SQLite) / `Json` (PostgreSQL) |
| `list[string]` | `List[str]` / `Optional[List[str]]` | Use `prisma.type` or `prisma.skip` |

### Schema Inheritance

Venue extends Listing:

```yaml
# venue.yaml
schema:
  name: Venue
  description: Venue-specific fields
  extends: Listing  # Inherits all Listing fields

fields:
  - name: tennis
    type: boolean
    description: Whether tennis is available
    nullable: true
```

Generated Python:
```python
from .listing import LISTING_FIELDS

VENUE_SPECIFIC_FIELDS: List[FieldSpec] = [
    # venue-specific fields only
]

VENUE_FIELDS: List[FieldSpec] = LISTING_FIELDS + VENUE_SPECIFIC_FIELDS
```

## Adding a New Entity Type

### Example: Adding a "Winery" Entity

**Step 1**: Create YAML schema

```bash
# Create winery.yaml
cat > engine/config/schemas/winery.yaml <<EOF
schema:
  name: Winery
  description: Winery-specific fields for wine venues
  extends: Listing

fields:
  - name: grape_varieties
    type: list[string]
    description: Grape varieties grown or featured
    nullable: true
    python:
      sa_column: "Column(ARRAY(String))"

  - name: appellation
    type: string
    description: Wine appellation or region
    nullable: true

  - name: tasting_room
    type: boolean
    description: Whether a tasting room is available
    nullable: true

  - name: vineyard_size_hectares
    type: float
    description: Size of vineyard in hectares
    nullable: true
EOF
```

**Step 2**: Generate schemas

```bash
python -m engine.schema.generate --schema winery
```

**Step 3**: Verify

```bash
# Check generated file
cat engine/schema/winery.py

# Validate
python -m engine.schema.generate --validate
```

**Step 4**: Use in extraction engine

```python
from engine.schema.winery import WINERY_FIELDS, WINERY_SPECIFIC_FIELDS

# Use in your extractor
def extract_winery_data(raw_data):
    extraction_fields = WINERY_FIELDS
    # ... extraction logic
```

**That's it!** No code changes needed - just YAML + generation.

## Workflow Best Practices

### Development Workflow

1. **Edit YAML First**: Always edit `.yaml` files, never `.py` files
2. **Preview Changes**: Use `--dry-run` to see what will be generated
3. **Generate**: Run generation command
4. **Validate**: Use `--validate` to confirm sync
5. **Test**: Run test suite to ensure no regressions
6. **Commit**: Commit YAML changes and generated files together

### Git Workflow

**Before committing:**
```bash
# 1. Generate schemas
python -m engine.schema.generate --force

# 2. Validate
python -m engine.schema.generate --validate

# 3. Run tests
pytest engine/tests/test_schema_sync.py

# 4. Stage changes
git add engine/config/schemas/*.yaml
git add engine/schema/*.py

# 5. Commit
git commit -m "feat(schema): Add new winery entity"
```

### Pre-Commit Hook (Optional)

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "Validating schema synchronization..."
python -m engine.schema.generate --validate --no-color

if [ $? -ne 0 ]; then
  echo ""
  echo "❌ Schema drift detected!"
  echo "Run: python -m engine.schema.generate --force"
  echo ""
  exit 1
fi

echo "✅ Schemas are in sync"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### Schema Drift Detected

**Problem**: `--validate` reports schemas out of sync

**Solution**:
```bash
python -m engine.schema.generate --force
```

### Import Errors After Generation

**Problem**: Generated files have import errors

**Solution**:
1. Check YAML syntax is valid
2. Ensure `python.type_annotation` overrides are correct
3. Verify custom imports exist (e.g., EntityType)

### Field Order Matters

**Problem**: Generated schema has different field order than manual

**Solution**: Field order in YAML determines field order in Python. Update YAML to match desired order.

### List Types in Prisma

**Problem**: Prisma generator fails on `list[string]` types

**Solution**: Add `prisma.skip` or `prisma.type` to YAML:

```yaml
- name: categories
  type: list[string]
  prisma:
    skip: true  # Skip in Prisma generation
    # OR
    type: "Category[]"  # Use relation
```

## Testing

### Validation Tests

Schema sync tests ensure YAML matches generated files:

```bash
pytest engine/tests/test_schema_sync.py -v
```

These tests check:
- Field count matches
- Field names and order match
- Field attributes match (nullable, required, index, etc.)
- Search metadata matches
- No duplicates
- Schema integrity

### Adding Tests for New Schemas

When adding a new entity schema, update `test_schema_sync.py`:

```python
def test_winery_yaml_field_count_matches_manual(self):
    """Test that winery.yaml has same number of fields as manual winery.py"""
    winery_yaml = self.schema_dir / "winery.yaml"
    schema = self.parser.parse(winery_yaml)

    self.assertEqual(len(schema.fields), len(manual_winery_fields))
```

## FAQ

**Q: Can I edit generated `.py` files directly?**
A: No. Always edit YAML. Generated files will be overwritten.

**Q: How do I add a new field to an existing entity?**
A: Add the field to the YAML file, then regenerate.

**Q: Can I have custom business logic in generated files?**
A: No. Generated files are pure schema definitions. Put business logic in separate modules.

**Q: What if I need a type not in the supported list?**
A: Use `python.type_annotation` override in YAML to specify custom types.

**Q: How do I migrate an existing manual schema to YAML?**
A: See Phase 4 of the implementation plan. Use the conversion script as reference.

## Related Documentation

- [Adding Entity Types](./adding_entity_type.md)
- [Architecture Overview](../ARCHITECTURE.md)
- [Extraction Engine Guide](./extraction_engine.md)

## References

- YAML Schema Source: `engine/config/schemas/`
- Generator Source: `engine/schema/generators/`
- CLI Source: `engine/schema/cli.py`
- Tests: `engine/tests/test_schema_sync.py`
