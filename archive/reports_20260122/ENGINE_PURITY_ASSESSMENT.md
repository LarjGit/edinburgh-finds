# Engine Purity Assessment Report
**Date:** 2026-01-22
**Status:** FAILED - Extensive Legacy Terminology Remaining

## Executive Summary

The Engine Purity Remediation track (conductor/tracks/engine_purity_remediation_20260122) was incorrectly marked as complete. While critical runtime issues were resolved, **extensive legacy terminology remains throughout the codebase**. The assessment incorrectly concluded that legacy terms in tests, comments, docstrings, class names, and variable names were "acceptable."

**User Requirement:** NO trace whatsoever of old design in the code.

**Current State:** Legacy terminology is pervasive across:
- Source code (field names, class names, variable names, function names)
- Test files (extensively throughout)
- Generated files (with incorrect source file references)
- Documentation and comments
- File names

## Critical Findings

### 1. Legacy Field: `entity_type`

**Status:** Still extensively used throughout the codebase

#### Files with `entity_type` references:

**Generated Files:**
- `engine/extraction/models/entity_extraction.py:21` - **CRITICAL**
  - Contains field: `entity_type: Optional[str]`
  - File header incorrectly states: "Generated from: engine/config/schemas/listing.yaml"
  - Should be generated from entity.yaml and use `entity_class` instead

**Core Source Files:**
- `engine/ingest.py:40,56` - Contains VENUE mapping logic
  ```python
  "VENUE": "place",
  if entity_type_value in ["VENUE", "venue"]:
  ```
- `engine/run_seed.py` - References entity_type
- `engine/seed_data.py:24,28,197` - Uses legacy entity_type field with comment "Legacy field - will be mapped"
- `engine/extraction/merging.py:255,259` - Comments reference entity_type
- `engine/extraction/quarantine.py` - Contains entity_type
- `engine/extraction/entity_classifier.py` - May contain entity_type references
- `engine/extraction/attribute_splitter.py` - Contains entity_type

**Test Files (24+ files):**
- `engine/extraction/tests/test_schema_compatibility.py` - Multiple references
- `engine/extraction/tests/test_e2e.py` - Multiple test assertions using entity_type
- `engine/extraction/tests/test_snapshots.py` - Assertions checking for "VENUE"
- `engine/extraction/tests/test_seed_data_generation.py` - Test data uses entity_type
- `engine/extraction/tests/test_cli_single.py` - Mock data uses entity_type
- `engine/extraction/tests/test_cli_batch.py` - Extensive usage in test mocks
- `engine/extraction/tests/test_web_app_compatibility.py` - Uses both entity_type and entityType
- `engine/tests/test_sport_scotland_extractor.py:146` - Test "entity_type defaults to VENUE"
- `engine/tests/test_edinburgh_council_extractor.py:177` - Test "entity_type defaults to VENUE"
- `engine/tests/test_google_places_extractor.py:130` - Test "entity_type is NOT defaulted to VENUE"
- `engine/tests/test_open_charge_map_extractor.py:119,125,308` - Multiple references
- `engine/tests/test_osm_extractor.py` - 10+ references to entity_type
- `engine/tests/test_summary_synthesis.py` - Contains entity_type

**Documentation:**
- `engine/extraction/llm_cache.py:146,161` - Docstring examples use entity_type="VENUE"
- `engine/extraction/utils/SUMMARY_SYNTHESIS_EXTENSIBILITY.md` - Documentation references
- `engine/schema/generators/python_fieldspec.py` - Generator logic may reference it

### 2. Legacy Enum Value: `VENUE`

**Status:** 18+ files still reference VENUE

#### Files with `VENUE` references:

**Core Source Files:**
- `engine/ingest.py:40,56` - **CRITICAL** - Hardcoded mapping `"VENUE": "place"`
- `engine/seed_data.py:24,28,197` - Test data uses `entity_type: "VENUE"`
- `engine/config/entity_model.yaml:303` - Comment: "Entity type labels: VENUE, COACH, CLUB (replaced by...)"
- `engine/extraction/llm_cache.py:146,161` - Docstring example uses `entity_type="VENUE"`

**Test Files (extensive):**
All test files contain multiple assertions and test data using "VENUE":
- `engine/extraction/tests/test_web_app_compatibility.py` - 15+ occurrences
- `engine/extraction/tests/test_snapshots.py` - 8+ assertions `== "VENUE"`
- `engine/extraction/tests/test_seed_data_generation.py` - 10+ test data objects
- `engine/extraction/tests/test_e2e.py` - 10+ mock objects
- `engine/extraction/tests/test_schema_compatibility.py` - 8+ references
- `engine/extraction/tests/test_cli_single.py` - Mock data
- `engine/extraction/tests/test_cli_batch.py` - 10+ test objects
- `engine/tests/test_sport_scotland_extractor.py:146,152` - Assertions checking for "VENUE"
- `engine/tests/test_edinburgh_council_extractor.py:177,183` - Assertions checking for "VENUE"
- `engine/tests/test_google_places_extractor.py:130` - Test about NOT defaulting to VENUE
- `engine/tests/test_open_charge_map_extractor.py:119,125,308` - Multiple assertions
- `engine/tests/test_osm_extractor.py` - 12+ references in test expectations
- `engine/tests/test_python_generator.py:362-367` - Test expectations for VENUE_SPECIFIC_FIELDS
- `engine/schema/generators/python_fieldspec.py:82` - Comment about VENUE_SPECIFIC_FIELDS

### 3. Legacy Term: `Listing` (should be `Entity`)

**Status:** Pervasive throughout codebase - 59+ files

#### Class Names:
- `engine/tests/test_listing_merge.py:12` - **class TestListingMerger**
- `engine/tests/test_prisma_generator.py:503` - **class TestListingYAMLIntegration**

#### Variable Names (extensive usage):
- `extracted_listings` - Used in 30+ files
- `listings` - Used in 50+ files
- `listing` - Used throughout as variable name

#### Function Names:
- `engine/extraction/merging.py:193` - `merge_listings()`
- `engine/extraction/merging.py:286` - `_format_single_listing()`
- `engine/extraction/deduplication.py:322` - `find_duplicates(self, listings: List[...])`

#### File Names:
- `engine/tests/test_listing_merge.py` - **FILE NAME** needs renaming

#### Comments and Docstrings:
- `engine/extraction/merging.py:2` - "Field-level trust merging for extracted listings"
- `engine/extraction/deduplication.py:2` - "Deduplication logic for extracted listings"
- `engine/extraction/deduplication.py:27,31,72,87,134,159` - Multiple docstrings reference "listings"
- `engine/extraction/health.py:109` - `extracted_listings = await db.extractedlisting.find_many()`
- `engine/extraction/health_check.py` - Multiple function parameters named `extracted_listings`
- `engine/extraction/quarantine.py:190` - Function `_save_extracted_listing`
- Multiple test file docstrings reference "listings"

#### Generated File Metadata:
- `engine/extraction/models/entity_extraction.py:4` - **CRITICAL**
  - Header says: "Generated from: engine/config/schemas/listing.yaml"
  - But listing.yaml no longer exists - only entity.yaml exists
  - This indicates the generator metadata is stale

#### Other References:
- `engine/config/monitoring_alerts.yaml:186` - Comment "Duplicate listings detected"
- `engine/schema/generators/python_fieldspec.py:82` - Comment "LISTING_FIELDS/VENUE_SPECIFIC_FIELDS"
- `engine/ingestion/CONNECTOR_GUIDE.md:39` - "Enrich venue listings"
- `engine/docs/id_strategy.md` - May reference ListingMerger or listings

### 4. Legacy CamelCase: `entityType`

**Status:** Present in web compatibility layer tests

#### Files:
- `engine/extraction/tests/test_web_app_compatibility.py` - 17+ occurrences
  - Line 29: `entityType: true`
  - Line 44: `mock_listing.entityType = "VENUE"`
  - Line 79: `assert listing.entityType == "VENUE"`
  - Lines 151-217: Multiple test assertions and assignments
- `engine/extraction/tests/test_schema_compatibility.py` - 5 occurrences
  - Line 219, 227, 248, 258: References to entityType field

### 5. Python Cache Files with Legacy Names

**Status:** Compiled bytecode contains legacy module names

#### Files:
- `engine/extraction/models/__pycache__/venue_extraction.cpython-312.pyc`
- `engine/schema/__pycache__/listing.cpython-312.pyc`
- `engine/schema/__pycache__/listing_generated.cpython-312.pyc`
- `engine/schema/__pycache__/venue.cpython-312.pyc`
- `engine/tests/__pycache__/test_listing_merge.cpython-312-pytest-9.0.2.pyc`

**Action Required:** Delete these files and ensure source files are renamed

### 6. Test Fixture Files with Legacy Names

**Status:** Test data files use legacy terminology

#### Files:
- `engine/tests/fixtures/google_places_venue_response.json`

**Action Required:** Rename to reflect new terminology

### 7. Legacy Variable Naming Patterns

**Status:** Pervasive throughout codebase

#### Examples:
- `merge_listings()` should be `merge_entities()`
- `extracted_listings` should be `extracted_entities`
- `listings` should be `entities`
- `listing` should be `entity`
- `ListingMerger` should be `EntityMerger`
- `LISTING_FIELDS` should be `ENTITY_FIELDS` (already exists in entity.py)
- `VENUE_SPECIFIC_FIELDS` should be removed entirely
- `VENUE_FIELDS` should be removed entirely

## Remediation Requirements

### Phase 1: Critical Source Code Fixes

1. **Regenerate entity_extraction.py**
   - Update generator to use entity.yaml (not listing.yaml)
   - Replace `entity_type` field with `entity_class`
   - Update file header metadata
   - File: `engine/extraction/models/entity_extraction.py`

2. **Remove Legacy Mapping Logic**
   - Remove VENUE mapping from ingest.py
   - Remove legacy entity_type handling
   - Files: `engine/ingest.py`, `engine/seed_data.py`

3. **Rename Classes**
   - `TestListingMerger` → `TestEntityMerger`
   - `TestListingYAMLIntegration` → `TestEntityYAMLIntegration`

4. **Rename Functions**
   - `merge_listings()` → `merge_entities()`
   - `_format_single_listing()` → `_format_single_entity()`
   - `find_duplicates(listings)` → `find_duplicates(entities)`
   - `_save_extracted_listing()` → `_save_extracted_entity()`

5. **Rename Files**
   - `engine/tests/test_listing_merge.py` → `test_entity_merge.py`
   - `engine/tests/fixtures/google_places_venue_response.json` → `google_places_entity_response.json`

### Phase 2: Variable Renaming

1. **Global Find/Replace Operations**
   - `extracted_listings` → `extracted_entities`
   - `listings` → `entities`
   - `listing` → `entity` (context-aware)
   - `entity_type` → `entity_class` (in all non-legacy contexts)

2. **Function Parameters**
   - Update all function signatures to use `entities` instead of `listings`
   - Update type hints: `List[Dict]` parameters should reference entities

### Phase 3: Test File Updates

1. **Update All Test Files** (24+ files)
   - Replace `entity_type` with `entity_class`
   - Replace `"VENUE"` with appropriate entity_class values (`"place"`)
   - Replace `entityType` (camelCase) with appropriate new field
   - Update all assertions and mock data
   - Update test descriptions and docstrings

2. **Test Files Requiring Updates:**
   - test_schema_compatibility.py
   - test_web_app_compatibility.py
   - test_e2e.py
   - test_snapshots.py
   - test_seed_data_generation.py
   - test_cli_single.py
   - test_cli_batch.py
   - test_cli_source.py
   - test_sport_scotland_extractor.py
   - test_edinburgh_council_extractor.py
   - test_google_places_extractor.py
   - test_open_charge_map_extractor.py
   - test_osm_extractor.py
   - test_summary_synthesis.py
   - test_python_generator.py
   - test_listing_merge.py (also rename file)
   - test_prisma_generator.py

### Phase 4: Documentation and Comments

1. **Update Docstrings**
   - All references to "listings" → "entities"
   - All references to "venue" → "entity" or appropriate term
   - Update LLM cache examples

2. **Update Code Comments**
   - entity_model.yaml:303 - Remove VENUE, COACH, CLUB comment
   - python_fieldspec.py:82 - Remove VENUE_SPECIFIC_FIELDS comment
   - All inline comments referencing legacy terms

3. **Update Documentation Files**
   - ingestion/CONNECTOR_GUIDE.md - Replace "venue listings" with "entities"
   - extraction/utils/SUMMARY_SYNTHESIS_EXTENSIBILITY.md
   - docs/id_strategy.md - Update ListingMerger references

4. **Update Configuration**
   - monitoring_alerts.yaml:186 - "Duplicate listings" → "Duplicate entities"

### Phase 5: Cleanup

1. **Delete Python Cache Files**
   ```bash
   rm engine/extraction/models/__pycache__/venue_extraction.cpython-312.pyc
   rm engine/schema/__pycache__/listing.cpython-312.pyc
   rm engine/schema/__pycache__/listing_generated.cpython-312.pyc
   rm engine/schema/__pycache__/venue.cpython-312.pyc
   rm engine/tests/__pycache__/test_listing_merge.cpython-312-pytest-9.0.2.pyc
   ```

2. **Verify No Legacy Terms Remain**
   ```bash
   # Should return ZERO results
   grep -r "entity_type" engine/ --include="*.py" | grep -v "__pycache__"
   grep -r "VENUE" engine/ --include="*.py" --include="*.yaml" | grep -v "__pycache__"
   grep -r "Listing" engine/ --include="*.py" | grep -v "__pycache__"
   grep -r "listing" engine/ --include="*.py" | grep -v "__pycache__" | grep -v "# listing"
   grep -r "entityType" engine/ --include="*.py" | grep -v "__pycache__"
   ```

## Estimated Impact

### Files Requiring Changes: 80+
- **Source files:** 15+
- **Test files:** 24+
- **Documentation files:** 5+
- **Configuration files:** 3+
- **Generated files:** 2+ (need regeneration)
- **File renames:** 2+
- **Cache cleanup:** 5+ files

### Breaking Changes
- All extraction model code
- All test code
- Database seeding scripts
- Extraction pipeline
- Merge and deduplication logic
- Health check and monitoring

## Verification Checklist

After remediation, the following must ALL return ZERO results:

```bash
# Field name checks
grep -r "\bentity_type\b" engine/ --include="*.py" | grep -v "__pycache__" | grep -v ".pyc"

# Enum value checks
grep -r "\bVENUE\b" engine/ --include="*.py" --include="*.yaml" | grep -v "__pycache__"

# Model name checks (excluding valid uses in file paths or as substring)
grep -rw "Listing" engine/ --include="*.py" | grep -v "__pycache__"
grep -r "listing" engine/ --include="*.py" | grep -v "__pycache__" | grep -v "# listing" | grep -v "\"listing\""

# CamelCase check
grep -r "entityType" engine/ --include="*.py" | grep -v "__pycache__"

# Generator constant checks
grep -r "LISTING_FIELDS" engine/ --include="*.py" | grep -v "entity.py"
grep -r "VENUE_SPECIFIC_FIELDS" engine/ --include="*.py"
grep -r "VENUE_FIELDS" engine/ --include="*.py"
```

## Priority Order

1. **CRITICAL (Blocks Runtime):**
   - Regenerate entity_extraction.py from entity.yaml
   - Remove entity_type field from extraction model
   - Update ingest.py to remove VENUE mapping
   - Update seed_data.py

2. **HIGH (Code Quality):**
   - Rename classes (TestListingMerger, etc.)
   - Rename functions (merge_listings, etc.)
   - Rename files (test_listing_merge.py, etc.)
   - Update all variable names in source code

3. **MEDIUM (Test Quality):**
   - Update all 24+ test files
   - Update test fixtures
   - Update test docstrings

4. **LOW (Documentation):**
   - Update comments and docstrings
   - Update documentation files
   - Update configuration file comments

## Conclusion

The Engine Purity Remediation track was **prematurely marked as complete**. The assessment incorrectly concluded that legacy terminology in tests, comments, docstrings, and class names was "acceptable."

**User requirement:** NO trace whatsoever of the old design in the code.

**Current state:** Extensive legacy terminology remains in:
- Core extraction models (entity_type field)
- All test files (VENUE, entity_type)
- Class names (ListingMerger)
- Function names (merge_listings)
- Variable names (listings, extracted_listings)
- File names (test_listing_merge.py)
- Comments and documentation
- Generated file metadata

**Recommendation:** Create a new conductor track to systematically remove ALL legacy terminology according to the phased approach above.
