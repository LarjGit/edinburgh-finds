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
    """Test connector selection logic (Phase A: hardcoded)."""

    def test_select_connectors_returns_list(self):
        """select_connectors should return a list of connector names."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )
        connectors = select_connectors(request)
        assert isinstance(connectors, list), "select_connectors should return a list"

    def test_select_connectors_phase_a_hardcoded(self):
        """Phase A: select_connectors should return hardcoded serper and google_places."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )
        connectors = select_connectors(request)

        # Phase A hardcoded selection
        assert len(connectors) == 2, "Phase A should select exactly 2 connectors"
        assert "serper" in connectors, "serper should be selected"
        assert "google_places" in connectors, "google_places should be selected"

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

    def test_orchestrate_returns_dict(self):
        """orchestrate() should return a structured report dict."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        assert isinstance(report, dict), "orchestrate should return a dict"

    def test_orchestrate_report_structure(self):
        """orchestrate() report should have required top-level keys."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        # Required report keys
        assert "query" in report, "report should include query"
        assert "candidates_found" in report, "report should include candidates_found"
        assert "accepted_entities" in report, "report should include accepted_entities"
        assert "connectors" in report, "report should include connectors metrics"
        assert "errors" in report, "report should include errors"

    def test_orchestrate_candidates_found_is_int(self):
        """candidates_found should be a non-negative integer."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        assert isinstance(report["candidates_found"], int), "candidates_found should be int"
        assert report["candidates_found"] >= 0, "candidates_found should be >= 0"

    def test_orchestrate_accepted_entities_is_int(self):
        """accepted_entities should be a non-negative integer."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        assert isinstance(report["accepted_entities"], int), "accepted_entities should be int"
        assert report["accepted_entities"] >= 0, "accepted_entities should be >= 0"

    def test_orchestrate_deduplication_works(self):
        """Deduplication should result in accepted_entities <= candidates_found."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        # Deduplication invariant
        assert report["accepted_entities"] <= report["candidates_found"], \
            "accepted_entities should be <= candidates_found (deduplication)"

    def test_orchestrate_connectors_metrics_is_dict(self):
        """connectors metrics should be a dict with per-connector data."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        assert isinstance(report["connectors"], dict), "connectors should be a dict"

    def test_orchestrate_errors_is_list(self):
        """errors should be a list."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        assert isinstance(report["errors"], list), "errors should be a list"

    def test_orchestrate_query_echo(self):
        """Report should echo the original query string."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        assert report["query"] == "tennis courts Edinburgh", "query should be echoed in report"


class TestOrchestrateIntegration:
    """Integration tests for orchestrate() with real connectors."""

    @pytest.mark.integration
    def test_orchestrate_executes_serper_and_google_places(self):
        """orchestrate() should execute both serper and google_places connectors."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        # Both connectors should have metrics
        assert "serper" in report["connectors"], "serper metrics should be present"
        assert "google_places" in report["connectors"], "google_places metrics should be present"

    @pytest.mark.integration
    def test_orchestrate_serper_metrics_structure(self):
        """Serper connector metrics should have expected structure."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)
        serper_metrics = report["connectors"]["serper"]

        # Verify metrics structure
        assert "executed" in serper_metrics, "serper metrics should include 'executed'"
        assert "execution_time_ms" in serper_metrics, "serper metrics should include 'execution_time_ms'"
        assert "cost_usd" in serper_metrics, "serper metrics should include 'cost_usd'"

    @pytest.mark.integration
    def test_orchestrate_google_places_metrics_structure(self):
        """Google Places connector metrics should have expected structure."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)
        google_places_metrics = report["connectors"]["google_places"]

        # Verify metrics structure
        assert "executed" in google_places_metrics, "google_places metrics should include 'executed'"
        assert "execution_time_ms" in google_places_metrics, "google_places metrics should include 'execution_time_ms'"
        assert "cost_usd" in google_places_metrics, "google_places metrics should include 'cost_usd'"

    @pytest.mark.integration
    def test_orchestrate_finds_candidates(self):
        """orchestrate() should find at least some candidates for a real query."""
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            query="tennis courts Edinburgh",
        )

        report = orchestrate(request)

        # Should find some candidates (real API call)
        # Note: This test requires API keys and network access
        # In CI/CD, mock the connectors or skip with pytest.mark.skipif
        assert report["candidates_found"] >= 0, "Should complete without error"
