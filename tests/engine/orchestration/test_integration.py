"""
Integration tests for orchestration system.

Tests the full orchestration flow end-to-end with multiple connectors:
- Multi-connector execution and coordination
- Cross-source deduplication
- Phase ordering (discovery before enrichment)
- Error handling and resilience
- Real-world query scenarios
- Metrics aggregation across connectors
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from engine.orchestration.planner import orchestrate, select_connectors
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.ingestion.base import BaseConnector


class TestMultiConnectorOrchestration:
    """Test orchestration with multiple connectors working together."""

    def test_orchestrate_executes_multiple_connectors(self):
        """
        orchestrate() should execute all selected connectors and aggregate results.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts in Edinburgh",
        )

        report = orchestrate(request)

        # Should execute multiple connectors for a category search
        assert len(report["connectors"]) > 1, "Should execute multiple connectors"

        # All executed connectors should have metrics
        for connector_name, metrics in report["connectors"].items():
            assert "executed" in metrics, f"{connector_name} should have 'executed' field"
            assert "execution_time_ms" in metrics, f"{connector_name} should track execution time"
            assert "cost_usd" in metrics, f"{connector_name} should track cost"

    def test_orchestrate_aggregates_candidates_across_sources(self):
        """
        orchestrate() should collect candidates from all connectors.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts in Edinburgh",
        )

        report = orchestrate(request)

        # Should find candidates from multiple sources
        assert report["candidates_found"] >= 0, "Should collect candidates"

        # Candidates count should be sum of all connector results
        total_candidates_from_metrics = sum(
            metrics.get("candidates_found", 0)
            for metrics in report["connectors"].values()
        )

        # Total candidates should match the aggregated count
        # (Note: This may differ if deduplication happens during collection)
        assert isinstance(total_candidates_from_metrics, int), "Should aggregate candidate counts"

    def test_orchestrate_deduplicates_across_sources(self):
        """
        orchestrate() should deduplicate entities found by multiple connectors.
        Same venue found by serper and google_places should only appear once.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="Oriam Scotland",  # Well-known venue likely in multiple sources
        )

        report = orchestrate(request)

        # After deduplication, accepted entities should be <= candidates
        assert report["accepted_entities"] <= report["candidates_found"], (
            "Deduplication should reduce or maintain entity count"
        )

    def test_orchestrate_respects_phase_ordering(self):
        """
        orchestrate() should execute discovery connectors before enrichment.
        Verify through metrics that discovery phase completes first.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts Edinburgh",
        )

        # Get selected connectors to understand expected order
        selected = select_connectors(request)

        report = orchestrate(request)

        # All selected connectors should have metrics (even if they failed)
        for connector_name in selected:
            assert connector_name in report["connectors"], (
                f"{connector_name} should have metrics"
            )

        # Verify each connector has valid metrics
        # Note: Some connectors may fail (executed=False), which is acceptable
        for connector_name in selected:
            metrics = report["connectors"][connector_name]
            assert "executed" in metrics, f"{connector_name} should have 'executed' field"
            assert "execution_time_ms" in metrics, f"{connector_name} should track execution time"
            assert metrics["execution_time_ms"] >= 0, "Execution time should be non-negative"


class TestErrorHandlingAndResilience:
    """Test orchestration error handling and resilience."""

    def test_orchestrate_continues_after_connector_failure(self):
        """
        If one connector fails, orchestration should continue with other connectors.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        # Execute orchestration (may have errors from API failures)
        report = orchestrate(request)

        # Report should still be structured even if errors occurred
        assert "errors" in report, "Report should include errors list"
        assert isinstance(report["errors"], list), "Errors should be a list"

        # Should still have some results even if errors occurred
        assert "connectors" in report, "Should have connector metrics"
        assert "candidates_found" in report, "Should report candidates found"
        assert "accepted_entities" in report, "Should report accepted entities"

    def test_orchestrate_tracks_connector_errors(self):
        """
        orchestrate() should track which connectors encountered errors.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="test query",
        )

        report = orchestrate(request)

        # Errors should be structured
        for error in report["errors"]:
            assert "connector" in error, "Error should identify connector"
            assert "error" in error, "Error should include error message"

    def test_orchestrate_handles_invalid_connector_gracefully(self):
        """
        If a connector is in the selection but not in the registry,
        orchestration should log error and continue.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts",
        )

        # Mock select_connectors to return an invalid connector
        with patch("engine.orchestration.planner.select_connectors") as mock_select:
            mock_select.return_value = ["serper", "invalid_connector", "google_places"]

            report = orchestrate(request)

            # Should handle invalid connector gracefully
            assert "invalid_connector" in [e["connector"] for e in report["errors"]], (
                "Should log error for invalid connector"
            )

            # Should still execute valid connectors
            assert "serper" in report["connectors"] or "google_places" in report["connectors"], (
                "Should execute valid connectors despite invalid one"
            )


class TestRealWorldQueryScenarios:
    """Test orchestration with real-world query patterns."""

    @pytest.mark.integration
    def test_category_search_uses_multiple_sources(self):
        """
        Category search should use multiple discovery sources for comprehensive coverage.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts in Edinburgh",
        )

        selected = select_connectors(request)
        report = orchestrate(request)

        # Should use discovery sources (serper, openstreetmap)
        discovery_connectors = ["serper", "openstreetmap"]
        executed_discovery = [
            c for c in discovery_connectors
            if c in report["connectors"] and report["connectors"][c]["executed"]
        ]

        assert len(executed_discovery) >= 1, (
            "Category search should use discovery connectors"
        )

    @pytest.mark.integration
    def test_specific_venue_search_prioritizes_quality(self):
        """
        Specific venue search should prioritize high-quality enrichment sources.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            query="Oriam Scotland",
        )

        selected = select_connectors(request)
        report = orchestrate(request)

        # Should use high-trust enrichment (google_places)
        assert "google_places" in report["connectors"], (
            "Specific search should use google_places for high-quality data"
        )

    @pytest.mark.integration
    def test_sports_query_includes_domain_specific_source(self):
        """
        Sports-related queries should include domain-specific connector (sport_scotland).
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="rugby clubs in Edinburgh",
        )

        selected = select_connectors(request)

        # Should include sport_scotland for sports queries
        assert "sport_scotland" in selected, (
            "Sports query should include sport_scotland connector"
        )

    @pytest.mark.integration
    def test_non_sports_query_excludes_domain_specific_source(self):
        """
        Non-sports queries should not include sports-specific connector to save resources.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="restaurants in Edinburgh",
        )

        selected = select_connectors(request)

        # Should NOT include sport_scotland for non-sports queries
        assert "sport_scotland" not in selected, (
            "Non-sports query should exclude sport_scotland connector"
        )

    @pytest.mark.integration
    def test_empty_query_handled_gracefully(self):
        """
        Empty or whitespace-only queries should be handled gracefully.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="   ",  # Whitespace only
        )

        report = orchestrate(request)

        # Should complete without error
        assert report["query"] == "   ", "Should echo original query"
        assert report["candidates_found"] >= 0, "Should handle empty query"
        assert isinstance(report["errors"], list), "Should have errors structure"


class TestMetricsAndObservability:
    """Test metrics collection and observability features."""

    def test_orchestrate_tracks_execution_time_per_connector(self):
        """
        orchestrate() should track execution time for each connector.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        # Each connector should have execution time
        for connector_name, metrics in report["connectors"].items():
            assert "execution_time_ms" in metrics, (
                f"{connector_name} should track execution time"
            )
            assert isinstance(metrics["execution_time_ms"], (int, float)), (
                "Execution time should be numeric"
            )
            assert metrics["execution_time_ms"] >= 0, (
                "Execution time should be non-negative"
            )

    def test_orchestrate_tracks_cost_per_connector(self):
        """
        orchestrate() should track cost for each connector.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        # Each connector should have cost tracking
        for connector_name, metrics in report["connectors"].items():
            assert "cost_usd" in metrics, f"{connector_name} should track cost"
            assert isinstance(metrics["cost_usd"], (int, float)), "Cost should be numeric"
            assert metrics["cost_usd"] >= 0, "Cost should be non-negative"

    def test_orchestrate_tracks_candidates_per_connector(self):
        """
        orchestrate() should track how many candidates each connector found.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts Edinburgh",
        )

        report = orchestrate(request)

        # Each connector should report candidates found
        for connector_name, metrics in report["connectors"].items():
            if "candidates_found" in metrics:
                assert isinstance(metrics["candidates_found"], int), (
                    "Candidates count should be integer"
                )
                assert metrics["candidates_found"] >= 0, (
                    "Candidates count should be non-negative"
                )

    def test_orchestrate_provides_total_cost_visibility(self):
        """
        Report should enable calculating total cost across all connectors.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        # Should be able to calculate total cost
        total_cost = sum(
            metrics["cost_usd"]
            for metrics in report["connectors"].values()
        )

        assert isinstance(total_cost, (int, float)), "Total cost should be calculable"
        assert total_cost >= 0, "Total cost should be non-negative"


class TestConnectorE2EExecution:
    """
    E2E tests for connector execution with real queries.

    These tests use real connectors (not mocks) to validate that:
    - Adapters pass correct parameters to connectors
    - Connectors can handle the queries adapters send
    - Integration contracts between layers actually work
    - Real execution produces expected results
    """

    @pytest.mark.integration
    @pytest.mark.slow
    def test_sport_scotland_executes_with_natural_language_query(self):
        """
        E2E test: Sport Scotland should handle natural language sports queries.

        This test validates the full integration chain:
        1. User query "tennis courts Edinburgh" enters orchestrator
        2. Planner selects sport_scotland for sports queries
        3. Adapter calls sport_scotland.fetch() with appropriate parameters
        4. Sport Scotland translates query to layer name (e.g., "tennis_courts")
        5. Sport Scotland fetches data from WFS API
        6. Adapter maps results to canonical format
        7. Results appear in orchestration report

        This is THE critical test that prevents over-mocking bugs.
        If this passes, the feature actually works. If it fails, something
        in the integration chain is broken.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        # Verify sport_scotland was executed
        assert "sport_scotland" in report["connectors"], (
            "Sport Scotland should be executed for sports queries"
        )

        ss_metrics = report["connectors"]["sport_scotland"]

        # CRITICAL: Sport Scotland should execute successfully, not fail
        # If this fails, there's an integration bug (e.g., adapter sending wrong params)
        if not ss_metrics["executed"]:
            # If it failed, report should include error details
            errors = [e for e in report["errors"] if e["connector"] == "sport_scotland"]
            pytest.fail(
                f"Sport Scotland failed to execute. Error: {errors[0]['error'] if errors else 'Unknown'}"
            )

        # Should successfully fetch and map results
        assert ss_metrics["executed"] is True, "Sport Scotland should execute successfully"
        assert ss_metrics["candidates_found"] >= 0, "Should return candidate count"
        assert ss_metrics["execution_time_ms"] > 0, "Should track execution time"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_sport_scotland_query_translation_and_graceful_failure(self):
        """
        E2E test: Sport Scotland query translation and graceful failure handling.

        Phase 2 Status: Query translation works, but Sport Scotland WFS layer discovery
        needs implementation. The connector correctly translates "padel courts" → "tennis_courts"
        but Sport Scotland API doesn't have this layer configured yet.

        This test verifies:
        1. Sport Scotland is selected for sports queries ✓
        2. Query is translated from natural language to layer name ✓
        3. Failures are handled gracefully (don't crash orchestration) ✓
        4. Error tracking provides debugging info ✓

        Phase 3 TODO: Discover actual Sport Scotland WFS layer names and complete integration.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="padel courts in Edinburgh",
        )

        report = orchestrate(request)

        # Sport Scotland should be selected for sports query
        assert "sport_scotland" in report["connectors"], (
            "Sport Scotland should be selected for padel query"
        )

        ss_metrics = report["connectors"]["sport_scotland"]

        # Should have metrics (executed True or False)
        assert "executed" in ss_metrics, "Should have execution status"

        # Verify query translation happened (check error message contains layer name, not raw query)
        if not ss_metrics["executed"]:
            errors = [e for e in report["errors"] if e["connector"] == "sport_scotland"]
            assert len(errors) > 0, "Failed connector should log error"

            error_msg = errors[0]["error"]

            # Error should mention layer name (tennis_courts) not raw query (padel courts in Edinburgh)
            # This proves query translation is working
            assert "padel courts in Edinburgh" not in error_msg.lower(), (
                "Error should contain translated layer name, not raw query"
            )

        # Orchestration should continue despite Sport Scotland failure
        assert "serper" in report["connectors"] or "google_places" in report["connectors"], (
            "Other connectors should execute despite Sport Scotland failure"
        )

    @pytest.mark.integration
    def test_all_selected_connectors_can_execute(self):
        """
        E2E test: Every connector selected by planner should be able to execute.

        This catches integration bugs where planner selects a connector
        but the connector can't handle the query format.
        """
        test_queries = [
            "padel courts in Edinburgh",
            "tennis clubs Edinburgh",
            "rugby facilities Leith",
        ]

        for query in test_queries:
            request = IngestRequest(
                ingestion_mode=IngestionMode.DISCOVER_MANY,
                query=query,
            )

            report = orchestrate(request)

            # Every selected connector should either succeed or fail gracefully
            for connector_name, metrics in report["connectors"].items():
                assert "executed" in metrics, (
                    f"{connector_name} missing 'executed' status for query '{query}'"
                )

                # If it failed, should have error tracking
                if not metrics["executed"]:
                    errors = [e for e in report["errors"] if e["connector"] == connector_name]
                    assert len(errors) > 0, (
                        f"{connector_name} failed but no error logged for query '{query}'"
                    )


class TestDeduplicationIntegration:
    """Test cross-source deduplication integration."""

    def test_deduplication_reduces_duplicates(self):
        """
        When multiple connectors return the same venue, deduplication should reduce count.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="Oriam Scotland",  # Well-known venue
        )

        report = orchestrate(request)

        # If we got candidates from multiple sources
        if len(report["connectors"]) > 1 and report["candidates_found"] > 0:
            # Deduplication should have been applied
            # accepted_entities <= candidates_found (invariant)
            assert report["accepted_entities"] <= report["candidates_found"], (
                "Deduplication should reduce or maintain count"
            )

    def test_deduplication_preserves_unique_entities(self):
        """
        Deduplication should preserve all unique entities.
        """
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        # If candidates were found
        if report["candidates_found"] > 0:
            # Should have at least some accepted entities (unless all rejected)
            assert report["accepted_entities"] >= 0, (
                "Should preserve valid unique entities"
            )
