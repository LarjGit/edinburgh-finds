"""
Tests for LLM Prompt Improvements - Orchestration Pipeline

This test suite verifies three key improvements to LLM extraction prompts:
1. Concise Summaries - No verbose AI-sounding fluff
2. Improved Classification - Accurate entity_class and canonical_roles
3. Uncertainty Handling - Return null for uncertain data instead of hallucinating

These tests use mocked LLM responses to verify prompt structure and behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from engine.extraction.extractors.serper_extractor import SerperExtractor
from engine.extraction.extractors.osm_extractor import OSMExtractor
from engine.extraction.models.entity_extraction import EntityExtraction


class TestPromptStructure:
    """Test that prompts contain the required improvement sections"""

    def test_serper_prompt_contains_uncertainty_handling(self):
        """Serper prompt should have explicit uncertainty handling instructions"""
        # Mock LLM client to avoid API key requirement
        mock_llm = Mock()
        extractor = SerperExtractor(llm_client=mock_llm)
        prompt = extractor.system_message

        # Check for uncertainty handling keywords
        assert "uncertain" in prompt.lower() or "hallucination" in prompt.lower(), \
            "Prompt should contain uncertainty handling instructions"
        assert "null" in prompt.lower(), \
            "Prompt should emphasize using null for uncertain data"

    def test_osm_prompt_contains_uncertainty_handling(self):
        """OSM prompt should have explicit uncertainty handling instructions"""
        # Mock LLM client to avoid API key requirement
        mock_llm = Mock()
        extractor = OSMExtractor(llm_client=mock_llm)
        prompt = extractor.system_message

        # Check for uncertainty handling keywords
        assert "uncertain" in prompt.lower() or "hallucination" in prompt.lower(), \
            "Prompt should contain uncertainty handling instructions"
        assert "null" in prompt.lower(), \
            "Prompt should emphasize using null for uncertain data"

    def test_classification_rules_include_dimensions(self):
        """Classification rules should mention canonical_roles (dimensions)"""
        # Mock LLM client to avoid API key requirement
        mock_llm = Mock()
        extractor = SerperExtractor(llm_client=mock_llm)
        classification_rules = extractor._get_classification_rules()

        assert "canonical_roles" in classification_rules, \
            "Classification rules should include canonical_roles guidance"
        assert "entity_class" in classification_rules, \
            "Classification rules should include entity_class guidance"

    def test_serper_prompt_mentions_concise_summaries(self):
        """Serper prompt should emphasize concise extraction"""
        # Mock LLM client to avoid API key requirement
        mock_llm = Mock()
        extractor = SerperExtractor(llm_client=mock_llm)
        prompt = extractor.system_message

        # Check for conciseness emphasis
        assert "concise" in prompt.lower() or "brief" in prompt.lower(), \
            "Prompt should emphasize concise output"


class TestUncertaintyHandling:
    """Test that extractors properly handle uncertain data with null values"""

    def test_serper_returns_null_for_ambiguous_address(self, mock_ctx):
        """When address fragments are ambiguous, should return null instead of guessing"""
        mock_llm_client = Mock()

        # Mock LLM to return extraction with null for uncertain address
        mock_extraction = EntityExtraction(
            entity_name="Edinburgh Sports Centre",
            entity_class="place",
            street_address=None,  # Uncertain, so null
            city="Edinburgh",
            postcode=None,  # Not mentioned
            latitude=None,
            longitude=None,
            phone=None,
            website=None,
            canonical_activities=["padel"],
            canonical_roles=["provides_facility"]
        )
        mock_llm_client.extract.return_value = mock_extraction

        extractor = SerperExtractor(llm_client=mock_llm_client)

        # Ambiguous search results (only city mentioned, no street)
        raw_data = {
            "organic": [
                {
                    "title": "Edinburgh Sports Centre",
                    "snippet": "Sports centre in Edinburgh offering padel",
                    "link": "https://example.com"
                }
            ]
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Should use null for missing/uncertain fields
        assert extracted["street_address"] is None, \
            "Should return null for uncertain address, not guess or hallucinate"
        assert extracted["postcode"] is None, \
            "Should return null for missing postcode"

    def test_serper_returns_null_for_uncertain_phone(self, mock_ctx):
        """When phone number is unclear or incomplete, should return null"""
        mock_llm_client = Mock()

        # Mock LLM to return extraction with null for uncertain phone
        mock_extraction = EntityExtraction(
            entity_name="Game4Padel",
            entity_class="place",
            street_address="1 New Park Square",
            city="Edinburgh",
            phone=None,  # Uncertain format, so null
            canonical_activities=["padel"],
            canonical_roles=["provides_facility"]
        )
        mock_llm_client.extract.return_value = mock_extraction

        extractor = SerperExtractor(llm_client=mock_llm_client)

        # Search results with ambiguous phone mention
        raw_data = {
            "organic": [
                {
                    "title": "Game4Padel",
                    "snippet": "Call us for info at xxx-xxxx",  # Incomplete phone
                    "link": "https://example.com"
                }
            ]
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Should use null for incomplete/uncertain phone
        assert extracted["phone"] is None, \
            "Should return null for uncertain phone number format"


class TestClassificationImprovement:
    """Test that entity classification guidance is present in prompts"""

    def test_classification_rules_mention_place_type(self):
        """Classification rules should mention 'place' entity_class"""
        mock_llm = Mock()
        extractor = SerperExtractor(llm_client=mock_llm)
        classification_rules = extractor._get_classification_rules()

        assert "place" in classification_rules.lower(), \
            "Classification rules should mention 'place' entity_class"
        assert "physical location" in classification_rules.lower() or \
               "coordinates" in classification_rules.lower(), \
            "Classification rules should explain when to use entity_class=place"

    def test_classification_rules_mention_person_type(self):
        """Classification rules should mention 'person' entity_class"""
        mock_llm = Mock()
        extractor = SerperExtractor(llm_client=mock_llm)
        classification_rules = extractor._get_classification_rules()

        assert "person" in classification_rules.lower(), \
            "Classification rules should mention 'person' entity_class"
        assert "individual" in classification_rules.lower() or \
               "named individual" in classification_rules.lower(), \
            "Classification rules should explain when to use entity_class=person"

    def test_classification_rules_mention_event_type(self):
        """Classification rules should mention 'event' entity_class"""
        mock_llm = Mock()
        extractor = SerperExtractor(llm_client=mock_llm)
        classification_rules = extractor._get_classification_rules()

        assert "event" in classification_rules.lower(), \
            "Classification rules should mention 'event' entity_class"
        assert "time-bounded" in classification_rules.lower() or \
               "start/end" in classification_rules.lower(), \
            "Classification rules should explain when to use entity_class=event"

    def test_classification_rules_mention_role_examples(self):
        """Classification rules should provide canonical_roles examples"""
        mock_llm = Mock()
        extractor = SerperExtractor(llm_client=mock_llm)
        classification_rules = extractor._get_classification_rules()

        # Check for role examples
        assert "provides_facility" in classification_rules or \
               "provides_instruction" in classification_rules or \
               "sells_goods" in classification_rules, \
            "Classification rules should provide canonical_roles examples"


class TestConciseSummaries:
    """Test that summaries are concise and avoid verbose AI-sounding language"""

    @patch('engine.extraction.utils.summary_synthesis.InstructorClient')
    def test_summary_synthesis_prompt_emphasizes_conciseness(self, mock_instructor_class):
        """Summary synthesis should have explicit conciseness instructions"""
        # Mock the InstructorClient to avoid API key requirement
        mock_instructor_class.return_value = Mock()

        from engine.extraction.utils.summary_synthesis import SummarySynthesizer

        synthesizer = SummarySynthesizer()

        # Check brand voice rules for conciseness
        assert "concise" in synthesizer.brand_voice_rules.lower() or \
               "brief" in synthesizer.brand_voice_rules.lower(), \
            "Brand voice rules should emphasize conciseness"

        # Check prohibited phrases are defined
        assert "PROHIBITED PHRASES" in synthesizer.brand_voice_rules, \
            "Should define prohibited verbose phrases"
        assert "Located at" in synthesizer.brand_voice_rules, \
            "Should prohibit 'Located at' phrase"

    def test_prompt_prohibits_verbose_phrases(self):
        """Extraction prompts should prohibit verbose AI-sounding phrases"""
        # Mock LLM client to avoid API key requirement
        mock_llm = Mock()
        extractor = SerperExtractor(llm_client=mock_llm)
        prompt = extractor.system_message

        # Check that prompt discourages verbose language
        assert "fluff" in prompt.lower() or "generic" in prompt.lower(), \
            "Prompt should discourage generic/fluffy language"


class TestPromptIntegration:
    """Integration tests verifying end-to-end prompt behavior"""

    @pytest.mark.slow
    def test_serper_extractor_uses_improved_prompt(self):
        """Verify SerperExtractor loads and uses the improved prompt template"""
        # Mock LLM client to avoid API key requirement
        mock_llm = Mock()
        extractor = SerperExtractor(llm_client=mock_llm)

        # Verify prompt is loaded
        assert extractor.system_message is not None
        assert len(extractor.system_message) > 100, \
            "System message should contain substantial prompt content"

        # Verify classification rules are injected
        assert "entity_class" in extractor.system_message
        assert "canonical_roles" in extractor.system_message

    @pytest.mark.slow
    def test_osm_extractor_uses_improved_prompt(self):
        """Verify OSMExtractor loads and uses the improved prompt template"""
        # Mock LLM client to avoid API key requirement
        mock_llm = Mock()
        extractor = OSMExtractor(llm_client=mock_llm)

        # Verify prompt is loaded
        assert extractor.system_message is not None
        assert len(extractor.system_message) > 100, \
            "System message should contain substantial prompt content"

        # Verify classification rules are injected
        assert "entity_class" in extractor.system_message
        assert "canonical_roles" in extractor.system_message
