"""
Execution Context for Intelligent Ingestion Orchestration.

This module provides the ExecutionContext class, which holds shared state
during orchestration execution. It serves as a container for:
- candidates: Entities discovered but not yet accepted
- accepted_entities: Entities that passed deduplication
- accepted_entity_keys: Set of keys for deduplication tracking
- evidence: Supporting data collected during discovery
- seeds: Initial seed data (IDs, known entities)

All containers are mutable to allow state updates during orchestration.
"""

from typing import Any, Dict, List, Set


class ExecutionContext:
    """
    Shared state container for orchestration execution.

    Holds mutable collections that are updated throughout the orchestration
    lifecycle. All fields are initialized as empty containers.

    Attributes:
        candidates: List of candidate entities discovered during ingestion
        accepted_entities: List of entities accepted after deduplication
        accepted_entity_keys: Set of unique keys for accepted entities
        evidence: Dict of supporting evidence collected during discovery
        seeds: Dict of initial seed data (IDs, known entities)
    """

    def __init__(self) -> None:
        """Initialize ExecutionContext with empty containers."""
        self.candidates: List[Any] = []
        self.accepted_entities: List[Any] = []
        self.accepted_entity_keys: Set[str] = set()
        self.evidence: Dict[str, Any] = {}
        self.seeds: Dict[str, Any] = {}
