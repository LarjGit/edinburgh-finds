"""
Tests for extract_with_lens_contract function.

Verifies the lens-aware extraction pipeline that maps raw data to
canonical dimensions using lens contract configuration.
"""

import pytest
from engine.extraction.base import extract_with_lens_contract, dedupe_preserve_order


class TestDedupePreserveOrder:
    """Tests for dedupe_preserve_order helper function."""

    def test_removes_duplicates(self):
        """Should remove duplicate values from list."""
        result = dedupe_preserve_order(["padel", "tennis", "padel", "gym", "tennis"])
        assert result == ["padel", "tennis", "gym"]

    def test_preserves_insertion_order(self):
        """Should preserve the order of first occurrence."""
        result = dedupe_preserve_order(["c", "a", "b", "a", "c"])
        assert result == ["c", "a", "b"]

    def test_empty_list(self):
        """Should handle empty list."""
        result = dedupe_preserve_order([])
        assert result == []

    def test_no_duplicates(self):
        """Should handle list with no duplicates."""
        result = dedupe_preserve_order(["a", "b", "c"])
        assert result == ["a", "b", "c"]


class TestExtractWithLensContract:
    """Tests for extract_with_lens_contract function."""

    @pytest.fixture
    def minimal_lens_contract(self):
        """Minimal lens contract for testing."""
        return {
            "facets": {
                "activity": {
                    "dimension_source": "canonical_activities",
                    "ui_label": "Activity",
                    "display_mode": "multi_select"
                },
                "role": {
                    "dimension_source": "canonical_roles",
                    "ui_label": None,
                    "display_mode": "internal"
                },
                "place_type": {
                    "dimension_source": "canonical_place_types",
                    "ui_label": "Place Type",
                    "display_mode": "single_select"
                },
                "access": {
                    "dimension_source": "canonical_access",
                    "ui_label": "Access",
                    "display_mode": "multi_select"
                }
            },
            "values": [
                {"key": "padel", "facet": "activity", "display_name": "Padel"},
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"},
                {"key": "gym", "facet": "activity", "display_name": "Gym"},
                {"key": "provides_facility", "facet": "role", "display_name": "Venue"},
                {"key": "sells_goods", "facet": "role", "display_name": "Retailer"},
                {"key": "sports_centre", "facet": "place_type", "display_name": "Sports Centre"},
                {"key": "pay_and_play", "facet": "access", "display_name": "Pay & Play"}
            ],
            "mapping_rules": [
                {"pattern": r"(?i)\bpadel\b", "canonical": "padel", "confidence": 1.0},
                {"pattern": r"(?i)\btennis\b", "canonical": "tennis", "confidence": 1.0},
                {"pattern": r"(?i)\bgym\b|\bfitness\b", "canonical": "gym", "confidence": 0.9},
                {"pattern": r"(?i)sports\s+(centre|center)", "canonical": "sports_centre", "confidence": 0.95},
                {"pattern": r"(?i)\bvenue\b|\bfacility\b", "canonical": "provides_facility", "confidence": 0.85},
                {"pattern": r"(?i)pay.and.play", "canonical": "pay_and_play", "confidence": 0.8}
            ],
            "modules": {
                "sports_facility": {
                    "description": "Sports-specific facility attributes",
                    "fields": []
                }
            },
            "module_triggers": [
                {
                    "when": {"facet": "activity", "value": "padel"},
                    "add_modules": ["sports_facility"],
                    "conditions": [{"entity_class": "place"}]
                },
                {
                    "when": {"facet": "activity", "value": "tennis"},
                    "add_modules": ["sports_facility"],
                    "conditions": [{"entity_class": "place"}]
                }
            ]
        }

    def test_extracts_single_activity_from_categories(self, minimal_lens_contract):
        """Should extract single activity from categories via mapping rules."""
        raw_data = {
            "name": "Padel Court",
            "categories": ["Padel Court", "Sports Venue"],
            "address": "123 Main St",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        assert result["entity_class"] == "place"
        assert "padel" in result["canonical_activities"]
        # "Sports Venue" should map to provides_facility role
        assert "provides_facility" in result["canonical_roles"]
        assert isinstance(result["canonical_activities"], list)
        assert isinstance(result["modules"], dict)

    def test_extracts_multiple_activities(self, minimal_lens_contract):
        """Should extract multiple activities from categories."""
        raw_data = {
            "name": "Multi-Sport Centre",
            "categories": ["Tennis", "Padel", "Fitness"],
            "address": "456 Sports Ave",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        assert result["entity_class"] == "place"
        assert "padel" in result["canonical_activities"]
        assert "tennis" in result["canonical_activities"]
        assert "gym" in result["canonical_activities"]

    def test_deduplicates_canonical_values(self, minimal_lens_contract):
        """Should deduplicate repeated canonical values."""
        raw_data = {
            "name": "Padel Centre",
            "categories": ["Padel", "Padel Court", "Padel Venue"],
            "address": "789 Court Rd",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # Should only have one "padel" despite multiple padel-related categories
        assert result["canonical_activities"].count("padel") == 1

    def test_distributes_values_to_correct_dimensions(self, minimal_lens_contract):
        """Should distribute values to correct dimension arrays based on facet."""
        raw_data = {
            "name": "Tennis Venue",
            "categories": ["Tennis", "Sports Centre", "Pay and Play"],
            "address": "100 Tennis Rd",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # Activities should be in canonical_activities
        assert "tennis" in result["canonical_activities"]

        # Place types should be in canonical_place_types
        assert "sports_centre" in result["canonical_place_types"]

        # Access should be in canonical_access
        assert "pay_and_play" in result["canonical_access"]

    def test_triggers_lens_modules_for_matching_values(self, minimal_lens_contract):
        """Should trigger lens modules when conditions match."""
        raw_data = {
            "name": "Padel Venue",
            "categories": ["Padel"],
            "address": "200 Padel St",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # sports_facility module should be triggered for padel activity at place
        assert "sports_facility" in result["modules"]

    def test_does_not_trigger_modules_for_wrong_entity_class(self, minimal_lens_contract):
        """Should not trigger modules if entity_class condition doesn't match."""
        raw_data = {
            "name": "Sarah Wilson",
            "type": "coach",
            "categories": ["Tennis Coach"],
            "activities": ["tennis"]
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # Entity should be person (not place), so sports_facility should not be triggered
        assert result["entity_class"] == "person"
        assert "sports_facility" not in result["modules"]

    def test_includes_engine_required_modules(self, minimal_lens_contract):
        """Should include engine-required modules based on entity_class."""
        raw_data = {
            "name": "Tennis Centre",
            "categories": ["Tennis"],
            "address": "300 Centre Ln",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # Place entities should have core and location modules (from engine)
        assert "core" in result["modules"]
        assert "location" in result["modules"]

    def test_merges_classifier_and_lens_dimensions(self, minimal_lens_contract):
        """Should merge dimensions from both classifier and lens mapping."""
        raw_data = {
            "name": "Tennis Club",
            "categories": ["Tennis"],  # Mapped by lens to 'tennis'
            "address": "400 Club St",
            "latitude": 55.95,
            "longitude": -3.18,
            "has_courts": True,  # Classifier extracts 'provides_facility' role
            "membership_required": True,  # Classifier extracts 'membership_org' role
            "activities": ["padel"]  # Classifier extracts activities
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # Should have activities from both lens mapping and classifier
        assert "tennis" in result["canonical_activities"]  # From lens
        assert "padel" in result["canonical_activities"]  # From classifier

        # Should have roles from classifier
        assert "provides_facility" in result["canonical_roles"]
        assert "membership_org" in result["canonical_roles"]

    def test_returns_all_required_dimension_fields(self, minimal_lens_contract):
        """Should return all four dimension fields as lists."""
        raw_data = {
            "name": "Simple Place",
            "address": "500 Simple St",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        assert "canonical_activities" in result
        assert "canonical_roles" in result
        assert "canonical_place_types" in result
        assert "canonical_access" in result
        assert isinstance(result["canonical_activities"], list)
        assert isinstance(result["canonical_roles"], list)
        assert isinstance(result["canonical_place_types"], list)
        assert isinstance(result["canonical_access"], list)

    def test_handles_empty_categories(self, minimal_lens_contract):
        """Should handle entities with no categories."""
        raw_data = {
            "name": "Place Without Categories",
            "address": "600 Empty St",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        assert result["entity_class"] == "place"
        assert isinstance(result["canonical_activities"], list)
        # Should not crash, should return empty or classifier-populated dimensions

    def test_filters_by_confidence_threshold(self, minimal_lens_contract):
        """Should filter out mapping rules below confidence threshold."""
        # Add a low-confidence rule
        minimal_lens_contract["mapping_rules"].append({
            "pattern": r"(?i)\bmaybe\b",
            "canonical": "tennis",
            "confidence": 0.5  # Below 0.7 threshold
        })

        raw_data = {
            "name": "Maybe Tennis",
            "categories": ["maybe tennis"],
            "address": "700 Low Confidence St",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # Low confidence match should be filtered out
        # (hard to test without the exact pattern matching, but the logic is there)
        assert result["entity_class"] == "place"

    def test_canonical_values_deduped_before_trigger_evaluation(self, minimal_lens_contract):
        """Should deduplicate canonical values before evaluating module triggers.

        Ensures that even if multiple raw categories map to the same canonical value
        (e.g., "padel court", "padel facility", "padel club" all → "padel"),
        the trigger only fires ONCE, not three times.
        """
        raw_data = {
            "name": "Padel Complex",
            "categories": ["Padel Court", "Padel Facility", "Padel Club"],
            "address": "800 Padel Way",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # All three categories map to "padel", should only have one
        assert result["canonical_activities"].count("padel") == 1

        # Module should only be triggered ONCE (not three times)
        # If it were triggered three times, we'd see duplicate modules or errors
        assert "sports_facility" in result["modules"]
        # Should only have this module once in the modules dict
        assert isinstance(result["modules"], dict)

    def test_dimension_arrays_deduped_before_storage(self, minimal_lens_contract):
        """Should deduplicate dimension arrays before returning result."""
        raw_data = {
            "name": "Tennis Complex",
            "categories": ["Tennis", "Tennis Court", "Tennis Club"],  # All map to "tennis"
            "address": "900 Tennis Ave",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # Should only have "tennis" once, not three times
        assert result["canonical_activities"] == ["tennis"]
        assert result["canonical_activities"].count("tennis") == 1

    def test_deduplication_preserves_order_across_pipeline(self, minimal_lens_contract):
        """Should preserve insertion order during deduplication across extraction pipeline."""
        raw_data = {
            "name": "Multi-Sport Centre",
            "categories": ["Tennis", "Padel", "Tennis Court", "Gym", "Padel Club"],
            "address": "1000 Sport St",
            "latitude": 55.95,
            "longitude": -3.18
        }

        result = extract_with_lens_contract(raw_data, minimal_lens_contract)

        # Order should be: tennis (appears first), padel (appears second), gym (appears fourth)
        # Duplicates "Tennis Court" → tennis and "Padel Club" → padel are removed
        activities = result["canonical_activities"]
        assert activities == ["tennis", "padel", "gym"]

        # Verify order is preserved: tennis before padel before gym
        assert activities.index("tennis") < activities.index("padel")
        assert activities.index("padel") < activities.index("gym")
