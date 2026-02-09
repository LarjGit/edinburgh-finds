# Lens Development Guide

## Overview

Lenses are vertical-specific configuration files that define how the universal Edinburgh Finds engine should interpret and display entities for specific domains (e.g., sports, wine, restaurants). This guide covers how to develop, test, and deploy new lenses.

## Architecture: Engine vs Lens Separation

The system maintains strict separation between universal engine concepts and vertical-specific lens concepts:

### Engine Layer (Universal)
- **Entity Classes**: `place`, `person`, `organization`, `event`, `thing`
- **Dimensions**: `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`
- **Universal Modules**: `core`, `location`, `contact`, `hours`, `amenities`, `time_range`

### Lens Layer (Vertical-Specific)
- **Facets**: How dimensions are displayed (`"Activities"`, `"Venue Type"`)
- **Values**: Canonical vocabulary (`"padel"`, `"tennis"`, `"sports_facility"`)
- **Mapping Rules**: Raw data → canonical values
- **Domain Modules**: Vertical-specific data structures (`sports_facility`, `wine_production`)

## Lens Structure

### Required Schema Format

Every lens must include these top-level sections:

```yaml
# Schema version (required)
schema: lens/v1

# Facets define how dimensions are interpreted and displayed
facets:
  activity:
    dimension_source: canonical_activities  # Must be valid engine dimension
    ui_label: "Activities"
    display_mode: tags
    order: 1
    show_in_filters: true
    show_in_navigation: true
    icon: "activity"

# Canonical values registry
values:
  - key: padel
    facet: activity  # Must reference existing facet
    display_name: "Padel"
    description: "Racquet sport combining elements of tennis and squash"
    seo_slug: "padel"
    search_keywords: ["padel", "racket sport", "racquet sport"]
    icon_url: "/icons/padel.svg"
    color: "#10B981"

# Mapping rules (raw data → canonical values)
mapping_rules:
  - id: map_padel_from_name
    pattern: "(?i)padel"  # Regex pattern
    canonical: "padel"    # Must reference existing value key
    confidence: 0.95

# Module triggers (when to attach domain modules)
module_triggers:
  - when:
      facet: activity
      value: padel
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

# Module definitions
modules:
  sports_facility:
    description: "Sports facility with courts, pitches, or equipment"
    field_rules:
      - rule_id: extract_padel_court_count
        target_path: padel_courts.total
        extractor: regex_capture
        pattern: "(?i)(\\d+)\\s+(?:fully\\s+)?(?:covered(?:,\\s*|\\s+and\\s+)?)?(?:heated\\s+)?courts?"
        source_fields: [summary, description, entity_name]
        confidence: 0.85
        applicability:
          source: [serper, google_places, sport_scotland]
          entity_class: [place]
        normalizers: [round_integer]
```

## Development Workflow

### 1. Create Lens Configuration

Create your lens file following the required structure:

```bash
mkdir -p engine/lenses/your_vertical
touch engine/lenses/your_vertical/lens.yaml
```

### 2. Define Facets

Facets map engine dimensions to user-facing concepts:

```yaml
facets:
  activity:
    dimension_source: canonical_activities  # Engine dimension
    ui_label: "Activities"
    display_mode: tags
    order: 1
    show_in_filters: true
    show_in_navigation: true
    icon: "activity"

  place_type:
    dimension_source: canonical_place_types
    ui_label: "Venue Type"
    display_mode: badge
    order: 2
    show_in_filters: true
    show_in_navigation: false
    icon: "building"
```

**Valid dimension_source values:**
- `canonical_activities`
- `canonical_roles`
- `canonical_place_types`
- `canonical_access`

### 3. Define Canonical Values

Create controlled vocabulary for each facet:

```yaml
values:
  - key: padel
    facet: activity
    display_name: "Padel"
    description: "Racquet sport combining elements of tennis and squash"
    seo_slug: "padel"
    search_keywords: ["padel", "racket sport", "racquet sport"]
    icon_url: "/icons/padel.svg"
    color: "#10B981"

  - key: sports_facility
    facet: place_type
    display_name: "Sports Facility"
    description: "Venue providing sports courts, pitches, or equipment"
    seo_slug: "sports-facility"
    search_keywords: ["sports centre", "sports facility", "leisure centre"]
    icon_url: "/icons/facility.svg"
    color: "#3B82F6"
```

### 4. Create Mapping Rules

Define regex patterns that map raw data to canonical values:

```yaml
mapping_rules:
  - id: map_padel_from_name
    pattern: "(?i)padel"
    canonical: "padel"
    confidence: 0.95

  - id: map_sports_facility_type
    pattern: "(?i)(sports\\s*(centre|center|facility|club)|leisure\\s*(centre|center)|padel\\s*(club|centre|center)|padel\\s*courts?)"
    canonical: "sports_facility"
    confidence: 0.85
```

**Mapping Rule Execution:**
- Rules search across `source_fields` (defaults to `["entity_name", "description", "raw_categories", "summary", "street_address"]`)
- First match wins per rule
- Multiple rules can contribute to same dimension
- Results are deduplicated and sorted for determinism

### 5. Add Module Triggers

Define when to attach domain modules:

```yaml
module_triggers:
  - when:
      facet: activity
      value: padel
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

  - when:
      facet: activity
      value: tennis
    add_modules: [sports_facility]
    conditions:
      - entity_class: place
```

### 6. Define Domain Modules

Create vertical-specific data extraction:

```yaml
modules:
  sports_facility:
    description: "Sports facility with courts, pitches, or equipment"
    field_rules:
      - rule_id: extract_padel_court_count
        target_path: padel_courts.total
        extractor: regex_capture
        pattern: "(?i)(\\d+)\\s*(?:fully\\s+)?(?:covered(?:,\\s*|\\s+and\\s+)?)?(?:heated\\s+)?courts?"
        source_fields: [summary, description, entity_name]
        confidence: 0.85
        applicability:
          source: [serper, google_places, sport_scotland]
          entity_class: [place]
        normalizers: [round_integer]
```

**Available Extractors:**
- `regex_capture`: Extract text using regex pattern
- `numeric_parser`: Extract numbers from text

**Available Normalizers:**
- `trim`: Remove whitespace
- `round_integer`: Round to nearest integer
- `lowercase`: Convert to lowercase

## Validation

Your lens must pass all 7 validation gates:

### Gate 1: Schema Validation
Required sections: `schema`, `facets`, `values`, `mapping_rules`

### Gate 2: Canonical Reference Integrity
- `facets.dimension_source` must be valid engine dimension
- `values.facet` must reference existing facet
- `mapping_rules.canonical` must reference existing value
- `module_triggers` references must be valid

### Gate 3: Connector Reference Validation
Connector names must exist in registry

### Gate 4: Identifier Uniqueness
No duplicate `value.key` across all values

### Gate 5: Regex Compilation Validation
All `mapping_rules.pattern` must be valid regex

### Gate 6: Smoke Coverage Validation
Every facet must have at least one value

### Gate 7: Fail-Fast Enforcement
Errors abort immediately at load time

## Testing Your Lens

### 1. Validation

```python
from engine.lenses.validator import validate_lens_config
import yaml

with open('your_lens.yaml') as f:
    config = yaml.safe_load(f)

validate_lens_config(config)  # Raises ValidationError if invalid
```

### 2. Test Mapping Rules

```python
from tests.engine.extraction.test_helpers import extract_with_lens_for_testing

def test_padel_mapping():
    lens_contract = {
        "facets": {"activity": {"dimension_source": "canonical_activities"}},
        "values": [{"key": "padel", "facet": "activity", "display_name": "Padel"}],
        "mapping_rules": [{"pattern": r"(?i)\bpadel\b", "canonical": "padel", "confidence": 1.0}],
        "modules": {},
        "module_triggers": []
    }
    
    raw_data = {"entity_name": "Padel Club", "categories": ["Sports"]}
    result = extract_with_lens_for_testing(raw_data, lens_contract)
    
    assert "padel" in result["canonical_activities"]
```

### 3. Integration Testing

```bash
python scripts/test_orchestration_live.py --persist false --verbose
```

## Production Pipeline

### Phase 1: Primitive Extraction
Source extractors return only schema-defined primitives:
- `entity_name`, `latitude`, `longitude`, `phone`, etc.
- NO canonical dimensions or modules

### Phase 2: Lens Application
Lens contract adds vertical-specific interpretation:
- Mapping rules populate `canonical_activities`, `canonical_roles`, etc.
- Module triggers determine which domain modules to apply
- Module field rules extract additional structured data

```python
# Production path (from extraction_integration.py)
# Phase 1: Extract primitives
extracted = extractor.extract(raw_data, ctx=context)
validated = extractor.validate(extracted)
phase1_attributes, discovered_attributes = extractor.split_attributes(validated)

# Phase 2: Apply lens contract
if context and context.lens_contract:
    enriched = apply_lens_contract(
        extracted_primitives=validated,
        lens_contract=dict(context.lens_contract),
        source=source,
        entity_class=entity_class
    )
```

## Best Practices

### Facet Design
1. **Use engine dimensions**: Only `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`
2. **Clear UI labels**: Make facets immediately understandable to users
3. **Logical ordering**: Use `order` field to prioritise important facets

### Value Definition
1. **Unique keys**: Each `value.key` must be unique across entire lens
2. **Rich metadata**: Include `description`, `search_keywords`, `icon_url`, `color`
3. **SEO-friendly slugs**: Use `seo_slug` for URL generation

### Mapping Rules
1. **Robust regex**: Use `(?i)` for case-insensitive matching
2. **Word boundaries**: Use `\b` to avoid partial matches
3. **Confidence scores**: Set appropriate confidence levels (0.0-1.0)
4. **Test with real data**: Verify patterns work with actual source data

### Module Development
1. **Source-aware rules**: Use `applicability.source` to filter by data source
2. **Entity-class filtering**: Use `applicability.entity_class` for relevant entities
3. **Nested target paths**: Use dot notation for structured data (`courts.total`)
4. **Normalisation**: Apply normalizers to clean extracted values

## Troubleshooting

### Common Issues

**ValidationError: Missing required section**
```
Missing required section: facets
```
Ensure your lens has all required top-level sections.

**ValidationError: Invalid dimension_source**
```
Facet 'activity' has invalid dimension_source 'custom_activities'
```
Use only valid engine dimensions: `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`.

**Mapping rules not triggering**
- Check regex syntax with online regex tester
- Verify `canonical` value exists in `values` section
- Check confidence threshold (default 0.7)

**Module fields not extracted**
- Verify `applicability.source` matches your data source
- Check `source_fields` contain the fields you're extracting from
- Test regex patterns with sample data

### Debug Tools

```python
# Test lens loading
from engine.lenses.loader import VerticalLens
lens = VerticalLens(Path("your_lens.yaml"))

# Test mapping rules
from engine.lenses.mapping_engine import execute_mapping_rules
rules = [{"pattern": r"(?i)padel", "canonical": "padel", "dimension": "canonical_activities"}]
entity = {"entity_name": "Padel Club"}
result = execute_mapping_rules(rules, entity)

# Test module extraction
from engine.extraction.module_extractor import execute_field_rules
rules = [{"target_path": "courts.total", "extractor": "regex_capture", "pattern": r"(\d+)\s*courts"}]
entity = {"description": "5 courts available"}
result = execute_field_rules(rules, entity, "test_source")
```

## Resources

- **Validation Schema**: `engine/lenses/validator.py`
- **Mapping Engine**: `engine/lenses/mapping_engine.py`
- **Lens Loader**: `engine/lenses/loader.py`
- **Test Helpers**: `tests/engine/extraction/test_helpers.py`
- **Entity Model**: `engine/config/entity_model.yaml`
