# Engine Purity Remediation Plan - Core Files Only
**Date:** 2026-01-22
**Strategy:** Archive legacy tests/utilities, purify core operational code only

## Philosophy

**Do NOT translate legacy tests.** Archive them and write fresh tests against the new design as needed.

**Focus:** Core operational files that actually run the system (~20 files)
**Archive:** Tests, utilities, documentation with legacy assumptions (~60 files)
**Result:** Clean, pure engine with no legacy traces

## Phase 0: Archive Legacy Files

**Goal:** Remove all non-core files from engine/ to eliminate pollution

### 0.1 Create Archive Directory
```bash
mkdir -p archive/legacy_tests_and_utilities_20260122
```

### 0.2 Archive Test Files
```bash
# Archive all test directories
mv engine/tests archive/legacy_tests_and_utilities_20260122/engine_tests
mv engine/extraction/tests archive/legacy_tests_and_utilities_20260122/extraction_tests

# Archive test fixtures
# Already moved with engine/tests
```

### 0.3 Archive Utility Scripts
```bash
# Move non-core utility scripts
mv engine/validate_extraction.py archive/legacy_tests_and_utilities_20260122/
mv engine/check_entity_data.py archive/legacy_tests_and_utilities_20260122/
mv engine/check_raw_data.py archive/legacy_tests_and_utilities_20260122/

# If these exist, archive them too:
# mv engine/inspect_db.py archive/legacy_tests_and_utilities_20260122/
```

### 0.4 Archive Legacy Documentation (Optional)
```bash
# Can optionally archive old docs to rewrite fresh later
mv engine/docs/id_strategy.md archive/legacy_tests_and_utilities_20260122/
mv engine/ingestion/CONNECTOR_GUIDE.md archive/legacy_tests_and_utilities_20260122/
mv engine/extraction/utils/SUMMARY_SYNTHESIS_EXTENSIBILITY.md archive/legacy_tests_and_utilities_20260122/
```

### 0.5 Clean Python Cache
```bash
# Delete all __pycache__ directories with legacy bytecode
find engine -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Alternative if find fails on Windows:
# Remove them manually or use PowerShell:
# Get-ChildItem -Path engine -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

### 0.6 Create Archive Index
```bash
cat > archive/legacy_tests_and_utilities_20260122/README.md << 'EOF'
# Archived Legacy Tests and Utilities
**Date:** 2026-01-22
**Reason:** Pre-purity remediation files with legacy architecture assumptions

## What's Here
- `engine_tests/` - All engine tests (entity_type, VENUE, Listing references)
- `extraction_tests/` - All extraction tests
- `validate_extraction.py` - Legacy validation script
- `check_entity_data.py` - Legacy data checker
- `check_raw_data.py` - Legacy raw data checker
- `id_strategy.md` - Legacy documentation
- `CONNECTOR_GUIDE.md` - Legacy documentation
- `SUMMARY_SYNTHESIS_EXTENSIBILITY.md` - Legacy documentation

## Why Archive?
These files encoded the OLD architecture:
- entity_type field (removed)
- VENUE enum (removed)
- Listing terminology (now Entity)
- entityType camelCase (removed)

Rather than translate 60+ files with high error risk, we archived them.
New tests will be written fresh against the NEW pure design as needed.

## Recovery
If you need to reference old test logic:
1. Look here for the pattern
2. Rewrite it against the new Entity/entity_class model
3. Don't copy-paste - rethink it fresh
EOF
```

**Verification:**
```bash
# These directories should NO LONGER EXIST:
ls engine/tests  # Should fail
ls engine/extraction/tests  # Should fail

# This should succeed:
ls archive/legacy_tests_and_utilities_20260122/engine_tests
ls archive/legacy_tests_and_utilities_20260122/extraction_tests
```

---

## Phase 1: Regenerate Core Extraction Model

**Goal:** Fix the critical entity_extraction.py file

### 1.1 Verify Source Schema (entity.yaml)

**File:** `engine/config/schemas/entity.yaml`

**Check:** Ensure NO entity_type field exists (should only have entity_class)

**Action:** Read the file and verify

**Expected:** Field around line 50-63 should be:
```yaml
- name: entity_class
  type: string
  description: "Universal entity classification (place, person, organization, event, thing)"
```

### 1.2 Check listing.yaml Status

**Check:** Verify listing.yaml does NOT exist
```bash
ls engine/config/schemas/listing.yaml  # Should fail - file should not exist
```

**Expected:** File should not exist (entity.yaml is the single source)

### 1.3 Regenerate Pydantic Extraction Model

**Command:**
```bash
cd C:\Projects\edinburgh_finds
python -m engine.schema.generate --pydantic-extraction
```

**Expected Output:**
- Regenerates: `engine/extraction/models/entity_extraction.py`
- File header should say: "Generated from: engine/config/schemas/entity.yaml"
- Should have `entity_class` field, NOT `entity_type`

### 1.4 Verify Generated File

**File:** `engine/extraction/models/entity_extraction.py`

**Check Line 4:** Should say `Generated from: engine/config/schemas/entity.yaml` (NOT listing.yaml)

**Check for entity_class field (should exist):**
```bash
grep "entity_class:" engine/extraction/models/entity_extraction.py
```
**Expected:** Should find the field definition

**Check for entity_type field (should NOT exist):**
```bash
grep "entity_type:" engine/extraction/models/entity_extraction.py
```
**Expected:** Should return NOTHING (exit code 1)

**Verification:**
```bash
# This should PASS
grep "entity_class:" engine/extraction/models/entity_extraction.py

# This should FAIL (no matches)
! grep "entity_type:" engine/extraction/models/entity_extraction.py
```

---

## Phase 2: Core Variable Renaming (Source Files)

**Goal:** Rename all "listing" references to "entity" in operational code

### 2.1 Update Merging Module

**File:** `engine/extraction/merging.py`

**Changes:**
1. **Line 2** - Docstring: "Field-level trust merging for extracted listings"
   → "Field-level trust merging for extracted entities"

2. **Line 193** - Function name: `def merge_listings()` → `def merge_entities()`

3. **Line 195** - Docstring: "Merge multiple extracted listings into a single listing"
   → "Merge multiple extracted entities into a single entity"

4. **Line 198** - Parameter: `extracted_listings: List[Dict[str, Any]]`
   → `extracted_entities: List[Dict[str, Any]]`

5. **Line 208** - Return call: `return self._format_single_listing(extracted_listings[0])`
   → `return self._format_single_entity(extracted_entities[0])`

6. **Line 212** - Variable: `for listing in extracted_listings:`
   → `for entity in extracted_entities:`

7. **Line 225** - Variable: `for listing in extracted_listings:`
   → `for entity in extracted_entities:`

8. **Line 255** - Comment: "# Determine entity_type (should be consistent across all listings)"
   → "# Determine entity_class (should be consistent across all entities)"

9. **Line 259** - Variable: `for listing in extracted_listings`
   → `for entity in extracted_entities`

10. **Line 280** - Dict key: `"sources": [listing["source"] for listing in extracted_listings]`
    → `"sources": [entity["source"] for entity in extracted_entities]`

11. **Line 281** - Variable: `"source_count": len(extracted_listings)`
    → `"source_count": len(extracted_entities)`

12. **Line 286** - Function name: `def _format_single_listing()` → `def _format_single_entity()`

13. **Line 286** - Parameter: `listing: Dict[str, Any]` → `entity: Dict[str, Any]`

14. **Lines 310-328** - Function `_merge_discovered_attributes`:
    - Parameter: `extracted_listings` → `extracted_entities`
    - Variables: `for listing in extracted_listings` → `for entity in extracted_entities`

15. **Lines 348-357** - Function `_merge_external_ids`:
    - Parameter: `extracted_listings` → `extracted_entities`
    - Variables: `for listing in extracted_listings` → `for entity in extracted_entities`

**Quick Approach:** Use find/replace in the file:
- `extracted_listings` → `extracted_entities` (all occurrences)
- `listing` → `entity` (be careful with substrings like "listing" in comments)
- `merge_listings` → `merge_entities`
- `_format_single_listing` → `_format_single_entity`

### 2.2 Update Deduplication Module

**File:** `engine/extraction/deduplication.py`

**Changes:**
1. **Line 2** - Docstring: "Deduplication logic for extracted listings"
   → "Deduplication logic for extracted entities"

2. **Line 27** - Docstring: "Matches listings based on external IDs"
   → "Matches entities based on external IDs"

3. **Line 31** - Docstring: "Match two listings based on external IDs"
   → "Match two entities based on external IDs"

4. **Line 72** - Docstring: "Matches listings based on slugs"
   → "Matches entities based on slugs"

5. **Line 87** - Docstring: "Match two listings based on slugs"
   → "Match two entities based on slugs"

6. **Line 134** - Docstring: "Matches listings based on name similarity"
   → "Matches entities based on name similarity"

7. **Line 159** - Docstring: "Match two listings based on fuzzy name"
   → "Match two entities based on fuzzy name"

8. **Line 295** - Docstring: "Find if two listings match"
   → "Find if two entities match"

9. **Line 322** - Function signature: `def find_duplicates(self, listings: List[Dict])`
   → `def find_duplicates(self, entities: List[Dict])`

10. **Line 324** - Docstring: "Find all duplicate groups in a list of listings"
    → "Find all duplicate groups in a list of entities"

11. **Line 327** - Parameter doc: `listings: List of listings to check`
    → `entities: List of entities to check`

12. **Line 330** - Return doc: "each group contains 2+ duplicate listings"
    → "each group contains 2+ duplicate entities"

13. **Line 332-351** - Variables in function:
    - `if len(listings) < 2:` → `if len(entities) < 2:`
    - `for i, listing1 in enumerate(listings):` → `for i, entity1 in enumerate(entities):`
    - `for j in range(i + 1, len(listings)):` → `for j in range(i + 1, len(entities)):`
    - `listing2 = listings[j]` → `entity2 = entities[j]`
    - All other listing1/listing2 refs → entity1/entity2

**Quick Approach:** Find/replace:
- `listings` → `entities`
- `listing1` → `entity1`
- `listing2` → `entity2`

### 2.3 Update Quarantine Module

**File:** `engine/extraction/quarantine.py`

**Changes:**
1. **Line 190** - Function name: `async def _save_extracted_listing()`
   → `async def _save_extracted_entity()`

2. Update all callers of this function in the same file

3. Any variables named `listing` → `entity`

### 2.4 Update Health Modules

**File:** `engine/extraction/health.py`

**Changes:**
1. **Line 109** - Variable: `extracted_listings = await db.extractedlisting.find_many()`
   → `extracted_entities = await db.extractedentity.find_many()`

   **NOTE:** This depends on Prisma model name. If model is still `ExtractedListing`, keep that but update variable name:
   ```python
   extracted_entities = await db.extractedlisting.find_many()  # Model name unchanged
   ```

2. **Line 118** - Parameter: `extracted_listings=extracted_listings`
   → `extracted_entities=extracted_entities`

**File:** `engine/extraction/health_check.py`

**Changes:**
1. **Line 93** - Parameter: `extracted_listings: List[Any]`
   → `extracted_entities: List[Any]`

2. **Line 99** - Variable: `for record in extracted_listings`
   → `for record in extracted_entities`

3. **Line 131** - Parameter: `extracted_listings: List[Any]`
   → `extracted_entities: List[Any]`

4. **Line 142** - Variable: `for listing in extracted_listings:`
   → `for entity in extracted_entities:`

5. **Line 168** - Parameter: `extracted_listings: List[Any]`
   → `extracted_entities: List[Any]`

6. **Line 175** - Variable: `total = len(extracted_listings)`
   → `total = len(extracted_entities)`

7. **Line 180** - Variable: `for record in extracted_listings:`
   → `for record in extracted_entities:`

8. **Line 230** - Parameter: `extracted_listings: List[Any]`
   → `extracted_entities: List[Any]`

9. **Line 244** - Variable: `for record in extracted_listings:`
   → `for record in extracted_entities:`

10. **Line 288** - Parameters: `extracted_listings: List[Any]`
    → `extracted_entities: List[Any]`

11. **Lines 298-308** - Function calls - update all parameter names:
    - `extracted_listings` → `extracted_entities`

**Quick Approach:** Find/replace in both files:
- `extracted_listings` → `extracted_entities`
- `listing` → `entity` (context-aware)

---

## Phase 3: Remove Legacy Logic

**Goal:** Remove all entity_type and VENUE hardcoded logic

### 3.1 Update Ingest Script

**File:** `engine/ingest.py`

**Changes:**

1. **Lines 40-41** - REMOVE this entire mapping dict:
   ```python
   # DELETE THIS:
   "VENUE": "place",
   ```

2. **Lines 56-57** - REMOVE or UPDATE this legacy preprocessing:
   ```python
   # DELETE OR UPDATE:
   if entity_type_value in ["VENUE", "venue"]:
   ```

3. **Context:** Read the file first to understand the full context, then remove legacy entity_type handling

**Verification:**
```bash
# Should return NOTHING
grep "VENUE" engine/ingest.py
grep "entity_type" engine/ingest.py
```

### 3.2 Update Seed Data Script

**File:** `engine/seed_data.py`

**Changes:**

1. **Lines 24-28** - REMOVE entity_type field from test data:
   ```python
   # OLD:
   "entity_type": "VENUE",  # Legacy field - will be mapped

   # NEW:
   # Remove this field entirely
   ```

2. **Line 197** - REMOVE comment about mapping:
   ```python
   # DELETE:
   # Map legacy entity_type="VENUE" to new entity_class="place"
   ```

3. **Update logic** to use entity_class directly if needed, or let the engine infer it

**Verification:**
```bash
# Should return NOTHING
grep "VENUE" engine/seed_data.py
grep "entity_type" engine/seed_data.py | grep -v "# removed"
```

### 3.3 Update Entity Classifier

**File:** `engine/extraction/entity_classifier.py`

**Action:** Read file and check for any entity_type references

**Expected:** Should already be pure, but verify

**Verification:**
```bash
grep "entity_type" engine/extraction/entity_classifier.py
# Should return nothing or only entity_class references
```

### 3.4 Update Attribute Splitter

**File:** `engine/extraction/attribute_splitter.py`

**Action:** Read file and check for entity_type references

**Expected:** Should already be pure, but verify

**Verification:**
```bash
grep "entity_type" engine/extraction/attribute_splitter.py
```

---

## Phase 4: Configuration Cleanup

**Goal:** Clean up comments and documentation in config files

### 4.1 Update Entity Model YAML

**File:** `engine/config/entity_model.yaml`

**Change:**
- **Line 303** - REMOVE or UPDATE comment:
  ```yaml
  # DELETE OR UPDATE:
  # - Entity type labels: VENUE, COACH, CLUB (replaced by entity_class + canonical_roles)

  # NEW (if keeping comment):
  # - Legacy entity type labels removed - now using entity_class + canonical_roles
  ```

**Verification:**
```bash
grep "VENUE" engine/config/entity_model.yaml
# Should return nothing
```

### 4.2 Update Monitoring Alerts

**File:** `engine/config/monitoring_alerts.yaml`

**Change:**
- **Line 186** - UPDATE comment:
  ```yaml
  # OLD:
  # Duplicate listings detected

  # NEW:
  # Duplicate entities detected
  ```

**Verification:**
```bash
grep "listing" engine/config/monitoring_alerts.yaml
# Should return nothing (or only in alert messages if appropriate)
```

---

## Phase 5: Update Extractors

**Goal:** Ensure extractors don't use legacy terminology in variables

### 5.1 Review Extractor Files

**Files to check:**
- `engine/extraction/extractors/serper_extractor.py`
- `engine/extraction/extractors/osm_extractor.py`
- `engine/extraction/extractors/google_places_extractor.py`
- `engine/extraction/extractors/sport_scotland_extractor.py`
- `engine/extraction/extractors/edinburgh_council_extractor.py`
- `engine/extraction/extractors/open_charge_map_extractor.py`

**Action for each:**
1. Read the file
2. Find any variables named `listing` or `extracted_listing`
3. Rename to `entity` or `extracted_entity`
4. Update docstrings if they mention "venue listings"

**Expected:** Most extractors should already be clean from previous remediation

**Verification per file:**
```bash
grep -n "listing" engine/extraction/extractors/serper_extractor.py
grep -n "VENUE" engine/extraction/extractors/serper_extractor.py
# Repeat for each extractor
```

### 5.2 Update Base Extractor

**File:** `engine/extraction/base.py`

**Action:**
1. Check for variables named `listing`
2. Rename to `entity`
3. Update docstrings

**Verification:**
```bash
grep -n "listing" engine/extraction/base.py | grep -v "# entity"
```

---

## Phase 6: Schema Generator Cleanup

**Goal:** Remove VENUE_SPECIFIC_FIELDS and LISTING_FIELDS legacy references

### 6.1 Update Python FieldSpec Generator

**File:** `engine/schema/generators/python_fieldspec.py`

**Change:**
- **Line 82** - REMOVE or UPDATE comment:
  ```python
  # OLD:
  # Always need List for the LISTING_FIELDS/VENUE_SPECIFIC_FIELDS declaration

  # NEW:
  # Always need List for the ENTITY_FIELDS declaration
  ```

**Action:** Read the file and check for:
- References to `LISTING_FIELDS` (should now be `ENTITY_FIELDS` which exists in entity.py)
- References to `VENUE_SPECIFIC_FIELDS` (should be removed)
- References to `VENUE_FIELDS` (should be removed)

**Expected:** Generator should produce `ENTITY_FIELDS` constant, not LISTING/VENUE variants

**Verification:**
```bash
grep "VENUE" engine/schema/generators/python_fieldspec.py
grep "LISTING" engine/schema/generators/python_fieldspec.py
```

---

## Phase 7: LLM Cache Docstring Update

**Goal:** Update example code in docstrings

### 7.1 Update LLM Cache

**File:** `engine/extraction/llm_cache.py`

**Changes:**
- **Line 146** - Docstring example parameter:
  ```python
  # OLD:
  entity_type: Entity type (e.g., "VENUE", "COACH")

  # NEW:
  entity_class: Entity class (e.g., "place", "person", "organization")
  ```

- **Line 161** - Example call:
  ```python
  # OLD:
  ...     entity_type="VENUE",

  # NEW:
  ...     entity_class="place",
  ```

**Verification:**
```bash
grep "VENUE" engine/extraction/llm_cache.py
grep "entity_type" engine/extraction/llm_cache.py
```

---

## Phase 8: CLI and Runner Scripts

**Goal:** Ensure CLI scripts use pure terminology

### 8.1 Update Extraction CLI

**File:** `engine/extraction/run.py`

**Action:**
1. Check for variables named `listing` or `extracted_listing`
2. Rename to `entity` or `extracted_entity`

**Verification:**
```bash
grep -n "listing" engine/extraction/run.py | grep -v "# entity"
```

### 8.2 Update Seed Runner

**File:** `engine/run_seed.py`

**Action:**
1. Check for entity_type references
2. Ensure it works with new seed_data.py

**Verification:**
```bash
grep "entity_type" engine/run_seed.py
```

### 8.3 Update Schema CLI

**File:** `engine/schema/cli.py`

**Action:**
1. Check for references to listing.yaml
2. Ensure it only works with entity.yaml

**Verification:**
```bash
grep "listing" engine/schema/cli.py
```

---

## Phase 9: Final Verification

**Goal:** Confirm ZERO legacy traces in core engine code

### 9.1 Run Comprehensive Greps

```bash
cd C:\Projects\edinburgh_finds

# Check for entity_type field (should only be in entity_class contexts)
echo "=== Checking for entity_type ==="
grep -r "\bentity_type\b" engine/ --include="*.py" | grep -v "__pycache__"

# Check for VENUE enum
echo "=== Checking for VENUE ==="
grep -r "\bVENUE\b" engine/ --include="*.py" --include="*.yaml" | grep -v "__pycache__"

# Check for Listing class/variable names (excluding valid substring usage)
echo "=== Checking for Listing ==="
grep -rw "Listing" engine/ --include="*.py" | grep -v "__pycache__" | grep -v "entity.py"

# Check for listing variables (excluding comments)
echo "=== Checking for listing variables ==="
grep -r "\blisting\b" engine/ --include="*.py" | grep -v "__pycache__" | grep -v "# " | grep -v '"""'

# Check for entityType camelCase
echo "=== Checking for entityType ==="
grep -r "entityType" engine/ --include="*.py" | grep -v "__pycache__"

# Check for legacy generator constants
echo "=== Checking for legacy constants ==="
grep -r "LISTING_FIELDS" engine/ --include="*.py" | grep -v "entity.py" | grep -v "__pycache__"
grep -r "VENUE_SPECIFIC_FIELDS" engine/ --include="*.py" | grep -v "__pycache__"
grep -r "VENUE_FIELDS" engine/ --include="*.py" | grep -v "__pycache__"
```

### 9.2 Expected Results

**ALL commands should return ZERO results** (or only acceptable references like comments about migration)

### 9.3 Positive Verification

```bash
# These SHOULD exist and return results:
echo "=== Verifying entity_class exists ==="
grep -r "entity_class" engine/extraction/models/entity_extraction.py

echo "=== Verifying merge_entities exists ==="
grep -r "def merge_entities" engine/extraction/merging.py

echo "=== Verifying ENTITY_FIELDS exists ==="
grep -r "ENTITY_FIELDS" engine/schema/entity.py
```

---

## Phase 10: Test Run

**Goal:** Verify the engine still works

### 10.1 Regenerate Schema

```bash
python -m engine.schema.generate
```

**Expected:** No errors, files regenerated successfully

### 10.2 Run Seed Script (if applicable)

```bash
python engine/run_seed.py
```

**Expected:** Should work with new entity_class model

### 10.3 Check Imports

```bash
python -c "from engine.extraction.models.entity_extraction import EntityExtraction; print(EntityExtraction.model_fields.keys())"
```

**Expected:** Should show fields including 'entity_class', NOT 'entity_type'

---

## Summary Checklist

- [ ] **Phase 0:** Archived all test files and utilities
- [ ] **Phase 0:** Cleaned __pycache__ directories
- [ ] **Phase 0:** Created archive index README
- [ ] **Phase 1:** Regenerated entity_extraction.py from entity.yaml
- [ ] **Phase 1:** Verified entity_class field exists, entity_type removed
- [ ] **Phase 2:** Renamed variables in merging.py
- [ ] **Phase 2:** Renamed variables in deduplication.py
- [ ] **Phase 2:** Renamed variables in quarantine.py
- [ ] **Phase 2:** Renamed variables in health.py and health_check.py
- [ ] **Phase 3:** Removed VENUE mapping from ingest.py
- [ ] **Phase 3:** Removed entity_type from seed_data.py
- [ ] **Phase 3:** Verified entity_classifier.py is pure
- [ ] **Phase 3:** Verified attribute_splitter.py is pure
- [ ] **Phase 4:** Cleaned entity_model.yaml comments
- [ ] **Phase 4:** Updated monitoring_alerts.yaml
- [ ] **Phase 5:** Updated all 6 extractors
- [ ] **Phase 5:** Updated base.py extractor
- [ ] **Phase 6:** Updated python_fieldspec.py generator
- [ ] **Phase 7:** Updated llm_cache.py docstrings
- [ ] **Phase 8:** Verified run.py CLI
- [ ] **Phase 8:** Verified run_seed.py
- [ ] **Phase 8:** Verified schema cli.py
- [ ] **Phase 9:** Ran all verification greps - ZERO legacy terms
- [ ] **Phase 10:** Test run successful

---

## Files Modified Summary

**Core Files (~20):**
1. engine/extraction/models/entity_extraction.py (regenerated)
2. engine/extraction/merging.py
3. engine/extraction/deduplication.py
4. engine/extraction/quarantine.py
5. engine/extraction/health.py
6. engine/extraction/health_check.py
7. engine/extraction/base.py
8. engine/extraction/run.py
9. engine/extraction/llm_cache.py
10. engine/extraction/entity_classifier.py (verify only)
11. engine/extraction/attribute_splitter.py (verify only)
12. engine/extraction/extractors/serper_extractor.py
13. engine/extraction/extractors/osm_extractor.py
14. engine/extraction/extractors/google_places_extractor.py
15. engine/extraction/extractors/sport_scotland_extractor.py
16. engine/extraction/extractors/edinburgh_council_extractor.py
17. engine/extraction/extractors/open_charge_map_extractor.py
18. engine/ingest.py
19. engine/seed_data.py
20. engine/run_seed.py
21. engine/schema/cli.py
22. engine/schema/generators/python_fieldspec.py
23. engine/config/entity_model.yaml
24. engine/config/monitoring_alerts.yaml

**Files Archived (~60+):**
- All of engine/tests/ (20+ files)
- All of engine/extraction/tests/ (10+ files)
- Utility scripts (3+ files)
- Documentation (3+ files)
- All __pycache__ directories

---

## Post-Remediation: Writing New Tests

When you need tests in the future:

### Write Against NEW Model
```python
# NEW TEST PATTERN
def test_merge_entities():
    """Test merging multiple entities into one."""
    entities = [
        {
            "entity_name": "Test Entity",
            "entity_class": "place",  # NOT entity_type
            "canonical_roles": ["provides_facility"],
            # ...
        }
    ]
    merged = merger.merge_entities(entities)  # NOT merge_listings
    assert merged["entity_class"] == "place"
```

### Don't Reference Old Tests
- Don't copy-paste from archive
- Think fresh about what needs testing
- Test the NEW contracts
- Use NEW terminology from day one

---

## Conclusion

This plan focuses on ~20 core operational files, archives the rest.

**Result:** Clean, pure engine with no legacy traces and no risk of test translation errors.
