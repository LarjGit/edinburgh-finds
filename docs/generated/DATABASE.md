# Database Architecture

**Generated:** 2026-02-06
**Status:** Auto-generated documentation

---

## Overview

Edinburgh Finds uses **PostgreSQL** (hosted on Supabase) as its primary data store. The database schema is auto-generated from YAML definitions in `engine/config/schemas/entity.yaml` — never edit the Prisma schema directly.

The Prisma ORM is used by both the Python engine (Prisma Client Python) and the Next.js frontend (Prisma Client JS).

---

## Entity-Relationship Diagram

```mermaid
erDiagram
    OrchestrationRun ||--o{ RawIngestion : "triggers"
    RawIngestion ||--o{ ExtractedEntity : "produces"
    RawIngestion ||--o{ FailedExtraction : "records failures"
    Entity ||--o{ EntityRelationship : "source of"
    Entity ||--o{ EntityRelationship : "target of"
    Entity ||--o{ LensEntity : "belongs to lenses"

    OrchestrationRun {
        string id PK
        string query
        string ingestion_mode
        string status
        int candidates_found
        int accepted_entities
        float budget_spent_usd
        string metadata_json
        datetime createdAt
    }

    RawIngestion {
        string id PK
        string source
        string source_url
        string file_path
        string status
        datetime ingested_at
        string hash
        string metadata_json
        string orchestration_run_id FK
    }

    ExtractedEntity {
        string id PK
        string raw_ingestion_id FK
        string source
        string entity_class
        string attributes
        string discovered_attributes
        string external_ids
        string extraction_hash
        string model_used
    }

    FailedExtraction {
        string id PK
        string raw_ingestion_id FK
        string source
        string error_message
        string error_details
        int retry_count
        datetime last_attempt_at
    }

    Entity {
        string id PK
        string entity_name
        string entity_class
        string slug UK
        string summary
        string description
        string_array raw_categories
        string_array canonical_activities
        string_array canonical_roles
        string_array canonical_place_types
        string_array canonical_access
        json discovered_attributes
        json modules
        string street_address
        string city
        string postcode
        float latitude
        float longitude
        string phone
        string email
        string website_url
        json opening_hours
        json source_info
        json field_confidence
        json external_ids
    }

    EntityRelationship {
        string id PK
        string sourceEntityId FK
        string targetEntityId FK
        string type
        float confidence
        string source
    }

    LensEntity {
        string lensId PK
        string entityId PK_FK
    }

    MergeConflict {
        string id PK
        string field_name
        string conflicting_values
        string winner_source
        string winner_value
        int trust_difference
        float severity
        string entity_id
        boolean resolved
    }

    ConnectorUsage {
        string id PK
        string connector_name
        date date
        int request_count
    }
```

---

## Model Descriptions

### Entity (Core Model)

The central model representing a real-world entity (place, person, organization, event, or thing).

**Key fields:**
- `entity_name` — Official name of the entity
- `entity_class` — Universal classification: `place`, `person`, `organization`, `event`, `thing`
- `slug` — URL-safe unique identifier (auto-generated)
- `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access` — Multi-valued dimension arrays stored as PostgreSQL `TEXT[]` with GIN indexes for fast faceted filtering
- `modules` — JSONB structure containing namespaced module data (e.g., `{sports_facility: {padel_courts: {total: 6}}}`)
- `discovered_attributes` — JSONB bucket for extra attributes not in the schema
- `source_info` — Provenance metadata tracking contributing sources
- `field_confidence` — Per-field confidence scores for merge decisions
- `external_ids` — External system identifiers (Google Place ID, OSM ID, etc.)

### RawIngestion

Immutable record of raw data fetched from an external source.

**Purpose:** Preserves the exact data received from connectors, enabling replay and debugging.

**Key fields:**
- `source` — Connector that produced this data (e.g., "serper", "google_places")
- `file_path` — Path to raw JSON file on disk (`engine/data/raw/<source>/<timestamp>_<id>.json`)
- `hash` — Content hash for ingestion-level deduplication
- `orchestration_run_id` — Links to the parent orchestration run

### ExtractedEntity

Structured entity data extracted from a RawIngestion record.

**Purpose:** Intermediate pipeline artifact between raw data and the final Entity.

**Key fields:**
- `raw_ingestion_id` — Links back to the source RawIngestion
- `source` — Which connector produced the original data
- `attributes` — JSON string of extracted schema primitives
- `discovered_attributes` — JSON string of non-schema attributes
- `extraction_hash` — Hash for extraction-level deduplication

### OrchestrationRun

Tracks a complete orchestration execution from query to entity persistence.

**Key fields:**
- `query` — The original user query
- `ingestion_mode` — Execution mode (e.g., "discover_many", "verify_one")
- `status` — Current state: "in_progress", "completed", "failed"
- `budget_spent_usd` — Total API cost for this run

### EntityRelationship

Represents relationships between entities (e.g., "teaches_at", "plays_at", "part_of").

### LensEntity

Join table linking entities to lenses, enabling multi-lens entity membership.

### MergeConflict

Records conflicts encountered during multi-source merge, including which value won and why.

### ConnectorUsage

Tracks daily API usage per connector for rate limiting and cost monitoring.

### FailedExtraction

Records extraction failures with error details and retry metadata.

---

## Indexing Strategy

The database uses strategic indexing for performance:

| Table | Index | Purpose |
|-------|-------|---------|
| Entity | `entity_name` | Name search |
| Entity | `entity_class` | Class filtering |
| Entity | `latitude, longitude` | Geo queries |
| Entity | `city`, `postcode` | Location filtering |
| Entity | `canonical_*` (GIN) | Faceted dimension filtering |
| RawIngestion | `hash` | Deduplication lookup |
| RawIngestion | `source, status` | Connector status queries |
| ExtractedEntity | `extraction_hash` | Extraction dedup |

---

## Schema Management

**Single Source of Truth:** `engine/config/schemas/entity.yaml`

```bash
# Validate schemas
python -m engine.schema.generate --validate

# Regenerate all derived schemas
python -m engine.schema.generate --all

# After schema changes, sync to database
cd web && npx prisma migrate dev
```

Generated files (never edit directly):
- `web/prisma/schema.prisma` — Prisma schema for frontend
- `engine/prisma/schema.prisma` — Prisma schema for engine
- `engine/schema/entity.py` — Python FieldSpecs
- `web/lib/types/generated/*.ts` — TypeScript interfaces

---

## Migration Strategy

Migrations are managed through Prisma:

```bash
cd web
npx prisma migrate dev      # Create migration (development)
npx prisma migrate deploy   # Apply migrations (production)
npx prisma db push          # Quick sync without migration file
```

Historical SQLite migrations are preserved in `web/prisma/migrations_sqlite_backup/` for reference. The project migrated from SQLite to PostgreSQL (Supabase).

---

## Related Documentation

- **Schema YAML:** `engine/config/schemas/entity.yaml`
- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Backend:** [BACKEND.md](BACKEND.md) — How the engine interacts with the database
- **Configuration:** [CONFIGURATION.md](CONFIGURATION.md) — DATABASE_URL setup
