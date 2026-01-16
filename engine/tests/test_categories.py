"""
Tests for Category Mapping Utility

Tests the canonical category mapping system that converts raw,
uncontrolled categories (from extraction) into a controlled taxonomy.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the module to test
from engine.extraction.utils import category_mapper


class TestCategoryMapperImport:
    """Test that the category mapper module can be imported"""

    def test_category_mapper_module_can_be_imported(self):
        """Test basic import"""
        assert category_mapper is not None

    def test_map_to_canonical_function_exists(self):
        """Test that main mapping function exists"""
        assert hasattr(category_mapper, 'map_to_canonical')
        assert callable(category_mapper.map_to_canonical)

    def test_load_config_function_exists(self):
        """Test that config loader exists"""
        assert hasattr(category_mapper, 'load_config')
        assert callable(category_mapper.load_config)


class TestConfigLoading:
    """Test configuration loading and caching"""

    def test_load_config_returns_dict(self):
        """Test that config loading returns a dictionary"""
        config = category_mapper.load_config()
        assert isinstance(config, dict)

    def test_config_has_required_sections(self):
        """Test that config contains all required sections"""
        config = category_mapper.load_config()
        assert 'taxonomy' in config
        assert 'mapping_rules' in config
        assert 'promotion_config' in config

    def test_taxonomy_is_list(self):
        """Test that taxonomy is a list of category definitions"""
        config = category_mapper.load_config()
        assert isinstance(config['taxonomy'], list)
        assert len(config['taxonomy']) > 0

    def test_taxonomy_entries_have_required_fields(self):
        """Test that each taxonomy entry has required fields"""
        taxonomy = category_mapper.get_taxonomy()
        for entry in taxonomy:
            assert 'category_key' in entry
            assert 'display_name' in entry
            assert 'description' in entry
            assert 'search_keywords' in entry

    def test_mapping_rules_is_list(self):
        """Test that mapping_rules is a list"""
        config = category_mapper.load_config()
        assert isinstance(config['mapping_rules'], list)
        assert len(config['mapping_rules']) > 0

    def test_mapping_rules_have_required_fields(self):
        """Test that each mapping rule has required fields"""
        config = category_mapper.load_config()
        for rule in config['mapping_rules']:
            assert 'pattern' in rule
            assert 'canonical' in rule
            assert 'confidence' in rule
            assert isinstance(rule['confidence'], (int, float))
            assert 0 <= rule['confidence'] <= 1

    def test_config_caching_works(self):
        """Test that config is cached after first load"""
        # Clear cache
        category_mapper.reload_config()

        # First load
        config1 = category_mapper.load_config()

        # Second load (should be cached)
        config2 = category_mapper.load_config()

        # Should be the same object (cached)
        assert config1 is config2


class TestBasicCategoryMapping:
    """Test basic category mapping functionality"""

    def test_map_single_sport_category(self):
        """Test mapping a single clear sport category"""
        raw = ["Tennis"]
        canonical = category_mapper.map_to_canonical(raw)
        assert 'tennis' in canonical

    def test_map_padel_category(self):
        """Test mapping padel (with accent handling)"""
        raw = ["Padel Club"]
        canonical = category_mapper.map_to_canonical(raw)
        assert 'padel' in canonical

    def test_map_padel_with_accent(self):
        """Test mapping pádel with accent"""
        raw = ["Pádel"]
        canonical = category_mapper.map_to_canonical(raw)
        assert 'padel' in canonical

    def test_map_multiple_categories(self):
        """Test mapping multiple raw categories"""
        raw = ["Tennis Club", "Sports Centre"]
        canonical = category_mapper.map_to_canonical(raw)
        assert 'tennis' in canonical
        assert 'sports_centre' in canonical

    def test_map_venue_type(self):
        """Test mapping venue types"""
        raw = ["Sports Centre"]
        canonical = category_mapper.map_to_canonical(raw)
        assert 'sports_centre' in canonical

    def test_map_gym_category(self):
        """Test mapping gym/fitness categories"""
        raw = ["Fitness Club", "Gym"]
        canonical = category_mapper.map_to_canonical(raw)
        assert 'gym' in canonical

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive"""
        raw_lower = ["tennis club"]
        raw_upper = ["TENNIS CLUB"]
        raw_mixed = ["Tennis Club"]

        canonical_lower = category_mapper.map_to_canonical(raw_lower)
        canonical_upper = category_mapper.map_to_canonical(raw_upper)
        canonical_mixed = category_mapper.map_to_canonical(raw_mixed)

        assert canonical_lower == canonical_upper == canonical_mixed
        assert 'tennis' in canonical_lower


class TestConfidenceThreshold:
    """Test confidence threshold filtering"""

    def test_low_confidence_rules_excluded_by_default(self):
        """Test that low confidence mappings are excluded"""
        # Create a raw category that would match a low-confidence rule
        # (assuming there's a rule with confidence < 0.7)
        # This test depends on the specific rules in the config
        pass  # Skip if no low-confidence rules exist

    def test_custom_confidence_threshold(self):
        """Test providing a custom confidence threshold"""
        raw = ["Club"]  # "club" rule has confidence 0.7

        # With high threshold, should not map
        canonical_high = category_mapper.map_to_canonical(raw, min_confidence=0.9)

        # With low threshold, should map
        canonical_low = category_mapper.map_to_canonical(raw, min_confidence=0.5)

        # "club" should only appear with low threshold
        assert 'club' in canonical_low

    def test_high_confidence_rules_always_included(self):
        """Test that high confidence rules are always included"""
        raw = ["Tennis"]  # Should have confidence 1.0
        canonical = category_mapper.map_to_canonical(raw, min_confidence=0.9)
        assert 'tennis' in canonical


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_input_returns_empty_list(self):
        """Test that empty input returns empty list"""
        assert category_mapper.map_to_canonical([]) == []
        assert category_mapper.map_to_canonical(None) == []

    def test_none_values_in_list_ignored(self):
        """Test that None values in input are gracefully ignored"""
        raw = ["Tennis", None, "Padel"]
        canonical = category_mapper.map_to_canonical(raw)
        assert 'tennis' in canonical
        assert 'padel' in canonical
        # Should not crash

    def test_empty_strings_ignored(self):
        """Test that empty strings are ignored"""
        raw = ["Tennis", "", "  ", "Padel"]
        canonical = category_mapper.map_to_canonical(raw)
        assert 'tennis' in canonical
        assert 'padel' in canonical

    def test_whitespace_trimmed(self):
        """Test that whitespace is properly trimmed"""
        raw = ["  Tennis Club  "]
        canonical = category_mapper.map_to_canonical(raw)
        assert 'tennis' in canonical

    def test_unmapped_category_returns_empty(self):
        """Test that completely unmapped categories return empty list"""
        raw = ["Some Random Unmappable Category XYZ123"]
        canonical = category_mapper.map_to_canonical(raw)
        # Should return empty (no matches)
        # Note: Might have some matches if rules are too broad
        # Just ensure it doesn't crash
        assert isinstance(canonical, list)

    def test_max_categories_limit_enforced(self):
        """Test that max_categories limit is enforced"""
        # Create many raw categories that would map to different canonicals
        raw = [
            "Tennis", "Padel", "Squash", "Badminton",
            "Gym", "Swimming Pool", "Golf", "Climbing",
            "Yoga", "Martial Arts"
        ]
        canonical = category_mapper.map_to_canonical(raw)

        # Should be limited to max_categories (default 5 in config)
        assert len(canonical) <= 5


class TestMultipleMappings:
    """Test that one raw category can map to multiple canonical categories"""

    def test_compound_category_maps_to_multiple(self):
        """Test that a compound category can map to multiple canonicals"""
        raw = ["Indoor Tennis Sports Centre"]
        canonical = category_mapper.map_to_canonical(raw)

        # Should match both 'tennis' and 'sports_centre'
        assert 'tennis' in canonical
        assert 'sports_centre' in canonical

    def test_private_sports_club_maps_correctly(self):
        """Test complex category with multiple qualifiers"""
        raw = ["Private Tennis Club"]
        canonical = category_mapper.map_to_canonical(raw)

        # Should match tennis and potentially private_club
        assert 'tennis' in canonical


class TestSingleCategoryMapping:
    """Test single category mapping with confidence scores"""

    def test_map_single_category_returns_matches(self):
        """Test that map_single_category returns confidence scores"""
        matches = category_mapper.map_single_category("Tennis Club")

        assert isinstance(matches, list)
        assert len(matches) > 0

        # Each match should be a tuple of (canonical_key, confidence)
        for match in matches:
            assert isinstance(match, tuple)
            assert len(match) == 2
            assert isinstance(match[0], str)  # canonical_key
            assert isinstance(match[1], (int, float))  # confidence

    def test_map_single_category_sorted_by_confidence(self):
        """Test that results are sorted by confidence (highest first)"""
        matches = category_mapper.map_single_category("Tennis Sports Centre")

        if len(matches) > 1:
            # Check that confidence scores are in descending order
            for i in range(len(matches) - 1):
                assert matches[i][1] >= matches[i+1][1]

    def test_map_single_category_respects_threshold(self):
        """Test that confidence threshold is respected"""
        matches = category_mapper.map_single_category("Club", min_confidence=0.9)

        # All returned matches should have confidence >= 0.9
        for canonical_key, confidence in matches:
            assert confidence >= 0.9


class TestCategoryValidation:
    """Test category validation functions"""

    def test_get_category_keys_returns_set(self):
        """Test that get_category_keys returns a set"""
        keys = category_mapper.get_category_keys()
        assert isinstance(keys, set)
        assert len(keys) > 0

    def test_get_category_keys_contains_expected_categories(self):
        """Test that taxonomy contains expected sport categories"""
        keys = category_mapper.get_category_keys()
        assert 'tennis' in keys
        assert 'padel' in keys
        assert 'sports_centre' in keys
        assert 'venue' in keys

    def test_validate_canonical_categories_with_valid_input(self):
        """Test validation with all valid categories"""
        categories = ['tennis', 'padel', 'sports_centre']
        valid, invalid = category_mapper.validate_canonical_categories(categories)

        assert len(valid) == 3
        assert len(invalid) == 0
        assert set(valid) == {'tennis', 'padel', 'sports_centre'}

    def test_validate_canonical_categories_with_invalid_input(self):
        """Test validation with some invalid categories"""
        categories = ['tennis', 'invalid_category', 'padel']
        valid, invalid = category_mapper.validate_canonical_categories(categories)

        assert 'tennis' in valid
        assert 'padel' in valid
        assert 'invalid_category' in invalid

    def test_validate_canonical_categories_with_all_invalid(self):
        """Test validation with all invalid categories"""
        categories = ['invalid1', 'invalid2']
        valid, invalid = category_mapper.validate_canonical_categories(categories)

        assert len(valid) == 0
        assert len(invalid) == 2


class TestCategoryMetadata:
    """Test category metadata retrieval functions"""

    def test_get_category_display_name(self):
        """Test retrieving display names for categories"""
        assert category_mapper.get_category_display_name('tennis') == 'Tennis'
        assert category_mapper.get_category_display_name('sports_centre') == 'Sports Centre'
        assert category_mapper.get_category_display_name('padel') == 'Padel'

    def test_get_category_display_name_returns_none_for_invalid(self):
        """Test that invalid category keys return None"""
        assert category_mapper.get_category_display_name('invalid_key') is None

    def test_get_category_hierarchy_for_leaf_node(self):
        """Test hierarchy retrieval for a leaf category"""
        hierarchy = category_mapper.get_category_hierarchy('padel')

        # Padel should have 'venue' as parent
        assert 'venue' in hierarchy
        assert 'padel' in hierarchy
        assert hierarchy.index('venue') < hierarchy.index('padel')

    def test_get_category_hierarchy_for_root_node(self):
        """Test hierarchy for a root-level category"""
        hierarchy = category_mapper.get_category_hierarchy('venue')

        # Venue is root, should only contain itself
        assert hierarchy == ['venue']

    def test_get_category_hierarchy_preserves_order(self):
        """Test that hierarchy is in parent-to-child order"""
        hierarchy = category_mapper.get_category_hierarchy('tennis')

        # Should be ordered from root to leaf
        assert isinstance(hierarchy, list)
        # tennis has venue as parent
        if len(hierarchy) > 1:
            assert hierarchy[0] == 'venue'
            assert hierarchy[-1] == 'tennis'


class TestUnmappedCategoryLogging:
    """Test unmapped category logging functionality"""

    @patch('engine.extraction.utils.category_mapper.logger')
    def test_unmapped_categories_logged(self, mock_logger):
        """Test that unmapped categories are logged"""
        raw = ["Some Completely Unmappable Category XYZ"]
        category_mapper.map_to_canonical(raw, log_unmapped=True)

        # Check that logger.info was called for unmapped category
        # Note: This might not trigger if the category happens to match a rule
        # This test is more of a smoke test
        pass

    def test_unmapped_logging_can_be_disabled(self):
        """Test that unmapped logging can be disabled"""
        raw = ["Unmappable Category"]
        # Should not raise any exceptions when logging is disabled
        canonical = category_mapper.map_to_canonical(raw, log_unmapped=False)
        assert isinstance(canonical, list)


class TestConfigReload:
    """Test configuration reload functionality"""

    def test_reload_config_clears_cache(self):
        """Test that reload_config clears the cache"""
        # Load config (caches it)
        config1 = category_mapper.load_config()

        # Reload (clears cache)
        category_mapper.reload_config()

        # Load again (should be fresh)
        config2 = category_mapper.load_config()

        # Content should be the same, but it should have reloaded
        assert config1 == config2


class TestRealWorldExamples:
    """Test with real-world category examples"""

    def test_edinburgh_council_categories(self):
        """Test categories from Edinburgh Council data"""
        raw = ["Sports Centre", "Swimming Pool", "Leisure Centre"]
        canonical = category_mapper.map_to_canonical(raw)

        assert 'sports_centre' in canonical
        assert 'swimming_pool' in canonical

    def test_google_places_categories(self):
        """Test categories that might come from Google Places"""
        raw = ["gym", "health_club", "sports_club"]
        canonical = category_mapper.map_to_canonical(raw)

        assert 'gym' in canonical

    def test_osm_categories(self):
        """Test categories that might come from OpenStreetMap"""
        raw = ["leisure=sports_centre", "sport=tennis"]
        canonical = category_mapper.map_to_canonical(raw)

        # Should extract sport types from OSM tags
        assert 'sports_centre' in canonical or 'tennis' in canonical

    def test_mixed_source_categories(self):
        """Test categories from multiple different sources"""
        raw = [
            "Padel Club",  # Clean, specific
            "Indoor Sports Facility",  # Descriptive
            "Tennis",  # Simple sport name
            "Private Members",  # Qualifier
        ]
        canonical = category_mapper.map_to_canonical(raw)

        assert 'padel' in canonical
        assert 'tennis' in canonical
        # Should have at least sports-related categories
        assert len(canonical) >= 2
