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


class TestParallelExecution:
    """Tests for parallel execution and deterministic merging."""

    def test_parallel_execution_within_phase(self):
        """
        Verify that multiple connectors within a phase can execute in parallel.

        This test verifies the infrastructure exists, not actual parallelism.
        Real parallelism would require async/threading, which is tested separately.
        """
        plan = ExecutionPlan()
        execution_log: List[str] = []

        # Create multiple connectors in same phase
        connector_a = FakeConnector(
            name="connector_a",
            spec=ConnectorSpec(
                name="connector_a",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.data_a"],
                supports_query_only=True,
            ),
            on_execute=lambda: execution_log.append("connector_a"),
        )

        connector_b = FakeConnector(
            name="connector_b",
            spec=ConnectorSpec(
                name="connector_b",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.data_b"],
                supports_query_only=True,
            ),
            on_execute=lambda: execution_log.append("connector_b"),
        )

        plan.add_connector(connector_a.spec)
        plan.add_connector(connector_b.spec)

        connector_instances = {
            "connector_a": connector_a,
            "connector_b": connector_b,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY)
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        orchestrator.execute(request, query_features)

        # Both connectors should execute
        assert len(execution_log) == 2
        assert "connector_a" in execution_log
        assert "connector_b" in execution_log

    def test_deterministic_merge_order_by_connector_name(self):
        """
        Verify that when multiple connectors modify context, updates are merged
        in deterministic order (sorted by connector name).

        This ensures reproducible behavior even with parallel execution.
        """
        plan = ExecutionPlan()

        # Create connectors that append to candidates list (names out of alphabetical order)
        connector_z = FakeConnector(
            name="z_connector",
            spec=ConnectorSpec(
                name="z_connector",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.candidates"],
                supports_query_only=True,
            ),
            on_execute=lambda ctx: ctx.candidates.append({"source": "z_connector"}),
        )

        connector_a = FakeConnector(
            name="a_connector",
            spec=ConnectorSpec(
                name="a_connector",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.candidates"],
                supports_query_only=True,
            ),
            on_execute=lambda ctx: ctx.candidates.append({"source": "a_connector"}),
        )

        connector_m = FakeConnector(
            name="m_connector",
            spec=ConnectorSpec(
                name="m_connector",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.candidates"],
                supports_query_only=True,
            ),
            on_execute=lambda ctx: ctx.candidates.append({"source": "m_connector"}),
        )

        # Add in non-alphabetical order
        plan.add_connector(connector_z.spec)
        plan.add_connector(connector_a.spec)
        plan.add_connector(connector_m.spec)

        connector_instances = {
            "z_connector": connector_z,
            "a_connector": connector_a,
            "m_connector": connector_m,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY)
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        result = orchestrator.execute(request, query_features)

        # Verify candidates are merged in alphabetical order by connector name
        assert len(result.candidates) == 3
        assert result.candidates[0]["source"] == "a_connector"
        assert result.candidates[1]["source"] == "m_connector"
        assert result.candidates[2]["source"] == "z_connector"

    def test_scalar_collision_higher_trust_wins(self):
        """
        Verify that when multiple connectors write to the same scalar field,
        the connector with higher trust_level wins.

        Scalar collision policy: trust > last writer
        """
        plan = ExecutionPlan()

        # Connector with low trust writes "low_trust_value"
        low_trust_connector = FakeConnector(
            name="low_trust",
            spec=ConnectorSpec(
                name="low_trust",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=3,  # Lower trust
                requires=["request.query"],
                provides=["context.evidence"],
                supports_query_only=True,
            ),
            on_execute=lambda ctx: setattr(ctx, "_test_scalar", "low_trust_value"),
        )

        # Connector with high trust writes "high_trust_value"
        high_trust_connector = FakeConnector(
            name="high_trust",
            spec=ConnectorSpec(
                name="high_trust",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=8,  # Higher trust
                requires=["request.query"],
                provides=["context.evidence"],
                supports_query_only=True,
            ),
            on_execute=lambda ctx: setattr(ctx, "_test_scalar", "high_trust_value"),
        )

        # Add in order that would make low_trust win if we used "last writer wins"
        plan.add_connector(high_trust_connector.spec)
        plan.add_connector(low_trust_connector.spec)

        connector_instances = {
            "low_trust": low_trust_connector,
            "high_trust": high_trust_connector,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY)
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        result = orchestrator.execute(request, query_features)

        # Higher trust should win
        assert hasattr(result, "_test_scalar")
        assert result._test_scalar == "high_trust_value"

    def test_scalar_collision_last_writer_wins_on_trust_tie(self):
        """
        Verify that when multiple connectors with EQUAL trust write to the same scalar field,
        last writer wins based on deterministic connector ordering (alphabetical).

        Scalar collision policy: trust > last writer (alphabetical)
        """
        plan = ExecutionPlan()

        # Both connectors have same trust level
        connector_a = FakeConnector(
            name="a_connector",
            spec=ConnectorSpec(
                name="a_connector",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,  # Same trust
                requires=["request.query"],
                provides=["context.evidence"],
                supports_query_only=True,
            ),
            on_execute=lambda ctx: setattr(ctx, "_test_scalar", "value_from_a"),
        )

        connector_z = FakeConnector(
            name="z_connector",
            spec=ConnectorSpec(
                name="z_connector",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,  # Same trust
                requires=["request.query"],
                provides=["context.evidence"],
                supports_query_only=True,
            ),
            on_execute=lambda ctx: setattr(ctx, "_test_scalar", "value_from_z"),
        )

        # Add in reverse alphabetical order
        plan.add_connector(connector_z.spec)
        plan.add_connector(connector_a.spec)

        connector_instances = {
            "a_connector": connector_a,
            "z_connector": connector_z,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(ingestion_mode=IngestionMode.DISCOVER_MANY)
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        result = orchestrator.execute(request, query_features)

        # Last writer in alphabetical order (z_connector) should win
        assert hasattr(result, "_test_scalar")
        assert result._test_scalar == "value_from_z"


class TestEarlyStopping:
    """Tests for early stopping based on budget and confidence thresholds."""

    def test_resolve_one_stops_when_confidence_threshold_met(self):
        """
        RESOLVE_ONE mode should stop when confidence >= min_confidence AND
        at least one entity is accepted.

        Verifies:
        - DISCOVERY phase runs
        - STRUCTURED phase runs
        - ENRICHMENT phase is skipped (early stop)
        - Final context has confidence >= min_confidence
        - Final context has at least one accepted entity
        """
        plan = ExecutionPlan()
        execution_log: List[str] = []

        # Discovery connector: adds a candidate
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

        # Structured connector: accepts entity and sets high confidence
        def structured_execute(ctx):
            execution_log.append("structured")
            if ctx.candidates:
                ctx.accept_entity(ctx.candidates[0])
            ctx.confidence = 0.9  # High confidence

        structured_connector = FakeConnector(
            name="structured",
            spec=ConnectorSpec(
                name="structured",
                phase=ExecutionPhase.STRUCTURED,
                trust_level=8,
                requires=["context.candidates"],
                provides=["context.accepted_entities"],
                supports_query_only=False,
            ),
            on_execute=structured_execute,
        )

        # Enrichment connector: should NOT run due to early stopping
        enrichment_connector = FakeConnector(
            name="enrichment",
            spec=ConnectorSpec(
                name="enrichment",
                phase=ExecutionPhase.ENRICHMENT,
                trust_level=6,
                requires=["context.accepted_entities"],
                provides=["context.enriched"],
                supports_query_only=False,
            ),
            on_execute=lambda: execution_log.append("enrichment"),
        )

        plan.add_connector(discovery_connector.spec)
        plan.add_connector(structured_connector.spec)
        plan.add_connector(enrichment_connector.spec)

        connector_instances = {
            "discovery": discovery_connector,
            "structured": structured_connector,
            "enrichment": enrichment_connector,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(
            ingestion_mode=IngestionMode.RESOLVE_ONE,
            min_confidence=0.8,  # Threshold
        )
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        result = orchestrator.execute(request, query_features)

        # Verify early stop: enrichment should NOT have executed
        assert "structured" in execution_log
        assert "enrichment" not in execution_log

        # Verify stopping conditions were met
        assert hasattr(result, "confidence")
        assert result.confidence >= 0.8
        assert len(result.accepted_entities) >= 1

    def test_discover_many_stops_when_entity_count_reached(self):
        """
        DISCOVER_MANY mode should stop when len(accepted_entities) >= target_entity_count.

        Verifies:
        - Execution stops after reaching target count
        - Remaining phases are skipped
        - Final entity count >= target_entity_count
        """
        plan = ExecutionPlan()
        execution_log: List[str] = []

        # Discovery connector: adds multiple candidates
        def discovery_execute(ctx):
            execution_log.append("discovery")
            ctx.candidates.extend([
                {"name": "entity_1", "lat": 1.0, "lng": 1.0},
                {"name": "entity_2", "lat": 2.0, "lng": 2.0},
                {"name": "entity_3", "lat": 3.0, "lng": 3.0},
            ])

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
            on_execute=discovery_execute,
        )

        # Structured connector: accepts entities (reaches target count)
        def structured_execute(ctx):
            execution_log.append("structured")
            for candidate in ctx.candidates:
                ctx.accept_entity(candidate)

        structured_connector = FakeConnector(
            name="structured",
            spec=ConnectorSpec(
                name="structured",
                phase=ExecutionPhase.STRUCTURED,
                trust_level=8,
                requires=["context.candidates"],
                provides=["context.accepted_entities"],
                supports_query_only=False,
            ),
            on_execute=structured_execute,
        )

        # Enrichment connector: should NOT run (early stop)
        enrichment_connector = FakeConnector(
            name="enrichment",
            spec=ConnectorSpec(
                name="enrichment",
                phase=ExecutionPhase.ENRICHMENT,
                trust_level=6,
                requires=["context.accepted_entities"],
                provides=["context.enriched"],
                supports_query_only=False,
            ),
            on_execute=lambda: execution_log.append("enrichment"),
        )

        plan.add_connector(discovery_connector.spec)
        plan.add_connector(structured_connector.spec)
        plan.add_connector(enrichment_connector.spec)

        connector_instances = {
            "discovery": discovery_connector,
            "structured": structured_connector,
            "enrichment": enrichment_connector,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            target_entity_count=2,  # Stop after 2 entities
        )
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        result = orchestrator.execute(request, query_features)

        # Verify early stop: enrichment should NOT have executed
        assert "discovery" in execution_log
        assert "structured" in execution_log
        assert "enrichment" not in execution_log

        # Verify stopping condition was met
        assert len(result.accepted_entities) >= 2

    def test_budget_pre_check_prevents_execution(self):
        """
        Budget pre-check should prevent connector execution if budget would be exceeded.

        Verifies:
        - Expensive connector is skipped when budget is low
        - Budget tracking is updated correctly
        """
        plan = ExecutionPlan()
        execution_log: List[str] = []

        # Expensive discovery connector (costs $10)
        discovery_connector = FakeConnector(
            name="expensive_discovery",
            spec=ConnectorSpec(
                name="expensive_discovery",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.candidates"],
                supports_query_only=True,
                estimated_cost_usd=10.0,  # Expensive
            ),
            on_execute=lambda: execution_log.append("expensive_discovery"),
        )

        plan.add_connector(discovery_connector.spec)

        connector_instances = {
            "expensive_discovery": discovery_connector,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            budget_usd=5.0,  # Budget too low
        )
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        result = orchestrator.execute(request, query_features)

        # Verify connector was skipped due to budget
        assert "expensive_discovery" not in execution_log

        # Verify budget tracking exists
        assert hasattr(result, "budget_spent_usd")
        assert result.budget_spent_usd <= 5.0

    def test_budget_post_check_stops_after_phase(self):
        """
        Budget post-check should stop execution after a phase if budget is exhausted.

        Verifies:
        - First phase executes and consumes budget
        - Subsequent phases are skipped due to budget exhaustion
        - Budget spent is tracked correctly
        """
        plan = ExecutionPlan()
        execution_log: List[str] = []

        # Discovery connector: costs $8 (most of budget)
        def discovery_execute(ctx):
            execution_log.append("discovery")
            ctx.candidates.append({"name": "entity_1"})

        discovery_connector = FakeConnector(
            name="discovery",
            spec=ConnectorSpec(
                name="discovery",
                phase=ExecutionPhase.DISCOVERY,
                trust_level=5,
                requires=["request.query"],
                provides=["context.candidates"],
                supports_query_only=True,
                estimated_cost_usd=8.0,
            ),
            on_execute=discovery_execute,
        )

        # Structured connector: costs $5 (would exceed budget)
        structured_connector = FakeConnector(
            name="structured",
            spec=ConnectorSpec(
                name="structured",
                phase=ExecutionPhase.STRUCTURED,
                trust_level=8,
                requires=["context.candidates"],
                provides=["context.accepted_entities"],
                supports_query_only=False,
                estimated_cost_usd=5.0,
            ),
            on_execute=lambda: execution_log.append("structured"),
        )

        plan.add_connector(discovery_connector.spec)
        plan.add_connector(structured_connector.spec)

        connector_instances = {
            "discovery": discovery_connector,
            "structured": structured_connector,
        }

        orchestrator = Orchestrator(plan=plan, connector_instances=connector_instances)
        request = IngestRequest(
            ingestion_mode=IngestionMode.DISCOVER_MANY,
            budget_usd=10.0,  # Total budget
        )
        query_features = QueryFeatures(
            looks_like_category_search=False,
            has_geo_intent=False,
        )

        result = orchestrator.execute(request, query_features)

        # Verify discovery ran but structured was skipped
        assert "discovery" in execution_log
        assert "structured" not in execution_log

        # Verify budget tracking
        assert hasattr(result, "budget_spent_usd")
        assert result.budget_spent_usd <= 10.0
