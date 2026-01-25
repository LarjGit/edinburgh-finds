# Subsystem: engine-orchestration

## Purpose
The `engine-orchestration` subsystem implements the **Intelligent Ingestion Orchestration** logic. It coordinates the execution of multiple data connectors through a multi-phase pipeline, ensuring data quality via trust-based conflict resolution and optimizing resource usage through early stopping conditions.

## Key Components

### Orchestration Control
- **Orchestrator (orchestrator.py)**: The main control loop that executes connectors in strict phase order. It manages the `ExecutionContext`, enforces phase barriers, and handles scalar field conflict resolution using a trust-based "higher trust wins" strategy.
- **ExecutionPlan (execution_plan.py)**: Manages connectors as a dependency-aware graph (DAG-lite). It automatically infers dependencies based on `context.*` keys and selects the best providers for required data using trust levels and phase order.
- **ExecutionContext (execution_context.py)**: A shared, mutable container for state during an ingestion run. It tracks discovered candidates, accepted entities, evidence, and budget spent. It also implements a 3-tier deduplication strategy (IDs -> Geo-based -> Hash).

### Logic & Features
- **Condition DSL (conditions.py)**: A None-safe Domain Specific Language for evaluating complex conditions against the request, extracted query features, and current execution context. It supports boolean logic and nested path resolution.
- **QueryFeatures (query_features.py)**: Extracts deterministic boolean signals from query strings (e.g., `looks_like_category_search`, `has_geo_intent`) to guide orchestration decisions.
- **Types (types.py)**: Defines foundational immutable types like `IngestRequest`, `IngestionMode` (`RESOLVE_ONE` vs. `DISCOVER_MANY`), and geographic primitives.

## Architecture

### 3-Phase Sequential Pipeline
The orchestrator enforces a strict phase-based execution barrier:
1. **DISCOVERY**: Initial data gathering (e.g., search results).
2. **STRUCTURED**: High-quality structured data sources (e.g., official APIs).
3. **ENRICHMENT**: Additional details and refinement (e.g., website scraping).

### Dependency Inference & Gating
Connectors declare what they `require` and `provide`. The `ExecutionPlan` matches these at runtime. Connectors are "gated" and may be skipped if their required context is empty and they don't support query-only execution.

### Conflict Resolution
When multiple connectors in the same phase update the same scalar field:
- **Higher Trust Level**: The value from the more trusted connector is preserved.
- **Deterministic Tie-breaking**: If trust levels are equal, the alphabetically later connector name wins.
- **Lists/Dicts**: Collections are typically merged or appended rather than replaced.

### Early Stopping
Execution can terminate early if:
- **Budget Exhausted**: The estimated cost of the next phase or connector exceeds the remaining budget.
- **Goal Reached**: In `RESOLVE_ONE` mode, stops if high confidence is achieved. In `DISCOVER_MANY` mode, stops if the target entity count is reached.

## Dependencies
### Internal
- **engine-ingestion**: Connectors managed by the orchestrator are implementations of ingestion connectors.
- **engine-core**: Uses core logging and configuration utilities.

## Evidence
- `engine/orchestration/orchestrator.py`: Implementation of phase ordering and trust-based merging.
- `engine/orchestration/execution_plan.py`: Dependency inference and provider selection logic.
- `engine/orchestration/execution_context.py`: 3-tier deduplication strategy and state management.
- `engine/orchestration/conditions.py`: None-safe evaluation of orchestration conditions.
- `engine/orchestration/query_features.py`: Rule-based query signal extraction.
- `engine/orchestration/types.py`: Definitions of `IngestionMode` and `IngestRequest`.
