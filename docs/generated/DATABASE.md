# DATABASE.md - Universal Entity Extraction Engine

**Generated:** 2026-02-08
**Source Files:**
- `engine/config/schemas/entity.yaml`
- `web/prisma/schema.prisma`
- `engine/orchestration/entity_finalizer.py`
- `docs/generated/diagrams/entity_model.mmd`

**System:** Universal Entity Extraction Engine
**Reference Application:** Edinburgh Finds (padel/sports discovery)

---

## Table of Contents

1. [Overview](#overview)
2. [Schema Architecture](#schema-architecture)
3. [Entity Model](#entity-model)
4. [Canonical Dimensions](#canonical-dimensions)
5. [Modules System](#modules-system)
6. [Pipeline Tables](#pipeline-tables)
7. [Indexes & Performance](#indexes--performance)
8. [Schema Generation](#schema-generation)
9. [Data Integrity](#data-integrity)
10. [Migrations](#migrations)

---

## Overview

### Database Role

The database is the authoritative record of all discovered entities and their pipeline provenance. It serves three primary functions:

1. **Entity Storage** — Validated, deduplicated, merged entities ready for frontend consumption
2. **Pipeline State** — Raw ingestion → extracted entities → finalized entities with full lineage tracking
3. **Operational Metadata** — Orchestration runs, merge conflicts, failed extractions, connector usage

### Technology Stack

- **Database:** PostgreSQL (via Supabase)
- **ORM:** Prisma 7.3+ (TypeScript/JavaScript frontend), Prisma Client Python (Python engine)
- **Indexing:** GIN indexes for multi-valued TEXT[] arrays (canonical dimensions)
- **Data Structures:** JSONB for flexible vertical-specific modules

### Database Independence

The engine's database schema is **vertical-agnostic**. Adding a new vertical (e.g., Wine Discovery, Restaurant Finder) requires:
- ✅ New Lens YAML configuration
- ❌ **NO** database schema changes
- ❌ **NO** table migrations

All domain-specific data lives in:
- **Canonical dimensions** (opaque TEXT[] arrays interpreted by Lens)
- **Modules** (namespaced JSONB interpreted by Lens)

---

## Schema Architecture

### Single Source of Truth: YAML Schemas

The database schema is **auto-generated** from YAML definitions. This eliminates schema drift and enables horizontal scaling.

**YAML Schema Location:** `engine/config/schemas/*.yaml`

**Generation Pipeline:**
```
YAML Definition
    ↓
Python FieldSpecs (engine/schema/*.py)
    ↓
Prisma Schema (web/prisma/schema.prisma, engine/prisma/schema.prisma)
    ↓
TypeScript Interfaces (web/lib/types/generated/*.ts)
```

**Critical Rule:** NEVER edit generated files directly. They contain `DO NOT EDIT` headers and are overwritten on regeneration.

### Schema Regeneration Command

```bash
# Validate YAML schemas
python -m engine.schema.generate --validate

# Regenerate all derived schemas
python -m engine.schema.generate --all

# Apply to database (development)
cd web && npx prisma db push

# Apply to database (production)
cd web && npx prisma migrate dev
```

### Schema Extension Pattern

```yaml
# engine/config/schemas/entity.yaml
schema:
  name: Entity
  description: Base schema for all entity types
  extends: null  # Top-level schema

fields:
  - name: entity_name
    type: string
    nullable: false
    required: true
    index: true
```

---

## Entity Model

### Entity Table Structure

The `Entity` table is the **final published record** of all discovered entities. It represents the output of the 11-stage pipeline (Lens Resolution → Planning → Ingestion → Extraction → Lens Application → Classification → Deduplication → Merge → Finalization).

```mermaid
erDiagram
    %% ============================================================
    %% ENTITY MODEL - Universal Entity Extraction Engine
    %% ============================================================
    %% Shows the core entity schema structure with:
    %% - Universal entity classification (place/person/organization/event/thing)
    %% - Canonical dimensions (TEXT[] arrays for faceted filtering)
    %% - Modules system (JSONB for vertical-specific structured data)
    %% - Provenance tracking and confidence scoring
    %% - Relationships between RawIngestion, ExtractedEntity, and Entity
    %%
    %% Generated: 2026-02-08
    %% Source: engine/config/schemas/entity.yaml, web/prisma/schema.prisma
    %% ============================================================

    Entity {
        string id PK "entity_id - Auto-generated CUID"
        string entity_name "Official name (required, indexed)"
        string entity_class "Universal classification: place, person, organization, event, thing"
        string slug UK "URL-safe identifier (auto-generated, unique)"
        string summary "Short description summary"
        string description "Long-form aggregated evidence"

        %% CLASSIFICATION
        string[] raw_categories "Uncontrolled observational labels (NOT indexed)"

        %% CANONICAL DIMENSIONS - Postgres TEXT[] with GIN indexes
        string[] canonical_activities "Activities provided/supported (opaque, lens-interpreted)"
        string[] canonical_roles "Functional roles (provides_facility, sells_goods, etc.)"
        string[] canonical_place_types "Physical place classifications (lens-interpreted)"
        string[] canonical_access "Access requirements (membership, pay_and_play, free, etc.)"

        %% FLEXIBLE DATA STRUCTURES
        json discovered_attributes "Extra attributes not in core schema"
        json modules "Namespaced JSONB: {sports_facility: {}, hospitality_venue: {}}"

        %% LOCATION
        string street_address "Full address"
        string city "City/town (indexed)"
        string postcode "UK postcode format (indexed)"
        string country "Country name"
        float latitude "WGS84 decimal degrees"
        float longitude "WGS84 decimal degrees"

        %% CONTACT
        string phone "E.164 format (+441315397071)"
        string email "Public email address"
        string website_url "Official website"

        %% SOCIAL MEDIA
        string instagram_url "Instagram profile"
        string facebook_url "Facebook page"
        string twitter_url "Twitter/X profile"
        string linkedin_url "LinkedIn company page"

        %% OPERATING HOURS
        json opening_hours "{monday: {open: '05:30', close: '22:00'}, sunday: 'CLOSED'}"

        %% PROVENANCE AND METADATA
        json source_info "URLs, method, timestamps, notes"
        json field_confidence "Per-field confidence scores (0.0-1.0)"
        json external_ids "{google: 'abc123', osm: '456'}"
        datetime createdAt "Creation timestamp"
        datetime updatedAt "Last update timestamp"
    }

    ExtractedEntity {
        string id PK "Auto-generated CUID"
        string raw_ingestion_id FK "Link to source RawIngestion"
        string source "Connector name (serper, google_places, osm, etc.)"
        string entity_class "Universal classification"
        string attributes "Structured attributes from extraction"
        string discovered_attributes "Additional discovered fields"
        string external_ids "External system identifiers"
        string extraction_hash "Content hash for deduplication"
        string model_used "LLM model identifier (if used)"
        datetime createdAt "Extraction timestamp"
        datetime updatedAt "Last update timestamp"
    }

    RawIngestion {
        string id PK "Auto-generated CUID"
        string source "Connector name (serper, google_places, osm, sport_scotland, etc.)"
        string source_url "Original URL or query"
        string file_path "Path to raw JSON: engine/data/raw/source/timestamp_id.json"
        string status "success, failed, pending"
        string hash "Content hash for deduplication"
        string metadata_json "Additional metadata as JSON"
        string orchestration_run_id FK "Link to parent OrchestrationRun (nullable)"
        datetime ingested_at "Ingestion timestamp"
    }

    OrchestrationRun {
        string id PK "Auto-generated CUID"
        string query "Original user query"
        string ingestion_mode "discover_many, verify_one, etc."
        string status "in_progress, completed, failed"
        int candidates_found "Number of entities discovered"
        int accepted_entities "Number of entities persisted"
        float budget_spent_usd "Cost tracking"
        string metadata_json "Additional orchestration metadata"
        datetime createdAt "Run start timestamp"
        datetime updatedAt "Last update timestamp"
    }

    FailedExtraction {
        string id PK "Auto-generated CUID"
        string raw_ingestion_id FK "Link to failed RawIngestion"
        string source "Connector name"
        string error_message "Error description"
        string error_details "Detailed error trace"
        int retry_count "Number of retry attempts"
        datetime last_attempt_at "Last retry timestamp"
        datetime createdAt "Initial failure timestamp"
        datetime updatedAt "Last update timestamp"
    }

    MergeConflict {
        string id PK "Auto-generated CUID"
        string field_name "Field with conflict"
        string conflicting_values "JSON array of conflicting values"
        string winner_source "Source that won conflict resolution"
        string winner_value "Final value selected"
        int trust_difference "Trust delta between sources"
        float severity "Conflict severity score"
        string entity_id FK "Link to Entity (nullable)"
        boolean resolved "Conflict resolution status"
        string resolution_notes "Human notes on resolution"
        datetime createdAt "Conflict detected timestamp"
        datetime updatedAt "Last update timestamp"
    }

    EntityRelationship {
        string id PK "Auto-generated CUID"
        string sourceEntityId FK "Source entity"
        string targetEntityId FK "Target entity"
        string type "Relationship type: teaches_at, plays_at, part_of, etc."
        float confidence "Confidence score (0.0-1.0)"
        string source "Connector that discovered relationship"
        datetime createdAt "Relationship created timestamp"
        datetime updatedAt "Last update timestamp"
    }

    LensEntity {
        string lensId PK "Lens identifier"
        string entityId PK,FK "Entity identifier"
        datetime createdAt "Membership timestamp"
    }

    %% ============================================================
    %% RELATIONSHIPS
    %% ============================================================

    %% Data Pipeline Flow
    OrchestrationRun ||--o{ RawIngestion : "executes"
    RawIngestion ||--o{ ExtractedEntity : "extracts"
    RawIngestion ||--o{ FailedExtraction : "may fail"
    ExtractedEntity }o--|| Entity : "merges into"

    %% Entity Relationships
    Entity ||--o{ EntityRelationship : "source of"
    Entity ||--o{ EntityRelationship : "target of"
    Entity ||--o{ LensEntity : "member of lenses"
    Entity ||--o{ MergeConflict : "may have conflicts"

    %% ============================================================
    %% NOTES ON MODULE STRUCTURE
    %% ============================================================
    %% modules JSONB Examples:
    %%
    %% Universal Modules (all entity types):
    %% - core: {entity_id, entity_name, slug}
    %% - location: {street_address, city, postcode, latitude, longitude}
    %% - contact: {phone, email, website_url, social_media}
    %% - hours: {opening_hours, special_hours}
    %%
    %% Vertical-Specific Modules (lens-triggered):
    %% - sports_facility: {court_count, court_types, indoor_outdoor, equipment_rental}
    %% - fitness_facility: {class_schedule, equipment_list, membership_tiers}
    %% - hospitality_venue: {cuisine_types, dietary_options, price_range, booking_required}
    %% - retail_store: {product_categories, brands_carried, payment_methods}
    %%
    %% Module Trigger Logic (from lens.yaml):
    %% - IF canonical_activities contains 'tennis' → add sports_facility module
    %% - IF canonical_place_types contains 'restaurant' → add hospitality_venue module
    %% - IF canonical_roles contains 'sells_goods' → add retail_store module
    %%
    %% ============================================================
```

### Core Fields

#### Identification
- **`id`** (Primary Key): Auto-generated CUID
- **`entity_name`**: Official name (required, indexed)
- **`slug`**: URL-safe identifier (unique, auto-generated from entity_name)
- **`entity_class`**: Universal classification (`place`, `person`, `organization`, `event`, `thing`)

#### Content
- **`summary`**: Short description (1-2 sentences)
- **`description`**: Long-form aggregated evidence from multiple sources

#### Classification
- **`raw_categories`**: Uncontrolled observational labels (NOT indexed, NOT used for filtering)
  - Examples: `["Padel Club", "Sports Centre", "Fitness"]`
  - Used by Lens mapping rules to populate canonical dimensions

#### Location
- **`street_address`**: Full address
- **`city`**: City/town (indexed)
- **`postcode`**: UK postcode format (indexed)
- **`country`**: Country name
- **`latitude`** / **`longitude`**: WGS84 decimal degrees

#### Contact
- **`phone`**: E.164 format (e.g., `+441315397071`)
- **`email`**: Public email address
- **`website_url`**: Official website

#### Social Media
- **`instagram_url`**, **`facebook_url`**, **`twitter_url`**, **`linkedin_url`**

#### Operating Hours
- **`opening_hours`**: JSONB structure
  ```json
  {
    "monday": {"open": "05:30", "close": "22:00"},
    "tuesday": {"open": "05:30", "close": "22:00"},
    "sunday": "CLOSED"
  }
  ```

#### Provenance and Metadata
- **`source_info`**: JSONB — URLs, extraction method, timestamps, notes
- **`field_confidence`**: JSONB — Per-field confidence scores (0.0-1.0)
- **`external_ids`**: JSONB — External system identifiers (e.g., `{"google": "ChIJ...", "osm": "123456"}`)
- **`createdAt`** / **`updatedAt`**: Timestamps

---

## Canonical Dimensions

### Purpose

Canonical dimensions are **PostgreSQL TEXT[] arrays with GIN indexes** that enable fast faceted filtering without requiring domain-specific columns. They store multi-valued dimension values as native PostgreSQL arrays.

**Key Principle:** Values are **completely opaque to the engine**. The engine stores and indexes these arrays but assigns no meaning to their contents. All semantic interpretation is provided exclusively by the Lens layer via `canonical_values` and `mapping_rules` in `lens.yaml`.

**Technical Implementation:**
- Storage: Native PostgreSQL `TEXT[]` type
- Indexing: GIN (Generalized Inverted Index) for containment queries
- Engine Behavior: Stores, indexes, and queries arrays without interpreting values
- Lens Responsibility: Defines all vocabulary, display names, icons, and semantic meaning

### The Four Canonical Dimensions

#### 1. `canonical_activities` (TEXT[])
Activities provided or supported by the entity.

**Examples:**
- `["tennis", "padel", "squash"]` (sports facility)
- `["wine_tasting", "vineyard_tours"]` (winery)
- `["yoga", "pilates", "strength_training"]` (fitness studio)

**Lens Mapping (from `lens.yaml`):**
```yaml
mapping_rules:
  - pattern: "(?i)tennis|racket sports"
    dimension: canonical_activities
    value: tennis
    confidence: 0.95

canonical_values:
  tennis:
    display_name: "Tennis"
    seo_slug: "tennis"
    icon: "racquet"
```

#### 2. `canonical_roles` (TEXT[])
Functional roles this entity plays (internal-only facet, not shown in UI by default).

**Examples:**
- `["provides_facility"]` (venue with courts/equipment)
- `["provides_instruction"]` (coaching service)
- `["sells_goods"]` (retail store)
- `["membership_org"]` (sports club, association)
- `["produces_goods"]` (manufacturer, winery)

**Purpose:** Query optimization and module triggering logic.

#### 3. `canonical_place_types` (TEXT[])
Physical place classifications (applicable to `entity_class="place"` only).

**Examples:**
- `["sports_centre"]` (multi-sport facility)
- `["private_club"]` (members-only club)
- `["restaurant"]` (hospitality venue)
- `["retail_store"]` (shop)
- `["winery"]` (wine production facility)

**Lens Mapping:**
```yaml
mapping_rules:
  - pattern: "(?i)sports (centre|center)|leisure centre"
    dimension: canonical_place_types
    value: sports_centre
    confidence: 0.90
```

#### 4. `canonical_access` (TEXT[])
Access requirements and models.

**Examples:**
- `["membership"]` (members-only facility)
- `["pay_and_play"]` (public access, pay per session)
- `["free"]` (public parks, open spaces)
- `["private_club"]` (invitation/application required)

### Database Implementation

**Postgres Type:** `TEXT[]` (native array type)

**Index Type:** GIN (Generalized Inverted Index) for fast containment queries

**Example Prisma Schema:**
```prisma
model Entity {
  canonical_activities   String[]   @default([])
  canonical_roles        String[]   @default([])
  canonical_place_types  String[]   @default([])
  canonical_access       String[]   @default([])
}
```

**Example Query (Prisma):**
```typescript
// Find all entities that provide tennis or padel
const entities = await prisma.entity.findMany({
  where: {
    canonical_activities: {
      hasSome: ["tennis", "padel"]
    }
  }
});
```

**Example Query (SQL):**
```sql
-- Find entities with tennis AND padel
SELECT * FROM "Entity"
WHERE canonical_activities @> ARRAY['tennis', 'padel'];

-- Find entities with tennis OR padel
SELECT * FROM "Entity"
WHERE canonical_activities && ARRAY['tennis', 'padel'];
```

### Extraction Contract: Who Populates Canonical Dimensions?

**Phase 1 (Extractors):**
- Return ONLY schema primitives + raw observations
- MUST NOT emit `canonical_*` fields

**Phase 2 (Lens Application):**
- Populate canonical dimensions using Lens `mapping_rules`
- Apply pattern matching to `raw_categories` and raw text fields
- Example:
  ```yaml
  mapping_rules:
    - pattern: "(?i)tennis|racket sports"
      dimension: canonical_activities
      value: tennis
      confidence: 0.95
  ```

**Current Implementation Status:**
⚠️ Lens Application (Phase 2) is **partially implemented**. Extractors currently don't populate canonical dimensions from lens mapping rules. See `docs/target/architecture.md` Section 4.2 (Extraction Contract) for full pipeline specification.

---

## Modules System

### Purpose

Modules provide **namespaced structured data** for vertical-specific attributes that don't fit the universal schema. They are stored as JSONB in the `modules` field.

**Key Principle:** Modules are triggered by Lens rules based on `entity_class` and canonical dimension values.

### Module Structure

```json
{
  "core": {
    "entity_id": "cm5xyz...",
    "entity_name": "The Padel Club Edinburgh",
    "slug": "padel-club-edinburgh"
  },
  "location": {
    "street_address": "123 Example St",
    "city": "Edinburgh",
    "postcode": "EH1 2AB",
    "latitude": 55.9533,
    "longitude": -3.1883
  },
  "contact": {
    "phone": "+441315551234",
    "email": "info@padelclub.com",
    "website_url": "https://padelclub.com"
  },
  "sports_facility": {
    "court_count": 4,
    "court_types": ["indoor_padel", "outdoor_padel"],
    "equipment_rental": true,
    "coaching_available": true
  }
}
```

### Universal Modules (All Entity Types)

These modules are always present:

1. **`core`**: `{entity_id, entity_name, slug}`
2. **`location`**: `{street_address, city, postcode, latitude, longitude}`
3. **`contact`**: `{phone, email, website_url, social_media}`
4. **`hours`**: `{opening_hours, special_hours}`

### Vertical-Specific Modules (Lens-Triggered)

These modules are added based on Lens `module_triggers` rules:

#### `sports_facility`
**Triggered When:** `canonical_activities` contains sports-related values (e.g., `tennis`, `padel`, `squash`)

**Fields:**
```json
{
  "court_count": 4,
  "court_types": ["indoor_padel", "outdoor_padel"],
  "indoor_outdoor": "both",
  "equipment_rental": true,
  "coaching_available": true,
  "membership_required": false,
  "booking_system": "https://booking.example.com"
}
```

#### `fitness_facility`
**Triggered When:** `canonical_activities` contains fitness-related values (e.g., `yoga`, `pilates`, `strength_training`)

**Fields:**
```json
{
  "class_schedule": "https://classes.example.com",
  "equipment_list": ["free_weights", "cardio_machines", "yoga_mats"],
  "membership_tiers": ["basic", "premium", "vip"],
  "personal_training": true
}
```

#### `hospitality_venue`
**Triggered When:** `canonical_place_types` contains `restaurant`, `cafe`, `bar`

**Fields:**
```json
{
  "cuisine_types": ["italian", "mediterranean"],
  "dietary_options": ["vegetarian", "vegan", "gluten_free"],
  "price_range": "$$",
  "booking_required": true,
  "outdoor_seating": true
}
```

#### `retail_store`
**Triggered When:** `canonical_roles` contains `sells_goods`

**Fields:**
```json
{
  "product_categories": ["sports_equipment", "clothing"],
  "brands_carried": ["Wilson", "Head", "Babolat"],
  "payment_methods": ["cash", "card", "contactless"],
  "online_shop": "https://shop.example.com"
}
```

### Module Trigger Logic (from `lens.yaml`)

```yaml
module_triggers:
  - when:
      dimension: canonical_activities
      values: [tennis, padel, squash]
    add_modules: [sports_facility]

  - when:
      dimension: canonical_place_types
      values: [restaurant, cafe, bar]
    add_modules: [hospitality_venue]

  - when:
      dimension: canonical_roles
      values: [sells_goods]
    add_modules: [retail_store]
```

### Database Implementation

**Postgres Type:** `JSONB` (binary JSON for efficient indexing)

**Example Prisma Schema:**
```prisma
model Entity {
  modules   Json  // JSONB in PostgreSQL
}
```

**Example Query (Prisma):**
```typescript
// Find entities with sports_facility module
const entities = await prisma.entity.findMany({
  where: {
    modules: {
      path: ['sports_facility'],
      not: Prisma.JsonNull
    }
  }
});

// Find entities with 4+ courts
const entities = await prisma.entity.findMany({
  where: {
    modules: {
      path: ['sports_facility', 'court_count'],
      gte: 4
    }
  }
});
```

**Example Query (SQL):**
```sql
-- Find entities with sports_facility module
SELECT * FROM "Entity"
WHERE modules ? 'sports_facility';

-- Find entities with 4+ courts
SELECT * FROM "Entity"
WHERE (modules->'sports_facility'->>'court_count')::int >= 4;
```

---

## Pipeline Tables

### Data Flow Overview

```
Query
  ↓
OrchestrationRun (tracks query execution)
  ↓
RawIngestion (stores raw JSON from connectors)
  ↓
ExtractedEntity (structured extraction output)
  ↓
Entity (final published record)
```

### OrchestrationRun

Tracks multi-source query execution.

**Fields:**
- `id` (PK): Auto-generated CUID
- `query`: Original user query (e.g., "padel courts in Edinburgh")
- `ingestion_mode`: `discover_many`, `verify_one`, `enrich_existing`
- `status`: `in_progress`, `completed`, `failed`
- `candidates_found`: Number of entities discovered
- `accepted_entities`: Number of entities persisted to `Entity` table
- `budget_spent_usd`: Cost tracking (connector API costs + LLM costs)
- `metadata_json`: Additional orchestration metadata (connector timing, errors)
- `createdAt` / `updatedAt`: Timestamps

**Relationships:**
- `OrchestrationRun` 1→N `RawIngestion`

### RawIngestion

Stores raw JSON data from connectors (Serper, GooglePlaces, OSM, etc.).

**Fields:**
- `id` (PK): Auto-generated CUID
- `source`: Connector name (e.g., `serper`, `google_places`, `osm`)
- `source_url`: Original URL or query that generated this data
- `file_path`: Path to raw JSON file (`engine/data/raw/<source>/<timestamp>_<id>.json`)
- `status`: `success`, `failed`, `pending`
- `hash`: Content hash for deduplication (prevents duplicate ingestion)
- `metadata_json`: Additional metadata (API rate limits, request timing)
- `orchestration_run_id` (FK): Link to parent `OrchestrationRun` (nullable for backward compatibility)
- `ingested_at`: Ingestion timestamp

**Relationships:**
- `RawIngestion` N→1 `OrchestrationRun`
- `RawIngestion` 1→N `ExtractedEntity`
- `RawIngestion` 1→N `FailedExtraction`

**Deduplication:**
Raw ingestion records are deduplicated by content hash. If the same data is ingested twice (e.g., same query re-run), the existing `RawIngestion` record is reused.

### ExtractedEntity

Structured extraction output from raw ingestion data.

**Fields:**
- `id` (PK): Auto-generated CUID
- `raw_ingestion_id` (FK): Link to source `RawIngestion`
- `source`: Connector name (redundant with `RawIngestion.source` for query optimization)
- `entity_class`: Universal classification (`place`, `person`, `organization`, `event`, `thing`)
- `attributes`: JSON string containing structured attributes (e.g., `{"entity_name": "...", "street_address": "..."}`)
- `discovered_attributes`: JSON string containing extra attributes not in core schema
- `external_ids`: JSON string containing external system IDs (e.g., `{"google": "ChIJ...", "osm": "123456"}`)
- `extraction_hash`: Content hash for deduplication (detects duplicate entities from different sources)
- `model_used`: LLM model identifier if LLM extraction was used (e.g., `claude-sonnet-4.5-20250929`)
- `createdAt` / `updatedAt`: Timestamps

**Relationships:**
- `ExtractedEntity` N→1 `RawIngestion`
- `ExtractedEntity` N→1 `Entity` (via merge/finalization)

**Extraction Contract:**
- **Phase 1 (Extractors):** Populate `attributes`, `discovered_attributes`, `external_ids` with schema primitives only
- **Phase 2 (Lens Application):** Canonical dimensions and modules are populated during finalization

### Entity

Final published record (see [Entity Model](#entity-model) section for full details).

**Relationships:**
- `Entity` N→1 `ExtractedEntity` (many-to-one: multiple `ExtractedEntity` records can merge into one `Entity`)
- `Entity` 1→N `EntityRelationship` (source of relationships)
- `Entity` 1→N `EntityRelationship` (target of relationships)
- `Entity` 1→N `LensEntity` (membership in vertical lenses)
- `Entity` 1→N `MergeConflict` (conflicts encountered during merge)

### FailedExtraction

Tracks extraction failures for retry and debugging.

**Fields:**
- `id` (PK): Auto-generated CUID
- `raw_ingestion_id` (FK): Link to failed `RawIngestion`
- `source`: Connector name
- `error_message`: Error description (e.g., "LLM extraction timeout")
- `error_details`: Detailed error trace (stack trace, LLM response)
- `retry_count`: Number of retry attempts
- `last_attempt_at`: Last retry timestamp
- `createdAt` / `updatedAt`: Timestamps

**Relationships:**
- `FailedExtraction` N→1 `RawIngestion`

### MergeConflict

Tracks conflicts encountered during entity merge (when multiple sources provide conflicting values for the same field).

**Fields:**
- `id` (PK): Auto-generated CUID
- `field_name`: Field with conflict (e.g., `phone`)
- `conflicting_values`: JSON array of conflicting values (e.g., `["+441315551234", "+441315559999"]`)
- `winner_source`: Source that won conflict resolution (e.g., `google_places`)
- `winner_value`: Final value selected
- `trust_difference`: Trust delta between sources (higher trust source wins)
- `severity`: Conflict severity score (0.0-1.0)
- `entity_id` (FK): Link to `Entity` (nullable)
- `resolved`: Conflict resolution status (true if resolved by human/automated process)
- `resolution_notes`: Human notes on resolution
- `createdAt` / `updatedAt`: Timestamps

**Relationships:**
- `MergeConflict` N→1 `Entity`

**Trust Hierarchy (defined in `engine/extraction/merging.py`):**
```python
TRUST_LEVELS = {
    "google_places": 10,  # Highest trust
    "osm": 8,
    "sport_scotland": 7,
    "serper": 5,
    "tavily": 5,
    "overpass": 4,
}
```

### EntityRelationship

Tracks relationships between entities (e.g., coach teaches at venue, player plays at club).

**Fields:**
- `id` (PK): Auto-generated CUID
- `sourceEntityId` (FK): Source entity
- `targetEntityId` (FK): Target entity
- `type`: Relationship type (e.g., `teaches_at`, `plays_at`, `part_of`, `member_of`)
- `confidence`: Confidence score (0.0-1.0)
- `source`: Connector that discovered relationship
- `createdAt` / `updatedAt`: Timestamps

**Relationships:**
- `EntityRelationship` N→1 `Entity` (source)
- `EntityRelationship` N→1 `Entity` (target)

**Example Queries:**
```typescript
// Find all coaches at a venue
const coaches = await prisma.entityRelationship.findMany({
  where: {
    targetEntityId: venueId,
    type: "teaches_at"
  },
  include: {
    sourceEntity: true
  }
});
```

### LensEntity

Junction table tracking entity membership in vertical lenses.

**Fields:**
- `lensId` (PK1): Lens identifier (e.g., `edinburgh_finds_padel`)
- `entityId` (PK2, FK): Entity identifier
- `createdAt`: Membership timestamp

**Relationships:**
- `LensEntity` N→1 `Entity`

**Purpose:** Allows entities to be members of multiple verticals (e.g., a sports center might be in both "Padel" and "Tennis" lenses).

### ConnectorUsage

Tracks daily connector API usage for rate limit monitoring.

**Fields:**
- `id` (PK): Auto-generated CUID
- `connector_name`: Connector name (e.g., `serper`, `google_places`)
- `date`: Date (PostgreSQL `DATE` type)
- `request_count`: Number of requests made on this date
- `createdAt` / `updatedAt`: Timestamps

**Unique Constraint:** `(connector_name, date)`

**Purpose:** Rate limit monitoring and budget tracking.

---

## Indexes & Performance

### Primary Indexes

#### Entity Table Indexes
```prisma
model Entity {
  @@index([entity_name])        // Name search
  @@index([entity_class])       // Filter by type
  @@index([slug])               // Unique slug lookup (also @@unique)
  @@index([city])               // Location filtering
  @@index([postcode])           // Postcode search
  @@index([latitude, longitude]) // Geospatial queries
  @@index([createdAt])          // Recent entities
  @@index([updatedAt])          // Recently modified
}
```

#### GIN Indexes for Canonical Dimensions

**Purpose:** Fast containment queries on TEXT[] arrays

**Implementation:**
```sql
-- Auto-generated by Prisma during migration
CREATE INDEX "idx_canonical_activities_gin" ON "Entity" USING GIN (canonical_activities);
CREATE INDEX "idx_canonical_roles_gin" ON "Entity" USING GIN (canonical_roles);
CREATE INDEX "idx_canonical_place_types_gin" ON "Entity" USING GIN (canonical_place_types);
CREATE INDEX "idx_canonical_access_gin" ON "Entity" USING GIN (canonical_access);
```

**Query Performance:**
- **`@>` (contains):** O(log n) with GIN index
- **`&&` (overlaps):** O(log n) with GIN index
- **`hasSome` (Prisma):** Translates to `&&` operator

**Example Query Patterns:**
```typescript
// Fast: Uses GIN index
const entities = await prisma.entity.findMany({
  where: {
    canonical_activities: {
      hasSome: ["tennis", "padel"]
    }
  }
});

// Fast: Uses GIN index
const entities = await prisma.entity.findMany({
  where: {
    canonical_activities: {
      hasEvery: ["tennis", "coaching"]
    }
  }
});
```

#### Pipeline Table Indexes
```prisma
model RawIngestion {
  @@index([source])
  @@index([status])
  @@index([hash])              // Deduplication
  @@index([ingested_at])       // Time-based queries
  @@index([orchestration_run_id])
  @@index([source, status])    // Composite for connector health
  @@index([status, ingested_at]) // Composite for pending tasks
}

model ExtractedEntity {
  @@index([raw_ingestion_id])
  @@index([source])
  @@index([entity_class])
  @@index([extraction_hash])   // Deduplication
  @@index([source, entity_class]) // Composite for source analysis
  @@index([createdAt])         // Time-based queries
}
```

### Query Optimization Patterns

#### 1. Faceted Filtering (Canonical Dimensions)
```typescript
// Combine multiple facets
const entities = await prisma.entity.findMany({
  where: {
    canonical_activities: {
      hasSome: ["tennis", "padel"]
    },
    canonical_access: {
      hasSome: ["pay_and_play"]
    },
    city: "Edinburgh"
  }
});
```

#### 2. Geospatial Queries
```typescript
// Find entities within bounding box
const entities = await prisma.entity.findMany({
  where: {
    latitude: {
      gte: minLat,
      lte: maxLat
    },
    longitude: {
      gte: minLng,
      lte: maxLng
    }
  }
});
```

#### 3. Module-Based Queries
```typescript
// Find entities with specific module
const entities = await prisma.entity.findMany({
  where: {
    modules: {
      path: ['sports_facility'],
      not: Prisma.JsonNull
    }
  }
});
```

#### 4. Full-Text Search (Future)
```sql
-- Add tsvector column for full-text search
ALTER TABLE "Entity" ADD COLUMN search_vector tsvector;

-- Update search vector
UPDATE "Entity" SET search_vector =
  to_tsvector('english',
    coalesce(entity_name, '') || ' ' ||
    coalesce(summary, '') || ' ' ||
    coalesce(description, '')
  );

-- Create GIN index
CREATE INDEX "idx_entity_search_vector" ON "Entity" USING GIN (search_vector);
```

---

## Schema Generation

### Generation Workflow

```
1. Edit YAML schema
   └─ engine/config/schemas/entity.yaml

2. Validate YAML
   └─ python -m engine.schema.generate --validate

3. Generate Python FieldSpecs
   └─ engine/schema/entity.py (DO NOT EDIT)

4. Generate Prisma schema
   └─ web/prisma/schema.prisma (DO NOT EDIT)
   └─ engine/prisma/schema.prisma (DO NOT EDIT)

5. Generate TypeScript interfaces
   └─ web/lib/types/generated/entity.ts (DO NOT EDIT)

6. Apply to database
   └─ cd web && npx prisma db push (dev)
   └─ cd web && npx prisma migrate dev (prod)
```

### YAML Schema Structure

```yaml
schema:
  name: Entity
  description: Base schema for all entity types
  extends: null

fields:
  - name: entity_name
    type: string
    description: Official name of the entity
    nullable: false
    required: true
    index: true
    python:
      validators:
        - non_empty
      extraction_required: true
    prisma:
      name: entity_name
      type: "String"
    search:
      category: identity
      keywords:
        - name
        - called
```

### Field Attributes

#### Core Attributes
- **`name`**: Field name (Python/Prisma compatible)
- **`type`**: Data type (`string`, `integer`, `float`, `boolean`, `datetime`, `json`, `list[string]`)
- **`description`**: Human-readable description
- **`nullable`**: Allow NULL values
- **`required`**: Required for LLM extraction
- **`default`**: Default value
- **`unique`**: Unique constraint
- **`index`**: Create database index
- **`primary_key`**: Primary key field
- **`exclude`**: Exclude from LLM extraction (auto-generated or engine-populated)

#### Python-Specific Attributes
```yaml
python:
  validators:
    - non_empty
    - e164_phone
    - postcode_uk
    - url_http
  extraction_required: true
  extraction_name: website  # Different name in extraction
  default: "default_factory=list"
  sa_column: "Column(ARRAY(String))"  # SQLAlchemy override
  type_annotation: "Dict[str, Any]"
```

#### Prisma-Specific Attributes
```yaml
prisma:
  name: id  # Different name in Prisma
  type: "String"
  attributes:
    - "@id"
    - "@default(cuid())"
    - "@unique"
```

#### Search Attributes
```yaml
search:
  category: identity  # Category for LLM prompt grouping
  keywords:
    - name
    - called
    - named
```

### Regeneration Commands

```bash
# Full regeneration
python -m engine.schema.generate --all

# Validate only (no generation)
python -m engine.schema.generate --validate

# Generate specific targets
python -m engine.schema.generate --python
python -m engine.schema.generate --prisma
python -m engine.schema.generate --typescript
```

### Generated File Markers

All generated files contain a header to prevent manual editing:

```python
# ============================================================
# GENERATED FILE - DO NOT EDIT
# ============================================================
# This file is automatically generated from YAML schemas.
# Source: engine/config/schemas/entity.yaml
# Generated: 2026-02-03 09:13:48
```

---

## Data Integrity

### Determinism and Idempotency

**Invariant 4 (from `docs/target/system-vision.md`):**
> Given the same inputs and lens contract, the system produces identical outputs.

**Database Implications:**
1. **Content Hashing**: `RawIngestion.hash` and `ExtractedEntity.extraction_hash` prevent duplicate data
2. **Deterministic Merge**: Trust-based conflict resolution (no randomness)
3. **Idempotent Upserts**: Re-running same query updates existing entities (no duplicates)

### Validation Layers

#### 1. YAML Schema Validation
```bash
python -m engine.schema.generate --validate
```
- Ensures YAML schemas are well-formed
- Validates field types and constraints
- Checks for invalid Prisma/Python mappings

#### 2. Pydantic Validation (Python)
```python
from engine.schema.entity import EntityFieldSpec

# Pydantic validates at runtime
entity = EntityFieldSpec(
    entity_name="The Padel Club",
    entity_class="place",
    phone="+441315551234"  # Must be E.164 format
)
```

#### 3. Prisma Validation (TypeScript)
```typescript
// Prisma validates at compile time
await prisma.entity.create({
  data: {
    entity_name: "The Padel Club",
    slug: "padel-club",  // Must be unique
    entity_class: "place"
  }
});
```

#### 4. Database Constraints
```sql
-- Unique constraints
ALTER TABLE "Entity" ADD CONSTRAINT "Entity_slug_key" UNIQUE (slug);

-- Check constraints (future)
ALTER TABLE "Entity" ADD CONSTRAINT "check_entity_class"
  CHECK (entity_class IN ('place', 'person', 'organization', 'event', 'thing'));
```

### Provenance Tracking

Every entity records its data lineage:

```json
{
  "source_info": {
    "primary_source": "google_places",
    "contributing_sources": ["serper", "osm"],
    "extraction_method": "llm",
    "extraction_timestamp": "2026-02-08T10:30:00Z",
    "urls": [
      "https://maps.google.com/...",
      "https://www.openstreetmap.org/..."
    ]
  },
  "field_confidence": {
    "entity_name": 1.0,
    "street_address": 0.95,
    "phone": 0.85
  },
  "external_ids": {
    "google": "ChIJxyz...",
    "osm": "123456",
    "facebook": "padelclub"
  }
}
```

### Conflict Resolution

**Trust Hierarchy (from `engine/extraction/merging.py`):**
```python
TRUST_LEVELS = {
    "google_places": 10,
    "osm": 8,
    "sport_scotland": 7,
    "serper": 5,
    "tavily": 5,
    "overpass": 4,
}
```

**Merge Rules:**
1. **Higher trust wins** (e.g., `google_places` beats `serper`)
2. **Missingness filtering** (don't overwrite real values with NULL)
3. **Conflict logging** (all conflicts recorded in `MergeConflict` table)

**Example Conflict:**
```json
{
  "field_name": "phone",
  "conflicting_values": ["+441315551234", "+441315559999"],
  "winner_source": "google_places",
  "winner_value": "+441315551234",
  "trust_difference": 5,
  "severity": 0.8
}
```

---

## Migrations

### Development Workflow

```bash
# 1. Edit YAML schema
vim engine/config/schemas/entity.yaml

# 2. Regenerate Prisma schema
python -m engine.schema.generate --all

# 3. Push to development database (no migration files)
cd web
npx prisma db push

# 4. Verify in database
npx prisma studio
```

### Production Workflow

```bash
# 1. Edit YAML schema
vim engine/config/schemas/entity.yaml

# 2. Regenerate Prisma schema
python -m engine.schema.generate --all

# 3. Create migration
cd web
npx prisma migrate dev --name add_canonical_dimensions

# 4. Review migration SQL
cat prisma/migrations/<timestamp>_add_canonical_dimensions/migration.sql

# 5. Apply to production
npx prisma migrate deploy
```

### Migration Best Practices

#### 1. Always Create Migrations for Production
```bash
# ❌ BAD (production)
npx prisma db push

# ✅ GOOD (production)
npx prisma migrate dev --name descriptive_name
npx prisma migrate deploy
```

#### 2. Test Migrations on Seed Data
```bash
# 1. Create migration
npx prisma migrate dev --name add_field

# 2. Seed database
npx prisma db seed

# 3. Verify data integrity
npm run test:integration
```

#### 3. Backward Compatibility
When adding new fields, use default values to avoid breaking existing data:

```prisma
model Entity {
  // ✅ GOOD: Default value prevents NULL errors
  canonical_activities String[] @default([])

  // ❌ BAD: Required field breaks existing records
  required_field String
}
```

#### 4. Handle Array Field Migrations
When adding new canonical dimensions:

```sql
-- Migration: add canonical_roles field
ALTER TABLE "Entity" ADD COLUMN "canonical_roles" TEXT[] DEFAULT '{}';

-- Create GIN index
CREATE INDEX "idx_canonical_roles_gin" ON "Entity" USING GIN (canonical_roles);
```

### Common Migration Scenarios

#### Scenario 1: Add New Canonical Dimension
```yaml
# 1. Edit entity.yaml
fields:
  - name: canonical_certifications
    type: list[string]
    description: "Professional certifications (opaque values)"
    nullable: true
    exclude: true
    python:
      sa_column: "Column(ARRAY(String))"
      default: "default_factory=list"
    prisma:
      type: "String[]"
      attributes:
        - "@default([])"
```

```bash
# 2. Regenerate
python -m engine.schema.generate --all

# 3. Create migration
cd web
npx prisma migrate dev --name add_canonical_certifications
```

#### Scenario 2: Add New Module
No database migration required! Modules are stored in JSONB.

```yaml
# 1. Edit lens.yaml
module_triggers:
  - when:
      dimension: canonical_activities
      values: [wine_tasting]
    add_modules: [winery]
```

```yaml
# 2. Define module schema in lens.yaml
module_schemas:
  winery:
    vineyard_size_hectares: float
    grape_varieties: list[string]
    wine_types: list[string]
    tasting_room: boolean
```

#### Scenario 3: Rename Field
```prisma
// ❌ BAD: Breaks existing data
model Entity {
  new_name String
}

// ✅ GOOD: Multi-step migration
// Step 1: Add new field with default
model Entity {
  old_name String?
  new_name String?
}

// Step 2: Backfill data
UPDATE "Entity" SET new_name = old_name WHERE new_name IS NULL;

// Step 3: Make new field required, drop old field
model Entity {
  new_name String
}
```

### Prisma Studio (Database GUI)

```bash
# Launch Prisma Studio
cd web
npx prisma studio

# Opens http://localhost:5555
```

**Features:**
- Browse all tables
- Edit records (use with caution)
- View relationships
- Execute queries

---

## Appendix: Key File References

### Schema Definitions
- **YAML Schema:** `engine/config/schemas/entity.yaml`
- **Python FieldSpecs:** `engine/schema/entity.py` (generated)
- **Prisma Schema (Web):** `web/prisma/schema.prisma` (generated)
- **Prisma Schema (Engine):** `engine/prisma/schema.prisma` (generated)
- **TypeScript Interfaces:** `web/lib/types/generated/entity.ts` (generated)

### Schema Generation
- **Generator Entry Point:** `engine/schema/generate.py`
- **Python Generator:** `engine/schema/generators/python.py`
- **Prisma Generator:** `engine/schema/generators/prisma.py`
- **TypeScript Generator:** `engine/schema/generators/typescript.py`

### Pipeline Components
- **Entity Finalizer:** `engine/orchestration/entity_finalizer.py`
- **Entity Merger:** `engine/extraction/merging.py`
- **Slug Generator:** `engine/extraction/deduplication.py`
- **Orchestrator:** `engine/orchestration/orchestrator.py`

### Architectural Authority
- **System Vision:** `docs/target/system-vision.md` (immutable invariants)
- **Runtime Architecture:** `docs/target/architecture.md` (pipeline specification)

---

**End of DATABASE.md**
