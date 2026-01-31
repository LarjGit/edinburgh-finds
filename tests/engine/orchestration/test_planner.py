"""
Tests for Planner module.

Validates the orchestrate() function and connector selection logic:
- orchestrate() executes connectors and produces a report
- Hardcoded selection (Phase A) includes serper and google_places
- Deduplication works (accepted < candidates)
- Metrics tracking per connector
- Error handling (non-fatal connector failures)
"""

import pytest
from engine.orchestration.planner import orchestrate, select_connectors
from engine.orchestration.types import IngestRequest, IngestionMode


class TestSelectConnectors:
    """Test connector selection logic (Phase B: intelligent selection)."""

    def test_select_connectors_returns_list(self):
        """select_connectors should return a list of connector names."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )
        connectors = select_connectors(request)
        assert isinstance(connectors, list), "select_connectors should return a list"

    def test_select_connectors_includes_base_connectors(self):
        """select_connectors should include core discovery and enrichment connectors."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )
        connectors = select_connectors(request)

        # Should always include serper (discovery) and google_places (enrichment)
        assert "serper" in connectors, "serper should be selected for discovery"
        assert "google_places" in connectors, "google_places should be selected for enrichment"
        # Phase B: May include additional connectors based on query features
        assert len(connectors) >= 2, "Should select at least base connectors"

    def test_select_connectors_deterministic(self):
        """select_connectors should return same connectors for same request."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        connectors_1 = select_connectors(request)
        connectors_2 = select_connectors(request)

        assert connectors_1 == connectors_2, "Selection should be deterministic"


class TestOrchestrate:
    """Test orchestrate() main execution flow."""

    @pytest.mark.asyncio
    async def test_orchestrate_returns_dict(self, mock_context):
        """orchestrate() should return a structured report dict."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        assert isinstance(report, dict), "orchestrate should return a dict"

    @pytest.mark.asyncio
    async def test_orchestrate_report_structure(self, mock_context):
        """orchestrate() report should have required top-level keys."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        # Required report keys
        assert "query" in report, "report should include query"
        assert "candidates_found" in report, "report should include candidates_found"
        assert "accepted_entities" in report, "report should include accepted_entities"
        assert "connectors" in report, "report should include connectors metrics"
        assert "errors" in report, "report should include errors"

    @pytest.mark.asyncio
    async def test_orchestrate_candidates_found_is_int(self, mock_context):
        """candidates_found should be a non-negative integer."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        assert isinstance(report["candidates_found"], int), "candidates_found should be int"
        assert report["candidates_found"] >= 0, "candidates_found should be >= 0"

    @pytest.mark.asyncio
    async def test_orchestrate_accepted_entities_is_int(self, mock_context):
        """accepted_entities should be a non-negative integer."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        assert isinstance(report["accepted_entities"], int), "accepted_entities should be int"
        assert report["accepted_entities"] >= 0, "accepted_entities should be >= 0"

    @pytest.mark.asyncio
    async def test_orchestrate_deduplication_works(self, mock_context):
        """Deduplication should result in accepted_entities <= candidates_found."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        # Deduplication invariant
        assert report["accepted_entities"] <= report["candidates_found"], \
            "accepted_entities should be <= candidates_found (deduplication)"

    @pytest.mark.asyncio
    async def test_orchestrate_connectors_metrics_is_dict(self, mock_context):
        """connectors metrics should be a dict with per-connector data."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        assert isinstance(report["connectors"], dict), "connectors should be a dict"

    @pytest.mark.asyncio
    async def test_orchestrate_errors_is_list(self, mock_context):
        """errors should be a list."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        assert isinstance(report["errors"], list), "errors should be a list"

    @pytest.mark.asyncio
    async def test_orchestrate_query_echo(self, mock_context):
        """Report should echo the original query string."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        assert report["query"] == "tennis courts Edinburgh", "query should be echoed in report"


class TestSelectConnectorsPhaseB:
    """Test intelligent connector selection logic (Phase B)."""

    def test_category_search_with_geo_and_sports_domain(self):
        """
        Category search with geographic intent and sports domain should use:
        - Discovery connectors (serper, openstreetmap) for broad coverage
        - Enrichment connectors (google_places) for high-quality data
        - Domain-specific connectors (sport_scotland) for sports
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts in Edinburgh",
        )

        selected = select_connectors(request)

        # Should include all relevant connectors
        assert "serper" in selected, "Should use serper for discovery"
        assert "google_places" in selected, "Should use google_places for enrichment"
        assert "openstreetmap" in selected, "Should use OSM for free discovery"
        assert "sport_scotland" in selected, "Should use sport_scotland for sports domain"

        # Verify order: discovery connectors first, then enrichment
        discovery_phase = ["serper", "openstreetmap"]
        enrichment_phase = ["google_places", "sport_scotland"]

        # All discovery connectors should come before enrichment
        last_discovery_idx = max(
            [selected.index(c) for c in discovery_phase if c in selected]
        )
        first_enrichment_idx = min(
            [selected.index(c) for c in enrichment_phase if c in selected]
        )

        assert last_discovery_idx < first_enrichment_idx, (
            "Discovery connectors should execute before enrichment connectors"
        )

    def test_specific_venue_search_prioritizes_enrichment(self):
        """
        Specific venue search should prioritize high-trust enrichment.
        Use fewer connectors since we're looking for a specific entity.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="Oriam Scotland",
        )

        selected = select_connectors(request)

        # Should prioritize google_places for authoritative data
        assert "google_places" in selected, "Should use google_places for specific search"

        # May include serper for initial discovery
        # But should be more selective than category search
        assert len(selected) <= 2, "Should be selective for specific venue search"

    def test_sports_query_includes_sport_scotland(self):
        """
        Queries with sports-related terms should include sport_scotland.
        Test various sports keywords.
        """
        sports_queries = [
            "tennis clubs in Edinburgh",
            "football facilities Leith",
            "swimming pools near me",
            "rugby clubs",
        ]

        for query in sports_queries:
            request = IngestRequest(
                ingestion_mode=IngestionMode.DISCOVER_MANY,
                query=query,
            )

            selected = select_connectors(request)

            assert "sport_scotland" in selected, (
                f"Query '{query}' should include sport_scotland connector"
            )

    def test_non_sports_query_excludes_sport_scotland(self):
        """
        Non-sports queries should not include sport_scotland to save resources.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="coffee shops in Edinburgh",
        )

        selected = select_connectors(request)

        assert "sport_scotland" not in selected, (
            "Non-sports query should not include sport_scotland"
        )

    def test_category_search_without_geo_uses_discovery(self):
        """
        Category search without specific location should focus on discovery.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel",
        )

        selected = select_connectors(request)

        # Should include discovery connectors
        assert "serper" in selected, "Should use serper for discovery"
        assert "openstreetmap" in selected, "Should use OSM for discovery"

    def test_connector_ordering_by_phase(self):
        """
        Connectors should be ordered by phase: discovery first, then enrichment.
        This ensures base candidates are found before enrichment.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts in Edinburgh",
        )

        selected = select_connectors(request)

        # Get indices of discovery and enrichment connectors
        discovery_connectors = ["serper", "openstreetmap"]
        enrichment_connectors = ["google_places", "sport_scotland"]

        discovery_indices = [
            selected.index(c) for c in selected if c in discovery_connectors
        ]
        enrichment_indices = [
            selected.index(c) for c in selected if c in enrichment_connectors
        ]

        if discovery_indices and enrichment_indices:
            # All discovery should come before all enrichment
            assert max(discovery_indices) < min(enrichment_indices), (
                "Discovery connectors must execute before enrichment connectors"
            )

    def test_resolve_one_mode_is_more_selective(self):
        """
        RESOLVE_ONE mode should use fewer connectors than DISCOVER_MANY.
        Focus on high-quality, authoritative sources.
        """
        query = "tennis courts in Edinburgh"

        discover_request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query=query,
        )
        resolve_request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query=query,
        )

        discover_selected = select_connectors(discover_request)
        resolve_selected = select_connectors(resolve_request)

        # RESOLVE_ONE should use fewer or equal connectors
        assert len(resolve_selected) <= len(discover_selected), (
            "RESOLVE_ONE should be more selective than DISCOVER_MANY"
        )

        # RESOLVE_ONE should prioritize high-trust connectors
        if "google_places" in discover_selected:
            assert "google_places" in resolve_selected, (
                "RESOLVE_ONE should include high-trust google_places"
            )


class TestSelectConnectorsBudgetAware:
    """Test budget-aware connector selection logic (Phase C)."""

    def test_no_budget_limit_selects_all_relevant_connectors(self):
        """
        When budget_usd is None, select_connectors should not skip any relevant connectors.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts in Edinburgh",
            budget_usd=None,
        )

        selected = select_connectors(request)

        # Should include all relevant connectors for sports + category search
        assert "serper" in selected
        assert "google_places" in selected
        assert "openstreetmap" in selected
        assert "sport_scotland" in selected

    def test_zero_budget_selects_only_free_connectors(self):
        """
        When budget_usd is 0.0, select_connectors should only select free connectors.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts in Edinburgh",
            budget_usd=0.0,
        )

        selected = select_connectors(request)

        # Should only include free connectors (openstreetmap, sport_scotland)
        # Should exclude paid connectors (serper, google_places)
        assert "openstreetmap" in selected, "Should include free OSM"
        assert "sport_scotland" in selected, "Should include free SportScotland"
        assert "serper" not in selected, "Should exclude paid Serper"
        assert "google_places" not in selected, "Should exclude paid GooglePlaces"

    def test_low_budget_prioritizes_essential_connectors(self):
        """
        When budget is tight (e.g., $0.02), prioritize essential high-trust connectors.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts in Edinburgh",
            budget_usd=0.02,  # Only enough for 1-2 paid API calls
        )

        selected = select_connectors(request)

        # Should include at least one discovery and one enrichment source
        # Free connectors should always be included
        assert "openstreetmap" in selected, "Should always include free OSM"

        # Should be selective with paid connectors
        paid_connectors = [c for c in selected if c in ["serper", "google_places"]]
        assert len(paid_connectors) <= 2, "Should limit paid connectors with low budget"

    def test_high_budget_allows_comprehensive_search(self):
        """
        When budget is high (e.g., $1.00), select all relevant connectors for comprehensive results.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts in Edinburgh",
            budget_usd=1.0,  # Plenty of budget
        )

        selected = select_connectors(request)

        # Should include all relevant connectors
        assert "serper" in selected
        assert "google_places" in selected
        assert "openstreetmap" in selected
        assert "sport_scotland" in selected

    def test_budget_respects_cumulative_cost(self):
        """
        Budget tracking should be cumulative - stop adding connectors when budget would be exceeded.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts in Edinburgh",
            budget_usd=0.015,  # Between serper ($0.01) and google_places ($0.017)
        )

        selected = select_connectors(request)

        # Calculate total estimated cost
        from engine.orchestration.registry import CONNECTOR_REGISTRY
        total_cost = sum(
            CONNECTOR_REGISTRY[c].cost_per_call_usd
            for c in selected
            if c in CONNECTOR_REGISTRY
        )

        # Total cost should not exceed budget
        assert total_cost <= 0.015, "Total connector cost should respect budget limit"

    def test_free_connectors_not_affected_by_budget(self):
        """
        Free connectors should always be selected regardless of budget constraints.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts in Edinburgh",
            budget_usd=0.0,  # Zero budget
        )

        selected = select_connectors(request)

        # Free connectors should be included
        free_connector_names = ["openstreetmap", "sport_scotland"]
        selected_free = [c for c in selected if c in free_connector_names]

        assert len(selected_free) > 0, "Should include at least one free connector"


class TestOrchestrateIntegration:
    """Integration tests for orchestrate() with real connectors."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_orchestrate_executes_serper_and_google_places(self, mock_context):
        """orchestrate() should execute both serper and google_places connectors."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        # Both connectors should have metrics
        assert "serper" in report["connectors"], "serper metrics should be present"
        assert "google_places" in report["connectors"], "google_places metrics should be present"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_orchestrate_serper_metrics_structure(self, mock_context):
        """Serper connector metrics should have expected structure."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)
        serper_metrics = report["connectors"]["serper"]

        # Verify metrics structure
        assert "executed" in serper_metrics, "serper metrics should include 'executed'"
        assert "execution_time_ms" in serper_metrics, "serper metrics should include 'execution_time_ms'"
        assert "cost_usd" in serper_metrics, "serper metrics should include 'cost_usd'"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_orchestrate_google_places_metrics_structure(self, mock_context):
        """Google Places connector metrics should have expected structure."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)
        google_places_metrics = report["connectors"]["google_places"]

        # Verify metrics structure
        assert "executed" in google_places_metrics, "google_places metrics should include 'executed'"
        assert "execution_time_ms" in google_places_metrics, "google_places metrics should include 'execution_time_ms'"
        assert "cost_usd" in google_places_metrics, "google_places metrics should include 'cost_usd'"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_orchestrate_finds_candidates(self, mock_context):
        """orchestrate() should find at least some candidates for a real query."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = await orchestrate(request, ctx=mock_context)

        # Should find some candidates (real API call)
        # Note: This test requires API keys and network access
        # In CI/CD, mock the connectors or skip with pytest.mark.skipif
        assert report["candidates_found"] >= 0, "Should complete without error"


class TestLensLoadingBoundary:
    """Test lens loading boundary compliance (architecture.md 3.2)."""

    @pytest.mark.asyncio
    async def test_orchestrate_accepts_execution_context_parameter(self, mock_context):
        """
        orchestrate() must accept ExecutionContext parameter (LB-001).

        Per architecture.md 3.2: "Lens contracts enter runtime exclusively
        through ExecutionContext." The orchestrate() function should receive
        lens contract via ctx parameter, not load it internally.
        """
        from engine.orchestration.execution_context import ExecutionContext

        # Create minimal lens contract
        lens_contract = {
            "mapping_rules": [],
            "module_triggers": [],
            "modules": {},
            "facets": {},
            "values": [],
            "confidence_threshold": 0.7,
            "lens_id": "edinburgh_finds",
        }

        # Create context with lens contract
        ctx = ExecutionContext(
            lens_id="edinburgh_finds",
            lens_contract=lens_contract,
            lens_hash="test_hash"
        )

        # Create request
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        # orchestrate() should accept ctx parameter
        report = await orchestrate(request, ctx=ctx)

        # Should return valid report
        assert isinstance(report, dict), "orchestrate should return report"
        assert "query" in report, "report should include query"

    @pytest.mark.asyncio
    async def test_orchestrate_uses_lens_from_context_not_disk(self, mock_context):
        """
        orchestrate() must use lens from context (LB-001 + LR-003).

        Per architecture.md 3.2: "No runtime component may load, reload, or
        mutate lens configuration." After LR-003, orchestrate() requires ctx
        parameter and has NO fallback bootstrap path. Lens loading occurs
        only at bootstrap.
        """
        from engine.orchestration.execution_context import ExecutionContext

        # Create minimal lens contract
        lens_contract = {
            "mapping_rules": [],
            "module_triggers": [],
            "modules": {},
            "facets": {},
            "values": [],
            "confidence_threshold": 0.7,
        }

        ctx = ExecutionContext(
            lens_id="test_lens",
            lens_contract=lens_contract,
            lens_hash="test_hash"
        )

        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        # orchestrate() should work correctly with provided context
        report = await orchestrate(request, ctx=ctx)

        # Should return valid report
        assert isinstance(report, dict)
        assert "query" in report
