# Implementation Plan: Pydantic Extraction Generator

## Phase 1: Generator Implementation [checkpoint: 4bc5ec9]
- [x] **Create Generator Module** [32e9324]
    - [x] Create `engine/schema/generators/pydantic_extraction.py`.
    - [x] Implement class `PydanticExtractionGenerator`.
    - [x] Implement type mapping (YAML types -> Pydantic types).
    - [x] Implement field generation with `Field(default=None)` semantics.
- [x] **Handle Validators** [ac3d0a7]
    - [x] Design strategy for validators (e.g., look for `python.validator` metadata in YAML or import a mixin).
    - [x] Update `listing.yaml` if necessary to support validator metadata.
- [x] **CLI Integration** [6ff6756]
    - [x] Update `engine/schema/cli.py` to add `--pydantic-extraction` flag (or include in default generation).

## Phase 2: Testing & Validation
- [x] **Unit Tests**
    - [x] Create `engine/tests/test_pydantic_extraction_generator.py`.
    - [x] Test generation of basic fields.
    - [x] Test null semantics (all optionals).
- [x] **Integration Check**
    - [x] Generate the file locally.
    - [x] Compare with current manual `entity_extraction.py`.
    - [x] Verify `entity_type` is present.

## Phase 3: Migration
- [x] **Replace Manual File**
    - [x] Overwrite `engine/extraction/models/entity_extraction.py` with generated code.
- [x] **Verify System**
    - [x] Run `pytest engine/tests/test_null_semantics.py`.
    - [x] Run `pytest engine/tests/test_serper_extractor.py`.

## Phase 4: Documentation
- [x] **Update Docs**
    - [x] Update `docs/schema_management.md` to include this new generator.
