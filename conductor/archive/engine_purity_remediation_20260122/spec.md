# Specification: Engine Purity Remediation
**Date:** 2026-01-22
**Status:** Approved

## 1. Problem Definition
The project has undergone a partial migration to a vertical-agnostic architecture.
- **State A (Database/Schema):** ✅ PURE. Uses `Entity` model, `entity_class`, native arrays, and has removed `entityType`.
- **State B (Application Code):** ❌ IMPURE. Python code still references `Listing` table, `entityType` column, and hardcodes `VENUE` enum logic.

**Result:** The application cannot run. Seed scripts fail. Extractors force legacy logic. New verticals cannot be added without code changes.

## 2. Remediation Requirements

### 2.1. Seed Data Repair
**Target:** `engine/seed_data.py`
- **Requirement:** Must insert data into the `Entity` table (not `Listing`).
- **Requirement:** Must NOT attempt to set `entityType`.
- **Requirement:** Must set `entity_class` correctly (e.g., 'place' for venues, 'organization' for clubs).
- **Requirement:** Must set `canonical_roles` (e.g., `['provides_facility']`).

### 2.2. Extractor Agnosticism
**Target:** All Extractors in `engine/extraction/extractors/`
- **Requirement:** Remove all calls to `get_extraction_fields(entity_type="VENUE")`.
- **Requirement:** Extractors must initialize using the universal `get_extraction_fields()` which returns the superset of fields.
- **Requirement:** `OSMExtractor`, `GooglePlacesExtractor`, etc., must not default to "VENUE".
- **Requirement:** Output dictionaries must map to `entity_class` and `canonical_roles`, not `entity_type`.

### 2.3. Prompt Engineering Purity
**Target:** `engine/extraction/prompts/`
- **Requirement:** Prompts (e.g., Serper, Base) must not contain hardcoded lists of verticals (VENUE, COACH, etc.).
- **Requirement:** Classification rules must be injected dynamically or be generic enough to apply to any vertical.
- **Solution:** Use `{classification_rules}` variable in prompts, populated from `EntityClassifier` or Lens config.

### 2.4. Taxonomy Decoupling
**Target:** `engine/extraction/utils/category_mapper.py`
- **Requirement:** Remove hardcoded file path to `engine/config/canonical_categories.yaml`.
- **Requirement:** Allow the path/config to be injected, enabling the Lens layer to provide its own taxonomy files.

### 2.5. Config Cleanup
**Target:** `engine/config/`
- **Requirement:** Verify `venue.yaml` and `winery.yaml` are strictly removed.
- **Requirement:** `entity.yaml` (or `listing.yaml` if not yet renamed) must be the single source of truth.

## 3. Verification Criteria
The remediation is considered complete when:
1.  `python engine/run_seed.py` executes successfully and populates the `Entity` table in Postgres.
2.  `python -m engine.extraction.run` works for a sample source without "VENUE" errors.
3.  `grep -r "entityType" engine/` returns no functional code matches.
4.  `grep -r "VENUE" engine/` returns no functional code matches (excluding perhaps legacy comments which should be cleaned).