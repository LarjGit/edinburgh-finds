# Summary Synthesis Extensibility Guide

## Overview

The `SummarySynthesizer` uses a **convention-based approach** to automatically discover which fields are relevant for each summary type. This means **no code changes are needed** when adding new entity types, new summary fields, or new attributes.

## How It Works

### Convention: Summary Type → Field Prefix

The synthesizer automatically extracts the field prefix from the summary type name:

```
"padel_summary"     → looks for fields starting with "padel_" or "padel"
"tennis_summary"    → looks for fields starting with "tennis_" or "tennis"
"restaurant_summary"→ looks for fields starting with "restaurant_" or "restaurant"
"winery_summary"    → looks for fields starting with "winery_" or "winery"
```

### Examples

#### Example 1: Adding a New Entity Type (RESTAURANT)

**In your schema (venue.py or future restaurant.py):**
```python
FieldSpec(
    name="restaurant_cuisine",
    type_annotation="Optional[str]",
    description="Type of cuisine served (e.g., Italian, Scottish, Asian Fusion)"
),
FieldSpec(
    name="restaurant_michelin_stars",
    type_annotation="Optional[int]",
    description="Number of Michelin stars (0-3)"
),
FieldSpec(
    name="restaurant_price_range",
    type_annotation="Optional[str]",
    description="Price category (£, ££, £££, ££££)"
),
FieldSpec(
    name="restaurant_seating_capacity",
    type_annotation="Optional[int]",
    description="Total seating capacity"
),
FieldSpec(
    name="restaurant_summary",
    type_annotation="Optional[str]",
    description="Overall summary of the restaurant experience"
),
```

**Usage (no code changes):**
```python
from engine.extraction.utils.summary_synthesis import SummarySynthesizer

synthesizer = SummarySynthesizer()

restaurant_facts = {
    "entity_name": "The Kitchin",
    "restaurant_cuisine": "Modern Scottish",
    "restaurant_michelin_stars": 1,
    "restaurant_price_range": "£££",
    "restaurant_seating_capacity": 60
}

rich_text = [
    "The Kitchin is Edinburgh's premier Michelin-starred restaurant..."
]

# Works automatically! No synthesizer code changes needed.
summary = synthesizer.synthesize_summary(
    summary_type="restaurant_summary",
    structured_facts=restaurant_facts,
    rich_text=rich_text
)
```

The synthesizer automatically:
1. Extracts prefix "restaurant_" from "restaurant_summary"
2. Finds all fields starting with "restaurant_" in the facts
3. Uses those fields for summary synthesis

#### Example 2: Adding New Fields to Existing Type

**In venue.py (new padel fields):**
```python
FieldSpec(
    name="padel_indoor_courts",
    type_annotation="Optional[int]",
    description="Number of indoor padel courts"
),
FieldSpec(
    name="padel_outdoor_courts",
    type_annotation="Optional[int]",
    description="Number of outdoor padel courts"
),
FieldSpec(
    name="padel_court_surface",
    type_annotation="Optional[str]",
    description="Type of court surface (glass, acrylic, etc.)"
),
```

**Usage (no code changes):**
```python
padel_facts = {
    "entity_name": "Game4Padel",
    "padel": True,
    "padel_total_courts": 6,
    "padel_indoor_courts": 4,  # NEW
    "padel_outdoor_courts": 2,  # NEW
    "padel_court_surface": "panoramic glass"  # NEW
}

# Automatically includes all padel_* fields!
summary = synthesizer.synthesize_summary(
    summary_type="padel_summary",
    structured_facts=padel_facts,
    rich_text=rich_text
)
```

## Special Cases: Custom Field Prefixes

Some summary types don't follow the simple convention (e.g., `swimming_summary` needs both "swimming_" and "pool" fields). For these cases, use `CUSTOM_FIELD_PREFIXES`:

**In `summary_synthesis.py`:**
```python
CUSTOM_FIELD_PREFIXES = {
    "swimming_summary": ["swimming_", "pool"],
    "parking_and_transport_summary": ["parking_", "transport", "ev_charging"],
    "amenities_summary": ["restaurant", "bar", "cafe", "wifi"],
    # Add your custom mappings here if needed
}
```

## Future Entity Types

This approach is designed to work seamlessly with:

### YAML Schema Architecture
When you implement the YAML-based schema system (Track: "YAML Schema - Single Source of Truth"), summary synthesis will automatically work:

**In `engine/config/schemas/restaurant.yaml`:**
```yaml
entity_type: RESTAURANT
fields:
  - name: restaurant_cuisine
    type: Optional[str]
  - name: restaurant_michelin_stars
    type: Optional[int]
  - name: restaurant_summary
    type: Optional[str]
```

Summary synthesis will automatically discover all `restaurant_*` fields from the generated schema.

### Additional Entity Types Examples

**WINERY:**
- `winery_grape_varieties`
- `winery_tasting_room`
- `winery_summary`

**ART_GALLERY:**
- `gallery_permanent_collection`
- `gallery_current_exhibitions`
- `gallery_summary`

**THEATER:**
- `theater_seating_capacity`
- `theater_accessibility`
- `theater_summary`

All work automatically with zero code changes to `SummarySynthesizer`!

## Testing New Summary Types

The test suite includes extensibility tests that demonstrate this works:

```python
# See: engine/tests/test_summary_synthesis.py
class TestExtensibility:
    def test_new_entity_type_restaurant_summary(self):
        """Proves new entity types work without code changes"""

    def test_new_fields_added_to_existing_type(self):
        """Proves new fields work without code changes"""

    def test_convention_based_field_discovery(self):
        """Tests the internal field discovery logic"""
```

## Summary

✅ **Convention-based**: Field discovery works via naming patterns
✅ **Zero code changes**: New entity types and fields work automatically
✅ **YAML-ready**: Designed for future YAML schema architecture
✅ **Tested**: Extensibility proven with comprehensive tests
✅ **Future-proof**: Scales horizontally across unlimited entity types

When adding new entity types or summary fields, just follow the naming convention:
- Summary field: `{entity_type}_summary`
- Related fields: `{entity_type}_*`

The `SummarySynthesizer` handles the rest automatically.
