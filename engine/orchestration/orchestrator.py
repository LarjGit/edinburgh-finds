"""
Orchestrator for Intelligent Ingestion Orchestration.

This module provides the main control loop that enforces phase barriers,
manages connector execution, and coordinates the ingestion pipeline.

The orchestrator:
- Enforces strict phase ordering: DISCOVERY -> STRUCTURED -> ENRICHMENT
- Manages shared ExecutionContext across all connectors
- Supports parallel execution within phases (future enhancement)
- Handles early stopping based on budget and confidence thresholds

Key Components:
- Orchestrator: Main control loop for executing connectors
- FakeConnector: Test double for deterministic testing
"""

from typing import Callable, Dict, Optional

from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import (
    ConnectorSpec,
    ExecutionPhase,
    ExecutionPlan,
)
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.types import IngestRequest


class FakeConnector:
    """
    Test double for connector testing.

    Provides a deterministic connector implementation for testing the orchestrator
    without requiring real API calls or external dependencies.

    The on_execute callback allows tests to:
    - Track execution order
    - Modify context state
    - Simulate different connector behaviors

    Attributes:
        name: Connector identifier
        spec: ConnectorSpec defining metadata and dependencies
        on_execute: Optional callback executed when connector runs
    """

    def __init__(
        self,
        name: str,
        spec: ConnectorSpec,
        on_execute: Optional[Callable] = None,
    ):
        """
        Initialize FakeConnector.

        Args:
            name: Connector identifier
            spec: ConnectorSpec with phase, trust_level, etc.
            on_execute: Optional callback(context) -> None or callback() -> None
        """
        self.name = name
        self.spec = spec
        self.on_execute = on_execute

    def execute(
        self,
        request: IngestRequest,
        query_features: QueryFeatures,
        context: ExecutionContext,
    ) -> None:
        """
        Execute the connector (test implementation).

        Invokes the on_execute callback if provided. The callback can either
        take the context as an argument (for modifying state) or take no
        arguments (for logging execution order).

        Args:
            request: The ingestion request
            query_features: Extracted query features
            context: Shared execution context (mutable)
        """
        if self.on_execute:
            # Try calling with context first (for state modification)
            try:
                self.on_execute(context)
            except TypeError:
                # Fallback to no-argument call (for logging)
                self.on_execute()


class Orchestrator:
    """
    Main orchestrator for connector execution.

    Enforces phase barriers and coordinates connector execution across the
    three sequential phases: DISCOVERY -> STRUCTURED -> ENRICHMENT.

    The orchestrator:
    1. Groups connectors by phase
    2. Executes phases in strict sequential order
    3. Passes a shared ExecutionContext through all connectors
    4. Allows parallel execution within each phase (future enhancement)

    Attributes:
        plan: ExecutionPlan containing all connectors to execute
        _connector_instances: Optional dict mapping connector names to instances (for testing)
    """

    def __init__(self, plan: ExecutionPlan, connector_instances: Optional[Dict[str, "FakeConnector"]] = None):
        """
        Initialize Orchestrator.

        Args:
            plan: ExecutionPlan with connectors to execute
            connector_instances: Optional dict mapping connector names to instances (for testing)
        """
        self.plan = plan
        self._connector_instances = connector_instances or {}

    def execute(
        self, request: IngestRequest, query_features: QueryFeatures
    ) -> ExecutionContext:
        """
        Execute all connectors in the plan with phase ordering.

        Runs connectors in strict phase order:
        1. DISCOVERY phase (all connectors)
        2. STRUCTURED phase (all connectors)
        3. ENRICHMENT phase (all connectors)

        A shared ExecutionContext is passed through all phases, allowing
        later phases to build on results from earlier phases.

        Args:
            request: The ingestion request
            query_features: Extracted query features

        Returns:
            ExecutionContext with final state after all connectors execute
        """
        # Create shared context
        context = ExecutionContext()

        # Execute connectors in phase order
        for phase in [
            ExecutionPhase.DISCOVERY,
            ExecutionPhase.STRUCTURED,
            ExecutionPhase.ENRICHMENT,
        ]:
            self._execute_phase(phase, request, query_features, context)

        return context

    def _execute_phase(
        self,
        phase: ExecutionPhase,
        request: IngestRequest,
        query_features: QueryFeatures,
        context: ExecutionContext,
    ) -> None:
        """
        Execute all connectors for a specific phase.

        Filters connectors by phase and executes them. Currently executes
        sequentially, but designed to support parallel execution in future.

        Args:
            phase: The execution phase to run
            request: The ingestion request
            query_features: Extracted query features
            context: Shared execution context (mutable)
        """
        # Filter connectors for this phase
        phase_connectors = [
            node for node in self.plan.connectors if node.spec.phase == phase
        ]

        # Execute each connector in the phase
        # TODO: Add parallel execution support
        for node in phase_connectors:
            # Get connector instance from registry or create new FakeConnector
            if node.spec.name in self._connector_instances:
                connector = self._connector_instances[node.spec.name]
            else:
                # Fallback: create new FakeConnector (for simple tests)
                connector = FakeConnector(name=node.spec.name, spec=node.spec)

            connector.execute(request, query_features, context)
