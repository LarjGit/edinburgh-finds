# Testing Guide

Edinburgh Finds uses a multi-layered testing strategy to ensure data integrity, architectural purity, and functional correctness.

## Testing Framework
- **Primary Tool**: `pytest`
- **Configuration**: `pytest.ini` in the root directory.
- **Coverage**: Tracked via `.coverage` and `coverage.json`.

## Test Categories

### 1. Engine Purity Tests (Critical)
These tests enforce the architectural boundary between the vertical-agnostic engine and domain-specific lenses.
```bash
pytest tests/engine/test_purity.py
pytest tests/engine/config/test_entity_model_purity.py
```
- **Import Check**: Ensures `engine/` never imports from `lenses/`.
- **Keyword Check**: Ensures `entity_model.yaml` doesn't contain domain-specific terms.

### 2. Lens Validation
Verifies that lens configurations (`lens.yaml`) are valid and follow the architectural contract.
```bash
pytest tests/lenses/test_validator.py
python scripts/validate_wine_lens.py
```

### 3. Ingestion & Extraction Tests
Verifies the data acquisition and processing pipelines.
```bash
pytest tests/engine/test_lens_membership.py
pytest tests/modules/test_composition.py
```

### 4. Frontend & Query Tests
Verifies the Next.js utility functions and database queries.
```bash
cd web
npm test  # If configured, otherwise use pytest on web/lib/*.test.ts patterns
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=engine --cov-report=html
```

## CI Pipeline
Every pull request triggers the GitHub Actions workflow defined in `.github/workflows/tests.yml`. This pipeline runs:
1.  **Shell Purity Check**: `bash scripts/check_engine_purity.sh`
2.  **Full Test Suite**: All `pytest` tests.

Failure in any of these steps will block the merge.

---
*Evidence: docs/architecture/subsystems/infrastructure.md, pytest.ini, .github/workflows/tests.yml*
