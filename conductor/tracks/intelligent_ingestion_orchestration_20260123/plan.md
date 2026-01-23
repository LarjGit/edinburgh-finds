# Implementation Plan - Intelligent Ingestion Orchestration

## Phase 1: Core Types, Features & Safe DSL (TDD)
Establish the immutable core types, the features extraction module, and the safe Condition DSL. This phase ensures the foundation is type-safe and handles edge cases (like `None` values) correctly.

- [x] Task: Core Types Implementation [f1959cc]
    - [x] Create `engine/orchestration/types.py` with `IngestRequest`, `IngestionMode`, `BoundingBox`, `GeoPoint`.
    - [x] Add unit tests for immutability and default value handling.
- [ ] Task: Query Features Module
    - [ ] Create `engine/orchestration/query_features.py` with `QueryFeatures` dataclass and a deterministic factory method `extract(query, request)`.
    - [ ] Write unit tests to verify deterministic feature extraction.
- [ ] Task: Condition DSL Implementation
    - [ ] Create `engine/orchestration/conditions.py` with `Condition`, `CompositeCondition`, `Operator`.
    - [ ] Implement `evaluate` method with `None`-safe logic for all operators (especially `CONTAINS`, `INTERSECTS`).
    - [ ] Implement concrete helper `build_eval_context(request, query_features, execution_context)`.
    - [ ] Implement `ConditionParser` for dict/YAML parsing.
    - [ ] Write comprehensive tests for DSL evaluation (including nested paths, missing keys, `None` values) and context builder assertions.
- [ ] Task: Conductor - User Manual Verification 'Core Types, Features & Safe DSL' (Protocol in workflow.md)

## Phase 2: Execution Context & Deduplication (TDD)
Implement the shared state container and the robust, deterministic deduplication logic.

- [ ] Task: Execution Context Structure
    - [ ] Create `engine/orchestration/execution_context.py` with `ExecutionContext` class.
    - [ ] Implement storage for `candidates`, `accepted_entities`, `accepted_entity_keys` (Set[str]), `evidence`, `seeds`.
- [ ] Task: Deterministic Deduplication Logic
    - [ ] Implement `_generate_entity_key` with the 3-tier strategy (Strong IDs -> Geo -> Stable SHA1).
    - [ ] Implement `accept_entity` with side-effects, explicit return type, and duplicate detection.
    - [ ] Write tests verifying:
        - Stable hashing (same input = same hash).
        - Geo rounding and `0.0` handling.
        - Priority order of key generation.
        - Duplicate candidates return correct tuple and maintain stable counts.
- [ ] Task: Conductor - User Manual Verification 'Execution Context & Deduplication' (Protocol in workflow.md)

## Phase 3: Execution Plan & Phase Barriers (TDD)
Build the DAG-lite structure and the logic for phase-based execution and aggregate gating.

- [ ] Task: Connector Node & Plan Structure
    - [ ] Create `engine/orchestration/execution_plan.py` with `ConnectorNode` and `ExecutionPlan`.
    - [ ] Implement `add_connector` with dependency inference (only `context.*` keys).
- [ ] Task: Provider Selection & Tie-Breaking
    - [ ] Implement `_get_best_provider` using `(-trust_level, phase_order)` logic.
    - [ ] Write tests ensuring correct provider is selected in tie-break scenarios.
- [ ] Task: Aggregate Gating Logic
    - [ ] Implement `should_run_connector` with the specific skipping logic defined in spec.
    - [ ] Write tests for gating: ensure connectors skip/run correctly based on context availability and `supports_query_only`.
- [ ] Task: Conductor - User Manual Verification 'Execution Plan & Phase Barriers' (Protocol in workflow.md)

## Phase 4: Orchestrator & Integration (TDD)
Implement the main control loop that enforces the phase barriers, manages parallelism, and handles early stopping.

- [ ] Task: Orchestrator Core Loop & Fake Connector
    - [ ] Create `engine/orchestration/orchestrator.py` with `Orchestrator` class.
    - [ ] Implement `execute` method enforcing `DISCOVERY` -> `STRUCTURED` -> `ENRICHMENT` order.
    - [ ] Define `FakeConnector` interface for deterministic testing.
- [ ] Task: Parallel Execution & Deterministic Merging
    - [ ] Implement `_execute_phase` with parallel execution support.
    - [ ] Implement deterministic result merging (sort by connector name; scalar collision policy: trust > last writer).
    - [ ] Write unit tests for scalar collision to prove determinism.
- [ ] Task: Early Stopping & Budgeting
    - [ ] Add checks for `budget_usd` (pre/post) and `target_entity_count`/`min_confidence`.
    - [ ] Write integration tests using `FakeConnector` to simulate full runs and verify stopping conditions.
- [ ] Task: Conductor - User Manual Verification 'Orchestrator & Integration' (Protocol in workflow.md)

## Phase 5: Final Verification
Ensure full spec compliance.

- [ ] Task: Spec Compliance Audit
    - [ ] Map each major spec requirement to implementation file/test.
    - [ ] Verify all tests pass and coverage > 80%.
