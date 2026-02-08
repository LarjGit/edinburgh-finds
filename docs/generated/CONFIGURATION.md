# Configuration Reference

**Universal Entity Extraction Engine**
**Generated:** 2026-02-08
**Audience:** Developers, AI agents, system operators

---

## Table of Contents

1. [Overview](#overview)
2. [Schema Configuration](#schema-configuration)
3. [Lens Configuration](#lens-configuration)
4. [Connector Registry](#connector-registry)
5. [Environment Variables](#environment-variables)
6. [Validation Rules](#validation-rules)
7. [Module Schemas](#module-schemas)
8. [Canonical Value Registry](#canonical-value-registry)
9. [Configuration Best Practices](#configuration-best-practices)
10. [Troubleshooting](#troubleshooting)

---

## 1. Overview

The Universal Entity Extraction Engine is **configuration-driven** and **vertical-agnostic**. All domain knowledge and behavior is defined through YAML configuration files, not code.

### Configuration Philosophy

**Engine Purity Principle**: The engine contains zero domain knowledge. Adding a new vertical (e.g., Wine Discovery, Restaurant Finder) requires **ONLY** creating new configuration files—no code changes.

### Configuration Hierarchy

```
Configuration Layers:
├── YAML Schemas (engine/config/schemas/*.yaml)
│   └── Define universal data model structure
├── Lens Contracts (engine/lenses/<lens_id>/lens.yaml)
│   └── Define domain-specific interpretation
├── Connector Registry (engine/orchestration/registry.py)
│   └── Define connector metadata (cost, trust, phase, timeout)
└── Environment Variables (.env)
    └── Define runtime secrets and connection strings
```

### Single Source of Truth

YAML schemas auto-generate derived artifacts:

```
entity.yaml (source of truth)
    ↓
    ├→ engine/schema/entity.py (Python FieldSpecs)
    ├→ engine/prisma/schema.prisma (Prisma schema)
    ├→ web/prisma/schema.prisma (Prisma schema)
    └→ web/lib/types/generated/entity.ts (TypeScript types)
```

**NEVER edit generated files**—they contain "DO NOT EDIT" headers and are overwritten during regeneration.

### Configuration Workflow

```
1. Edit YAML config (schema or lens)
2. Validate: python -m engine.schema.generate --validate
3. Regenerate: python -m engine.schema.generate --all
4. Test: pytest (backend), npm run build (frontend)
5. Commit changes
```

---

## 2. Schema Configuration

Schema configuration defines the universal data model structure. Schemas are **vertical-agnostic** and contain no domain-specific terminology.

### Location

```
engine/config/schemas/
└── entity.yaml         # Universal entity schema (single source of truth)
```

### Schema Structure

```yaml
# ============================================================
# ENTITY SCHEMA - Common fields for all entity types
# ============================================================

schema:
  name: Entity
  description: Base schema for all entity types
  extends: null  # Can extend other schemas

fields:
  - name: entity_name
    type: string
    description: Official name of the entity
    nullable: false
    required: true
    index: true
    search:
      category: identity
      keywords: [name, called, named]
    python:
      validators: [non_empty]
      extraction_required: true

  - name: entity_class
    type: string
    description: "Universal entity classification (place, person, organization, event, thing)"
    nullable: true
    exclude: true  # Populated by engine, not LLM extraction
    index: true
    notes:
      - "Valid values: place, person, organization, event, thing"
      - "Determined by entity_classifier.py using deterministic rules"
```

### Field Definition Reference

Each field definition supports the following attributes:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `name` | string | Field name (snake_case) | `entity_name` |
| `type` | string | Data type (see types below) | `string`, `list[string]`, `json` |
| `description` | string | Human-readable description | `"Official name of the entity"` |
| `nullable` | boolean | Allow NULL values | `false` |
| `required` | boolean | Required for LLM extraction | `true` |
| `index` | boolean | Create database index | `true` |
| `unique` | boolean | Enforce uniqueness constraint | `true` |
| `default` | string | Default value expression | `cuid()`, `null`, `dict` |
| `exclude` | boolean | Exclude from LLM extraction | `true` |
| `primary_key` | boolean | Mark as primary key | `true` |
| `search` | object | Search metadata (see below) | - |
| `python` | object | Python-specific config (see below) | - |
| `prisma` | object | Prisma-specific config (see below) | - |
| `notes` | list[string] | Documentation notes | - |

### Supported Data Types

| YAML Type | Python Type | Prisma Type | Description |
|-----------|-------------|-------------|-------------|
| `string` | `str` | `String` | Text field |
| `integer` | `int` | `Int` | Whole number |
| `float` | `float` | `Float` | Decimal number |
| `boolean` | `bool` | `Boolean` | True/false |
| `datetime` | `datetime` | `DateTime` | Timestamp |
| `json` | `Dict[str, Any]` | `Json` | Flexible JSON object |
| `list[string]` | `List[str]` | `String[]` | Array of strings |
| `list[integer]` | `List[int]` | `Int[]` | Array of integers |
| `list[float]` | `List[float]` | `Float[]` | Array of floats |
| `list[boolean]` | `List[bool]` | `Boolean[]` | Array of booleans |

### Search Metadata

```yaml
search:
  category: identity     # Search category (identity, location, contact, etc.)
  keywords:              # Keywords for semantic search
    - name
    - called
    - named
```

### Python-Specific Configuration

```yaml
python:
  validators:                  # Validation functions
    - non_empty
    - postcode_uk
    - e164_phone
    - url_http
  extraction_required: true    # Must be extracted by LLM
  extraction_name: website     # Alias name for LLM extraction
  default: "default_factory=list"  # Default value factory
  sa_column: "Column(ARRAY(String))"  # SQLAlchemy column definition
  type_annotation: "Dict[str, Any]"   # Python type hint
```

### Prisma-Specific Configuration

```yaml
prisma:
  name: id                     # Different name in Prisma schema
  type: "String[]"             # Override Prisma type
  attributes:                  # Prisma attributes
    - "@id"
    - "@default(cuid())"
    - "@updatedAt"
```

### Complete Entity Schema Example

Here's a complete field definition showing all features:

```yaml
fields:
  # ------------------------------------------------------------------
  # IDENTIFICATION
  # ------------------------------------------------------------------
  - name: entity_id
    type: string
    description: Unique identifier (auto-generated)
    nullable: false
    required: false
    primary_key: true
    exclude: true
    default: cuid()
    prisma:
      name: id
      attributes:
        - "@id"
        - "@default(cuid())"

  - name: entity_name
    type: string
    description: Official name of the entity
    nullable: false
    required: true
    index: true
    search:
      category: identity
      keywords: [name, called, named]
    python:
      validators: [non_empty]
      extraction_required: true

  - name: entity_class
    type: string
    description: "Universal entity classification (place, person, organization, event, thing)"
    nullable: true
    exclude: true
    index: true
    notes:
      - "Valid values: place, person, organization, event, thing"
      - "Determined by entity_classifier.py using deterministic rules"

  - name: slug
    type: string
    description: URL-safe version of entity name (auto-generated)
    nullable: false
    required: false
    unique: true
    index: true
    exclude: true
    default: null

  # ------------------------------------------------------------------
  # CLASSIFICATION
  # ------------------------------------------------------------------
  - name: raw_categories
    type: list[string]
    description: Raw free-form categories detected by the LLM
    nullable: true
    exclude: true
    python:
      sa_column: "Column(ARRAY(String))"
      default: "default_factory=list"
    prisma:
      type: "String[]"
      attributes:
        - "@default([])"
    notes:
      - "Uncontrolled observational labels - NOT indexed, NOT used for filtering"
      - "Used by lenses for mapping rules only"

  # ------------------------------------------------------------------
  # MULTI-VALUED DIMENSIONS (Engine-Lens Architecture)
  # ------------------------------------------------------------------
  - name: canonical_activities
    type: list[string]
    description: "Activities provided/supported (opaque values, lens-interpreted)"
    nullable: true
    exclude: true
    python:
      sa_column: "Column(ARRAY(String))"
      default: "default_factory=list"
    prisma:
      type: "String[]"
      attributes:
        - "@default([])"
    notes:
      - "Postgres text[] array with GIN index for faceted filtering"
      - "Opaque to engine - lens provides interpretation"

  - name: canonical_roles
    type: list[string]
    description: "Roles this entity plays (opaque values, universal function-style keys)"
    nullable: true
    exclude: true
    python:
      sa_column: "Column(ARRAY(String))"
      default: "default_factory=list"
    prisma:
      type: "String[]"
      attributes:
        - "@default([])"
    notes:
      - "Universal function-style keys: provides_facility, sells_goods, provides_instruction"

  - name: canonical_place_types
    type: list[string]
    description: "Physical place classifications (opaque values, lens-interpreted)"
    nullable: true
    exclude: true
    python:
      sa_column: "Column(ARRAY(String))"
      default: "default_factory=list"
    prisma:
      type: "String[]"
      attributes:
        - "@default([])"
    notes:
      - "Applicable to place entity_class only"

  - name: canonical_access
    type: list[string]
    description: "Access requirements (opaque values, lens-interpreted)"
    nullable: true
    exclude: true
    python:
      sa_column: "Column(ARRAY(String))"
      default: "default_factory=list"
    prisma:
      type: "String[]"
      attributes:
        - "@default([])"
    notes:
      - "Examples: membership, pay_and_play, free, private_club"

  # ------------------------------------------------------------------
  # FLEXIBLE ATTRIBUTE BUCKETS
  # ------------------------------------------------------------------
  - name: discovered_attributes
    type: json
    description: Extra attributes not explicitly defined in schema
    nullable: true
    python:
      sa_column: "Column(JSON)"

  - name: modules
    type: json
    description: "Namespaced module data (JSONB) organized by module key"
    nullable: true
    exclude: true
    python:
      sa_column: "Column(JSON)"
    prisma:
      type: "Json"
    notes:
      - "Namespaced JSONB structure: {module_key: {fields}}"
      - "Example: {sports_facility: {padel_courts: {total: 4}}}"

  # ------------------------------------------------------------------
  # LOCATION
  # ------------------------------------------------------------------
  - name: street_address
    type: string
    description: Full street address including building number, street name, city and postcode
    nullable: true
    search:
      category: location
      keywords: [address, location, street]

  - name: city
    type: string
    description: City or town
    nullable: true
    index: true
    search:
      category: location
      keywords: [city, town]

  - name: postcode
    type: string
    description: Full UK postcode with correct spacing (e.g., 'SW1A 0AA')
    nullable: true
    index: true
    search:
      category: location
      keywords: [postcode, postal code, zip]
    python:
      validators: [postcode_uk]

  - name: country
    type: string
    description: Country name
    nullable: true
    search:
      category: location
      keywords: [country]

  - name: latitude
    type: float
    description: WGS84 Latitude coordinate (decimal degrees)
    nullable: true

  - name: longitude
    type: float
    description: WGS84 Longitude coordinate (decimal degrees)
    nullable: true

  # ------------------------------------------------------------------
  # CONTACT
  # ------------------------------------------------------------------
  - name: phone
    type: string
    description: Primary contact phone number with country code (E.164 UK format)
    nullable: true
    search:
      category: contact
      keywords: [phone, telephone, contact]
    python:
      validators: [e164_phone]

  - name: email
    type: string
    description: Primary public email address
    nullable: true
    search:
      category: contact
      keywords: [email, contact]

  - name: website_url
    type: string
    description: Official website URL
    nullable: true
    search:
      category: contact
      keywords: [website, url, site]
    python:
      validators: [url_http]
      extraction_name: website

  # ------------------------------------------------------------------
  # OPENING HOURS
  # ------------------------------------------------------------------
  - name: opening_hours
    type: json
    description: "Opening hours per day (strings or nested open/close times)"
    nullable: true
    python:
      sa_column: "Column(JSON)"
    search:
      category: hours
      keywords: [hours, opening, times]

  # ------------------------------------------------------------------
  # METADATA (excluded from extraction)
  # ------------------------------------------------------------------
  - name: source_info
    type: json
    description: "Provenance metadata: URLs, method, timestamps, notes"
    nullable: true
    default: dict
    exclude: true
    python:
      default: "default_factory=dict"
      sa_column: "Column(JSON)"
      type_annotation: "Dict[str, Any]"

  - name: field_confidence
    type: json
    description: Per-field confidence scores used for merge decisions
    nullable: true
    default: dict
    exclude: true
    python:
      default: "default_factory=dict"
      sa_column: "Column(JSON)"
      type_annotation: "Dict[str, float]"

  - name: created_at
    type: datetime
    description: Creation timestamp
    nullable: true
    exclude: true
    python:
      sa_column: "Column(DateTime(timezone=True), nullable=False, server_default=func.now())"
    prisma:
      name: createdAt
      type: "DateTime"
      attributes:
        - "@default(now())"

  - name: updated_at
    type: datetime
    description: Last update timestamp
    nullable: true
    exclude: true
    python:
      sa_column: "Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())"
    prisma:
      name: updatedAt
      type: "DateTime"
      attributes:
        - "@updatedAt"

  - name: external_ids
    type: json
    description: "External system IDs (e.g., {'google': 'ChIJ...', 'osm': 12345})"
    nullable: true
    exclude: true
    python:
      sa_column: "Column(JSON)"

# ------------------------------------------------------------------
# EXTRACTION-ONLY FIELDS (LLM)
# ------------------------------------------------------------------
# These fields are extracted but not stored in final Entity table
extraction_fields:
  - name: rating
    type: float
    description: Average rating (typically 0-5 scale)
    nullable: true

  - name: user_rating_count
    type: integer
    description: Number of user ratings/reviews
    nullable: true

  - name: currently_open
    type: boolean
    description: Whether the entity is currently open
    nullable: true

  - name: external_id
    type: string
    description: External identifier from source system (e.g., Google Place ID, OSM ID)
    nullable: true
```

### Schema Validation

Validate schema structure before committing:

```bash
# Validate all schemas
python -m engine.schema.generate --validate

# Regenerate derived artifacts
python -m engine.schema.generate --all
```

Validation checks:

- Field names are valid identifiers (snake_case)
- Types are supported
- Required fields are not nullable
- Index/unique constraints are valid
- Python/Prisma overrides are syntactically correct

---

## 3. Lens Configuration

Lens configuration defines **all domain-specific interpretation**. Lenses are the ONLY place where vertical logic exists.

### Location

```
engine/lenses/
├── edinburgh_finds/
│   └── lens.yaml       # Sports discovery lens (reference implementation)
└── wine/
    └── lens.yaml       # Wine discovery lens (example)
```

### Lens Philosophy

**Lenses own all semantics**. The engine treats lens configurations as opaque contracts and never interprets their meaning.

### Lens YAML Structure

A complete lens configuration includes 8 sections:

```yaml
# Schema version (required)
schema: lens/v1

# 1. Query vocabulary for orchestration
vocabulary:
  activity_keywords: [...]
  location_indicators: [...]
  facility_keywords: [...]

# 2. Connector selection rules
connector_rules:
  <connector_name>:
    priority: high|medium|low
    triggers: [...]

# 3. Facet definitions (how dimensions are interpreted)
facets:
  <facet_key>:
    dimension_source: canonical_activities
    ui_label: "Activities"
    display_mode: tags
    order: 1
    show_in_filters: true
    show_in_navigation: true
    icon: "activity"

# 4. Canonical values registry
values:
  - key: padel
    facet: activity
    display_name: "Padel"
    description: "..."
    seo_slug: "padel"
    search_keywords: [...]
    icon_url: "/icons/padel.svg"
    color: "#10B981"

# 5. Mapping rules (raw data → canonical values)
mapping_rules:
  - id: map_padel_from_name
    pattern: "(?i)padel"
    canonical: "padel"
    confidence: 0.95

# 6. Module triggers (when to attach structured modules)
module_triggers:
  - when:
      facet: activity
      value: padel
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

# 7. Module definitions (domain-specific structured data)
modules:
  sports_facility:
    description: "..."
    field_rules: [...]

# 8. Confidence threshold
confidence_threshold: 0.7
```

### Section 1: Vocabulary

Defines domain-specific keywords for query feature extraction and connector routing.

```yaml
vocabulary:
  # Activity-related keywords
  activity_keywords:
    - padel
    - tennis
    - squash
    - badminton
    - pickleball
    - racquet sport
    - racket sport

  # Location indicator words
  location_indicators:
    - edinburgh
    - leith
    - portobello
    - stockbridge
    - in
    - near
    - around

  # Facility type keywords
  facility_keywords:
    - sports centre
    - sports center
    - leisure centre
    - leisure center
    - sports facility
    - club
    - courts
    - venue

  # Role keywords (optional)
  role_keywords:
    - coach
    - instructor
    - trainer
    - retailer
    - supplier
```

**Usage**: Query features are extracted using these keywords to inform connector selection and orchestration behavior.

### Section 2: Connector Rules

Defines when and how to use each connector based on query features.

```yaml
connector_rules:
  # High-priority connector for sports queries
  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [
          padel, tennis, squash, badminton, pickleball,
          football, rugby, swimming,
          sports, facilities, pools, clubs
        ]

  # Medium-priority connector for location-based searches
  google_places:
    priority: medium
    triggers:
      - type: location_present
      - type: facility_search

  # Always-on fallback connector
  serper:
    priority: medium
    triggers:
      - type: always

  # Conditional connector (only when location + activity match)
  openstreetmap:
    priority: low
    triggers:
      - type: all_conditions_met
        conditions:
          - location_present: true
          - has_activity_keyword: true
```

**Trigger Types**:

| Trigger Type | Description | Example |
|--------------|-------------|---------|
| `always` | Always execute | Serper (fallback) |
| `any_keyword_match` | Query contains any keyword | Sport Scotland |
| `location_present` | Location detected in query | Google Places |
| `facility_search` | Facility keyword detected | Google Places |
| `all_conditions_met` | All conditions satisfied | OSM |

**Priority Levels**:

- `high`: Execute first, highest cost budget
- `medium`: Execute after high-priority connectors
- `low`: Execute only if needed, lowest cost budget

### Section 3: Facets

Facets define how canonical dimensions are interpreted and displayed in the UI.

```yaml
facets:
  # Activity facet (maps to canonical_activities dimension)
  activity:
    dimension_source: canonical_activities
    ui_label: "Activities"
    display_mode: tags
    order: 1
    show_in_filters: true
    show_in_navigation: true
    icon: "activity"

  # Place type facet (maps to canonical_place_types dimension)
  place_type:
    dimension_source: canonical_place_types
    ui_label: "Venue Type"
    display_mode: badge
    order: 2
    show_in_filters: true
    show_in_navigation: false
    icon: "building"

  # Role facet (maps to canonical_roles dimension)
  role:
    dimension_source: canonical_roles
    ui_label: "Services"
    display_mode: list
    order: 3
    show_in_filters: false
    show_in_navigation: false
    icon: "briefcase"

  # Access facet (maps to canonical_access dimension)
  access:
    dimension_source: canonical_access
    ui_label: "Access Type"
    display_mode: tags
    order: 4
    show_in_filters: true
    show_in_navigation: false
    icon: "key"
```

**Facet Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `dimension_source` | string | Yes | Must be one of: `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access` |
| `ui_label` | string | Yes | Display label in UI |
| `display_mode` | string | Yes | Display mode: `tags`, `badge`, `list`, `pills` |
| `order` | integer | Yes | Sort order in UI (lower = first) |
| `show_in_filters` | boolean | Yes | Show in filter sidebar |
| `show_in_navigation` | boolean | Yes | Show in top-level navigation |
| `icon` | string | Yes | Icon identifier |

### Section 4: Canonical Values

Defines all valid canonical values and their display metadata.

```yaml
values:
  # Activity: Padel
  - key: padel
    facet: activity
    display_name: "Padel"
    description: "Racquet sport combining elements of tennis and squash"
    seo_slug: "padel"
    search_keywords: ["padel", "racket sport", "racquet sport"]
    icon_url: "/icons/padel.svg"
    color: "#10B981"

  # Activity: Tennis
  - key: tennis
    facet: activity
    display_name: "Tennis"
    description: "Classic racquet sport played on rectangular court"
    seo_slug: "tennis"
    search_keywords: ["tennis", "lawn tennis", "racquet"]
    icon_url: "/icons/tennis.svg"
    color: "#3B82F6"

  # Place Type: Sports Facility
  - key: sports_facility
    facet: place_type
    display_name: "Sports Facility"
    description: "Venue providing sports courts, pitches, or equipment"
    seo_slug: "sports-facility"
    search_keywords: ["sports centre", "sports facility", "leisure centre"]
    icon_url: "/icons/facility.svg"
    color: "#8B5CF6"

  # Role: Facility Provider
  - key: provides_facility
    facet: role
    display_name: "Facility Provider"
    description: "Provides physical venue for activities"
    seo_slug: "facility-provider"
    search_keywords: ["venue", "facility", "centre"]
    icon_url: "/icons/building.svg"
    color: "#6B7280"

  # Access: Pay and Play
  - key: pay_and_play
    facet: access
    display_name: "Pay and Play"
    description: "Open to public, pay per session"
    seo_slug: "pay-and-play"
    search_keywords: ["pay and play", "public", "walk-in"]
    icon_url: "/icons/cash.svg"
    color: "#10B981"
```

**Value Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `key` | string | Yes | Unique identifier (stored in database) |
| `facet` | string | Yes | Facet key this value belongs to |
| `display_name` | string | Yes | Human-readable label |
| `description` | string | Yes | Detailed explanation |
| `seo_slug` | string | Yes | URL-safe slug for SEO |
| `search_keywords` | list[string] | Yes | Search/matching keywords |
| `icon_url` | string | Yes | Icon path or URL |
| `color` | string | Yes | Hex color code for UI theming |

### Section 5: Mapping Rules

Defines how raw data is transformed into canonical values.

```yaml
mapping_rules:
  # Map "padel" from entity name
  - id: map_padel_from_name
    pattern: "(?i)padel"
    canonical: "padel"
    confidence: 0.95
    source_fields: [entity_name, summary, description]

  # Map sports facility from place type indicators
  - id: map_sports_facility_type
    pattern: "(?i)(sports\\s*(centre|center|facility|club)|leisure\\s*(centre|center)|padel\\s*(club|centre|center)|padel\\s*courts?)"
    canonical: "sports_facility"
    confidence: 0.85
    source_fields: [entity_name, street_address, raw_categories]

  # Map tennis from description
  - id: map_tennis_from_description
    pattern: "(?i)tennis\\s*(court|club|centre|center|facility)"
    canonical: "tennis"
    confidence: 0.90
    source_fields: [entity_name, description]

  # Map pay-and-play access from description
  - id: map_pay_and_play_access
    pattern: "(?i)(pay\\s*and\\s*play|public\\s*(access|booking)|walk-?in|drop-?in)"
    canonical: "pay_and_play"
    confidence: 0.75
    source_fields: [description, discovered_attributes]
```

**Mapping Rule Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Unique rule identifier |
| `pattern` | string | Yes | Regex pattern to match |
| `canonical` | string | Yes | Canonical value key (must exist in `values`) |
| `confidence` | float | Yes | Confidence score (0.0-1.0) |
| `source_fields` | list[string] | No | Fields to search (default: entity_name, summary, description, raw_categories, street_address) |

**Default Evidence Surfaces**: If `source_fields` is omitted, the engine searches: `entity_name`, `summary`, `description`, `raw_categories`, `street_address`.

**Pattern Best Practices**:

- Use `(?i)` for case-insensitive matching
- Escape special regex characters: `\.`, `\(`, `\)`
- Use word boundaries `\b` for exact word matches
- Use non-capturing groups `(?:...)` for performance

### Section 6: Module Triggers

Defines when to attach domain-specific structured modules.

```yaml
module_triggers:
  # Attach sports_facility module to places with padel activity
  - when:
      facet: activity
      value: padel
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

  # Attach sports_facility module to places with tennis activity
  - when:
      facet: activity
      value: tennis
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

  # Attach coaching module to entities with instructor role
  - when:
      facet: role
      value: provides_instruction
    add_modules: [coaching]
    conditions:
      - entity_class: [person, organization]

  # Attach retail module to entities with retail role and place class
  - when:
      facet: role
      value: sells_goods
    add_modules: [retail, product_catalog]
    conditions:
      - entity_class: place
      - facet: place_type
        value: retail_store
```

**Module Trigger Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `when` | object | Yes | Trigger condition (facet + value) |
| `add_modules` | list[string] | Yes | Modules to attach (must exist in `modules`) |
| `conditions` | list[object] | No | Additional constraints (entity_class, facet/value) |

### Section 7: Module Definitions

Defines domain-specific structured data schemas and extraction rules.

```yaml
modules:
  # Sports facility module
  sports_facility:
    description: "Sports facility with courts, pitches, or equipment"
    field_rules:
      # Extract padel court count
      - rule_id: extract_padel_court_count
        target_path: padel_courts.total
        extractor: regex_capture
        pattern: "(?i)(\\d+)\\s+(?:fully\\s+)?(?:covered(?:,\\s*|\\s+and\\s+)?)?(?:heated\\s+)?padel\\s*courts?"
        source_fields: [summary, description, entity_name]
        confidence: 0.85
        applicability:
          source: [serper, google_places, sport_scotland]
          entity_class: [place]
        normalizers: [round_integer]

      # Extract tennis court count
      - rule_id: extract_tennis_court_count
        target_path: tennis_courts.total
        extractor: regex_capture
        pattern: "(?i)(\\d+)\\s*tennis\\s*courts?"
        source_fields: [description, entity_name]
        confidence: 0.85
        applicability:
          source: [serper, google_places, sport_scotland]
          entity_class: [place]
        normalizers: [round_integer]

      # Extract indoor/outdoor designation
      - rule_id: extract_court_indoor_outdoor
        target_path: facility_type
        extractor: regex_capture
        pattern: "(?i)(indoor|outdoor|covered)"
        source_fields: [description, summary]
        confidence: 0.80
        normalizers: [lowercase]

  # Coaching module
  coaching:
    description: "Coaching services and instructor details"
    field_rules:
      - rule_id: extract_coaching_specialization
        target_path: specialization
        extractor: regex_capture
        pattern: "(?i)(beginner|intermediate|advanced|professional|youth|kids|children)\\s*(?:coaching|lessons|instruction)"
        source_fields: [description, summary]
        confidence: 0.75
        normalizers: [lowercase]
```

**Module Definition Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Module purpose |
| `field_rules` | list[object] | Yes | Extraction rules for module fields |

**Field Rule Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `rule_id` | string | Yes | Unique rule identifier |
| `target_path` | string | Yes | Dot-notation path in module (e.g., `padel_courts.total`) |
| `extractor` | string | Yes | Extraction method: `regex_capture`, `llm_extraction`, `deterministic_lookup` |
| `pattern` | string | Yes (regex) | Regex pattern with capture group |
| `source_fields` | list[string] | Yes | Fields to extract from |
| `confidence` | float | Yes | Confidence score (0.0-1.0) |
| `applicability` | object | No | Constraints (source, entity_class) |
| `normalizers` | list[string] | No | Post-processing functions: `lowercase`, `round_integer`, `trim`, `uppercase` |

### Section 8: Confidence Threshold

Global confidence threshold for mapping rules.

```yaml
# Mapping rules with confidence below this threshold are ignored
confidence_threshold: 0.7
```

### Complete Lens Example

Here's the complete Edinburgh Finds lens configuration:

```yaml
# Edinburgh Finds Lens Configuration
# Defines domain knowledge for sports discovery in Edinburgh

# Schema version (required)
schema: lens/v1

# Query vocabulary for orchestration
vocabulary:
  activity_keywords:
    - padel
    - tennis
    - squash
    - badminton
    - pickleball
    - racquet sport
    - racket sport

  location_indicators:
    - edinburgh
    - leith
    - portobello
    - stockbridge
    - morningside
    - newington
    - bruntsfield
    - marchmont
    - in
    - near
    - around

  facility_keywords:
    - sports centre
    - sports center
    - leisure centre
    - leisure center
    - sports facility
    - club
    - courts
    - venue

# Connector selection rules
connector_rules:
  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [
          padel, tennis, squash, badminton, pickleball,
          football, rugby, swimming,
          sports, facilities, pools, clubs, centres, centers
        ]

  google_places:
    priority: medium
    triggers:
      - type: location_present
      - type: facility_search

  serper:
    priority: medium
    triggers:
      - type: always

# Facets define how dimensions are interpreted
facets:
  activity:
    dimension_source: canonical_activities
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

# Canonical values registry
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

# Mapping rules (raw data → canonical values)
mapping_rules:
  - id: map_padel_from_name
    pattern: "(?i)padel"
    canonical: "padel"
    confidence: 0.95

  - id: map_sports_facility_type
    pattern: "(?i)(sports\\s*(centre|center|facility|club)|leisure\\s*(centre|center)|padel\\s*(club|centre|center)|padel\\s*courts?)"
    canonical: "sports_facility"
    confidence: 0.85

# Module triggers
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

      - rule_id: extract_tennis_court_count
        target_path: tennis_courts.total
        extractor: regex_capture
        pattern: "(?i)(\\d+)\\s*tennis\\s*courts?"
        source_fields: [description, entity_name]
        confidence: 0.85
        applicability:
          source: [serper, google_places, sport_scotland]
          entity_class: [place]
        normalizers: [round_integer]

# Confidence threshold
confidence_threshold: 0.7
```

---

## 4. Connector Registry

The connector registry defines metadata for all available data sources.

### Location

```
engine/orchestration/registry.py
```

### ConnectorSpec Structure

```python
@dataclass(frozen=True)
class ConnectorSpec:
    """
    Immutable metadata specification for a connector.

    Attributes:
        name: Unique identifier (e.g., "serper")
        connector_class: Fully qualified class path for dynamic import
        phase: Orchestration phase ("discovery" or "enrichment")
        cost_per_call_usd: Average cost in USD per API call
        trust_level: Trust score from 0.0 to 1.0 (1.0 = authoritative)
        timeout_seconds: Maximum execution timeout for this connector
        rate_limit_per_day: Maximum requests allowed per day
    """
    name: str
    connector_class: str
    phase: str  # "discovery" or "enrichment"
    cost_per_call_usd: float
    trust_level: float  # 0.0 to 1.0
    timeout_seconds: int
    rate_limit_per_day: int
```

### Registered Connectors

Current registry includes 6 connectors:

```python
CONNECTOR_REGISTRY: Dict[str, ConnectorSpec] = {
    "serper": ConnectorSpec(
        name="serper",
        connector_class="engine.ingestion.connectors.serper.SerperConnector",
        phase="discovery",
        cost_per_call_usd=0.01,
        trust_level=0.75,
        timeout_seconds=30,
        rate_limit_per_day=2500,
    ),
    "google_places": ConnectorSpec(
        name="google_places",
        connector_class="engine.ingestion.connectors.google_places.GooglePlacesConnector",
        phase="enrichment",
        cost_per_call_usd=0.017,
        trust_level=0.95,
        timeout_seconds=30,
        rate_limit_per_day=1000,
    ),
    "openstreetmap": ConnectorSpec(
        name="openstreetmap",
        connector_class="engine.ingestion.connectors.open_street_map.OSMConnector",
        phase="discovery",
        cost_per_call_usd=0.0,
        trust_level=0.70,
        timeout_seconds=60,
        rate_limit_per_day=10000,
    ),
    "sport_scotland": ConnectorSpec(
        name="sport_scotland",
        connector_class="engine.ingestion.connectors.sport_scotland.SportScotlandConnector",
        phase="enrichment",
        cost_per_call_usd=0.0,
        trust_level=0.90,
        timeout_seconds=60,
        rate_limit_per_day=10000,
    ),
    "edinburgh_council": ConnectorSpec(
        name="edinburgh_council",
        connector_class="engine.ingestion.connectors.edinburgh_council.EdinburghCouncilConnector",
        phase="enrichment",
        cost_per_call_usd=0.0,
        trust_level=0.90,
        timeout_seconds=60,
        rate_limit_per_day=10000,
    ),
    "open_charge_map": ConnectorSpec(
        name="open_charge_map",
        connector_class="engine.ingestion.connectors.open_charge_map.OpenChargeMapConnector",
        phase="enrichment",
        cost_per_call_usd=0.0,
        trust_level=0.80,
        timeout_seconds=60,
        rate_limit_per_day=10000,
    ),
}
```

### Connector Attributes Reference

| Attribute | Description | Example Values |
|-----------|-------------|----------------|
| `name` | Unique connector identifier | `serper`, `google_places` |
| `connector_class` | Python class path | `engine.ingestion.connectors.serper.SerperConnector` |
| `phase` | Orchestration phase | `discovery` (broad search), `enrichment` (detail lookup) |
| `cost_per_call_usd` | Average API cost | `0.01` (Serper), `0.0` (free APIs) |
| `trust_level` | Data quality score (0.0-1.0) | `0.95` (Google), `0.70` (crowdsourced) |
| `timeout_seconds` | Max execution time | `30` (fast), `60` (slower) |
| `rate_limit_per_day` | Daily request limit | `2500` (Serper free tier), `10000` (conservative) |

### Trust Level Guidelines

| Trust Level | Description | Examples |
|-------------|-------------|----------|
| **0.95-1.0** | Authoritative, verified data | Google Places (0.95) |
| **0.85-0.94** | Official government/organization data | Sport Scotland (0.90), Edinburgh Council (0.90) |
| **0.75-0.84** | Specialized crowdsourced data | Open Charge Map (0.80) |
| **0.60-0.74** | Web search results, moderate quality | Serper (0.75) |
| **0.40-0.59** | General crowdsourced data | OpenStreetMap (0.70) |

### Orchestration Phases

**Discovery Phase**: Broad entity discovery (search-oriented)

- Serper (web search)
- OpenStreetMap (geographic search)

**Enrichment Phase**: Detailed entity enrichment (lookup-oriented)

- Google Places (place details)
- Sport Scotland (sports facility details)
- Edinburgh Council (civic data)
- Open Charge Map (EV charging details)

### Adding a New Connector

1. **Implement connector class** (extends `BaseConnector`)
2. **Register in `CONNECTOR_REGISTRY`**:

```python
CONNECTOR_REGISTRY["new_connector"] = ConnectorSpec(
    name="new_connector",
    connector_class="engine.ingestion.connectors.new_connector.NewConnector",
    phase="enrichment",
    cost_per_call_usd=0.0,
    trust_level=0.85,
    timeout_seconds=60,
    rate_limit_per_day=10000,
)
```

3. **Add connector class mapping**:

```python
_CONNECTOR_CLASSES["new_connector"] = NewConnector
```

4. **Add lens routing rules** (in lens.yaml):

```yaml
connector_rules:
  new_connector:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [domain, specific, keywords]
```

---

## 5. Environment Variables

Environment variables configure runtime behavior and store secrets.

### Location

```
.env                    # Backend + frontend (root)
web/.env                # Frontend only (Next.js)
```

### Required Variables

#### Backend (Engine)

```bash
# ------------------------------------------------------------------
# Database Configuration (REQUIRED)
# ------------------------------------------------------------------
# PostgreSQL Connection String
# Format: postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public
DATABASE_URL="postgresql://postgres:password@localhost:5432/edinburgh_finds?schema=public"

# ------------------------------------------------------------------
# LLM API Keys (REQUIRED for extraction)
# ------------------------------------------------------------------
# Anthropic API for Claude-powered extraction
ANTHROPIC_API_KEY="sk-ant-api03-..."

# ------------------------------------------------------------------
# Data Source API Keys (OPTIONAL but recommended)
# ------------------------------------------------------------------
# Google Places API (for Places ingestion)
GOOGLE_PLACES_API_KEY="your-google-places-api-key"

# Serper API (for search-based ingestion)
SERPER_API_KEY="your-serper-api-key"
```

#### Frontend (Web)

```bash
# ------------------------------------------------------------------
# Database Configuration (REQUIRED)
# ------------------------------------------------------------------
# PostgreSQL Connection String (same as backend)
DATABASE_URL="postgresql://postgres:password@localhost:5432/edinburgh_finds?schema=public"

# ------------------------------------------------------------------
# Next.js Configuration
# ------------------------------------------------------------------
# Node environment
NODE_ENV="development"  # or "production"
```

### Optional Variables

```bash
# ------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------
# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL="INFO"

# ------------------------------------------------------------------
# Orchestration Configuration
# ------------------------------------------------------------------
# Maximum connectors to execute in parallel
MAX_PARALLEL_CONNECTORS="3"

# Cost budget per query (USD)
MAX_COST_PER_QUERY="0.50"

# ------------------------------------------------------------------
# Extraction Configuration
# ------------------------------------------------------------------
# LLM model for extraction
ANTHROPIC_MODEL="claude-sonnet-4.5"

# LLM temperature (0.0-1.0)
ANTHROPIC_TEMPERATURE="0.0"

# ------------------------------------------------------------------
# Development Configuration
# ------------------------------------------------------------------
# Enable debug mode
DEBUG="false"

# Enable verbose logging
VERBOSE="false"
```

### Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string (Supabase or local) |
| `ANTHROPIC_API_KEY` | Yes | - | Anthropic API key for Claude LLM extraction |
| `GOOGLE_PLACES_API_KEY` | No | - | Google Places API key (enrichment connector) |
| `SERPER_API_KEY` | No | - | Serper API key (discovery connector) |
| `NODE_ENV` | No | `development` | Node environment (`development`, `production`) |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MAX_PARALLEL_CONNECTORS` | No | `3` | Max concurrent connector executions |
| `MAX_COST_PER_QUERY` | No | `0.50` | Cost budget per query (USD) |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4.5` | LLM model identifier |
| `ANTHROPIC_TEMPERATURE` | No | `0.0` | LLM temperature (0.0 = deterministic) |
| `DEBUG` | No | `false` | Enable debug mode |
| `VERBOSE` | No | `false` | Enable verbose logging |

### Example .env File

```bash
# ============================================================
# Edinburgh Finds - Environment Configuration
# ============================================================

# ------------------------------------------------------------------
# Database Configuration
# ------------------------------------------------------------------
# PostgreSQL Connection String (Required for Dev & Prod)
# Format: postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public
DATABASE_URL="postgresql://postgres:password@localhost:5432/edinburgh_finds?schema=public"

# ------------------------------------------------------------------
# API Keys
# ------------------------------------------------------------------
# Anthropic API (required for LLM extraction)
ANTHROPIC_API_KEY="sk-ant-api03-..."

# Google Places API (for Places ingestion)
GOOGLE_PLACES_API_KEY="your-google-places-api-key"

# Serper API (for search-based ingestion)
SERPER_API_KEY="your-serper-api-key"

# ------------------------------------------------------------------
# Optional Configuration
# ------------------------------------------------------------------
# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL="INFO"

# Node environment
NODE_ENV="development"
```

### Security Best Practices

1. **Never commit `.env` to git** (add to `.gitignore`)
2. **Use `.env.example` for templates** (with placeholder values)
3. **Rotate API keys regularly**
4. **Use different keys for dev/staging/production**
5. **Store production secrets in secure vault** (e.g., AWS Secrets Manager)
6. **Restrict database user permissions** (principle of least privilege)

---

## 6. Validation Rules

The system enforces strict validation at multiple levels to maintain architectural integrity.

### Validation Philosophy

**Fail-Fast Enforcement**: Invalid configurations abort immediately at load time (not runtime). Silent fallback behavior is forbidden.

### Architectural Validation Gates

The system implements **7 validation gates** (defined in `docs/target/architecture.md` Section 6.7):

#### Gate 1: Schema Validation

**Requirement**: Required top-level sections must be present in lens.yaml

**Required Sections**:
- `schema` (lens version)
- `facets` (dimension interpretation)
- `values` (canonical registry)
- `mapping_rules` (raw → canonical transformation)

**Validation**:
```python
# In engine/lenses/validator.py
REQUIRED_LENS_SECTIONS = {
    "schema",
    "facets",
    "values",
    "mapping_rules",
}

def _validate_required_sections(config):
    for section in REQUIRED_LENS_SECTIONS:
        if section not in config:
            raise ValidationError(f"Missing required section: {section}")
```

#### Gate 2: Canonical Reference Integrity

**Requirement**: All references must point to valid canonical values

**Validations**:

1. **Facet dimension sources** must be one of:
   - `canonical_activities`
   - `canonical_roles`
   - `canonical_place_types`
   - `canonical_access`

2. **Value facet references** must exist in `facets` section

3. **Mapping rule canonical references** must exist in `values` section

4. **Module trigger facet references** must exist in `facets` section

5. **Module trigger module references** must exist in `modules` section

**Example Validation Error**:
```
ValidationError: Facet 'activity' has invalid dimension_source 'canonical_sports'.
dimension_source must be one of: canonical_activities, canonical_roles,
canonical_place_types, canonical_access
```

#### Gate 3: Connector Reference Validation

**Requirement**: All connector names in `connector_rules` must exist in `CONNECTOR_REGISTRY`

**Validation**:
```python
from engine.orchestration.registry import CONNECTOR_REGISTRY

def _validate_connector_references(connector_rules):
    for connector_name in connector_rules.keys():
        if connector_name not in CONNECTOR_REGISTRY:
            raise ValidationError(
                f"Connector rules references non-existent connector '{connector_name}'"
            )
```

**Available Connectors**: `serper`, `google_places`, `openstreetmap`, `sport_scotland`, `edinburgh_council`, `open_charge_map`

#### Gate 4: Identifier Uniqueness

**Requirement**: Keys must be unique within their scope

**Validations**:

1. **Value keys** must be unique across all values
2. **Facet keys** are implicitly unique (dict structure)
3. **Module names** are implicitly unique (dict structure)

**Example Validation Error**:
```
ValidationError: Duplicate value.key found: padel, tennis.
Each value.key must be unique across all values.
```

#### Gate 5: Regex Compilation Validation

**Requirement**: All regex patterns in `mapping_rules` must compile

**Validation**:
```python
import re

def _validate_regex_patterns(mapping_rules):
    for rule in mapping_rules:
        pattern = rule.get("pattern")
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValidationError(
                f"Invalid regex pattern: {pattern}. Error: {e}"
            )
```

**Common Regex Errors**:
- Unescaped special characters: `(` → `\(`
- Invalid character class: `[a-Z]` → `[a-zA-Z]`
- Unbalanced groups: `(abc` → `(abc)`

#### Gate 6: Smoke Coverage Validation

**Requirement**: Every facet must have at least one value

**Validation**:
```python
def _validate_facet_coverage(facets, values):
    facets_with_values = {v.get("facet") for v in values}
    for facet_key in facets.keys():
        if facet_key not in facets_with_values:
            raise ValidationError(
                f"Facet '{facet_key}' has no values. "
                "Every facet must have at least one value."
            )
```

#### Gate 7: Fail-Fast Enforcement

**Requirement**: Errors abort immediately, no silent fallbacks

**Implementation**: All validation gates raise `ValidationError` immediately on violation. No default values, no recovery, no "best effort" behavior.

### Schema Validation

Schema files (`engine/config/schemas/*.yaml`) are validated for:

1. **Field name validity**: Snake_case, no reserved words
2. **Type validity**: Type must be in `SUPPORTED_TYPES`
3. **Constraint validity**: Required fields cannot be nullable
4. **Reference validity**: Foreign keys must reference valid schemas

**Validation Command**:
```bash
python -m engine.schema.generate --validate
```

### Lens Validation

Lens files (`engine/lenses/<lens_id>/lens.yaml`) are validated for all 7 gates at load time.

**Validation Command**:
```bash
# Validation happens automatically when lens is loaded
python -m engine.orchestration.cli run "test query"

# Or test lens loading explicitly
python -c "from engine.lenses.loader import load_lens; load_lens('edinburgh_finds')"
```

### Entity Validation

Extracted entities are validated against Pydantic schemas before persistence.

**Validation Rules**:

1. **Required fields** must be present
2. **Field types** must match schema
3. **Validators** must pass (phone format, postcode format, URL format)
4. **Canonical dimensions** must contain only declared values (checked during lens application)

**Example Validation Error**:
```python
ValidationError: 1 validation error for Entity
  phone
    String should match pattern '^\\+44\\d{10}$' [type=string_pattern_mismatch]
```

### Bootstrap Validation

At system startup, the following checks run:

1. **Lens contract validation** (all 7 gates)
2. **Connector registry validation** (all connectors have valid metadata)
3. **Database connectivity** (connection string valid)
4. **API key presence** (required keys exist in environment)

**Fail-Fast**: System refuses to start if any bootstrap validation fails.

---

## 7. Module Schemas

Modules provide **namespaced structured data** for domain-specific attributes.

### Module Philosophy

**Universal Core + Domain Modules**: The universal schema (`entity.yaml`) defines common fields. Modules extend entities with domain-specific structured data stored in the `modules` JSONB column.

### Module Structure

Modules are stored as nested JSONB:

```json
{
  "modules": {
    "sports_facility": {
      "padel_courts": {
        "total": 4,
        "indoor": 2,
        "outdoor": 2,
        "covered": true,
        "heated": true
      },
      "tennis_courts": {
        "total": 6,
        "surface": "hard"
      },
      "facility_type": "indoor"
    },
    "hospitality_venue": {
      "cuisine_type": ["italian", "mediterranean"],
      "seating_capacity": 80,
      "outdoor_seating": true,
      "private_dining_available": true
    }
  }
}
```

### Universal Modules

Universal modules apply to all verticals:

#### core

Basic entity identity (always present)

```json
{
  "core": {
    "entity_id": "clx...",
    "entity_name": "The Padel Club",
    "entity_class": "place",
    "slug": "padel-club"
  }
}
```

#### location

Geographic information (for place entities)

```json
{
  "location": {
    "street_address": "123 Main St",
    "city": "Edinburgh",
    "postcode": "EH1 2AB",
    "country": "United Kingdom",
    "latitude": 55.9533,
    "longitude": -3.1883,
    "neighborhood": "Old Town"
  }
}
```

#### contact

Contact information

```json
{
  "contact": {
    "phone": "+441315551234",
    "email": "info@example.com",
    "website_url": "https://example.com",
    "instagram_url": "@example",
    "facebook_url": "https://facebook.com/example"
  }
}
```

#### hours

Opening hours

```json
{
  "hours": {
    "monday": {"open": "06:00", "close": "22:00"},
    "tuesday": {"open": "06:00", "close": "22:00"},
    "wednesday": {"open": "06:00", "close": "22:00"},
    "thursday": {"open": "06:00", "close": "22:00"},
    "friday": {"open": "06:00", "close": "23:00"},
    "saturday": {"open": "08:00", "close": "23:00"},
    "sunday": {"open": "08:00", "close": "21:00"}
  }
}
```

### Domain-Specific Modules

Domain modules are triggered by lens rules:

#### sports_facility

For sports venues (triggered when `canonical_activities` includes sports)

```json
{
  "sports_facility": {
    "padel_courts": {
      "total": 4,
      "indoor": 2,
      "outdoor": 2,
      "covered": true,
      "heated": true
    },
    "tennis_courts": {
      "total": 6,
      "surface": "hard"
    },
    "squash_courts": {
      "total": 3
    },
    "facility_type": "indoor",
    "changing_rooms": true,
    "showers": true,
    "equipment_rental": true,
    "coaching_available": true,
    "membership_required": false
  }
}
```

#### fitness_facility

For gyms and fitness centers

```json
{
  "fitness_facility": {
    "equipment_types": ["cardio", "weights", "functional"],
    "group_classes": ["yoga", "spin", "hiit"],
    "personal_training": true,
    "pool": false,
    "sauna": true,
    "24_hour_access": false
  }
}
```

#### hospitality_venue

For restaurants, cafes, bars

```json
{
  "hospitality_venue": {
    "cuisine_type": ["italian", "mediterranean"],
    "meal_types": ["lunch", "dinner"],
    "price_range": "££",
    "seating_capacity": 80,
    "outdoor_seating": true,
    "bar": true,
    "takeaway": true,
    "delivery": false,
    "private_dining_available": true,
    "dietary_options": ["vegetarian", "vegan", "gluten-free"]
  }
}
```

#### retail_store

For shops and retailers

```json
{
  "retail_store": {
    "product_categories": ["sports_equipment", "apparel", "footwear"],
    "brands_carried": ["Nike", "Adidas", "Wilson"],
    "online_ordering": true,
    "click_and_collect": true,
    "returns_policy": "30_days"
  }
}
```

#### coaching

For instructors and coaches

```json
{
  "coaching": {
    "specialization": ["padel", "tennis"],
    "experience_years": 10,
    "qualifications": ["LTA Level 3", "PTR Certified"],
    "teaches_levels": ["beginner", "intermediate", "advanced"],
    "age_groups": ["youth", "adult"],
    "private_lessons": true,
    "group_lessons": true,
    "rates": {
      "private_hourly": "£50",
      "group_hourly": "£20"
    }
  }
}
```

### Module Field Rules

Modules are populated using **field rules** defined in lens configuration:

```yaml
modules:
  sports_facility:
    description: "Sports facility with courts, pitches, or equipment"
    field_rules:
      # Extract court count using regex
      - rule_id: extract_padel_court_count
        target_path: padel_courts.total
        extractor: regex_capture
        pattern: "(?i)(\\d+)\\s+padel\\s*courts?"
        source_fields: [summary, description, entity_name]
        confidence: 0.85
        applicability:
          source: [serper, google_places, sport_scotland]
          entity_class: [place]
        normalizers: [round_integer]

      # Extract facility type using LLM
      - rule_id: extract_facility_type
        target_path: facility_type
        extractor: llm_extraction
        prompt: "Determine if this is an 'indoor', 'outdoor', or 'mixed' facility"
        source_fields: [description, summary]
        confidence: 0.80
        applicability:
          entity_class: [place]
```

### Extractor Types

| Extractor | Description | Use Case |
|-----------|-------------|----------|
| `regex_capture` | Extract using regex pattern | Structured data in text (court counts, phone numbers) |
| `llm_extraction` | Extract using LLM with schema | Unstructured data requiring interpretation |
| `deterministic_lookup` | Lookup from predefined mappings | Known mappings (abbreviations, codes) |

### Normalizer Functions

| Normalizer | Description | Example Input → Output |
|------------|-------------|------------------------|
| `lowercase` | Convert to lowercase | `"INDOOR"` → `"indoor"` |
| `uppercase` | Convert to uppercase | `"indoor"` → `"INDOOR"` |
| `trim` | Remove leading/trailing whitespace | `" padel "` → `"padel"` |
| `round_integer` | Round to nearest integer | `"4.2"` → `4` |
| `parse_boolean` | Parse boolean | `"yes"` → `true` |
| `parse_currency` | Extract currency amount | `"£50/hour"` → `50.0` |

---

## 8. Canonical Registry

The canonical value registry defines **all valid values** for canonical dimensions.

### Registry Philosophy

**No Undeclared Values**: All canonical values must be explicitly declared. Orphaned references are invalid and fail fast.

### Registry Structure

Canonical values are defined in `lens.yaml` under the `values` section:

```yaml
values:
  - key: padel                    # Unique identifier (stored in DB)
    facet: activity               # Facet this value belongs to
    display_name: "Padel"         # UI label
    description: "..."            # Full description
    seo_slug: "padel"             # URL slug
    search_keywords: [...]        # Search matching
    icon_url: "/icons/padel.svg"  # Icon path
    color: "#10B981"              # UI theming color
```

### Complete Canonical Value Example

```yaml
values:
  # ============================================================
  # ACTIVITY FACET (canonical_activities dimension)
  # ============================================================

  - key: padel
    facet: activity
    display_name: "Padel"
    description: "Racquet sport combining elements of tennis and squash, played in doubles on an enclosed court"
    seo_slug: "padel"
    search_keywords:
      - padel
      - racket sport
      - racquet sport
      - paddle tennis
    icon_url: "/icons/padel.svg"
    color: "#10B981"
    related_values:
      - tennis
      - squash
      - pickleball

  - key: tennis
    facet: activity
    display_name: "Tennis"
    description: "Classic racquet sport played on rectangular court with net, singles or doubles"
    seo_slug: "tennis"
    search_keywords:
      - tennis
      - lawn tennis
      - racquet sport
    icon_url: "/icons/tennis.svg"
    color: "#3B82F6"
    related_values:
      - padel
      - squash

  - key: squash
    facet: activity
    display_name: "Squash"
    description: "Indoor racquet sport played in four-walled court"
    seo_slug: "squash"
    search_keywords:
      - squash
      - racquetball
      - racket sport
    icon_url: "/icons/squash.svg"
    color: "#8B5CF6"
    related_values:
      - tennis
      - padel

  # ============================================================
  # PLACE_TYPE FACET (canonical_place_types dimension)
  # ============================================================

  - key: sports_facility
    facet: place_type
    display_name: "Sports Facility"
    description: "Venue providing sports courts, pitches, or specialized equipment for athletic activities"
    seo_slug: "sports-facility"
    search_keywords:
      - sports centre
      - sports center
      - leisure centre
      - leisure center
      - sports facility
      - sports complex
    icon_url: "/icons/facility.svg"
    color: "#10B981"

  - key: fitness_centre
    facet: place_type
    display_name: "Fitness Centre"
    description: "Gym or health club with exercise equipment and group fitness classes"
    seo_slug: "fitness-centre"
    search_keywords:
      - gym
      - fitness centre
      - fitness center
      - health club
    icon_url: "/icons/gym.svg"
    color: "#F59E0B"

  - key: outdoor_facility
    facet: place_type
    display_name: "Outdoor Facility"
    description: "Open-air venue for sports and recreation"
    seo_slug: "outdoor-facility"
    search_keywords:
      - outdoor
      - open air
      - park
      - playing field
    icon_url: "/icons/outdoor.svg"
    color: "#22C55E"

  # ============================================================
  # ROLE FACET (canonical_roles dimension)
  # ============================================================

  - key: provides_facility
    facet: role
    display_name: "Facility Provider"
    description: "Provides physical venue for activities"
    seo_slug: "facility-provider"
    search_keywords:
      - venue
      - facility
      - centre
      - center
    icon_url: "/icons/building.svg"
    color: "#6B7280"

  - key: provides_instruction
    facet: role
    display_name: "Instruction Provider"
    description: "Offers coaching, lessons, or training services"
    seo_slug: "instruction-provider"
    search_keywords:
      - coach
      - instructor
      - trainer
      - lessons
      - coaching
    icon_url: "/icons/teacher.svg"
    color: "#3B82F6"

  - key: sells_goods
    facet: role
    display_name: "Retail Provider"
    description: "Sells equipment, apparel, or related products"
    seo_slug: "retail-provider"
    search_keywords:
      - shop
      - store
      - retailer
      - supplier
    icon_url: "/icons/shopping.svg"
    color: "#F59E0B"

  - key: membership_org
    facet: role
    display_name: "Membership Organization"
    description: "Operates as members-only club or association"
    seo_slug: "membership-organization"
    search_keywords:
      - club
      - association
      - society
      - members
    icon_url: "/icons/users.svg"
    color: "#8B5CF6"

  # ============================================================
  # ACCESS FACET (canonical_access dimension)
  # ============================================================

  - key: pay_and_play
    facet: access
    display_name: "Pay and Play"
    description: "Open to public, pay per session without membership"
    seo_slug: "pay-and-play"
    search_keywords:
      - pay and play
      - public access
      - walk-in
      - drop-in
      - no membership
    icon_url: "/icons/cash.svg"
    color: "#10B981"

  - key: membership
    facet: access
    display_name: "Membership Required"
    description: "Requires paid membership for access"
    seo_slug: "membership-required"
    search_keywords:
      - membership
      - members only
      - subscription
      - annual fee
    icon_url: "/icons/card.svg"
    color: "#F59E0B"

  - key: free
    facet: access
    display_name: "Free Access"
    description: "Free to use, no payment required"
    seo_slug: "free-access"
    search_keywords:
      - free
      - no charge
      - complimentary
    icon_url: "/icons/gift.svg"
    color: "#22C55E"

  - key: private_club
    facet: access
    display_name: "Private Club"
    description: "Exclusive access for members only, invitation or application required"
    seo_slug: "private-club"
    search_keywords:
      - private
      - exclusive
      - members only
      - invitation only
    icon_url: "/icons/lock.svg"
    color: "#6B7280"
```

### Canonical Value Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `key` | string | Yes | Unique identifier (stored in database, never changes) |
| `facet` | string | Yes | Facet key this value belongs to (must exist in `facets`) |
| `display_name` | string | Yes | Human-readable label for UI |
| `description` | string | Yes | Detailed explanation (1-2 sentences) |
| `seo_slug` | string | Yes | URL-safe slug (kebab-case, used in URLs) |
| `search_keywords` | list[string] | Yes | Keywords for search and mapping rules |
| `icon_url` | string | Yes | Icon path or URL |
| `color` | string | Yes | Hex color code for UI theming (e.g., `#10B981`) |
| `related_values` | list[string] | No | Related canonical values (for recommendations) |
| `aliases` | list[string] | No | Alternative names/spellings |
| `deprecated` | boolean | No | Mark as deprecated (still valid but discouraged) |

### Registry Validation

The canonical registry is validated at lens load time:

1. **Uniqueness**: No duplicate `key` values
2. **Facet references**: All `facet` references must exist in `facets` section
3. **Complete metadata**: All required attributes present
4. **Color format**: Valid hex color codes
5. **Slug format**: Valid URL slug (kebab-case, no special characters)

### Using Canonical Values

**In Mapping Rules**:
```yaml
mapping_rules:
  - pattern: "(?i)padel"
    canonical: "padel"  # Must exist in values registry
    confidence: 0.95
```

**In Module Triggers**:
```yaml
module_triggers:
  - when:
      facet: activity
      value: padel  # Must exist in values registry
    add_modules: [sports_facility]
```

**In Database Queries**:
```sql
-- Find all entities with padel activity
SELECT * FROM "Entity"
WHERE 'padel' = ANY(canonical_activities);

-- Find entities with multiple activities
SELECT * FROM "Entity"
WHERE canonical_activities @> ARRAY['padel', 'tennis'];
```

---

## 9. Configuration Best Practices

### Engine Purity

**NEVER add domain logic to engine code**. All domain semantics belong in lens configuration.

**Wrong (violates engine purity)**:
```python
# engine/classification/entity_classifier.py
if "padel" in entity_name.lower():  # ❌ Domain-specific term in engine
    entity.canonical_activities.append("padel")
```

**Right (lens-driven interpretation)**:
```yaml
# engine/lenses/edinburgh_finds/lens.yaml
mapping_rules:
  - pattern: "(?i)padel"  # ✅ Domain logic in lens
    canonical: "padel"
    confidence: 0.95
```

### Deterministic Configuration

**Mapping rules must be deterministic**. Given the same input, always produce the same output.

**Wrong (non-deterministic)**:
```yaml
mapping_rules:
  - pattern: "(?i)(padel|tennis)"  # ❌ Captures either value unpredictably
    canonical: "${captured_value}"
    confidence: 0.90
```

**Right (explicit rules)**:
```yaml
mapping_rules:
  - pattern: "(?i)padel"
    canonical: "padel"
    confidence: 0.95

  - pattern: "(?i)tennis"
    canonical: "tennis"
    confidence: 0.95
```

### Confidence Calibration

Confidence scores should reflect **actual reliability**:

| Confidence | Description | Use Case |
|------------|-------------|----------|
| **0.95-1.0** | Exact match, unambiguous | Official names, domain-specific terms |
| **0.85-0.94** | Strong pattern, minor ambiguity | Type indicators, category names |
| **0.75-0.84** | Moderate pattern, some ambiguity | Descriptive text, inferred attributes |
| **0.60-0.74** | Weak pattern, significant ambiguity | Speculative matching, fallback rules |

**Example**:
```yaml
mapping_rules:
  # High confidence: Exact match in entity name
  - pattern: "(?i)\\bpadel\\b"
    canonical: "padel"
    confidence: 0.95

  # Medium confidence: Type indicator in description
  - pattern: "(?i)sports\\s*(centre|facility)"
    canonical: "sports_facility"
    confidence: 0.85

  # Lower confidence: Inferred from context
  - pattern: "(?i)courts?\\s*(available|for\\s*hire)"
    canonical: "provides_facility"
    confidence: 0.75
```

### Regex Best Practices

1. **Always use case-insensitive flag**: `(?i)`
2. **Escape special characters**: `.` → `\.`, `(` → `\(`
3. **Use word boundaries**: `\b` for exact matches
4. **Test patterns online**: regex101.com before deployment
5. **Document complex patterns**: Add comments in lens.yaml

**Examples**:
```yaml
mapping_rules:
  # Simple keyword match
  - pattern: "(?i)padel"
    canonical: "padel"
    confidence: 0.95

  # Word boundary (exact word)
  - pattern: "(?i)\\btennis\\b"
    canonical: "tennis"
    confidence: 0.95

  # Alternative options
  - pattern: "(?i)(sports\\s*centre|leisure\\s*centre|sports\\s*facility)"
    canonical: "sports_facility"
    confidence: 0.85

  # Numeric extraction
  - pattern: "(?i)(\\d+)\\s+padel\\s*courts?"
    target_path: padel_courts.total
    confidence: 0.85
```

### Module Trigger Conditions

Use module triggers to **conditionally attach modules** based on entity characteristics.

**Example**:
```yaml
module_triggers:
  # Only attach sports_facility module to places
  - when:
      facet: activity
      value: padel
    add_modules: [sports_facility]
    conditions:
      - entity_class: place  # Constraint: must be a place

  # Attach coaching module to people or organizations
  - when:
      facet: role
      value: provides_instruction
    add_modules: [coaching]
    conditions:
      - entity_class: [person, organization]
```

### Canonical Value Naming

**Use universal, functional names** (not domain-specific labels):

**Wrong**:
```yaml
values:
  - key: padel_club  # ❌ Domain-specific
    facet: place_type
```

**Right**:
```yaml
values:
  - key: sports_facility  # ✅ Universal, functional
    facet: place_type
    display_name: "Padel Club"  # Domain-specific label is OK in display_name
```

### Configuration Versioning

1. **Version lens schema**: Include `schema: lens/v1` in lens.yaml
2. **Track configuration changes**: Commit lens changes with descriptive messages
3. **Test before deploying**: Validate lens before production deployment
4. **Document breaking changes**: Note incompatible changes in commit messages

---

## 10. Troubleshooting

### Validation Failures

#### Error: Missing Required Section

```
ValidationError: Missing required section: mapping_rules
```

**Solution**: Add missing section to lens.yaml:
```yaml
mapping_rules:
  - pattern: "(?i)..."
    canonical: "..."
    confidence: 0.85
```

#### Error: Invalid Dimension Source

```
ValidationError: Facet 'activity' has invalid dimension_source 'canonical_sports'.
dimension_source must be one of: canonical_activities, canonical_roles,
canonical_place_types, canonical_access
```

**Solution**: Use valid dimension source:
```yaml
facets:
  activity:
    dimension_source: canonical_activities  # ✅ Valid
```

#### Error: Non-Existent Connector

```
ValidationError: Connector rules references non-existent connector 'my_connector'.
Available connectors: serper, google_places, openstreetmap, sport_scotland,
edinburgh_council, open_charge_map
```

**Solution**: Either:
1. Fix typo in connector name
2. Add connector to `engine/orchestration/registry.py`

#### Error: Orphaned Canonical Reference

```
ValidationError: Mapping rule references non-existent value 'padel_sport'.
Available values: padel, tennis, squash
```

**Solution**: Add missing value to registry:
```yaml
values:
  - key: padel_sport  # Add missing value
    facet: activity
    display_name: "Padel"
    # ... other attributes
```

#### Error: Invalid Regex Pattern

```
ValidationError: Invalid regex pattern in mapping rule: '(?i)(padel[)'.
Regex error: unbalanced parenthesis at position 10
```

**Solution**: Fix regex syntax:
```yaml
mapping_rules:
  - pattern: "(?i)(padel)"  # ✅ Balanced parentheses
    canonical: "padel"
    confidence: 0.95
```

### Schema Generation Errors

#### Error: Schema Validation Failed

```bash
$ python -m engine.schema.generate --validate
SchemaValidationError: Field 'entity_name' in entity.yaml has invalid type 'str'.
Supported types: string, integer, float, boolean, datetime, json, list[string]
```

**Solution**: Use valid YAML type:
```yaml
fields:
  - name: entity_name
    type: string  # ✅ Valid YAML type (not Python type)
```

#### Error: Generated File Already Modified

```bash
$ python -m engine.schema.generate --all
Warning: Generated file engine/schema/entity.py has been manually modified.
Manual changes will be lost. Continue? [y/N]
```

**Solution**: NEVER edit generated files. Edit source YAML instead:
1. Revert manual changes to generated file
2. Edit `engine/config/schemas/entity.yaml`
3. Regenerate: `python -m engine.schema.generate --all`

### Missing Canonical Values

#### Symptom: Entities Not Categorized

Entities are extracted but `canonical_activities`, `canonical_roles`, etc. are empty.

**Diagnosis**:
1. Check if mapping rules exist in lens.yaml
2. Check if patterns match entity data
3. Check confidence threshold (rules below threshold ignored)

**Solution**:
```yaml
# Add or adjust mapping rules
mapping_rules:
  - pattern: "(?i)padel"
    canonical: "padel"
    confidence: 0.95  # Ensure above confidence_threshold (0.7)

# Lower confidence threshold if needed
confidence_threshold: 0.6  # Default: 0.7
```

### Lens Loading Errors

#### Error: Lens File Not Found

```
FileNotFoundError: Lens configuration not found: engine/lenses/my_lens/lens.yaml
```

**Solution**: Create lens directory and file:
```bash
mkdir -p engine/lenses/my_lens
touch engine/lenses/my_lens/lens.yaml
# Add lens configuration to lens.yaml
```

#### Error: Invalid YAML Syntax

```
yaml.scanner.ScannerError: mapping values are not allowed here
  in "engine/lenses/edinburgh_finds/lens.yaml", line 42, column 18
```

**Solution**: Fix YAML syntax (common issues):
- Indentation errors (use 2 spaces, not tabs)
- Missing colons after keys
- Unquoted strings with special characters

### Environment Variable Errors

#### Error: Missing Required Environment Variable

```
EnvironmentError: ANTHROPIC_API_KEY environment variable not set
```

**Solution**: Add to `.env` file:
```bash
ANTHROPIC_API_KEY="sk-ant-api03-..."
```

#### Error: Invalid Database URL

```
prisma.errors.PrismaClientInitializationError: Can't reach database server
```

**Solution**: Check DATABASE_URL format:
```bash
# Correct format
DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public"

# Example
DATABASE_URL="postgresql://postgres:password@localhost:5432/edinburgh_finds?schema=public"
```

### Module Extraction Errors

#### Symptom: Module Fields Not Populated

Module is attached but fields are empty or missing.

**Diagnosis**:
1. Check if field_rules patterns match source data
2. Check if source_fields contain relevant data
3. Check confidence scores

**Solution**:
```yaml
modules:
  sports_facility:
    field_rules:
      - rule_id: extract_court_count
        target_path: padel_courts.total
        extractor: regex_capture
        pattern: "(?i)(\\d+)\\s*padel\\s*courts?"  # Test pattern
        source_fields: [summary, description, entity_name]  # Check these fields
        confidence: 0.85
```

### Performance Issues

#### Symptom: Slow Query Execution

Orchestration queries take >30 seconds.

**Diagnosis**:
1. Too many connectors selected
2. Expensive connectors (Google Places) used excessively
3. No rate limiting

**Solution**:
```yaml
# Adjust connector priorities and triggers
connector_rules:
  google_places:
    priority: medium  # Lower priority
    triggers:
      - type: location_present  # More restrictive trigger
```

#### Symptom: High API Costs

Monthly API costs exceed budget.

**Diagnosis**:
1. Check connector usage in logs
2. Review cost_per_call_usd in registry
3. Check rate_limit_per_day

**Solution**:
1. Increase usage of free connectors (OSM, Sport Scotland)
2. Reduce expensive connector priority
3. Implement cost budgets in orchestration

---

## Summary

Configuration is the **heart** of the Universal Entity Extraction Engine. By keeping all domain knowledge in YAML configuration files, the engine remains pure, vertical-agnostic, and horizontally scalable.

### Key Takeaways

1. **YAML schemas** define universal data structure (single source of truth)
2. **Lens contracts** define domain-specific interpretation (all semantics)
3. **Connector registry** defines data source metadata (cost, trust, routing)
4. **Environment variables** store secrets and runtime configuration
5. **Validation gates** enforce architectural integrity (fail-fast)
6. **Modules** extend entities with domain-specific structured data
7. **Canonical registry** declares all valid dimension values (no orphans)

### Configuration Workflow

```
1. Edit Configuration
   ├─ Schema: engine/config/schemas/entity.yaml
   ├─ Lens: engine/lenses/<lens_id>/lens.yaml
   ├─ Registry: engine/orchestration/registry.py
   └─ Environment: .env

2. Validate
   ├─ Schema: python -m engine.schema.generate --validate
   └─ Lens: Automatic at load time (fail-fast)

3. Regenerate (schemas only)
   └─ python -m engine.schema.generate --all

4. Test
   ├─ Backend: pytest
   ├─ Frontend: cd web && npm run build
   └─ Integration: python -m engine.orchestration.cli run "test query"

5. Commit
   └─ git add <changed files> && git commit -m "feat: ..."
```

### Next Steps

- **Read**: `docs/target/system-vision.md` (architectural principles)
- **Read**: `docs/target/architecture.md` (runtime mechanics)
- **Explore**: Example lenses in `engine/lenses/`
- **Practice**: Create a new lens for a different vertical
- **Validate**: Run full test suite before production deployment

---

**Document Status**: Generated
**Last Updated**: 2026-02-08
**Maintainers**: Claude Code, Development Team
**Feedback**: Submit issues or suggestions via project repository
