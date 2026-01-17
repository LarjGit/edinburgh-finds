# Adding a New Entity Type - Step-by-Step Tutorial

## Overview

This tutorial shows you how to add a new entity type to Edinburgh Finds using YAML-based schema generation. We'll use **Winery** as an example, demonstrating how to scale horizontally to new verticals.

**Time Required**: ~30 minutes for your first entity, <15 minutes after that.

**What You'll Learn**:
- Creating YAML schema files
- Generating Python FieldSpecs automatically
- Testing and validating new schemas
- Using the new entity in extraction pipelines

## Prerequisites

- Edinburgh Finds project cloned and set up
- Python environment activated
- Basic understanding of YAML syntax
- Familiarity with FieldSpec concept

## Step 1: Define Your Entity's Fields

Before writing YAML, list the fields your entity needs. For a winery:

**Business Requirements**:
- What grapes do they grow? → `grape_varieties` (list of strings)
- What's their wine region? → `appellation` (string)
- Can visitors taste wines? → `tasting_room` (boolean)
- How big is their vineyard? → `vineyard_size_hectares` (float)
- What wines do they produce? → `wine_types` (list: red, white, rosé, sparkling)
- Do they offer tours? → `tours_available` (boolean)
- Can they host events? → `event_space` (boolean)

**Inherited Fields**: All entities inherit 27 base fields from `Listing`:
- entity_name, entity_type, slug
- street_address, city, postcode, coordinates
- phone, email, website_url
- social media URLs
- opening_hours, summary
- metadata fields

## Step 2: Create the YAML Schema File

Create `engine/config/schemas/winery.yaml`:

```bash
cd engine/config/schemas
touch winery.yaml
```

**File Content**:

```yaml
# ============================================================
# WINERY SCHEMA - Winery-specific fields
# ============================================================
# This schema extends the base Listing schema.
# Winery-specific fields for wine venues and vineyards.
#
# DO NOT EDIT GENERATED FILES (winery.py)
# Edit this YAML file and regenerate instead.
# ============================================================

schema:
  name: Winery
  description: Winery-specific fields for wine venues and vineyards
  extends: Listing

fields:
  # ------------------------------------------------------------------
  # FOREIGN KEY (for database relationship)
  # ------------------------------------------------------------------
  - name: listing_id
    type: string
    description: Foreign key to parent Listing
    nullable: false
    foreign_key: listings.listing_id
    primary_key: true
    exclude: true  # Internal relationship field

  # ------------------------------------------------------------------
  # VITICULTURE
  # ------------------------------------------------------------------
  - name: grape_varieties
    type: list[string]
    description: Grape varieties grown or featured at this winery
    nullable: true
    python:
      sa_column: "Column(ARRAY(String))"
    prisma:
      skip: true  # Handle as relation or JSON in Prisma
    search:
      category: viticulture
      keywords:
        - grapes
        - varieties
        - cultivars

  - name: appellation
    type: string
    description: Wine appellation or region (e.g., Bordeaux, Napa Valley)
    nullable: true
    search:
      category: viticulture
      keywords:
        - appellation
        - region
        - AOC

  - name: vineyard_size_hectares
    type: float
    description: Size of vineyard in hectares
    nullable: true

  - name: organic_certified
    type: boolean
    description: Whether the winery is certified organic
    nullable: true
    search:
      category: viticulture
      keywords:
        - organic
        - certified

  # ------------------------------------------------------------------
  # WINE PRODUCTION
  # ------------------------------------------------------------------
  - name: wine_types
    type: list[string]
    description: Types of wine produced (red, white, rosé, sparkling, dessert)
    nullable: true
    python:
      sa_column: "Column(ARRAY(String))"
    prisma:
      skip: true
    search:
      category: wine_production
      keywords:
        - wine
        - types
        - red
        - white
        - sparkling

  - name: annual_production_bottles
    type: integer
    description: Annual production volume in bottles
    nullable: true

  # ------------------------------------------------------------------
  # VISITOR EXPERIENCE
  # ------------------------------------------------------------------
  - name: tasting_room
    type: boolean
    description: Whether a tasting room is available
    nullable: true
    search:
      category: visitor_experience
      keywords:
        - tasting
        - room

  - name: tours_available
    type: boolean
    description: Whether vineyard or winery tours are offered
    nullable: true
    search:
      category: visitor_experience
      keywords:
        - tours
        - visits

  - name: reservation_required
    type: boolean
    description: Whether reservations are required for tastings/tours
    nullable: true

  - name: event_space
    type: boolean
    description: Whether the winery has event space for weddings, corporate events, etc.
    nullable: true
    search:
      category: visitor_experience
      keywords:
        - events
        - weddings
        - venue

  # ------------------------------------------------------------------
  # ADDITIONAL INFO
  # ------------------------------------------------------------------
  - name: winery_summary
    type: string
    description: A short overall description of the winery and its offerings
    nullable: true
```

**Key Points**:
- `extends: Listing` gives you all 27 base fields automatically
- Use descriptive field names (snake_case)
- Add `search` metadata for fields that should be LLM-searchable
- Use `list[string]` for arrays, with `prisma.skip: true`
- Include `winery_summary` for AI-generated overviews

## Step 3: Generate Python FieldSpec File

Run the generation command:

```bash
python -m engine.schema.generate --schema winery
```

**Expected Output**:
```
ℹ Schema directory: C:\Projects\edinburgh_finds\engine\config\schemas
ℹ Output directory: C:\Projects\edinburgh_finds\engine\schema
ℹ Found 1 schema(s) to generate

Processing: winery.yaml
✓ Generated: C:\Projects\edinburgh_finds\engine\schema\winery.py

Summary:
✓ 1 schema(s) generated successfully
```

**Generated File**: `engine/schema/winery.py`

This file now contains:
- `WINERY_SPECIFIC_FIELDS` - Your 12 winery-specific fields
- `WINERY_FIELDS` - All 27 Listing fields + 12 winery fields = 39 total
- Helper functions: `get_field_by_name()`, `get_extraction_fields()`, etc.

## Step 4: Validate the Generated Schema

Verify the generated file is correct:

```bash
# Check syntax
python -c "from engine.schema.winery import WINERY_FIELDS; print(f'✓ {len(WINERY_FIELDS)} fields loaded')"

# Validate sync
python -m engine.schema.generate --validate
```

**Expected Output**:
```
✓ listing.py: In sync
✓ venue.py: In sync
✓ winery.py: In sync
✓ All schemas are in sync!
```

## Step 5: Inspect the Generated Schema

Let's look at what was generated:

```python
from engine.schema.winery import (
    WINERY_FIELDS,           # All 39 fields (27 inherited + 12 specific)
    WINERY_SPECIFIC_FIELDS,  # Just the 12 winery-specific fields
    get_extraction_fields    # Helper to get fields for LLM extraction
)

# Count fields
print(f"Total fields: {len(WINERY_FIELDS)}")
print(f"Winery-specific: {len(WINERY_SPECIFIC_FIELDS)}")

# Show first winery-specific field
field = WINERY_SPECIFIC_FIELDS[1]  # Skip listing_id (foreign key)
print(f"\nExample field:")
print(f"  Name: {field.name}")
print(f"  Type: {field.type_annotation}")
print(f"  Description: {field.description}")
print(f"  Search category: {field.search_category}")
```

## Step 6: Create a Test File

Create `engine/tests/test_winery_schema.py`:

```python
"""Tests for Winery schema"""

import unittest
from engine.schema.winery import (
    WINERY_FIELDS,
    WINERY_SPECIFIC_FIELDS,
    get_field_by_name,
    get_extraction_fields
)


class TestWinerySchema(unittest.TestCase):
    """Test Winery schema structure"""

    def test_field_count(self):
        """Winery should have inherited + specific fields"""
        # 27 from Listing + 12 winery-specific
        self.assertGreaterEqual(len(WINERY_FIELDS), 39)

    def test_winery_specific_fields(self):
        """Winery-specific fields should be defined"""
        field_names = [f.name for f in WINERY_SPECIFIC_FIELDS]

        self.assertIn('grape_varieties', field_names)
        self.assertIn('appellation', field_names)
        self.assertIn('tasting_room', field_names)
        self.assertIn('winery_summary', field_names)

    def test_inherited_fields(self):
        """Winery should inherit Listing fields"""
        # Test some key inherited fields
        entity_name = get_field_by_name('entity_name')
        self.assertIsNotNone(entity_name)
        self.assertEqual(entity_name.description, 'Official name of the entity')

        phone = get_field_by_name('phone')
        self.assertIsNotNone(phone)

    def test_extraction_fields(self):
        """Extraction fields should exclude internal fields"""
        extraction = get_extraction_fields()

        # Should NOT include excluded fields
        names = [f.name for f in extraction]
        self.assertNotIn('listing_id', names)
        self.assertNotIn('slug', names)

        # SHOULD include searchable fields
        self.assertIn('grape_varieties', names)
        self.assertIn('tasting_room', names)

    def test_search_metadata(self):
        """Fields should have search metadata"""
        grape_varieties = get_field_by_name('grape_varieties')
        self.assertEqual(grape_varieties.search_category, 'viticulture')
        self.assertIn('grapes', grape_varieties.search_keywords)


if __name__ == '__main__':
    unittest.main()
```

Run the test:

```bash
python -m pytest engine/tests/test_winery_schema.py -v
```

## Step 7: Use in an Extractor

Create `engine/extraction/extractors/winery_extractor.py`:

```python
"""Winery data extractor"""

from typing import Dict, Any, Optional
from engine.schema.winery import get_extraction_fields


def extract_winery_data(raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract winery data from raw source.

    Args:
        raw_data: Raw data from connector (Google Places, Serper, etc.)

    Returns:
        Extracted winery data matching WINERY_FIELDS schema
    """
    # Get fields for extraction (excludes internal fields)
    extraction_fields = get_extraction_fields()

    # Build extraction prompt
    field_descriptions = []
    for field in extraction_fields:
        if not field.exclude:
            field_descriptions.append(
                f"- {field.name}: {field.description}"
            )

    # Your extraction logic here
    extracted = {
        'entity_name': raw_data.get('name'),
        'entity_type': 'WINERY',
        'street_address': raw_data.get('address'),
        # ... extract other fields

        # Winery-specific fields
        'grape_varieties': extract_grape_varieties(raw_data),
        'appellation': extract_appellation(raw_data),
        'tasting_room': raw_data.get('has_tasting_room'),
        'tours_available': raw_data.get('offers_tours'),
        # ...
    }

    return extracted


def extract_grape_varieties(raw_data: Dict[str, Any]) -> Optional[list]:
    """Extract grape varieties from raw data"""
    # Your extraction logic
    description = raw_data.get('description', '')
    # Use LLM or regex to extract varieties
    return ['Chardonnay', 'Pinot Noir']  # Example


def extract_appellation(raw_data: Dict[str, Any]) -> Optional[str]:
    """Extract wine region/appellation"""
    # Your extraction logic
    return raw_data.get('region')
```

## Step 8: Add to Entity Type Enum

Update `engine/schema/types.py`:

```python
from enum import Enum

class EntityType(str, Enum):
    """Supported entity types"""
    VENUE = "VENUE"
    RETAILER = "RETAILER"
    CAFE = "CAFE"
    RESTAURANT = "RESTAURANT"
    WINERY = "WINERY"  # ← Add this
    # ... other types
```

## Step 9: Update Database (If Using Prisma)

If you're using Prisma for the database, generate the Prisma schema:

```bash
# This would be implemented in future phases
# python -m engine.schema.generate --target prisma
```

For now, manually update `prisma/schema.prisma` or wait for Prisma generator completion.

## Step 10: Test End-to-End

Create a test winery record:

```python
from engine.schema.winery import WINERY_FIELDS

# Sample winery data
test_winery = {
    'entity_name': 'Château Test Vineyard',
    'entity_type': 'WINERY',
    'street_address': '123 Vineyard Road',
    'city': 'Bordeaux',
    'country': 'France',
    'grape_varieties': ['Merlot', 'Cabernet Sauvignon', 'Cabernet Franc'],
    'appellation': 'Bordeaux AOC',
    'tasting_room': True,
    'tours_available': True,
    'vineyard_size_hectares': 15.5,
    'wine_types': ['red', 'rosé'],
    'winery_summary': 'Family-owned vineyard producing exceptional Bordeaux blends since 1850.',
}

# Validate against schema
for field in WINERY_FIELDS:
    if field.required and not field.exclude:
        assert field.name in test_winery, f"Missing required field: {field.name}"

print("✓ Test winery data validates against schema")
```

## Summary Checklist

After completing this tutorial, you should have:

- [x] Created `engine/config/schemas/winery.yaml`
- [x] Generated `engine/schema/winery.py` automatically
- [x] Validated the schema with `--validate`
- [x] Created tests in `test_winery_schema.py`
- [x] Created extractor in `winery_extractor.py`
- [x] Updated `EntityType` enum
- [x] Tested with sample data

## Key Takeaways

**What You Learned**:
1. ✅ YAML is the single source of truth
2. ✅ Generators handle all the boilerplate
3. ✅ Schema inheritance (extends: Listing) saves massive time
4. ✅ Adding new entity types takes ~30 minutes, not days
5. ✅ Validation ensures schemas stay in sync
6. ✅ No manual FieldSpec writing needed ever again

**Time Savings**:
- **Before YAML**: 2-4 hours to manually define FieldSpecs, write Prisma schema, keep in sync
- **After YAML**: 30 minutes to write YAML, 5 seconds to generate everything

**Horizontal Scaling**:
With this system, you can now add:
- Restaurants (menu_items, cuisine_type, michelin_stars)
- Hotels (room_count, star_rating, amenities)
- Galleries (artist_count, exhibition_schedule)
- Theaters (seating_capacity, performance_types)
- Museums (collection_size, permanent_exhibits)

All following the same pattern, inheriting from Listing, with automatic code generation.

## Next Steps

1. **Add more entity types**: Try restaurant.yaml or gallery.yaml
2. **Customize extractors**: Build LLM-based extraction for your new entities
3. **Set up CI/CD**: Add `--validate` to your CI pipeline
4. **Pre-commit hooks**: Prevent manual edits to generated files
5. **Share with team**: Document your specific entity types

## Troubleshooting

**Q: Generation fails with "Field type not supported"**
A: Check your YAML `type` fields. Supported: string, integer, float, boolean, datetime, json, list[string]

**Q: Generated file has wrong field order**
A: Field order in YAML determines Python order. Reorder fields in YAML.

**Q: Import errors after generation**
A: Run `python -m engine.schema.generate --validate` to check for issues.

**Q: Want to add a field to existing entity**
A: Edit the YAML file, run generation, done. Never edit .py directly.

## Additional Resources

- [Schema Management Guide](./schema_management.md) - Comprehensive CLI documentation
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- [Conductor Plan](../conductor/tracks/yaml_schema_source_of_truth_20260116/plan.md) - Implementation plan

## Feedback

Found this tutorial helpful? Have suggestions? Please contribute to improve it!

**Congratulations!** 🎉 You've successfully added a new entity type to Edinburgh Finds using YAML-based schema generation.
