# Test Strategy & Organization

## Testing Philosophy

**Integration-First Testing:** We prioritize integration tests that validate complete workflows over unit tests that mock everything.

**Why?**
- Unit tests with excessive mocking test mock behavior, not system behavior
- Integration tests catch real bugs at component boundaries
- TDD works best when tests verify actual value delivery

## Test Organization

```
tests/
├── engine/
│   ├── orchestration/      # Orchestration layer tests
│   ├── extraction/          # Extraction logic tests
│   ├── lenses/              # Lens system tests
│   └── ingestion/           # Connector tests
└── web/                     # Frontend tests
```

## Test Markers

### `@pytest.mark.slow`
Tests that interact with real database or take >1 second:
```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_finalize_entities():
    db = Prisma()
    await db.connect()
    # ... test with real database
```

Run fast tests only:
```bash
pytest -m "not slow"
```

Run all tests:
```bash
pytest
```

## Testing Principles

### 1. Test Real Behavior, Not Mocks

**❌ Bad: Zombie Test**
```python
def test_persistence():
    mock_db = Mock()
    mock_db.create.return_value = Mock(id="123")
    # ... 50 lines of mock configuration
    assert mock_db.create.called  # Testing mock behavior
```

**✅ Good: Integration Test**
```python
@pytest.mark.slow
async def test_persistence():
    db = Prisma()
    await db.connect()
    result = await db.entity.create(data=entity_data)
    assert result.slug == "expected-slug"  # Testing real behavior
```

### 2. Use Mocks Sparingly

Acceptable mock usage:
- External API calls (Anthropic, Serper, Google Places)
- Expensive operations in fast tests
- Isolated logic testing

Avoid:
- Mocking >20 objects in one test
- Mocking internal system components
- Testing that mocks were called with specific arguments

### 3. TDD Red → Green → Refactor

```python
# Step 1: Write failing test
def test_slug_generation():
    generator = SlugGenerator()
    assert generator.generate("The Venue") == "venue"  # ❌ FAILS

# Step 2: Implement minimum to pass
class SlugGenerator:
    def generate(self, name):
        return name.lower().replace("the ", "")  # ✅ PASSES

# Step 3: Refactor for edge cases
# (add more tests for Unicode, special chars, etc.)
```

### 4. Test Database Fixtures

For slow tests that need database setup:

```python
@pytest.fixture
async def test_db():
    db = Prisma()
    await db.connect()
    yield db
    await db.disconnect()

@pytest.mark.slow
async def test_with_db(test_db):
    entity = await test_db.entity.create(data={...})
    assert entity.slug is not None
```

## Coverage Targets

- **Minimum:** 80% coverage for all new code
- **Critical paths:** 100% coverage (authentication, payments, data integrity)
- **Generated code:** Excluded from coverage (Prisma client, schema generators)

Run coverage:
```bash
pytest --cov=engine --cov-report=html
# Open htmlcov/index.html
```

## Test Templates

### Integration Test Template
```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_workflow():
    """Test complete end-to-end workflow."""
    db = Prisma()
    await db.connect()

    # Arrange: Setup test data
    test_data = {...}

    # Act: Execute workflow
    result = await some_workflow(test_data)

    # Assert: Verify end state
    assert result.status == "success"

    # Cleanup
    await db.entity.delete_many(where={...})
    await db.disconnect()
```

### Fast Unit Test Template
```python
def test_deterministic_logic():
    """Test pure logic with no side effects."""
    # Arrange
    input_data = "test input"

    # Act
    result = pure_function(input_data)

    # Assert
    assert result == "expected output"
```

## Anti-Patterns

### Zombie Tests
Tests that pass no matter what the code does:
```python
# ❌ This always passes
def test_something():
    mock = Mock()
    mock.do_thing()
    assert True  # Always true!
```

### Brittle Tests
Tests that break when implementation details change:
```python
# ❌ Tests internal implementation
def test_uses_specific_sql_query():
    assert "SELECT * FROM" in db.last_query
```

### Over-Mocking
```python
# ❌ 30 mocks configured
with patch("mod1") as m1, \
     patch("mod2") as m2, \
     # ... 28 more patches
```

## When Tests Fail

1. **Read the error message** - Don't just re-run
2. **Check what changed** - Recent commits that might have broken it
3. **Verify test is valid** - Is the test testing real behavior?
4. **Fix root cause** - Don't just update the test to pass

## Running Tests in CI

Tests run automatically on:
- Pull requests
- Commits to main
- Scheduled daily runs

CI runs:
```bash
pytest -m "not slow"  # Fast tests only
pytest --slow         # Full test suite (nightly)
```

## Future: Contract Testing

As we grow, we'll add:
- Contract tests between engine and web
- API contract tests for external integrations
- Snapshot testing for UI components
