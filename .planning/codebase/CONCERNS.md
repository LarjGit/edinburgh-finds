# Codebase Concerns

**Analysis Date:** 2026-01-27

## Tech Debt

### Incomplete Persistence Pipeline (CRITICAL)

**Area:** Orchestration data flow

**Issue:** The `--persist` flag in orchestration saves data to `RawIngestion` and `ExtractedEntity` tables but never completes the pipeline to save final merged entities to the `Entity` table. End-to-end persistence is broken.

**Files:**
- `engine/orchestration/persistence.py` (lines 58-180)
- `engine/orchestration/planner.py` (lines 259-263)

**Impact:**
- Users cannot persist discovered entities to the database for production use
- Feature is non-functional despite extensive orchestration infrastructure
- Data loss: raw API responses collected but never merged into final Entity records

**Fix approach:**
1. Add merging step after extraction (Persistence → Extract → Dedupe → Merge → Entity table)
2. Implement `merge_entities()` function that applies field-level trust hierarchy
3. Link merged Entity records back to RawIngestion for lineage tracking
4. See `ORCHESTRATION_PERSISTENCE_SPEC.md` for detailed specification

---

### Async/Event Loop Handling Broken (HIGH PRIORITY)

**Area:** Persistence system reliability

**Issue:** Event loop detection in persistence layer causes silent failures when orchestration runs in async context. The fallback from sync to async fails silently, returning `{"persisted_count": 0}` with error message instead of actually persisting.

**Files:**
- `engine/orchestration/persistence.py` (sync wrapper with event loop detection)

**Impact:**
- Google Places and other connector data silently fails to persist in async contexts
- CLI works (no event loop), but Jupyter notebooks and async test contexts lose data
- Difficult to debug: no exception raised, just silent count=0

**Fix approach:**
1. Remove `asyncio.get_running_loop()` detection
2. Make persistence fully async throughout the stack
3. Update CLI to use `asyncio.run(orchestrate())`
4. Update planner to await persistence calls
5. See Phase 1 of `ORCHESTRATION_PERSISTENCE_PLAN.md`

---

### Ingest.py Uses create() Instead of upsert() (MEDIUM)

**Area:** Entity database operations

**Issue:** `engine/ingest.py` line 164 has TODO comment to switch back to upsert. Currently uses `create()` with exception fallback to `update()`. This is inefficient and fragile.

**Files:**
- `engine/ingest.py` (lines 163-174)

**Impact:**
- Slower ingestion (tries create first, then catches exception for update)
- Exception-based control flow is anti-pattern
- No way to distinguish actual creation from updates

**Fix approach:**
1. Replace try/except create→update with proper upsert on slug field
2. Benchmark performance improvement
3. Update tests to verify upsert behavior

---

### Temporary JSON Field Workarounds (MEDIUM)

**Area:** Entity table schema

**Issue:** `engine/ingest.py` lines 145-148 delete `discovered_attributes` and `external_ids` before saving due to JSON serialization issues. These are critical fields being silently dropped.

**Files:**
- `engine/ingest.py` (lines 144-148)

**Impact:**
- External IDs lost during ingestion (breaks deduplication)
- Discovered attributes (LLM-extracted metadata) never persisted
- Data loss with no warning to user

**Fix approach:**
1. Investigate JSON serialization failures
2. Add proper JSON validation before save
3. Remove temporary delete workarounds
4. Ensure round-trip serialization works for all field types
5. Add tests to verify no fields are silently dropped

---

## Security Considerations

### Placeholder API Key Values in Code (LOW SEVERITY)

**Area:** Configuration management

**Issue:** Connector initialization checks for placeholder strings like `"YOUR_GOOGLE_PLACES_API_KEY_HERE"` suggesting these were hardcoded at some point.

**Files:**
- `engine/ingestion/connectors/google_places.py` (API key validation)
- `engine/ingestion/connectors/serper.py` (API key validation)
- `engine/ingestion/connectors/open_charge_map.py` (API key validation)

**Impact:**
- Low risk (only checks if placeholder is set, fails gracefully)
- Suggests historical pattern of hardcoding credentials

**Recommendations:**
1. Audit git history for any hardcoded API keys
2. Ensure all connectors use environment variables only
3. Add pre-commit hook to detect API key patterns
4. Document required environment variables in README

---

### Missing API Key Validation at Startup (LOW)

**Area:** Configuration validation

**Issue:** `engine/orchestration/planner.py` only warns about missing `ANTHROPIC_API_KEY` for Serper extraction, but doesn't fail fast.

**Files:**
- `engine/orchestration/planner.py` (lines checking ANTHROPIC_API_KEY)

**Impact:**
- Extraction may fail mid-pipeline instead of at startup
- Warning logged but extraction proceeds anyway

**Recommendations:**
1. Validate all required API keys at planner initialization
2. Fail fast before executing any connectors
3. Provide clear error message listing missing variables

---

## Performance Bottlenecks

### LLM Cost Not Tracked for Orchestration Pipeline (MEDIUM)

**Area:** Cost control and monitoring

**Issue:** LLM client in extraction tracks costs, but orchestration persistence doesn't report total cost of multi-source extraction and merging.

**Files:**
- `engine/extraction/llm_client.py` (cost tracking implemented)
- `engine/orchestration/persistence.py` (no cost tracking)

**Impact:**
- Users cannot see cost of their queries
- No budget enforcement across orchestration
- Potential for runaway LLM costs in batch operations

**Improvement path:**
1. Add cost tracking to PersistenceManager
2. Report accumulated cost in orchestration report
3. Implement optional cost budget limit
4. Show per-connector cost breakdown

---

### Async Timeouts Not Enforced Consistently (MEDIUM)

**Area:** Connector timeout handling

**Issue:** Each connector defines timeout independently (30-60 seconds), but no global timeout on orchestration phase execution.

**Files:**
- `engine/ingestion/connectors/*.py` (individual timeouts)
- `engine/orchestration/orchestrator.py` (no phase timeout)

**Impact:**
- Single slow connector can block entire phase
- Phase 3 (enrichment) has no limit, could run indefinitely
- User queries may hang with no feedback

**Improvement path:**
1. Add `phase_timeout_seconds` to ExecutionPlan
2. Implement phase-level timeout enforcement
3. Add timeout warnings to diagnostic logging
4. Document timeout configuration in orchestration guide

---

## Fragile Areas

### Deduplication System Relies on Three Fallback Strategies (HIGH RISK)

**Area:** Cross-source deduplication

**Issue:** Deduplication uses external ID → slug match → fuzzy matching in sequence. No mechanism to detect if matches are false positives or missing genuine duplicates.

**Files:**
- `engine/orchestration/execution_context.py` (deduplication logic)
- `tests/engine/orchestration/test_deduplication.py` (test coverage)

**Why fragile:**
- Fuzzy matching can incorrectly merge distinct entities (e.g., "The Racquet Club" vs "Racquet Club")
- Slug-based matching case-sensitive and whitespace-sensitive
- No confidence score returned; binary match/no-match
- Tests exist but edge cases undocumented

**Safe modification:**
1. Add confidence scores to all three matching strategies
2. Document when each strategy is appropriate
3. Add configurable confidence thresholds
4. Log all matches with strategy used for debugging
5. Add manual review workflow for borderline cases

**Test coverage:** Moderate (11 test cases for deduplication)

---

### Extraction Prompts Not Versioned (MEDIUM RISK)

**Area:** LLM extraction consistency

**Issue:** Extraction prompts in `engine/extraction/prompts/` are updated directly without version tracking or A/B testing capability.

**Files:**
- `engine/extraction/prompts/` (all prompt files)
- `engine/extraction/llm_client.py` (prompt loading)

**Why fragile:**
- Prompt changes affect output of all future extractions
- No way to trace which prompt version created each extracted record
- Cannot roll back or compare extraction quality
- Difficult to identify which prompt change caused regression

**Safe modification:**
1. Add `prompt_version` field to extracted records
2. Version prompts with ISO date (e.g., `entity_extraction_20260127.txt`)
3. Load correct version in llm_client based on timestamp
4. Document prompt changelog in `engine/extraction/prompts/README.md`
5. Add prompt comparison tests before deploying

**Test coverage:** Low (no prompt version tests)

---

### Sport Detection Hardcoded Keywords (MEDIUM RISK)

**Area:** Query classification

**Issue:** Sports queries detected via hardcoded keyword list in planner. "Powerleague", "Sportscotland facilities", and similar common terms not recognized.

**Files:**
- `engine/orchestration/query_features.py` (sports keyword list)
- `engine/orchestration/planner.py` (connector selection)

**Why fragile:**
- Missing keywords prevent correct connector selection
- No fallback for misspellings or variations
- Manual maintenance burden

**Safe modification:**
1. Review and expand keyword list (at least 30+ sports/activities)
2. Add fuzzy matching for typos
3. Consider simple ML classifier if keyword list exceeds 100 items
4. Add test cases for common misspellings
5. Document how to add new sports

**Test coverage:** Basic (5 tests for sports detection)

---

## Scaling Limits

### Deduplication O(n²) Comparison (LOW RISK - FUTURE CONCERN)

**Area:** Cross-source deduplication performance

**Issue:** Deduplication compares each accepted candidate against all previous candidates in ExecutionContext. With N candidates, creates O(N²) comparisons.

**Current capacity:** Works fine up to ~100-200 candidates per query
**Limit:** Becomes noticeable at 500+ candidates (e.g., broad queries like "facilities Edinburgh")
**Scaling path:**
1. Implement spatial indexing for geo-based dedup (use lat/lng within 50m radius)
2. Use external ID bucketing (group by source first)
3. Consider embedding-based similarity for text matching

---

### RawIngestion Data Directory Not Pruned (LOW RISK)

**Area:** Disk space management

**Issue:** `engine/data/raw/` grows indefinitely with each ingestion. No cleanup or archival policy.

**Files:**
- `engine/orchestration/persistence.py` (writes to `engine/data/raw/`)

**Current capacity:** Works fine for pilot, but not suitable for production scale
**Limit:** Disk fills up with repeated queries
**Scaling path:**
1. Implement data retention policy (e.g., keep 30 days, archive to cloud)
2. Add cleanup CLI command
3. Compress old raw data
4. Monitor disk usage and alert

---

## Missing Critical Features

### No Merge Conflict Resolution UI (HIGH IMPACT)

**Problem:** When multiple sources provide conflicting data (different phone numbers, addresses), system saves to `MergeConflict` table but no mechanism to resolve or display which value won.

**Files:**
- `web/prisma/schema.prisma` (MergeConflict model exists)
- No UI component to display conflicts
- `engine/extraction/merging.py` (trust hierarchy rules)

**Blocks:**
- Data quality verification
- Manual curation workflow
- Admin dashboard

**Implementation approach:**
1. Create `/admin/conflicts` page in Next.js
2. Display conflicting values with source and confidence
3. Allow admin to select winning value
4. Update Entity record and close conflict

---

### No Extraction Confidence Visibility (MEDIUM IMPACT)

**Problem:** `field_confidence` JSON field exists but not displayed in UI. Users cannot see confidence scores for extracted data.

**Files:**
- `web/prisma/schema.prisma` (field_confidence: Json)
- No TypeScript types generated
- No UI components

**Blocks:**
- Users cannot assess data quality
- Cannot prioritize which records need review
- No transparency into extraction accuracy

**Implementation approach:**
1. Generate TypeScript types for field_confidence
2. Display confidence badge on each field in entity pages
3. Sort entities by average confidence score
4. Add filter for "high confidence only"

---

## Test Coverage Gaps

### Orchestration Pipeline Not End-to-End Tested (HIGH PRIORITY)

**What's not tested:** Complete flow from CLI query to final Entity table record

**Files:**
- `tests/engine/orchestration/` (test suite exists)
- `ORCHESTRATION_PERSISTENCE_SPEC.md` (documents missing E2E test)

**Risk:** Persistence feature appears tested but breaks in real execution

**Gap details:**
- Mock tests exist for persistence (`test_persistence.py`)
- No actual database persistence test
- No real connector execution test
- No multi-source deduplication validation

**Priority:** High (blocking production feature)

**Coverage:**
- Unit tests for individual components: ~90%
- Integration tests (with real DB): ~20%
- End-to-end tests (CLI → Entity table): ~0%

---

### Connector Adapter Bridge Not Tested (MEDIUM PRIORITY)

**What's not tested:** Adapter layer that bridges async connectors to orchestrator

**Files:**
- `engine/orchestration/adapters.py` (adapter implementations)
- `tests/engine/orchestration/test_adapters.py` (minimal tests)

**Risk:**
- Google Places adapter may have undiscovered bugs
- Sport Scotland WFS adapter incomplete (commented out in Phase 3 TODO)
- Error propagation unclear

**Coverage gaps:**
- No timeout handling tests
- No rate limit tests
- No error recovery tests

---

### LLM Extraction Not Tested Against Real Models (LOW PRIORITY - COST)

**What's not tested:** Actual extraction output quality from real Claude models

**Files:**
- `engine/extraction/llm_client.py` (real Anthropic calls)
- Tests use mocks only

**Risk:**
- Prompt changes may degrade quality undetected
- Model version changes (claude-haiku-20250318 → newer) could break output
- Null semantics not verified end-to-end

**Why untested:** Cost (~$0.01 per extraction × 100 tests = $1/test run)

**Mitigation:**
1. Run real extraction tests nightly/weekly
2. Keep snapshot of expected outputs
3. Alert if output differs significantly
4. Budget $20/month for extraction QA

---

## Dependency Risks

### Instructor Library Version Not Pinned (MEDIUM RISK)

**Package:** `instructor` (for Pydantic-LLM integration)

**Files:**
- `engine/requirements.txt` (no version constraint)
- `engine/extraction/llm_client.py` (uses instructor)

**Risk:**
- New instructor versions may have different behavior
- Breaking changes could silently break extraction
- Different retry logic or validation rules

**Mitigation:**
1. Pin to specific version: `instructor==1.3.x`
2. Document tested versions
3. Test before upgrading
4. Monitor instructor releases for breaking changes

---

### Fuzzywuzzy Uses Levenshtein Without Validation (LOW RISK)

**Package:** `fuzzywuzzy` + `python-Levenshtein` (for fuzzy dedup matching)

**Files:**
- `engine/requirements.txt` (both packages listed)
- `engine/orchestration/execution_context.py` (used for entity matching)

**Risk:**
- Levenshtein distance can give unexpected results for short strings
- No minimum confidence threshold enforced

**Mitigation:**
1. Document Levenshtein scoring behavior
2. Add minimum confidence threshold (e.g., 85% match)
3. Only use for names 5+ characters long
4. Add tests for edge cases (abbreviations, typos)

---

## Known Issues from Conductor Tracks

### Sport Scotland WFS Integration Incomplete (BLOCKED)

**Issue:** Phase 3 TODO in test file indicates Sport Scotland WFS layer names not discovered

**Files:**
- `tests/engine/orchestration/test_integration.py` (line 438)
- `engine/orchestration/adapters.py` (Sport Scotland adapter commented)

**Status:** Blocked on external discovery
**Impact:** Sport Scotland data not ingested via orchestration
**Unblock path:** Contact Sport Scotland, identify WFS layer names, uncomment adapter

---

### Engine Purity Verified But Still Fragile (MONITORING REQUIRED)

**Issue:** Engine successfully decoupled from Padel-specific logic, but separation could regress if new features added to wrong layer

**Files:**
- Entire `engine/` directory (must remain vertical-agnostic)
- `lenses/` directory (vertical-specific logic)

**Status:** Active architecture maintained by tests
**Risk:** Refactors could accidentally import lens code or hardcode domain terms
**Mitigation:** Maintain `tests/engine/test_purity.py` as gatekeeper

---

## Observability Gaps

### No Cross-Source Deduplication Visibility (MEDIUM)

**Problem:** When multiple connectors return similar entities, deduplication happens silently. No log showing which candidates were merged or why.

**Files:**
- `engine/orchestration/execution_context.py` (dedup logic)

**Impact:**
- Difficult to debug why expected entity is missing
- Cannot verify deduplication is working correctly
- User has no insight into candidate merging

**Improvement:**
1. Add `dedup_decision` field to candidate records
2. Log which candidates matched and confidence score
3. Include in CLI `--verbose` output

---

### Missing Diagnostic Endpoint for Connector Health (LOW)

**Problem:** No API endpoint to check which connectors are healthy/available

**Files:**
- `engine/extraction/health.py` (health metrics exist but not surfaced)

**Impact:**
- Operators cannot see connector status
- Failures attributed to query rather than source
- No early warning of API degradation

**Improvement:**
1. Create `/health/connectors` API endpoint
2. Check connector availability and response time
3. Display in admin dashboard

---

---

*Concerns audit: 2026-01-27*
