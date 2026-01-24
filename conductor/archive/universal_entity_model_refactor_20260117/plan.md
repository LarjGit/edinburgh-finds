# Implementation Plan: Universal Entity Model Refactor

## Phase 1: Model Refactoring
- [x] **Rename Module & Class**
    - [x] Rename `engine/extraction/models/venue_extraction.py` to `entity_extraction.py`.
    - [x] Rename class `VenueExtraction` to `EntityExtraction` within the file.
    - [x] Update docstrings to refer to "Entity" instead of "Venue".

## Phase 2: Update Extractors
- [x] **Refactor Serper Extractor**
    - [x] Update imports in `engine/extraction/extractors/serper_extractor.py`.
    - [x] Rename internal variables (e.g., `venue_extraction` -> `entity_extraction`).
- [x] **Refactor OSM Extractor**
    - [x] Update imports in `engine/extraction/extractors/osm_extractor.py`.
    - [x] Rename internal variables.

## Phase 3: Update Tests
- [x] **Update Imports & Fixtures**
    - [x] Refactor `engine/tests/test_serper_extractor.py`.
    - [x] Refactor `engine/tests/test_osm_extractor.py`.
    - [x] Search for any other test files importing `VenueExtraction`.

## Phase 4: Verification
- [x] **Run Tests**
    - [x] Execute `pytest engine/tests/test_serper_extractor.py engine/tests/test_osm_extractor.py` to ensure the rename didn't break functionality.
- [x] **Grep Check**
    - [x] Search codebase for lingering `VenueExtraction` references to ensure 100% coverage.