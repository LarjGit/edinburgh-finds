Audience: Developers

# Project Management & Core Engine Logic

This section details the high-level project management documentation and the core logic governing data ingestion, schema generation, and the primary entity model.

## Overview

The system is managed through a structured "Conductor" workflow which tracks progress and technical standards. The core engine translates raw ingested data into a unified, lens-aware Entity model using Prisma as the primary ORM.

## Components

### Project Management (`conductor/`)
- **`product.md` / `product-guidelines.md`**: Defines the product vision, core features, and user experience standards.
- **`tech-stack.md`**: Outlines the technologies used (PostgreSQL, Prisma, Python, Next.js, etc.).
- **`tracks.md` / `workflow.md`**: Tracks development progress and defines the standard operating procedures for new features.
- **`code_styleguides/`**: Contains language-specific (Python, React, TypeScript) standards to ensure consistency.

### Engine Core Logic
- **`engine/ingest.py`**: The primary entry point for ingesting validated entity data into the database. It handles field mapping, JSON serialization, and upsert logic.
- **`engine/schema.prisma`**: The source of truth for the database schema. **Note: This file is generated from YAML schemas.**
- **`engine/check_data.py` / `engine/inspect_db.py`**: Utilities for verifying database state and data integrity.

### Tooling Specification
- **`.prune-suite/SPEC.md`**: Specification for the `PRUNE-SUITE` tool, used for automated codebase cleaning and orphan file detection.

## Data Flow

1. **Schema Generation**:
   `YAML Schemas` → `Schema Generator` → `schema.prisma` → `Prisma Client (Python/TS)`

2. **Ingestion Pipeline**:
   `Validated Payload` → `ingest_entity()` → `Field Separation (Core vs Modules)` → `Database Upsert (Entity Table)`

## Configuration Surface

- **Prisma Configuration**:
  - `engine/prisma.config.ts`: Configuration for the Prisma client and generation targets.
- **Engine Requirements**:
  - `engine/requirements.txt`: Defines Python dependencies specific to the engine subsystem (e.g., `prisma`, `pydantic`).

## Public Interfaces

### Ingestion API
Evidence: `engine/ingest.py:27-31`
```python
async def ingest_entity(data: Dict[str, Any]):
    """
    Ingests a single Entity.
    data: Flat dictionary containing all fields.
    """
```

### Database Schema
Evidence: `engine/schema.prisma:36-70`
Key tables:
- `Entity`: Central store for all discovered locations/entities.
- `RawIngestion`: Registry of all raw data files and their sources.
- `LensEntity`: Join table for associating entities with specific vertical lenses.

## Examples

### Schema Regeneration
To update the database schema after modifying YAML definitions:
```bash
python -m engine.schema.generate
npx prisma migrate dev
```

### Manual Ingestion Seed
Evidence: `engine/run_seed.py` (referenced by context)
```bash
python -m engine.run_seed
```

## Edge Cases / Notes
- **Generated Schema**: Never edit `engine/schema.prisma` directly. It is overwritten during the schema generation process from YAML sources.
- **JSON Field Handling**: The ingestion logic carefully separates "CORE_COLUMNS" from module-specific data, which is stored in the `modules` JSONB column.
- **Slug Generation**: If no slug is provided, the engine automatically generates one from the `entity_name`, but adds source-specific prefixes in some workflows to avoid collisions.
