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

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple


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
        budget_spent_usd: Total budget spent on connectors (USD)
        confidence: Current confidence score (0.0-1.0)
        metrics: Dict of per-connector execution metrics
        errors: List of errors that occurred during execution
    """

    def __init__(self) -> None:
        """Initialize ExecutionContext with empty containers."""
        self.candidates: List[Any] = []
        self.accepted_entities: List[Any] = []
        self.accepted_entity_keys: Set[str] = set()
        self.evidence: Dict[str, Any] = {}
        self.seeds: Dict[str, Any] = {}
        self.budget_spent_usd: float = 0.0
        self.confidence: float = 0.0
        self.metrics: Dict[str, Any] = {}
        self.errors: List[Dict[str, Any]] = []

    def _normalize_name(self, name: str) -> str:
        """
        Normalize a name for consistent comparison.

        Applies casefold, strips leading/trailing whitespace, and collapses
        multiple whitespace characters to single spaces.

        Args:
            name: The name to normalize

        Returns:
            Normalized name string
        """
        # Casefold (aggressive lowercase), strip, and collapse whitespace
        normalized = name.casefold().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _generate_entity_key(self, candidate: Dict[str, Any]) -> str:
        """
        Generate a unique key for entity deduplication.

        Uses 3-tier strategy:
        1. Strong IDs (google, osm, etc.) - highest priority
        2. Geo-based (normalized_name + rounded lat/lng) - medium priority
        3. SHA1 hash of canonical fields - fallback

        Args:
            candidate: The candidate entity dict

        Returns:
            A unique key string for deduplication
        """
        # Tier 1: Strong IDs (check candidate.ids or context.seeds)
        ids = candidate.get("ids", {})
        if not ids:
            # Check seeds as fallback
            ids = self.seeds

        if ids:
            # Sort keys lexicographically for determinism
            sorted_keys = sorted(ids.keys())
            for key in sorted_keys:
                value = ids[key]
                if value:
                    return f"{key}:{value}"

        # Tier 2: Geo-based key (name + rounded coordinates)
        lat = candidate.get("lat")
        lng = candidate.get("lng")
        name = candidate.get("name", "")

        # CRITICAL: Explicitly check is not None (accept 0.0)
        if lat is not None and lng is not None and name:
            normalized_name = self._normalize_name(name)
            # Round to 4 decimal places
            rounded_lat = round(lat, 4)
            rounded_lng = round(lng, 4)
            return f"{normalized_name}:{rounded_lat}:{rounded_lng}"

        # Tier 3: SHA1 hash fallback
        # Create canonical representation: sorted keys, normalized string values
        canonical = {}
        for key in sorted(candidate.keys()):
            value = candidate[key]
            if isinstance(value, str):
                canonical[key] = self._normalize_name(value)
            else:
                canonical[key] = value

        # Serialize to JSON and hash
        canonical_json = json.dumps(canonical, sort_keys=True)
        hash_digest = hashlib.sha1(canonical_json.encode("utf-8")).hexdigest()
        return hash_digest

    def accept_entity(
        self, candidate: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Accept or reject a candidate entity based on deduplication.

        Generates a unique key for the candidate and checks if it's already
        been accepted. If not a duplicate, adds to accepted_entities and
        accepted_entity_keys.

        Args:
            candidate: The candidate entity dict to evaluate

        Returns:
            Tuple of (accepted, key, reason):
            - accepted: True if entity was accepted, False if duplicate
            - key: The generated deduplication key
            - reason: None if accepted, "duplicate" if rejected
        """
        key = self._generate_entity_key(candidate)

        # Check if already accepted
        if key in self.accepted_entity_keys:
            return (False, key, "duplicate")

        # Accept the entity
        self.accepted_entities.append(candidate)
        self.accepted_entity_keys.add(key)
        return (True, key, None)
