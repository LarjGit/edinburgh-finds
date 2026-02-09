"""
Execution Context for Universal Entity Extraction Engine.

This module provides the ExecutionContext class per docs/target-architecture.md 3.6.

ExecutionContext is an immutable carrier object that holds:
- lens_id: Identifier for the active lens
- lens_contract: Validated lens runtime contract
- lens_hash: Reproducibility hash (optional)

ExecutionContext is created exactly once during bootstrap and passed through
the entire runtime pipeline. It contains only plain serializable data and
has no mutable state or business logic.

For mutable orchestrator state (candidates, accepted_entities, metrics, etc.),
use OrchestratorState instead.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ExecutionContext:
    """
    Immutable carrier object for lens contract and metadata.

    Per docs/target-architecture.md 3.6, ExecutionContext is a frozen dataclass that:
    - Identifies the active lens
    - Carries the validated lens runtime contract
    - Carries reproducibility metadata

    Properties:
    - Created exactly once during bootstrap
    - Never mutated (frozen dataclass)
    - Contains only plain serializable data
    - Safe for logging, persistence, and replay
    - No live loaders, registries, or mutable references

    Attributes:
        lens_id: Identifier for the active lens (e.g., "edinburgh_finds")
        lens_contract: Validated lens runtime contract (dict)
        lens_hash: Optional content hash for reproducibility
    """

    lens_id: str
    lens_contract: Dict[str, Any]
    lens_hash: Optional[str] = None
