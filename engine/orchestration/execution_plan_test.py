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


class TestProviderSelection:
    """Tests for provider selection and tie-breaking logic."""

    def test_get_best_provider_single_provider(self):
        """Test that single provider is selected."""
        plan = ExecutionPlan()

        spec = ConnectorSpec(
            name="only_provider",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=[],
            provides=["context.data"],
            supports_query_only=True,
        )
        plan.add_connector(spec)

        best = plan._get_best_provider("context.data")
        assert best.spec.name == "only_provider"

    def test_get_best_provider_higher_trust_wins(self):
        """Test that provider with higher trust level is selected."""
        plan = ExecutionPlan()

        # Lower trust provider
        spec_low = ConnectorSpec(
            name="low_trust",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=5,
            requires=[],
            provides=["context.data"],
            supports_query_only=True,
        )
        plan.add_connector(spec_low)

        # Higher trust provider
        spec_high = ConnectorSpec(
            name="high_trust",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=9,
            requires=[],
            provides=["context.data"],
            supports_query_only=True,
        )
        plan.add_connector(spec_high)

        best = plan._get_best_provider("context.data")
        assert best.spec.name == "high_trust"
        assert best.spec.trust_level == 9

    def test_get_best_provider_earlier_phase_wins_tie(self):
        """Test that earlier phase wins when trust levels are equal."""
        plan = ExecutionPlan()

        # Later phase (ENRICHMENT)
        spec_enrichment = ConnectorSpec(
            name="enrichment_provider",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=7,
            requires=[],
            provides=["context.data"],
            supports_query_only=False,
        )
        plan.add_connector(spec_enrichment)

        # Earlier phase (STRUCTURED)
        spec_structured = ConnectorSpec(
            name="structured_provider",
            phase=ExecutionPhase.STRUCTURED,
            trust_level=7,
            requires=[],
            provides=["context.data"],
            supports_query_only=True,
        )
        plan.add_connector(spec_structured)

        best = plan._get_best_provider("context.data")
        assert best.spec.name == "structured_provider"
        assert best.spec.phase == ExecutionPhase.STRUCTURED

    def test_get_best_provider_trust_beats_phase(self):
        """Test that higher trust beats earlier phase."""
        plan = ExecutionPlan()

        # Earlier phase but lower trust
        spec_early = ConnectorSpec(
            name="early_low_trust",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=5,
            requires=[],
            provides=["context.data"],
            supports_query_only=True,
        )
        plan.add_connector(spec_early)

        # Later phase but higher trust
        spec_late = ConnectorSpec(
            name="late_high_trust",
            phase=ExecutionPhase.ENRICHMENT,
            trust_level=9,
            requires=[],
            provides=["context.data"],
            supports_query_only=False,
        )
        plan.add_connector(spec_late)

        best = plan._get_best_provider("context.data")
        assert best.spec.name == "late_high_trust"
        assert best.spec.trust_level == 9

    def test_get_best_provider_same_trust_and_phase_deterministic(self):
        """Test that selection is deterministic when trust and phase are equal."""
        plan = ExecutionPlan()

        # First provider
        spec_a = ConnectorSpec(
            name="provider_a",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=[],
            provides=["context.data"],
            supports_query_only=True,
        )
        plan.add_connector(spec_a)

        # Second provider (identical trust and phase)
        spec_b = ConnectorSpec(
            name="provider_b",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=[],
            provides=["context.data"],
            supports_query_only=True,
        )
        plan.add_connector(spec_b)

        # Should select deterministically (by name, alphabetically)
        best = plan._get_best_provider("context.data")
        assert best.spec.name == "provider_a"

    def test_get_best_provider_no_provider_returns_none(self):
        """Test that None is returned when no provider exists."""
        plan = ExecutionPlan()

        # Add connector that doesn't provide the requested key
        spec = ConnectorSpec(
            name="other_provider",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=7,
            requires=[],
            provides=["context.other_data"],
            supports_query_only=True,
        )
        plan.add_connector(spec)

        best = plan._get_best_provider("context.data")
        assert best is None

    def test_get_best_provider_multiple_provides_from_same_connector(self):
        """Test that connector providing multiple keys can be selected."""
        plan = ExecutionPlan()

        spec = ConnectorSpec(
            name="multi_provider",
            phase=ExecutionPhase.DISCOVERY,
            trust_level=8,
            requires=[],
            provides=["context.data_a", "context.data_b", "context.data_c"],
            supports_query_only=True,
        )
        plan.add_connector(spec)

        # Should find provider for any of its provided keys
        best_a = plan._get_best_provider("context.data_a")
        best_b = plan._get_best_provider("context.data_b")
        best_c = plan._get_best_provider("context.data_c")

        assert best_a.spec.name == "multi_provider"
        assert best_b.spec.name == "multi_provider"
        assert best_c.spec.name == "multi_provider"
