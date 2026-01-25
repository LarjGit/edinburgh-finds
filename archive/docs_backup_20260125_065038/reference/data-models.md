# Data Models Reference

This document describes the core data models used in Edinburgh Finds. The schema is generated from YAML definitions and managed via Prisma.

## Core Entities

### Entity
The primary model representing a discovered place, person, or thing.
- **Fields**:
    - `id`: Unique CUID.
    - `entity_name`: Display name.
    - `entity_class`: High-level classification.
    - `slug`: URL-friendly identifier.
    - `attributes`: Narrative description or key-value pairs.
    - `modules`: JSON storage for dynamic domain-specific data.
    - **Location**: `street_address`, `city`, `postcode`, `latitude`, `longitude`.
    - **Contact**: `phone`, `email`, `website_url`, social links.
    - **Metadata**: `opening_hours`, `source_info`, `field_confidence`.
- **Relationships**:
    - `outgoingRelationships`: Relationships where this entity is the source.
    - `incomingRelationships`: Relationships where this entity is the target.
    - `lensMemberships`: Lenses this entity belongs to.

### EntityRelationship
Represents a typed connection between two entities.
- **Types**: `teaches_at`, `plays_at`, `part_of`, etc.
- **Fields**: `confidence` score, `source` (provenance).

### LensEntity
A join model that associates an `Entity` with a specific `Lens` (domain).

## Ingestion Models

### RawIngestion
Stores records of data collected from external sources.
- **Fields**: `source`, `source_url`, `file_path` (local storage reference), `status`, `hash`.
- **Purpose**: Provides a durable audit trail of all data that has entered the system.

### ExtractedEntity
Represents a temporary, source-specific extraction before it is merged into a canonical `Entity`.
- **Fields**: `extraction_hash`, `model_used` (LLM version).

### FailedExtraction
Logs details about failed attempts to extract structured data from raw ingestion.
- **Fields**: `error_message`, `error_details`, `retry_count`.

### MergeConflict
Captured when automated merging cannot resolve a field value with high confidence or when trust levels are tied.
- **Fields**: `field_name`, `conflicting_values`, `winner_source`, `severity`.

## Schema Management
The schema is **generated** and should not be edited directly in `schema.prisma`.
1. **Source**: `engine/config/schemas/*.yaml`
2. **Generation**: `python -m engine.schema.generate`
3. **Migration**: `npx prisma migrate dev`

---
*Evidence: engine/schema.prisma analysis.*
