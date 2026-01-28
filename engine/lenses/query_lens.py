"""
Query-focused lens loader for orchestration.

This module provides a lightweight lens accessor specifically for:
1. Query feature extraction (activity keywords, location indicators)
2. Connector selection rules (domain-specific routing)

This coexists with the comprehensive VerticalLens loader (loader.py) which handles
the full lens configuration (facets, values, modules, triggers, etc.).
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class QueryLensConfig:
    """
    Lightweight lens configuration for query orchestration.

    Attributes:
        lens_name: Lens identifier (e.g., "padel", "wine")
        activity_keywords: Domain-specific activity terms
        location_indicators: Geographic context indicators
        facility_keywords: Facility type terms
        connector_rules: Connector selection rules
    """
    lens_name: str
    activity_keywords: List[str]
    location_indicators: List[str]
    facility_keywords: List[str]
    connector_rules: Dict[str, Any]


class QueryLens:
    """
    Query-focused lens accessor for orchestration.

    Provides simplified interface for:
    - Activity keyword lookup (for query feature extraction)
    - Location indicator lookup (for geographic context detection)
    - Connector selection rules (for domain-specific routing)

    Usage:
        >>> lens = get_active_lens("padel")
        >>> keywords = lens.get_activity_keywords()
        >>> connectors = lens.get_connectors_for_query("padel courts Edinburgh", query_features)
    """

    def __init__(self, config: QueryLensConfig):
        """
        Initialize query lens with configuration.

        Args:
            config: QueryLensConfig with vocabulary and routing rules
        """
        self.config = config
        self.lens_name = config.lens_name

    def get_activity_keywords(self) -> List[str]:
        """
        Get activity-related keywords for query feature extraction.

        Returns:
            List of domain-specific activity terms

        Example:
            >>> lens = get_active_lens("padel")
            >>> lens.get_activity_keywords()
            ['padel', 'tennis', 'football', 'rugby', 'swimming', ...]
        """
        return self.config.activity_keywords

    def get_location_indicators(self) -> List[str]:
        """
        Get location indicator words for geographic context detection.

        Returns:
            List of location-related terms

        Example:
            >>> lens = get_active_lens("padel")
            >>> lens.get_location_indicators()
            ['in', 'near', 'around', 'edinburgh', 'leith', ...]
        """
        return self.config.location_indicators

    def get_facility_keywords(self) -> List[str]:
        """
        Get facility type keywords for category search detection.

        Returns:
            List of facility-related terms
        """
        return self.config.facility_keywords

    def get_connectors_for_query(
        self,
        query: str,
        query_features: Optional["QueryFeatures"] = None
    ) -> List[str]:
        """
        Determine which lens-specific connectors should run for this query.

        This method analyzes the query and query features to determine which
        domain-specific connectors are relevant based on trigger rules.

        Args:
            query: User query string (normalized to lowercase)
            query_features: Optional QueryFeatures object with extracted features

        Returns:
            List of connector names that should be added to base connectors

        Example:
            >>> lens = get_active_lens("padel")
            >>> lens.get_connectors_for_query("padel courts edinburgh", features)
            ['sport_scotland', 'edinburgh_council']
        """
        connectors = []
        normalized_query = query.lower()

        connector_rules = self.config.connector_rules.get("connectors", {})

        for connector_name, rules in connector_rules.items():
            if self._matches_triggers(normalized_query, query_features, rules.get("triggers", [])):
                connectors.append(connector_name)

        return connectors

    def _matches_triggers(
        self,
        query: str,
        query_features: Optional["QueryFeatures"],
        triggers: List[Dict[str, Any]]
    ) -> bool:
        """
        Check if query matches any trigger rule for a connector.

        Trigger types:
        - any_keyword_match: Match if query contains N keywords
        - category_search: Match if looks like category search
        - location_match: Match if query contains location keywords
        - facility_search: Match if query mentions facilities
        - brand_mention: Match if query mentions specific brands

        Args:
            query: Normalized query string
            query_features: Optional QueryFeatures object
            triggers: List of trigger rule dicts

        Returns:
            True if any trigger matches, False otherwise
        """
        for trigger in triggers:
            trigger_type = trigger.get("type")

            if trigger_type == "any_keyword_match":
                keywords = trigger.get("keywords", [])
                threshold = trigger.get("threshold", 1)
                matches = sum(1 for kw in keywords if kw in query)
                if matches >= threshold:
                    return True

            elif trigger_type == "location_match":
                keywords = trigger.get("keywords", [])
                threshold = trigger.get("threshold", 1)
                matches = sum(1 for kw in keywords if kw in query)
                if matches >= threshold:
                    return True

            elif trigger_type == "facility_search":
                keywords = trigger.get("keywords", [])
                if any(kw in query for kw in keywords):
                    location_required = trigger.get("location_required", False)
                    if not location_required:
                        return True
                    # Check if location indicator present
                    if query_features and query_features.has_geo_intent:
                        return True

            elif trigger_type == "category_search":
                if query_features and query_features.looks_like_category_search:
                    activity_keywords = trigger.get("activity_keywords", [])
                    if any(kw in query for kw in activity_keywords):
                        return True

            elif trigger_type == "brand_mention":
                brands = trigger.get("brands", [])
                if any(brand in query for brand in brands):
                    return True

        return False


def load_query_lens(lens_name: str) -> QueryLens:
    """
    Load query lens configuration from YAML files.

    Expected structure:
        engine/lenses/<lens_name>/query_vocabulary.yaml
        engine/lenses/<lens_name>/connector_rules.yaml

    Args:
        lens_name: Lens identifier (e.g., "padel", "wine")

    Returns:
        QueryLens instance with loaded configuration

    Raises:
        FileNotFoundError: If lens config files not found
        yaml.YAMLError: If YAML parsing fails

    Example:
        >>> lens = load_query_lens("padel")
        >>> keywords = lens.get_activity_keywords()
    """
    lens_dir = Path(f"engine/lenses/{lens_name}")

    # Load query vocabulary
    vocab_path = lens_dir / "query_vocabulary.yaml"
    if not vocab_path.exists():
        raise FileNotFoundError(
            f"Query vocabulary not found: {vocab_path}. "
            f"Expected structure: engine/lenses/{lens_name}/query_vocabulary.yaml"
        )

    with vocab_path.open() as f:
        vocab = yaml.safe_load(f)

    # Load connector rules
    connectors_path = lens_dir / "connector_rules.yaml"
    if not connectors_path.exists():
        raise FileNotFoundError(
            f"Connector rules not found: {connectors_path}. "
            f"Expected structure: engine/lenses/{lens_name}/connector_rules.yaml"
        )

    with connectors_path.open() as f:
        connector_rules = yaml.safe_load(f)

    # Build configuration
    config = QueryLensConfig(
        lens_name=lens_name,
        activity_keywords=vocab.get("activity_keywords", []),
        location_indicators=vocab.get("location_indicators", []),
        facility_keywords=vocab.get("facility_keywords", []),
        connector_rules=connector_rules,
    )

    return QueryLens(config)


def get_active_lens(lens_name: Optional[str] = None) -> QueryLens:
    """
    Get active query lens (with caching).

    Args:
        lens_name: Lens identifier (defaults to "padel" if not specified)

    Returns:
        QueryLens instance

    Example:
        >>> lens = get_active_lens("padel")
        >>> lens.get_activity_keywords()
        ['padel', 'tennis', 'football', ...]
    """
    if lens_name is None:
        lens_name = "padel"  # Default lens

    # Simple caching: load once and reuse
    if not hasattr(get_active_lens, "_cache"):
        get_active_lens._cache = {}

    if lens_name not in get_active_lens._cache:
        get_active_lens._cache[lens_name] = load_query_lens(lens_name)

    return get_active_lens._cache[lens_name]
