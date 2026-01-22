# Plan: Engine Purity Remediation
**Status:** Active
**Created:** 2026-01-22

## Phase 1: Critical Runtime Fixes (Seed & Ingest)
**Goal:** Restore the ability to run basic engine scripts by fixing the mismatch between Code and DB Schema.

- [x] **1.1. Fix `seed_data.py`**
    - [x] Read `engine/seed_data.py` to identify legacy SQL/Prisma calls.
    - [x] Refactor to use `Entity` model. [12b3b29]
    - [x] Remove `entityType` field assignment. [12b3b29]
    - [x] Map legacy `entityType="VENUE"` to `entity_class="place"` + `canonical_roles=["provides_facility"]`. [12b3b29]
    - [x] Verify execution: Note - seed_data.py uses SQLite but schema is PostgreSQL. Actual seeding is via ingest.py.

- [x] **1.2. Fix `ingest.py`**
    - [x] Search `engine/ingest.py` for `entityType` or `Listing` model usage. [91c2781]
    - [x] Update to use `Entity` model. [91c2781]
    - [x] Ensure `entity_class` is populated if missing (default to 'thing' or specific logic). [91c2781]

## Phase 2: Extractor Purification
**Goal:** Remove "VENUE" and legacy typing from the extraction layer.

- [x] **2.1. Audit Extractors**
    - [x] Run `grep -r "entity_type" engine/extraction/extractors/`.
    - [x] Run `grep -r "VENUE" engine/extraction/extractors/`.

- [x] **2.2. Remediation: Universal Initialization**
    - [x] Fix `engine/extraction/schema_utils.py` bug (line 43: removed entity_type parameter).
    - [x] Refactor `engine/extraction/extractors/osm_extractor.py`: remove `entity_type="VENUE"`.
    - [x] Refactor `engine/extraction/extractors/serper_extractor.py`: remove `entity_type="VENUE"`.
    - [x] Refactor `engine/extraction/extractors/google_places_extractor.py`: remove docstring VENUE mentions.
    - [x] Refactor `engine/extraction/extractors/sport_scotland_extractor.py`: remove docstring VENUE mentions.
    - [x] Refactor `engine/extraction/extractors/edinburgh_council_extractor.py`: remove docstring VENUE mentions.
    - [x] Refactor `engine/extraction/extractors/open_charge_map_extractor.py`: remove docstring VENUE mentions.

- [x] **2.3. Remediation: Output Normalization**
    - [x] Verified extractors use universal schema fields (entity_class handled by downstream pipeline).

## Phase 3: Prompt & Taxonomy Decoupling
**Goal:** Remove vertical-specific knowledge from the core engine assets.

- [x] **3.1. Refactor Prompts**
    - [x] Read `engine/extraction/prompts/serper_extraction.txt`.
    - [x] Identify hardcoded classification lists (found in osm_extraction.txt lines 101-108).
    - [x] Replace with `{classification_rules}` placeholder in all three prompt files.
    - [x] Remove "Edinburgh Finds" and vertical-specific examples from prompts.
    - [x] Update OSMExtractor to inject classification rules via _get_classification_rules().
    - [x] Update SerperExtractor to inject classification rules via _get_classification_rules().
    - [x] Verify extractors initialize correctly with injected rules (103 tests passing).

- [x] **3.2. Decouple Category Mapper** [dfe72a4]
    - [x] Modify `engine/extraction/utils/category_mapper.py` to accept a `config_path` argument.
    - [x] Update callsites to pass the path (or default to a safe location if needed).

## Phase 4: Verification & Cleanup
**Goal:** Prove purity.

- [ ] **4.1. Run Purity Check**
    - [ ] Run `grep -r "entityType" engine/`.
    - [ ] Run `grep -r "VENUE" engine/`.
    - [ ] Run `grep -r "Listing" engine/` (should only be found in `web` or generic contexts, not as the engine's main model).

- [ ] **4.2. End-to-End Test**
    - [ ] Run a manual extraction for one source.
    - [ ] Verify data lands in `Entity` table in Supabase (or local Postgres).