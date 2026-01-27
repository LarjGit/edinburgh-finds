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

### Task 2.1: Add Diagnostic Logging & Error Visibility
**Goal:** Make failures visible so we know what's actually breaking

**Implementation:**
1. **Add debug logging to `persistence.py`:**
   - Before calling `extract_entity()` - log source, raw_ingestion_id
   - After successful extraction - log entity_class, attribute count
   - In exception handlers - log full stack trace with context
   - Use structured logging with clear prefixes: `[PERSIST]`, `[EXTRACT]`

2. **Update `planner.py` to show extraction errors prominently:**
   - Add separate section in report: `extraction_errors` list
   - Include: source, entity_name, error message, timestamp
   - Count total vs successful extractions

3. **Update CLI (`engine/orchestration/cli.py`) to display extraction errors:**
   - Add "Extraction Pipeline" section after connector metrics
   - Show: "X/Y entities extracted successfully"
   - List extraction failures with source and error
   - Color-code: green for success, red for failures

4. **Add upfront validation for API keys:**
   - Check `ANTHROPIC_API_KEY` at start if query might need Serper
   - Warn user: "⚠ Serper extraction will fail without ANTHROPIC_API_KEY"
   - Don't block execution, just warn

**Acceptance Criteria:**
- Run CLI with missing API key → see warning at start
- Run CLI with extraction failure → see error in "Extraction Pipeline" section
- Logs show entry/exit for each extraction attempt
- Errors include full context (source, raw_id, exception)

---

### Task 2.2: Create Database Verification Script
**Goal:** Quick tool to inspect what's actually in the database

**Implementation:**
Create `scripts/verify_orchestration_db.py`:

```python
"""
Database verification script for orchestration pipeline.

Queries all relevant tables and displays actual data to verify
the pipeline is working end-to-end.

Usage:
    python scripts/verify_orchestration_db.py [--run-id <id>]
    python scripts/verify_orchestration_db.py --latest
"""

# Queries:
# 1. List recent OrchestrationRun records (last 10)
# 2. For each run, show linked RawIngestion records
# 3. For each RawIngestion, show linked ExtractedEntity records
# 4. Show actual attributes (first 200 chars) to verify not empty
# 5. Count totals: runs, raw_ingestions, extracted_entities

# Output format:
# OrchestrationRun: <id> | Query: <query> | Status: <status>
#   └─ RawIngestion: <id> | Source: <source> | Status: <status>
#      └─ ExtractedEntity: <id> | Class: <entity_class>
#         Attributes: {name: "...", ...} (first 200 chars)
#         Discovered: {...} (first 100 chars)

# Highlight issues:
# - RawIngestion with no ExtractedEntity (extraction failed)
# - ExtractedEntity with empty attributes (extraction returned nothing)
# - OrchestrationRun with status "failed"
```

**Features:**
- `--latest` flag: Show only the most recent run
- `--run-id <id>` flag: Show specific run
- Color output: green for complete chains, red for broken links
- Summary at end: "X runs, Y raw ingestions, Z extracted entities"

**Acceptance Criteria:**
- Script runs without errors
- Shows complete data lineage (run → raw → extracted)
- Highlights broken chains (raw with no extracted entity)
- Output is human-readable

---

### Task 2.3: Write Real Integration Tests
**Goal:** Test with actual database, no mocks for core persistence/extraction flow

**Implementation:**
Create `tests/engine/orchestration/test_persistence_integration.py`:

**Test 1: Full Structured Source Flow (Google Places)**
```python
async def test_google_places_full_integration():
    """Test complete flow: orchestrate → persist → extract → database query"""
    # 1. Create orchestration run with Google Places data
    # 2. Verify OrchestrationRun record exists
    # 3. Verify RawIngestion record exists and links to run
    # 4. Verify ExtractedEntity record exists with:
    #    - entity_class = "place"
    #    - attributes contains: name, latitude, longitude, address
    #    - attributes is not empty JSON "{}"
    # 5. Verify external_ids has google place_id
```

**Test 2: Unstructured Source with Mock LLM (Serper)**
```python
async def test_serper_extraction_integration(mock_anthropic):
    """Test Serper extraction with mocked LLM (to avoid API costs)"""
    # 1. Mock Anthropic API to return structured entity
    # 2. Create orchestration run with Serper data
    # 3. Verify ExtractedEntity created with LLM-extracted data
    # 4. Verify model_used field is populated
```

**Test 3: Extraction Failure Handling**
```python
async def test_extraction_failure_handling():
    """Test that extraction failures don't crash persistence"""
    # 1. Create RawIngestion with invalid data
    # 2. Attempt extraction (should fail)
    # 3. Verify error logged in persistence_errors
    # 4. Verify other entities still processed
```

**Test 4: Multiple Sources Same Run**
```python
async def test_multiple_sources_single_run():
    """Test orchestration with multiple connectors"""
    # 1. Run orchestration that triggers Google Places + OSM
    # 2. Verify multiple RawIngestion records link to same run
    # 3. Verify ExtractedEntity records created for both sources
```

**Key Requirements:**
- Use real Prisma database (test database or transaction rollback)
- No mocks for PersistenceManager, extract_entity, or database
- Mock only external APIs (Anthropic, HTTP calls)
- Use fixtures for test data cleanup
- Each test verifies actual database state

**Acceptance Criteria:**
- All 4 tests pass
- Tests use real database (no mock Prisma client)
- Coverage >80% for persistence.py and extraction_integration.py
- Tests catch the type of failure we had (empty ExtractedEntity table)

---

### Task 2.4: Manual E2E Verification Protocol
**Goal:** Human verification that the system actually works

**Step 1: Run Live Query**
```bash
# With Google Places (structured source)
python -m engine.orchestration.cli run "powerleague portobello" --persist

# Expected output:
# - Connectors executed: google_places, sport_scotland
# - Candidates found: 5-10
# - Extraction Pipeline: X/Y entities extracted successfully
# - Persisted: X entities
# - NO errors in Extraction Pipeline section
```

**Step 2: Run Verification Script**
```bash
python scripts/verify_orchestration_db.py --latest

# Expected output:
# - Shows OrchestrationRun with query
# - Shows RawIngestion records (2-3 for google_places, sport_scotland)
# - Shows ExtractedEntity records with populated attributes
# - Attributes show actual data: {name: "Powerleague Portobello", ...}
# - NO broken chains (raw with no extracted entity)
```

**Step 3: Direct Database Query**
```bash
# Use Prisma Studio or direct SQL to verify
cd web && npx prisma studio

# Check tables:
# 1. OrchestrationRun - has record with query "powerleague portobello"
# 2. RawIngestion - has 2-3 records linked to run
# 3. ExtractedEntity - has 2-3 records with:
#    - entity_class: "place"
#    - attributes: NOT empty JSON "{}"
#    - attributes contains: {"name": "...", "latitude": ..., ...}
```

**Step 4: Document Results**
Create verification report in git notes:
```
Phase 2 Manual Verification Results:
- CLI execution: SUCCESS
- OrchestrationRun created: YES (id: <id>)
- RawIngestion count: X
- ExtractedEntity count: X
- Sample attributes: {name: "...", latitude: ..., address: "..."}
- Extraction errors: NONE (or list errors if any)
- Verification script output: [paste summary]
```

**Acceptance Criteria:**
- CLI completes without crashes
- Verification script shows complete data lineage
- ExtractedEntity table has records with populated attributes
- Attributes contain actual data (not empty JSON)
- All results documented in git notes before commit

---

### Task 2.5: Fix Any Issues Found
**Goal:** Address issues discovered during verification

**Contingency Actions Based on Findings:**

**If Google Places extraction fails:**
- Check `_extract_entity_from_raw()` logic for Google Places
- Verify field extraction handles both old/new API formats
- Add error handling for missing required fields

**If Serper extraction fails due to API key:**
- This is expected - document in git notes
- Verify error is logged correctly
- Ensure other sources still process

**If extraction succeeds but attributes are empty:**
- Check `split_attributes()` logic in extractors
- Verify attributes dict is being built correctly
- Check JSON serialization (ensure not serializing as empty)

**If database records not created:**
- Check Prisma schema matches expectations
- Verify foreign key relationships
- Check transaction handling in persistence

**Implementation:**
- Only fix issues found during verification
- Each fix must be tested with integration test
- Re-run verification after each fix

**Acceptance Criteria:**
- All issues found during verification are resolved
- Verification re-run shows clean results
- Integration tests pass

---

### Summary Checkpoint Requirements

**Before marking Phase 2 complete, ALL must be true:**
1. ✅ Diagnostic logging shows entry/exit for each extraction
2. ✅ CLI displays extraction errors prominently
3. ✅ Verification script runs and shows complete data lineage
4. ✅ Integration tests pass (4 tests, real database)
5. ✅ Manual verification shows ExtractedEntity records with populated attributes
6. ✅ Git notes document verification results with actual data samples
7. ✅ No silent failures - all errors visible to user

**Completed Earlier:**
- [x] **Task: Tune LLM Prompts for Orchestration Pipeline** [1909733]
    - [x] Update prompts in `engine/extraction/prompts/` to focus on concise summaries
    - [x] Improve classification and dimension extraction in prompts
    - [x] Add "Uncertainty Handling" instructions to reduce hallucinations

**Phase 2 Verification Task:**
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
