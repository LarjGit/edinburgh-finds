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

import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from engine.orchestration.execution_context import ExecutionContext
from engine.orchestration.execution_plan import (
    ConnectorSpec,
    ExecutionPhase,
    ExecutionPlan,
)
from engine.orchestration.query_features import QueryFeatures
from engine.orchestration.types import IngestRequest


@dataclass
class ScalarUpdate:
    """
    Tracks a scalar field update with metadata for conflict resolution.

    Attributes:
        value: The value being written
        trust_level: Trust level of the connector that wrote it
        connector_name: Name of the connector (for tie-breaking)
    """

    value: Any
    trust_level: int
    connector_name: str


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
        Execute all connectors in the plan with phase ordering and early stopping.

        Runs connectors in strict phase order:
        1. DISCOVERY phase (all connectors)
        2. STRUCTURED phase (all connectors)
        3. ENRICHMENT phase (all connectors)

        A shared ExecutionContext is passed through all phases, allowing
        later phases to build on results from earlier phases.

        Early stopping conditions:
        - RESOLVE_ONE: Stop when confidence >= min_confidence AND at least one entity accepted
        - DISCOVER_MANY: Stop when len(accepted_entities) >= target_entity_count
        - Budget: Stop if budget would be exceeded or has been exhausted

        Args:
            request: The ingestion request
            query_features: Extracted query features

        Returns:
            ExecutionContext with final state after all connectors execute
        """
        # Create shared context
        context = ExecutionContext()

        # Execute connectors in phase order with early stopping checks
        for phase in [
            ExecutionPhase.DISCOVERY,
            ExecutionPhase.STRUCTURED,
            ExecutionPhase.ENRICHMENT,
        ]:
            # Pre-phase budget check
            if not self._should_continue_execution(phase, request, context):
                break

            # Execute phase
            self._execute_phase(phase, request, query_features, context)

            # Post-phase early stopping check
            if not self._should_continue_execution(None, request, context):
                break

        return context

    def _execute_phase(
        self,
        phase: ExecutionPhase,
        request: IngestRequest,
        query_features: QueryFeatures,
        context: ExecutionContext,
    ) -> None:
        """
        Execute all connectors for a specific phase with deterministic merging.

        Filters connectors by phase and executes them in alphabetical order
        by name to ensure deterministic behavior. Handles scalar collisions
        using trust-based conflict resolution.

        Conflict resolution rules:
        - List fields: Append (preserve all values)
        - Dict fields: Merge by key
        - Scalar fields: Higher trust wins; on tie, last writer (alphabetical) wins

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

        # Sort by connector name for deterministic execution order
        phase_connectors.sort(key=lambda node: node.spec.name)

        # Track scalar updates for conflict resolution
        scalar_updates: Dict[str, ScalarUpdate] = {}

        # Execute each connector in alphabetical order
        for node in phase_connectors:
            # Get connector instance from registry or create new FakeConnector
            if node.spec.name in self._connector_instances:
                connector = self._connector_instances[node.spec.name]
            else:
                # Fallback: create new FakeConnector (for simple tests)
                connector = FakeConnector(name=node.spec.name, spec=node.spec)

            # Capture context state before execution
            context_snapshot_before = self._capture_scalar_fields(context)

            # Execute connector
            connector.execute(request, query_features, context)

            # Track budget spending
            context.budget_spent_usd += node.spec.estimated_cost_usd

            # Capture context state after execution
            context_snapshot_after = self._capture_scalar_fields(context)

            # Track scalar changes for conflict resolution
            for field_name, new_value in context_snapshot_after.items():
                old_value = context_snapshot_before.get(field_name)

                # If value changed, track it for merge
                if new_value != old_value:
                    existing_update = scalar_updates.get(field_name)

                    # Apply conflict resolution: higher trust wins, then alphabetical order
                    if existing_update is None:
                        # First write - accept it
                        scalar_updates[field_name] = ScalarUpdate(
                            value=new_value,
                            trust_level=node.spec.trust_level,
                            connector_name=node.spec.name,
                        )
                    else:
                        # Conflict - apply trust-based resolution
                        if node.spec.trust_level > existing_update.trust_level:
                            # Higher trust wins
                            scalar_updates[field_name] = ScalarUpdate(
                                value=new_value,
                                trust_level=node.spec.trust_level,
                                connector_name=node.spec.name,
                            )
                        elif node.spec.trust_level == existing_update.trust_level:
                            # Equal trust - last writer (alphabetically later) wins
                            if node.spec.name > existing_update.connector_name:
                                scalar_updates[field_name] = ScalarUpdate(
                                    value=new_value,
                                    trust_level=node.spec.trust_level,
                                    connector_name=node.spec.name,
                                )
                        # else: existing update has higher trust, keep it

        # Apply final scalar values to context
        self._apply_scalar_updates(context, scalar_updates)

    def _capture_scalar_fields(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Capture scalar field values from context.

        Captures non-list, non-dict fields that start with underscore (test fields).

        Args:
            context: The execution context

        Returns:
            Dict mapping field names to their values
        """
        snapshot = {}
        for field_name in dir(context):
            if field_name.startswith("_test_"):
                value = getattr(context, field_name, None)
                snapshot[field_name] = value
        return snapshot

    def _apply_scalar_updates(
        self, context: ExecutionContext, updates: Dict[str, ScalarUpdate]
    ) -> None:
        """
        Apply scalar updates to context based on conflict resolution.

        Args:
            context: The execution context to update
            updates: Dict mapping field names to ScalarUpdate objects
        """
        for field_name, update in updates.items():
            setattr(context, field_name, update.value)

    def _should_continue_execution(
        self,
        next_phase: Optional[ExecutionPhase],
        request: IngestRequest,
        context: ExecutionContext,
    ) -> bool:
        """
        Determine if execution should continue based on early stopping conditions.

        Checks three stopping conditions:
        1. Budget: Stop if executing next_phase would exceed budget (pre-check)
                  or if budget already exhausted (post-check)
        2. RESOLVE_ONE: Stop if confidence >= min_confidence AND at least one entity accepted
        3. DISCOVER_MANY: Stop if entity count >= target_entity_count

        Args:
            next_phase: The phase about to execute (None for post-phase check)
            request: The ingestion request with thresholds
            context: Current execution context

        Returns:
            True if execution should continue, False if should stop
        """
        from engine.orchestration.types import IngestionMode

        # Budget pre-check: Can we afford the next phase?
        if next_phase is not None and request.budget_usd is not None:
            # Calculate estimated cost of next phase
            phase_connectors = [
                node for node in self.plan.connectors if node.spec.phase == next_phase
            ]
            estimated_phase_cost = sum(
                node.spec.estimated_cost_usd for node in phase_connectors
            )

            # Stop if we can't afford this phase
            if context.budget_spent_usd + estimated_phase_cost > request.budget_usd:
                return False

        # Budget post-check: Have we exhausted the budget?
        if request.budget_usd is not None:
            if context.budget_spent_usd >= request.budget_usd:
                return False

        # RESOLVE_ONE early stopping
        if request.ingestion_mode == IngestionMode.RESOLVE_ONE:
            if request.min_confidence is not None:
                # Stop if we have high confidence AND at least one entity
                if (
                    context.confidence >= request.min_confidence
                    and len(context.accepted_entities) >= 1
                ):
                    return False

        # DISCOVER_MANY early stopping
        if request.ingestion_mode == IngestionMode.DISCOVER_MANY:
            if request.target_entity_count is not None:
                # Stop if we've reached the target entity count
                if len(context.accepted_entities) >= request.target_entity_count:
                    return False

        # Continue execution
        return True
