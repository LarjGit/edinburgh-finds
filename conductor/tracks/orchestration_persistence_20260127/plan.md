# Implementation Plan: Orchestration Persistence Integration

This plan implements the complete orchestration persistence pipeline, including the `OrchestrationRun` tracking table, async-native persistence, and tuned LLM extraction.

## Phase 1: Infrastructure & Async Fixes
*Goal: Prepare the database and fix event loop issues to enable reliable data flow.*

- [x] **Task: Update Prisma Schema for OrchestrationRun** [807eb13]
    - [x] Add `OrchestrationRun` model to `engine/schema.prisma`
    - [x] Link `RawIngestion` to `OrchestrationRun`
    - [x] Run `npx prisma migrate dev` (or equivalent) to apply changes
- [ ] **Task: Refactor Persistence to be Async-Native**
    - [ ] Remove `persist_entities_sync` wrapper in `engine/orchestration/persistence.py`
    - [ ] Update `orchestrate()` in `planner.py` to be `async`
    - [ ] Update CLI to call async orchestrate via `asyncio.run()`
    - [ ] Verify Google Places data is now persisted correctly
- [ ] **Task: Conductor - User Manual Verification 'Phase 1: Infrastructure & Async Fixes' (Protocol in workflow.md)**

## Phase 2: Extraction Integration & Prompt Tuning
*Goal: Bridge the orchestration layer to the extraction engine and improve LLM output.*

- [ ] **Task: Implement Extraction Integration Bridge**
    - [ ] Create `engine/orchestration/extraction_integration.py`
    - [ ] Implement `needs_extraction` logic (skip structured sources)
    - [ ] Implement `extract_entity` to invoke `HybridExtractionEngine`
- [ ] **Task: Tune LLM Prompts for Orchestration Pipeline**
    - [ ] Update prompts in `engine/extraction/prompts/` (or equivalent) to focus on concise summaries
    - [ ] Improve classification and dimension extraction in prompts
    - [ ] Add "Uncertainty Handling" instructions to reduce hallucinations
- [ ] **Task: Conductor - User Manual Verification 'Phase 2: Extraction Integration & Prompt Tuning' (Protocol in workflow.md)**

## Phase 3: Merging Integration & Pipeline Completion
*Goal: Deliver final deduplicated records to the Entity table.*

- [ ] **Task: Implement Merging Integration Bridge**
    - [ ] Create `engine/orchestration/merging_integration.py`
    - [ ] Implement trust-hierarchy-based field merging
    - [ ] Implement `source_info` tracking for provenance
- [ ] **Task: Integrate Phases into Persistence Manager**
    - [ ] Update `PersistenceManager.persist_entities` to call extraction and merging
    - [ ] Implement transaction safety for the multi-stage pipeline
    - [ ] Verify `Entity` table population via E2E test
- [ ] **Task: Conductor - User Manual Verification 'Phase 3: Merging Integration & Pipeline Completion' (Protocol in workflow.md)**

## Phase 4: Intelligent Planner Enhancements
*Goal: Expand the reach and accuracy of the orchestrator.*

- [ ] **Task: Expand Sports & Domain Detection**
    - [ ] Update `_is_sports_related` with brand and venue keywords
    - [ ] Implement `_is_edinburgh_related` and `_is_ev_related`
- [ ] **Task: Improve Connector Selection Logic**
    - [ ] Update `select_connectors` to use OSM liberally for brand/category searches
    - [ ] Implement triggers for `edinburgh_council` and `open_charge_map`
- [ ] **Task: Conductor - User Manual Verification 'Phase 4: Intelligent Planner Enhancements' (Protocol in workflow.md)**

## Phase 5: Observability & Final Verification
*Goal: Provide clear feedback to the user and ensure production readiness.*

- [ ] **Task: Enhance CLI Reporting**
    - [ ] Add "Pipeline Stages" section to the report
    - [ ] Show extraction and merging counts
    - [ ] Add "Final Entities" summary with completeness scores
- [ ] **Task: Final End-to-End Verification**
    - [ ] Run full suite of integration tests
    - [ ] Perform manual verification with "powerleague portobello" query
    - [ ] Verify code coverage > 80% for new modules
- [ ] **Task: Conductor - User Manual Verification 'Phase 5: Observability & Final Verification' (Protocol in workflow.md)**
