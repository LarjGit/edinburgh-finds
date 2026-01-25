# Subsystem: database

## Purpose
The database subsystem manages persistent data storage, schema evolution, and type-safe data access for the entire Edinburgh Finds platform. It employs a **Meta-Schema** architecture where the single source of truth is a YAML-based schema definition, which is then used to generate database schemas (Prisma), data models (Pydantic), and type definitions (TypeScript/Python) used across the engine and web frontend.

## Key Components

### Schema Definition
- **YAML Schemas** (`engine/config/schemas/`): The single source of truth for all data models. `entity.yaml` defines the core fields for the platform.
- **Schema Parser** (`engine/schema/parser.py`): Parses YAML definitions into internal `SchemaDefinition` objects, validating structure and types.

### Schema Generation Engine
- **Core FieldSpec** (`engine/schema/core.py`): A framework-neutral specification for fields, providing metadata for both database constraints and LLM extraction rules.
- **CLI Tool** (`engine/schema/generate.py`): Orchestrates the generation of all target formats.
- **Generators** (`engine/schema/generators/`):
    - **Prisma Generator** (`prisma.py`): Generates `schema.prisma` files for both the engine (Python) and web (Next.js) targets.
    - **Python Generator** (`python_fieldspec.py`): Generates Python `FieldSpec` objects for runtime use.
    - **Pydantic Generator** (`pydantic_extraction.py`): Generates models specifically tuned for LLM-based data extraction.
    - **TypeScript Generator** (`typescript.py`): Generates TypeScript interfaces and optionally Zod schemas for the frontend.

### Data Access & ORM
- **Prisma** (`engine/schema.prisma`): The primary ORM used for database interactions. It supports PostgreSQL (primary production database) and uses features like text arrays and GIN indexes for efficient faceted search.

## Architecture
The database subsystem follows a **generated-code pattern** to ensure consistency across different languages and frameworks:

1.  **Define:** Developers modify `engine/config/schemas/entity.yaml`.
2.  **Generate:** Running `python -m engine.schema.generate` updates all downstream artifacts.
3.  **Migrate:** `prisma migrate dev` applies changes to the physical database.
4.  **Consume:**
    - The **Ingestion Engine** uses generated Prisma clients to store raw data.
    - The **Extraction Engine** uses generated Pydantic models for structured LLM output.
    - The **Web Frontend** uses generated TypeScript types for type-safe UI development.

## Data Models

### Core Models
- **Entity**: The central model representing venues, people, organizations, etc.
    - Uses Postgres **text arrays** (`canonical_activities`, `canonical_place_types`, etc.) for fast faceted filtering.
    - Contains **JSONB modules** for flexible, namespaced data storage.
    - Supports geographical indexing (Latitude/Longitude).
- **EntityRelationship**: Graph-like storage for links between entities (e.g., "plays_at", "teaches_at").
- **LensEntity**: A join table that maps entities to "Lenses" (curated subsets/views of the data).

### Ingestion & Lifecycle Models
- **RawIngestion**: Stores provenance of data, including source URLs and file paths to raw JSON.
- **ExtractedEntity**: Stores intermediate results of LLM extraction before merging into canonical entities.
- **FailedExtraction**: Tracks errors and retry counts for the extraction pipeline.
- **MergeConflict**: Records conflicts encountered when merging data from multiple sources for human or automated resolution.

## Dependencies

### Internal
- **config**: Consumes YAML schema definitions.
- **engine-extraction**: Provides generated Pydantic models for LLM extraction.
- **lenses**: Used by `LensEntity` to define data subsets.

### External
- **Prisma**: Primary ORM and schema management tool.
- **PostgreSQL**: Production database, utilizing text[] arrays and GIN indexes.
- **PyYAML**: For parsing schema definitions.
- **Pydantic**: For dynamic model creation and validation.

## Evidence
- Schema Source: `engine/config/schemas/entity.yaml`
- Prisma Configuration: `engine/schema.prisma`
- Generation Logic: `engine/schema/generate.py`, `engine/schema/generators/prisma.py`
- Core Models: `engine/schema.prisma:24-154`
- Test Coverage: `tests/query/test_prisma_array_filters.py`
