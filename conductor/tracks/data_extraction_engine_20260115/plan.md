# Track: Data Extraction Engine - Implementation Plan

## Overview

This plan details the phased implementation of the Data Extraction Engine. Each phase builds incrementally toward a complete, production-ready extraction system.

**Implementation Philosophy:** Test-Driven Development (TDD) - Write tests first, implement to pass, refactor for quality.

---

## Phase 1: Foundation & Architecture [checkpoint: f44b6f1]

**Goal:** Establish core infrastructure for extraction engine

### Tasks

- [x] Create `engine/extraction/` module structure (9a39fb3)
- [x] Write tests for base extractor interface (`test_base.py`) (5f6030f)
- [x] Implement `base.py` with abstract `BaseExtractor` class (extract, validate, split_attributes methods) (fd40963)
- [x] Write tests for schema utilities (`test_schema_utils.py`) (9c80845)
- [x] Implement `schema_utils.py` (get_extraction_fields, get_llm_config, is_field_in_schema functions) (7e4618a)
- [x] Create `engine/config/extraction.yaml` with model and trust level settings (7e4618a)
- [x] Write tests for config loading (`test_config.py`) (7e4618a)
- [x] Implement config loader with validation (7e4618a)
- [x] Write tests for attribute splitting logic (`test_attribute_splitter.py`) (7e4618a)
- [x] Implement attribute splitter (schema-defined → attributes, rest → discovered_attributes) (7e4618a)
- [x] Create `ExtractedListing` Prisma model for intermediate extraction results (e939646)
- [x] Create `FailedExtraction` Prisma model for quarantine pattern (4bbfeef)
- [x] Run Prisma migration to create tables (dbd4f3f)

**Success Criteria:**
- BaseExtractor interface is tested and documented
- Schema utilities correctly identify fields from listing.py/venue.py
- Attribute splitting correctly separates schema-defined vs discovered fields
- Config loading validates required fields (model, trust_levels)
- All tests pass with >80% coverage

---

## Phase 2: Deterministic Extractors

**Goal:** Implement extractors for clean, structured API sources

### Task 2.1: Google Places Extractor

- [x] Write tests for Google Places extraction (`test_google_places_extractor.py`)
- [x] Create test fixture: `fixtures/google_places_venue_response.json`
- [x] Implement `google_places_extractor.py` extending BaseExtractor
- [x] Implement field mapping (displayName → entity_name, location → lat/lng, etc.)
- [x] Implement external ID capture (Google Place ID)
- [x] Write tests for phone number formatting (integrated in test_google_places_extractor.py)
- [x] Implement `format_phone_uk()` using phonenumbers library
- [x] Integrate phone formatting into Google Places extractor
- [x] Write tests for postcode formatting (integrated in test_google_places_extractor.py)
- [x] Implement `format_postcode_uk()` with UK regex
- [x] Integrate postcode formatting into extractor
- [x] Test extraction with real Google Places fixture data
- [x] Verify all extracted fields match expected schema

### Task 2.2: Sport Scotland Extractor

- [x] Write tests for Sport Scotland extraction (`test_sport_scotland_extractor.py`)
- [x] Create test fixture: `fixtures/sport_scotland_facility_response.json`
- [x] Implement `sport_scotland_extractor.py` extending BaseExtractor
- [x] Implement GeoJSON feature parsing
- [x] Map Sport Scotland fields to venue schema
- [x] Handle Sport Scotland-specific attributes (facility types, sports offered)
- [x] Test extraction with real Sport Scotland WFS data

### Task 2.3: Edinburgh Council Extractor

- [x] Update existing `transform.py` to new BaseExtractor interface
- [x] Write comprehensive tests for Edinburgh Council (`test_edinburgh_council_extractor.py`)
- [x] Refactor existing transform logic into `edinburgh_council_extractor.py`
- [x] Ensure compatibility with BaseExtractor interface
- [x] Add external ID tracking for council features
- [x] Test with existing raw Edinburgh Council data

### Task 2.4: OpenChargeMap Extractor

- [ ] Write tests for OpenChargeMap extraction (`test_open_charge_map_extractor.py`)
- [ ] Create test fixture: `fixtures/open_charge_map_response.json`
- [ ] Implement `open_charge_map_extractor.py` extending BaseExtractor
- [ ] Map charging station data to venue attributes (discovered_attributes for EV-specific fields)
- [ ] Handle enrichment-only extractions (coordinates, availability)
- [ ] Test extraction with real OpenChargeMap data

**Success Criteria:**
- ✅ All 4 deterministic extractors implemented and tested
- ✅ Phone and postcode formatting working with 100% accuracy
- ✅ External IDs captured for all sources
- ✅ Test coverage >80% for deterministic extractors
- ✅ Fixtures cover common and edge cases

**Phase Checkpoint:** Deterministic extraction working for 4/6 sources

---

## Phase 3: LLM Extractors & Instructor Integration

**Goal:** Implement intelligent extraction for unstructured sources

### Task 3.1: Instructor Setup

- [ ] Add `instructor` and `anthropic` to project dependencies
- [ ] Write tests for Instructor integration (`test_instructor_client.py`)
- [ ] Implement `llm_client.py` wrapping Anthropic client with Instructor
- [ ] Create Pydantic models for structured LLM output (`models/venue_extraction.py`)
- [ ] Implement retry logic with validation feedback (max 2 retries)
- [ ] Write tests for null semantics enforcement (`test_null_semantics.py`)
- [ ] Create prompt templates with null semantic rules (`prompts/extraction_base.txt`)
- [ ] Test LLM client with sample prompts

### Task 3.2: Serper Extractor

- [ ] Write tests for Serper extraction (`test_serper_extractor.py`)
- [ ] Create test fixtures: `fixtures/serper_padel_search.json`
- [ ] Implement `serper_extractor.py` extending BaseExtractor with LLM mode
- [ ] Create Serper-specific prompt template
- [ ] Implement snippet aggregation (combine multiple search results)
- [ ] Handle missing fields gracefully (lots of nulls expected)
- [ ] Write tests for conflict detection within raw text
- [ ] Implement conflict resolution logic (recency wins, specificity wins)
- [ ] Test extraction with real Serper fixtures
- [ ] Verify confidence scoring for ambiguous fields

### Task 3.3: OSM Extractor

- [ ] Write tests for OSM extraction (`test_osm_extractor.py`)
- [ ] Create test fixtures: `fixtures/osm_overpass_sports_facility.json`
- [ ] Implement `osm_extractor.py` extending BaseExtractor with LLM mode
- [ ] Create OSM-specific prompt template (handle free-text tags)
- [ ] Map OSM tags to venue fields (sport=* → sports offered, amenity=* → categories)
- [ ] Extract OSM ID for deduplication
- [ ] Handle multilingual tags and descriptions
- [ ] Test extraction with real OSM Overpass data

**Success Criteria:**
- ✅ Instructor library integrated with retry logic
- ✅ Serper and OSM extractors working with >85% success rate
- ✅ Null semantics correctly enforced (null ≠ false for booleans)
- ✅ Conflict detection flags ambiguous data
- ✅ LLM extraction cached to prevent redundant API calls
- ✅ Test coverage >80% for LLM extractors

**Phase Checkpoint:** All 6 sources extracting successfully

---

## Phase 4: Special Field Processing

**Goal:** Implement advanced field extraction (opening hours, summaries)

### Task 4.1: Opening Hours Extraction

- [ ] Write tests for opening hours parsing (`test_opening_hours.py`)
- [ ] Create test fixtures with various hour formats ("Mon-Fri 9-5", "24/7", structured JSON)
- [ ] Implement `opening_hours_extractor.py` with LLM template
- [ ] Define strict JSON schema for opening hours output
- [ ] Implement validation: 24-hour format, valid times, CLOSED vs null handling
- [ ] Test with edge cases (24-hour venues, seasonal hours, irregular schedules)
- [ ] Integrate into all extractors

### Task 4.2: Categories Handling

- [ ] Create `engine/config/canonical_categories.yaml` with initial taxonomy
- [ ] Write tests for category extraction (`test_categories.py`)
- [ ] Implement LLM category extraction (free-form, multiple allowed)
- [ ] Implement canonical category mapping (config-based, manual promotion workflow)
- [ ] Write tests for category promotion logic
- [ ] Document category promotion workflow in README

### Task 4.3: Summary Synthesis (Multi-Stage)

**Sub-task 4.3.1: Rich Text Capture (Update Ingestion)**

- [ ] Update `engine/config/sources.yaml` - add rich text fields to Google Places field mask
- [ ] Update `google_places.py` connector to capture editorialSummary and reviews
- [ ] Update `serper.py` connector to extract meta descriptions from snippets
- [ ] Add `raw_descriptions` field to RawIngestion model or extraction output
- [ ] Write tests for rich text storage (`test_rich_text_capture.py`)
- [ ] Test that reviews and descriptions are captured in raw data

**Sub-task 4.3.2: Summary Synthesis Implementation**

- [ ] Write tests for summary synthesis (`test_summary_synthesis.py`)
- [ ] Create test fixtures with structured facts + rich descriptions
- [ ] Implement `summary_synthesizer.py` with multi-stage process:
  - Stage 1: Extract structured facts (already done by main extractor)
  - Stage 2: Gather rich descriptions from raw_descriptions field
  - Stage 3: LLM synthesis with character limits
- [ ] Implement character limit enforcement with retry (max 3 attempts)
- [ ] Add `llm_extraction_config` to FieldSpec in venue.py for summary fields
- [ ] Test summary generation for padel_summary, tennis_summary, gym_summary
- [ ] Verify summaries follow "Knowledgeable Local Friend" voice (reference product-guidelines.md)
- [ ] Test character limit enforcement (min/max boundaries)

**Success Criteria:**
- ✅ Opening hours extracted in consistent JSON format
- ✅ Categories extracted as free-form arrays
- ✅ Canonical categories config functional
- ✅ Rich text (reviews, descriptions) captured from Google Places
- ✅ Summaries synthesized with character limits enforced
- ✅ Summary quality validated (practical, no fluff, local context)
- ✅ Test coverage >80% for all special field processors

**Phase Checkpoint:** Special fields (hours, summaries, categories) working end-to-end

---

## Phase 5: Deduplication & Merging

**Goal:** Combine multi-source data into single high-quality listings

### Task 5.1: Deduplication Detection

- [ ] Write tests for external ID matching (`test_external_id_matching.py`)
- [ ] Implement external ID matcher (Google Place ID, OSM ID, etc.)
- [ ] Write tests for slug matching (`test_slug_matching.py`)
- [ ] Implement slug-based deduplication
- [ ] Add `fuzzywuzzy` dependency for string similarity
- [ ] Write tests for fuzzy name + location matching (`test_fuzzy_matching.py`)
- [ ] Implement fuzzy matcher with confidence scoring
- [ ] Write tests for multi-strategy matching orchestration
- [ ] Implement `deduplication.py` with strategy cascade (external ID → slug → fuzzy)
- [ ] Test with known duplicate fixtures (same venue, different sources)

### Task 5.2: Field-Level Trust Merging

- [ ] Write tests for trust hierarchy (`test_trust_hierarchy.py`)
- [ ] Implement trust level loader from extraction.yaml
- [ ] Write tests for field-level merge logic (`test_field_merge.py`)
- [ ] Implement `merge_field()` function (higher trust wins)
- [ ] Add field_sources tracking to Listing model (or separate FieldProvenance table)
- [ ] Run Prisma migration for field provenance tracking
- [ ] Write tests for full listing merge (`test_listing_merge.py`)
- [ ] Implement `merge_listings()` that combines multiple ExtractedListing records
- [ ] Test merge scenarios:
  - 2 sources, no conflicts (simple merge)
  - 2 sources, conflicting fields (trust hierarchy resolves)
  - 3+ sources, complex conflicts
  - Manual override (trust=100) always wins

### Task 5.3: Merge Conflict Reporting

- [ ] Write tests for conflict detection (`test_merge_conflicts.py`)
- [ ] Implement conflict detector (same field, different values, similar trust levels)
- [ ] Create `MergeConflict` model for tracking unresolved conflicts
- [ ] Implement conflict logging and storage
- [ ] Test conflict reporting in health dashboard

**Success Criteria:**
- ✅ External ID matching: 100% accuracy
- ✅ Slug matching: 95% accuracy
- ✅ Fuzzy matching: >85% accuracy for true duplicates
- ✅ False positive rate <5% (incorrectly merged distinct entities)
- ✅ Field-level trust correctly prioritizes manual > official > crowd > open
- ✅ Merge conflicts logged for manual review
- ✅ Test coverage >80% for deduplication and merging

**Phase Checkpoint:** Multi-source merging produces single, high-quality listings

---

## Phase 6: Error Handling & Observability

**Goal:** Production-ready error handling and monitoring

### Task 6.1: Quarantine Pattern Implementation

- [ ] Write tests for quarantine logic (`test_quarantine.py`)
- [ ] Implement error capture to FailedExtraction table
- [ ] Implement retry counter and max retry enforcement
- [ ] Write tests for retry workflow
- [ ] Implement CLI retry command (`--retry-failed`)
- [ ] Test quarantine with intentionally failing fixtures (invalid data, LLM timeout simulation)

### Task 6.2: Health Dashboard

- [ ] Write tests for health metrics calculation (`test_health_metrics.py`)
- [ ] Implement `health_check.py` with metrics:
  - Unprocessed record count
  - Success rate per source
  - Field null rates
  - Recent failures
  - LLM usage and cost estimation
  - Merge conflict count
- [ ] Implement CLI health command (`python -m engine.extraction.health`)
- [ ] Create formatted output (table, colors for warnings)
- [ ] Test health dashboard with sample data

### Task 6.3: Structured Logging

- [ ] Write tests for logging configuration (`test_logging.py`)
- [ ] Implement structured logging (JSON format with contextual fields)
- [ ] Add logging to all extractors (info, warning, error levels)
- [ ] Log extraction metadata: source, duration, tokens, fields extracted, confidence
- [ ] Test log output format and content

### Task 6.4: LLM Cost Tracking

- [ ] Write tests for cost calculation (`test_llm_cost.py`)
- [ ] Implement token counter (from Anthropic API response)
- [ ] Implement cost estimator (tokens × model pricing)
- [ ] Add cost tracking to health dashboard
- [ ] Create CLI command for cost report (`--cost-report`)
- [ ] Test cost tracking with sample LLM calls

**Success Criteria:**
- ✅ Failed extractions automatically quarantined (don't halt pipeline)
- ✅ Retry workflow recovers >50% of transient failures
- ✅ Health dashboard shows actionable insights
- ✅ Structured logs enable debugging
- ✅ LLM cost tracked and visible
- ✅ Test coverage >80% for observability features

**Phase Checkpoint:** Extraction engine observable and resilient

---

## Phase 7: CLI & Orchestration

**Goal:** Complete CLI interface for all extraction workflows

### Task 7.1: Single Record Extraction

- [ ] Write tests for CLI single mode (`test_cli_single.py`)
- [ ] Implement `run.py --raw-id=<uuid>` command
- [ ] Implement verbose output (field-by-field extraction results)
- [ ] Test with various RawIngestion record IDs

### Task 7.2: Per-Source Batch Extraction

- [ ] Write tests for CLI per-source mode (`test_cli_source.py`)
- [ ] Implement `run.py --source=<source_name>` command
- [ ] Implement progress bar for batch processing
- [ ] Implement summary report (success/failure counts, time, cost)
- [ ] Test with each source type

### Task 7.3: Batch All Unprocessed

- [ ] Write tests for CLI batch mode (`test_cli_batch.py`)
- [ ] Implement `run_all.py` command
- [ ] Query all unprocessed RawIngestion records
- [ ] Process in source-grouped batches
- [ ] Implement overall summary report
- [ ] Test with mixed unprocessed records

### Task 7.4: Orchestration Helpers

- [ ] Implement `--dry-run` flag (show what would be extracted, don't commit)
- [ ] Implement `--limit=N` flag (process only N records, for testing)
- [ ] Implement `--force-retry` flag (re-extract even if already processed)
- [ ] Write tests for all CLI flags
- [ ] Create usage documentation (`docs/extraction_cli.md`)

**Success Criteria:**
- ✅ CLI supports all 4 modes (single, per-source, batch all, retry)
- ✅ Progress indicators show real-time status
- ✅ Summary reports provide actionable data
- ✅ Dry-run mode enables safe testing
- ✅ Documentation complete and accurate
- ✅ Test coverage >80% for CLI interface

**Phase Checkpoint:** Full CLI operational and documented

---

## Phase 8: Integration & End-to-End Testing

**Goal:** Verify complete pipeline functionality

### Task 8.1: End-to-End Test Suite

- [ ] Write end-to-end test: Ingest → Extract → Merge → Verify Listing created
- [ ] Test scenario 1: Single source, single venue (Google Places)
- [ ] Test scenario 2: Multi-source, same venue (Google + OSM + Serper)
- [ ] Test scenario 3: Discovery ingestion, new venue extraction
- [ ] Test scenario 4: Entity-specific ingestion, targeted extraction
- [ ] Test scenario 5: Conflicting data from multiple sources, trust hierarchy resolves
- [ ] Test scenario 6: Failed extraction, quarantine, retry, success
- [ ] Verify all tests use fixtures (no real API calls in tests)

### Task 8.2: Snapshot Validation

- [ ] Create "known-good" extraction snapshots for each source
- [ ] Write snapshot comparison tests
- [ ] Test that future extractions match snapshots (no regressions)
- [ ] Document snapshot update workflow

### Task 8.3: Integration with Existing Codebase

- [ ] Verify extraction works with existing Prisma schema
- [ ] Test compatibility with web app (Listing queries work)
- [ ] Verify extracted data displays correctly in frontend
- [ ] Test seed data generation from extracted listings

**Success Criteria:**
- ✅ End-to-end tests cover full pipeline
- ✅ Snapshots prevent regressions
- ✅ Integration with web app verified
- ✅ All tests pass with >80% overall coverage
- ✅ No breaking changes to existing features

**Phase Checkpoint:** Extraction engine fully integrated and tested

---

## Phase 9: Documentation & Knowledge Transfer

**Goal:** Complete documentation for future maintenance and extension

### Tasks

- [ ] Write `docs/extraction_engine_overview.md` (architecture, design decisions)
- [ ] Write `docs/adding_new_extractor.md` (step-by-step guide with template)
- [ ] Write `docs/extraction_cli_reference.md` (all commands with examples)
- [ ] Write `docs/troubleshooting_extraction.md` (common errors and solutions)
- [ ] Document field-level trust configuration (how to add/adjust trust levels)
- [ ] Document canonical category management (promotion workflow)
- [ ] Document LLM prompt customization (how to tune per source)
- [ ] Create inline code documentation (docstrings for all public functions)
- [ ] Update ARCHITECTURE.md with extraction engine section
- [ ] Update README.md with extraction quickstart

**Success Criteria:**
- ✅ Documentation complete and accurate
- ✅ New developer can add extractor in <4 hours using docs
- ✅ Troubleshooting guide covers >90% of common issues
- ✅ Architecture diagrams updated
- ✅ Code documentation >90% coverage

**Phase Checkpoint:** Knowledge transfer complete

---

## Phase 10: Production Readiness & Optimization

**Goal:** Optimize for production deployment

### Tasks

- [ ] Run full extraction on all existing RawIngestion records
- [ ] Measure and document performance metrics (records/hour, cost/record)
- [ ] Identify bottlenecks (LLM latency, database writes, etc.)
- [ ] Implement async processing for deterministic extractors (if needed)
- [ ] Add database indexes for common queries (source, status, created_at)
- [ ] Implement LLM caching (check before calling API)
- [ ] Write tests for cache hit/miss scenarios
- [ ] Optimize Pydantic validation (use compiled validators if needed)
- [ ] Run extraction with 1000+ records, verify no memory leaks
- [ ] Document production deployment checklist
- [ ] Create monitoring alert thresholds (failure rate >10%, cost >$X/day)

**Success Criteria:**
- ✅ Extraction throughput >20 records/minute
- ✅ LLM cost <£0.50 per 100 records
- ✅ Memory usage stable (no leaks over long runs)
- ✅ Production deployment checklist complete
- ✅ Monitoring alerts configured

**Phase Checkpoint:** Ready for production deployment

---

## Success Metrics (Overall Track)

### Must-Have (Phase 1-8)

- [ ] All 6 ingestion sources have functional extractors
- [ ] Deterministic extractors: 100% success rate
- [ ] LLM extractors: >85% success rate
- [ ] Zero duplicate listings created (deduplication working)
- [ ] Test coverage >80% across all modules
- [ ] Rich text captured from Google Places and Serper
- [ ] Summary synthesis working for all `*_summary` fields
- [ ] Field-level trust tracking operational
- [ ] Health dashboard provides actionable insights
- [ ] CLI supports all documented modes
- [ ] End-to-end tests pass consistently

### Nice-to-Have (Phase 9-10)

- [ ] Documentation enables self-service troubleshooting
- [ ] Performance optimized for production scale
- [ ] LLM caching reduces costs by >30%
- [ ] Async processing implemented (if bottlenecks identified)

---

## Future Considerations (Not in Scope)

### Relationship Extraction (Separate Track)

**Placeholder:** Track already marked in tracks.md

- Extract "teaches_at", "plays_at", "based_at" relationships
- Populate `ListingRelationship` table
- Enable ecosystem graph queries

### Advanced Features

- Automated canonical category promotion (ML-based)
- Image extraction and validation
- Sentiment analysis from reviews
- Real-time extraction on webhook triggers
- Parallel worker architecture for high-volume processing

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| LLM costs exceed budget | Implement caching early (Phase 3), monitor costs (Phase 6), use Haiku (cheap model) |
| Deduplication creates false positives | Multi-strategy with confidence thresholds, manual review for <85% matches |
| Extraction too slow | Async processing, batch optimization, profile and optimize bottlenecks (Phase 10) |
| Schema changes break extractors | Comprehensive test coverage, snapshot testing, schema versioning |
| LLM quality degrades over time | Snapshot tests catch regressions, prompt versioning, model pinning |

---

## Checkpoints for User Verification

**After Phase 2:**
- Run: `python -m engine.extraction.run --source=google_places --limit=5`
- Verify: 5 Google Places venues extracted with correct fields
- Confirm: Phone numbers formatted to E.164, postcodes formatted correctly

**After Phase 3:**
- Run: `python -m engine.extraction.run --source=serper --limit=3`
- Verify: 3 Serper results extracted (expect some nulls, that's normal)
- Confirm: Null semantics correct (null ≠ false for booleans)

**After Phase 4:**
- Run: `python -m engine.extraction.run --raw-id=<google_places_record>`
- Verify: Summary fields populated (padel_summary, gym_summary, etc.)
- Confirm: Summaries are 100-200 characters, "Knowledgeable Local Friend" voice

**After Phase 5:**
- Run: `python -m engine.extraction.run_all --limit=10`
- Verify: Duplicate venues merged (check Listing table, not multiple "Game4Padel" records)
- Confirm: Field provenance shows which source provided each field

**After Phase 7:**
- Run: `python -m engine.extraction.health`
- Verify: Dashboard shows stats for all sources
- Confirm: No critical errors, failure rate <5%

---

## Definition of Done

A phase is complete when:

1. All tasks marked `[x]` complete
2. All tests passing (pytest with >80% coverage)
3. Code passes linting and type checking
4. User verification checkpoint passed (if applicable)
5. Changes committed with proper message (e.g., `feat(extraction): Add Google Places extractor`)
6. Git note attached with phase summary
7. Plan.md updated with checkpoint commit hash
8. Conductor plan update committed

Track is complete when:

1. All 10 phases marked complete
2. Success metrics achieved
3. Documentation published
4. Production deployment successful
5. User acceptance confirmed
