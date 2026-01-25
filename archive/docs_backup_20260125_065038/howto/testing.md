# Testing Guide

Edinburgh Finds uses automated testing across both its Python engine and TypeScript web layers.

## Python (Engine) Tests
We use `pytest` for the data engine and ingestion logic.

### Running Engine Tests
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=engine

# Run a specific subsystem's tests
pytest tests/engine/
```

### Key Test Suites
- `tests/engine/`: Core orchestration and ingestion logic.
- `tests/lenses/`: Lens-specific validation and processing.
- `tests/modules/`: Individual module functionality (validators, etc.).
- `tests/query/`: Query feature extraction and DSL tests.

## Web (Frontend) Tests
The web layer uses `eslint` for linting and type checking.

### Running Web Checks
```bash
cd web

# Run linting
npm run lint

# Run type check
npx tsc --noEmit
```

## Continuous Integration
Tests are automatically run on every pull request via GitHub Actions.
- **Workflow Location**: `.github/workflows/tests.yml`
- **Actions**:
    - Python environment setup and `pytest` execution.
    - Node.js environment setup and `lint` execution.
    - Database migration validation.

---
*Evidence: pytest.ini, tests/ directory, and web/package.json.*
