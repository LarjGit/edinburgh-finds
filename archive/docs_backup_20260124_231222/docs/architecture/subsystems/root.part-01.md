# Subsystem: Root (Part 01)

## Overview
The Root subsystem provides the foundational environment, project-wide configuration, and critical architectural enforcement for the Edinburgh Finds platform. It manages environment variables, sets up the Python testing environment, and hosts the "Architectural Guardians"—automated tests that ensure the Engine remains decoupled from domain-specific Lenses and that the Core Entity Model remains vertical-agnostic.

## Components

### 1. Environment Configuration
The project uses environment variables for infrastructure and third-party service integration.
- **Database**: PostgreSQL connection string via `DATABASE_URL`.
- **LLM Services**: Anthropic API keys for data extraction.
- **Data Sources**: API keys for Google Places and Serper.
- **Environment**: Controls logging levels and runtime modes (Dev/Prod).

Evidence: `.env.example:1-32`

### 2. Test Infrastructure
Foundational test setup ensuring consistent behavior across the monorepo.
- **Python Path Injection**: `conftest.py` automatically resolves the project root to enable clean imports across subsystems.
- **Test Markers**: `pytest.ini` defines custom markers such as `slow` to allow for selective test execution during CI/CD.

Evidence: `conftest.py:1-7`, `pytest.ini:1-3`

### 3. Architectural Guardians
Automated enforcement of the project's core design principles.

#### Engine Purity (`test_purity.py`)
Enforces the **LensContract** boundary:
- **No Lens Imports**: The Engine is forbidden from importing any code from the `lenses/` directory.
- **Structural Purity**: The Engine must not contain literal string comparisons against dimension values (e.g., `canonical_activities`). It must treat these values as opaque strings, only performing set operations or pass-throughs.

Evidence: `tests/engine/test_purity.py:12-78`

#### Entity Model Purity (`test_entity_model_purity.py`)
Validates that `entity_model.yaml` remains 100% vertical-agnostic:
- **Keyword Blacklist**: Blocks domain-specific terms like "padel", "wine", or "cafe" from the core schema.
- **Opaque Dimensions**: Ensures all dimensions (activities, roles, etc.) are stored as Postgres `text[]` arrays with GIN indexes and are explicitly marked as opaque.
- **Universal Modules Only**: Restricts core modules to cross-vertical concepts (location, contact, hours, amenities).

Evidence: `tests/engine/config/test_entity_model_purity.py:13-250`

### 4. Lens System Validation
Verification of the Lens-aware architecture logic.
- **Lens Loader**: Implements fail-fast validation for YAML configurations, ensuring `dimension_source` and facet references are valid at load time.
- **Processing Logic**: Tests for `DerivedGrouping` (AND/OR logic) and `ModuleTrigger` systems that dynamically attach UI modules to entities based on their classified attributes.

Evidence: `tests/lenses/test_loader.py:15-100`, `tests/lenses/test_lens_processing.py:90-200`

## Data Flow
1. **Environment Initialization**: `.env` variables are loaded by the Engine and Scripts to initialize DB connections and LLM clients.
2. **Contract Validation**: During test execution, Guardian tests scan the `engine/` and `engine/config/` directories to ensure no domain-specific "leakage" has occurred.
3. **Lens Loading**: `VerticalLens` loads `lens.yaml` files, performing schema validation before these lenses can be used to map raw data to the universal entity model.

## Configuration Surface
- `.env`: Database and API credentials.
- `pytest.ini`: Custom test markers and configuration.
- `engine/config/entity_model.yaml`: (Validated here) The source of truth for the universal entity structure.

## Edge Cases / Notes
- **Opaque Values**: The engine is allowed to branch on `entity_class` (e.g., `place` vs `person`) but *never* on the content of dimensions.
- **Fail-Fast Loading**: The `VerticalLens` loader will raise a `LensConfigError` immediately if a configuration file violates the schema, preventing runtime errors in the ingestion pipeline.
