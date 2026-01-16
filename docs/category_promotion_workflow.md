# Category Promotion Workflow

This document explains the category management system in Edinburgh Finds and how raw categories from extraction are promoted to canonical categories used for navigation and filtering.

## Overview

Edinburgh Finds uses a **two-tier category system**:

1. **Raw Categories** (`Listing.categories`): Uncontrolled, free-form categories extracted from data sources
2. **Canonical Categories** (`Listing.canonical_categories`): Controlled taxonomy used for site navigation, filtering, and search

This approach preserves the original data while providing a consistent user experience.

## Architecture

### Data Flow

```
┌─────────────────┐
│  Data Sources   │ (Google Places, OSM, Edinburgh Council, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Extractors    │ Extract raw categories (e.g., "Tennis Club", "Leisure Centre")
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Listing.        │ Store raw categories (array of strings)
│  categories     │ e.g., ["Tennis Club", "Leisure Centre", "Private Members"]
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Category Mapper │ Apply regex pattern matching rules
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Listing.        │ Store canonical categories (array of keys)
│  canonical_     │ e.g., ["tennis", "sports_centre", "private_club"]
│  categories     │
└─────────────────┘
```

### Components

1. **Taxonomy** (`engine/config/canonical_categories.yaml`):
   - Defines all valid canonical categories
   - Hierarchical structure (e.g., "padel" → parent: "venue")
   - Display names, descriptions, search keywords

2. **Mapping Rules** (`engine/config/canonical_categories.yaml`):
   - Regex patterns that map raw categories to canonical ones
   - Confidence scores (0-1) for each mapping
   - Applied in order, one raw category can match multiple rules

3. **Category Mapper** (`engine/extraction/utils/category_mapper.py`):
   - Python module that loads config and applies mapping logic
   - Functions for mapping, validation, and hierarchy navigation
   - Caches config for performance

## Canonical Taxonomy Structure

### Top-Level Entity Types

- **venue**: Physical locations (sports centres, gyms, clubs)
- **retail**: Shops and equipment retailers
- **coach**: Coaching services and academies
- **club**: Membership organizations
- **event**: Tournaments, leagues, competitions

### Sport Types (Padel-First)

- **padel**: Padel courts and facilities
- **tennis**: Tennis courts and facilities
- **squash**: Squash courts
- **badminton**: Badminton courts
- **pickleball**: Pickleball courts
- **table_tennis**: Table tennis facilities

### Venue Subtypes

- **sports_centre**: Multi-sport facilities
- **gym**: Fitness and gym facilities
- **swimming_pool**: Swimming and aquatic facilities
- **outdoor_pitch**: Outdoor sports pitches
- **private_club**: Members-only clubs
- **public_facility**: Publicly accessible facilities

See `engine/config/canonical_categories.yaml` for the complete taxonomy.

## Mapping Process

### Step 1: Extraction

During the extraction phase, extractors capture raw categories as-is from source data:

```python
# Google Places might return:
raw_categories = ["gym", "health_club", "sports_complex"]

# OSM might provide:
raw_categories = ["leisure=sports_centre", "sport=tennis"]

# Edinburgh Council might have:
raw_categories = ["Sports Centre", "Swimming Pool"]
```

These are stored in `Listing.categories` without modification.

### Step 2: Automatic Mapping

The `category_mapper` applies mapping rules to convert raw categories to canonical ones:

```python
from engine.extraction.utils.category_mapper import map_to_canonical

raw = ["Tennis Club", "Indoor Sports Facility"]
canonical = map_to_canonical(raw)
# Result: ['tennis', 'sports_centre']
```

Mapping rules use regex patterns:

```yaml
mapping_rules:
  - pattern: "(?i)\\btennis\\b"
    canonical: tennis
    confidence: 1.0

  - pattern: "(?i)sports\\s+(centre|center)"
    canonical: sports_centre
    confidence: 0.95
```

### Step 3: Confidence Filtering

Only mappings above the confidence threshold (default: 0.7) are included:

```python
# Rule with confidence 0.9 → INCLUDED
# Rule with confidence 0.5 → EXCLUDED (below threshold)
```

You can customize the threshold:

```python
canonical = map_to_canonical(raw, min_confidence=0.8)
```

### Step 4: Deduplication and Limiting

- Duplicate canonical categories are removed
- Results are limited to `max_categories` (default: 5)

### Step 5: Storage

Canonical categories are stored in `Listing.canonical_categories`:

```sql
-- PostgreSQL array of strings
canonical_categories: ['tennis', 'sports_centre', 'gym']
```

## Using the Category Mapper

### Basic Usage

```python
from engine.extraction.utils.category_mapper import map_to_canonical

raw_categories = ["Padel Club", "Private Members", "Indoor Courts"]
canonical_categories = map_to_canonical(raw_categories)
# ['padel', 'private_club']
```

### Custom Confidence Threshold

```python
canonical = map_to_canonical(
    raw_categories,
    min_confidence=0.8  # More strict
)
```

### Single Category Analysis

For debugging or manual review:

```python
from engine.extraction.utils.category_mapper import map_single_category

matches = map_single_category("Indoor Tennis Sports Centre")
# [('tennis', 1.0), ('sports_centre', 0.95)]
```

### Validation

Check if categories are valid:

```python
from engine.extraction.utils.category_mapper import validate_canonical_categories

categories = ['tennis', 'padel', 'invalid_cat']
valid, invalid = validate_canonical_categories(categories)
# valid: ['tennis', 'padel']
# invalid: ['invalid_cat']
```

### Get Display Names

For UI rendering:

```python
from engine.extraction.utils.category_mapper import get_category_display_name

display = get_category_display_name('sports_centre')
# 'Sports Centre'
```

### Get Hierarchy

Navigate parent-child relationships:

```python
from engine.extraction.utils.category_mapper import get_category_hierarchy

hierarchy = get_category_hierarchy('padel')
# ['venue', 'padel']  # Root to leaf
```

## Managing the Taxonomy

### Adding a New Canonical Category

1. **Edit `engine/config/canonical_categories.yaml`**

   ```yaml
   taxonomy:
     - category_key: new_sport
       display_name: New Sport
       parent: venue  # Optional
       description: Description of the new sport
       search_keywords:
         - new sport
         - keyword2
   ```

2. **Add Mapping Rules**

   ```yaml
   mapping_rules:
     - pattern: "(?i)\\bnew[_\\s-]sport\\b"
       canonical: new_sport
       confidence: 1.0
   ```

3. **Test the Mapping**

   ```python
   from engine.extraction.utils.category_mapper import reload_config, map_to_canonical

   reload_config()  # Force reload after config change
   result = map_to_canonical(["New Sport Club"])
   assert 'new_sport' in result
   ```

4. **Run Tests**

   ```bash
   pytest engine/tests/test_categories.py -v
   ```

### Adjusting Mapping Rules

To improve mapping accuracy:

1. Review unmapped categories in `logs/unmapped_categories.log`
2. Identify patterns in unmapped categories
3. Add or adjust mapping rules in the config
4. Test with real data
5. Monitor confidence scores

### Confidence Guidelines

| Confidence | Use Case | Example |
|------------|----------|---------|
| 1.0 | Exact, unambiguous match | "tennis" → tennis |
| 0.9-0.95 | Very strong match, minor ambiguity | "health club" → gym |
| 0.8-0.85 | Good match, some context needed | "leisure centre" → sports_centre |
| 0.7-0.75 | Acceptable match, notable ambiguity | "club" → club (could mean many things) |
| < 0.7 | Too ambiguous, excluded by default | - |

## Unmapped Categories

### Logging

Unmapped categories are automatically logged for manual review:

```
logs/unmapped_categories.log
```

Each line contains one unmapped category. Review this file periodically to:
- Identify new category types
- Spot extraction quality issues
- Find opportunities to expand the taxonomy

### Handling Unmapped Categories

**Option 1: Add to Taxonomy**

If the category represents a new entity type or sport:
1. Add to taxonomy in `canonical_categories.yaml`
2. Create mapping rules
3. Re-process affected listings

**Option 2: Create Mapping Rule**

If the category should map to an existing canonical category:
1. Add a mapping rule
2. Test the pattern
3. Re-process affected listings

**Option 3: Ignore**

Some categories are too specific or irrelevant:
- Brand names (e.g., "Nike Store")
- Temporary events (e.g., "Summer 2024 Program")
- Administrative tags (e.g., "Verified")

These can be safely ignored (they remain in raw categories but don't map to canonical).

## Integration with Extraction Pipeline

### Automatic Mapping

During extraction, integrate category mapping:

```python
from engine.extraction.utils.category_mapper import map_to_canonical

class MyExtractor(BaseExtractor):
    def extract(self, raw_data):
        # ... extraction logic ...

        # Extract raw categories
        raw_categories = self._extract_raw_categories(raw_data)

        return {
            'categories': raw_categories,  # Store raw
            # Canonical mapping happens separately in merge/dedup phase
        }
```

### Merge Phase Integration

Apply canonical mapping during the merge phase (after deduplication):

```python
from engine.extraction.utils.category_mapper import map_to_canonical

def merge_listings(listings):
    # ... merge logic ...

    # Collect all raw categories from all sources
    all_raw_categories = []
    for listing in listings:
        if listing.categories:
            all_raw_categories.extend(listing.categories)

    # Map to canonical
    canonical_categories = map_to_canonical(all_raw_categories)

    merged_listing.categories = list(set(all_raw_categories))  # Deduplicated raw
    merged_listing.canonical_categories = canonical_categories

    return merged_listing
```

## Manual Review Workflow (Future)

While not yet implemented, the planned manual review workflow includes:

1. **Admin Interface**
   - View unmapped categories with frequency counts
   - Preview suggested mappings
   - Approve or reject suggestions

2. **Bulk Operations**
   - Re-map all listings after taxonomy changes
   - Audit category quality metrics
   - Export/import taxonomy

3. **Quality Metrics**
   - % of listings with at least one canonical category
   - Average canonical categories per listing
   - Most common unmapped categories
   - Confidence score distribution

## Best Practices

### For Taxonomy Design

1. **Keep it shallow**: Aim for 2-3 levels maximum
2. **Be specific**: "tennis" is better than "racquet_sport"
3. **User-centric**: Use terms users search for
4. **Start narrow**: Add categories as needed, don't over-engineer
5. **Stable keys**: Never change `category_key`, only display names

### For Mapping Rules

1. **Word boundaries**: Use `\\b` to avoid partial matches
   - ✅ `\\btennis\\b` matches "tennis" but not "table tennis"
   - ❌ `tennis` matches both

2. **Case insensitive**: Always use `(?i)` flag
   - ✅ `(?i)\\bpadel\\b` matches "Padel", "PADEL", "padel"

3. **Multiple patterns**: Create specific rules for variants
   - Better to have 3 specific rules than 1 overly generic rule

4. **Test thoroughly**: Use real-world examples
   - Edinburgh Council: "Sports Centre", "Leisure Centre"
   - Google Places: "gym", "health_club"
   - OSM: "leisure=sports_centre"

### For Confidence Scores

1. **Conservative defaults**: Better to under-map than over-map
2. **High confidence** (≥0.9): Use when pattern is unambiguous
3. **Medium confidence** (0.7-0.85): Use for common but contextual terms
4. **Low confidence** (<0.7): Don't use, excluded by default

## Troubleshooting

### Categories not mapping

**Problem**: Raw categories aren't being mapped to canonical categories

**Solutions**:
1. Check that mapping rules exist for those patterns
2. Verify confidence threshold isn't too high
3. Test regex patterns with Python's `re` module:
   ```python
   import re
   pattern = r"(?i)\\btennis\\b"
   text = "Tennis Club"
   print(re.search(pattern, text))  # Should match
   ```
4. Check logs for error messages

### Too many/too few categories

**Problem**: Listings have unexpected number of canonical categories

**Solutions**:
1. Adjust `max_categories` in config
2. Review mapping rule specificity (too broad or too narrow)
3. Adjust confidence thresholds

### Performance issues

**Problem**: Category mapping is slow

**Solutions**:
1. Config is cached after first load (check cache is working)
2. Reduce number of mapping rules if possible
3. Use more specific patterns (faster regex matching)
4. Consider batch processing instead of per-listing

## Related Documentation

- `engine/config/canonical_categories.yaml` - Taxonomy and mapping configuration
- `engine/extraction/utils/category_mapper.py` - Implementation
- `engine/tests/test_categories.py` - Test suite
- `engine/schema/listing.py` - Database schema for categories

## Future Enhancements

1. **Machine Learning Mapping**: Train a model to suggest mappings for unmapped categories
2. **Admin UI**: Web interface for taxonomy management
3. **Analytics**: Category usage statistics and quality metrics
4. **Multi-language**: Support for non-English categories
5. **Confidence Auto-tuning**: Adjust confidence scores based on mapping accuracy
6. **Synonym Management**: Handle spelling variations and regional differences
