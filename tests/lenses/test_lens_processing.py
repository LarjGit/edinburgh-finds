"""
Tests for lens processing classes and methods.

Tests the helper classes and processing logic:
- FacetDefinition
- CanonicalValue
- DerivedGrouping (AND-within-rule, OR-across-rules)
- ModuleTrigger (explicit list format with facet/value)
- ModuleDefinition
- VerticalLens processing methods
- LensRegistry
- dedupe_preserve_order helper
"""

import pytest
from pathlib import Path
import yaml

from engine.lenses.loader import (
    FacetDefinition,
    CanonicalValue,
    DerivedGrouping,
    ModuleTrigger,
    ModuleDefinition,
    VerticalLens,
    LensRegistry,
    dedupe_preserve_order
)


class TestFacetDefinition:
    """Test FacetDefinition class."""

    def test_init_stores_all_fields(self):
        """FacetDefinition should store all facet configuration fields."""
        facet_data = {
            "dimension_source": "canonical_activities",
            "ui_label": "What do you want to do?",
            "display_mode": "multi_select",
            "order": 10,
            "show_in_filters": True,
            "show_in_navigation": True,
            "icon": "activity"
        }

        facet = FacetDefinition(key="activity", data=facet_data)

        assert facet.key == "activity"
        assert facet.dimension_source == "canonical_activities"
        assert facet.ui_label == "What do you want to do?"
        assert facet.display_mode == "multi_select"
        assert facet.order == 10
        assert facet.show_in_filters is True
        assert facet.show_in_navigation is True
        assert facet.icon == "activity"

    def test_internal_facet_with_null_ui_label(self):
        """Internal facets should support null ui_label."""
        facet_data = {
            "dimension_source": "canonical_roles",
            "ui_label": None,
            "display_mode": "internal",
            "order": 5,
            "show_in_filters": False,
            "show_in_navigation": False
        }

        facet = FacetDefinition(key="role", data=facet_data)

        assert facet.ui_label is None
        assert facet.display_mode == "internal"


class TestCanonicalValue:
    """Test CanonicalValue class."""

    def test_init_stores_all_fields(self):
        """CanonicalValue should store all value configuration fields."""
        value_data = {
            "key": "padel",
            "facet": "activity",
            "display_name": "Padel",
            "description": "Padel tennis - a racquet sport combining tennis and squash",
            "seo_slug": "padel-edinburgh",
            "search_keywords": ["padel", "padel tennis", "pádel"],
            "icon_url": "/icons/padel.svg",
            "color": "#FF6B35"
        }

        value = CanonicalValue(data=value_data)

        assert value.key == "padel"
        assert value.facet == "activity"
        assert value.display_name == "Padel"
        assert value.description == "Padel tennis - a racquet sport combining tennis and squash"
        assert value.seo_slug == "padel-edinburgh"
        assert value.search_keywords == ["padel", "padel tennis", "pádel"]
        assert value.icon_url == "/icons/padel.svg"
        assert value.color == "#FF6B35"


class TestDerivedGrouping:
    """Test DerivedGrouping class with AND-within-rule, OR-across-rules semantics."""

    def test_init_stores_fields(self):
        """DerivedGrouping should store id, label, description, rules."""
        grouping_data = {
            "id": "venues",
            "label": "Venues",
            "description": "All sports venues",
            "rules": [
                {
                    "entity_class": "place",
                    "roles": ["provides_facility"]
                }
            ]
        }

        grouping = DerivedGrouping(data=grouping_data)

        assert grouping.id == "venues"
        assert grouping.label == "Venues"
        assert grouping.description == "All sports venues"
        assert len(grouping.rules) == 1

    def test_matches_and_within_rule(self):
        """All conditions within a rule must match (AND logic)."""
        grouping_data = {
            "id": "venues",
            "label": "Venues",
            "description": "Sports venues",
            "rules": [
                {
                    "entity_class": "place",
                    "roles": ["provides_facility"]
                }
            ]
        }

        grouping = DerivedGrouping(data=grouping_data)

        # Entity matches: correct entity_class AND has required role
        entity_match = {
            "entity_class": "place",
            "canonical_roles": ["provides_facility", "sells_goods"]
        }
        assert grouping.matches(entity_match) is True

        # Entity doesn't match: correct entity_class but missing role
        entity_no_match = {
            "entity_class": "place",
            "canonical_roles": ["sells_goods"]
        }
        assert grouping.matches(entity_no_match) is False

        # Entity doesn't match: has role but wrong entity_class
        entity_no_match2 = {
            "entity_class": "organization",
            "canonical_roles": ["provides_facility"]
        }
        assert grouping.matches(entity_no_match2) is False

    def test_matches_or_across_rules(self):
        """Any rule can match (OR logic across rules)."""
        grouping_data = {
            "id": "sports_providers",
            "label": "Sports Providers",
            "description": "Venues or coaches",
            "rules": [
                {
                    "entity_class": "place",
                    "roles": ["provides_facility"]
                },
                {
                    "entity_class": "person",
                    "roles": ["provides_instruction"]
                }
            ]
        }

        grouping = DerivedGrouping(data=grouping_data)

        # Matches first rule
        entity1 = {
            "entity_class": "place",
            "canonical_roles": ["provides_facility"]
        }
        assert grouping.matches(entity1) is True

        # Matches second rule
        entity2 = {
            "entity_class": "person",
            "canonical_roles": ["provides_instruction"]
        }
        assert grouping.matches(entity2) is True

        # Matches neither rule
        entity3 = {
            "entity_class": "organization",
            "canonical_roles": ["sells_goods"]
        }
        assert grouping.matches(entity3) is False


class TestModuleTrigger:
    """Test ModuleTrigger class with explicit list format."""

    def test_init_stores_fields(self):
        """ModuleTrigger should store facet, value, add_modules, conditions."""
        trigger_data = {
            "when": {
                "facet": "activity",
                "value": "padel"
            },
            "add_modules": ["sports_facility"],
            "conditions": {
                "entity_class": "place"
            }
        }

        trigger = ModuleTrigger(data=trigger_data)

        assert trigger.facet == "activity"
        assert trigger.value == "padel"
        assert trigger.add_modules == ["sports_facility"]
        assert trigger.conditions == {"entity_class": "place"}

    def test_matches_when_value_present(self):
        """Trigger should fire when entity has the specified value in the facet."""
        trigger_data = {
            "when": {
                "facet": "activity",
                "value": "padel"
            },
            "add_modules": ["sports_facility"]
        }

        trigger = ModuleTrigger(data=trigger_data)

        # Entity has the value in the facet
        canonical_values_by_facet = {
            "activity": ["padel", "tennis"],
            "role": ["provides_facility"]
        }
        assert trigger.matches("place", canonical_values_by_facet) is True

        # Entity doesn't have the value
        canonical_values_by_facet_no_match = {
            "activity": ["tennis"],
            "role": ["provides_facility"]
        }
        assert trigger.matches("place", canonical_values_by_facet_no_match) is False

    def test_matches_with_entity_class_condition(self):
        """Trigger should respect entity_class conditions."""
        trigger_data = {
            "when": {
                "facet": "activity",
                "value": "padel"
            },
            "add_modules": ["sports_facility"],
            "conditions": {
                "entity_class": "place"
            }
        }

        trigger = ModuleTrigger(data=trigger_data)

        canonical_values_by_facet = {
            "activity": ["padel"]
        }

        # Matches: has value AND correct entity_class
        assert trigger.matches("place", canonical_values_by_facet) is True

        # Doesn't match: has value but wrong entity_class
        assert trigger.matches("person", canonical_values_by_facet) is False


class TestModuleDefinition:
    """Test ModuleDefinition class."""

    def test_init_stores_fields(self):
        """ModuleDefinition should store name, description, fields."""
        module_data = {
            "description": "Sports facility information",
            "fields": {
                "inventory": {
                    "type": "json",
                    "description": "List of facilities/courts"
                },
                "court_count": {
                    "type": "integer",
                    "description": "Total number of courts"
                }
            }
        }

        module = ModuleDefinition(name="sports_facility", data=module_data)

        assert module.name == "sports_facility"
        assert module.description == "Sports facility information"
        assert "inventory" in module.fields
        assert "court_count" in module.fields


class TestDedupePreserveOrder:
    """Test dedupe_preserve_order helper function."""

    def test_removes_duplicates(self):
        """Should remove duplicate values."""
        values = ["a", "b", "c", "b", "a", "d"]
        result = dedupe_preserve_order(values)
        assert result == ["a", "b", "c", "d"]

    def test_preserves_insertion_order(self):
        """Should preserve first occurrence order."""
        values = ["z", "a", "m", "a", "b", "z"]
        result = dedupe_preserve_order(values)
        assert result == ["z", "a", "m", "b"]

    def test_empty_list(self):
        """Should handle empty list."""
        assert dedupe_preserve_order([]) == []

    def test_no_duplicates(self):
        """Should handle list with no duplicates."""
        values = ["a", "b", "c"]
        result = dedupe_preserve_order(values)
        assert result == ["a", "b", "c"]


class TestVerticalLensProcessingMethods:
    """Test VerticalLens processing methods."""

    @pytest.fixture
    def lens_config(self, tmp_path):
        """Create a test lens configuration."""
        config_path = tmp_path / "lens.yaml"

        config = {
            "facets": {
                "activity": {
                    "dimension_source": "canonical_activities",
                    "ui_label": "Activity",
                    "display_mode": "multi_select",
                    "order": 10,
                    "show_in_filters": True,
                    "show_in_navigation": True
                },
                "role": {
                    "dimension_source": "canonical_roles",
                    "ui_label": None,
                    "display_mode": "internal",
                    "order": 5,
                    "show_in_filters": False,
                    "show_in_navigation": False
                }
            },
            "values": [
                {
                    "key": "padel",
                    "facet": "activity",
                    "display_name": "Padel"
                },
                {
                    "key": "tennis",
                    "facet": "activity",
                    "display_name": "Tennis"
                },
                {
                    "key": "provides_facility",
                    "facet": "role",
                    "display_name": "Venue"
                }
            ],
            "mapping_rules": [
                {
                    "pattern": r"(?i)\bp[aá]d[eé]l\b",
                    "canonical": "padel",
                    "confidence": 1.0
                },
                {
                    "pattern": r"(?i)\btennis\b",
                    "canonical": "tennis",
                    "confidence": 1.0
                },
                {
                    "pattern": r"(?i)\bpaddle\b",
                    "canonical": "padel",
                    "confidence": 0.8
                },
                {
                    "pattern": r"(?i)\bcourt\b",
                    "canonical": "tennis",
                    "confidence": 0.6
                }
            ],
            "derived_groupings": [
                {
                    "id": "venues",
                    "label": "Venues",
                    "description": "Sports venues",
                    "rules": [
                        {
                            "entity_class": "place",
                            "roles": ["provides_facility"]
                        }
                    ]
                }
            ],
            "modules": {
                "sports_facility": {
                    "description": "Sports facility information",
                    "fields": {
                        "inventory": {"type": "json"}
                    }
                }
            },
            "module_triggers": [
                {
                    "when": {
                        "facet": "activity",
                        "value": "padel"
                    },
                    "add_modules": ["sports_facility"],
                    "conditions": {
                        "entity_class": "place"
                    }
                }
            ]
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        return config_path

    def test_map_raw_category(self, lens_config):
        """map_raw_category should apply regex mapping rules and filter by confidence."""
        lens = VerticalLens(lens_config)

        # High confidence match
        result = lens.map_raw_category("Padel courts available")
        assert "padel" in result

        # Multiple matches
        result = lens.map_raw_category("Tennis and Pádel")
        assert "tennis" in result
        assert "padel" in result

        # Low confidence match (below 0.7 threshold)
        result = lens.map_raw_category("Tennis court facilities")
        # "court" pattern matches but confidence 0.6 < 0.7 threshold
        # So only high confidence "tennis" pattern should match
        assert len(result) == 1
        assert "tennis" in result

        # No match
        result = lens.map_raw_category("Swimming pool")
        assert result == []

    def test_get_values_by_facet(self, lens_config):
        """get_values_by_facet should return values for a specific facet."""
        lens = VerticalLens(lens_config)

        activity_values = lens.get_values_by_facet("activity")
        assert len(activity_values) == 2
        assert any(v.key == "padel" for v in activity_values)
        assert any(v.key == "tennis" for v in activity_values)

        role_values = lens.get_values_by_facet("role")
        assert len(role_values) == 1
        assert role_values[0].key == "provides_facility"

    def test_get_facets_sorted(self, lens_config):
        """get_facets_sorted should return facets sorted by order field."""
        lens = VerticalLens(lens_config)

        facets = lens.get_facets_sorted()
        assert len(facets) == 2
        # role (order 5) should come before activity (order 10)
        assert facets[0].key == "role"
        assert facets[1].key == "activity"

    def test_compute_grouping(self, lens_config):
        """compute_grouping should return first matching grouping id."""
        lens = VerticalLens(lens_config)

        # Entity matches venues grouping
        entity_match = {
            "entity_class": "place",
            "canonical_roles": ["provides_facility"]
        }
        assert lens.compute_grouping(entity_match) == "venues"

        # Entity doesn't match any grouping
        entity_no_match = {
            "entity_class": "person",
            "canonical_roles": ["provides_instruction"]
        }
        assert lens.compute_grouping(entity_no_match) is None

    def test_get_required_modules(self, lens_config):
        """get_required_modules should apply module triggers."""
        lens = VerticalLens(lens_config)

        # Trigger fires: place with padel activity
        canonical_values_by_facet = {
            "activity": ["padel"],
            "role": ["provides_facility"]
        }
        modules = lens.get_required_modules("place", canonical_values_by_facet)
        assert "sports_facility" in modules

        # Trigger doesn't fire: place without padel
        canonical_values_by_facet_no_trigger = {
            "activity": ["tennis"],
            "role": ["provides_facility"]
        }
        modules = lens.get_required_modules("place", canonical_values_by_facet_no_trigger)
        assert "sports_facility" not in modules

        # Trigger doesn't fire: wrong entity_class
        modules = lens.get_required_modules("person", canonical_values_by_facet)
        assert "sports_facility" not in modules


class TestLensRegistry:
    """Test LensRegistry class."""

    def test_register_and_get_lens(self, tmp_path):
        """Should be able to register and retrieve lenses."""
        config_path = tmp_path / "lens.yaml"

        config = {
            "facets": {
                "activity": {
                    "dimension_source": "canonical_activities"
                }
            },
            "values": [
                {
                    "key": "padel",
                    "facet": "activity"
                }
            ],
            "mapping_rules": []
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        # Register lens
        LensRegistry.register("test_lens", config_path)

        # Retrieve lens
        lens = LensRegistry.get_lens("test_lens")
        assert lens is not None
        assert isinstance(lens, VerticalLens)

    def test_get_nonexistent_lens_raises_error(self):
        """Getting a non-existent lens should raise KeyError."""
        with pytest.raises(KeyError):
            LensRegistry.get_lens("nonexistent")
