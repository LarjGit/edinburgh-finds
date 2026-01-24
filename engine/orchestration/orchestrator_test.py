"""
Tests for Orchestrator core loop and phase-ordered execution.

This test suite verifies:
- Phase barrier enforcement (DISCOVERY -> STRUCTURED -> ENRICHMENT)
- FakeConnector interface for deterministic testing
- Basic orchestrator structure and execute method
"""

from dataclasses import dataclass
from typing import List

import pytest

from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import (
    ConnectorSpec,
    ExecutionPhase,
    ExecutionPlan,
)
from engine.orchestration.orchestrator import FakeConnector, Orchestrator
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.types import IngestRequest, IngestionMode


@dataclass
class FakeConnectorResult:
    """
    Result from a FakeConnector execution.

    Tracks what the connector did during execution for test verification.

    Attributes:
        connector_name: Name of the connector that ran
        phase: Phase the connector belongs to
        candidates_added: Number of candidates added to context
        context_updates: Dict of context updates made
    """

    connector_name: str
    phase: ExecutionPhase
    candidates_added: int = 0
    context_updates: dict = None

    def __post_init__(self):
        if self.context_updates is None:
            self.context_updates = {}


class TestFakeConnector:
    """Tests for FakeConnector test interface."""

    def test_fake_connector_exists(self):
        """Verify FakeConnector class exists and can be instantiated."""
        # This should fail until we implement FakeConnector
        connector = FakeConnector(
            name="test_connector",
            spec=ConnectorSpec(
                name="test_connector",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.candidates"],
                supports_query_only=True,
            ),
        )
        assert connector.name == "test_connector"
        assert connector.spec.phase == ExecutionPhase.DISCOVERY

    def test_fake_connector_execute_method(self):
        """Verify FakeConnector has an execute method."""
        connector = FakeConnector(
            name="test_connector",
            spec=ConnectorSpec(
                name="test_connector",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.candidates"],
                supports_query_only=True,
            ),
        )

        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY)
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )
        context = ExecutionContext()

        # Should not raise
        connector.execute(request, query_features, context)


class TestOrchestrator:
    """Tests for Orchestrator core loop."""

    def test_orchestrator_exists(self):
        """Verify Orchestrator class exists and can be instantiated."""
        plan = ExecutionPlan()
        orchestrator = Orchestrator(plan=plan)
        assert orchestrator.plan is plan

    def test_orchestrator_execute_method_exists(self):
        """Verify Orchestrator has an execute method with correct signature."""
        plan = ExecutionPlan()
        orchestrator = Orchestrator(plan=plan)

        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY)
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        # Should not raise (even if it returns None for now)
        result = orchestrator.execute(request, query_features)
        # Result should be an ExecutionContext
        assert isinstance(result, ExecutionContext)

    def test_orchestrator_enforces_phase_order(self):
        """
        Verify orchestrator executes connectors in phase order: DISCOVERY -> STRUCTURED -> ENRICHMENT.

        Creates connectors in mixed order and verifies they execute in correct phase sequence.
        """
        plan = ExecutionPlan()

        # Track execution order
        execution_log: List[str] = []

        # Create FakeConnectors that log when they execute
        def make_logging_connector(name: str, phase: ExecutionPhase):
            connector = FakeConnector(
                name=name,
                spec=ConnectorSpec(
                    name=name,
                    phase=phase,
                    trust_level=5,
                    requires=["request.query"],
                    provides=[f"context.{name}_data"],
                    supports_query_only=True,
                ),
                on_execute=lambda: execution_log.append(name),
            )
            return connector

        # Add connectors in WRONG order (ENRICHMENT, DISCOVERY, STRUCTURED)
        enrichment_connector = make_logging_connector("enrichment_1", ExecutionPhase.ENRICHMENT)
        discovery_connector = make_logging_connector("discovery_1", ExecutionPhase.DISCOVERY)
        structured_connector = make_logging_connector("structured_1", ExecutionPhase.STRUCTURED)

        # Add to plan in wrong order
        plan.add_connector(enrichment_connector.spec)
        plan.add_connector(discovery_connector.spec)
        plan.add_connector(structured_connector.spec)

        # Register connector instances
        connector_instances = {
            "enrichment_1": enrichment_connector,
            "discovery_1": discovery_connector,
            "structured_1": structured_connector,
        }

        # Execute
        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY)
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        orchestrator.execute(request, query_features)

        # Verify execution order: DISCOVERY -> STRUCTURED -> ENRICHMENT
        assert execution_log == ["discovery_1", "structured_1", "enrichment_1"]

    def test_orchestrator_executes_all_connectors_in_phase(self):
        """
        Verify orchestrator executes all connectors within a phase.

        Multiple connectors in same phase should all execute.
        """
        plan = ExecutionPlan()
        execution_log: List[str] = []

        def make_logging_connector(name: str, phase: ExecutionPhase):
            return FakeConnector(
                name=name,
                spec=ConnectorSpec(
                    name=name,
                    phase=phase,
                    trust_level=5,
                    requires=["request.query"],
                    provides=[f"context.{name}_data"],
                    supports_query_only=True,
                ),
                on_execute=lambda: execution_log.append(name),
            )

        # Add multiple connectors in DISCOVERY phase
        connector_1 = make_logging_connector("discovery_1", ExecutionPhase.DISCOVERY)
        connector_2 = make_logging_connector("discovery_2", ExecutionPhase.DISCOVERY)
        connector_3 = make_logging_connector("discovery_3", ExecutionPhase.DISCOVERY)

        plan.add_connector(connector_1.spec)
        plan.add_connector(connector_2.spec)
        plan.add_connector(connector_3.spec)

        # Register connector instances
        connector_instances = {
            "discovery_1": connector_1,
            "discovery_2": connector_2,
            "discovery_3": connector_3,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY)
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        orchestrator.execute(request, query_features)

        # All three discovery connectors should execute
        assert len(execution_log) == 3
        assert "discovery_1" in execution_log
        assert "discovery_2" in execution_log
        assert "discovery_3" in execution_log

    def test_orchestrator_passes_context_between_phases(self):
        """
        Verify orchestrator passes context state from one phase to the next.

        Data added to context in DISCOVERY should be available in STRUCTURED phase.
        """
        plan = ExecutionPlan()

        # Discovery connector adds a candidate
        discovery_connector = FakeConnector(
            name="discovery",
            spec=ConnectorSpec(
                name="discovery",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.candidates"],
                supports_query_only=True,
            ),
            on_execute=lambda ctx: ctx.candidates.append({"name": "test_entity"}),
        )

        # Structured connector reads the candidate
        structured_results = []
        structured_connector = FakeConnector(
            name="structured",
            spec=ConnectorSpec(
                name="structured",
                phase=ExecutionPhase.STRUCTURED,
                trust_level=8,
                requires=["context.candidates"],
                provides=["context.enriched"],
                supports_query_only=False,
            ),
            on_execute=lambda ctx: structured_results.append(len(ctx.candidates)),
        )

        plan.add_connector(discovery_connector.spec)
        plan.add_connector(structured_connector.spec)

        # Register connector instances
        connector_instances = {
            "discovery": discovery_connector,
            "structured": structured_connector,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY)
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        result = orchestrator.execute(request, query_features)

        # Verify structured connector saw the candidate from discovery
        assert len(structured_results) == 1
        assert structured_results[0] == 1
        # Verify final context has the candidate
        assert len(result.candidates) == 1
        assert result.candidates[0]["name"] == "test_entity"
