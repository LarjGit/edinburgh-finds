# Specification: Intelligent Ingestion Orchestration (v6)

## Overview
Implement the **Intelligent Ingestion Orchestration - Architecture v6** to provide a runtime-safe, phase-ordered, and intelligent control plane for the data ingestion engine. This architecture replaces ad-hoc script execution with a formal `Orchestrator` that enforces dependency management, phase barriers, and resource optimization.

## Functional Requirements

### 1. Core Types (Immutable)
- Implement `IngestRequest` as a frozen dataclass (Immutable).
    - **FR1:** MUST include:
        - `ingestion_mode`: Enum (`RESOLVE_ONE`, `DISCOVER_MANY`).
        - `target_entity_count`: Optional[int]. **Clarification:** Defaults are resolved by configuration at orchestration startup, not embedded in engine code.
        - `min_confidence`: Optional[float]. **Clarification:** Defaults are resolved by configuration at orchestration startup, not embedded in engine code.
- **FR1 (New):** Implement `QueryFeatures` dataclass in a dedicated module (`engine/orchestration/query_features.py`).
    - The Engine computes this **once** per request via a deterministic factory method (e.g., `QueryFeatures.extract(query, request)`).
    - Provided to the Orchestrator for condition evaluation (accessible via `query_features.*`).
    - Contains boolean signals (e.g., `looks_like_category_search`, `has_geo_intent`).
- Implement `BoundingBox` and `GeoPoint` value objects.

### 2. Condition DSL (Safe Operations)
- Implement `Condition` and `CompositeCondition` classes.
- **FR2:** Evaluation context is fixed to include:
    - `request.*`
    - `query_features.*`
    - `context.*` (Access to `ExecutionContext`)
    - Precomputed booleans (e.g., `has_geo_constraint`, `is_resolve_one`).
- **FR2 (Helper):** Implement a concrete helper `build_eval_context(request, query_features, execution_context)` which MUST be the only way to construct the context.
- **Safety:** Missing paths MUST return `None`. All operators (including `CONTAINS`, `INTERSECTS`) MUST be `None`-safe (returning `False` instead of crashing).

### 3. Execution Context (Stable Deduplication)
- Implement `ExecutionContext` to hold shared state (`candidates`, `accepted_entities`, `accepted_entity_keys`, `evidence`, `seeds`).
- **FR3:** Implement `accept_entity(candidate) -> Tuple[bool, str, Optional[str]]`:
    - **Name Normalization:** Explicitly defined as: `value.casefold().strip()`, with whitespace collapsed to single spaces. Optional punctuation removal based on strictness config.
    - **Key Generation Strategy:**
        1.  **Strong IDs:** Check `candidate.ids` or `context.seeds`. Precedence is defined by `lens_config.strong_id_precedence`. If absent, fall back to lexicographic key order (e.g., sort keys alphabetically).
        2.  **Geo Fallback:** `normalized_name` + `rounded_lat`/`rounded_lng` (precision: 4 decimal places). **CRITICAL:** Explicitly check `lat/lng is not None` (accept `0.0`).
        3.  **Stable Hash (Final Fallback):** Calculate SHA1 hash over a canonical subset of candidate fields. **Determinism:** Sort keys alphabetically, normalize values, serialize to JSON/string, then hash. **NEVER** use Python's built-in `hash()`.
    - **Side Effects:** Explicitly updates internal `accepted_entities` list and `accepted_entity_keys` set if accepted.
    - **Deduplication:** Duplicate candidates return `(False, same_key, reason="duplicate")`. `accepted_entities` count remains stable.

### 4. Execution Plan (Phase Barriers & Contracts)
- Implement `ConnectorNode` and `ExecutionPlan` (DAG-lite).
- **FR4:** `ConnectorSpec` includes `supports_query_only` (bool).
- **FR4:** Provider selection tie-breaking: `(-trust_level, phase_order)`. Smaller `phase_order` wins ties.
- **FR4:** Parallel Context Merging:
    - Updates from parallel connectors MUST be committed in a deterministic order (e.g., sorted by connector name).
    - **Conflict Resolution:** 
        - List fields → Append.
        - Dict fields → Merge by key.
        - Scalar fields → Higher trust wins. If trust equal, last writer wins based on deterministic connector ordering.
- **Aggregate Gating:** `should_run_connector` logic:
    - Mechanically testable: A connector is "context-dependent" IFF `ConnectorSpec.requires` contains any `context.*` keys.
    - Skip connector IF:
        - It is context-dependent AND
        - `candidates` AND `accepted_entities` are empty AND
        - The specific required `context` keys (e.g., seeds) are missing AND
        - `supports_query_only` is False.
- **Confidence Contract:** Orchestrator reads a float [0..1] computed by a pluggable `ConfidenceCalculator` from context evidence/seeds + source metadata.

### 5. Orchestrator (Phase-Ordered Execution)
- Implement `Orchestrator` class.
- **Phase Barriers:** Enforce strict sequential execution: `DISCOVERY` → `STRUCTURED` → `ENRICHMENT`.
- **Parallelism:** Support parallel execution *within* a phase.
- **FR5:** Early Stopping Logic:
    - **RESOLVE_ONE:** Stop when `confidence >= min_confidence` AND at least one entity is accepted.
    - **DISCOVER_MANY:** Stop when `len(accepted_entities) >= target_entity_count`.
    - **Budget:** Check budget usage **pre-schedule** and **post-completion**.

## Non-Functional Requirements
- **Type Safety:** Strict type hints. Pydantic validation used **only** for parsing `ConnectorSpec` and configuration files (not for runtime `IngestRequest` or `ExecutionContext` objects).
- **Test Coverage:** >80% coverage.
    - **Specific Targets:** Condition DSL edge cases (`None` values), Deduplication stability (hashing), Aggregate Gating logic, and Deterministic Merging.
- **Determinism:** Execution must be reproducible.

## Out of Scope
- Implementation of specific Connectors.
- API Exposure.
