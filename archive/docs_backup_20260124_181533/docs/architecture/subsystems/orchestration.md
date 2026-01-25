Audience: Developers

# Orchestration Subsystem

The Orchestration subsystem manages the "Intelligent Ingestion Orchestration" (IIO) control loop. It coordinates various data connectors across sequential phases, enforces execution barriers, manages shared state, and handles early stopping based on confidence and budget thresholds.

## Overview

The subsystem is designed to provide a deterministic and controllable pipeline for data ingestion. It uses a phase-based approach (DISCOVERY, STRUCTURED, ENRICHMENT) to ensure that data flows from broad discovery to high-specificity enrichment in a logical order.

## Components

- **Orchestrator**: The central controller that executes the ingestion plan. It manages the transitions between phases and enforces deterministic merging of results from different connectors.
  - Evidence: `engine/orchestration/orchestrator.py:90-111`
- **ExecutionPlan**: A directed graph (DAG-lite) representation of the connectors to be executed. It automatically infers dependencies between connectors based on their required and provided context keys.
  - Evidence: `engine/orchestration/execution_plan.py:91-110`
- **ExecutionContext**: A shared, mutable state container passed through the orchestration loop. It stores candidates, accepted entities, evidence, and seeds.
  - Evidence: `engine/orchestration/execution_context.py:22-48`
- **Condition DSL**: A safe, None-tolerant expression language used to gate connector execution and define early stopping rules.
  - Evidence: `engine/orchestration/conditions.py:73-86`
- **QueryFeatures**: A set of boolean signals extracted from the user's query (e.g., whether it looks like a category search) that guide the orchestrator's decisions.
  - Evidence: `engine/orchestration/query_features.py:22-38`
- **Foundational Types**: Immutable definitions for `IngestRequest`, `IngestionMode`, `GeoPoint`, and `BoundingBox`.
  - Evidence: `engine/orchestration/types.py:1-88`

## Data Flow

1.  **Extraction**: `QueryFeatures` are extracted from the input query string.
2.  **Initialization**: An `ExecutionContext` is initialized to hold the run's state.
3.  **Phase Execution**: The `Orchestrator` iterates through `DISCOVERY`, `STRUCTURED`, and `ENRICHMENT` phases.
4.  **Connector Selection**: In each phase, the orchestrator filters the `ExecutionPlan` for relevant connectors.
5.  **Gating**: Each connector is evaluated against its `Condition` (if any) and current `ExecutionContext` state to decide if it should run.
6.  **Execution & Merging**: Connectors execute, and their results are merged into the `ExecutionContext`. Scalar fields are merged using trust-based resolution.
7.  **Early Stopping**: After each phase (and before starting the next), the orchestrator evaluates stopping conditions like budget exhaustion or reaching confidence targets.
8.  **Completion**: The final `ExecutionContext` containing accepted entities and metadata is returned.

## Configuration Surface

- **IngestionMode**: Controls the stopping strategy.
  - `RESOLVE_ONE`: Stop once a single high-confidence entity is found.
  - `DISCOVER_MANY`: Continue until a target entity count is reached or the budget is spent.
  - Evidence: `engine/orchestration/types.py:24-33`
- **ConnectorSpec**: Defines how a connector fits into the system.
  - `trust_level`: Used for conflict resolution (higher wins).
  - `phase`: One of DISCOVERY, STRUCTURED, ENRICHMENT.
  - `requires`/`provides`: Context keys used for dependency inference.
  - Evidence: `engine/orchestration/execution_plan.py:44-77`

## Public Interfaces

- `Orchestrator.execute(request: IngestRequest, query_features: QueryFeatures) -> ExecutionContext`: Runs the full orchestration loop.
- `ExecutionPlan.add_connector(spec: ConnectorSpec)`: Adds a connector and infers its dependencies.
- `ExecutionContext.accept_entity(candidate: Dict) -> Tuple[bool, str, Optional[str]]`: Evaluates a candidate for deduplication and acceptance.
- `ConditionParser.parse(spec: Dict) -> Condition`: Creates an executable condition from a dictionary specification.

## Examples

### Creating an Ingest Request
```python
# Evidence: engine/orchestration/types.py:72-88
from engine.orchestration.types import IngestRequest, IngestionMode

request = IngestRequest(
    ingestion_mode=IngestionMode.RESOLVE_ONE,
    target_entity_count=1,
    min_confidence=0.8,
    budget_usd=0.50
)
```

### Defining a Connector Specification
```python
# Evidence: engine/orchestration/execution_plan.py:44-77
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase

spec = ConnectorSpec(
    name="google_places",
    phase=ExecutionPhase.STRUCTURED,
    trust_level=80,
    requires=["request.query"],
    provides=["context.candidates"],
    supports_query_only=True,
    estimated_cost_usd=0.02
)
```

## Edge Cases / Notes

- **Deterministic Execution**: Within a single phase, connectors are executed in alphabetical order by their name. This ensures that even with identical trust levels, the outcome is consistent across runs.
  - Evidence: `engine/orchestration/orchestrator.py:207-209`
- **Trust-Based Scalar Merging**: When multiple connectors attempt to write to the same scalar field in the context, the value from the connector with the highest `trust_level` is preserved. In case of a trust tie, the last writer (alphabetically) wins.
  - Evidence: `engine/orchestration/orchestrator.py:246-271`
- **None-Safe Evaluations**: The Condition DSL is designed to handle missing context paths or `None` values gracefully, returning `False` for comparisons rather than raising exceptions.
  - Evidence: `engine/orchestration/conditions.py:126-140`
- **Deduplication Strategy**: Entities are deduplicated using a 3-tier key generation strategy: specific provider IDs, geo-spatial proximity (normalized name + rounded coordinates), and finally a full-object hash.
  - Evidence: `engine/orchestration/execution_context.py:102-149`
