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
"""

import asyncio
import os
from typing import Dict, List, Any

from prisma import Prisma

from engine.orchestration.adapters import ConnectorAdapter
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.registry import CONNECTOR_REGISTRY, get_connector_instance
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.orchestration.persistence import PersistenceManager


def select_connectors(request: IngestRequest) -> List[str]:
    """
    Select which connectors to run for the given request.

    Phase A: Hardcoded selection - always returns ["serper", "google_places"]
    Phase B: Intelligent selection based on query features
    Phase C: Budget-aware gating

    Selection logic:
    - Category searches use multiple discovery sources (serper, openstreetmap)
    - Specific searches prioritize high-trust enrichment (google_places)
    - Sports queries include domain-specific connector (sport_scotland)
    - RESOLVE_ONE mode is more selective than DISCOVER_MANY
    - Connectors ordered by phase: discovery first, then enrichment
    - Budget constraints filter out paid connectors when budget is tight

    Args:
        request: The ingestion request containing query and parameters

    Returns:
        List of connector names to execute, ordered by phase
    """
    # Phase B: Intelligent selection based on query features
    query_features = QueryFeatures.extract(request.query, request)

    # Detect sports domain
    is_sports_query = _is_sports_related(request.query)

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

        # Domain-specific routing: Add sport_scotland for sports queries
        if is_sports_query:
            enrichment_connectors.append("sport_scotland")

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


def _is_sports_related(query: str) -> bool:
    """
    Detect if query is sports-related.

    Checks for sports-specific keywords to determine if domain-specific
    sports connectors (like sport_scotland) should be included.

    Args:
        query: The search query string

    Returns:
        True if query contains sports-related terms
    """
    normalized = query.lower()

    sports_keywords = [
        "padel",
        "tennis",
        "football",
        "rugby",
        "swimming",
        "pool",
        "pools",
        "sport",
        "sports",
        "gym",
        "fitness",
        "court",
        "courts",
        "pitch",
        "club",
        "clubs",
    ]

    return any(keyword in normalized for keyword in sports_keywords)


async def orchestrate(request: IngestRequest) -> Dict[str, Any]:
    """
    Orchestrate execution of connectors to fulfill ingestion request.

    Main orchestration flow:
    0. Create OrchestrationRun record (if persisting)
    1. Extract query features
    2. Select connectors to run
    3. Create execution context
    4. Execute connectors via adapters
    5. Apply deduplication
    6. Persist and extract entities
    7. Build structured report

    Args:
        request: The ingestion request containing query and parameters

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

        # 3. Create execution context
        context = ExecutionContext()

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

        if request.persist:
            try:
                # Use async PersistenceManager with db connection
                async with PersistenceManager(db=db) as persistence:
                    persistence_result = await persistence.persist_entities(
                        context.accepted_entities,
                        context.errors,
                        orchestration_run_id=orchestration_run_id
                    )
                    persisted_count = persistence_result["persisted_count"]
                    persistence_errors = persistence_result["persistence_errors"]

                    # Extraction errors are a subset of persistence_errors
                    # (failures during the extraction step)
                    extraction_errors = [
                        err for err in persistence_errors
                        if "timestamp" in err  # Extraction errors have timestamps
                    ]
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
