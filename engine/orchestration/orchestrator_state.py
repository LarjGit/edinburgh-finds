"""
Orchestrator State for Intelligent Ingestion Orchestration.

This module provides the OrchestratorState class, which holds mutable state
during orchestration execution. This is separate from ExecutionContext, which
carries immutable lens contract data per docs/target-architecture.md 3.6.

OrchestratorState serves as a container for:
- candidates: Entities discovered but not yet accepted
- accepted_entities: Entities that passed deduplication
- accepted_entity_keys: Set of keys for deduplication tracking
- evidence: Supporting data collected during discovery
- seeds: Initial seed data (IDs, known entities)
- metrics: Per-connector execution metrics
- errors: Error tracking
- budget_spent_usd: Budget tracking
- confidence: Current confidence score

All containers are mutable to allow state updates during orchestration.
"""

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from fuzzywuzzy import fuzz


class OrchestratorState:
    """
    Mutable state container for orchestration execution.

    Holds mutable collections and business logic that are updated throughout
    the orchestration lifecycle. All fields are initialized as empty containers.

    This is separate from ExecutionContext, which carries only immutable
    lens contract data per docs/target-architecture.md 3.6.

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

    # Fuzzy matching threshold (0-100): names above this similarity are considered duplicates
    FUZZY_MATCH_THRESHOLD = 85

    def __init__(self) -> None:
        """Initialize OrchestratorState with empty containers."""
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

    def _remove_common_articles(self, name: str) -> str:
        """
        Remove common articles (the, a, an) from the beginning of a name.

        This helps fuzzy matching by eliminating article differences.

        Args:
            name: The name to process

        Returns:
            Name without leading articles
        """
        # Normalize first
        normalized = self._normalize_name(name)

        # Remove common English articles from the beginning
        articles = [r"^the\s+", r"^a\s+", r"^an\s+"]
        for article in articles:
            normalized = re.sub(article, "", normalized)

        return normalized

    def _has_strong_identifier(self, candidate: Dict[str, Any]) -> bool:
        """
        Check if a candidate has strong identifying information (IDs or coordinates).

        Args:
            candidate: The candidate entity dict

        Returns:
            True if candidate has strong IDs or valid coordinates
        """
        # Check for strong IDs
        ids = candidate.get("ids", {})
        if ids:
            # Has at least one ID
            return True

        # Check for valid coordinates (must be not None)
        lat = candidate.get("lat")
        lng = candidate.get("lng")
        if lat is not None and lng is not None:
            # Has coordinates
            return True

        return False

    def _find_fuzzy_match(
        self, candidate: Dict[str, Any]
    ) -> Optional[str]:
        """
        Find a fuzzy match for the candidate among accepted entities.

        Bidirectional fuzzy matching strategy:
        1. Weak candidate (no IDs/coords) → fuzzy match against ALL accepted entities
        2. Strong candidate (has IDs/coords) → fuzzy match ONLY against weak accepted entities

        This enables cross-source deduplication:
        - Serper (weak) → fuzzy matches against Google (strong) ✓
        - Google (strong) → fuzzy matches against Serper (weak) ✓
        - Google (strong) → does NOT fuzzy match against another Google (strong) ✓

        Uses token set ratio matching to handle:
        - Word order differences
        - Extra/missing words
        - Punctuation and spacing variations
        - Article differences (the, a, an)

        Args:
            candidate: The candidate entity dict to search for fuzzy matches

        Returns:
            The key of the matching accepted entity, or None if no match found
        """
        candidate_name = candidate.get("name", "")
        if not candidate_name:
            return None

        candidate_has_strong_id = self._has_strong_identifier(candidate)
        normalized_candidate = self._remove_common_articles(candidate_name)

        # Check against accepted entities
        for accepted_entity in self.accepted_entities:
            accepted_name = accepted_entity.get("name", "")
            if not accepted_name:
                continue

            accepted_has_strong_id = self._has_strong_identifier(accepted_entity)

            # Apply fuzzy matching if:
            # - Candidate is weak (no strong ID), OR
            # - Accepted entity is weak (no strong ID)
            # This enables bidirectional cross-source matching
            if candidate_has_strong_id and accepted_has_strong_id:
                # Both have strong IDs - trust the IDs, skip fuzzy matching
                continue

            # Normalize accepted name
            normalized_accepted = self._remove_common_articles(accepted_name)

            # Use token_set_ratio for flexible matching
            similarity = fuzz.token_set_ratio(normalized_candidate, normalized_accepted)

            if similarity >= self.FUZZY_MATCH_THRESHOLD:
                # Found a match! Return the key of the accepted entity
                return self._generate_entity_key(accepted_entity)

        return None

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
        # Tier 1: Strong IDs (check candidate.ids or state.seeds)
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

        Multi-tier deduplication strategy:
        1. Tier 1/2/3: Generate exact key (IDs, geo, or SHA1 hash)
        2. Check for exact key match
        3. Tier 2.5: Check for fuzzy name match (NEW - cross-source deduplication)
        4. Accept if no duplicates found

        Args:
            candidate: The candidate entity dict to evaluate

        Returns:
            Tuple of (accepted, key, reason):
            - accepted: True if entity was accepted, False if duplicate
            - key: The generated deduplication key (or fuzzy match key if duplicate)
            - reason: None if accepted, "duplicate" if rejected
        """
        # Tier 1/2/3: Generate exact key
        key = self._generate_entity_key(candidate)

        # Check for exact key match
        if key in self.accepted_entity_keys:
            return (False, key, "duplicate")

        # Tier 2.5: Check for fuzzy name match
        fuzzy_match_key = self._find_fuzzy_match(candidate)
        if fuzzy_match_key:
            # Strong candidate matched against a weak accepted entity:
            # replace the weak entity so the richer data (IDs, coords) is kept.
            if self._has_strong_identifier(candidate):
                for i, accepted in enumerate(self.accepted_entities):
                    if self._generate_entity_key(accepted) == fuzzy_match_key:
                        self.accepted_entities[i] = candidate
                        self.accepted_entity_keys.discard(fuzzy_match_key)
                        self.accepted_entity_keys.add(key)
                        return (True, key, None)

            # Weak candidate matching an existing entity: drop as duplicate
            return (False, fuzzy_match_key, "duplicate")

        # No duplicates found - accept the entity
        self.accepted_entities.append(candidate)
        self.accepted_entity_keys.add(key)
        return (True, key, None)
