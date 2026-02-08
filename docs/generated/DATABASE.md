# Database Architecture — Universal Entity Extraction Engine

**System:** Universal Entity Extraction Engine
**Application:** Edinburgh Finds (Reference Lens)
**Last Updated:** 2026-02-08

---

## Overview

The database architecture implements a **universal entity schema** that remains stable across all verticals. The engine owns structure, indexing, persistence, and lifecycle behavior. Lenses own the meaning and population rules for all values.

**Core Principles:**

- **Single Source of Truth:** YAML schemas (`engine/config/schemas/*.yaml`) auto-generate Python models, Prisma schemas, and TypeScript interfaces
- **Universal Schema:** All entities conform to one schema regardless of vertical
- **Canonical Dimensions:** Postgres TEXT[] arrays with GIN indexes for faceted filtering
- **Namespaced Modules:** JSONB structures for vertical-specific structured data
- **Provenance Tracking:** Complete audit trail from raw ingestion to final entity

---

## Schema Generation Pipeline

```
engine/config/schemas/*.yaml
          ↓
  Schema Generator
          ↓
    ┌─────────┴─────────┐
    ↓                   ↓
Python FieldSpecs    Prisma Schemas
    ↓                   ↓
engine/schema/      web/prisma/schema.prisma
entity.py
```

**Commands:**

```bash
# Validate schemas before committing
python -m engine.schema.generate --validate

# Regenerate all derived schemas
python -m engine.schema.generate --all

# Apply schema changes to database
cd web && npx prisma db push        # Development
cd web && npx prisma migrate dev    # Production migration
```

**Generated Files (DO NOT EDIT):**

- `engine/schema/entity.py` — Python FieldSpecs
- `web/prisma/schema.prisma` — Prisma schema (frontend)
- `web/lib/types/generated/entity.ts` — TypeScript interfaces

---

## Entity Data Model

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
        Json discovered_attributes "Extra attributes not in core schema"
        Json modules "Namespaced JSONB: {sports_facility: {}, hospitality_venue: {}}"

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
        Json opening_hours "{monday: {open: '05:30', close: '22:00'}, sunday: 'CLOSED'}"

        %% PROVENANCE AND METADATA
        Json source_info "URLs, method, timestamps, notes"
        Json field_confidence "Per-field confidence scores (0.0-1.0)"
        Json external_ids "{google: 'abc123', osm: '456'} - External system identifiers"
        DateTime createdAt "Creation timestamp"
        DateTime updatedAt "Last update timestamp"
    }

    ExtractedEntity {
        string id PK "Auto-generated CUID"
        string raw_ingestion_id FK "Link to source RawIngestion"
        string source "Connector name (serper, google_places, osm, etc.)"
        string entity_class "Universal classification (place, person, organization, event, thing)"
        Json attributes "Structured entity attributes from extraction (Phase 1: primitives only)"
        Json discovered_attributes "Additional discovered fields not in schema"
        Json external_ids "External system identifiers {google: 'id', osm: 'id'}"
        string extraction_hash "Content hash for deduplication (SHA-256)"
        string model_used "LLM model identifier if AI extraction used"
        DateTime createdAt "Extraction timestamp"
        DateTime updatedAt "Last update timestamp"
    }

    RawIngestion {
        string id PK "Auto-generated CUID"
        string source "Connector name (serper, google_places, osm, sport_scotland, etc.)"
        string source_url "Original URL or query"
        string file_path "Path to raw JSON: engine/data/raw/source/timestamp_id.json"
        string status "success, failed, pending"
        string hash "Content hash for deduplication (SHA-256)"
        Json metadata_json "Additional metadata as JSON"
        string orchestration_run_id FK "Link to parent OrchestrationRun (nullable)"
        DateTime ingested_at "Ingestion timestamp"
    }

    OrchestrationRun {
        string id PK "Auto-generated CUID"
        string query "Original user query"
        string ingestion_mode "discover_many, verify_one, etc."
        string status "in_progress, completed, failed"
        int candidates_found "Number of entities discovered"
        int accepted_entities "Number of entities persisted"
        float budget_spent_usd "Cost tracking"
        Json metadata_json "Additional orchestration metadata"
        DateTime createdAt "Run start timestamp"
        DateTime updatedAt "Last update timestamp"
    }

    FailedExtraction {
        string id PK "Auto-generated CUID"
        string raw_ingestion_id FK "Link to failed RawIngestion"
        string source "Connector name"
        string error_message "Error description"
        string error_details "Detailed error trace"
        int retry_count "Number of retry attempts"
        DateTime last_attempt_at "Last retry timestamp"
        DateTime createdAt "Initial failure timestamp"
        DateTime updatedAt "Last update timestamp"
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
        DateTime createdAt "Conflict detected timestamp"
        DateTime updatedAt "Last update timestamp"
    }

    EntityRelationship {
        string id PK "Auto-generated CUID"
        string sourceEntityId FK "Source entity"
        string targetEntityId FK "Target entity"
        string type "Relationship type: teaches_at, plays_at, part_of, etc."
        float confidence "Confidence score (0.0-1.0)"
        string source "Connector that discovered relationship"
        DateTime createdAt "Relationship created timestamp"
        DateTime updatedAt "Last update timestamp"
    }

    LensEntity {
        string lensId PK "Lens identifier"
        string entityId PK,FK "Entity identifier"
        DateTime createdAt "Membership timestamp"
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

---

## Entity Table Structure

The **Entity** table is the primary canonical entity store. All entities from all verticals share this universal schema.

### Identity Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | String | Auto-generated CUID | Primary Key |
| `entity_name` | String | Official name | Required, Indexed |
| `entity_class` | String | Universal classification: place, person, organization, event, thing | Indexed |
| `slug` | String | URL-safe identifier (auto-generated) | Unique, Indexed |
| `summary` | String | Short description summary | Nullable |
| `description` | String | Long-form aggregated evidence | Nullable |

**Classification Rules (Architecture Section 4.1, Stage 8):**

- **place**: Geographic anchoring present (coordinates, street address, city, or postcode)
- **person**: Individual human
- **organization**: Group entity
- **event**: Time-bound occurrence
- **thing**: Everything else

---

### Canonical Dimensions (Multi-Valued Arrays)

Stored as **Postgres TEXT[] arrays** with **GIN indexes** for efficient faceted filtering.

| Dimension | Description | Storage | Index |
|-----------|-------------|---------|-------|
| `canonical_activities` | Activities provided/supported | TEXT[] | GIN |
| `canonical_roles` | Functional roles (provides_facility, sells_goods, etc.) | TEXT[] | GIN |
| `canonical_place_types` | Physical place classifications | TEXT[] | GIN |
| `canonical_access` | Access requirements (membership, pay_and_play, free) | TEXT[] | GIN |

**Engine Guarantees:**

- Arrays are always present (never null)
- Empty array `[]` represents absence of observed values
- Values are opaque identifiers (engine does not interpret)
- No duplicate values within a dimension
- Ordering is stable and deterministic

**Lens Responsibilities:**

- Declare allowed values in canonical registry
- Populate values through mapping rules
- Provide display metadata and presentation semantics

**Query Example (PostgreSQL):**

```sql
-- Find all entities with 'tennis' activity
SELECT * FROM "Entity"
WHERE 'tennis' = ANY(canonical_activities);

-- Find entities with multiple activities
SELECT * FROM "Entity"
WHERE canonical_activities && ARRAY['tennis', 'padel'];
```

---

### Modules (Namespaced JSONB)

The `modules` field stores structured vertical-specific data as **JSONB**.

**Universal Modules (Always Available):**

- `core` — Entity identity (entity_id, entity_name, slug)
- `location` — Geographic data (street_address, city, postcode, latitude, longitude)
- `contact` — Contact information (phone, email, website_url, social_media)
- `hours` — Operating hours (opening_hours, special_hours)
- `amenities` — Facility amenities (parking, accessibility, facilities)
- `time_range` — Temporal validity (event dates, seasonal hours)

**Domain Modules (Lens-Triggered):**

- `sports_facility` — Court counts, types, booking, equipment
- `fitness_facility` — Class schedules, equipment, membership tiers
- `hospitality_venue` — Cuisine types, dietary options, price range
- `retail_store` — Product categories, brands, payment methods

**Example Module Structure:**

```json
{
  "sports_facility": {
    "tennis_courts": {
      "total": 12,
      "indoor": 8,
      "outdoor": 4,
      "surfaces": ["hard_court", "clay"]
    },
    "padel_courts": {
      "total": 3,
      "indoor": 3,
      "covered": true,
      "heated": true
    },
    "booking": {
      "online_booking_available": true,
      "advance_booking_days": 7,
      "booking_url": "https://example.com/book"
    },
    "coaching_available": true,
    "equipment_rental": true
  },
  "amenities": {
    "parking": {
      "available": true,
      "spaces": 50,
      "cost": "free"
    },
    "accessibility": {
      "wheelchair_accessible": true,
      "accessible_parking": true,
      "accessible_changing_rooms": true
    },
    "facilities": ["changing_rooms", "showers", "cafe", "pro_shop"]
  }
}
```

**Module Trigger Logic (from `lens.yaml`):**

```yaml
module_triggers:
  - when:
      dimension: canonical_activities
      values: [tennis]
    add_modules: [sports_facility]

  - when:
      dimension: canonical_place_types
      values: [restaurant]
    add_modules: [hospitality_venue]
```

---

### Location Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `street_address` | String | Full street address | Nullable |
| `city` | String | City or town | Indexed |
| `postcode` | String | UK postcode (e.g., 'SW1A 0AA') | Indexed |
| `country` | String | Country name | Nullable |
| `latitude` | Float | WGS84 decimal degrees | Nullable |
| `longitude` | Float | WGS84 decimal degrees | Nullable |

**Index Strategy:**

```sql
CREATE INDEX idx_entity_city ON "Entity"(city);
CREATE INDEX idx_entity_postcode ON "Entity"(postcode);
CREATE INDEX idx_entity_coordinates ON "Entity"(latitude, longitude);
```

---

### Contact Fields

| Field | Type | Description | Format |
|-------|------|-------------|--------|
| `phone` | String | Primary contact phone | E.164 UK format (+441315397071) |
| `email` | String | Public email address | Standard email |
| `website_url` | String | Official website | HTTP/HTTPS URL |
| `instagram_url` | String | Instagram profile | URL or handle |
| `facebook_url` | String | Facebook page | URL |
| `twitter_url` | String | Twitter/X profile | URL or handle |
| `linkedin_url` | String | LinkedIn company page | URL |

---

### Provenance and Metadata

| Field | Type | Description |
|-------|------|-------------|
| `source_info` | JSON | URLs, method (connector name), timestamps, notes |
| `field_confidence` | JSON | Per-field confidence scores (0.0–1.0) |
| `external_ids` | JSON | External system identifiers (e.g., `{google: 'abc123', osm: '456'}`) |
| `raw_categories` | String[] | Uncontrolled observational labels (NOT indexed) |
| `discovered_attributes` | JSON | Extra attributes not in core schema |
| `createdAt` | DateTime | Creation timestamp (auto-generated) |
| `updatedAt` | DateTime | Last update timestamp (auto-updated) |

**Provenance Guarantees:**

- Never silently discarded
- Survives merges deterministically
- Conflicting provenance preserved (not overwritten)

---

## Pipeline Tables

### RawIngestion

Immutable raw data artifacts from connectors.

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | CUID |
| `source` | String | Connector name (serper, google_places, osm, etc.) |
| `source_url` | String | Original URL or query |
| `file_path` | String | Path to raw JSON: `engine/data/raw/<source>/<timestamp>_<id>.json` |
| `status` | String | success, failed, pending |
| `hash` | String | Content hash (SHA-256) for deduplication |
| `orchestration_run_id` | String | Link to OrchestrationRun (nullable) |
| `ingested_at` | DateTime | Ingestion timestamp |

**Indexes:**

- `source`
- `status`
- `hash`
- `orchestration_run_id`
- Composite: `(source, status)`, `(status, ingested_at)`

---

### ExtractedEntity

Extracted structured data from raw artifacts (Phase 1: primitives only).

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | CUID |
| `raw_ingestion_id` | String | Foreign key to RawIngestion |
| `source` | String | Connector name |
| `entity_class` | String | place, person, organization, event, thing |
| `attributes` | JSON | Schema-aligned primitives (entity_name, latitude, phone, etc.) |
| `discovered_attributes` | JSON | Additional discovered fields |
| `external_ids` | JSON | External system identifiers |
| `extraction_hash` | String | Content hash for deduplication |
| `model_used` | String | LLM model identifier (if AI extraction used) |

**Indexes:**

- `raw_ingestion_id`
- `source`
- `entity_class`
- `extraction_hash`
- Composite: `(source, entity_class)`

---

### OrchestrationRun

Orchestration execution metadata.

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | CUID |
| `query` | String | Original user query |
| `ingestion_mode` | String | discover_many, verify_one, etc. |
| `status` | String | in_progress, completed, failed |
| `candidates_found` | Int | Number of entities discovered |
| `accepted_entities` | Int | Number of entities persisted |
| `budget_spent_usd` | Float | Cost tracking |
| `metadata_json` | JSON | Additional orchestration metadata |

---

### FailedExtraction

Failed extraction tracking for retry logic.

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | CUID |
| `raw_ingestion_id` | String | Foreign key to RawIngestion |
| `source` | String | Connector name |
| `error_message` | String | Error description |
| `error_details` | String | Detailed error trace |
| `retry_count` | Int | Number of retry attempts |
| `last_attempt_at` | DateTime | Last retry timestamp |

---

### MergeConflict

Multi-source merge conflict tracking.

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | CUID |
| `field_name` | String | Field with conflict |
| `conflicting_values` | String | JSON array of conflicting values |
| `winner_source` | String | Source that won conflict resolution |
| `winner_value` | String | Final value selected |
| `trust_difference` | Int | Trust delta between sources |
| `severity` | Float | Conflict severity score |
| `entity_id` | String | Link to Entity (nullable) |
| `resolved` | Boolean | Conflict resolution status |
| `resolution_notes` | String | Human notes on resolution |

---

## Indexing Strategy

### Primary Indexes

**Entity Table:**

```sql
-- Identity
CREATE INDEX idx_entity_name ON "Entity"(entity_name);
CREATE INDEX idx_entity_class ON "Entity"(entity_class);
CREATE UNIQUE INDEX idx_slug ON "Entity"(slug);

-- Location
CREATE INDEX idx_city ON "Entity"(city);
CREATE INDEX idx_postcode ON "Entity"(postcode);
CREATE INDEX idx_coordinates ON "Entity"(latitude, longitude);

-- Canonical Dimensions (GIN for array containment)
CREATE INDEX idx_canonical_activities ON "Entity" USING GIN(canonical_activities);
CREATE INDEX idx_canonical_roles ON "Entity" USING GIN(canonical_roles);
CREATE INDEX idx_canonical_place_types ON "Entity" USING GIN(canonical_place_types);
CREATE INDEX idx_canonical_access ON "Entity" USING GIN(canonical_access);

-- Temporal
CREATE INDEX idx_created_at ON "Entity"(createdAt);
CREATE INDEX idx_updated_at ON "Entity"(updatedAt);
```

**Pipeline Tables:**

```sql
-- RawIngestion
CREATE INDEX idx_raw_ingestion_source ON "RawIngestion"(source);
CREATE INDEX idx_raw_ingestion_status ON "RawIngestion"(status);
CREATE INDEX idx_raw_ingestion_hash ON "RawIngestion"(hash);
CREATE INDEX idx_raw_ingestion_composite ON "RawIngestion"(source, status);

-- ExtractedEntity
CREATE INDEX idx_extracted_entity_source ON "ExtractedEntity"(source);
CREATE INDEX idx_extracted_entity_hash ON "ExtractedEntity"(extraction_hash);
CREATE INDEX idx_extracted_entity_composite ON "ExtractedEntity"(source, entity_class);
```

---

## Migration Strategy

### Development Workflow

```bash
# 1. Edit YAML schema
vim engine/config/schemas/entity.yaml

# 2. Validate changes
python -m engine.schema.generate --validate

# 3. Regenerate derived schemas
python -m engine.schema.generate --all

# 4. Apply to database (development)
cd web && npx prisma db push

# 5. Create migration (production)
cd web && npx prisma migrate dev --name descriptive_migration_name

# 6. Commit changes
git add engine/config/schemas/ web/prisma/ engine/schema/
git commit -m "feat(schema): add new entity field"
```

### Production Migration

```bash
# 1. Review generated migration
cd web && npx prisma migrate dev --create-only

# 2. Test migration
cd web && npx prisma migrate dev

# 3. Deploy to production
cd web && npx prisma migrate deploy
```

---

## Data Integrity Guarantees

**Immutability:**

- `RawIngestion` records are immutable after persistence
- `ExtractedEntity` records are immutable after creation
- `Entity` records may only change through idempotent upsert

**Determinism:**

- Same inputs + lens contract → identical outputs
- No randomness, iteration-order dependence, or time-based behavior
- All tie-breaking is deterministic

**Idempotency:**

- Re-running same execution updates existing entities (no duplicates)
- Upsert keys are stable and deterministic

**Fail-Fast:**

- Invalid lens schema or registry → abort at bootstrap
- Schema violations → abort execution
- Contract boundary violations → architectural defect

---

## Observability

**Traceability:**

- Every entity retains explicit provenance (`source_info`)
- Field-level confidence tracking (`field_confidence`)
- External identifier preservation (`external_ids`)
- Merge conflict auditing (`MergeConflict` table)

**Metrics:**

- Orchestration execution tracking (`OrchestrationRun`)
- Failed extraction monitoring (`FailedExtraction`)
- Connector usage tracking (`ConnectorUsage`)

---

## Key Architectural Constraints

**Engine Purity (Invariant 1):**

- Engine contains ZERO domain knowledge
- No hardcoded values for "Padel", "Wine", "Tennis", etc.
- All semantics live exclusively in Lens YAML configs

**Universal Schema Authority (Invariant 8):**

- Universal schema names are authoritative end-to-end
- No permanent translation layers permitted
- Schema evolution requires explicit migration

**Canonical Dimensions (Architecture Section 5.2):**

- Exactly four canonical dimensions (adding/removing requires architectural review)
- Values are opaque identifiers (no semantic interpretation in engine)
- Populated exclusively by lens mapping rules (Phase 2)

**Extraction Contract (Architecture Section 4.2):**

- **Phase 1 (Extractors):** Emit ONLY primitives + raw observations
- **Phase 2 (Lens Application):** Populate canonical dimensions + modules
- Extractors MUST NOT emit `canonical_*` fields or `modules`

---

## References

- **Schema Authority:** `engine/config/schemas/entity.yaml`
- **Architectural Constitution:** `docs/target/system-vision.md` (Immutable invariants)
- **Runtime Specification:** `docs/target/architecture.md` (Section 5 — Canonical Data Model)
- **Entity Model Diagram:** `docs/generated/diagrams/entity_model.mmd`
- **Prisma Schema:** `web/prisma/schema.prisma` (Generated, do not edit)
