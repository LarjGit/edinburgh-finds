"""
Query feature extraction for orchestration system.

Provides deterministic boolean signal extraction from query strings to guide
connector selection and execution decisions. Features are computed once per
request and made available to condition evaluation via query_features.*.

The extraction is purely rule-based and deterministic - same query always
produces same features.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.orchestration.types import IngestRequest


@dataclass(frozen=True)
class QueryFeatures:
    """
    Immutable boolean signals extracted from query string.

    These features guide orchestration decisions about which connectors to run
    and how to interpret results. All features are computed deterministically
    from the query string and request parameters.

    Attributes:
        looks_like_category_search: True if query appears to be a generic
            category/activity search (e.g., "tennis courts") rather than a
            specific venue name (e.g., "Oriam Scotland").
        has_geo_intent: True if query contains geographic markers like location
            names, "in", "near", or proximity indicators.
    """

    looks_like_category_search: bool
    has_geo_intent: bool

    @classmethod
    def extract(cls, query: str, request: "IngestRequest") -> "QueryFeatures":
        """
        Extract features from query string and request parameters.

        This is the only way to create QueryFeatures instances. Extraction is
        deterministic - same inputs always produce same output.

        Args:
            query: The user's search query string
            request: The ingestion request containing mode and parameters

        Returns:
            QueryFeatures with computed boolean signals
        """
        # Normalize query for analysis
        normalized = query.strip().lower()

        # Empty or whitespace-only queries have no features
        if not normalized:
            return cls(
                looks_like_category_search=False,
                has_geo_intent=False,
            )

        # Detect category search patterns
        looks_like_category = cls._detect_category_search(normalized)

        # Detect geographic intent
        has_geo = cls._detect_geo_intent(normalized)

        return cls(
            looks_like_category_search=looks_like_category,
            has_geo_intent=has_geo,
        )

    @staticmethod
    def _detect_category_search(normalized_query: str) -> bool:
        """
        Detect if query looks like a category/activity search.

        Category searches are generic terms for types of venues or activities
        (e.g., "tennis courts", "padel", "sports facilities") rather than
        specific venue names (e.g., "Oriam Scotland", "Edinburgh Leisure Centre").

        Heuristics:
        - Contains generic activity/facility terms
        - Plural forms (courts, facilities, centres)
        - Lacks proper nouns or specific identifiers
        - Short queries (1-3 words) without geographic qualifiers

        Args:
            normalized_query: Lowercased, stripped query string

        Returns:
            True if query appears to be a category search
        """
        # Category indicator terms
        category_terms = [
            "court",
            "courts",
            "centre",
            "center",
            "facility",
            "facilities",
            "club",
            "clubs",
            "padel",
            "tennis",
            "football",
            "rugby",
            "swimming",
            "gym",
            "sport",
            "sports",
        ]

        # Specific venue indicators (suggest not a category search)
        specific_indicators = [
            "leisure",  # Often part of specific venue names
            "edinburgh leisure",
            "oriam",
            "meggetland",
        ]

        # Check for specific venue indicators first
        for indicator in specific_indicators:
            if indicator in normalized_query:
                # If query contains specific venue name, not a category search
                # unless it also has clear category terms
                return False

        # Check for category terms
        for term in category_terms:
            if term in normalized_query:
                return True

        # Default: if no category terms found, assume specific search
        return False

    @staticmethod
    def _detect_geo_intent(normalized_query: str) -> bool:
        """
        Detect if query contains geographic intent.

        Geographic intent means the user is looking for results in a specific
        location or area. This includes explicit location names, proximity
        indicators, and geographic prepositions.

        Heuristics:
        - Contains "in", "near", "around", "at"
        - Contains location names (Edinburgh, Leith, etc.)
        - Contains "near me" or similar proximity phrases

        Args:
            normalized_query: Lowercased, stripped query string

        Returns:
            True if query has geographic intent
        """
        # Geographic prepositions and proximity terms
        geo_markers = [
            " in ",
            " near ",
            " around ",
            " at ",
            "near me",
            "nearby",
        ]

        # Known location names (can be expanded)
        location_names = [
            "edinburgh",
            "leith",
            "morningside",
            "stockbridge",
            "portobello",
            "musselburgh",
            "dalkeith",
            "lothian",
            "scotland",
        ]

        # Check for geographic markers
        for marker in geo_markers:
            if marker in normalized_query:
                return True

        # Check for location names
        for location in location_names:
            if location in normalized_query:
                return True

        return False
