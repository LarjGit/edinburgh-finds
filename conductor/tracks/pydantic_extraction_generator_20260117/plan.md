# Implementation Plan: Pydantic Extraction Generator

## Phase 1: Generator Implementation
- [x] **Create Generator Module** [32e9324]
    - [x] Create `engine/schema/generators/pydantic_extraction.py`.
    - [x] Implement class `PydanticExtractionGenerator`.
    - [x] Implement type mapping (YAML types -> Pydantic types).
    - [x] Implement field generation with `Field(default=None)` semantics.
- [ ] **Handle Validators**
    - [ ] Design strategy for validators (e.g., look for `python.validator` metadata in YAML or import a mixin).
    - [ ] Update `listing.yaml` if necessary to support validator metadata.
- [ ] **CLI Integration**
    - [ ] Update `engine/schema/cli.py` to add `--pydantic-extraction` flag (or include in default generation).

## Phase 2: Testing & Validation
- [ ] **Unit Tests**
    - [ ] Create `engine/tests/test_pydantic_extraction_generator.py`.
    - [ ] Test generation of basic fields.
    - [ ] Test null semantics (all optionals).
- [ ] **Integration Check**
    - [ ] Generate the file locally.
    - [ ] Compare with current manual `entity_extraction.py`.
    - [ ] Verify `entity_type` is present.

## Phase 3: Migration
- [ ] **Replace Manual File**
    - [ ] Overwrite `engine/extraction/models/entity_extraction.py` with generated code.
- [ ] **Verify System**
    - [ ] Run `pytest engine/tests/test_null_semantics.py`.
    - [ ] Run `pytest engine/tests/test_serper_extractor.py`.

## Phase 4: Documentation
- [ ] **Update Docs**
    - [ ] Update `docs/schema_management.md` to include this new generator.
