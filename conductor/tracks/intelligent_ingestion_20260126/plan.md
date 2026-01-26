# Implementation Plan: Intelligent Ingestion Orchestration

This plan implements the integration layer for the orchestration kernel across three phases as defined in the specification.

## Phase 1: Foundation & Plumbing (Phase A) [checkpoint: 7cf6a41]
Build the core infrastructure to run orchestrated queries through a CLI.

- [x] **Task: Modify Core Types** `5e6ef27`
    - [x] Update `ExecutionContext` in `engine/orchestration/execution_context.py` to include `metrics` and `errors`.
    - [x] Update `IngestRequest` in `engine/orchestration/types.py` to include the `query` field.
- [x] **Task: Implement Registry** `23caad3`
    - [x] Create `engine/orchestration/registry.py` with `ConnectorSpec` entries for `serper` and `google_places`.
    - [x] Implement `get_connector_instance` factory.
- [x] **Task: Build Adapter Layer** `618389a`
    - [x] Create `engine/orchestration/adapters.py` with `ConnectorAdapter`.
    - [x] Implement `asyncio.run` bridge for `BaseConnector.fetch`.
    - [x] Implement canonical mapping for `Serper` and `GooglePlaces`.
    - [x] Implement JSON normalization for the `raw` payload.
- [x] **Task: Create Planner & CLI** `a04b69a`
    - [x] Create `engine/orchestration/planner.py` with `orchestrate()` and hardcoded `select_connectors()`.
    - [x] Create `engine/orchestration/cli.py` with `run` command and basic report formatting.
- [x] **Task: Write Tests (Foundation)** `5928836`
    - [x] Implement `tests/engine/orchestration/test_adapters.py`.
    - [x] Implement `tests/engine/orchestration/test_registry.py`.
- [x] **Task: Fix Google Places API v1 Compatibility** `2dc971e`
    - [x] Update adapter to recognize "places" key from new API.
    - [x] Update field mapping for displayName, id, location format.
    - [x] Add backward compatibility for both API versions.
    - [x] Add tests for new API format (87 tests total).
- [x] **Task: Conductor - User Manual Verification 'Phase 1: Foundation' (Protocol in workflow.md)** `7cf6a41`

## Phase 2: Intelligence & Expanded Connectivity (Phase B)
Implement query-aware selection and integrate more connectors.

- [ ] **Task: Enhance Registry**
    - [ ] Add `openstreetmap` and `sport_scotland` to the registry.
    - [ ] Update adapter mapping for new connectors.
- [ ] **Task: Implement Selection Intelligence**
    - [ ] Update `select_connectors()` in `planner.py` to use `QueryFeatures`.
    - [ ] Implement rules for category vs. specific place detection.
    - [ ] Implement domain-specific routing (e.g., sports).
- [ ] **Task: Write Tests (Intelligence)**
    - [ ] Implement `tests/engine/orchestration/test_planner.py` for selection logic.
    - [ ] Add integration tests in `tests/engine/orchestration/test_integration.py`.
- [ ] **Task: Conductor - User Manual Verification 'Phase 2: Intelligence' (Protocol in workflow.md)**

## Phase 3: Production Readiness & Persistence (Phase C)
Complete the inventory and wire up database persistence.

- [ ] **Task: Finalize Registry & Budgeting**
    - [ ] Add `edinburgh_council` and `open_charge_map` to the registry.
    - [ ] Update `select_connectors()` with budget-aware gating logic.
- [ ] **Task: Implement Persistence Mode**
    - [ ] Add `--persist` flag to CLI.
    - [ ] Integrate with existing extractors/ingestors to save accepted entities to the DB.
- [ ] **Task: Polish & Smoke Test**
    - [ ] Finalize CLI report formatting (colors, tables).
    - [ ] Create `scripts/test_orchestration_live.py` for real-world verification.
- [ ] **Task: Conductor - User Manual Verification 'Phase 3: Production' (Protocol in workflow.md)**