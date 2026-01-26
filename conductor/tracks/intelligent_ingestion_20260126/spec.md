# Specification: Intelligent Ingestion Orchestration

## 1. Overview
Implement an integration layer for the existing orchestration kernel (`engine/orchestration/`) to enable intelligent, CLI-driven entity ingestion. This track will move the system from a manual connector execution model to an automated flow where the system analyzes a query and orchestrates the best discovery and enrichment strategy.

## 2. Functional Requirements
- **CLI Entry Point:** Create `python -m engine.orchestration.cli` to trigger the orchestration flow via free-text queries.
- **Intelligent Selection:** Implement a `Planner` that analyzes queries (using `QueryFeatures`) and budget constraints to select the optimal set of connectors.
- **Connector Registry:** A central registry for all 6 existing connectors (`Serper`, `GooglePlaces`, `OSM`, `SportScotland`, `EdinburghCouncil`, `OpenChargeMap`) with metadata (cost, phase, trust level).
- **Adaptation Layer:** Bridges the async `BaseConnector` interface with the orchestrator's execution flow, including result mapping to the canonical candidate schema.
- **Persistence Integration:** Option to persist results to the database via existing extractor/ingestion logic.
- **Observability:** Track and display per-connector metrics (latency, cost, candidates found) and errors in a structured report.

## 3. Non-Functional Requirements
- **Reliability:** Individual connector failures must be non-fatal; the orchestrator should continue with remaining planned connectors.
- **Efficiency:** Enforce budget limits and early stopping based on confidence or candidate count.
- **Maintainability:** Isolate intelligence logic (selection rules) from execution logic (orchestrator kernel).

## 4. Acceptance Criteria (Phased)
### Phase A (Plumbing)
- [ ] CLI `run` command executes hardcoded connectors (Serper, GooglePlaces).
- [ ] Deduplication works (Accepted < Candidates).
- [ ] Structured report shows metrics per connector.

### Phase B (Intelligence)
- [ ] Selection logic correctly distinguishes between category searches (broad) and specific place searches (high-precision).
- [ ] Domain-specific connectors (e.g., SportScotland) are automatically included for relevant queries.

### Phase C (Production)
- [ ] All 6 connectors are available in the registry.
- [ ] Budget limits effectively trigger early stopping.
- [ ] `--persist` flag successfully saves entities to the database.

## 5. Out of Scope
- Migrating the Orchestrator kernel itself to be fully asynchronous (will use `asyncio.run` bridge for now).
- Machine learning-based connector selection (rules-based is sufficient).