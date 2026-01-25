# Subsystem: tests

## Purpose
The tests subsystem provides a comprehensive suite for validating the core engine, lens configurations, data migrations, and database query performance. It ensures that the system adheres to architectural contracts, maintains data purity, and performs efficiently under load, particularly for the multi-dimensional lens architecture.

## Common Workflows

### Validating a New Lens
When a new lens (e.g., `lenses/my_lens/lens.yaml`) is added, the following workflow is performed:
1. **Schema Validation**: The `VerticalLens` loader automatically validates the YAML structure and architectural contracts (e.g., valid `dimension_source`, existing facets).
2. **Contract Testing**: A dedicated test file (e.g., `tests/lenses/test_my_lens.py`) is created to verify specific mapping rules and facet configurations.
3. **Extraction Testing**: A script similar to `scripts/test_wine_extraction.py` is used to verify that raw data is correctly mapped to canonical dimensions according to the lens contract.

### Testing Data Migrations
When the database schema evolves (e.g., from `Listing` to `Entity` model):
1. **Rule Verification**: `resolve_entity_class_and_roles` logic is tested against various legacy types.
2. **Data Integrity**: A temporary SQLite database is created, populated with legacy data, and migrated to ensure no data loss and correct classification.
3. **Evidence**: `tests/migration/test_migrate_listing_to_entity.py:27-100`

### Performance Benchmarking
For query-heavy features like multi-select filters:
1. **Dataset Generation**: Large volumes of test data (e.g., 10,000 records) are injected into a test database.
2. **Execution Timing**: Prisma queries using `hasSome` or `hasEvery` are timed to ensure they meet performance thresholds (e.g., < 100ms).
3. **Plan Analysis**: `EXPLAIN ANALYZE` is used to verify that GIN indexes on Postgres `text[]` arrays are being utilized.
4. **Evidence**: `tests/query/test_prisma_array_filters.py:206-250`

## Key Components

| Component | Description | Evidence |
|-----------|-------------|----------|
| `VerticalLens` | Loader and validator for lens configurations; enforces fail-fast contracts. | `tests/lenses/test_loader.py` |
| `LensRegistry` | Central registry for managing loaded lenses. | `tests/lenses/test_lens_processing.py:348-370` |
| `validate_lens_config` | Core validation logic for architectural contracts 1-5. | `tests/lenses/test_validator.py` |
| `DerivedGrouping` | Matches entities against lens-defined groupings using AND/OR logic. | `tests/lenses/test_lens_processing.py:102-180` |
| `ModuleTrigger` | Logic for conditionally triggering domain modules based on facet values. | `tests/lenses/test_lens_processing.py:196-280` |

## Architecture & Diagrams

### Test Hierarchy
```mermaid
graph TD
    A[Pytest Runner] --> B[Lens Tests]
    A --> C[Migration Tests]
    A --> D[Module Tests]
    A --> E[Query Tests]
    
    B --> B1[Schema Validation]
    B --> B2[Contract Enforcement]
    B --> B3[Mapping Rules]
    
    C --> C1[Type Mapping]
    C --> C2[Database Migration]
    
    E --> E1[Array Filters]
    E --> E2[Performance/GIN Indexes]
```

### Lens Validation Flow
```mermaid
sequenceDiagram
    participant D as Developer
    participant L as VerticalLens
    participant V as Validator
    
    D->>L: Initialize(lens_path)
    L->>L: Load YAML
    L->>V: validate_lens_config(config)
    V-->>V: Check Dimension Sources
    V-->>V: Check Facet References
    V-->>V: Check Value Uniqueness
    V-->>L: Success / ValidationError
    L-->>D: Lens Object / LensConfigError
```

## Dependencies

### Internal
- `engine.lenses.loader`: Used for all lens validation tests.
- `engine.lenses.validator`: Core contract enforcement logic.
- `engine.extraction.base`: Used for extraction integration tests.
- `migrate_listing_to_entity`: Script being tested in migration suite.

### External
- `pytest`: Primary test runner.
- `prisma`: ORM used for database query and performance tests.
- `PyYAML`: Used for parsing and validating lens configurations.
- `PostgreSQL`: Required for array filter and GIN index performance tests.

## Configuration & Examples

### Running Tests
```bash
# Run all tests
pytest

# Run lens-specific tests
pytest tests/lenses/

# Run performance tests (requires Postgres)
export DATABASE_URL="postgresql://user:pass@localhost:5432/db"
pytest tests/query/test_prisma_array_filters.py
```

### Lens Contract Test Example
```python
def test_all_facets_use_valid_dimension_source(self, lens):
    """All facets should use one of the 4 allowed dimension sources."""
    facets = lens.config.get("facets", {})
    for facet_key, facet_config in facets.items():
        dimension_source = facet_config.get("dimension_source")
        assert dimension_source in ALLOWED_DIMENSION_SOURCES, (
            f"Facet '{facet_key}' uses invalid dimension_source '{dimension_source}'"
        )
```

## Evidence
- `scripts/test_wine_extraction.py`: Wine lens integration test.
- `tests/lenses/test_edinburgh_finds_lens.py`: Edinburgh lens contract validation.
- `tests/lenses/test_lens_processing.py`: Core processing unit tests.
- `tests/lenses/test_loader.py`: Loader fail-fast behavior tests.
- `tests/lenses/test_validator.py`: Contract enforcement unit tests.
- `tests/migration/test_migrate_listing_to_entity.py`: Schema migration verification.
- `tests/modules/test_composition.py`: Module namespacing and YAML strict loading.
- `tests/query/test_prisma_array_filters.py`: Postgres array query and performance tests.
