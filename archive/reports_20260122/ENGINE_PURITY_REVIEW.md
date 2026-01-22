# Engine Purity Review Findings
**Date:** 2026-01-22
**Status:** In Transition (Approx. 50% Complete)

## Executive Summary
The review of the codebase indicates that while significant structural changes (Database Schema) have been applied to support a vertical-agnostic engine, the application logic (Extractors, Seeding, Prompts) lags behind. The system is currently in a fractured state where the database schema expects a pure "Entity" model, but the ingestion and seeding logic still operates on legacy "Listing" and "VENUE" concepts.

## 1. Critical Blocking Violations

### 1.1. Broken Seed Data Script (`engine/seed_data.py`)
**Severity:** Critical (Runtime Failure)
- **Violation:** The script attempts to insert into a table named `Listing` with a column `entityType`.
- **Reality:** The Prisma schema (`web/prisma/schema.prisma`) defines the model as `Entity` and has **removed** the `entityType` field.
- **Impact:** `run_seed.py` will fail immediately.
- **Fix:** Update `seed_data.py` to target the `Entity` table (or verify mapping) and remove `entityType` from the INSERT statement.

### 1.2. Extractors Hardcoded to Legacy Types
**Severity:** High
- **Violation:** Extractors (e.g., `OSMExtractor`) still initialize with explicit legacy type dependencies.
  ```python
  # engine/extraction/extractors/osm_extractor.py
  self.schema_fields = get_extraction_fields(entity_type="VENUE")
  ```
- **Impact:** Prevents the engine from being truly agnostic. It forces "VENUE" schema logic even if the entity is a generic "place" or "thing".

### 1.3. Prompt Engineering Leaks
**Severity:** Medium
- **Violation:** LLM Prompts (e.g., `engine/extraction/prompts/serper_extraction.txt`) contain hardcoded, vertical-specific classification instructions.
  - *"Classify the entity as one of: VENUE, RETAIL, COACH, CLUB, EVENT"*
  - *"Padel Club -> VENUE"*
- **Impact:** The engine cannot natively support a new vertical (e.g., "Winery") without modifying these core text files.
- **Fix:** Move classification logic to the `EntityClassifier` or inject dynamic prompts from the Lens layer.

## 2. Architectural Violations

### 2.1. Category Mapper Dependency
**Severity:** Medium
- **Violation:** `engine/extraction/utils/category_mapper.py` hardcodes the path to `engine/config/canonical_categories.yaml`.
- **Impact:** This ties the engine to a specific, potentially vertical-biased taxonomy file in the engine directory.
- **Fix:** Make the taxonomy configuration path injectable or move the file to the active Lens directory.

### 2.2. Vertical-Specific Schemas
**Severity:** Low (Cleanup)
- **Status:** `venue.yaml` and `winery.yaml` appear to be removed from `engine/config/schemas/`, which is **Correct**.
- **Action:** Ensure `entity.yaml` is the sole source of truth and is generic.

## 3. Status of "Purity" Goals

| Goal | Status | Notes |
| :--- | :--- | :--- |
| **No `entityType` Column** | ✅ Passed | Removed from Prisma schema. |
| **Universal `Entity` Model** | ✅ Passed | `Entity` model exists with `entity_class`. |
| **Agnostic Extractors** | ❌ Failed | Still use `entity_type="VENUE"` and hardcoded prompts. |
| **Agnostic Seeding** | ❌ Failed | Script is broken and uses legacy fields. |
| **Lens-Driven Logic** | ⚠️ Partial | Lens architecture exists, but engine still hardcodes dependencies. |

## 4. Recommendations
1.  **Immediate Fix:** Refactor `engine/seed_data.py` to match the new `Entity` schema.
2.  **Code Cleanup:** Search and replace `get_extraction_fields(entity_type="VENUE")` with `get_extraction_fields()` in all extractors.
3.  **Prompt Refactoring:** Abstract the classification instructions in prompts to use variables injected from the Lens configuration.
4.  **Config Injection:** Modify `category_mapper.py` to accept a config path argument, allowing the Lens to provide its own taxonomy.
