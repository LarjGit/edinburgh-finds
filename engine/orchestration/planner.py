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
from pathlib import Path
from typing import Dict, List, Any, Optional

from prisma import Prisma

from engine.lenses.loader import VerticalLens, LensConfigError
from engine.orchestration.adapters import ConnectorAdapter
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.registry import CONNECTOR_REGISTRY, get_connector_instance
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.orchestration.persistence import PersistenceManager
from engine.orchestration.entity_finalizer import EntityFinalizer
from engine.lenses.query_lens import get_active_lens


def select_connectors(request: IngestRequest) -> List[str]:
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
        List of connector names to execute, ordered by phase
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

    # Return connectors ordered by phase: discovery first, then enrichment
    return selected_connectors


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
    ctx: Optional[ExecutionContext] = None
) -> Dict[str, Any]:
    """
    Orchestrate execution of connectors to fulfill ingestion request.

    Main orchestration flow:
    0. Create OrchestrationRun record (if persisting)
    1. Extract query features
    2. Select connectors to run
    3. Create execution context (or use provided context)
    4. Execute connectors via adapters
    5. Apply deduplication
    6. Persist and extract entities
    7. Build structured report

    Args:
        request: The ingestion request containing query and parameters
        ctx: Optional ExecutionContext with pre-loaded lens contract.
             If provided, lens loading is skipped (bootstrap boundary).
             Per architecture.md 3.2: Lens contracts should be loaded once
             at bootstrap and injected via ExecutionContext.

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

        # 2. Select connectors to run
        connector_names = select_connectors(request)

        # 2.5. Check API key availability and warn if Serper will be used
        warnings = []
        if "serper" in connector_names and not os.getenv("ANTHROPIC_API_KEY"):
            warnings.append({
                "type": "missing_api_key",
                "message": "⚠ Serper extraction will fail without ANTHROPIC_API_KEY",
            })

        # 3. Create or use execution context
        # Per architecture.md 3.2: Lens loading should happen at bootstrap
        # If ctx provided → use it (bootstrap boundary respected)
        # If ctx not provided → load lens here (backward compatibility)
        if ctx is not None:
            # Context provided by bootstrap - use it directly
            context = ctx
        else:
            # Legacy path: Load lens here (will be deprecated once bootstrap is enforced)
            # Resolve lens_id with fail-fast for missing lens
            # Per architecture.md §3.1: Dev/test fallback requires explicit flag
            lens_id = request.lens or os.getenv("LENS_ID")

            if not lens_id:
                # FATAL ERROR: No lens specified and no dev/test fallback enabled
                # This prevents silent misconfiguration in production
                error_msg = (
                    "No lens specified. Set request.lens or LENS_ID environment variable. "
                    "For dev/test environments, enable explicit fallback in configuration."
                )
                return {
                    "query": request.query,
                    "candidates_found": 0,
                    "accepted_entities": 0,
                    "connectors": {},
                    "errors": [{"connector": "lens_resolution", "error": error_msg}],
                }

            # Bootstrap: Load and validate lens configuration ONCE
            # This is the bootstrap boundary - lens loading permitted ONLY here
            lens_contract = None
            try:
                lens_path = Path(__file__).parent.parent / "lenses" / lens_id / "lens.yaml"
                vertical_lens = VerticalLens(lens_path)

                # Extract compiled, immutable lens contract (plain dict)
                # Shallow copy for defensive programming
                lens_contract = {
                    "mapping_rules": list(vertical_lens.mapping_rules),  # Copy list
                    "module_triggers": list(vertical_lens.module_triggers),  # Copy list
                    "modules": dict(vertical_lens.domain_modules),  # Copy dict
                    "facets": dict(vertical_lens.facets),  # Copy dict for facet→dimension lookup
                    "values": list(vertical_lens.values),  # Copy list for canonical value lookup
                    "confidence_threshold": vertical_lens.confidence_threshold,
                }

                # Compute deterministic content hash for reproducibility
                import hashlib
                import json
                canonical_contract = json.dumps(lens_contract, sort_keys=True)
                lens_hash = hashlib.sha256(canonical_contract.encode("utf-8")).hexdigest()

            except LensConfigError as e:
                # Fail fast on invalid lens (per architecture.md 3.2)
                # Context doesn't exist yet, so accumulate error and return early
                return {
                    "query": request.query,
                    "candidates_found": 0,
                    "accepted_entities": 0,
                    "connectors": {},
                    "errors": [{"connector": "lens_bootstrap", "error": f"Lens validation failed: {e}"}],
                }

            # Create context with lens metadata per architecture.md 3.6
            # NOTE: This fallback bootstrap path should be removed in Phase B - only cli.bootstrap_lens should create context
            context = ExecutionContext(
                lens_id=lens_id,
                lens_contract=lens_contract,
                lens_hash=lens_hash
            )

        # 4. Execute connectors via adapters
        for connector_name in connector_names:
            # Get connector spec from registry
            if connector_name not in CONNECTOR_REGISTRY:
                # Log error but continue with other connectors
                context.errors.append({
                    "connector": connector_name,
                    "error": f"Connector not found in registry: {connector_name}",
                    "execution_time_ms": 0,
                })
                continue

            registry_spec = CONNECTOR_REGISTRY[connector_name]

            # Create ConnectorSpec for adapter (convert registry spec to execution plan spec)
            connector_spec = ConnectorSpec(
                name=registry_spec.name,
                phase=ExecutionPhase.DISCOVERY if registry_spec.phase == "discovery" else ExecutionPhase.ENRICHMENT,
                trust_level=int(registry_spec.trust_level * 100),  # Convert 0.0-1.0 to 0-100
                requires=["request.query"],  # Phase A: minimal requirements
                provides=["context.candidates"],
                supports_query_only=True,
                estimated_cost_usd=registry_spec.cost_per_call_usd,
            )

            # Get connector instance
            try:
                connector = get_connector_instance(connector_name)

                # Create adapter
                adapter = ConnectorAdapter(connector, connector_spec)

                # Execute connector (adapter handles errors internally)
                await adapter.execute(request, query_features, context)

            except Exception as e:
                # Unexpected error during adapter creation
                context.errors.append({
                    "connector": connector_name,
                    "error": f"Failed to create connector: {str(e)}",
                    "execution_time_ms": 0,
                })

        # 5. Apply deduplication
        # Process all candidates through accept_entity to deduplicate
        for candidate in context.candidates:
            context.accept_entity(candidate)

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
                        context.accepted_entities,
                        context.errors,
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
                context.errors.append({
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
            "candidates_found": len(context.candidates),
            "accepted_entities": len(context.accepted_entities),
            "connectors": context.metrics,
            "errors": context.errors,
        }

        # Add warnings if any
        if warnings:
            report["warnings"] = warnings

        # Add persistence info if persist was enabled
        if request.persist:
            report["persisted_count"] = persisted_count
            report["persistence_errors"] = persistence_errors

            # Add extraction statistics
            extraction_total = len(context.accepted_entities)
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
                total_budget = sum(m.get("cost_usd", 0.0) for m in context.metrics.values())

                await db.orchestrationrun.update(
                    where={"id": orchestration_run_id},
                    data={
                        "status": "completed" if not context.errors else "completed_with_errors",
                        "candidates_found": len(context.candidates),
                        "accepted_entities": len(context.accepted_entities),
                        "budget_spent_usd": total_budget,
                    }
                )
            except Exception as e:
                # Don't crash if status update fails
                pass

            await db.disconnect()
