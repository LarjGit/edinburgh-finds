# Snapshot Testing Workflow

## Overview

Snapshot testing captures the output of extractors at a known-good state and compares future extractions against these snapshots. This prevents regressions when modifying extraction logic.

## Why Snapshot Testing?

The extraction engine transforms raw data from various sources into structured listings. Changes to extraction logic (field mappings, validation rules, LLM prompts) can inadvertently break existing functionality. Snapshot tests:

1. **Detect regressions**: Catch unintended changes to extraction output
2. **Document behavior**: Serve as executable documentation of expected output
3. **Enable refactoring**: Provide safety net when improving code
4. **Prevent drift**: Ensure consistency across different extractor versions

## Snapshot Test Structure

Snapshot tests are located in `engine/extraction/tests/test_snapshots.py` and follow this pattern:

```python
def test_[source]_snapshot(self):
    """Test [Source] extractor produces consistent output."""
    # 1. Load fixture data
    with open(fixture_path, 'r') as f:
        raw_data = json.load(f)

    # 2. Extract and validate
    extractor = SourceExtractor()
    result = extractor.extract(raw_data)
    validated = extractor.validate(result)

    # 3. Assert against expected snapshot
    assert validated["entity_name"] == "Expected Name"
    assert validated["latitude"] == 55.9533
    # ... more assertions
```

## Creating Snapshots

### Step 1: Create Representative Fixture Data

For each source, create a fixture file in `engine/tests/fixtures/`:

- `google_places_venue_response.json` - Google Places API response
- `sport_scotland_facility_response.json` - Sport Scotland WFS GeoJSON
- `edinburgh_council_feature_response.json` - Council GeoJSON feature
- `open_charge_map_response.json` - OpenChargeMap API response
- `serper_padel_search.json` - Serper search results
- `osm_overpass_sports_facility.json` - OSM Overpass API response

**Fixture Best Practices:**
- Use real API responses (anonymized if needed)
- Include common and edge cases (missing fields, nulls, special characters)
- Keep fixtures under 1000 lines for readability
- Add comments explaining unusual data structures

### Step 2: Run Extraction and Capture Output

```bash
# Run the extractor manually to see the output
python -c "
from engine.extraction.extractors import GooglePlacesExtractor
import json

with open('engine/tests/fixtures/google_places_venue_response.json') as f:
    data = json.load(f)

extractor = GooglePlacesExtractor()
result = extractor.extract(data['places'][0])
validated = extractor.validate(result)

print(json.dumps(validated, indent=2))
"
```

### Step 3: Write Snapshot Assertions

Based on the captured output, write assertions that verify:

1. **Required fields** are present and correct
2. **Field types** match expectations (str, float, int)
3. **Value ranges** are valid (coordinates, phone format)
4. **External IDs** are captured
5. **Entity type** is correct

Example:

```python
def test_google_places_snapshot(self):
    # ... load fixture ...

    # Verify exact values for critical fields
    assert validated["entity_name"] == "Game4Padel | Edinburgh Park"
    assert validated["external_id"] == "ChIJhwNDsAjFh0gRDARGLR5vtdI"

    # Verify types and ranges for others
    assert isinstance(validated["latitude"], float)
    assert -90 <= validated["latitude"] <= 90
```

### Step 4: Run Snapshot Tests

```bash
# Run all snapshot tests
pytest engine/extraction/tests/test_snapshots.py -v

# Run a specific snapshot test
pytest engine/extraction/tests/test_snapshots.py::TestExtractionSnapshots::test_google_places_snapshot -v
```

## Updating Snapshots

### When to Update

Update snapshots when:
- **Intentional changes**: You've improved extraction logic and want to capture the new output
- **New fields**: You've added fields to the schema
- **Bug fixes**: You've fixed extraction bugs and the new output is correct
- **Format changes**: External API responses have changed structure

### Update Process

1. **Review the Diff**:
   ```bash
   # Run the test to see what changed
   pytest engine/extraction/tests/test_snapshots.py::test_google_places_snapshot -v
   ```

   The test output will show:
   ```
   AssertionError: assert '+44 131 539 7071' == '+441315397071'
   ```

2. **Verify the Change is Intentional**:
   - Is this change expected from your code modifications?
   - Does the new output match the requirements?
   - Are there any unintended side effects?

3. **Update the Assertions**:
   ```python
   # Old assertion
   assert validated["phone"] == "+44 131 539 7071"

   # New assertion (after phone formatting improvement)
   assert validated["phone"] == "+441315397071"
   ```

4. **Document the Change**:
   ```bash
   git commit -m "test(extraction): Update Google Places snapshot for E.164 phone formatting

   Phone numbers are now formatted to E.164 standard (no spaces).
   Updated snapshot to reflect new formatting behavior."
   ```

5. **Run Full Test Suite**:
   ```bash
   # Ensure no other tests broke
   pytest engine/extraction/tests/ -v
   ```

## Snapshot Test Categories

### 1. **Exact Value Snapshots**
Verify specific values for critical fields (names, IDs, addresses):

```python
assert validated["entity_name"] == "Game4Padel | Edinburgh Park"
assert validated["external_id"] == "ChIJhwNDsAjFh0gRDARGLR5vtdI"
```

**When to use**: Critical fields that should never change for a given fixture.

### 2. **Type & Range Snapshots**
Verify types and valid ranges:

```python
assert isinstance(validated["latitude"], (int, float))
assert -90 <= validated["latitude"] <= 90
```

**When to use**: Derived or formatted fields that may vary but must be valid.

### 3. **Structure Snapshots**
Verify presence and structure of fields:

```python
assert "entity_name" in validated
assert "latitude" in validated
assert "external_ids" in discovered
```

**When to use**: Optional fields or discovered attributes.

### 4. **Consistency Snapshots**
Verify deterministic behavior:

```python
result1 = extractor.extract(raw_data)
result2 = extractor.extract(raw_data)
assert result1 == result2
```

**When to use**: Non-LLM extractors that should be fully deterministic.

## Handling LLM-Based Extractors

LLM extractors (Serper, OSM) are non-deterministic. Special handling:

### 1. Mock LLM Responses

```python
with patch("engine.extraction.llm_client.get_instructor_client") as mock_client:
    mock_response = MagicMock()
    mock_response.entity_name = "Expected Name"
    # ... set other fields ...

    mock_client.messages.create.return_value = mock_response

    # Now extraction is deterministic
    result = extractor.extract(raw_data)
```

### 2. Test Prompts Separately

Test LLM prompts in isolation:

```python
def test_serper_prompt_structure():
    """Verify Serper prompt includes required context."""
    prompt = SerperExtractor()._build_prompt(raw_data)

    assert "entity_name" in prompt
    assert "Extract structured data" in prompt
```

### 3. Validate Structure, Not Content

For LLM output, test structure rather than exact values:

```python
assert "entity_name" in validated
assert isinstance(validated["entity_name"], str)
assert len(validated["entity_name"]) > 0
```

## Troubleshooting

### Test Fails After Fixture Update

**Problem**: You updated a fixture and now the snapshot test fails.

**Solution**:
1. Check if the fixture structure changed (e.g., wrapped in array)
2. Update test to extract data correctly:
   ```python
   # Before
   raw_data = json.load(f)

   # After
   fixture_data = json.load(f)
   raw_data = fixture_data["places"][0]  # Extract from array
   ```

### Test Fails Intermittently

**Problem**: LLM-based tests sometimes pass, sometimes fail.

**Solution**: Ensure LLM calls are mocked:
```python
with patch("engine.extraction.llm_client.get_instructor_client"):
    # Test code here
```

### Test Fails on CI But Passes Locally

**Problem**: Snapshot test passes locally but fails in CI.

**Solution**:
1. Check for filesystem path differences (Windows vs Linux)
2. Ensure fixtures are committed to git
3. Verify fixture files use LF line endings (not CRLF)

### Snapshot is Too Brittle

**Problem**: Snapshot breaks frequently for insignificant changes.

**Solution**: Use type/structure assertions instead of exact values:
```python
# Too brittle
assert validated["latitude"] == 55.930189299999995

# Better
assert 55.92 < validated["latitude"] < 55.94
```

## Best Practices

1. **Keep Snapshots Focused**: Test one extractor per test function
2. **Use Representative Data**: Fixtures should reflect real-world API responses
3. **Document Assertions**: Comment why specific values are expected
4. **Run Before Committing**: Always run snapshot tests before pushing code
5. **Review Diffs Carefully**: Understand why snapshots changed before updating
6. **Version Fixtures**: Track fixture changes in git for audit trail
7. **Test Edge Cases**: Include fixtures with missing fields, nulls, special characters

## Integration with CI/CD

Snapshot tests run automatically in CI:

```yaml
# .github/workflows/test.yml
- name: Run Snapshot Tests
  run: pytest engine/extraction/tests/test_snapshots.py -v
```

If snapshots fail in CI:
1. Pull latest code
2. Run tests locally
3. Review and update snapshots if changes are intentional
4. Commit updated tests
5. Push and verify CI passes

## Related Documentation

- [Extraction Engine Overview](./extraction_engine_overview.md)
- [Adding a New Extractor](./adding_new_extractor.md)
- [Testing Strategy](./testing_strategy.md)
- [Troubleshooting Extraction](./troubleshooting_extraction.md)

---

**Last Updated**: 2026-01-17
**Maintained By**: Engineering Team
