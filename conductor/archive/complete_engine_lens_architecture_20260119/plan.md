# Plan: Complete Engine-Lens Architecture

**Track ID:** `complete_engine_lens_architecture_20260119`
**Created:** 2026-01-19
**Status:** Active
**Goal:** Finalize the separation of the Entity Engine and Vertical Lenses by migrating the database to Postgres (Supabase), eliminating all vertical-specific logic from the engine, and validating the architecture through a full data re-ingestion and lens-aware extraction.

## Context
This track addresses the critical blockers identified in the `next_steps_codex.md` review. The current system relies on SQLite (which lacks native array/JSONB support required for the architecture) and still contains legacy code coupling the engine to the "Sports" vertical.

## Phase 1: Database Migration (Postgres/Supabase)
**Goal:** Establish the production database foundation required for array types and GIN indexing.

- [x] **Task 1.1: Switch to Postgres** [f43c83b]
  - Update `web/prisma/schema.prisma` datasource provider to `postgresql`.
  - Update environment variables configuration for local and CI environments.

- [x] **Task 1.2: Schema Modernization** [f43c83b]
  - Modify `canonical_activity`, `canonical_role`, `canonical_place_type`, `canonical_amenities` in `schema.prisma` to be native `String[]` types (removing manual JSON string handling).
  - Change `modules` field to native `Json` type.
  - Ensure `@default([])` is applied to array fields.

- [x] **Task 1.3: Migration & Indexing** [a26ee18]
  - Create a new migration: `npx prisma migrate dev --name init_postgres_arrays`.
  - Verify migration SQL includes GIN indexes for array fields (crucial for `has`, `hasSome` performance).
  - Update `engine/schema.prisma` to match (if separate).
  - **Note**: Migration prepared but not executed. Requires PostgreSQL database (Phase 4).

- [x] **Task 1.4: Validation**
  - Run `tests/query/test_prisma_array_filters.py` against the Postgres instance.
  - Verify that array filtering works natively without JSON parsing logic.
  - **Completed**: All 6 array filter tests passing. Native String[] arrays and array operations (has, hasSome, hasEvery) validated on Supabase PostgreSQL.

## Phase 2: Engine Purity & Cleanup
**Goal:** Remove all "Sports" and "Venue" concepts from the core engine, making it truly vertical-agnostic.

- [x] **Task 2.1: Remove Legacy Schema (PARTIAL)**
  - Deleted `engine/schema/venue.py`.
  - Updated `engine/extraction/schema_utils.py` to use only universal LISTING_FIELDS and map VENUE→PLACE.
  - Updated `engine/tests/test_schema_sync.py` to remove venue-specific tests.
  - **NOTE**: Changes to `engine/ingest.py` and `engine/run_seed.py` were reverted - ingestion refactor will be a separate track.

- [x] **Task 2.2: Decouple Extraction Defaults**
  - Removed `entity_type="VENUE"` default from `engine/extraction/run.py` line 187.
  - Updated `schema_utils.py` to default to PLACE (not VENUE) and always return universal LISTING_FIELDS.
  - Extraction now relies on extractors to provide entity_type explicitly.

- [x] **Task 2.3: Sanitize Classifier** [68f2cbf]
  - Refactor `engine/extraction/entity_classifier.py`:
    - Remove hardcoded sports keywords (e.g., "coach", "instructor") - these belong in Lens config or specific extractors.
    - Remove "sports_centre" default fallback.
  - Ensure the classifier outputs only opaque, universal `EntityClass` values.

- [x] **Task 2.4: Universal Pipeline** [d46fe41]
  - Audit `engine/extraction/extractors/` to ensure all extractors return `EntityExtraction` models, not `VenueExtraction`.
  - Verify that `extract_with_lens_contract` is the sole entry point for logic that might need lens specifics.

## Phase 3: Logic & Semantics (Classifier & Triggers)
**Goal:** Correct logic errors in classification and configuration loading.

- [x] **Task 3.1: Fix Classification Priority** [f5e337b]
  - Update `engine/extraction/entity_classifier.py` logic to follow the hierarchy:
    1. **Event** (Time-bound, specific date/duration)
    2. **Place** (Physical location, address-centric)
    3. **Organization** (Abstract entity, membership, business)
    4. **Person** (Individual, human attributes)
    5. **Thing** (Catch-all)
  - *Rationale:* An organization (e.g., a Club) might have an address, but if it has members and bylaws, it's an Org first. A Person might have an "address", but shouldn't be a Place.

- [x] **Task 3.2: Fix ModuleTrigger Shape** [07064d3]
  - Update `engine/lenses/loader.py` to handle `conditions` as a list of dictionaries (matching `lens.yaml` spec), not a single dictionary.
  - Add unit test for `ModuleTrigger` loading with list-based conditions.

- [x] **Task 3.3: Configurable Thresholds** [b9f02e7]
  - Remove hardcoded `0.7` confidence threshold from `engine/extraction/base.py` and `engine/lenses/loader.py`.
  - Pass threshold values from the loaded Lens Configuration into the extraction context.

## Phase 4: Re-ingestion & Validation
**Goal:** Prove the system works end-to-end with the new architecture.

- [ ] **Task 4.1: Fresh Ingestion**
  - Clear the Postgres database.
  - Run ingestion for a subset of data (e.g., Edinburgh area) to populate `RawIngestion`.

- [ ] **Task 4.2: Lens-Aware Extraction**
  - Run the full extraction pipeline: `python -m engine.extraction.run_all`.
  - Monitor logs for "Lens" activity and ensuring no "Venue" legacy logs appear.

- [ ] **Task 4.3: Data Verification**
  - Inspect the database (using `psql` or Prisma Studio).
  - Verify `canonical_*` fields are true Postgres arrays.
  - Verify `modules` column contains valid JSONB namespaced by module name.

## Phase 5: Frontend Integration
**Goal:** Connect the UI to the new data structure.

- [ ] **Task 5.1: Query Layer Update**
  - Refactor `web/lib/lens-query.ts`.
  - Replace any in-application filtering logic with direct Prisma array filters (`has`, `hasSome`, `hasEvery`).

- [ ] **Task 5.2: UI Connection**
  - Ensure Facet components in the frontend correctly read from the new array structure.

- [ ] **Task 5.3: Multi-Lens Verification**
  - Switch config to "Wine Discovery" lens (if available) or a mock second lens.
  - Verify that without changing engine code, the frontend filters and data shape adapt to the new lens configuration.