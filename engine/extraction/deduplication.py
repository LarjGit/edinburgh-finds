"""
Deduplication logic for extracted entities.

Implements a cascade of matching strategies:
1. External ID matching (100% confidence) - Google Place ID, OSM ID, etc.
2. Slug matching (100% confidence for exact, lower for similar)
3. Fuzzy matching (name similarity + geographic proximity)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from fuzzywuzzy import fuzz
import math
import re
from unidecode import unidecode


@dataclass
class MatchResult:
    """Result of a deduplication match attempt."""
    is_match: bool
    confidence: float
    match_type: str = ""
    matched_on: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ExternalIDMatcher:
    """Matches entities based on external IDs (Google Place ID, OSM ID, etc.)."""

    def match(self, ids1: Dict[str, str], ids2: Dict[str, str]) -> MatchResult:
        """
        Match two entities based on external IDs.

        Args:
            ids1: Dictionary of external IDs for entity 1
            ids2: Dictionary of external IDs for entity 2

        Returns:
            MatchResult with confidence 1.0 if any external ID matches
        """
        if not ids1 or not ids2:
            return MatchResult(is_match=False, confidence=0.0)

        # Find common ID types
        common_types = set(ids1.keys()) & set(ids2.keys())

        if not common_types:
            return MatchResult(is_match=False, confidence=0.0)

        # Check if any common ID matches
        for id_type in common_types:
            id1 = self._normalize_id(ids1[id_type])
            id2 = self._normalize_id(ids2[id_type])

            if id1 == id2:
                return MatchResult(
                    is_match=True,
                    confidence=1.0,
                    match_type="external_id",
                    matched_on=id_type
                )

        return MatchResult(is_match=False, confidence=0.0)

    def _normalize_id(self, external_id: str) -> str:
        """Normalize external ID for comparison (lowercase, trim whitespace)."""
        if not external_id:
            return ""
        return str(external_id).strip().lower()


class SlugMatcher:
    """Matches entities based on slugs (URL-safe identifiers)."""

    def __init__(self, exact_threshold: float = 1.0, similarity_threshold: float = 0.9):
        """
        Initialize slug matcher.

        Args:
            exact_threshold: Confidence for exact slug match (default 1.0)
            similarity_threshold: Minimum similarity ratio to consider a match
        """
        self.exact_threshold = exact_threshold
        self.similarity_threshold = similarity_threshold

    def match(self, slug1: Optional[str], slug2: Optional[str]) -> MatchResult:
        """
        Match two entities based on slugs.

        Args:
            slug1: Slug for entity 1
            slug2: Slug for entity 2

        Returns:
            MatchResult with confidence based on slug similarity
        """
        if not slug1 or not slug2:
            return MatchResult(is_match=False, confidence=0.0)

        slug1_norm = self._normalize_slug(slug1)
        slug2_norm = self._normalize_slug(slug2)

        if not slug1_norm or not slug2_norm:
            return MatchResult(is_match=False, confidence=0.0)

        # Exact match
        if slug1_norm == slug2_norm:
            return MatchResult(
                is_match=True,
                confidence=self.exact_threshold,
                match_type="slug"
            )

        # Fuzzy similarity for typo tolerance
        similarity = fuzz.ratio(slug1_norm, slug2_norm) / 100.0

        if similarity >= self.similarity_threshold:
            return MatchResult(
                is_match=True,
                confidence=similarity,
                match_type="slug",
                details={"similarity": similarity}
            )

        return MatchResult(is_match=False, confidence=similarity)

    def _normalize_slug(self, slug: str) -> str:
        """Normalize slug for comparison (lowercase, trim whitespace)."""
        if not slug:
            return ""
        return str(slug).strip().lower()


class FuzzyMatcher:
    """Matches entities based on name similarity and geographic proximity."""

    def __init__(
        self,
        threshold: float = 0.85,
        max_distance_meters: float = 200.0,
        name_weight: float = 0.7,
        location_weight: float = 0.3
    ):
        """
        Initialize fuzzy matcher.

        Args:
            threshold: Minimum confidence to consider a match
            max_distance_meters: Maximum distance between venues to consider a match
            name_weight: Weight for name similarity (0-1)
            location_weight: Weight for location proximity (0-1)
        """
        self.threshold = threshold
        self.max_distance_meters = max_distance_meters
        self.name_weight = name_weight
        self.location_weight = location_weight

    def match(self, entity1: Dict[str, Any], entity2: Dict[str, Any]) -> MatchResult:
        """
        Match two entities based on fuzzy name and location similarity.

        Args:
            entity1: First entity with entity_name, latitude, longitude
            entity2: Second entity with entity_name, latitude, longitude

        Returns:
            MatchResult with combined confidence score
        """
        # Extract fields
        name1 = entity1.get("entity_name", "")
        name2 = entity2.get("entity_name", "")
        lat1 = entity1.get("latitude")
        lng1 = entity1.get("longitude")
        lat2 = entity2.get("latitude")
        lng2 = entity2.get("longitude")

        # Both name and location are required for fuzzy matching
        if not name1 or not name2:
            return MatchResult(is_match=False, confidence=0.0)

        if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
            return MatchResult(is_match=False, confidence=0.0)

        # Calculate name similarity
        name_similarity = self._calculate_name_similarity(name1, name2)

        # Calculate location proximity score
        distance_meters = self._calculate_distance(lat1, lng1, lat2, lng2)
        location_score = self._distance_to_score(distance_meters)

        # If distance exceeds threshold, no match regardless of name
        if distance_meters > self.max_distance_meters:
            return MatchResult(
                is_match=False,
                confidence=0.0,
                details={
                    "name_similarity": name_similarity,
                    "distance_meters": distance_meters,
                    "reason": "distance_exceeded"
                }
            )

        # Combined confidence score
        confidence = (
            self.name_weight * name_similarity +
            self.location_weight * location_score
        )

        is_match = confidence >= self.threshold

        return MatchResult(
            is_match=is_match,
            confidence=confidence,
            match_type="fuzzy" if is_match else "",
            details={
                "name_similarity": name_similarity,
                "distance_meters": distance_meters,
                "location_score": location_score
            }
        )

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using fuzzy string matching."""
        # Normalize names
        name1 = name1.strip().lower()
        name2 = name2.strip().lower()

        # Use token sort ratio for better handling of word order differences
        similarity = fuzz.token_sort_ratio(name1, name2) / 100.0
        return similarity

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two coordinates in meters using Haversine formula.

        Args:
            lat1, lng1: Coordinates of first point
            lat2, lng2: Coordinates of second point

        Returns:
            Distance in meters
        """
        # Earth's radius in meters
        R = 6371000

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        # Haversine formula
        a = (
            math.sin(delta_lat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance

    def _distance_to_score(self, distance_meters: float) -> float:
        """
        Convert distance to a 0-1 score (closer = higher score).

        Uses exponential decay: score = e^(-distance / decay_constant)
        """
        # Decay constant: distance at which score = 0.37 (~37%)
        # Using 50m means venues within 50m get high scores
        decay_constant = 50.0

        score = math.exp(-distance_meters / decay_constant)
        return score


class Deduplicator:
    """
    Main deduplication orchestrator.

    Implements cascade of strategies: external ID → slug → fuzzy
    """

    def __init__(
        self,
        external_id_matcher: Optional[ExternalIDMatcher] = None,
        slug_matcher: Optional[SlugMatcher] = None,
        fuzzy_matcher: Optional[FuzzyMatcher] = None
    ):
        """Initialize deduplicator with optional custom matchers."""
        self.external_id_matcher = external_id_matcher or ExternalIDMatcher()
        self.slug_matcher = slug_matcher or SlugMatcher()
        self.fuzzy_matcher = fuzzy_matcher or FuzzyMatcher()

    def find_match(self, entity1: Dict[str, Any], entity2: Dict[str, Any]) -> MatchResult:
        """
        Find if two entities match using cascade of strategies.

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            MatchResult with highest confidence match found
        """
        # Strategy 1: External ID matching (highest confidence)
        result = self._match_external_id(entity1, entity2)
        if result.is_match:
            return result

        # Strategy 2: Slug matching
        result = self._match_slug(entity1, entity2)
        if result.is_match:
            return result

        # Strategy 3: Fuzzy name + location matching
        result = self._match_fuzzy(entity1, entity2)
        if result.is_match:
            return result

        # No match found
        return MatchResult(is_match=False, confidence=0.0)

    def find_duplicates(self, entities: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Find all duplicate groups in a list of entities.

        Args:
            entities: List of entities to check for duplicates

        Returns:
            List of duplicate groups, where each group contains 2+ duplicate entities
        """
        if len(entities) < 2:
            return []

        # Track which entities have been grouped
        grouped_ids = set()
        duplicate_groups = []

        for i, entity1 in enumerate(entities):
            entity1_id = entity1.get("id")

            # Skip if already grouped
            if entity1_id in grouped_ids:
                continue

            # Find all matches for this entity
            group = [entity1]
            grouped_ids.add(entity1_id)

            for j in range(i + 1, len(entities)):
                entity2 = entities[j]
                entity2_id = entity2.get("id")

                # Skip if already grouped
                if entity2_id in grouped_ids:
                    continue

                # Check for match
                result = self.find_match(entity1, entity2)
                if result.is_match:
                    group.append(entity2)
                    grouped_ids.add(entity2_id)

            # Only add groups with 2+ members
            if len(group) >= 2:
                duplicate_groups.append(group)

        return duplicate_groups

    def _match_external_id(self, entity1: Dict[str, Any], entity2: Dict[str, Any]) -> MatchResult:
        """Match using external IDs."""
        ids1 = entity1.get("external_ids", {})
        ids2 = entity2.get("external_ids", {})
        return self.external_id_matcher.match(ids1, ids2)

    def _match_slug(self, entity1: Dict[str, Any], entity2: Dict[str, Any]) -> MatchResult:
        """Match using slugs."""
        slug1 = entity1.get("slug")
        slug2 = entity2.get("slug")
        return self.slug_matcher.match(slug1, slug2)

    def _match_fuzzy(self, entity1: Dict[str, Any], entity2: Dict[str, Any]) -> MatchResult:
        """Match using fuzzy name + location."""
        return self.fuzzy_matcher.match(entity1, entity2)


class SlugGenerator:
    """Generate URL-safe slugs from entity names."""

    def generate(self, name: str, location: Optional[str] = None) -> str:
        """
        Generate URL-safe slug from entity name.

        Examples:
            "Edinburgh Padel Club" → "edinburgh-padel-club"
            "The Game4Padel - Portobello" → "game4padel-portobello"
            "Café Olé" → "cafe-ole"

        Args:
            name: Entity name
            location: Optional location to append

        Returns:
            URL-safe slug
        """
        # Remove articles (the, a, an) from start
        slug = re.sub(r'^(the|a|an)\s+', '', name.lower(), flags=re.IGNORECASE)

        # Convert Unicode to ASCII (accents: "Café" → "Cafe")
        slug = unidecode(slug)

        # Remove special characters (keep alphanumeric, spaces, hyphens)
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)

        # Replace spaces with hyphens
        slug = re.sub(r'\s+', '-', slug.strip())

        # Add location suffix if provided
        if location:
            location_slug = unidecode(location.lower())
            location_slug = re.sub(r'[^a-z0-9\s-]', '', location_slug)
            location_slug = re.sub(r'\s+', '-', location_slug.strip())
            slug = f"{slug}-{location_slug}"

        # Remove duplicate hyphens
        slug = re.sub(r'-+', '-', slug)

        # Strip leading/trailing hyphens
        return slug.strip('-')
