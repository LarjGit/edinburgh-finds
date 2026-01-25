# Subsystem: tests

## Purpose
The `tests` subsystem provides the testing infrastructure and specific test suites for verifying migrations, core module logic, and query filtering. It ensures data integrity, correctness of the engine's core components, and adherence to schema constraints during evolution.

## Key Components

### Test Configuration
- **conftest.py**: Root-level pytest configuration that ensures the project root is added to the system path, making all internal modules importable during test execution.

### Migration Testing
- **tests/migration/test_migrate_listing_to_entity.py**: Comprehensive test suite for the `migrate_listing_to_entity.py` migration script. It validates:
  - Entity type mapping rules (e.g., mapping "VENUE" to "place" with roles).
  - Data transformation logic using a temporary SQLite database.
  - Schema migration correctness.

### Module Validation
- **tests/modules/test_composition.py**: Ensures that module data stored in JSONB fields is properly namespaced. It also tests the strict YAML loader to prevent duplicate keys in configuration files.

### Query Testing
- **tests/query/test_prisma_array_filters.py**: (Unopened in this step) Focuses on verifying Prisma query filters, particularly for array and JSONB fields.

## Architecture

- **Pytest Framework**: Employs `pytest` as the primary test runner, utilizing fixtures for lifecycle management.
- **Isolated Integration Tests**: Uses temporary file-based SQLite databases to run integration tests for migrations without affecting the development or production databases.
- **Schema-First Validation**: Tests are heavily focused on ensuring that data complies with the architectural "Engine Purity" principles, specifically regarding entity classification and module namespacing.
- **Static Analysis via Testing**: Includes tests that act as static analysis tools, such as the strict YAML loader verification.

## Dependencies

### Internal
- **engine/modules/validator.py**: Used for testing module and YAML validation logic.
- **scripts/migrate_listing_to_entity.py**: Targeted by migration tests.

### External
- **pytest**: Core testing framework.
- **sqlite3**: Standard library module for integration testing.
- **PyYAML**: Used for validating configuration parsing.

## Evidence
- **conftest.py:1-6**: Path resolution for test imports.
- **tests/migration/test_migrate_listing_to_entity.py:13-118**: Detailed mapping rules and temporary database fixtures for migration testing.
- **tests/modules/test_composition.py:17-158**: Validation logic for module namespacing and strict YAML loading.
