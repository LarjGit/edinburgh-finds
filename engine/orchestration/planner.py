"""
Planner for Intelligent Ingestion Orchestration.

Orchestrates the execution of connectors to fulfill an ingestion request:
- Analyzes query and selects optimal connectors
- Executes connectors in sequence via adapters
- Applies deduplication to candidates
- Produces structured execution report

Phase A: Hardcoded connector selection (serper, google_places)
Phase B: Intelligent selection based on query features
Phase C: Budget-aware gating and early stopping
"""

from typing import Dict, List, Any

from engine.orchestration.adapters import ConnectorAdapter
from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import ConnectorSpec, ExecutionPhase
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.registry import CONNECTOR_REGISTRY, get_connector_instance
from engine.orchestration.types import IngestRequest, IngestionMode


def select_connectors(request: IngestRequest) -> List[str]:
    """
    Select which connectors to run for the given request.

    Phase A: Hardcoded selection - always returns ["serper", "google_places"]
    Phase B: Intelligent selection based on query features
    Phase C: Will add budget-aware gating

    Selection logic:
    - Category searches use multiple discovery sources (serper, openstreetmap)
    - Specific searches prioritize high-trust enrichment (google_places)
    - Sports queries include domain-specific connector (sport_scotland)
    - RESOLVE_ONE mode is more selective than DISCOVER_MANY
    - Connectors ordered by phase: discovery first, then enrichment

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

    # Return connectors ordered by phase: discovery first, then enrichment
    return discovery_connectors + enrichment_connectors


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


def orchestrate(request: IngestRequest) -> Dict[str, Any]:
    """
    Orchestrate execution of connectors to fulfill ingestion request.

    Main orchestration flow:
    1. Extract query features
    2. Select connectors to run
    3. Create execution context
    4. Execute connectors via adapters
    5. Apply deduplication
    6. Build structured report

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
    # 1. Extract query features
    query_features = QueryFeatures.extract(request.query, request)

    # 2. Select connectors to run
    connector_names = select_connectors(request)

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
            adapter.execute(request, query_features, context)

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

    # 6. Build structured report
    report = {
        "query": request.query,
        "candidates_found": len(context.candidates),
        "accepted_entities": len(context.accepted_entities),
        "connectors": context.metrics,
        "errors": context.errors,
    }

    return report
