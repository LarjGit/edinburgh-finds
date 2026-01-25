Audience: Developers

# Scripts Subsystem

The Scripts subsystem provides utility commands and manual test scripts for managing data ingestion, extraction pipelines, lens validation, and documentation quality. These scripts serve as both operational tools and integration test examples.

## Overview

The scripts are divided into two primary locations:
- `engine/scripts/`: Low-level connector tests and ingestion utilities.
- `scripts/`: High-level pipeline orchestration, lens-aware extraction, and validation tools.

## Components

### Ingestion Connector Tests (`engine/scripts/`)
- **`run_serper_connector.py`**: Manual integration test for the Serper API. Verifies API connectivity, response parsing, and deduplication.
- **`run_google_places_connector.py`**: Test script for the Google Places API integration.
- **`run_open_charge_map_connector.py`**: Integration test for the Open Charge Map data source.
- **`run_edinburgh_council_connector.py`**: Validates the Edinburgh Council data scraper/connector.
- **`run_sport_scotland_connector.py`**: Tests the Sport Scotland data ingestion.

### Pipeline & Validation Utilities (`scripts/`)
- **`run_lens_aware_extraction.py`**: Orchestrates the re-extraction of raw data using specialized Lenses (e.g., Edinburgh Finds). It updates the `Entity` table with dimensions derived from Lens contracts.
- **`validate_docs.py`**: Ensures documentation quality and coverage across the repository.
- **`validate_wine_lens.py`**: Performs schema and logic validation specifically for the Wine Discovery lens.
- **`test_wine_extraction.py`**: A dedicated test suite for verifying the extraction logic against wine-related raw data.

## Data Flow

1. **Ingestion Test Flow**:
   `sources.yaml` → `Connector` → `Raw JSON File` → `Database (RawIngestion Table)`

2. **Lens-Aware Extraction Flow**:
   `Database (RawIngestion)` + `Lens (YAML)` → `VerticalLens Loader` → `Extraction Engine` → `Database (Entity Table)`

## Configuration Surface

- **Environment Variables**:
  - `DATABASE_URL`: Must point to a PostgreSQL instance for lens-aware extraction.
  - API Keys (e.g., `SERPER_API_KEY`): Usually managed via `engine/config/sources.yaml`.

- **Configuration Files**:
  - `engine/config/sources.yaml`: Defines API endpoints and authentication for connectors.
  - `lenses/*/lens.yaml`: Defines the schema and mapping rules used by extraction scripts.

## Public Interfaces

### Command Line
Most scripts are designed to be run as modules or direct scripts:

```bash
# Run a connector test
python -m engine.scripts.run_serper_connector

# Run lens-aware extraction
python scripts/run_lens_aware_extraction.py --limit 10 --source google_places
```

## Examples

### Running Lens-Aware Extraction
Evidence: `scripts/run_lens_aware_extraction.py:228-245`

```python
# Example of executing the script with filters
python scripts/run_lens_aware_extraction.py --source osm --limit 50
```

### Serper Connector Verification
Evidence: `engine/scripts/README.md:37-46`
The script verifies:
1. Configuration loading
2. API authentication
3. Content hashing
4. Filesystem and Database persistence

## Edge Cases / Notes

- **Database Compatibility**: `run_lens_aware_extraction.py` explicitly requires PostgreSQL and will fail if `DATABASE_URL` points to SQLite. This is due to the use of advanced JSONB features and dimension arrays.
- **Dry Run Mode**: High-level scripts like `run_lens_aware_extraction.py` support a `--dry-run` flag to validate extraction logic without committing changes to the database.
- **Path Resolution**: Scripts typically add the project root to `sys.path` to ensure absolute imports work correctly regardless of the execution directory.
