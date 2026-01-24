# Implementation Plan - Intelligent Ingestion Orchestration

## Phase 1: Core Types, Features & Safe DSL (TDD) [checkpoint: c17ba8d]
Establish the immutable core types, the features extraction module, and the safe Condition DSL. This phase ensures the foundation is type-safe and handles edge cases (like `None` values) correctly.

- [x] Task: Core Types Implementation [f1959cc]
    - [x] Create `engine/orchestration/types.py` with `IngestRequest`, `IngestionMode`, `BoundingBox`, `GeoPoint`.
    - [x] Add unit tests for immutability and default value handling.
- [x] Task: Query Features Module [8d106f0]
    - [x] Create `engine/orchestration/query_features.py` with `QueryFeatures` dataclass and a deterministic factory method `extract(query, request)`.
    - [x] Write unit tests to verify deterministic feature extraction.
- [x] Task: Condition DSL Implementation [396aa40]
    - [x] Create `engine/orchestration/conditions.py` with `Condition`, `CompositeCondition`, `Operator`.
    - [x] Implement `evaluate` method with `None`-safe logic for all operators (especially `CONTAINS`, `INTERSECTS`).
    - [x] Implement concrete helper `build_eval_context(request, query_features, execution_context)`.
    - [x] Implement `ConditionParser` for dict/YAML parsing.
    - [x] Write comprehensive tests for DSL evaluation (including nested paths, missing keys, `None` values) and context builder assertions.
- [x] Task: Conductor - User Manual Verification 'Core Types, Features & Safe DSL' (Protocol in workflow.md)

## Phase 2: Execution Context & Deduplication (TDD) [checkpoint: ac2f752]
Implement the shared state container and the robust, deterministic deduplication logic.

- [x] Task: Execution Context Structure [3d00d9f]
    - [x] Create `engine/orchestration/execution_context.py` with `ExecutionContext` class.
    - [x] Implement storage for `candidates`, `accepted_entities`, `accepted_entity_keys` (Set[str]), `evidence`, `seeds`.
- [x] Task: Deterministic Deduplication Logic [703e75f]
    - [x] Implement `_generate_entity_key` with the 3-tier strategy (Strong IDs -> Geo -> Stable SHA1).
    - [x] Implement `accept_entity` with side-effects, explicit return type, and duplicate detection.
    - [x] Write tests verifying:
        - Stable hashing (same input = same hash).
        - Geo rounding and `0.0` handling.
        - Priority order of key generation.
        - Duplicate candidates return correct tuple and maintain stable counts.
- [x] Task: Conductor - User Manual Verification 'Execution Context & Deduplication' (Protocol in workflow.md)

## Phase 3: Execution Plan & Phase Barriers (TDD) [checkpoint: 8f4c0f0]
Build the DAG-lite structure and the logic for phase-based execution and aggregate gating.

- [x] Task: Connector Node & Plan Structure [b3f2e5b]
    - [x] Create `engine/orchestration/execution_plan.py` with `ConnectorNode` and `ExecutionPlan`.
    - [x] Implement `add_connector` with dependency inference (only `context.*` keys).
- [x] Task: Provider Selection & Tie-Breaking [fa68946]
    - [x] Implement `_get_best_provider` using `(-trust_level, phase_order)` logic.
    - [x] Write tests ensuring correct provider is selected in tie-break scenarios.
- [x] Task: Aggregate Gating Logic [e5917b1]
    - [x] Implement `should_run_connector` with the specific skipping logic defined in spec.
    - [x] Write tests for gating: ensure connectors skip/run correctly based on context availability and `supports_query_only`.
- [x] Task: Conductor - User Manual Verification 'Execution Plan & Phase Barriers' (Protocol in workflow.md)

## Phase 4: Orchestrator & Integration (TDD)
Implement the main control loop that enforces the phase barriers, manages parallelism, and handles early stopping.

- [x] Task: Orchestrator Core Loop & Fake Connector [95e5ec7]
    - [x] Create `engine/orchestration/orchestrator.py` with `Orchestrator` class.
    - [x] Implement `execute` method enforcing `DISCOVERY` -> `STRUCTURED` -> `ENRICHMENT` order.
    - [x] Define `FakeConnector` interface for deterministic testing.
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
