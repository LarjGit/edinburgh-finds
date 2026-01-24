"""
Execution Plan for Intelligent Ingestion Orchestration.

This module provides the DAG-lite structure for managing connector execution
order, dependency inference, and phase-based orchestration. The execution plan:

- Organizes connectors by ExecutionPhase (DISCOVERY -> STRUCTURED -> ENRICHMENT)
- Infers dependencies based on context.* keys in requires/provides
- Supports provider selection and tie-breaking based on trust level
- Enables parallel execution within phases

The plan enforces strict phase barriers while allowing parallelism within each phase.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from engine.orchestration.execution_context import ExecutionContext


class ExecutionPhase(Enum):
    """
    Execution phases for connector orchestration.

    Defines the three sequential phases of ingestion:
    - DISCOVERY: Initial data gathering (lowest specificity, highest coverage)
    - STRUCTURED: High-quality structured data sources
    - ENRICHMENT: Additional details and refinement

    Phase order enforces sequential execution barriers.
    """

    DISCOVERY = 1
    STRUCTURED = 2
    ENRICHMENT = 3


@dataclass
class ConnectorSpec:
    """
    Specification for a connector in the execution plan.

    Defines the metadata needed to schedule and execute a connector:
    - name: Unique identifier for the connector
    - phase: Execution phase (DISCOVERY, STRUCTURED, ENRICHMENT)
    - trust_level: Quality/reliability score (higher is better, used for tie-breaking)
    - requires: List of input dependencies (e.g., "request.query", "context.candidates")
    - provides: List of outputs produced (e.g., "context.seeds", "context.enriched_data")
    - supports_query_only: Whether connector can run with only query (no geographic constraint)

    Attributes:
        name: Unique connector identifier
        phase: ExecutionPhase enum value
        trust_level: Integer score for provider selection (higher = better)
        requires: List of required input keys (supports nested paths)
        provides: List of output keys this connector produces
        supports_query_only: True if connector can run without geographic constraints
    """

    name: str
    phase: ExecutionPhase
    trust_level: int
    requires: List[str]
    provides: List[str]
    supports_query_only: bool


@dataclass
class ConnectorNode:
    """
    Node in the execution plan DAG.

    Wraps a ConnectorSpec with inferred dependencies based on context.* requirements.
    Dependencies are determined by matching context.* keys in requires against
    the provides lists of previously added connectors.

    Attributes:
        spec: The connector specification
        dependencies: List of connector names this node depends on
    """

    spec: ConnectorSpec
    dependencies: List[str]


class ExecutionPlan:
    """
    DAG-lite execution plan for connector orchestration.

    Manages the collection of connectors and their dependencies. Automatically
    infers dependencies when connectors are added by matching context.* keys
    in requires against provides from existing connectors.

    Dependency inference rules:
    - Only context.* keys in requires create dependencies
    - request.* and query_features.* keys do NOT create dependencies
    - Duplicate dependencies are automatically eliminated
    - Connectors are executed in phase order (DISCOVERY -> STRUCTURED -> ENRICHMENT)

    Attributes:
        connectors: List of ConnectorNode objects in the plan
    """

    def __init__(self) -> None:
        """Initialize ExecutionPlan with empty connector list."""
        self.connectors: List[ConnectorNode] = []

    def add_connector(self, spec: ConnectorSpec) -> None:
        """
        Add a connector to the execution plan with automatic dependency inference.

        Analyzes the spec.requires list for context.* keys and matches them against
        the provides lists of previously added connectors. Dependencies are inferred
        only for context.* keys (not request.* or query_features.*).

        Args:
            spec: ConnectorSpec to add to the plan
        """
        dependencies = self._infer_dependencies(spec)

        # Create node and add to plan
        node = ConnectorNode(spec=spec, dependencies=dependencies)
        self.connectors.append(node)

    def _infer_dependencies(self, spec: ConnectorSpec) -> List[str]:
        """
        Infer dependencies for a connector based on context.* requirements.

        Extracts context.* keys from spec.requires and matches them against
        the provides lists of existing connectors. Only context.* keys create
        dependencies (request.* and query_features.* are ignored).

        Args:
            spec: ConnectorSpec to infer dependencies for

        Returns:
            List of connector names (dependencies), with duplicates removed
        """
        dependencies = []

        # Extract context.* keys from requires
        context_keys = [req for req in spec.requires if req.startswith("context.")]

        if not context_keys:
            return dependencies

        # For each context key, find providers in existing connectors
        for context_key in context_keys:
            for existing_node in self.connectors:
                if context_key in existing_node.spec.provides:
                    # Add dependency if not already present
                    if existing_node.spec.name not in dependencies:
                        dependencies.append(existing_node.spec.name)

        return dependencies

    def _get_best_provider(self, context_key: str) -> Optional[ConnectorNode]:
        """
        Select the best provider for a given context key using tie-breaking rules.

        Provider selection follows the spec's (-trust_level, phase_order) logic:
        1. Higher trust_level wins (primary criterion)
        2. Earlier phase (smaller phase.value) wins ties
        3. Alphabetically first name wins if trust and phase are equal (determinism)

        Args:
            context_key: The context key to find a provider for (e.g., "context.data")

        Returns:
            The best ConnectorNode that provides this key, or None if no provider exists
        """
        # Find all connectors that provide this key
        candidates = [
            node for node in self.connectors if context_key in node.spec.provides
        ]

        if not candidates:
            return None

        # Sort by: highest trust (descending), earliest phase (ascending), name (ascending)
        # Using tuple comparison: (-trust_level, phase.value, name)
        best = min(
            candidates,
            key=lambda node: (
                -node.spec.trust_level,  # Negative for descending order
                node.spec.phase.value,  # Ascending - earlier phases have smaller values
                node.spec.name,  # Alphabetical for determinism
            ),
        )

        return best

    def should_run_connector(
        self, node: ConnectorNode, context: "ExecutionContext"
    ) -> bool:
        """
        Determine if a connector should run based on aggregate gating logic.

        A connector is SKIPPED if ALL of these conditions are true:
        1. It is context-dependent (requires contains any context.* keys)
        2. candidates list is empty
        3. accepted_entities list is empty
        4. The specific required context.* keys have no data
        5. supports_query_only is False

        Otherwise, the connector should RUN.

        Args:
            node: ConnectorNode to evaluate
            context: Current ExecutionContext with runtime state

        Returns:
            True if connector should run, False if it should be skipped
        """
        # Extract context.* keys from requires
        context_keys = [
            req for req in node.spec.requires if req.startswith("context.")
        ]

        # If not context-dependent, always run
        if not context_keys:
            return True

        # If supports_query_only, can run even without context data
        if node.spec.supports_query_only:
            return True

        # Check if we have ANY data in candidates or accepted_entities
        if context.candidates or context.accepted_entities:
            return True

        # Check if ANY of the specific required context keys have data
        for context_key in context_keys:
            # Extract the attribute name from "context.key_name"
            attr_name = context_key.split(".", 1)[1]

            # Get the attribute from context
            if hasattr(context, attr_name):
                attr_value = getattr(context, attr_name)

                # Check if the attribute has data (non-empty list, dict, set, etc.)
                if attr_value:
                    return True

        # All skip conditions met: context-dependent, no candidates/entities, no required keys
        return False
