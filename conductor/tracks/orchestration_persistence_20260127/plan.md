# Implementation Plan: Orchestration Persistence Integration

This plan implements the complete orchestration persistence pipeline, including the `OrchestrationRun` tracking table, async-native persistence, and tuned LLM extraction.

## CRITICAL TESTING REQUIREMENTS (ALL PHASES)

**Every phase MUST include:**
1. **Integration Tests** - Test the COMPLETE flow (orchestrate → persist → extract → merge → database)
   - Use real Prisma database (no mocks for database/persistence/extraction)
   - Verify actual database records exist and contain correct data
   - Test both success and failure paths
2. **Manual CLI Verification** - Run actual CLI commands and inspect results
   - Execute: `python -m engine.orchestration.cli run "test query" --persist`
   - Query database directly to verify records
   - Check that data is usable (not empty JSON blobs)
3. **Database Verification Script** - Write and run verification query BEFORE claiming complete
   - Query all relevant tables (OrchestrationRun, RawIngestion, ExtractedEntity, Entity)
   - Print actual field values to verify they're populated correctly
   - Document results in git notes
4. **NO Phase is Complete Until:**
   - Integration tests pass
   - Manual CLI test produces usable database records
   - Database verification shows correctly structured data
   - Results documented in git notes

**Why This Matters:**
Phase 2 was marked complete based on passing unit tests (22/22), but the real integration was completely broken. Unit tests with mocks don't catch integration failures. Every phase requires end-to-end verification.

## Phase 1: Infrastructure & Async Fixes [checkpoint: 3c44eed]
*Goal: Prepare the database and fix event loop issues to enable reliable data flow.*

- [x] **Task: Update Prisma Schema for OrchestrationRun** [807eb13]
    - [x] Add `OrchestrationRun` model to `engine/schema.prisma`
    - [x] Link `RawIngestion` to `OrchestrationRun`
    - [x] Run `npx prisma migrate dev` (or equivalent) to apply changes
- [x] **Task: Refactor Persistence to be Async-Native** [abc8991]
    - [x] Remove `persist_entities_sync` wrapper usage from `planner.py`
    - [x] Update `orchestrate()` in `planner.py` to be `async`
    - [x] Update CLI to call async orchestrate via `asyncio.run()`
    - [x] Verify Google Places data is now persisted correctly
- [x] **Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Async Fixes' (Protocol in workflow.md)**

## Phase 2: Extraction Integration & Diagnostic Verification [INCOMPLETE - DEBUGGING NEEDED]
*Goal: Fix and verify the extraction integration bridge works end-to-end.*

**STATUS ANALYSIS (2026-01-27):**

**Code Structure: ✓ GOOD**
- `extraction_integration.py` exists with proper `extract_entity()` function (lines 70-174)
- `persistence.py` imports and calls it correctly (line 16, lines 122-143)
- `planner.py` passes `orchestration_run_id` correctly (line 288)
- Raw data IS being saved to disk (confirmed: `engine/data/raw/` has data)
- The integration bridge EXISTS and IS BEING CALLED

**Actual Problem: Silent Failures**
1. **Overly Permissive Error Handling** - `persistence.py:150-165` catches all exceptions and logs them quietly
2. **Missing API Keys** - Serper needs `ANTHROPIC_API_KEY` but fails silently
3. **Structured Source Issues** - Google Places might be throwing exceptions that get swallowed
4. **No Visibility** - Errors logged but not shown prominently to user
5. **Unit Tests Don't Test Reality** - Mocks hide integration failures

**Root Cause:** Errors are being swallowed by try/except blocks. We need to make failures VISIBLE, not rewrite the code.

**Fix Strategy:** Debug, Verify, and Test (not rewrite)

---

- [ ] **Task: Add Diagnostic Logging & Error Visibility**
    - [ ] Add debug logging to `persistence.py` before calling `extract_entity()` (log source, raw_ingestion_id)
    - [ ] Add debug logging after successful extraction (log entity_class, attribute count)
    - [ ] Add full stack trace logging in exception handlers with context
    - [ ] Use structured logging with clear prefixes: `[PERSIST]`, `[EXTRACT]`
    - [ ] Update `planner.py` to add `extraction_errors` list to report dict
    - [ ] Include in extraction errors: source, entity_name, error message, timestamp
    - [ ] Update `planner.py` to count total vs successful extractions
    - [ ] Update CLI (`engine/orchestration/cli.py`) to display "Extraction Pipeline" section
    - [ ] CLI shows "X/Y entities extracted successfully" with color coding
    - [ ] CLI lists extraction failures with source and error details
    - [ ] Add upfront validation check for `ANTHROPIC_API_KEY` if query might need Serper
    - [ ] Display warning: "⚠ Serper extraction will fail without ANTHROPIC_API_KEY"
    - [ ] Test: Run CLI with missing API key and verify warning displays at start
    - [ ] Test: Run CLI with extraction failure and verify error in "Extraction Pipeline" section
    - [ ] Test: Verify logs show entry/exit for each extraction attempt
    - [ ] Test: Verify errors include full context (source, raw_id, exception)
- [ ] **Task: Create Database Verification Script**
    - [ ] Create file `scripts/verify_orchestration_db.py`
    - [ ] Implement query for recent OrchestrationRun records (last 10)
    - [ ] Implement query for linked RawIngestion records per run
    - [ ] Implement query for linked ExtractedEntity records per RawIngestion
    - [ ] Display actual attributes (first 200 chars) to verify not empty
    - [ ] Display discovered_attributes (first 100 chars)
    - [ ] Count totals: runs, raw_ingestions, extracted_entities
    - [ ] Add `--latest` flag to show only most recent run
    - [ ] Add `--run-id <id>` flag to show specific run
    - [ ] Implement color output: green for complete chains, red for broken links
    - [ ] Highlight RawIngestion with no ExtractedEntity (extraction failed)
    - [ ] Highlight ExtractedEntity with empty attributes
    - [ ] Add summary section at end with total counts
    - [ ] Test: Run script without errors
    - [ ] Test: Verify shows complete data lineage (run → raw → extracted)
    - [ ] Test: Verify highlights broken chains
    - [ ] Test: Verify output is human-readable
- [ ] **Task: Write Real Integration Tests**
    - [ ] Create file `tests/engine/orchestration/test_persistence_integration.py`
    - [ ] Write test: `test_google_places_full_integration()`
        - [ ] Test orchestrate → persist → extract → database query for Google Places
        - [ ] Verify OrchestrationRun record exists
        - [ ] Verify RawIngestion record exists and links to run
        - [ ] Verify ExtractedEntity has entity_class = "place"
        - [ ] Verify attributes contains: name, latitude, longitude, address
        - [ ] Verify attributes is NOT empty JSON "{}"
        - [ ] Verify external_ids has google place_id
    - [ ] Write test: `test_serper_extraction_integration()`
        - [ ] Mock Anthropic API to return structured entity (avoid API costs)
        - [ ] Create orchestration run with Serper data
        - [ ] Verify ExtractedEntity created with LLM-extracted data
        - [ ] Verify model_used field is populated
    - [ ] Write test: `test_extraction_failure_handling()`
        - [ ] Create RawIngestion with invalid data
        - [ ] Attempt extraction (should fail gracefully)
        - [ ] Verify error logged in persistence_errors
        - [ ] Verify other entities still processed (resilience)
    - [ ] Write test: `test_multiple_sources_single_run()`
        - [ ] Run orchestration that triggers Google Places + OSM
        - [ ] Verify multiple RawIngestion records link to same run
        - [ ] Verify ExtractedEntity records created for both sources
    - [ ] Ensure all tests use real Prisma database (test database or transaction rollback)
    - [ ] Ensure NO mocks for PersistenceManager, extract_entity, or database
    - [ ] Mock only external APIs (Anthropic, HTTP calls)
    - [ ] Create fixtures for test data cleanup
    - [ ] Verify all 4 tests pass
    - [ ] Verify tests use real database (no mock Prisma client)
    - [ ] Verify coverage >80% for persistence.py and extraction_integration.py
    - [ ] Verify tests catch the type of failure we had (empty ExtractedEntity table)
- [ ] **Task: Manual E2E Verification Protocol**
    - [ ] Step 1: Run live query with CLI
        - [ ] Execute: `python -m engine.orchestration.cli run "powerleague portobello" --persist`
        - [ ] Verify connectors executed: google_places, sport_scotland
        - [ ] Verify candidates found: 5-10
        - [ ] Verify "Extraction Pipeline" section shows X/Y entities extracted
        - [ ] Verify NO errors in Extraction Pipeline section
    - [ ] Step 2: Run verification script
        - [ ] Execute: `python scripts/verify_orchestration_db.py --latest`
        - [ ] Verify shows OrchestrationRun with query
        - [ ] Verify shows RawIngestion records (2-3 for google_places, sport_scotland)
        - [ ] Verify shows ExtractedEntity records with populated attributes
        - [ ] Verify attributes show actual data: {name: "Powerleague Portobello", ...}
        - [ ] Verify NO broken chains (raw with no extracted entity)
    - [ ] Step 3: Direct database inspection
        - [ ] Open Prisma Studio: `cd web && npx prisma studio`
        - [ ] Check OrchestrationRun has record with query "powerleague portobello"
        - [ ] Check RawIngestion has 2-3 records linked to run
        - [ ] Check ExtractedEntity has 2-3 records with entity_class: "place"
        - [ ] Check ExtractedEntity attributes is NOT empty JSON "{}"
        - [ ] Check attributes contains: {"name": "...", "latitude": ..., ...}
    - [ ] Step 4: Document results in git notes
        - [ ] Document CLI execution result (SUCCESS/FAIL)
        - [ ] Document OrchestrationRun ID
        - [ ] Document RawIngestion count
        - [ ] Document ExtractedEntity count
        - [ ] Document sample attributes (paste actual data)
        - [ ] Document extraction errors (NONE or list)
        - [ ] Document verification script output summary
- [ ] **Task: Fix Any Issues Found During Verification**
    - [ ] If Google Places extraction fails:
        - [ ] Check `_extract_entity_from_raw()` logic for Google Places
        - [ ] Verify field extraction handles both old/new API formats
        - [ ] Add error handling for missing required fields
        - [ ] Write integration test for fix
        - [ ] Re-run verification
    - [ ] If Serper extraction fails due to API key:
        - [ ] Document as expected in git notes
        - [ ] Verify error is logged correctly
        - [ ] Ensure other sources still process
    - [ ] If extraction succeeds but attributes are empty:
        - [ ] Check `split_attributes()` logic in extractors
        - [ ] Verify attributes dict is being built correctly
        - [ ] Check JSON serialization (ensure not serializing as empty)
        - [ ] Write integration test for fix
        - [ ] Re-run verification
    - [ ] If database records not created:
        - [ ] Check Prisma schema matches expectations
        - [ ] Verify foreign key relationships
        - [ ] Check transaction handling in persistence
        - [ ] Write integration test for fix
        - [ ] Re-run verification
    - [ ] Ensure all issues found are resolved
    - [ ] Ensure verification re-run shows clean results
    - [ ] Ensure integration tests pass after fixes

**Completed Earlier:**
- [x] **Task: Tune LLM Prompts for Orchestration Pipeline** [1909733]
    - [x] Update prompts in `engine/extraction/prompts/` to focus on concise summaries
    - [x] Improve classification and dimension extraction in prompts
    - [x] Add "Uncertainty Handling" instructions to reduce hallucinations

**Phase 2 Checkpoint Requirements (ALL must be true):**
1. ✅ Diagnostic logging shows entry/exit for each extraction
2. ✅ CLI displays extraction errors prominently
3. ✅ Verification script runs and shows complete data lineage
4. ✅ Integration tests pass (4 tests, real database)
5. ✅ Manual verification shows ExtractedEntity records with populated attributes
6. ✅ Git notes document verification results with actual data samples
7. ✅ No silent failures - all errors visible to user

- [ ] **Task: Conductor - User Manual Verification 'Phase 2: Extraction Integration & Diagnostic Verification' (Protocol in workflow.md)**

## Phase 3: Merging Integration & Pipeline Completion
*Goal: Deliver final deduplicated records to the Entity table.*

- [ ] **Task: Implement Merging Integration Bridge**
    - [ ] Create `engine/orchestration/merging_integration.py`
    - [ ] Implement trust-hierarchy-based field merging
    - [ ] Implement `source_info` tracking for provenance
- [ ] **Task: Integrate Merging into Persistence Manager**
    - [ ] Update `PersistenceManager.persist_entities` to call merging after extraction
    - [ ] Implement transaction safety for the multi-stage pipeline
    - [ ] Handle merge conflicts and log to errors list
- [ ] **Task: Write Integration Tests for Merging** (MANDATORY)
    - [ ] Test: orchestrate() → persist() → extract() → merge() → Entity table query
    - [ ] Use real Prisma database (no mocks for persistence/extraction/merging)
    - [ ] Verify Entity table has populated structured fields (not JSON blobs)
    - [ ] Test trust hierarchy: Google Places coords override Serper coords
    - [ ] Test source_info tracking: verify field provenance is recorded
    - [ ] Test deduplication: same entity from multiple sources creates 1 Entity record
- [ ] **Task: Manual E2E Verification BEFORE Marking Complete** (MANDATORY)
    - [ ] Run: `python -m engine.orchestration.cli run "powerleague portobello" --persist`
    - [ ] Query Entity table: verify records exist with structured fields populated
    - [ ] Check: entity_name, slug, canonical_activities, phone_primary, address_street all populated
    - [ ] Check: source_info JSON shows which connector provided each field
    - [ ] Verify: Multiple sources merge into single Entity record
    - [ ] Document verification results in git notes before committing
- [ ] **Task: Conductor - User Manual Verification 'Phase 3: Merging Integration & Pipeline Completion' (Protocol in workflow.md)**

## Phase 4: Intelligent Planner Enhancements
*Goal: Expand the reach and accuracy of the orchestrator.*

- [ ] **Task: Expand Sports & Domain Detection**
    - [ ] Update `_is_sports_related` with brand and venue keywords (Powerleague, Goals, Nuffield, etc.)
    - [ ] Implement `_is_edinburgh_related` (Edinburgh, Leith, Portobello, etc.)
    - [ ] Implement `_is_ev_related` (charging, EV, electric vehicle, etc.)
- [ ] **Task: Improve Connector Selection Logic**
    - [ ] Update `select_connectors` to use OSM liberally for brand/category searches
    - [ ] Implement triggers for `edinburgh_council` and `open_charge_map`
    - [ ] Add connector selection tests with various query patterns
- [ ] **Task: Write Integration Tests for Intelligent Selection** (MANDATORY)
    - [ ] Test: "powerleague" query triggers sport_scotland connector
    - [ ] Test: "edinburgh council" query triggers edinburgh_council connector
    - [ ] Test: "EV charging" query triggers open_charge_map connector
    - [ ] Test: Brand queries (e.g., "Nuffield gym") trigger OSM + Google Places
    - [ ] Verify: Connector selection logic returns expected connector list for each query type
- [ ] **Task: Manual Verification of Query Detection** (MANDATORY)
    - [ ] Run: `python -m engine.orchestration.cli run "powerleague portobello" --persist`
    - [ ] Verify: sport_scotland connector was selected and executed
    - [ ] Run: `python -m engine.orchestration.cli run "EV charging stations Edinburgh" --persist`
    - [ ] Verify: open_charge_map connector was selected
    - [ ] Check CLI output: connector selection shows intelligent routing
    - [ ] Document query patterns tested in git notes
- [ ] **Task: Conductor - User Manual Verification 'Phase 4: Intelligent Planner Enhancements' (Protocol in workflow.md)**

## Phase 5: Observability & Final Verification
*Goal: Provide clear feedback to the user and ensure production readiness.*

- [ ] **Task: Enhance CLI Reporting**
    - [ ] Add "Pipeline Stages" section showing: Ingestion → Extraction → Merging → Entity
    - [ ] Show extraction counts: X/Y entities extracted successfully
    - [ ] Show merging counts: X entities merged from Y sources
    - [ ] Add "Final Entities" summary with completeness scores per entity
    - [ ] Display source breakdown: which connectors contributed to final entities
- [ ] **Task: Write Integration Tests for Full Pipeline** (MANDATORY)
    - [ ] Test: Complete pipeline from query → final Entity with all stages logged
    - [ ] Test: Error handling at each stage (ingestion fail, extraction fail, merge fail)
    - [ ] Test: Partial success (some sources fail but pipeline continues)
    - [ ] Verify: CLI report shows accurate counts for each stage
    - [ ] Verify: Completeness scores calculated correctly
    - [ ] Coverage check: All new modules >80% coverage
- [ ] **Task: Final Manual End-to-End Verification** (MANDATORY)
    - [ ] Run: `python -m engine.orchestration.cli run "powerleague portobello" --persist`
    - [ ] Verify CLI report shows:
      - Pipeline Stages section with extraction/merging counts
      - Final Entities summary with completeness scores
      - Source breakdown (which connectors contributed)
    - [ ] Query database and verify:
      - OrchestrationRun with accurate metrics
      - RawIngestion records linked correctly
      - ExtractedEntity records with populated fields
      - Entity records with merged data from multiple sources
      - source_info shows provenance
    - [ ] Test spec acceptance criteria (from spec.md):
      - [ ] OrchestrationRun table populated after run
      - [ ] Entity table contains records after --persist
      - [ ] Final Entity records show merged data from multiple sources
      - [ ] Sports queries trigger sport_scotland connector
      - [ ] source_info identifies trust-hierarchy winner for each field
    - [ ] Document all verification results in git notes
- [ ] **Task: Conductor - User Manual Verification 'Phase 5: Observability & Final Verification' (Protocol in workflow.md)**
