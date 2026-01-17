# Implementation Plan: Category-Entity Decoupling

## Phase 1: Configuration & Core Logic
- [x] **Refactor Taxonomy Configuration** (a3d903f)
    - [x] Edit `engine/config/canonical_categories.yaml`: Remove `parent: venue` from all sports.
    - [x] Create a new top-level conceptual grouping (optional) or just keep them flat.
- [ ] **Update Category Mapper**
    - [ ] Modify `engine/extraction/utils/category_mapper.py` to remove reliance on hierarchy for validation or pathing.
    - [ ] Update `get_category_hierarchy` to reflect the flat structure (or deprecate it if no longer useful).

## Phase 2: Extraction Engine Updates
- [ ] **Update Extraction Models**
    - [ ] Ensure `Listing` and `ExtractedListing` models strictly treat `entity_type` and `categories` as orthogonal fields.
- [ ] **Refactor Extraction Logic**
    - [ ] Update `engine/extraction/run.py` to avoid defaulting `entity_type` to "VENUE" if it can be inferred otherwise.
    - [ ] Check `engine/extraction/extractors/` (Serper, OSM, etc.) to ensure they populate `entity_type` correctly based on source data, not just the category.

## Phase 3: Validation & Cleanup
- [ ] **Update Tests**
    - [ ] Fix `engine/tests/test_categories.py` which likely tests the hierarchy.
    - [ ] Add tests for "Padel Coach" vs "Padel Venue" scenarios.
- [ ] **Frontend Check**
    - [ ] Verify `web/` components don't break with the flattened taxonomy.
