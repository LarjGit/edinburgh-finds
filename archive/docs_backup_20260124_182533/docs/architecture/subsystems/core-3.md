Audience: Developers

# Engine Configuration & Data Samples

This section details the declarative configuration system that serves as the single source of truth for the entity model, data source integration, and monitoring alerts.

## Overview

The engine relies on a "YAML-first" architecture. The data model, API connections, and extraction rules are defined in YAML files, which are then used to generate database schemas, Pydantic models, and LLM prompts. This ensures consistency across the ingestion and extraction pipelines.

## Components

### Schema Definitions (`engine/config/schemas/`)
- **`entity.yaml`**: The master schema for the `Entity` model. It defines fields, types, indexes, and metadata for database and LLM consumption.
  - **Engine Purity**: Implements the "Engine-Lens Architecture" where core dimensions like `canonical_activities` and `canonical_roles` are defined as opaque arrays, to be interpreted by vertical lenses.

### Engine Configuration (`engine/config/`)
- **`entity_model.yaml`**: High-level configuration for the entity model generator.
- **`extraction.yaml`**: Configuration for the LLM-based extraction engine, including model selection and prompt versioning.
- **`sources.yaml` (from `.example`)**: Registry of data connectors (Serper, Google Places, OSM, etc.) with API keys, rate limits, and default search parameters.
- **`monitoring_alerts.yaml`**: Defines threshold and alerting rules for data quality and pipeline health.

### Raw Data Samples (`engine/data/raw/`)
Sample JSON files from various sources used for testing and validation:
- **`edinburgh_council/`**: Local facility data.
- **`google_places/`**: Business and venue results.
- **`openstreetmap/`**: Geographic and amenity elements.

## Data Flow

1. **Schema Propagation**:
   `entity.yaml` → `Schema Parser` → `schema.prisma` (DB) + `entity.py` (Pydantic) + `extraction_base.txt` (LLM Prompt)

2. **Configuration Loading**:
   `sources.yaml` → `Ingestion Engine` → `Connector Instances` → `API Requests`

## Configuration Surface

### Entity Schema Example
Evidence: `engine/config/schemas/entity.yaml:18-40`
```yaml
fields:
  - name: entity_name
    type: string
    description: Official name of the entity
    required: true
    index: true
    python:
      extraction_required: true
```

### Source Configuration Example
Evidence: `engine/config/sources.yaml.example:32-43`
```yaml
serper:
  enabled: true
  api_key: "YOUR_API_KEY"
  rate_limits:
    requests_per_minute: 60
  default_params:
    gl: "uk"
```

## Public Interfaces

### YAML Structure
The schema YAMLs follow a specific structure:
- `schema`: Metadata about the model (name, description, inheritance).
- `fields`: Detailed field definitions for core columns.
- `extraction_fields`: Fields used only during LLM extraction (not necessarily core DB columns).

## Examples

### Adding a New Source
1. Copy `sources.yaml.example` to `sources.yaml`.
2. Add a new block under the relevant section (Primary or Enrichment).
3. Implement the corresponding connector in `engine/ingestion/connectors/`.

### Modifying the Entity Model
1. Edit `engine/config/schemas/entity.yaml`.
2. Run the generation script: `python -m engine.schema.generate`.
3. Review and apply Prisma migrations.

## Edge Cases / Notes
- **Opaque Dimensions**: Fields like `canonical_activities` are stored as PostgreSQL arrays (`text[]`). The engine does not validate the values within these arrays; validation is deferred to the Lens layer.
- **API Security**: `sources.yaml` is ignored by Git to prevent API key leakage. Always use `sources.yaml.example` as the template for new environments.
- **Raw Data Naming**: Raw ingestion files follow a naming convention: `YYYYMMDD_<query_slug>_<hash>.json`.
