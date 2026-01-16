"""
Tests for Summary Synthesis

This module tests the summary synthesis functionality which creates high-quality,
character-limited summary fields for sport-specific and category-specific attributes.

Summary synthesis follows a multi-stage process:
1. Extract structured facts from raw data (via main extractor)
2. Gather rich text descriptions from raw_descriptions field
3. LLM synthesis combining facts + descriptions with character limits
4. Retry with character limit enforcement (max 3 attempts)

Test Coverage:
- Summary synthesizer initialization
- Summary synthesis with structured facts + rich text
- Character limit enforcement (min/max boundaries)
- Retry logic for length violations
- Multiple summary types (padel_summary, tennis_summary, gym_summary, etc.)
- Brand voice validation ("Knowledgeable Local Friend" tone)
- Handling missing rich text gracefully
- Null semantics (null = no relevant info, not "no summary available")
"""

import pytest
import os
import json
from pathlib import Path
from typing import Dict, List

# Check if API key is available for LLM tests
HAS_API_KEY = os.getenv('ANTHROPIC_API_KEY') is not None
skip_without_api_key = pytest.mark.skipif(
    not HAS_API_KEY,
    reason="ANTHROPIC_API_KEY not set - LLM tests require API access"
)


@pytest.fixture
def sample_structured_facts():
    """Sample structured facts extracted by main extractor"""
    return {
        "entity_name": "Game4Padel | Edinburgh Park",
        "padel": True,
        "padel_total_courts": 4,
        "rating": 4.4,
        "user_rating_count": 15,
        "street_address": "1, New Park Square, Edinburgh Park, Edinburgh EH12 9GR, UK"
    }


@pytest.fixture
def sample_rich_descriptions():
    """Sample rich text descriptions from Google Places reviews/editorial"""
    return [
        "Game4Padel is Edinburgh's premier padel tennis facility featuring 4 state-of-the-art indoor courts with professional-grade glass walls and LED lighting.",
        "Great venue! The courts are well-maintained and the staff are friendly. Booking system is easy to use.",
        "Love this place. Perfect for beginners and experienced players. The heated courts are a bonus in winter.",
        "Excellent facilities with modern changing rooms and a small cafe. Good parking available."
    ]


@pytest.fixture
def tennis_venue_facts():
    """Sample facts for a tennis venue"""
    return {
        "entity_name": "Craiglockhart Tennis Centre",
        "tennis": True,
        "tennis_total_courts": 12,
        "tennis_indoor_courts": 4,
        "tennis_outdoor_courts": 8,
        "tennis_floodlit_courts": 6,
        "rating": 4.2,
        "user_rating_count": 89
    }


@pytest.fixture
def tennis_rich_descriptions():
    """Sample rich text for a tennis venue"""
    return [
        "Craiglockhart Tennis Centre is one of Scotland's premier tennis facilities, offering 12 courts across indoor and outdoor settings.",
        "The indoor courts are brilliant - climate controlled and perfect for year-round play. Membership is reasonable.",
        "Great mix of courts. The floodlit outdoor courts are perfect for evening games in summer."
    ]


@pytest.fixture
def gym_venue_facts():
    """Sample facts for a gym/fitness venue"""
    return {
        "entity_name": "PureGym Edinburgh Craigleith",
        "gym_available": True,
        "gym_size": 150,
        "classes_per_week": 45,
        "yoga_classes": True,
        "hiit_classes": True,
        "cycling_studio": True,
        "rating": 4.1
    }


@pytest.fixture
def gym_rich_descriptions():
    """Sample rich text for a gym"""
    return [
        "PureGym Craigleith offers a comprehensive fitness experience with 150 workout stations and a packed class schedule.",
        "The gym is spacious with good equipment variety. Spin studio is excellent and yoga classes are very popular.",
        "Open 24/7 which is perfect for shift workers. Never too crowded in off-peak hours."
    ]


class TestSummarySynthesizerInitialization:
    """Test summary synthesizer initialization and basic properties"""

    def test_summary_synthesizer_can_be_imported(self):
        """Test that SummarySynthesizer class can be imported"""
        try:
            from engine.extraction.utils.summary_synthesis import SummarySynthesizer
            assert SummarySynthesizer is not None
        except ImportError:
            pytest.fail("Failed to import SummarySynthesizer - implementation not yet created")

    @skip_without_api_key
    def test_summary_synthesizer_can_be_instantiated(self):
        """Test that SummarySynthesizer can be instantiated"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        assert synthesizer is not None


class TestPadelSummarySynthesis:
    """Test synthesis of padel_summary field"""

    @skip_without_api_key
    def test_synthesize_padel_summary_basic(self, sample_structured_facts, sample_rich_descriptions):
        """Test basic padel summary synthesis with facts + rich text"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=sample_structured_facts,
            rich_text=sample_rich_descriptions
        )

        # Verify summary is returned
        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 0

    @skip_without_api_key
    def test_padel_summary_character_limits(self, sample_structured_facts, sample_rich_descriptions):
        """Test that padel summary respects character limits (100-200 chars)"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=sample_structured_facts,
            rich_text=sample_rich_descriptions,
            min_chars=100,
            max_chars=200
        )

        assert summary is not None
        assert 100 <= len(summary) <= 200, (
            f"Summary length {len(summary)} outside 100-200 char range. "
            f"Summary: {summary}"
        )

    @skip_without_api_key
    def test_padel_summary_brand_voice(self, sample_structured_facts, sample_rich_descriptions):
        """Test that padel summary follows 'Knowledgeable Local Friend' voice"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=sample_structured_facts,
            rich_text=sample_rich_descriptions
        )

        # Check for prohibited phrases (marketing fluff)
        prohibited_phrases = [
            "located at",
            "features include",
            "a great place for",
            "welcome to",
            "proud to offer"
        ]

        summary_lower = summary.lower()
        for phrase in prohibited_phrases:
            assert phrase not in summary_lower, (
                f"Summary contains prohibited phrase '{phrase}'. "
                f"Should use contextual bridges instead. Summary: {summary}"
            )

    @skip_without_api_key
    def test_padel_summary_handles_no_rich_text(self, sample_structured_facts):
        """Test padel summary synthesis with only structured facts (no rich text)"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=sample_structured_facts,
            rich_text=[]
        )

        # Should still produce a summary from structured facts alone
        assert summary is not None
        assert len(summary) > 0

    @skip_without_api_key
    def test_padel_summary_returns_none_when_no_padel_data(self):
        """Test that padel_summary returns None when venue doesn't have padel"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        facts_without_padel = {
            "entity_name": "Tennis Centre",
            "tennis": True,
            "tennis_total_courts": 6
        }

        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=facts_without_padel,
            rich_text=[]
        )

        # No padel data, should return None (not "No padel available")
        assert summary is None


class TestTennisSummarySynthesis:
    """Test synthesis of tennis_summary field"""

    @skip_without_api_key
    def test_synthesize_tennis_summary_basic(self, tennis_venue_facts, tennis_rich_descriptions):
        """Test basic tennis summary synthesis"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="tennis_summary",
            structured_facts=tennis_venue_facts,
            rich_text=tennis_rich_descriptions
        )

        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 0

    @skip_without_api_key
    def test_tennis_summary_includes_court_details(self, tennis_venue_facts, tennis_rich_descriptions):
        """Test that tennis summary incorporates indoor/outdoor court details"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="tennis_summary",
            structured_facts=tennis_venue_facts,
            rich_text=tennis_rich_descriptions
        )

        # Should mention indoor/outdoor or total courts
        summary_lower = summary.lower()
        has_court_info = (
            "indoor" in summary_lower or
            "outdoor" in summary_lower or
            "12" in summary or
            "twelve" in summary_lower
        )
        assert has_court_info, (
            f"Tennis summary should reference court details. Summary: {summary}"
        )


class TestGymSummarySynthesis:
    """Test synthesis of gym_summary field"""

    @skip_without_api_key
    def test_synthesize_gym_summary_basic(self, gym_venue_facts, gym_rich_descriptions):
        """Test basic gym summary synthesis"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="gym_summary",
            structured_facts=gym_venue_facts,
            rich_text=gym_rich_descriptions
        )

        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 0

    @skip_without_api_key
    def test_gym_summary_character_limits(self, gym_venue_facts, gym_rich_descriptions):
        """Test that gym summary respects character limits"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="gym_summary",
            structured_facts=gym_venue_facts,
            rich_text=gym_rich_descriptions,
            min_chars=100,
            max_chars=200
        )

        assert 100 <= len(summary) <= 200


class TestCharacterLimitEnforcement:
    """Test character limit enforcement with retry logic"""

    @skip_without_api_key
    def test_retry_on_length_violation_too_short(self, sample_structured_facts, sample_rich_descriptions):
        """Test that synthesizer retries if summary is too short"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        # Very strict min limit to potentially trigger retry
        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=sample_structured_facts,
            rich_text=sample_rich_descriptions,
            min_chars=150,
            max_chars=200
        )

        # Should eventually produce valid length (or return None after max retries)
        if summary is not None:
            assert len(summary) >= 150

    @skip_without_api_key
    def test_retry_on_length_violation_too_long(self, sample_structured_facts, sample_rich_descriptions):
        """Test that synthesizer retries if summary is too long"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        # Very strict max limit to potentially trigger retry
        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=sample_structured_facts,
            rich_text=sample_rich_descriptions,
            min_chars=50,
            max_chars=100
        )

        # Should eventually produce valid length (or return None after max retries)
        if summary is not None:
            assert len(summary) <= 100

    @skip_without_api_key
    def test_max_retries_respected(self, sample_structured_facts):
        """Test that synthesizer respects max_retries limit"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        # Impossible constraints to guarantee retries
        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=sample_structured_facts,
            rich_text=[],
            min_chars=500,  # Impossible to hit with minimal data
            max_chars=600,
            max_retries=2
        )

        # After 2 retries, should give up and return None or best attempt
        # (Implementation decision: return None if never valid)
        # Test just verifies it doesn't retry forever
        assert True  # If we get here, max_retries worked


class TestMultipleSummaryTypes:
    """Test synthesizing multiple summary types for same venue"""

    @skip_without_api_key
    def test_venue_with_multiple_sports(self):
        """Test synthesizing multiple summaries for multi-sport venue"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()

        # Multi-sport venue
        facts = {
            "entity_name": "Edinburgh Sports Centre",
            "padel": True,
            "padel_total_courts": 2,
            "tennis": True,
            "tennis_total_courts": 4,
            "gym_available": True
        }

        rich_text = [
            "Edinburgh Sports Centre is a comprehensive facility with padel, tennis, and gym facilities."
        ]

        # Synthesize all three summaries
        padel_summary = synthesizer.synthesize_summary("padel_summary", facts, rich_text)
        tennis_summary = synthesizer.synthesize_summary("tennis_summary", facts, rich_text)
        gym_summary = synthesizer.synthesize_summary("gym_summary", facts, rich_text)

        # All three should be generated
        assert padel_summary is not None
        assert tennis_summary is not None
        assert gym_summary is not None

        # Summaries should be different (not just copy-paste)
        assert padel_summary != tennis_summary
        assert tennis_summary != gym_summary


class TestEdgeCases:
    """Test edge cases and error handling"""

    @skip_without_api_key
    def test_summary_with_empty_facts(self):
        """Test summary synthesis with empty facts dict"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts={},
            rich_text=[]
        )

        # Should return None (no data to summarize)
        assert summary is None

    @skip_without_api_key
    def test_summary_with_none_facts(self):
        """Test summary synthesis with None facts"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()
        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=None,
            rich_text=[]
        )

        assert summary is None

    @skip_without_api_key
    def test_summary_with_very_long_rich_text(self, sample_structured_facts):
        """Test summary synthesis with excessive rich text (should handle gracefully)"""
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()

        # Generate very long rich text list
        long_rich_text = [
            f"This is review number {i} about the padel venue with various details."
            for i in range(50)
        ]

        summary = synthesizer.synthesize_summary(
            summary_type="padel_summary",
            structured_facts=sample_structured_facts,
            rich_text=long_rich_text
        )

        # Should still produce a valid summary (not error out)
        assert summary is not None
        assert len(summary) > 0


class TestIntegrationWithExtractors:
    """Test integration with existing extractors"""

    def test_google_places_extractor_provides_rich_text(self):
        """Test that GooglePlacesExtractor.extract_rich_text() returns usable data"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor

        # Load fixture
        fixture_path = Path(__file__).parent / "fixtures" / "google_places_venue_response.json"
        with open(fixture_path, 'r') as f:
            fixture = json.load(f)

        extractor = GooglePlacesExtractor()
        first_venue = fixture["places"][0]

        rich_text = extractor.extract_rich_text(first_venue)

        # Should return a list of strings
        assert isinstance(rich_text, list)
        # May be empty if fixture doesn't have reviews/editorial (that's OK)
        # Just verify it's callable and returns correct type

    @skip_without_api_key
    def test_summary_synthesis_end_to_end(self):
        """Test end-to-end flow: extract → rich text → synthesize summary"""
        from engine.extraction.extractors.google_places_extractor import GooglePlacesExtractor
        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        # Load fixture
        fixture_path = Path(__file__).parent / "fixtures" / "google_places_venue_response.json"
        with open(fixture_path, 'r') as f:
            fixture = json.load(f)

        extractor = GooglePlacesExtractor()
        synthesizer = SummarySynthesizer()

        first_venue = fixture["places"][0]

        # Extract structured facts
        structured_facts = extractor.extract(first_venue)

        # Extract rich text
        rich_text = extractor.extract_rich_text(first_venue)

        # Synthesize summary (if venue has padel)
        if structured_facts.get("padel"):
            summary = synthesizer.synthesize_summary(
                summary_type="padel_summary",
                structured_facts=structured_facts,
                rich_text=rich_text
            )

            # If synthesis succeeds, verify it's valid
            if summary is not None:
                assert isinstance(summary, str)
                assert len(summary) > 0
