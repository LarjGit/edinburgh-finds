# COMPLETE ENGINE PURITY: DETAILED IMPLEMENTATION SPECIFICATION

**Author**: Claude (AI Assistant)
**Date**: 2026-01-21
**Purpose**: Comprehensive guide to eliminate ALL vertical-specific concepts from the engine layer

---

## EXECUTIVE SUMMARY

Your engine is **85% vertical-agnostic** but has critical remaining violations that block true horizontal scaling. This document provides an exhaustive account of **every change required** to achieve 100% engine purity with **zero legacy artifacts**.

**What your advisor identified:**
1. **entityType field** - Carries vertical meaning (VENUE, COACH)
2. **Category model** - Potentially vertical-specific taxonomy living in engine DB

**What this guide delivers:**
- Complete inventory of all violations
- Step-by-step fix for each violation
- Validation checklist to prove purity
- Implementation timeline (6 sprints)

---

## TABLE OF CONTENTS

1. [Current State Assessment](#part-1-current-state-assessment)
2. [Required Changes (Exhaustive)](#part-2-required-changes-exhaustive)
3. [Validation & Verification](#part-3-validation--verification)
4. [Implementation Order](#part-4-implementation-order)
5. [Migration Safety](#part-5-migration-safety)
6. [Post-Completion Validation](#part-6-post-completion-validation)
7. [Appendices](#appendices)

---

## PART 1: CURRENT STATE ASSESSMENT

### Critical Violations (Must Fix)

#### 1. **EntityType Enum** ⚠️ **PRIMARY VIOLATION**

**Location**: `engine/schema/types.py`

```python
class EntityType(str, Enum):
    VENUE = "VENUE"         # Sports vertical
    RETAILER = "RETAILER"   # Commerce vertical
    COACH = "COACH"         # Sports vertical
    INSTRUCTOR = "INSTRUCTOR" # Sports vertical
    CLUB = "CLUB"           # Sports vertical
    LEAGUE = "LEAGUE"       # Sports vertical
    EVENT = "EVENT"         # Borderline acceptable
    TOURNAMENT = "TOURNAMENT" # Sports vertical
```

**Why it's a violation**:
- VENUE, COACH, INSTRUCTOR are sports-specific vocabulary
- Blocks adding wine/restaurant verticals without code changes
- Should use `entity_class` (place, person, organization, event, thing) instead

**Impact**: 8 files reference `EntityType.VENUE`, `EntityType.COACH`, etc.

---

#### 2. **entityType Field in Schema** ⚠️ **PRIMARY VIOLATION**

**Locations**:
- `engine/config/schemas/listing.yaml` (lines 51-61)
- `web/prisma/schema.prisma` (line 38: `entityType String`)
- `engine/schema/listing.py` (line 49-54: generated from YAML)

**Current state**:
```yaml
# listing.yaml
- name: entity_type
  type: string
  description: Type of entity (venue, retailer, cafe, event, members_club, etc)
  required: true
  python:
    type_annotation: "EntityType"  # References the enum
```

```prisma
// schema.prisma
model Listing {
  entityType   String    // ❌ Should be deleted
  entity_class String    // ✅ This should be the only one
}
```

**Why it's a violation**:
- Description mentions "venue, retailer, cafe" (vertical vocabulary)
- Uses EntityType enum (see violation #1)
- Duplicates `entity_class` which is universal

**What exists correctly**: `entity_class` field already exists and is properly universal

---

#### 3. **Vertical-Specific Schema Files** ⚠️ **MODERATE VIOLATION**

**Files**:
- `engine/config/schemas/venue.yaml` (exists)
- `engine/schema/venue.py` (deleted according to git status, but may still be referenced)
- `engine/schema/winery.py` (156 lines, exists)
- `engine/config/schemas/winery.yaml` (exists)

**Why it's a violation**:
- "venue" and "winery" are vertical-specific entity types
- In universal engine, there should be ONE schema: `listing.yaml`
- Entity-specific behavior belongs in lens layer, not engine schemas

**Current git status shows**:
```
D engine/schema/venue.py     # Deleted but not committed
```

---

#### 4. **Extractors Defaulting to EntityType.VENUE** ⚠️ **HIGH VIOLATION**

**Affected files** (6 extractors):
- `engine/extraction/extractors/edinburgh_council_extractor.py`
- `engine/extraction/extractors/google_places_extractor.py`
- `engine/extraction/extractors/open_charge_map_extractor.py`
- `engine/extraction/extractors/sport_scotland_extractor.py`
- `engine/extraction/extractors/osm_extractor.py`
- `engine/extraction/extractors/serper_extractor.py`

**Example violation**:
```python
# edinburgh_council_extractor.py:102
extracted["entity_type"] = EntityType.VENUE.value  # Default to VENUE

# google_places_extractor.py:296
if is_field_in_schema(key, entity_type=EntityType.VENUE):
```

**Why it's a violation**:
- Hardcodes VENUE assumption (sports vertical)
- Extractors should be vertical-agnostic
- Should populate `entity_class` using `entity_classifier.py` logic instead

---

#### 5. **Category Model - Ambiguous Status** ⚠️ **CRITICAL DECISION NEEDED**

**Location**: `web/prisma/schema.prisma`

```prisma
model Category {
  id          String    @id @default(cuid())
  name        String    @unique
  slug        String    @unique
  description String?
  image       String?
  listings    Listing[] @relation("CategoryToListing")
}
```

**Why this needs analysis**:
- **If Category stores Edinburgh Finds taxonomy** ("Best Brunch", "Dog Friendly"): This is **lens-specific** and violates purity
- **If Category stores universal categories**: Could remain in engine

**Current evidence suggests lens-specific**:
- `engine/seed_data.py` creates Category entries
- `engine/extraction/utils/category_mapper.py` maps to canonical categories
- `engine/config/canonical_categories.yaml` exists (taxonomy file)

**Your advisor's point**: If Category = "Best brunch", that's **lens taxonomy** living in engine DB

---

#### 6. **canonical_categories.yaml File** ⚠️ **MODERATE VIOLATION**

**Location**: `engine/config/canonical_categories.yaml`

**Referenced by**:
- `engine/extraction/utils/category_mapper.py`
- Multiple tests in `engine/tests/test_categories.py`

**Why it's a violation**:
- "Canonical categories" imply a **controlled taxonomy**
- Taxonomies are vertical-specific (sports categories ≠ wine categories)
- Should live in lens layer as mapping rules

**Note**: Your listing.yaml already has:
```yaml
- name: categories
  type: list[string]
  description: Raw free-form categories detected by the LLM (uncontrolled labels)
```

This is **correct** (opaque extraction), but canonical_categories.yaml suggests **interpretation** is happening in engine.

---

#### 7. **schema_utils.py Legacy References** ⚠️ **LOW VIOLATION**

**Location**: `engine/extraction/schema_utils.py:23-39`

```python
def _normalize_entity_type(entity_type: Optional[object]) -> EntityType:
    """
    Note: VENUE is deprecated - use entity_class (place/person/organization/event/thing)
    """
    if normalized == "VENUE":
        return EntityType.PLACE  # Legacy mapping
```

**Why it's a violation**:
- Function still exists to support legacy EntityType enum
- Should be deleted entirely once EntityType enum is removed

---

### What's Already Correct ✅

These elements are properly vertical-agnostic:

1. **✅ entity_class field** - Uses universal values (place, person, organization, event, thing)
2. **✅ canonical_* dimension arrays** - Opaque strings with no interpretation
3. **✅ entity_classifier.py** - Uses structural logic only (no vertical keywords)
4. **✅ entity_model.yaml** - 100% universal, no vertical concepts
5. **✅ modules JSONB structure** - Flexible, namespaced, no vertical modules in engine
6. **✅ Lens layer exists** - `lenses/edinburgh_finds/lens.yaml` and `lenses/wine_discovery/lens.yaml`

---

## PART 2: REQUIRED CHANGES (EXHAUSTIVE)

### Phase 1: Database Schema Surgery

#### Task 1.1: Remove entityType from Prisma Schema

**File**: `web/prisma/schema.prisma`

**Change**:
```diff
model Listing {
  id           String     @id @default(cuid())
  entity_name  String
- entityType   String     // DELETE THIS LINE
  entity_class String     // Keep this, make it required
  slug         String     @unique
  ...
}
```

**Additional change**:
```diff
- @@index([entityType])    // DELETE THIS INDEX
+ @@index([entity_class])  // Already exists or add if missing
```

---

#### Task 1.2: Remove entity_type from listing.yaml

**File**: `engine/config/schemas/listing.yaml`

**Change**: Delete lines 51-61

```diff
- - name: entity_type
-   type: string
-   description: Type of entity (venue, retailer, cafe, event, members_club, etc)
-   nullable: false
-   required: true
-   index: true
-   python:
-     type_annotation: "EntityType"
-   prisma:
-     name: entityType
-     type: "String"
```

**Additional change**: Make entity_class required and non-excluded

```diff
  - name: entity_class
    type: string
    description: "Universal entity classification (place, person, organization, event, thing)"
-   nullable: true
+   nullable: false
-   exclude: true  # Populated by extraction engine
+   required: true
    index: true
```

---

#### Task 1.3: Regenerate Prisma Schema

**Command**:
```bash
python -m engine.schema.generate
```

**Verification**:
- `engine/schema/listing.py` should NOT have `entity_type` field
- `web/prisma/schema.prisma` should NOT have `entityType` field

---

#### Task 1.4: Create Prisma Migration

**Command**:
```bash
cd web
npx prisma migrate dev --name remove_entity_type_field
```

**What this does**:
- Drops `entityType` column from Listing table
- Removes `entityType` index
- Makes `entity_class` NOT NULL (if it has data)

**⚠️ MIGRATION WILL FAIL IF**:
- Existing rows have NULL entity_class
- You need to populate entity_class BEFORE making it required

**Data migration strategy** (if needed):
```sql
-- Map old entityType to new entity_class
UPDATE Listing SET entity_class =
  CASE
    WHEN entityType IN ('VENUE', 'RETAILER') THEN 'place'
    WHEN entityType IN ('COACH', 'INSTRUCTOR') THEN 'person'
    WHEN entityType IN ('CLUB', 'LEAGUE') THEN 'organization'
    WHEN entityType = 'EVENT' THEN 'event'
    WHEN entityType = 'TOURNAMENT' THEN 'event'
    ELSE 'thing'
  END
WHERE entity_class IS NULL;

-- Then make NOT NULL and drop old column
ALTER TABLE Listing ALTER COLUMN entity_class SET NOT NULL;
ALTER TABLE Listing DROP COLUMN entityType;
```

---

### Phase 2: Delete EntityType Enum

#### Task 2.1: Delete EntityType Enum Entirely

**File**: `engine/schema/types.py`

**Change**: Delete the ENTIRE file or delete the enum

```diff
- from enum import Enum
-
- class EntityType(str, Enum):
-     VENUE = "VENUE"
-     RETAILER = "RETAILER"
-     COACH = "COACH"
-     INSTRUCTOR = "INSTRUCTOR"
-     CLUB = "CLUB"
-     LEAGUE = "LEAGUE"
-     EVENT = "EVENT"
-     TOURNAMENT = "TOURNAMENT"
```

**Leave file empty** or delete it entirely. If other code uses this file, keep an empty file:

```python
# engine/schema/types.py
# This file intentionally left empty.
# EntityType enum has been removed in favor of universal entity_class.
# Use entity_class values: place, person, organization, event, thing
```

---

#### Task 2.2: Remove All EntityType Imports

**Files to update** (8 files):

1. `engine/extraction/extractors/edinburgh_council_extractor.py`
2. `engine/extraction/extractors/google_places_extractor.py`
3. `engine/extraction/extractors/open_charge_map_extractor.py`
4. `engine/extraction/extractors/sport_scotland_extractor.py`
5. `engine/extraction/extractors/osm_extractor.py`
6. `engine/extraction/extractors/serper_extractor.py`
7. `engine/extraction/schema_utils.py`
8. `engine/ingest.py`

**Change for all**:
```diff
- from engine.schema.types import EntityType
```

**Test files**:
- `engine/tests/test_enum_validation.py`
- `engine/tests/test_schema_utils.py`

---

#### Task 2.3: Replace EntityType Usage in Extractors

**Pattern to find**:
```bash
grep -rn "EntityType\." engine/extraction/extractors/
```

**Replace all instances**:

**Example: edinburgh_council_extractor.py**
```diff
- extracted["entity_type"] = EntityType.VENUE.value  # Default to VENUE
+ # entity_class will be determined by entity_classifier.py
+ # No default needed - classifier handles it
```

**Example: google_places_extractor.py**
```diff
- if is_field_in_schema(key, entity_type=EntityType.VENUE):
+ if is_field_in_schema(key):  # entity_type parameter no longer needed
```

**Example: osm_extractor.py**
```diff
- self.schema_fields = get_extraction_fields(entity_type="VENUE")
+ self.schema_fields = get_extraction_fields()  # Universal fields
```

---

#### Task 2.4: Update schema_utils.py

**File**: `engine/extraction/schema_utils.py`

**Delete the entire _normalize_entity_type function**:
```diff
- def _normalize_entity_type(entity_type: Optional[object]) -> EntityType:
-     """
-     Normalize entity_type to EntityType enum.
-     Note: VENUE is deprecated - use entity_class (place/person/organization/event/thing)
-     """
-     # ... delete entire function
```

**Update get_extraction_fields**:
```diff
- def get_extraction_fields(entity_type: Optional[object] = None) -> List[FieldSpec]:
+ def get_extraction_fields() -> List[FieldSpec]:
      """
-     Get schema fields that should be extracted (universal LISTING_FIELDS only).
+     Get universal schema fields for extraction.

      Engine-Lens Architecture:
      - All entity types use LISTING_FIELDS (vertical-agnostic)
      - Vertical-specific data goes into modules JSON field
      """
-     # Always return universal listing fields regardless of entity type
      return listing.get_extraction_fields()
```

**Update is_field_in_schema**:
```diff
- def is_field_in_schema(field_name: str, entity_type: Optional[object] = None) -> bool:
+ def is_field_in_schema(field_name: str) -> bool:
      """
      Check whether a field is part of the extraction schema.
      """
-     return any(field.name == field_name for field in get_extraction_fields(entity_type))
+     return any(field.name == field_name for field in get_extraction_fields())
```

---

### Phase 3: Delete Vertical Schema Files

#### Task 3.1: Delete Vertical Schema YAML Files

**Files to delete**:
```bash
rm engine/config/schemas/venue.yaml
rm engine/config/schemas/winery.yaml
```

**Verification**: Only `listing.yaml` should remain
```bash
ls engine/config/schemas/
# Expected output: listing.yaml only
```

---

#### Task 3.2: Delete Generated Vertical Schema Python Files

**Files to delete**:
```bash
rm engine/schema/venue.py  # May already be deleted (git status shows 'D')
rm engine/schema/winery.py
```

**Verification**:
```bash
ls engine/schema/*.py
# Expected: __init__.py, core.py, listing.py, types.py (empty), parser.py, generator.py, cli.py
```

---

#### Task 3.3: Remove Vertical Schema Imports

**Files to check**:
- `engine/schema/__init__.py`
- Any test files importing venue or winery schemas

**Change**:
```diff
- from engine.schema import venue, winery
```

---

### Phase 4: Resolve Category Model Decision

**⚠️ CRITICAL DECISION REQUIRED**: You must decide Category model fate

#### Option A: Category is Lens-Specific Taxonomy (RECOMMENDED)

**If** Category stores Edinburgh Finds taxonomy like "Best Brunch", "Dog Friendly":

**Actions**:

1. **Delete Category model from Prisma schema**:
```diff
- model Category {
-   id          String    @id @default(cuid())
-   name        String    @unique
-   slug        String    @unique
-   description String?
-   image       String?
-   listings    Listing[] @relation("CategoryToListing")
- }
```

2. **Remove categories relation from Listing**:
```diff
model Listing {
  ...
- categories   Category[] @relation("CategoryToListing")
  ...
}
```

3. **Keep categories field in Listing** (raw LLM extraction):
```prisma
model Listing {
  ...
  categories String[]  @default([])  // Raw strings from LLM, not relations
  ...
}
```

4. **Move canonical_categories.yaml to lens layer**:
```bash
mv engine/config/canonical_categories.yaml lenses/edinburgh_finds/categories.yaml
```

5. **Update category_mapper.py** to load from lens config, not engine config

6. **Delete seed_data.py Category logic**

---

#### Option B: Category is Universal (LESS LIKELY)

**If** Category stores truly universal categories applicable to ALL verticals:

**Actions**:
1. Keep Category model
2. Rename to something more universal: `Tag` or `Label`
3. Document what makes it universal
4. Ensure lens layer can add lens-specific categories separately

**Recommendation**: Based on file names and context, **Option A is correct**. Categories are lens-specific.

---

### Phase 5: Migrate to PostgreSQL (CRITICAL)

#### Task 5.1: Why PostgreSQL is Required

**Current blocker**: SQLite doesn't support native arrays

```prisma
// SQLite (current)
canonical_activities String  // JSON string "[\"padel\",\"tennis\"]"

// PostgreSQL (required)
canonical_activities String[] @default([])  // Native array
```

**Without PostgreSQL**:
- ❌ No GIN indexes (performance)
- ❌ No `has`, `hasSome`, `hasEvery` filters
- ❌ Dimensions stored as JSON (violates architecture)

**With PostgreSQL**:
- ✅ Native `text[]` arrays
- ✅ GIN indexes for O(1) faceted filtering
- ✅ Prisma array operators
- ✅ Architecture compliance

---

#### Task 5.2: Set Up Supabase Database

**Steps**:
1. Create Supabase project at supabase.com
2. Copy connection string from Settings → Database
3. Update `.env`:

```bash
# OLD (SQLite)
DATABASE_URL="file:./web/prisma/dev.db"

# NEW (Supabase Postgres)
DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
```

---

#### Task 5.3: Update Prisma Schema for PostgreSQL

**File**: `web/prisma/schema.prisma`

```diff
datasource db {
- provider = "sqlite"
+ provider = "postgresql"
  url      = env("DATABASE_URL")
}
```

---

#### Task 5.4: Verify Array Fields

**Ensure all dimension fields use native arrays**:

```prisma
model Listing {
  canonical_activities String[] @default([])  // ✅ Native array
  canonical_roles String[] @default([])       // ✅ Native array
  canonical_place_types String[] @default([]) // ✅ Native array
  canonical_access String[] @default([])      // ✅ Native array
}
```

**NOT** JSON:
```prisma
canonical_activities Json  // ❌ WRONG for Postgres
```

---

#### Task 5.5: Create Initial Migration

```bash
cd web
npx prisma migrate dev --name init_postgres_schema
```

**This creates**:
- All tables in PostgreSQL
- GIN indexes on dimension arrays (if defined in schema)
- Constraints and relations

---

#### Task 5.6: Add GIN Indexes

**Create migration** `web/prisma/migrations/YYYYMMDD_add_gin_indexes.sql`:

```sql
-- GIN indexes for fast array containment queries
CREATE INDEX IF NOT EXISTS idx_listing_canonical_activities_gin
  ON "Listing" USING GIN (canonical_activities);

CREATE INDEX IF NOT EXISTS idx_listing_canonical_roles_gin
  ON "Listing" USING GIN (canonical_roles);

CREATE INDEX IF NOT EXISTS idx_listing_canonical_place_types_gin
  ON "Listing" USING GIN (canonical_place_types);

CREATE INDEX IF NOT EXISTS idx_listing_canonical_access_gin
  ON "Listing" USING GIN (canonical_access);
```

**Apply**:
```bash
npx prisma migrate dev --name add_gin_indexes
```

---

### Phase 6: Update Extraction Pipeline

#### Task 6.1: Remove entity_type Population

**All extractors should**:
- ❌ NOT set `extracted["entity_type"]`
- ✅ SET `extracted["entity_class"]` by calling `entity_classifier.resolve_entity_class()`

**Example: edinburgh_council_extractor.py**

```diff
+ from engine.extraction.entity_classifier import resolve_entity_class

  def extract(self, raw_data):
      extracted = {}
      extracted["entity_name"] = raw_data.get("FACILITY_NAME")

-     extracted["entity_type"] = EntityType.VENUE.value  # Default to VENUE

      # ... other extraction

+     # Classify entity using universal rules
+     classification = resolve_entity_class(extracted)
+     extracted["entity_class"] = classification["entity_class"]
+     extracted["canonical_roles"] = classification["canonical_roles"]
+     extracted["canonical_activities"] = classification["canonical_activities"]
+     extracted["canonical_place_types"] = classification["canonical_place_types"]

      return extracted
```

**Apply to all 6 extractors**.

---

#### Task 6.2: Update Validation Logic

**Remove entity_type validation**:

```diff
- if "entity_type" not in validated:
-     validated["entity_type"] = EntityType.VENUE.value

+ if "entity_class" not in validated:
+     raise ValueError("entity_class is required")
```

---

#### Task 6.3: Update Ingestion Pipeline

**File**: `engine/ingest.py`

**Remove EntityType references**:

```diff
- from engine.schema.types import EntityType

  # Any code using EntityType.VENUE or EntityType.*
- if listing.get("entity_type") == EntityType.VENUE.value:
+ if listing.get("entity_class") == "place":
```

---

### Phase 7: Clean Up Tests

#### Task 7.1: Update Test Files

**Files to update**:

1. **engine/tests/test_enum_validation.py**
   - Delete if it only tests EntityType enum
   - Or update to test entity_class validation

2. **engine/tests/test_schema_utils.py**
   - Remove tests for `_normalize_entity_type`
   - Update tests to not pass `entity_type` parameter

3. **engine/tests/test_categories.py**
   - Update if it depends on Category model
   - Or move to lens layer tests

4. **All extractor tests**
   - Replace `EntityType.VENUE` with `"place"`
   - Replace `entity_type` assertions with `entity_class`

**Example**:
```diff
- assert extracted["entity_type"] == "VENUE"
+ assert extracted["entity_class"] == "place"
```

---

#### Task 7.2: Run Full Test Suite

```bash
pytest engine/tests/ -v
```

**Expected failures** (fix these):
- Any test asserting `entity_type` field exists
- Any test importing `EntityType`
- Any test using `EntityType.VENUE` or similar

---

### Phase 8: Documentation Updates

#### Task 8.1: Update ARCHITECTURE.md

**Add section**:

```markdown
## Entity Classification

The engine uses a universal, vertical-agnostic classification system:

### entity_class (Required, Single-Valued)
- place: Physical location with address/coordinates
- person: Named individual
- organization: Membership/business entity without fixed location
- event: Time-bounded occurrence
- thing: Fallback for entities that don't fit above

### Migration from EntityType
**DEPRECATED**: `entityType` enum (VENUE, COACH, RETAILER, etc.)
- ❌ Removed: Vertical-specific vocabulary
- ✅ Replaced by: `entity_class` + `canonical_roles`
- Example: VENUE → entity_class='place' + canonical_roles=['provides_facility']
```

---

#### Task 8.2: Update README.md

**Remove references to**:
- EntityType enum
- Venue/Coach/Retailer terminology
- entity_type field

**Replace with**:
- entity_class universal classification
- Lens-specific interpretation
- Link to engine purity principles

---

#### Task 8.3: Create MIGRATION.md Guide

**Document**:
- Why EntityType was removed
- How to map old values to new
- SQL migration scripts
- Code migration patterns

---

## PART 3: VALIDATION & VERIFICATION

### Validation Checklist

#### ✅ Database Purity

```bash
# 1. Check Prisma schema has no entityType
grep -i "entityType" web/prisma/schema.prisma
# Expected: No matches

# 2. Check for vertical-specific models
grep -i "venue\|coach\|winery" web/prisma/schema.prisma
# Expected: No matches (except in comments if needed)

# 3. Verify entity_class exists and is required
grep "entity_class.*String" web/prisma/schema.prisma
# Expected: entity_class String (not nullable)

# 4. Verify array fields
grep "String\[\]" web/prisma/schema.prisma
# Expected: canonical_activities, canonical_roles, canonical_place_types, canonical_access

# 5. Check database provider
grep "provider" web/prisma/schema.prisma
# Expected: provider = "postgresql"
```

---

#### ✅ Schema File Purity

```bash
# 1. Only listing.yaml should exist
ls engine/config/schemas/
# Expected: listing.yaml only

# 2. Check listing.yaml has no entity_type field
grep -i "entity_type" engine/config/schemas/listing.yaml
# Expected: No matches

# 3. Check listing.yaml has entity_class required
grep -A5 "entity_class" engine/config/schemas/listing.yaml | grep "required"
# Expected: required: true
```

---

#### ✅ Code Purity (Zero Vertical Keywords)

```bash
# 1. Check for EntityType enum usage
grep -r "EntityType\." engine/ --include="*.py" | grep -v "test_" | grep -v ".pyc"
# Expected: No matches (or only in test fixtures)

# 2. Check for VENUE/COACH/RETAILER strings
grep -ri "VENUE\|COACH\|INSTRUCTOR\|RETAILER" engine/ --include="*.py" | grep -v "test_" | grep -v "#"
# Expected: No matches (or only in comments/docstrings)

# 3. Check for entity_type field usage in extractors
grep -r '"entity_type"' engine/extraction/extractors/ --include="*.py"
# Expected: No matches

# 4. Check entity_classifier.py has no vertical keywords
grep -i "venue\|coach\|tennis\|padel\|wine" engine/extraction/entity_classifier.py
# Expected: No matches (except in example docstrings)

# 5. Check schema_utils has no EntityType
grep "EntityType" engine/extraction/schema_utils.py
# Expected: No matches
```

---

#### ✅ Vertical-Specific File Deletion

```bash
# 1. Check venue/winery schemas deleted
ls engine/schema/venue.py engine/schema/winery.py 2>/dev/null
# Expected: No such file or directory

# 2. Check venue/winery YAML configs deleted
ls engine/config/schemas/venue.yaml engine/config/schemas/winery.yaml 2>/dev/null
# Expected: No such file or directory

# 3. Check EntityType enum deleted or empty
cat engine/schema/types.py
# Expected: Empty file or file doesn't exist
```

---

#### ✅ Category Decision Implemented

```bash
# IF YOU CHOSE OPTION A (Delete Category model):
grep -i "model Category" web/prisma/schema.prisma
# Expected: No matches

# Check canonical_categories.yaml moved to lens
ls engine/config/canonical_categories.yaml
# Expected: No such file
ls lenses/edinburgh_finds/categories.yaml
# Expected: File exists
```

---

#### ✅ PostgreSQL Migration Complete

```bash
# 1. Check DATABASE_URL uses postgres
grep "DATABASE_URL" .env
# Expected: postgresql://...

# 2. Verify GIN indexes exist
psql $DATABASE_URL -c "\d \"Listing\"" | grep -i "gin"
# Expected: 4 GIN indexes on canonical_* fields

# 3. Test array query
psql $DATABASE_URL -c "SELECT entity_name FROM \"Listing\" WHERE 'test_value' = ANY(canonical_activities) LIMIT 1;"
# Expected: Query succeeds (even if no results)
```

---

#### ✅ Tests Pass

```bash
# Run full test suite
pytest engine/tests/ -v --tb=short

# Expected: All tests pass
# No failures related to EntityType
# No failures related to entity_type field
```

---

#### ✅ Extraction Pipeline Works

```bash
# Test extraction with entity_class
python -m engine.extraction.run --source google_places --limit 1

# Verify output has entity_class, not entity_type
# Check console output or database for extracted entity
```

---

### Success Criteria (Non-Negotiable)

1. **✅ Zero EntityType references** in engine/ (excluding archived tests)
2. **✅ Zero entityType field** in schema (DB, YAML, generated Python)
3. **✅ Zero vertical schema files** (venue.yaml, winery.yaml deleted)
4. **✅ All extractors populate entity_class**, not entity_type
5. **✅ Category decision documented and implemented**
6. **✅ PostgreSQL with native arrays** (not SQLite JSON strings)
7. **✅ GIN indexes on all dimension arrays**
8. **✅ All tests pass** with new schema
9. **✅ entity_classifier.py has no vertical keywords** (except examples)
10. **✅ Grep returns zero hits** for VENUE/COACH in engine code

---

## PART 4: IMPLEMENTATION ORDER

### Recommended Phased Approach

#### Sprint 1: Database Migration (FOUNDATIONAL)
**Duration**: 1-2 days

**Goal**: Move to PostgreSQL with native arrays

**Tasks**:
1. Set up Supabase database
2. Update `.env` with PostgreSQL URL
3. Update `schema.prisma` provider to postgresql
4. Run `prisma migrate dev --name init_postgres`
5. Create GIN indexes migration
6. Verify arrays work with test query

**Success**: Database is PostgreSQL, arrays are native text[]

---

#### Sprint 2: Schema Cleanup (CRITICAL)
**Duration**: 2-3 hours

**Goal**: Remove all entityType artifacts from schema layer

**Tasks**:
1. Remove `entity_type` from `listing.yaml`
2. Make `entity_class` required in `listing.yaml`
3. Run `python -m engine.schema.generate`
4. Update Prisma schema manually (remove entityType field)
5. Create migration to drop entityType column
6. Delete `venue.yaml`, `winery.yaml` from `engine/config/schemas/`
7. Delete `venue.py`, `winery.py` from `engine/schema/`

**Success**: No entity_type/entityType in any schema file

---

#### Sprint 3: Delete EntityType Enum (HIGH IMPACT)
**Duration**: 3-4 hours

**Goal**: Remove EntityType enum from codebase

**Tasks**:
1. Empty `engine/schema/types.py` (or delete EntityType class)
2. Remove all `from engine.schema.types import EntityType` lines (8 files)
3. Update `schema_utils.py` - delete `_normalize_entity_type`, update function signatures
4. Update all extractors to remove `EntityType.VENUE` defaults
5. Update all extractors to call `entity_classifier.resolve_entity_class()`
6. Update `ingest.py` to use entity_class instead

**Success**: Zero `EntityType.` references in engine code

---

#### Sprint 4: Category Model Resolution (DECISION)
**Duration**: 2-3 hours

**Goal**: Implement Category decision

**If Option A (Delete)**:
1. Delete Category model from Prisma schema
2. Remove categories relation from Listing
3. Make categories field String[] (raw extraction)
4. Move `canonical_categories.yaml` to lens layer
5. Update `category_mapper.py` to load from lens
6. Update seed_data.py

**Success**: Category model deleted or moved to lens

---

#### Sprint 5: Test Updates (VALIDATION)
**Duration**: 2-3 hours

**Goal**: Fix all broken tests

**Tasks**:
1. Update test files to remove EntityType assertions
2. Replace `entity_type` checks with `entity_class`
3. Update extractor tests
4. Update schema_utils tests
5. Delete or update test_enum_validation.py
6. Run full pytest suite

**Success**: `pytest engine/tests/` passes 100%

---

#### Sprint 6: Documentation & Validation (FINAL)
**Duration**: 1-2 hours

**Goal**: Document changes and run validation

**Tasks**:
1. Update ARCHITECTURE.md
2. Update README.md
3. Create MIGRATION.md guide
4. Run all validation checks from Part 3
5. Create new Conductor track checkpoint commit

**Success**: All validation checks pass, docs updated

---

## PART 5: MIGRATION SAFETY

### Data Preservation Strategy

#### Option 1: Clean Slate (RECOMMENDED for dev)
**When**: Development environment, no production data

**Steps**:
1. Delete SQLite database: `rm web/prisma/dev.db`
2. Run all migrations on fresh Postgres
3. Re-extract data with new schema

**Pros**: Clean, no migration complexity
**Cons**: Lose existing extracted data

---

#### Option 2: Data Migration (If you need existing data)
**When**: Preserving extracted entities

**Steps**:

1. Export existing data:
```bash
sqlite3 web/prisma/dev.db ".dump Listing" > listing_export.sql
```

2. Create mapping script:
```python
# migrate_entity_type.py
import psycopg2

def migrate():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Map old entityType to new entity_class
    mapping = {
        'VENUE': 'place',
        'RETAILER': 'place',
        'COACH': 'person',
        'INSTRUCTOR': 'person',
        'CLUB': 'organization',
        'LEAGUE': 'organization',
        'EVENT': 'event',
        'TOURNAMENT': 'event',
    }

    for old, new in mapping.items():
        cur.execute(
            'UPDATE "Listing" SET entity_class = %s WHERE entityType = %s',
            (new, old)
        )

    conn.commit()
```

3. Run migration before dropping column

---

### Rollback Plan

**If migration fails**:
1. Keep SQLite database backup: `cp web/prisma/dev.db web/prisma/dev.db.backup`
2. Keep `.env` file backup with SQLite URL
3. Git branch for changes: `git checkout -b feature/remove-entity-type`
4. If needed to rollback: `git checkout main && mv dev.db.backup dev.db`

---

## PART 6: POST-COMPLETION VALIDATION

### Acid Test: Add a New Vertical

**Goal**: Prove engine purity by adding wine vertical with ZERO engine changes

**Test**:
1. Create `lenses/wine_discovery/lens.yaml` (already exists)
2. Add wine-specific values:
   - activity facet: "wine_tasting", "vineyard_tour"
   - place_type facet: "winery", "tasting_room"
3. Add wine-specific module: `wine_production`
4. Deploy without touching engine code

**Success criteria**:
- ✅ No changes to `engine/` directory
- ✅ No changes to Prisma schema
- ✅ No new migrations
- ✅ Wine entities extract and store correctly
- ✅ Same dimensions (canonical_activities) store wine values

**If you need to change engine code**, engine is NOT pure.

---

### Grep Tests (Pass/Fail)

```bash
# FAIL if ANY matches
grep -r "VENUE\|COACH\|RETAILER" engine/ --include="*.py" | grep -v test_ | grep -v "#"
grep -r "EntityType\." engine/ --include="*.py" | grep -v test_
grep -i "entityType" web/prisma/schema.prisma
grep -i "entity_type" engine/config/schemas/listing.yaml
ls engine/schema/venue.py 2>/dev/null
ls engine/config/schemas/venue.yaml 2>/dev/null

# PASS if file exists and has place/person/organization/event/thing
grep "entity_class.*String" web/prisma/schema.prisma
```

---

## APPENDICES

### Appendix A: File Change Summary

#### Files to DELETE (6 files)
```
engine/schema/venue.py
engine/schema/winery.py
engine/config/schemas/venue.yaml
engine/config/schemas/winery.yaml
engine/config/canonical_categories.yaml  (move to lens)
engine/schema/types.py  (delete EntityType enum, may keep file empty)
```

#### Files to MODIFY - Schema (2 files)
```
engine/config/schemas/listing.yaml  (remove entity_type, make entity_class required)
web/prisma/schema.prisma  (remove entityType, add GIN indexes)
```

#### Files to MODIFY - Code (9 files)
```
engine/extraction/schema_utils.py  (remove EntityType, update signatures)
engine/extraction/entity_classifier.py  (verify no vertical keywords)
engine/extraction/extractors/edinburgh_council_extractor.py
engine/extraction/extractors/google_places_extractor.py
engine/extraction/extractors/open_charge_map_extractor.py
engine/extraction/extractors/sport_scotland_extractor.py
engine/extraction/extractors/osm_extractor.py
engine/extraction/extractors/serper_extractor.py
engine/ingest.py  (remove EntityType usage)
```

#### Files to MODIFY - Tests (~10 files)
```
engine/tests/test_enum_validation.py
engine/tests/test_schema_utils.py
engine/tests/test_categories.py
All extractor test files
```

#### Files to MODIFY - Docs (3 files)
```
ARCHITECTURE.md
README.md
MIGRATION.md  (create new)
```

**Total: ~25-30 files to modify/delete**

---

### Appendix B: Critical Questions to Answer

Before starting, answer these:

1. **Category Model Decision**: Is Category lens-specific or universal?
   - If lens-specific: Delete model, move to lens layer
   - If universal: Keep but rename and document

2. **Existing Data**: Do you need to preserve extracted listings?
   - If yes: Use data migration strategy
   - If no: Clean slate (faster)

3. **Supabase Ready**: Do you have Supabase project credentials?
   - Get DATABASE_URL before starting migration

4. **Downtime Acceptable**: Can you break dev environment temporarily?
   - Migration will require downtime during schema changes

---

### Appendix C: Time Estimates

#### Minimum (experienced, no data migration)
- **6-8 hours** of focused work
- Assumes familiarity with codebase
- Assumes no data preservation needed

#### Realistic (with testing and validation)
- **12-16 hours** across 2-3 days
- Includes running full test suite
- Includes documentation updates

#### Conservative (with data migration and docs)
- **20-24 hours** across 3-4 days
- Includes data preservation strategy
- Includes comprehensive validation
- Includes team coordination

**Recommended**: Spread across **6 sprints over 2-3 days**

---

## FINAL NOTES

### What This Achieves

After completing ALL tasks above:

✅ **100% vertical-agnostic engine**
- Zero references to sports/wine/any domain
- Zero EntityType enum
- Zero vertical-specific schema files

✅ **PostgreSQL architecture**
- Native text[] arrays
- GIN indexes
- Performant faceted queries

✅ **Lens-driven interpretation**
- Engine stores opaque strings
- Lens provides meaning
- Add new verticals by YAML only

✅ **Your advisor will be satisfied**
- entityType → entity_class migration complete
- Category model resolved
- No vertical leaks remain

---

### The Two Core Issues

As your advisor identified, the problem boils down to:

1. **entityType field** - Carries vertical meaning (VENUE, COACH)
2. **Category model** - Potentially vertical-specific taxonomy in engine DB

Everything else (extractors, schema files, tests) cascades from fixing these two architectural decisions.

---

### Next Steps

1. **Review this document** thoroughly
2. **Answer Appendix B questions** (Category decision, data preservation)
3. **Set up Supabase** (get DATABASE_URL)
4. **Create new Conductor track** using this as specification
5. **Execute Sprint 1** (PostgreSQL migration) first
6. **Execute Sprints 2-6** sequentially
7. **Run validation checklist** after each sprint
8. **Celebrate** when all grep tests pass! 🎉

---

**END OF DOCUMENT**

Generated by Claude (AI Assistant)
Date: 2026-01-21
For: Edinburgh Finds Engine Purity Implementation
