# Track Specification: Orchestration Persistence Integration

**Track ID:** orchestration_persistence_20260127
**Type:** Feature
**Status:** Draft
**Priority:** Critical

## Overview
This track implements a production-ready persistence pipeline for the Intelligent Ingestion Orchestration system. Currently, the `--persist` flag only creates intermediate records (`ExtractedEntity`) and fails to produce final merged records in the `Entity` table. This feature will complete the data flow, ensuring that orchestrated multi-source data is extracted, deduplicated, and merged into canonical entities ready for display.

## Functional Requirements

### 1. End-to-End Persistence Pipeline
- **Complete Data Flow:** Integrate `RawIngestion` -> `ExtractedEntity` -> `Extraction Phase` -> `Merging Phase` -> `Entity`.
- **Async-Native Implementation:** Refactor persistence to be fully asynchronous, eliminating silent failures caused by event loop detection logic.
- **Data Lineage:** Ensure every `Entity` record tracks its provenance via `source_info` JSON, mapping fields back to their contributing connectors.

### 2. OrchestrationRun Tracking
- **New Model:** Implement an `OrchestrationRun` Prisma model to track query history, execution mode, status, candidates found, and budget spent.
- **Relational Integrity:** Link `RawIngestion` records to their parent `OrchestrationRun`.

### 3. Intelligent Connector Selection & Sports Detection
- **Expanded Keywords:** Improve `_is_sports_related` detection to include major UK brands (Powerleague, Goals, Nuffield, etc.) and venue types (Leisure Centre, Arena).
- **Liberal Free Sources:** Update the planner to use free sources like OpenStreetMap (OSM) more frequently for brand and category searches.
- **Domain Triggers:** Implement triggers for Edinburgh-specific data (Edinburgh Council) and EV charging (Open Charge Map).

### 4. Tuned LLM Extraction
- **Prompt Optimization:** Update LLM prompts for unstructured sources (Serper) to:
    - Improve attribute extraction from search snippets.
    - Generate concise, "locally curated" summaries without AI-sounding fluff.
    - Enhance classification of `entity_class` and multi-valued `dimensions`.
    - Improve handling of uncertain data to prevent hallucinations.

## Non-Functional Requirements
- **Performance:** Total persistence time < 10 seconds for a 10-entity query.
- **Idempotency:** Re-running the same query should update existing `Entity` records via slug-based deduplication, not create duplicates.
- **Reliability:** Failed extraction or merging for one entity should not block the rest of the pipeline.

## Acceptance Criteria
- [ ] `OrchestrationRun` table is successfully created and populated after a run.
- [ ] `Entity` table contains records after using the `--persist` flag.
- [ ] Final `Entity` records show merged data from multiple sources (e.g., Google coords + Serper name).
- [ ] Sports queries (e.g., "powerleague") successfully trigger the `sport_scotland` connector.
- [ ] `source_info` in the `Entity` table correctly identifies the trust-hierarchy-based winner for each field.

## Manual Verification Plan
- **Visual Inspection:** Use Prisma Studio or direct SQL queries to verify that the `Entity` table is populated correctly and that the `source_info` reflects the expected trust hierarchy.
- **CLI Verification:** Run `python -m engine.orchestration.cli run "powerleague portobello" --persist` and confirm the report shows counts for "Extracted Entities" and "Merged Entities".

## Out of Scope
- Web UI for reviewing merge conflicts (CLI/DB inspection only).
- Real-time "incremental" updates (full re-merge per run for now).
