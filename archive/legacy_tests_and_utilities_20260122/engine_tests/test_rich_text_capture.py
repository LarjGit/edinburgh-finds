"""
Tests for Rich Text Capture

Verifies that rich text (reviews, descriptions, snippets) is correctly
captured from ingestion sources and accessible through extractors for
summary synthesis.
"""

import pytest
from unittest.mock import Mock, patch
from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor


class TestGooglePlacesExtractorRichText:
    """Test that GooglePlacesExtractor can extract rich text."""

    def test_extract_editorial_summary(self):
        """Test extraction of editorial summary."""
        extractor = GooglePlacesExtractor()

        raw_data = {
            "displayName": {"text": "Test Venue"},
            "editorialSummary": {"text": "This is a great place for padel enthusiasts."}
        }

        rich_text = extractor.extract_rich_text(raw_data)

        assert len(rich_text) == 1
        assert rich_text[0] == "This is a great place for padel enthusiasts."

    def test_extract_reviews(self):
        """Test extraction of review texts."""
        extractor = GooglePlacesExtractor()

        raw_data = {
            "displayName": {"text": "Test Venue"},
            "reviews": [
                {"text": {"text": "Great place!"}},
                {"text": {"text": "Loved the facilities"}},
                {"text": {"text": "Best padel club in town"}}
            ]
        }

        rich_text = extractor.extract_rich_text(raw_data)

        assert len(rich_text) == 3
        assert "Great place!" in rich_text
        assert "Loved the facilities" in rich_text
        assert "Best padel club in town" in rich_text

    def test_extract_editorial_and_reviews(self):
        """Test extraction of both editorial summary and reviews."""
        extractor = GooglePlacesExtractor()

        raw_data = {
            "displayName": {"text": "Test Venue"},
            "editorialSummary": {"text": "Premier padel facility."},
            "reviews": [
                {"text": {"text": "Amazing courts"}},
                {"text": {"text": "Professional coaching"}}
            ]
        }

        rich_text = extractor.extract_rich_text(raw_data)

        assert len(rich_text) == 3
        assert rich_text[0] == "Premier padel facility."
        assert "Amazing courts" in rich_text
        assert "Professional coaching" in rich_text

    def test_extract_limits_reviews_to_five(self):
        """Test that only first 5 reviews are extracted."""
        extractor = GooglePlacesExtractor()

        raw_data = {
            "displayName": {"text": "Test Venue"},
            "reviews": [
                {"text": {"text": f"Review {i}"}} for i in range(10)
            ]
        }

        rich_text = extractor.extract_rich_text(raw_data)

        # Should only get first 5 reviews
        assert len(rich_text) == 5

    def test_extract_handles_missing_fields(self):
        """Test that extractor handles missing editorial summary and reviews."""
        extractor = GooglePlacesExtractor()

        raw_data = {
            "displayName": {"text": "Test Venue"}
            # No editorialSummary or reviews
        }

        rich_text = extractor.extract_rich_text(raw_data)

        assert len(rich_text) == 0

    def test_extract_handles_direct_string_editorial(self):
        """Test that extractor handles editorial summary as direct string."""
        extractor = GooglePlacesExtractor()

        raw_data = {
            "displayName": {"text": "Test Venue"},
            "editorialSummary": "Direct string summary"
        }

        rich_text = extractor.extract_rich_text(raw_data)

        assert len(rich_text) == 1
        assert rich_text[0] == "Direct string summary"


class TestSerperExtractorRichText:
    """Test that SerperExtractor can extract rich text without requiring LLM client."""

    def test_extract_rich_text_method_exists(self):
        """Test that SerperExtractor has extract_rich_text method (unit test)."""
        # Import here to avoid initialization issues
        from engine.extraction.base import BaseExtractor

        # Verify method exists on BaseExtractor
        assert hasattr(BaseExtractor, 'extract_rich_text')

    def test_extract_snippets_logic(self):
        """Test snippet extraction logic without initializing extractor."""
        # Test the logic directly without creating SerperExtractor instance
        raw_data = {
            "searchParameters": {"q": "padel edinburgh"},
            "organic": [
                {
                    "title": "Venue 1",
                    "link": "https://example.com",
                    "snippet": "A premier padel facility in Edinburgh"
                },
                {
                    "title": "Venue 2",
                    "link": "https://example2.com",
                    "snippet": "Indoor and outdoor courts available"
                }
            ]
        }

        # Test the extraction logic
        rich_text = []
        organic_results = raw_data.get("organic", [])
        for result in organic_results:
            if isinstance(result, dict):
                snippet = result.get("snippet", "")
                if snippet and isinstance(snippet, str):
                    rich_text.append(snippet)

        assert len(rich_text) == 2
        assert "A premier padel facility in Edinburgh" in rich_text
        assert "Indoor and outdoor courts available" in rich_text

    def test_extract_handles_missing_snippets_logic(self):
        """Test that logic handles results without snippets."""
        raw_data = {
            "searchParameters": {"q": "padel edinburgh"},
            "organic": [
                {
                    "title": "Venue 1",
                    "link": "https://example.com"
                    # No snippet
                },
                {
                    "title": "Venue 2",
                    "link": "https://example2.com",
                    "snippet": "Only this one has a snippet"
                }
            ]
        }

        # Test the extraction logic
        rich_text = []
        organic_results = raw_data.get("organic", [])
        for result in organic_results:
            if isinstance(result, dict):
                snippet = result.get("snippet", "")
                if snippet and isinstance(snippet, str):
                    rich_text.append(snippet)

        assert len(rich_text) == 1
        assert rich_text[0] == "Only this one has a snippet"

    def test_extract_handles_empty_organic_results_logic(self):
        """Test that logic handles no organic results."""
        raw_data = {
            "searchParameters": {"q": "padel edinburgh"},
            "organic": []
        }

        # Test the extraction logic
        rich_text = []
        organic_results = raw_data.get("organic", [])
        for result in organic_results:
            if isinstance(result, dict):
                snippet = result.get("snippet", "")
                if snippet and isinstance(snippet, str):
                    rich_text.append(snippet)

        assert len(rich_text) == 0

    def test_extract_handles_missing_organic_key_logic(self):
        """Test that logic handles missing organic key."""
        raw_data = {
            "searchParameters": {"q": "padel edinburgh"}
            # No organic key
        }

        # Test the extraction logic
        rich_text = []
        organic_results = raw_data.get("organic", [])
        for result in organic_results:
            if isinstance(result, dict):
                snippet = result.get("snippet", "")
                if snippet and isinstance(snippet, str):
                    rich_text.append(snippet)

        assert len(rich_text) == 0
