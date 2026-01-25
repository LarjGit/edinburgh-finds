# Subsystem: scripts

## Purpose
The `scripts` subsystem provides utility and validation scripts for running lens-aware extractions, testing new lens configurations, and ensuring the integrity of the project's documentation and data models. It serves as an operational layer for executing complex workflows that span multiple subsystems.

## Key Components

### Extraction & Processing
- `scripts/run_lens_aware_extraction.py`: A comprehensive script that orchestrates the re-extraction of entities from raw ingestion records using the lens-aware pipeline. It loads the Edinburgh Finds lens, processes raw data through the engine's extraction logic, and upserts the results into the `Entity` database table.

### Validation & Testing
- `scripts/test_wine_extraction.py`: A test script used to verify that the Wine Discovery lens correctly maps data to canonical dimensions and triggers domain-specific modules without requiring changes to the core engine code.
- `scripts/validate_wine_lens.py`: A validation utility that ensures the Wine Discovery lens configuration adheres to the lens schema, uses valid dimension sources, and follows the "Engine Purity" architectural principles.
- `scripts/validate_docs.py`: A maintenance script for the `doc-suite` system that validates the documentation manifest, checks for missing outputs, and generates a coverage report in `temp/doc-coverage-report.md`.

## Architecture
The scripts in this subsystem follow a pattern of:
1. **Environment Setup**: Adding the project root to the Python path to allow imports from the `engine` and other modules.
2. **Configuration Loading**: Loading lens contracts (`.yaml`) or state files (`.json`).
3. **Execution**: Invoking core engine functions like `extract_with_lens_contract` or `VerticalLens`.
4. **Persistence/Reporting**: Writing results to the database via Prisma or generating local markdown/JSON reports.

## Dependencies

### Internal
- `engine.lenses.loader`: Used for loading and validating lens configurations.
- `engine.extraction.base`: Provides the core `extract_with_lens_contract` function.
- `lenses/`: Scripts consume lens definitions from this directory.
- `temp/`: State and manifest files used by documentation validation scripts.

### External
- **Prisma**: Used for database interactions, specifically for the `Entity` and `RawIngestion` models.
- **PostgreSQL**: Required by extraction scripts for native JSONB and array support.
- **tqdm**: Used for progress visualization during long-running extraction tasks.

## Configuration
- `DATABASE_URL`: Must be set to a PostgreSQL connection string for scripts requiring database persistence (e.g., `run_lens_aware_extraction.py`).

## Evidence
- `scripts/run_lens_aware_extraction.py`: Implementation of lens-aware extraction pipeline.
- `scripts/test_wine_extraction.py`: Evidence of lens-agnostic engine design via wine lens testing.
- `scripts/validate_docs.py`: Documentation coverage and manifest validation logic.
- `scripts/validate_wine_lens.py`: Lens contract validation rules.
