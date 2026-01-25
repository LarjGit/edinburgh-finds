# Subsystem: engine-core

## Purpose
The `engine-core` subsystem defines the foundational, vertical-agnostic data model and configuration for the entire Edinburgh Finds engine. It ensures "engine purity" by strictly separating universal entity attributes from lens-specific (domain) interpretations.

## Key Components
- **Universal Entity Model**: Defined via YAML schemas (`engine/config/schemas/entity.yaml`), specifying core fields (identity, location, contact, hours) and opaque dimensions (activities, roles, access).
- **Configuration Management**: Centralized settings for data sources (`sources.yaml`), extraction parameters (`extraction.yaml`), and monitoring alerts (`monitoring_alerts.yaml`).
- **Data Ingestion Engine (`engine/ingest.py`)**: Core logic for validating and upserting entities. It maps incoming data to core columns or namespaced modules, ensuring data conforms to the universal schema.
- **Module Validator (`engine/modules/validator.py`)**: Enforces architectural contracts for module composition, preventing "flattened" JSONB structures and ensuring strict YAML parsing.
- **Data Integrity Tools**: Scripts like `check_data.py` and `inspect_db.py` for verifying database state and entity data consistency.
- **Raw Data Storage**: Repository for raw ingestion records (JSON) from various connectors (OSM, Google Places, etc.) used for testing and extraction.

## Architecture
The subsystem follows the **Engine-Lens Architecture**. The engine layer is designed to be vertical-agnostic, handling universal entities (place, person, organization, etc.). It stores domain-specific data in "opaque" fields (Postgres `text[]` arrays and `JSONB` modules) which are later interpreted by the lens layer.

### Architectural Contracts
- **Namespacing**: The `modules` JSONB field MUST be namespaced by module key (e.g., `{"location": {...}}`). Flattened structures are prohibited.
- **Strict Configuration**: YAML configuration files are loaded with duplicate key detection to prevent configuration drift or ambiguity.

## Dependencies
### Internal
- `engine/schema`: Consumes YAML schemas to generate Prisma and Python models.
- `engine/extraction`: Uses configuration (trust levels, LLM settings) for data processing.

### External
- **Prisma**: ORM used for database interactions.
- **Pydantic**: Used for runtime data validation during ingestion.
- **Anthropic Claude**: LLM configured for data extraction tasks.
- **YAML**: Used for all major configuration and schema definitions.

## Data Models
### Entity
The primary model representing a real-world object.
- **Core Fields**: `entity_id`, `entity_name`, `entity_class` (place, person, organization, event, thing).
- **Location**: `street_address`, `city`, `postcode`, `latitude`, `longitude`.
- **Contact**: `phone`, `email`, `website_url`, social media links.
- **Modules**: Namespaced `JSONB` for extensible, module-based data (e.g., `core`, `location`, `hours`).
- **Dimensions**: Opaque `text[]` arrays (e.g., `canonical_activities`, `canonical_roles`) for faceted filtering.

## Operational Workflows
### Entity Ingestion
1. **Validation**: Incoming data is validated against a Pydantic model generated from the YAML schema.
2. **Field Mapping**: Fields are separated into core database columns and Namespaced `modules`.
3. **Deduplication/Upsert**: Entities are upserted based on their `slug` or external identifiers.

### Seeding and Development
- **Sample Data**: `engine/seed_data.py` contains representative entity data (e.g., sports complexes) used for bootstrapping environments.
- **Seed Script**: `engine/run_seed.py` ingests sample data into the database to verify the end-to-end pipeline.
- **Manual Testing**: Connector-specific scripts (e.g., `engine/scripts/run_google_places_connector.py`) enable manual verification of API integrations and data extraction before full pipeline deployment.

## Testing and Quality Assurance
### Engine Purity Enforcement
The engine's architectural integrity is protected by automated "purity tests" (`tests/engine/test_purity.py`):
- **Boundary Violation Check**: Ensures no code in `engine/` imports from the `lenses/` directory, maintaining strict decoupling.
- **Structural Purity Check**: Prohibits literal string comparisons against dimension values (e.g., `if "padel" in canonical_activities`). The engine is only permitted to branch on `entity_class` or perform set-based operations on opaque dimension values.

### Data Integrity
- Automated checks for database connectivity and row counts via `inspect_db.py`.
- Validation of architectural contracts (namespacing, strict YAML) via `engine/modules/validator.py`.

## Evidence
- **Engine Purity Principles**: `engine/config/entity_model.yaml:5-15`
- **Subsystem configuration overview**: `engine/config/README.md`
- **Universal Entity Schema**: `engine/config/schemas/entity.yaml`
- **Source Trust Levels**: `engine/config/extraction.yaml:4-12`
- **Monitoring Alert Thresholds**: `engine/config/monitoring_alerts.yaml:13-100`
- **Ingestion Logic**: `engine/ingest.py:30-150`
- **Module Namespacing Contract**: `engine/modules/validator.py:17-60`
- **Engine Purity Tests**: `tests/engine/test_purity.py`
- **Sample Seed Data**: `engine/seed_data.py`
- **Manual Connector Testing**: `engine/scripts/run_google_places_connector.py`

