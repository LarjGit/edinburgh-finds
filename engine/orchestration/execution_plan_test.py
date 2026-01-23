"""
Tests for execution plan and connector node structures.

Validates the DAG-lite structure for managing connector execution order,
dependency inference, and phase-based orchestration.
"""

import pytest
from engine.orchestration.execution_plan import (
    ConnectorNode,
    ExecutionPlan,
    ConnectorSpec,
    ExecutionPhase,
)


class TestConnectorNode:
    """Tests for ConnectorNode structure."""

    def test_connector_node_creation(self):
        """Test that ConnectorNode can be created with required fields."""
        spec = ConnectorSpec(
            name="google_places",
            phase=ExecutionPhase.STRUCTURED,
            trust_level=9,
            requires=["request.bounding_box", "query_features.has_geo_intent"],
            provides=["context.candidates"],
            supports_query_only=True,
        )

        node = ConnectorNode(spec=spec, dependencies=[])

        assert node.spec.name == "google_places"
        assert node.spec.phase == ExecutionPhase.STRUCTURED
        assert node.spec.trust_level == 9
        assert node.spec.supports_query_only is True
        assert node.dependencies == []

    def test_connector_node_with_dependencies(self):
        """Test that ConnectorNode can track dependencies."""
        spec = ConnectorSpec(
            name="enrichment_connector",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=5,
            requires=["context.accepted_entities"],
            provides=["context.enriched_data"],
            supports_query_only=False,
        )

        node = ConnectorNode(spec=spec, dependencies=["google_places"])

        assert node.dependencies == ["google_places"]


class TestConnectorSpec:
    """Tests for ConnectorSpec dataclass."""

    def test_connector_spec_required_fields(self):
        """Test that ConnectorSpec requires all mandatory fields."""
        spec = ConnectorSpec(
            name="test_connector",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
        )

        assert spec.name == "test_connector"
        assert spec.phase == ExecutionPhase.DISCOVERY
        assert spec.trust_level == 7
        assert spec.requires == ["request.query"]
        assert spec.provides == ["context.candidates"]
        assert spec.supports_query_only is True

    def test_connector_spec_empty_requires(self):
        """Test that ConnectorSpec can have empty requires list."""
        spec = ConnectorSpec(
            name="discovery_connector",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=8,
            requires=[],
            provides=["context.seeds"],
            supports_query_only=False,
        )

        assert spec.requires == []


class TestExecutionPlan:
    """Tests for ExecutionPlan DAG-lite structure."""

    def test_execution_plan_initialization(self):
        """Test that ExecutionPlan initializes with empty connector list."""
        plan = ExecutionPlan()

        assert plan.connectors == []

    def test_add_connector_simple(self):
        """Test adding a connector with no dependencies."""
        plan = ExecutionPlan()

        spec = ConnectorSpec(
            name="discovery_connector",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=8,
            requires=["request.query"],
            provides=["context.seeds"],
            supports_query_only=True,
        )

        plan.add_connector(spec)

        assert len(plan.connectors) == 1
        assert plan.connectors[0].spec.name == "discovery_connector"
        assert plan.connectors[0].dependencies == []

    def test_add_connector_with_context_dependency(self):
        """Test that add_connector infers dependencies from context.* keys."""
        plan = ExecutionPlan()

        # Add first connector that provides context.candidates
        discovery_spec = ConnectorSpec(
            name="discovery_connector",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=8,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
        )
        plan.add_connector(discovery_spec)

        # Add second connector that requires context.candidates
        enrichment_spec = ConnectorSpec(
            name="enrichment_connector",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=5,
            requires=["context.candidates", "request.min_confidence"],
            provides=["context.enriched_data"],
            supports_query_only=False,
        )
        plan.add_connector(enrichment_spec)

        assert len(plan.connectors) == 2
        # The enrichment connector should have dependency on discovery connector
        enrichment_node = plan.connectors[1]
        assert "discovery_connector" in enrichment_node.dependencies

    def test_add_connector_ignores_non_context_dependencies(self):
        """Test that only context.* keys create dependencies."""
        plan = ExecutionPlan()

        # First connector provides context.candidates
        first_spec = ConnectorSpec(
            name="first_connector",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=8,
            requires=["request.query"],
            provides=["context.candidates"],
            supports_query_only=True,
        )
        plan.add_connector(first_spec)

        # Second connector requires request.* and query_features.* (no context.*)
        second_spec = ConnectorSpec(
            name="second_connector",
            phase=ExecutionPhase.STRUCTURED,
            trust_level=9,
            requires=["request.bounding_box", "query_features.has_geo_intent"],
            provides=["context.structured_data"],
            supports_query_only=True,
        )
        plan.add_connector(second_spec)

        # Second connector should have no dependencies (no context.* in requires)
        second_node = plan.connectors[1]
        assert second_node.dependencies == []

    def test_add_connector_multiple_context_dependencies(self):
        """Test connector with multiple context.* dependencies."""
        plan = ExecutionPlan()

        # Add connector A that provides context.seeds
        spec_a = ConnectorSpec(
            name="connector_a",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=8,
            requires=[],
            provides=["context.seeds"],
            supports_query_only=True,
        )
        plan.add_connector(spec_a)

        # Add connector B that provides context.candidates
        spec_b = ConnectorSpec(
            name="connector_b",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=[],
            provides=["context.candidates"],
            supports_query_only=True,
        )
        plan.add_connector(spec_b)

        # Add connector C that requires both context.seeds and context.candidates
        spec_c = ConnectorSpec(
            name="connector_c",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=5,
            requires=["context.seeds", "context.candidates"],
            provides=["context.enriched_data"],
            supports_query_only=False,
        )
        plan.add_connector(spec_c)

        # Connector C should depend on both A and B
        connector_c_node = plan.connectors[2]
        assert "connector_a" in connector_c_node.dependencies
        assert "connector_b" in connector_c_node.dependencies

    def test_add_connector_no_duplicate_dependencies(self):
        """Test that duplicate dependencies are not added."""
        plan = ExecutionPlan()

        # Add provider connector
        provider_spec = ConnectorSpec(
            name="provider",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=8,
            requires=[],
            provides=["context.data_a", "context.data_b"],
            supports_query_only=True,
        )
        plan.add_connector(provider_spec)

        # Add consumer that requires both data_a and data_b from same provider
        consumer_spec = ConnectorSpec(
            name="consumer",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=5,
            requires=["context.data_a", "context.data_b"],
            provides=["context.result"],
            supports_query_only=False,
        )
        plan.add_connector(consumer_spec)

        # Consumer should only have provider once in dependencies
        consumer_node = plan.connectors[1]
        assert consumer_node.dependencies.count("provider") == 1


class TestExecutionPhase:
    """Tests for ExecutionPhase enum."""

    def test_execution_phases_defined(self):
        """Test that all execution phases are defined."""
        assert ExecutionPhase.DISCOVERY
        assert ExecutionPhase.STRUCTURED
        assert ExecutionPhase.ENRICHMENT

    def test_phase_order(self):
        """Test that phases have correct ordering values."""
        # Phases should be ordered: DISCOVERY -> STRUCTURED -> ENRICHMENT
        assert ExecutionPhase.DISCOVERY.value < ExecutionPhase.STRUCTURED.value
        assert ExecutionPhase.STRUCTURED.value < ExecutionPhase.ENRICHMENT.value
