# Orchestration Integration Specification - Clean Slate

**Version**: Final
**Date**: 2026-01-26
**Purpose**: Enable intelligent, CLI-driven entity ingestion using the existing orchestration kernel

---

## 1. Product Vision

**Core Goal**: A user can run `orchestrate "Powerleague Portobello"` from the CLI, and the system intelligently selects appropriate connectors, executes them through the orchestration kernel, deduplicates results, and produces high-quality entities.

**Key Requirements**:
- Free-text query input (no manual connector specification)
- Intelligent connector selection based on query characteristics
- Observable execution (see what's happening, debug failures)
- Quality output (deduplication works, trust-based conflict resolution)
- Cost-aware (budget limits, early stopping)

---

## 2. What Already Exists (Orchestration Kernel)

The following components are **implemented and correct** in `engine/orchestration/`:

### Orchestration Control Flow
- **`Orchestrator`** - Main control loop, phase barriers, early stopping
  - Enforces DISCOVERY → STRUCTURED → ENRICHMENT phase order
  - Budget tracking, confidence-based stopping
  - Scalar conflict resolution (trust-level based)

### Execution Planning
- **`ExecutionPlan`** - DAG-lite connector scheduling
  - Groups connectors by phase
  - Dependency inference from context.* keys
  - Provider selection with tie-breaking

- **`ConnectorSpec`** - Connector metadata
  - `name`, `phase`, `trust_level`
  - `requires`, `provides` (dependency keys)
  - `supports_query_only`, `estimated_cost_usd`

### Shared State
- **`ExecutionContext`** - Mutable state container
  - `candidates`, `accepted_entities` (with deduplication)
  - 3-tier dedupe: strong IDs → geo-based → content hash
  - `evidence`, `seeds`, `budget_spent_usd`, `confidence`

### Query Analysis
- **`QueryFeatures`** - Extracts query characteristics
  - `looks_like_category_search` vs specific entity
  - `has_geo_intent`, `sport_type`, `facility_type`
  - Used for connector selection decisions

### Request Types
- **`IngestRequest`** - Immutable request object
  - `ingestion_mode` (RESOLVE_ONE, DISCOVER_MANY)
  - `target_entity_count`, `min_confidence`, `budget_usd`
  - **Missing**: `query` field (needs to be added)

### Production Connectors
Six connectors exist in `engine/ingestion/connectors/`:
- `SerperConnector` (Google search results)
- `GooglePlacesConnector` (high-trust place data)
- `OpenStreetMapConnector` (community geo data)
- `SportScotlandConnector`, `EdinburghCouncilConnector`, `OpenChargeMapConnector`

All inherit from `BaseConnector` with signature: `async def fetch(query: str) -> dict`

---

## 3. What's Missing (Integration Layer)

### A. No CLI Entry Point
**Problem**: No command to invoke orchestrated ingestion
**Need**: `python -m engine.orchestration.cli run "query"` that triggers the entire flow

### B. No Connector Selection Logic
**Problem**: Orchestration kernel doesn't know which connectors to run for a given query
**Need**: Decision layer that analyzes query and builds appropriate ExecutionPlan

### C. No Adapter Layer
**Problem**: Connectors have `async def fetch(query)`, orchestrator expects `execute(request, query_features, context)`
**Need**: Adapter that bridges connector interface to orchestrator interface

### D. No Connector Registry
**Problem**: No central place mapping connector names to specs and instances
**Need**: Registry with `ConnectorSpec` metadata and factory for instantiation

### E. No Planner/Factory
**Problem**: No module that wires registry + adapter + selection logic + orchestrator
**Need**: Planner that builds configured Orchestrator ready to execute

### F. Observability Gaps
**Problem**: ExecutionContext doesn't track metrics or errors per connector
**Need**: Add `metrics` and `errors` fields to ExecutionContext for reporting

---

## 4. Architecture Design

### Component Layering

```
┌─────────────────────────────────────────────────────────────┐
│  CLI (engine/orchestration/cli.py)                          │
│  - Parse arguments (query, mode, budget, flags)             │
│  - Invoke planner.orchestrate()                             │
│  - Format and display execution report                      │
│  - NO selection logic, NO adapter logic                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Planner (engine/orchestration/planner.py)                  │
│  - orchestrate(query, mode, budget) → ExecutionReport       │
│  - select_connectors(query, mode) → List[ConnectorSpec]     │
│  - build_plan(specs) → ExecutionPlan                        │
│  - build_orchestrator(plan, budget) → Orchestrator          │
│  INTELLIGENCE LIVES HERE (connector selection decisions)    │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│  Registry                │  │  Adapter                     │
│  (registry.py)           │  │  (adapters.py)               │
│  - CONNECTOR_SPECS       │  │  - Wrap BaseConnector        │
│  - get_instance(name)    │  │  - async→sync bridge         │
│  METADATA LIVES HERE     │  │  - Map results to canonical  │
└──────────────────────────┘  └──────────────────────────────┘
              │                           │
              └─────────────┬─────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Orchestrator (orchestrator.py) - EXISTING, UNTOUCHED       │
│  - Execute connectors in phase order                        │
│  - Enforce barriers, track budget, deduplicate              │
└─────────────────────────────────────────────────────────────┘
```

### Responsibility Matrix

| Component | Selection | Adaptation | Execution | CLI I/O |
|-----------|-----------|------------|-----------|---------|
| **CLI** | ❌ | ❌ | ❌ | ✅ |
| **Planner** | ✅ | ❌ | Orchestrates | ❌ |
| **Registry** | ❌ | ❌ | ❌ | ❌ |
| **Adapter** | ❌ | ✅ | ❌ | ❌ |
| **Orchestrator** | ❌ | ❌ | ✅ | ❌ |

### Key Architectural Principles

1. **Single Responsibility**: Each component has one clear job
2. **Intelligence Isolation**: All selection logic in Planner (easy to evolve)
3. **Thin Boundaries**: CLI and Adapter are thin translation layers
4. **Immutable Kernel**: Orchestrator remains untouched (proven correct)
5. **Observable Execution**: Every step produces trackable metrics

---

## 5. Phased Capability Rollout

### Phase A: End-to-End Proof (Hardcoded Selection)

**Capability Unlocked**: "I can type a query and see real connectors execute through orchestration with deduplication"

**Selection Strategy**: Hardcoded list (always run serper + google_places)

**Why This First**:
- Validates integration plumbing works
- Proves orchestration kernel handles real data
- Demonstrates deduplication with actual API responses
- Provides observable output to debug issues

**What Gets Built**:
- Registry with 2 connector specs (serper, google_places)
- Adapter that wraps BaseConnector → Orchestrator interface
- Planner with hardcoded `select_connectors()` returning fixed list
- CLI with `run` command
- ExecutionReport formatter for dry-run output

**Exit Criteria**:
- ✅ CLI command executes without errors
- ✅ Both connectors make real API calls
- ✅ Deduplication reduces candidate count (accepted < candidates)
- ✅ Phase ordering visible (DISCOVERY → STRUCTURED)
- ✅ Structured report shows metrics per connector

---

### Phase B: Query-Aware Selection (Basic Intelligence)

**Capability Unlocked**: "Different queries trigger different connector combinations based on query characteristics"

**Selection Strategy**: Simple rules using QueryFeatures
- Category search ("padel courts") → serper + google_places + osm
- Specific place ("Powerleague Portobello") → google_places only
- Sports query → add sport_scotland

**Why This Second**:
- Demonstrates decision layer works
- Proves intelligence is pluggable (just swap selection logic)
- Validates QueryFeatures integration
- Shows value of orchestration (different queries, different strategies)

**What Gets Built**:
- Update Planner `select_connectors()` with QueryFeatures-based rules
- Add openstreetmap, sport_scotland to registry (4 connectors total)
- Add corresponding adapters for new connectors

**Exit Criteria**:
- ✅ Category queries include serper
- ✅ Specific place queries skip serper (efficiency)
- ✅ Sports queries include sport_scotland
- ✅ Selection logic is clear and testable

---

### Phase C: Production-Ready (Full Inventory + Budget)

**Capability Unlocked**: "Production system with all connectors, cost controls, and persistent storage"

**Selection Strategy**: Full rule set + budget-aware gating
- All 6 connectors available
- Budget limits enforced (early stopping works)
- Connector gating based on previous phase results

**Why This Last**:
- Full connector inventory
- Budget enforcement tested (orchestrator already supports this)
- Persistence integration (save to DB via extractors)
- Production-grade error handling

**What Gets Built**:
- Add remaining connectors to registry (6 total)
- Wire budget enforcement in CLI (already implemented in Orchestrator)
- Add persistence mode (invoke extractors → ingest_entity)
- Production error reporting

**Exit Criteria**:
- ✅ All 6 connectors selectable
- ✅ Budget limits work (early stopping observable)
- ✅ Entities persist to database (not just dry-run)
- ✅ Production-ready observability

---

## 6. CLI Experience

### Command Structure

```bash
# Basic usage (dry-run by default)
orchestrate "Powerleague Portobello"

# With mode selection
orchestrate "padel courts edinburgh" --mode=discover-many

# With budget limit
orchestrate "climbing gyms" --budget=0.50

# Show plan without executing
orchestrate "sports facilities" --plan-only

# Execute with persistence (Phase C)
orchestrate "query" --persist
```

### Expected Output (Dry-Run)

```
Orchestration Run: "Powerleague Portobello"
Mode: RESOLVE_ONE
═══════════════════════════════════════════════════════════

PLAN
═══════════════════════════════════════════════════════════
Selected Connectors: google_places
Estimated Cost: $0.02
Phase Order: STRUCTURED

═══════════════════════════════════════════════════════════
EXECUTION
═══════════════════════════════════════════════════════════
✓ [STRUCTURED] google_places     12 candidates (340ms, $0.02)

═══════════════════════════════════════════════════════════
RESULTS
═══════════════════════════════════════════════════════════
Total Candidates: 12
Duplicates Removed: 3
Accepted Entities: 9

Top Accepted:
  1. Powerleague Portobello (google_places) [55.9532, -3.1234]
  2. Powerleague Edinburgh West (google_places) [55.9456, -3.2345]
  ...

═══════════════════════════════════════════════════════════
STATUS
═══════════════════════════════════════════════════════════
✓ Execution completed successfully
  Budget consumed: $0.02 / $5.00
```

### Error Scenarios

**Missing API Key**:
```
❌ Configuration error: Google Places API key not configured
   Please set a valid API key in engine/config/sources.yaml
```

**Connector Failure (Non-Fatal)**:
```
⚠️ 1 error occurred:
   - serper: API timeout (network error)

✓ Execution continued with google_places
  Accepted Entities: 8
```

**Budget Exceeded**:
```
✓ Early stopping triggered: budget exhausted ($0.50 / $0.50)
  Accepted Entities: 15
```

---

## 7. Decision-Making Logic (Connector Selection)

### Selection Philosophy

**Phase A**: Hardcoded (prove plumbing)
**Phase B**: Rules-based (prove intelligence layer)
**Phase C**: Budget-aware rules (prove production readiness)

### Phase A: Hardcoded Selection

```python
def select_connectors(query: str, mode: IngestionMode) -> List[str]:
    """Phase A: Always return serper + google_places"""
    return ["serper", "google_places"]
```

**Rationale**: Validates integration, not intelligence

---

### Phase B: Query-Aware Selection

```python
def select_connectors(query: str, mode: IngestionMode) -> List[str]:
    """Phase B: Select based on QueryFeatures"""

    features = QueryFeatures.extract(query, None)
    selected = []

    # Category search: broad discovery
    if features.looks_like_category_search:
        selected.append("serper")
        selected.append("google_places")
        selected.append("openstreetmap")

    # Specific place: high-trust only
    else:
        selected.append("google_places")

    # Sports-specific: add domain connector
    if features.sport_type or features.facility_type:
        selected.append("sport_scotland")

    return selected
```

**Rules**:
1. **Category queries** (e.g., "padel courts") → cast wide net (serper, places, osm)
2. **Specific queries** (e.g., "Powerleague Portobello") → high-trust only (google_places)
3. **Sports queries** → add domain connector (sport_scotland)

**Why These Rules**:
- Category searches benefit from breadth (serper's web scraping)
- Specific places benefit from precision (google_places' strong IDs)
- Domain connectors add specialized coverage

---

### Phase C: Budget-Aware Selection

```python
def select_connectors(query: str, mode: IngestionMode, budget: float) -> List[str]:
    """Phase C: Budget-aware selection"""

    features = QueryFeatures.extract(query, None)
    selected = []
    cost = 0.0

    # High-value connector (always include if affordable)
    if cost + 0.02 <= budget:
        selected.append("google_places")
        cost += 0.02

    # Category search: add breadth if budget allows
    if features.looks_like_category_search:
        if cost + 0.01 <= budget:
            selected.append("serper")
            cost += 0.01
        if cost + 0.00 <= budget:  # OSM is free
            selected.append("openstreetmap")

    # Sports-specific: add if budget allows
    if features.sport_type and cost + 0.05 <= budget:
        selected.append("sport_scotland")
        cost += 0.05

    return selected
```

**Budget Strategy**:
- Prioritize high-trust connectors (google_places first)
- Add breadth connectors only if budget allows
- Free connectors (OSM) always included

---

## 8. Implementation Requirements

### A. Modify Existing Files (2 files, minimal changes)

**1. ExecutionContext** (`engine/orchestration/execution_context.py`)
```python
def __init__(self) -> None:
    # ... existing fields ...
    self.metrics: Dict[str, Any] = {}  # NEW
    self.errors: List[Dict[str, Any]] = []  # NEW
```

**Why**: Adapters need to record per-connector metrics and errors. Current design would require dynamic attribute attachment (messy). Add to `__init__()` like other fields.

**2. IngestRequest** (`engine/orchestration/types.py`)
```python
@dataclass(frozen=True)
class IngestRequest:
    ingestion_mode: IngestionMode
    query: str  # NEW - raw query for connector execution
    target_entity_count: Optional[int] = None
    min_confidence: Optional[float] = None
    budget_usd: Optional[float] = None
```

**Why**: Adapters need the raw query to call `connector.fetch(query)`. Request is the natural place (keeps context together).

---

### B. New Files (4 core + 4 tests + 1 script)

**1. Registry** (`engine/orchestration/registry.py`, ~150 lines)

```python
CONNECTOR_SPECS = {
    "serper": ConnectorSpec(
        name="serper",
        phase=ExecutionPhase.DISCOVERY,
        trust_level=7,
        requires=["request.query"],
        provides=["context.candidates"],
        supports_query_only=True,
        estimated_cost_usd=0.01
    ),
    "google_places": ConnectorSpec(
        name="google_places",
        phase=ExecutionPhase.STRUCTURED,
        trust_level=9,
        requires=["request.query"],
        provides=["context.candidates"],
        supports_query_only=True,
        estimated_cost_usd=0.02
    ),
    # Phase B: add openstreetmap, sport_scotland
    # Phase C: add edinburgh_council, open_charge_map
}

def get_connector_instance(name: str) -> BaseConnector:
    """Factory to instantiate connector by name"""
    connector_classes = {
        "serper": SerperConnector,
        "google_places": GooglePlacesConnector,
        # Phase B/C: add more
    }
    if name not in connector_classes:
        raise ValueError(f"Unknown connector: {name}")
    return connector_classes[name]()
```

**Purpose**: Central metadata + factory. Single source of truth for connector capabilities.

---

**2. Adapter** (`engine/orchestration/adapters.py`, ~200 lines)

```python
class ConnectorAdapter:
    """Adapts BaseConnector (async) to Orchestrator interface (sync)"""

    def __init__(self, connector: BaseConnector, spec: ConnectorSpec):
        self.connector = connector
        self.spec = spec

    def execute(self, request: IngestRequest,
                query_features: QueryFeatures,
                context: ExecutionContext) -> None:
        """Execute connector and write results to context.candidates"""

        # Async→sync bridge (Phase A compromise, CLI-only safe)
        results = asyncio.run(self.connector.fetch(request.query))

        # Map results to canonical schema
        for item in self._extract_items(results):
            candidate = self._map_to_candidate(item)
            context.candidates.append(candidate)

        # Record metrics
        context.metrics[self.spec.name] = {
            "executed": True,
            "candidates_added": len(items),
            "execution_time_ms": elapsed_ms,
            "cost_usd": self.spec.estimated_cost_usd
        }

    def _map_to_candidate(self, raw_item: dict) -> dict:
        """Map connector-specific response to canonical candidate"""
        # Serper: no IDs, no coords in Phase A
        # Google Places: strong IDs, flat lat/lng
        # Schema: {"ids": {"google": "ChIJ..."}, "name": "...",
        #          "lat": 55.9, "lng": -3.1, "source": "...", "raw": {...}}
```

**Purpose**: Interface translation. Handles async bridge, response mapping, error handling.

**Key Decision - Async Bridge**: Use `asyncio.run()` in Phase A (CLI-only safe). If we need async orchestrator later (API endpoints), adapters become `async def execute()` and remove `asyncio.run()` (2-hour migration).

---

**3. Planner** (`engine/orchestration/planner.py`, ~200 lines)

```python
def orchestrate(query: str, mode: IngestionMode, budget_usd: float = 5.0,
                dry_run: bool = True) -> ExecutionReport:
    """
    Main entry point for orchestrated ingestion.

    This is the single public API. CLI calls this.

    Returns ExecutionReport with metrics, results, errors.
    """

    # Build request
    request = IngestRequest(
        query=query,
        ingestion_mode=mode,
        budget_usd=budget_usd
    )

    # Select connectors (intelligence layer)
    connector_names = select_connectors(query, mode)

    # Build execution plan
    plan = build_plan(connector_names)

    # Build configured orchestrator
    orchestrator = build_orchestrator(plan, connector_names)

    # Execute
    query_features = QueryFeatures.extract(query, request)
    context = orchestrator.execute(request, query_features)

    # Build report
    return ExecutionReport(
        query=query,
        mode=mode,
        selected_connectors=connector_names,
        total_candidates=len(context.candidates),
        total_accepted=len(context.accepted_entities),
        metrics=context.metrics,
        errors=context.errors
    )


def select_connectors(query: str, mode: IngestionMode) -> List[str]:
    """
    INTELLIGENCE LIVES HERE

    Phase A: Hardcoded list
    Phase B: QueryFeatures-based rules
    Phase C: Budget-aware rules
    """
    # Phase A implementation
    return ["serper", "google_places"]


def build_orchestrator(plan: ExecutionPlan,
                       connector_names: List[str]) -> Orchestrator:
    """
    Wire adapters and validate no missing connectors.

    Fail fast if connector in plan but not in registry.
    """
    adapted_connectors = {}
    for name in connector_names:
        spec = CONNECTOR_SPECS[name]
        instance = get_connector_instance(name)
        adapter = ConnectorAdapter(instance, spec)
        adapted_connectors[name] = adapter

    # Validate: fail if any connector missing (prevents silent FakeConnector fallback)
    plan_names = set(plan.get_all_connector_names())
    adapted_names = set(adapted_connectors.keys())
    if plan_names != adapted_names:
        raise ValueError(f"Connector mismatch: {plan_names - adapted_names}")

    return Orchestrator(plan=plan, connector_instances=adapted_connectors)
```

**Purpose**: Orchestrates the entire flow. Intelligence layer (selection) lives here.

---

**4. CLI** (`engine/orchestration/cli.py`, ~250 lines)

```python
@click.command()
@click.argument("query")
@click.option("--mode", type=click.Choice(["resolve-one", "discover-many"]),
              default="discover-many")
@click.option("--budget", type=float, default=5.0)
@click.option("--dry-run/--persist", default=True)
@click.option("--plan-only", is_flag=True)
def run(query: str, mode: str, budget: float, dry_run: bool, plan_only: bool):
    """Run orchestrated ingestion"""

    mode_enum = IngestionMode.RESOLVE_ONE if mode == "resolve-one" else IngestionMode.DISCOVER_MANY

    # Plan-only mode
    if plan_only:
        connector_names = select_connectors(query, mode_enum)
        display_plan(query, connector_names)
        return

    # Execute
    report = orchestrate(query, mode_enum, budget, dry_run)

    # Display
    display_report(report)


def display_report(report: ExecutionReport):
    """Format and display structured report"""
    # Show plan, execution, results, status sections
    # See CLI Experience section for format
```

**Purpose**: Thin layer. Parse args, invoke planner, format output. NO business logic.

---

### C. Tests (4 files, ~400 lines total)

1. `test_adapters.py` - Mock API responses, test mapping
2. `test_registry.py` - Validate specs, test factory
3. `test_planner.py` - Test selection logic, validation
4. `test_integration.py` - End-to-end with mocks

**Testing Strategy**: Mock all API calls in automated tests. Real API calls in manual smoke test script only.

---

### D. Manual Smoke Test Script

`scripts/test_orchestration_live.py` - Real API calls for validation

---

## 9. Canonical Candidate Schema

**Critical for Deduplication**: Adapters MUST produce this exact schema.

```python
candidate = {
    # Deduplication Tier 1: Strong IDs (dict, not string)
    "ids": {"google": "ChIJ123..."},  # or None for serper

    # Deduplication Tier 2: Geo-based (FLAT, not nested)
    "lat": 55.9532,  # or None
    "lng": -3.1234,  # or None

    # Core attributes
    "name": "Powerleague Portobello",
    "source": "google_places",

    # Optional
    "address": "123 Portobello Rd",
    "category": "sports_club",
    "confidence": 0.9,

    # Raw payload (for enrichment)
    "raw": {...}  # original API response
}
```

**Deduplication Behavior** (execution_context.py:66-121):
1. **Tier 1**: Strong ID match → skip duplicate
2. **Tier 2**: Geo-based (50m radius, name match) → skip duplicate
3. **Tier 3**: SHA1 content hash → skip duplicate

**Known Quirk**: Tier 1 uses alphabetical key sorting (`sorted(ids.keys())`). Works in Phase A/B (google < osm alphabetically = correct priority by luck). Phase C: If adding apple/facebook IDs, replace with explicit priority list.

---

## 10. Risk Analysis & Pushbacks

### Risk 1: Async Bridge is Phase A Compromise ⚠️

**Issue**: `asyncio.run()` in adapter fails if orchestrator called from async context (e.g., FastAPI endpoint).

**Phase A Decision**: Accept compromise. CLI-only usage is safe.

**Mitigation Path**: If async orchestrator needed (Phase D: API integration):
1. Change `Orchestrator.execute()` → `async def execute()`
2. Change `ConnectorAdapter.execute()` → `async def execute()`
3. Remove `asyncio.run()`, use `await self.connector.fetch()`
4. CLI becomes `asyncio.run(orchestrate())`

**Estimated migration**: 2 hours, low risk (adapters are isolated).

---

### Risk 2: ID Priority is Alphabetical ⚠️

**Issue**: execution_context.py:89 uses `sorted(ids.keys())` for Tier 1 deduplication. Alphabetical order is accidental, not intentional priority.

**Phase A/B Impact**: Low (google < osm alphabetically = correct by luck)

**Phase C Risk**: If adding apple/facebook IDs, priority breaks (apple < google = wrong)

**Recommendation**: Document as "known quirk" in Phase A/B. Phase C: Replace with explicit priority list in `ExecutionContext._generate_entity_key()`.

---

### Risk 3: No Gating Conditions in ConnectorSpec ✅

**Observation**: execution_plan.py:40-71 shows ConnectorSpec has NO `gating_condition` field.

**Implication**: Can't express "run google_places only if serper found < 5 results" in metadata.

**Current Behavior**: Repo uses `should_run_connector()` aggregate logic (checks supports_query_only, context.candidates empty, etc.)

**Phase A/B**: Sufficient (aggregate logic works for basic gating)

**Phase C**: If complex gating needed, integrate conditions.py safe DSL (already exists, not yet wired)

**Decision**: Don't invent gating_condition field. Use existing aggregate logic.

---

### Risk 4: Metrics Accuracy with Mapping Failures ⚠️

**Issue**: If adapter receives 10 items but 2 fail mapping (malformed), what should metrics say?

**Proposed**: Track separately
- `items_received`: 10 (from API)
- `candidates_added`: 8 (successfully mapped)
- `mapping_failures`: 2 (failed)

**Rationale**: Observability for debugging connector issues.

---

### Risk 5: JSON Serialization in Deduplication ⚠️

**Issue**: Tier 3 dedupe uses `json.dumps(canonical)` (execution_context.py:119). If `candidate["raw"]` contains datetime/sets, crashes.

**Likelihood**: High (Google Places API returns nested objects)

**Mitigation**: Add JSON normalization in adapter before appending to context:
- Sets → sorted list (deterministic)
- Tuples → list (preserve order)
- datetime/Decimal/custom → str() fallback

**Implementation**: `_normalize_for_json()` helper in adapter.

---

## 11. Implementation Checklist

### Pre-Implementation (Modify Existing Files)

- [ ] Add `metrics` and `errors` to `ExecutionContext.__init__()` (~2 lines)
- [ ] Add `query: str` to `IngestRequest` dataclass (~1 line)
- [ ] Run existing orchestrator tests to verify no breakage

### Phase A: End-to-End Proof

- [ ] Create `registry.py` with 2 connector specs (serper, google_places)
- [ ] Create `adapters.py` with ConnectorAdapter + mapping functions
  - [ ] Implement async bridge (asyncio.run)
  - [ ] Implement JSON normalization
  - [ ] Map serper results (no IDs, no coords in Phase A)
  - [ ] Map google_places results (strong IDs, flat lat/lng)
- [ ] Create `planner.py` with hardcoded select_connectors()
  - [ ] Implement orchestrate() entry point
  - [ ] Implement validation (fail on missing connectors)
- [ ] Create `cli.py` with run command
  - [ ] Implement display_report()
  - [ ] Add --plan-only flag
- [ ] Tests with mocked API responses (~400 lines)
- [ ] Manual smoke test script with real APIs (~80 lines)
- [ ] Run 5 test queries, verify deduplication works

### Phase B: Query-Aware Selection

- [ ] Add openstreetmap, sport_scotland to registry
- [ ] Add corresponding adapters
- [ ] Replace `select_connectors()` with QueryFeatures-based rules
- [ ] Test: category query includes serper, specific query doesn't
- [ ] Test: sports query includes sport_scotland

### Phase C: Production-Ready

- [ ] Add remaining connectors to registry (6 total)
- [ ] Add budget-aware selection logic
- [ ] Wire persistence mode (extractors → ingest_entity)
- [ ] Test early stopping with low budget
- [ ] Production error reporting

---

## 12. Success Criteria

### Phase A
- ✅ CLI command executes without errors
- ✅ Both connectors make real API calls
- ✅ Deduplication works (accepted < candidates)
- ✅ Phase ordering visible (DISCOVERY → STRUCTURED)
- ✅ Structured report shows per-connector metrics
- ✅ Connector failures are non-fatal (graceful degradation)

### Phase B
- ✅ Category queries trigger different connector set than specific queries
- ✅ Sports queries include sport_scotland
- ✅ Selection logic is testable and clear

### Phase C
- ✅ All 6 connectors available
- ✅ Budget enforcement works (early stopping observable)
- ✅ Entities persist to database
- ✅ Production-ready observability

---

## 13. Out of Scope (Future Work)

**Not in Phases A/B/C**:
- Parallel connector execution (orchestrator supports, not prioritizing)
- Machine learning connector selection (rules-based sufficient)
- Real-time streaming ingestion (batch is fine)
- Multi-query optimization (caching, batching)
- Fully async orchestrator (Phase D if needed for API integration)

---

## Appendix: File Structure

```
engine/orchestration/
├── __init__.py
├── orchestrator.py          # EXISTING (untouched)
├── execution_plan.py        # EXISTING (untouched)
├── execution_context.py     # MODIFIED (+2 lines: metrics, errors)
├── types.py                 # MODIFIED (+1 line: query field)
├── query_features.py        # EXISTING (untouched)
├── conditions.py            # EXISTING (unused in Phase A/B, optional Phase C)
├── adapters.py              # NEW (~200 lines)
├── registry.py              # NEW (~150 lines in Phase A, ~400 in Phase C)
├── planner.py               # NEW (~200 lines)
├── cli.py                   # NEW (~250 lines)
└── tests/
    ├── test_adapters.py     # NEW (~150 lines)
    ├── test_registry.py     # NEW (~50 lines)
    ├── test_planner.py      # NEW (~100 lines)
    └── test_integration.py  # NEW (~100 lines)

scripts/
└── test_orchestration_live.py  # NEW (~80 lines)
```

**Total New Code**: ~1,400 lines
**Modified Existing**: ~3 lines (2 files)

---

**END OF SPECIFICATION**
