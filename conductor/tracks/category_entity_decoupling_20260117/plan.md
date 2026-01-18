# Implementation Plan: Category-Entity Decoupling (REVISED)

## Context
**Objective:** Remove **ALL** concepts of category hierarchy.
- No `parent` field in `canonical_categories.yaml`.
- No `include_parents` logic in `category_mapper.py`.
- No assumption that a category implies a specific `entity_type` via inheritance.
- Categories and Entity Types must be strictly orthogonal.

## Phase 1: Configuration & Schema (IMMEDIATE)
- [x] **Purge Taxonomy Hierarchy**
    - [x] Edit `engine/config/canonical_categories.yaml`:
        - [x] Remove `parent: ...` from ALL entries (including `venue`, `gym`, etc.).
        - [x] Remove `include_parents` from `promotion_config`.
        - [x] Remove documentation comments referencing "parent categories" or "hierarchical navigation".
- [x] **Update Category Mapper Logic**
    - [x] Modify `engine/extraction/utils/category_mapper.py`:
        - [x] Remove `get_category_hierarchy` function entirely.
        - [x] Remove any logic that looks up `parent` in the taxonomy.
    - [x] Update `engine/tests/test_categories.py`:
        - [x] Remove tests that check for hierarchy/parent resolution.
        - [x] Ensure `get_canonical_categories` simply returns the mapped categories without climbing a tree.

## Phase 2: Extraction Logic Refinement
- [x] **Decouple Entity Type from Category**
    - [x] Review `engine/extraction/run.py` and extractors.
    - [x] Ensure `entity_type` is determined by the extractor's source data or specific heuristics, NOT by checking if a category is a child of "Venue".
    - [x] If `entity_type` cannot be determined, it should remain null or require manual review, rather than defaulting based on category.

## Phase 3: Documentation & Cleanup
- [x] **Documentation Sweep**
    - [x] `docs/managing_categories.md`: Remove sections on "Parent Category" and hierarchy.
    - [x] `docs/SYSTEM_DESIGN_MANUAL.md`: Update taxonomy description to be flat.
    - [x] `docs/category_promotion_workflow.md`: Remove hierarchy references.
- [x] **Verification**
    - [x] Run full extraction test suite.
    - [x] Verify that "Sports Centre" is just a category, not a sub-category of "Venue".
