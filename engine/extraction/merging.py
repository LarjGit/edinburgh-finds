"""
Field-level trust merging for extracted entities.

This module implements intelligent merging of data from multiple sources
based on a trust hierarchy. Each field is merged independently, choosing
the value from the most trusted source.
"""

from dataclasses import dataclass, field as dataclass_field
from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path

# ---------------------------------------------------------------------------
# Missingness predicate — single source of truth (architecture.md 9.4)
# ---------------------------------------------------------------------------
# Curated punctuation-dash and "not-available" sentinels only.
# Deliberately NOT including "null"/"none"/"unknown"/"tbd" etc. — those
# tokens appear legitimately in real field values and would cause silent
# data loss.  Extend only when a concrete production false-positive is
# observed and documented.
_PLACEHOLDER_SENTINELS = {"N/A", "n/a", "NA", "-", "\u2013", "\u2014"}
#                                              hyphen  en-dash  em-dash


def _is_missing(value: Any) -> bool:
    """Return True when *value* should be treated as absent.

    Covers None, empty/whitespace-only strings, and the curated
    placeholder sentinels above.  Non-string types (0, False, [], {})
    are always real values.
    """
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return stripped == "" or stripped in _PLACEHOLDER_SENTINELS


# ---------------------------------------------------------------------------
# Field-group sets — architecture.md 9.4 strategy routing
# ---------------------------------------------------------------------------
GEO_FIELDS = {"latitude", "longitude"}
NARRATIVE_FIELDS = {"summary", "description"}
CANONICAL_ARRAY_FIELDS = {
    "canonical_activities",
    "canonical_roles",
    "canonical_place_types",
    "canonical_access",
}


def _normalise_canonical(value: str) -> str:
    """Strip whitespace and lowercase for canonical-array deduplication."""
    return value.strip().lower()


@dataclass
class FieldValue:
    """Represents a field value from a specific source."""
    value: Any
    source: str
    confidence: float
    all_sources: List[str] = dataclass_field(default_factory=list)


class TrustHierarchy:
    """Manages trust levels for different data sources."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize trust hierarchy from config.

        Args:
            config_path: Path to extraction.yaml config file
        """
        if config_path is None:
            # Default to engine/config/extraction.yaml
            config_path = Path(__file__).parent.parent / "config" / "extraction.yaml"

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.trust_levels: Dict[str, int] = config.get("trust_levels", {})
        self.default_trust = self.trust_levels.get("unknown_source", 10)

    def get_trust_level(self, source: str) -> int:
        """
        Get trust level for a source.

        Args:
            source: Source name (e.g., "google_places", "osm")

        Returns:
            Trust level (0-100), or default if source unknown
        """
        return self.trust_levels.get(source, self.default_trust)

    def is_more_trusted(self, source1: str, source2: str) -> bool:
        """
        Check if source1 is more trusted than source2.

        Args:
            source1: First source name
            source2: Second source name

        Returns:
            True if source1 has higher trust level
        """
        return self.get_trust_level(source1) > self.get_trust_level(source2)

    def get_highest_trust_source(self, sources: List[str]) -> Optional[str]:
        """
        Get the source with highest trust level from a list.

        Args:
            sources: List of source names

        Returns:
            Source name with highest trust, or None if list is empty
        """
        if not sources:
            return None

        return max(sources, key=lambda s: self.get_trust_level(s))

    def sort_by_trust(self, sources: List[str], reverse: bool = True) -> List[str]:
        """
        Sort sources by trust level.

        Args:
            sources: List of source names
            reverse: If True, sort descending (highest trust first)

        Returns:
            Sorted list of sources
        """
        return sorted(sources, key=lambda s: self.get_trust_level(s), reverse=reverse)


class FieldMerger:
    """Merges individual field values from multiple sources."""

    def __init__(self, trust_hierarchy: Optional[TrustHierarchy] = None):
        """
        Initialize field merger.

        Args:
            trust_hierarchy: Optional trust hierarchy instance
        """
        self.trust_hierarchy = trust_hierarchy or TrustHierarchy()

    def merge_field(
        self,
        field_name: str,
        field_values: List[FieldValue]
    ) -> FieldValue:
        """
        Merge a single field using the strategy for its field group.

        Routing (architecture.md 9.4):
          - Canonical arrays  → union + normalise + dedup + sort
          - Geo fields        → presence (via _is_missing) then trust
          - Narrative text    → richer (longer) text then trust
          - Default           → trust tier → confidence → connector_id

        All winner-picking strategies share the same deterministic
        tie-break cascade: (-trust_level, -confidence, source) where
        source is ascending lexicographic connector_id.
        """
        if not field_values:
            return FieldValue(value=None, source=None, confidence=0.0)

        all_sources = [fv.source for fv in field_values]

        # Canonical arrays have their own missing-value handling (union → [])
        if field_name in CANONICAL_ARRAY_FIELDS:
            return self._merge_canonical_array(field_name, field_values, all_sources)

        # Modules have their own deep-merge semantics (architecture.md 9.4)
        if field_name == "modules":
            return self._merge_modules_deep(field_values, all_sources)

        # All other groups share the same missingness pre-filter
        non_missing = [fv for fv in field_values if not _is_missing(fv.value)]

        if not non_missing:
            highest_trust_source = self.trust_hierarchy.get_highest_trust_source(all_sources)
            result = FieldValue(value=None, source=highest_trust_source, confidence=0.0)
            result.all_sources = all_sources
            return result

        # Route to field-group strategy
        if field_name in GEO_FIELDS:
            return self._merge_geo(field_name, non_missing, all_sources)
        if field_name in NARRATIVE_FIELDS:
            return self._merge_narrative(field_name, non_missing, all_sources)
        return self._merge_trust_default(field_name, non_missing, all_sources)

    # ------------------------------------------------------------------
    # Strategy methods
    # ------------------------------------------------------------------

    def _merge_trust_default(
        self,
        field_name: str,
        candidates: List[FieldValue],
        all_sources: List[str],
    ) -> FieldValue:
        """Default: trust tier → confidence → connector_id (ascending)."""
        winner = min(candidates, key=lambda fv: (
            -self.trust_hierarchy.get_trust_level(fv.source),
            -fv.confidence,
            fv.source,
        ))
        result = FieldValue(value=winner.value, source=winner.source, confidence=winner.confidence)
        result.all_sources = all_sources
        return result

    def _merge_geo(
        self,
        field_name: str,
        candidates: List[FieldValue],
        all_sources: List[str],
    ) -> FieldValue:
        """Geo: presence (already filtered via _is_missing) → trust → connector_id.

        0 / 0.0 are valid coordinates (equator / prime meridian) and are NOT
        treated as missing.  Extensible point for future precision-based logic.
        """
        return self._merge_trust_default(field_name, candidates, all_sources)

    def _merge_narrative(
        self,
        field_name: str,
        candidates: List[FieldValue],
        all_sources: List[str],
    ) -> FieldValue:
        """Narrative: richer (longer) text → trust → connector_id."""
        winner = min(candidates, key=lambda fv: (
            -len(str(fv.value)),
            -self.trust_hierarchy.get_trust_level(fv.source),
            -fv.confidence,
            fv.source,
        ))
        result = FieldValue(value=winner.value, source=winner.source, confidence=winner.confidence)
        result.all_sources = all_sources
        return result

    def _merge_canonical_array(
        self,
        field_name: str,
        field_values: List[FieldValue],
        all_sources: List[str],
    ) -> FieldValue:
        """Canonical arrays: union, normalise, deduplicate, lexicographic sort.

        All contributing sources are co-authors — no single winner.
        Individual items that are missing per _is_missing are silently dropped.
        """
        seen: set = set()
        for fv in field_values:
            if fv.value is None:
                continue
            items = fv.value if isinstance(fv.value, list) else [fv.value]
            for item in items:
                if isinstance(item, str) and not _is_missing(item):
                    seen.add(_normalise_canonical(item))
        result = FieldValue(value=sorted(seen), source="merged", confidence=1.0)
        result.all_sources = all_sources
        return result


    # ------------------------------------------------------------------
    # Modules deep merge — architecture.md 9.4 "Modules JSON Structures"
    # ------------------------------------------------------------------

    def _merge_modules_deep(
        self,
        field_values: List[FieldValue],
        all_sources: List[str],
    ) -> FieldValue:
        """Entry point: strip Nones, recurse, wrap in FieldValue."""
        candidates = [
            (fv.value, fv.source, fv.confidence)
            for fv in field_values
            if fv.value is not None
        ]
        merged = self._deep_merge(candidates) if candidates else {}
        result = FieldValue(value=merged, source="merged", confidence=1.0)
        result.all_sources = all_sources
        return result

    def _deep_merge(self, candidates: List[tuple]) -> Any:
        """Recursive dispatch on value types.

        candidates: list of (value, source, confidence).
        Single candidate short-circuits immediately.
        """
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0][0]

        if all(isinstance(v, dict) for v, _s, _c in candidates):
            return self._deep_merge_dicts(candidates)
        if all(isinstance(v, list) for v, _s, _c in candidates):
            return self._deep_merge_arrays(candidates)

        # Type mismatch or scalar leaf → trust winner takes all
        return self._trust_winner_value(candidates)

    def _deep_merge_dicts(self, candidates: List[tuple]) -> Dict[str, Any]:
        """Object vs object → recursive merge on the union of keys.

        Keys are iterated in sorted order for deterministic output.
        """
        all_keys: set = set()
        for v, _s, _c in candidates:
            all_keys.update(v.keys())

        result: Dict[str, Any] = {}
        for key in sorted(all_keys):
            sub = [(v[key], s, c) for v, s, c in candidates if key in v]
            result[key] = self._deep_merge(sub)
        return result

    def _deep_merge_arrays(self, candidates: List[tuple]) -> Any:
        """Array vs array dispatch.

        - Contains any dict element → object array → wholesale from winner.
        - All same scalar type    → concat + dedup + sort (strings trimmed).
        - Mixed scalar types      → can't sort safely → wholesale from winner.
        """
        # Object-array check: any dict anywhere across all arrays?
        if any(
            isinstance(item, dict)
            for v, _s, _c in candidates
            for item in v
        ):
            return self._trust_winner_value(candidates)

        # Flatten all items; trim strings; track types
        trimmed: List[Any] = []
        types_seen: set = set()
        for v, _s, _c in candidates:
            for item in v:
                if isinstance(item, str):
                    trimmed.append(item.strip())
                    types_seen.add(str)
                else:
                    trimmed.append(item)
                    types_seen.add(type(item))

        if not trimmed:
            return []

        # Mixed types → unsafe to sort → trust winner wholesale
        if len(types_seen) > 1:
            return self._trust_winner_value(candidates)

        # Deduplicate and sort (all items are the same type)
        return sorted(set(trimmed), key=str)

    def _trust_winner_value(self, candidates: List[tuple]) -> Any:
        """Pick the value from the highest-trust source.

        Tie-break cascade: trust desc → confidence desc → source asc.
        """
        winner = min(candidates, key=lambda x: (
            -self.trust_hierarchy.get_trust_level(x[1]),
            -x[2],   # confidence descending
            x[1],    # source ascending (lexicographic)
        ))
        return winner[0]


class EntityMerger:
    """Merges multiple ExtractedEntity records into a single Listing."""

    def __init__(
        self,
        trust_hierarchy: Optional[TrustHierarchy] = None,
        field_merger: Optional[FieldMerger] = None
    ):
        """
        Initialize listing merger.

        Args:
            trust_hierarchy: Optional trust hierarchy instance
            field_merger: Optional field merger instance
        """
        self.trust_hierarchy = trust_hierarchy or TrustHierarchy()
        self.field_merger = field_merger or FieldMerger(self.trust_hierarchy)

    def merge_entities(self, extracted_entities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Merge multiple extracted entities into a single entity.

        Args:
            extracted_entities: List of ExtractedEntity records (as dicts)

        Returns:
            Merged entity dict with optimal field values and provenance tracking
        """
        if not extracted_entities:
            return None

        if len(extracted_entities) == 1:
            # No merging needed, but still format the output
            return self._format_single_entity(extracted_entities[0])

        # Collect all fields across all entities
        all_fields = set()
        for entity in extracted_entities:
            if "attributes" in entity and entity["attributes"]:
                all_fields.update(entity["attributes"].keys())

        # Merge each field independently
        merged_attributes = {}
        source_info = {}
        field_confidence = {}

        for field_name in all_fields:
            # Collect values for this field from all sources
            field_values = []

            for entity in extracted_entities:
                attributes = entity.get("attributes") or {}
                if field_name in attributes:
                    value = attributes[field_name]
                    source = entity["source"]
                    # Use a default confidence if not specified
                    confidence = entity.get("confidence", 0.8)

                    field_values.append(
                        FieldValue(value=value, source=source, confidence=confidence)
                    )

            # Merge this field
            if field_values:
                merged_value = self.field_merger.merge_field(field_name, field_values)

                if merged_value.value is not None:
                    merged_attributes[field_name] = merged_value.value
                    source_info[field_name] = merged_value.source

                    # Calculate field confidence based on agreement
                    agreement_ratio = self._calculate_agreement(field_values, merged_value.value)
                    field_confidence[field_name] = agreement_ratio

        # Merge discovered_attributes
        merged_discovered = self._merge_discovered_attributes(extracted_entities)

        # Combine external_ids from all sources
        merged_external_ids = self._merge_external_ids(extracted_entities)

        # Determine entity_type — deterministic cascade:
        #   _is_missing filter → trust descending → connector_id ascending
        entity_types = [
            (entity.get("entity_type"), entity["source"])
            for entity in extracted_entities
            if not _is_missing(entity.get("entity_type"))
        ]
        entity_type = None
        if entity_types:
            winner = min(entity_types, key=lambda x: (
                -self.trust_hierarchy.get_trust_level(x[1]),
                x[1],
            ))
            entity_type = winner[0]

        # Build final merged entity
        merged_entity = {
            **merged_attributes,
            "entity_type": entity_type,
            "discovered_attributes": merged_discovered,
            "external_ids": merged_external_ids,
            "source_info": source_info,
            "field_confidence": field_confidence,
            "sources": [entity["source"] for entity in extracted_entities],
            "source_count": len(extracted_entities)
        }

        return merged_entity

    def _format_single_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single entity to match merged entity structure.

        Provenance fields (source_info, field_confidence) are always dicts —
        never None — so that single-source and multi-source outputs share the
        same structural shape.
        """
        attributes = entity.get("attributes") or {}
        source = entity["source"]

        source_info = {field_name: source for field_name in attributes}
        field_confidence = {field_name: 1.0 for field_name in attributes}

        return {
            **attributes,
            "entity_type": entity.get("entity_type"),
            "discovered_attributes": entity.get("discovered_attributes") or {},
            "external_ids": entity.get("external_ids") or {},
            "source_info": source_info,
            "field_confidence": field_confidence,
            "sources": [source],
            "source_count": 1,
        }

    def _merge_discovered_attributes(
        self,
        extracted_entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge discovered_attributes from multiple sources.

        Discovered attributes are merged with same trust hierarchy as regular fields.
        """
        all_discovered_fields = set()
        for entity in extracted_entities:
            discovered = entity.get("discovered_attributes") or {}
            if discovered:
                all_discovered_fields.update(discovered.keys())

        merged_discovered = {}

        for field_name in all_discovered_fields:
            field_values = []

            for entity in extracted_entities:
                discovered = entity.get("discovered_attributes") or {}
                if field_name in discovered:
                    value = discovered[field_name]
                    source = entity["source"]
                    confidence = entity.get("confidence", 0.8)

                    field_values.append(
                        FieldValue(value=value, source=source, confidence=confidence)
                    )

            if field_values:
                merged_value = self.field_merger.merge_field(field_name, field_values)
                if merged_value.value is not None:
                    merged_discovered[field_name] = merged_value.value

        return merged_discovered

    def _merge_external_ids(
        self,
        extracted_entities: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Combine external IDs from all sources.

        Each source can contribute its own external ID.
        """
        merged_ids = {}

        for entity in extracted_entities:
            external_ids = entity.get("external_ids", {})
            if external_ids:
                merged_ids.update(external_ids)

        return merged_ids

    def _calculate_agreement(
        self,
        field_values: List[FieldValue],
        winning_value: Any
    ) -> float:
        """
        Calculate agreement ratio for a field.

        Args:
            field_values: All values for this field
            winning_value: The value that won the merge

        Returns:
            Agreement ratio (0.0-1.0), where 1.0 means all sources agree
        """
        if not field_values:
            return 0.0

        # Count how many sources provided the winning value
        agreements = sum(1 for fv in field_values if fv.value == winning_value)

        return agreements / len(field_values)


@dataclass
class MergeConflict:
    """Represents a merge conflict between sources."""
    field_name: str
    conflicting_values: List[Dict[str, Any]]
    winner_source: str
    winner_value: Any
    trust_difference: int
    severity: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "field_name": self.field_name,
            "conflicting_values": self.conflicting_values,
            "winner_source": self.winner_source,
            "winner_value": self.winner_value,
            "trust_difference": self.trust_difference,
            "severity": self.severity
        }


class ConflictDetector:
    """Detects and reports merge conflicts."""

    def __init__(
        self,
        trust_hierarchy: Optional[TrustHierarchy] = None,
        trust_difference_threshold: int = 15
    ):
        """
        Initialize conflict detector.

        Args:
            trust_hierarchy: Optional trust hierarchy instance
            trust_difference_threshold: Maximum trust difference before flagging conflict.
                                       Conflicts are only reported if the trust difference
                                       is less than this threshold (default: 15 points)
        """
        self.trust_hierarchy = trust_hierarchy or TrustHierarchy()
        self.trust_difference_threshold = trust_difference_threshold

    def detect_conflict(
        self,
        field_name: str,
        field_values: List[Dict[str, Any]]
    ) -> Optional[MergeConflict]:
        """
        Detect if there's a reportable conflict for a field.

        A conflict is reportable when:
        1. Multiple sources provide different (non-None) values
        2. The trust level difference between top sources is small (< threshold)

        Args:
            field_name: Name of the field being checked
            field_values: List of dicts with 'value', 'source', 'confidence'

        Returns:
            MergeConflict if conflict detected, None otherwise
        """
        # Need at least 2 sources to have a conflict
        if len(field_values) < 2:
            return None

        # Filter out None values
        non_none_values = [fv for fv in field_values if fv.get("value") is not None]

        if len(non_none_values) < 2:
            return None

        # Get unique values
        unique_values = set(str(fv["value"]) for fv in non_none_values)

        # If all values are the same, no conflict
        if len(unique_values) == 1:
            return None

        # Sort by trust level (highest first), then by confidence
        sorted_values = sorted(
            non_none_values,
            key=lambda fv: (
                self.trust_hierarchy.get_trust_level(fv["source"]),
                fv.get("confidence", 0.5)
            ),
            reverse=True
        )

        # Get trust levels for top 2 sources
        winner = sorted_values[0]
        runner_up = sorted_values[1]

        winner_trust = self.trust_hierarchy.get_trust_level(winner["source"])
        runner_up_trust = self.trust_hierarchy.get_trust_level(runner_up["source"])

        trust_difference = winner_trust - runner_up_trust

        # Only report conflict if trust difference is small
        if trust_difference >= self.trust_difference_threshold:
            return None

        # Calculate severity (0.0-1.0, higher = more severe)
        # Severity is inversely proportional to trust difference
        # 0 difference = 1.0 severity, threshold difference = 0.0 severity
        severity = 1.0 - (trust_difference / self.trust_difference_threshold)

        # Build conflicting values list with trust levels
        conflicting_values = []
        for fv in sorted_values:
            conflicting_values.append({
                "value": fv["value"],
                "source": fv["source"],
                "trust": self.trust_hierarchy.get_trust_level(fv["source"]),
                "confidence": fv.get("confidence", 0.5)
            })

        return MergeConflict(
            field_name=field_name,
            conflicting_values=conflicting_values,
            winner_source=winner["source"],
            winner_value=winner["value"],
            trust_difference=trust_difference,
            severity=severity
        )
