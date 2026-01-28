"""
Query feature extraction for orchestration system.

Provides deterministic boolean signal extraction from query strings to guide
connector selection and execution decisions. Features are computed once per
request and made available to condition evaluation via query_features.*.

The extraction is purely rule-based and deterministic - same query always
produces same features.

ARCHITECTURAL NOTE: This module is now VERTICAL-AGNOSTIC. All domain-specific
vocabulary (activity keywords, location names) is loaded from Lens configurations
at runtime. Adding a new vertical (Wine, Restaurants) requires ZERO code changes -
just create a new lens YAML config.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from engine.lenses.query_lens import get_active_lens, QueryLens

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
    def extract(
        cls,
        query: str,
        request: "IngestRequest",
        lens_name: Optional[str] = None
    ) -> "QueryFeatures":
        """
        Extract features from query string and request parameters.

        This is the only way to create QueryFeatures instances. Extraction is
        deterministic - same inputs always produce same output.

        VERTICAL-AGNOSTIC: Uses Lens-provided vocabulary for domain-specific
        term detection. Different lenses (Padel, Wine) provide different keywords
        without requiring code changes.

        Args:
            query: The user's search query string
            request: The ingestion request containing mode and parameters
            lens_name: Optional lens identifier (defaults to Padel if not specified)

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

        # Load Lens configuration for domain-specific vocabulary
        lens = get_active_lens(lens_name)

        # Detect category search patterns (using Lens vocabulary)
        looks_like_category = cls._detect_category_search(normalized, lens)

        # Detect geographic intent (using Lens location indicators)
        has_geo = cls._detect_geo_intent(normalized, lens)

        return cls(
            looks_like_category_search=looks_like_category,
            has_geo_intent=has_geo,
        )

    @staticmethod
    def _detect_category_search(normalized_query: str, lens: "QueryLens") -> bool:
        """
        Detect if query looks like a category/activity search.

        Category searches are generic terms for types of venues or activities
        (e.g., "tennis courts", "padel", "sports facilities") rather than
        specific venue names (e.g., "Oriam Scotland", "Edinburgh Leisure Centre").

        VERTICAL-AGNOSTIC: Uses Lens-provided activity and facility keywords.
        Different verticals (Padel sports vs Wine) provide different term sets
        without requiring code changes.

        Heuristics:
        - Contains generic activity/facility terms (from Lens)
        - Plural forms (courts, facilities, centres)
        - Lacks proper nouns or specific identifiers
        - Short queries (1-3 words) without geographic qualifiers

        Args:
            normalized_query: Lowercased, stripped query string
            lens: QueryLens providing domain-specific vocabulary

        Returns:
            True if query appears to be a category search
        """
        # Load category indicator terms from Lens (VERTICAL-AGNOSTIC)
        activity_keywords = lens.get_activity_keywords()
        facility_keywords = lens.get_facility_keywords()
        category_terms = activity_keywords + facility_keywords

        # Generic specific venue indicators (universal across verticals)
        # These suggest a branded/specific search rather than category search
        specific_indicators = [
            "leisure",  # Often part of specific venue names
            "the ",     # "The" suggests proper noun
            " ltd",
            " limited",
            " plc",
        ]

        # Check for specific venue indicators first
        for indicator in specific_indicators:
            if indicator in normalized_query:
                # If query contains specific venue name, not a category search
                # unless it also has clear category terms
                return False

        # Check for category terms (from Lens vocabulary)
        for term in category_terms:
            if term in normalized_query:
                return True

        # Default: if no category terms found, assume specific search
        return False

    @staticmethod
    def _detect_geo_intent(normalized_query: str, lens: "QueryLens") -> bool:
        """
        Detect if query contains geographic intent.

        Geographic intent means the user is looking for results in a specific
        location or area. This includes explicit location names, proximity
        indicators, and geographic prepositions.

        VERTICAL-AGNOSTIC: Uses Lens-provided location indicators.
        Different lenses (Edinburgh Padel vs Scotland Wine) provide different
        geographic vocabularies without requiring code changes.

        Heuristics:
        - Contains "in", "near", "around", "at" (universal geo markers)
        - Contains location names (from Lens - e.g., Edinburgh, Scotland, regions)
        - Contains "near me" or similar proximity phrases (universal)

        Args:
            normalized_query: Lowercased, stripped query string
            lens: QueryLens providing domain-specific location indicators

        Returns:
            True if query has geographic intent
        """
        # Universal geographic prepositions and proximity terms
        # These are vertical-agnostic (same across Padel, Wine, etc.)
        geo_markers = [
            " in ",
            " near ",
            " around ",
            " at ",
            "near me",
            "nearby",
        ]

        # Check for universal geographic markers
        for marker in geo_markers:
            if marker in normalized_query:
                return True

        # Load location names from Lens (VERTICAL-AGNOSTIC)
        # Padel lens: Edinburgh neighborhoods
        # Wine lens: Scotland wine regions
        location_names = lens.get_location_indicators()

        # Check for location names (from Lens vocabulary)
        for location in location_names:
            if location in normalized_query:
                return True

        return False
