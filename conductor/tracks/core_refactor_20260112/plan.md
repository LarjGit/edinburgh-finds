# Track Plan: Core Architecture Refactor

## Phase 1: Schema Definition & Generators
- [x] Task: specific - Create `engine/schema/` and port `FieldSpec` definitions. [schema_ported]
    - **Action:** Create `engine/schema/common.py` and `engine/schema/venue.py` with the provided python code.
    - **Action:** Create `engine/schema/core.py` (or similar) to hold the `FieldSpec` dataclass definition.
- [x] Task: Implement Pydantic Model Generator. [generator_implemented]
    - **Goal:** Dynamic creation of Pydantic models from `FieldSpec` lists.
    - **Action:** Create `engine/schema/generator.py` with a function `create_pydantic_model(name, fields)`.
    - **Test:** Verify it correctly generates a `VenueModel` that validates strict inputs.

## Phase 2: Database Refactor
- [x] Task: Refactor `prisma/schema.prisma`. [schema_refactored]
    - **Action:** Update `Listing` model:
        - Match columns to `LISTING_FIELDS` (Identity, Location, Contact, Social).
        - Add `attributes` (JSON) for `FieldSpec` validated data.
        - Add `discovered_attributes` (JSON) for catch-all data.
    - **Action:** Delete `Venue`, `Coach` models.
    - **Action:** Create migration `0_init_generic_schema`.

## Phase 3: Engine Rewrite
- [x] Task: Implement Generic Ingestor. [ingestor_implemented]
    - **Action:** Create `engine/ingest.py`.
    - **Logic:** `ingest_entity(data)` -> Detect Type -> Get Schema -> Validate -> Prisma Create `Listing`.
    - **Note:** Use `prisma-client-python` for type-safe DB access.

## Phase 4: Verification
- [x] Task: Run Seed with Sample Data. [verification_complete]
    - **Action:** Run the new ingestor with the Powerleague sample data.
    - **Check:** Verify data appears in `Listing` table and `attributes` column contains the niche fields.
- [ ] Task: Conductor - User Manual Verification 'Verification' (Protocol in workflow.md)
