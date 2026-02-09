"""
Planner for Intelligent Ingestion Orchestration.

Orchestrates the execution of connectors to fulfill an ingestion request:
- Analyzes query and selects optimal connectors
- Executes connectors in sequence via adapters
- Applies deduplication to candidates
- Optionally persists accepted entities to database
- Produces structured execution report

Phase A: Hardcoded connector selection (serper, google_places)
Phase B: Intelligent selection based on query features
Phase C: Budget-aware gating, early stopping, and persistence

ARCHITECTURAL NOTE: This module is now VERTICAL-AGNOSTIC. Domain-specific connector
routing (e.g., sport_scotland for sports queries) is driven by Lens configurations.
Adding a new vertical (Wine, Restaurants) requires ZERO planner code changes.
"""

import asyncio
import os
from typing import Dict, List, Any

from prisma import Prisma

from engine.orchestration.adapters import ConnectorAdapter
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.orchestrator_state import OrchestratorState
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase, ExecutionPlan
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.registry import CONNECTOR_REGISTRY, get_connector_instance
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.orchestration.persistence import PersistenceManager
from engine.orchestration.entity_finalizer import EntityFinalizer
from engine.lenses.query_lens import get_active_lens


def select_connectors(request: IngestRequest) -> ExecutionPlan:
    """
    Select which connectors to run for the given request.

    Phase A: Hardcoded selection - always returns ["serper", "google_places"]
    Phase B: Intelligent selection based on query features
    Phase C: Budget-aware gating

    Selection logic:
    - Category searches use multiple discovery sources (serper, openstreetmap)
    - Specific searches prioritize high-trust enrichment (google_places)
    - Domain-specific connectors determined by Lens (VERTICAL-AGNOSTIC)
      e.g., Padel lens adds sport_scotland for sports queries
           Wine lens adds wine_searcher for wine queries
    - RESOLVE_ONE mode is more selective than DISCOVER_MANY
    - Connectors ordered by phase: discovery first, then enrichment
    - Budget constraints filter out paid connectors when budget is tight

    Args:
        request: The ingestion request containing query and parameters

    Returns:
        ExecutionPlan with connectors to execute, ordered by phase
    """
    # Phase B: Intelligent selection based on query features
    query_features = QueryFeatures.extract(request.query, request, lens_name=request.lens)

    # Load Lens for domain-specific connector routing (VERTICAL-AGNOSTIC)
    lens = get_active_lens(request.lens)

    # Initialize connector sets by phase
    discovery_connectors = []
    enrichment_connectors = []

    # Selection rules based on query type and mode
    if request.ingestion_mode == IngestionMode.RESOLVE_ONE:
        # RESOLVE_ONE: Prioritize high-trust enrichment, minimal discovery
        if not query_features.looks_like_category_search:
            # Specific venue search - just use high-trust enrichment
            enrichment_connectors.append("google_places")
        else:
            # Category search in RESOLVE_ONE mode - still selective
            discovery_connectors.append("serper")
            enrichment_connectors.append("google_places")

    else:  # DISCOVER_MANY
        # Discovery phase: Use multiple sources for broad coverage
        discovery_connectors.append("serper")

        if query_features.looks_like_category_search:
            # Category search: Add free discovery source for comprehensive results
            discovery_connectors.append("openstreetmap")

        # Enrichment phase: Always use google_places for authoritative data
        enrichment_connectors.append("google_places")

    # Domain-specific routing: Use Lens to determine additional connectors (VERTICAL-AGNOSTIC)
    # This replaces the hardcoded _is_sports_related() check
    lens_connectors = lens.get_connectors_for_query(request.query.lower(), query_features)
    enrichment_connectors.extend(lens_connectors)

    # Phase C: Apply budget-aware gating
    selected_connectors = discovery_connectors + enrichment_connectors

    if request.budget_usd is not None:
        selected_connectors = _apply_budget_gating(selected_connectors, request.budget_usd)

    # Build ExecutionPlan from selected connectors
    plan = ExecutionPlan()
    for connector_name in selected_connectors:
        # Get connector spec from registry
        if connector_name not in CONNECTOR_REGISTRY:
            # Skip unknown connectors
            continue

        registry_spec = CONNECTOR_REGISTRY[connector_name]

        # Convert registry spec to execution plan spec
        connector_spec = ConnectorSpec(
            name=registry_spec.name,
            phase=ExecutionPhase.DISCOVERY if registry_spec.phase == "discovery" else ExecutionPhase.ENRICHMENT,
            trust_level=int(registry_spec.trust_level * 100),  # Convert 0.0-1.0 to 0-100
            requires=["request.query"],  # Phase A: minimal requirements
            provides=["context.candidates"],
            supports_query_only=True,
            estimated_cost_usd=registry_spec.cost_per_call_usd,
            timeout_seconds=registry_spec.timeout_seconds,  # PL-002: Pass timeout constraint
            rate_limit_per_day=registry_spec.rate_limit_per_day,  # PL-004: Pass rate limit constraint
        )

        # Add to plan (automatic dependency inference)
        plan.add_connector(connector_spec)

    return plan


def _apply_budget_gating(connectors: List[str], budget_usd: float) -> List[str]:
    """
    Filter connectors based on budget constraints.

    Budget-aware selection strategy:
    - Free connectors (cost = 0.0) are always included
    - Paid connectors are added in order until budget would be exceeded
    - Preserves connector order (discovery before enrichment)
    - Prioritizes high-trust connectors when budget is tight

    Args:
        connectors: List of connector names to filter
        budget_usd: Maximum budget in USD

    Returns:
        Filtered list of connectors that fit within budget
    """
    selected = []
    cumulative_cost = 0.0

    for connector_name in connectors:
        # Skip connectors not in registry
        if connector_name not in CONNECTOR_REGISTRY:
            continue

        spec = CONNECTOR_REGISTRY[connector_name]
        connector_cost = spec.cost_per_call_usd

        # Free connectors are always included
        if connector_cost == 0.0:
            selected.append(connector_name)
            continue

        # Check if adding this connector would exceed budget
        if cumulative_cost + connector_cost <= budget_usd:
            selected.append(connector_name)
            cumulative_cost += connector_cost
        # else: skip this connector (budget would be exceeded)

    return selected


async def orchestrate(
    request: IngestRequest,
    *,
    ctx: ExecutionContext
) -> Dict[str, Any]:
    """
    Orchestrate execution of connectors to fulfill ingestion request.

    Main orchestration flow:
    0. Create OrchestrationRun record (if persisting)
    1. Extract query features
    2. Select connectors to run
    3. Use execution context from bootstrap
    4. Execute connectors via adapters
    5. Apply deduplication
    6. Persist and extract entities
    7. Build structured report

    Args:
        request: The ingestion request containing query and parameters
        ctx: REQUIRED ExecutionContext with pre-loaded lens contract.
             Per docs/target-architecture.md 3.2: Lens contracts are loaded once at
             bootstrap and injected via ExecutionContext. All callers must
             bootstrap lens before calling orchestrate() (LR-003).

    Returns:
        Structured report dict with keys:
        - query: Echo of the original query
        - candidates_found: Total number of candidates discovered
        - accepted_entities: Number of unique entities after deduplication
        - connectors: Dict of per-connector metrics
        - errors: List of errors that occurred during execution
    """
    # 0. Create OrchestrationRun record if persisting
    orchestration_run_id = None
    db = None

    if request.persist:
        db = Prisma()
        await db.connect()

        orchestration_run = await db.orchestrationrun.create(
            data={
                "query": request.query,
                "ingestion_mode": request.ingestion_mode.value,
                "status": "in_progress",
            }
        )
        orchestration_run_id = orchestration_run.id

    try:
        # 1. Extract query features
        query_features = QueryFeatures.extract(request.query, request)

        # 2. Select connectors to run (returns ExecutionPlan)
        plan = select_connectors(request)

        # 2.5. Check API key availability and warn if Serper will be used
        warnings = []
        connector_names = [node.spec.name for node in plan.connectors]
        if "serper" in connector_names and not os.getenv("ANTHROPIC_API_KEY"):
            warnings.append({
                "type": "missing_api_key",
                "message": "⚠ Serper extraction will fail without ANTHROPIC_API_KEY",
            })

        # 3. Use execution context from bootstrap
        # Per docs/target-architecture.md 3.2: Lens loading occurs only during engine bootstrap
        # All callers must bootstrap lens before calling orchestrate()
        context = ctx

        # Create mutable orchestrator state (separate from immutable context per docs/target-architecture.md 3.6)
        state = OrchestratorState()

        # 4. Execute connectors via adapters (phase-aware with parallelism per PL-003)
        # Per docs/target-architecture.md 4.1 Stage 3: "Establish execution phases" implies
        # phase barriers with parallelism within phases
        from collections import defaultdict

        # Group connectors by phase
        phases = defaultdict(list)
        for node in plan.connectors:
            phases[node.spec.phase].append(node)

        # Execute phases in order: DISCOVERY → STRUCTURED → ENRICHMENT
        for phase in sorted(phases.keys(), key=lambda p: p.value):
            phase_nodes = phases[phase]

            # Execute all connectors in this phase concurrently
            tasks = []
            for node in phase_nodes:
                connector_name = node.spec.name

                try:
                    connector = get_connector_instance(connector_name)
                    adapter = ConnectorAdapter(connector, node.spec)

                    # Create task for concurrent execution
                    # Pass db for rate limit tracking (PL-004)
                    task = adapter.execute(request, query_features, context, state, db=db)
                    tasks.append(task)

                except Exception as e:
                    # Unexpected error during adapter creation
                    state.errors.append({
                        "connector": connector_name,
                        "error": f"Failed to create connector: {str(e)}",
                        "execution_time_ms": 0,
                    })

            # Wait for all connectors in this phase to complete
            # Note: adapter.execute() handles exceptions internally,
            # so gather should not raise exceptions
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=False)

        # 5. Apply deduplication
        # Process all candidates through accept_entity to deduplicate
        for candidate in state.candidates:
            state.accept_entity(candidate)

        # 6. Persist accepted entities if requested
        persisted_count = 0
        persistence_errors = []
        extraction_errors = []
        entities_created = 0
        entities_updated = 0

        if request.persist:
            try:
                # Use async PersistenceManager with db connection
                async with PersistenceManager(db=db) as persistence:
                    persistence_result = await persistence.persist_entities(
                        state.accepted_entities,
                        state.errors,
                        orchestration_run_id=orchestration_run_id,
                        context=context
                    )
                    persisted_count = persistence_result["persisted_count"]
                    persistence_errors = persistence_result["persistence_errors"]

                    # Extraction errors are a subset of persistence_errors
                    # (failures during the extraction step)
                    extraction_errors = [
                        err for err in persistence_errors
                        if "timestamp" in err  # Extraction errors have timestamps
                    ]

                # ✅ NEW: Finalize entities to Entity table
                finalizer = EntityFinalizer(db)
                finalization_result = await finalizer.finalize_entities(orchestration_run_id)
                entities_created = finalization_result.get("entities_created", 0)
                entities_updated = finalization_result.get("entities_updated", 0)

            except Exception as e:
                # Handle persistence errors gracefully - don't crash orchestration
                error_msg = f"Persistence failed: {str(e)}"
                state.errors.append({
                    "connector": "persistence",
                    "error": error_msg,
                })
                persistence_errors.append({
                    "source": "persistence",
                    "error": error_msg,
                    "entity_name": "N/A",
                })

        # 7. Build structured report
        report = {
            "query": request.query,
            "candidates_found": len(state.candidates),
            "accepted_entities": len(state.accepted_entities),
            "connectors": state.metrics,
            "errors": state.errors,
        }

        # Add warnings if any
        if warnings:
            report["warnings"] = warnings

        # Add persistence info if persist was enabled
        if request.persist:
            report["persisted_count"] = persisted_count
            report["persistence_errors"] = persistence_errors

            # Add extraction statistics
            extraction_total = len(state.accepted_entities)
            extraction_success = persisted_count  # Successfully persisted = successfully extracted
            report["extraction_total"] = extraction_total
            report["extraction_success"] = extraction_success
            report["extraction_errors"] = extraction_errors

            # Add entity finalization stats
            report["entities_created"] = entities_created
            report["entities_updated"] = entities_updated

        return report

    finally:
        # Update OrchestrationRun status and metrics if created
        if db and orchestration_run_id:
            try:
                # Calculate total budget spent
                total_budget = sum(m.get("cost_usd", 0.0) for m in state.metrics.values())

                await db.orchestrationrun.update(
                    where={"id": orchestration_run_id},
                    data={
                        "status": "completed" if not state.errors else "completed_with_errors",
                        "candidates_found": len(state.candidates),
                        "accepted_entities": len(state.accepted_entities),
                        "budget_spent_usd": total_budget,
                    }
                )
            except Exception as e:
                # Don't crash if status update fails
                pass

            await db.disconnect()
