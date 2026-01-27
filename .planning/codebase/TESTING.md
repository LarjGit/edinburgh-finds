# Testing Patterns

**Analysis Date:** 2026-01-27

## Test Framework

**Frontend (Next.js/TypeScript):**
- Runner: Jest (via `@jest/globals`)
- Assertion Library: Jest built-in expect
- Config: Not explicitly configured; uses Next.js defaults
- Run Commands:
  ```bash
  npm test                  # Run all tests (not configured in package.json)
  npm run lint              # Linting check (eslint)
  npm run build             # Build verification
  ```

**Backend (Python):**
- Runner: pytest
- Assertion Library: pytest assertions
- Config: `pytest.ini` at project root
- Markers: `@pytest.mark.slow` and `@pytest.mark.integration`
- Async support: `asyncio_mode = auto` enabled
- Run Commands:
  ```bash
  pytest                          # Run all tests
  pytest -m "not slow"            # Fast tests only (exclude @pytest.mark.slow)
  pytest --cov=engine             # With coverage
  pytest engine/orchestration/    # Specific module
  pytest -v                       # Verbose output
  ```

## Test File Organization

**Frontend (TypeScript):**
- Location: Co-located with source files
- Pattern: `{module}.test.ts` in same directory as `{module}.ts`
- Examples:
  - `web/lib/utils.ts` → `web/lib/utils.test.ts`
  - `web/lib/lens-query.ts` → `web/lib/lens-query.test.ts`

**Backend (Python):**
- Location: `tests/` directory at project root with mirrored structure
- Pattern: `tests/engine/{module}/{functionality}/test_{module}.py`
- Examples:
  - `engine/extraction/base.py` → `tests/engine/extraction/test_extractors.py`
  - `engine/orchestration/adapters.py` → `tests/engine/orchestration/test_adapters.py`
  - `engine/config/entity_model.yaml` → `tests/engine/config/test_entity_model_purity.py`

## Test Structure

**Frontend (Jest/TypeScript):**
```typescript
import { describe, it, expect } from '@jest/globals';

describe('parseAttributesJSON', () => {
  it('should parse valid JSON string', () => {
    const jsonString = '{"capacity": 250, "wheelchair_accessible": true}';
    const result = parseAttributesJSON(jsonString);
    expect(result).toEqual({ capacity: 250, wheelchair_accessible: true });
  });

  it('should return empty object for null input', () => {
    const result = parseAttributesJSON(null);
    expect(result).toEqual({});
  });
});
```

**Patterns:**
- Use `describe()` for test suites (one per function/feature)
- Use `it()` or `test()` for individual test cases (Jest aliases)
- Clear test names: "should [expected behavior]"
- Arrange-act-assert pattern (implicit in structure)
- One assertion per test preferred (or tightly related assertions)

**Backend (pytest/Python):**
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

class TestNormalizeForJson:
    """Test JSON normalization function."""

    def test_normalizes_datetime_to_iso_string(self):
        """datetime objects should be converted to ISO format strings."""
        dt = datetime(2024, 1, 15, 14, 30, 0)
        result = normalize_for_json(dt)

        assert isinstance(result, str)
        assert result == "2024-01-15T14:30:00"

    @pytest.mark.slow
    def test_some_slow_operation(self):
        """Test that takes >1 second."""
        # ... slow test code
        pass

    @pytest.mark.integration
    async def test_with_real_api(self):
        """Test requiring actual API calls."""
        # ... integration test code
        pass
```

**Patterns:**
- Organize with `class Test{Feature}` for grouping related tests
- Method naming: `test_{scenario}()` or `test_should_{expected}_{condition}`
- Docstrings explain what is being tested
- Use `@pytest.mark.slow` for tests >1 second (allows skipping with `-m "not slow"`)
- Use `@pytest.mark.integration` for tests requiring external APIs
- Async tests: Use `async def test_...()` with `asyncio_mode = auto`
- One assertion per test (or logically grouped assertions)

## Mocking

**Frontend (Jest):**
- Manual mocks not found in codebase
- Tests call functions directly with test data
- No mock setup visible in existing tests
- Pattern: Pass test data directly to functions

**Backend (Python):**
```python
from unittest.mock import Mock, AsyncMock, patch

class TestConnectorAdapter:
    def setup_method(self):
        """Setup called before each test."""
        self.mock_connector = Mock(spec=BaseConnector)
        self.mock_spec = ConnectorSpec(...)
        self.adapter = ConnectorAdapter(self.mock_connector, self.mock_spec)

    @patch('engine.orchestration.adapters.ConnectorAdapter.execute')
    async def test_execute_calls_connector(self, mock_execute):
        """Test that execute properly calls the connector."""
        mock_execute.return_value = [...]  # or AsyncMock
        # ... test code
```

**Patterns:**
- Use `Mock()` for sync dependencies
- Use `AsyncMock()` for async dependencies
- Use `@patch()` decorator for injecting mocks
- Setup complex mocks in `setup_method()` (called before each test)
- Pattern: `@patch('full.module.path.ClassName.method')`
- Return values set with `.return_value` or `.return_value.side_effect`

**What to Mock:**
- External API calls (Serper, Google Places, OpenStreetMap)
- Database queries (Prisma)
- File I/O operations
- Network requests

**What NOT to Mock:**
- Pure utility functions (should be tested directly)
- Data parsing/transformation logic
- Schema validation
- Deduplication matching (test with real data)

## Fixtures and Factories

**Frontend:**
- No fixtures found in existing tests
- Test data passed directly as function arguments
- Pattern: Inline test data in `it()` blocks

**Backend (Python):**
```python
import pytest
from datetime import datetime
from decimal import Decimal

@pytest.fixture
def sample_raw_ingestion():
    """Fixture providing sample raw ingestion data."""
    return {
        "name": "Test Entity",
        "lat": 55.9533,
        "lng": -3.1883,
        "raw_data": {...}
    }

def test_extract_with_fixture(sample_raw_ingestion):
    """Test using fixture."""
    extractor = GooglePlacesExtractor()
    result = extractor.extract(sample_raw_ingestion)
    assert result['entity_name'] == "Test Entity"
```

**Location:**
- `tests/conftest.py` for shared fixtures across all tests
- `tests/engine/{module}/conftest.py` for module-specific fixtures
- Fixtures used for complex setup (API responses, database records)

**Fixture Examples in Codebase:**
- Not yet implemented; fixtures could improve test readability
- Candidates: Sample raw ingestion payloads, mock connector responses

## Coverage

**Requirements:** Coverage tracking enabled via pytest
```bash
pytest --cov=engine --cov-report=html
```

**Target:** >80% for all new code (stated in CLAUDE.md)

**Current State:**
- Coverage report generation configured
- HTML report generated to `.coverage/`
- No minimum threshold enforced in CI yet

**Areas Covered:**
- Extraction utilities (utils.test.ts shows comprehensive coverage)
- Query builders (lens-query.test.ts extensive)
- Orchestration adapters (test_adapters.py)
- Entity model purity (test_entity_model_purity.py)

**Gaps:**
- Frontend API integration tests not visible
- Backend CLI tests exist but sparse
- No E2E tests configured

## Test Types

**Unit Tests:**
- Scope: Single function or method in isolation
- Approach: Call function with test data, assert output
- Example: `parseAttributesJSON()` with various inputs
- Isolation: Mocked dependencies, no side effects
- Count: Majority of test suite

**Integration Tests:**
```python
@pytest.mark.integration
async def test_extraction_pipeline():
    """Test full ingest → extract → dedupe flow."""
    # Orchestrate multiple components
    # May touch real database or external APIs
    pass
```
- Scope: Multiple components working together
- Approach: Exercise data flow from ingestion to database
- Example: Orchestration CLI test with real connector registry
- Isolation: Some real dependencies (marked with `@pytest.mark.integration`)
- Count: Small number of key flows

**E2E Tests:**
- Framework: Not configured
- Would test: Full web application flow
- Example: Navigate to search page → filter results → view details
- Status: Not implemented

## Common Patterns

**Async Testing (Python):**
```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async function."""
    result = await async_function()
    assert result == expected

# With asyncio_mode = auto, can be simpler:
async def test_without_decorator():
    """Async test without explicit decorator."""
    result = await async_function()
    assert result == expected
```

**Error Testing (Frontend):**
```typescript
it('should return empty object for invalid JSON', () => {
  const result = parseAttributesJSON('{invalid json}');
  expect(result).toEqual({});
});
```
- Pattern: Error cases return sensible defaults (empty object, empty array)
- No exceptions thrown for expected errors
- Logging instead of exceptions for user-facing code

**Error Testing (Backend):**
```python
def test_deduplication_with_poor_data():
    """Test deduplication handles missing fields gracefully."""
    entity1 = {"name": "Test"}  # Missing lat/lng
    entity2 = {"name": "Test", "lat": 55.9533, "lng": -3.1883}

    result = deduplicator.find_match(entity1, entity2)

    assert result.confidence < 1.0  # Lower confidence, not error
```
- Pattern: Return lower confidence scores, not exceptions
- Deduplication is forgiving (handles partial data)
- Extraction logs failures but re-raises

**Testing Complex Queries (Frontend):**
```typescript
describe("Query Semantics Integration", () => {
  test("OR within facet semantic - hasSome operator", () => {
    const filter = {
      facet: "activity",
      dimensionSource: "canonical_activities",
      selectedValues: ["padel", "tennis"],
      mode: "OR",
    };

    const query = queryByFacet(filter);

    expect(query).toEqual({
      canonical_activities: { hasSome: ["padel", "tennis"] },
    });

    // Comments explain what this query matches:
    // ✅ Entity with activities: ["padel"]
    // ✅ Entity with activities: ["tennis"]
    // ✅ Entity with activities: ["padel", "tennis"]
    // ❌ Entity with activities: ["squash", "badminton"]
  });
});
```
- Pattern: Include semantic examples showing what matches/doesn't match
- Query logic validated with Prisma array operators (hasSome, hasEvery, has)
- Tests serve as documentation of query semantics

## Running Tests

**Frontend:**
```bash
npm run lint              # ESLint checks (no jest tests in npm scripts yet)
npm run build             # Build check (includes type checking)
```

**Backend:**
```bash
pytest                          # All tests
pytest -m "not slow"            # Fast tests only (iterative development)
pytest --cov=engine             # With coverage
pytest --cov=engine --cov-report=html  # HTML coverage report
pytest engine/orchestration/    # Specific module
pytest -v -s                    # Verbose with stdout capture
pytest tests/engine/extraction/test_adapters.py::TestConnectorAdapter::test_normalizes_datetime_to_iso_string  # Single test
```

**CI/CD:**
- No CI pipeline configuration found
- Ideal: `pytest --cov=engine --cov-report=term` with min 80% threshold
- Frontend: `npm run lint && npm run build`

## Test Quality Standards

**Required for All Tests:**
1. Clear test name describing what is tested
2. Docstring explaining purpose (Python) or comment (TypeScript)
3. Arrange-act-assert structure
4. One logical assertion (or tightly related)
5. No hardcoded magic numbers without explanation

**Code Examples in Tests:**
- lens-query.test.ts uses semantic comments extensively
- Shows expected behavior with emoji indicators (✅ matches, ❌ doesn't match)
- Pattern to replicate in new tests

**Naming Convention Examples:**
- Good: `test_normalizes_datetime_to_iso_string()` (clear intent)
- Good: `test_returns_empty_object_for_invalid_json()` (clear expectation)
- Bad: `test_parsing()` (vague)
- Bad: `test_case_1()` (meaningless)

---

*Testing analysis: 2026-01-27*
