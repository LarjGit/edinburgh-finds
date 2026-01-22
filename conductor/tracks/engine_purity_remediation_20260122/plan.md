# Plan: Engine Purity Remediation
**Status:** Active
**Created:** 2026-01-22

## Phase 1: Critical Runtime Fixes (Seed & Ingest)
**Goal:** Restore the ability to run basic engine scripts by fixing the mismatch between Code and DB Schema.

- [ ] **1.1. Fix `seed_data.py`**
    - [x] Read `engine/seed_data.py` to identify legacy SQL/Prisma calls.
    - [x] Refactor to use `Entity` model. [12b3b29]
    - [x] Remove `entityType` field assignment. [12b3b29]
    - [x] Map legacy `entityType="VENUE"` to `entity_class="place"` + `canonical_roles=["provides_facility"]`. [12b3b29]
    - [x] Verify execution: Note - seed_data.py uses SQLite but schema is PostgreSQL. Actual seeding is via ingest.py.

- [ ] **1.2. Fix `ingest.py`**
    - [~] Search `engine/ingest.py` for `entityType` or `Listing` model usage.
    - [ ] Update to use `Entity` model.
    - [ ] Ensure `entity_class` is populated if missing (default to 'thing' or specific logic).

## Phase 2: Extractor Purification
**Goal:** Remove "VENUE" and legacy typing from the extraction layer.

- [ ] **2.1. Audit Extractors**
    - [ ] Run `grep -r "entity_type" engine/extraction/extractors/`.
    - [ ] Run `grep -r "VENUE" engine/extraction/extractors/`.

- [ ] **2.2. Remediation: Universal Initialization**
    - [ ] Refactor `engine/extraction/extractors/osm_extractor.py`: remove `entity_type="VENUE"`.
    - [ ] Refactor `engine/extraction/extractors/google_places_extractor.py`.
    - [ ] Refactor `engine/extraction/extractors/sport_scotland_extractor.py`.
    - [ ] Refactor `engine/extraction/extractors/edinburgh_council_extractor.py`.
    - [ ] Refactor `engine/extraction/extractors/open_charge_map_extractor.py`.
    - [ ] Refactor `engine/extraction/extractors/serper_extractor.py`.

- [ ] **2.3. Remediation: Output Normalization**
    - [ ] Ensure all extractors output `entity_class` instead of `entity_type`.
    - [ ] Update `engine/extraction/base.py` (BaseExtractor) if it enforces legacy types.

## Phase 3: Prompt & Taxonomy Decoupling
**Goal:** Remove vertical-specific knowledge from the core engine assets.

- [ ] **3.1. Refactor Prompts**
    - [ ] Read `engine/extraction/prompts/serper_extraction.txt`.
    - [ ] Identify hardcoded classification lists.
    - [ ] Replace with `{classification_rules}` placeholder.
    - [ ] Update calling code (likely `SerperExtractor` or `LLMClient`) to inject these rules (temporarily can be hardcoded in Python, but out of the text file).

- [ ] **3.2. Decouple Category Mapper**
    - [ ] Modify `engine/extraction/utils/category_mapper.py` to accept a `config_path` argument.
    - [ ] Update callsites to pass the path (or default to a safe location if needed).

## Phase 4: Verification & Cleanup
**Goal:** Prove purity.

- [ ] **4.1. Run Purity Check**
    - [ ] Run `grep -r "entityType" engine/`.
    - [ ] Run `grep -r "VENUE" engine/`.
    - [ ] Run `grep -r "Listing" engine/` (should only be found in `web` or generic contexts, not as the engine's main model).

- [ ] **4.2. End-to-End Test**
    - [ ] Run a manual extraction for one source.
    - [ ] Verify data lands in `Entity` table in Supabase (or local Postgres).