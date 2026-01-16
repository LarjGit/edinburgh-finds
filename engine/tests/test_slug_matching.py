"""
Tests for slug-based deduplication matching.

Slugs are URL-safe identifiers derived from entity names.
They provide a good secondary matching strategy when external IDs are not available.
"""

import pytest
from engine.extraction.deduplication import SlugMatcher, MatchResult


class TestSlugMatcher:
    """Test slug-based matching logic."""

    def test_exact_slug_match(self):
        """Should match two listings with identical slugs."""
        matcher = SlugMatcher()

        result = matcher.match("game4padel-edinburgh", "game4padel-edinburgh")

        assert result.is_match is True
        assert result.confidence == 1.0
        assert result.match_type == "slug"

    def test_no_match_different_slugs(self):
        """Should not match listings with different slugs."""
        matcher = SlugMatcher()

        result = matcher.match("game4padel-edinburgh", "padel-hub-glasgow")

        assert result.is_match is False
        assert result.confidence < 0.9  # Below similarity threshold

    def test_case_insensitive_matching(self):
        """Slug matching should be case-insensitive."""
        matcher = SlugMatcher()

        result = matcher.match("Game4Padel-Edinburgh", "game4padel-edinburgh")

        assert result.is_match is True
        assert result.confidence == 1.0

    def test_no_match_empty_slugs(self):
        """Should not match if either slug is empty or None."""
        matcher = SlugMatcher()

        assert matcher.match("", "game4padel-edinburgh").is_match is False
        assert matcher.match("game4padel-edinburgh", "").is_match is False
        assert matcher.match("", "").is_match is False
        assert matcher.match(None, "game4padel-edinburgh").is_match is False
        assert matcher.match("game4padel-edinburgh", None).is_match is False

    def test_whitespace_normalization(self):
        """Should normalize whitespace in slugs."""
        matcher = SlugMatcher()

        result = matcher.match(" game4padel-edinburgh ", "game4padel-edinburgh")

        assert result.is_match is True
        assert result.confidence == 1.0

    def test_slug_similarity_threshold(self):
        """Should match very similar slugs (typo tolerance)."""
        matcher = SlugMatcher()

        # Very similar slugs (one character difference)
        result = matcher.match("game4padel-edinburgh", "game4padel-edinburh")

        # This should match with high confidence (typo tolerance)
        assert result.is_match is True
        assert result.confidence >= 0.9

    def test_no_match_dissimilar_slugs(self):
        """Should not match dissimilar slugs."""
        matcher = SlugMatcher()

        result = matcher.match("game4padel-edinburgh", "tennis-club-london")

        assert result.is_match is False
        assert result.confidence < 0.5
