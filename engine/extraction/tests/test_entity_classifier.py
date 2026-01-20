"""
Tests for entity classification logic.

Tests cover:
- Deterministic entity_class resolution
- Multi-valued role assignment
- Priority-based classification algorithm
- Concrete classification examples from classification_rules.md
"""

import pytest

from engine.extraction.entity_classifier import resolve_entity_class


class TestEntityClassification:
    """Test entity_class resolution following deterministic algorithm."""

    def test_club_with_courts_resolves_to_place_with_roles(self):
        """
        Test: Club with courts → place + multiple roles.

        Rationale: Has physical location (courts), so primary classification
        is 'place'. Roles capture dual nature as both facility provider and
        membership organization.
        """
        raw_data = {
            "name": "Craigmillar Tennis Club",
            "address": "123 Tennis Road",
            "latitude": 55.9,
            "longitude": -3.1,
            "has_courts": True,
            "membership_required": True,
            "categories": ["tennis club", "sports facility"],
            "activities": ["tennis"],
            "place_type": "sports_centre",  # Explicit place_type
        }

        result = resolve_entity_class(raw_data)

        assert result["entity_class"] == "place"
        assert "provides_facility" in result["canonical_roles"]
        assert "membership_org" in result["canonical_roles"]
        assert "tennis" in result["canonical_activities"]
        assert "sports_centre" in result["canonical_place_types"]

    def test_freelance_coach_resolves_to_person_with_roles(self):
        """
        Test: Freelance coach → person + roles.

        Rationale: Named individual with no fixed physical location or
        time-bounded existence, so classified as 'person'. Role captures
        instruction-providing function.
        """
        raw_data = {
            "name": "Sarah Wilson",
            "type": "person",  # Use universal type
            "provides_instruction": True,  # Explicit role flag
            "activities": ["tennis"],
        }

        result = resolve_entity_class(raw_data)

        assert result["entity_class"] == "person"
        assert "provides_instruction" in result["canonical_roles"]
        assert "tennis" in result["canonical_activities"]

    def test_retail_chain_resolves_to_organization_with_roles(self):
        """
        Test: Sports retail chain → organization + roles.

        Rationale: Business entity with no courts/facilities and no single
        fixed location (chain), so classified as 'organization'. Role captures
        goods-selling function.
        """
        raw_data = {
            "name": "Sports Direct",
            "type": "retailer",
            "categories": ["sports shop", "retail"],
            "activities": ["tennis", "padel"],  # sells equipment for these sports
        }

        result = resolve_entity_class(raw_data)

        assert result["entity_class"] == "organization"
        assert "sells_goods" in result["canonical_roles"]
        assert "tennis" in result["canonical_activities"]
        assert "padel" in result["canonical_activities"]

    def test_tournament_resolves_to_event_with_no_roles(self):
        """
        Test: Tournament → event + no roles.

        Rationale: Time-bounded entity (has start/end times), so classified
        as 'event' even if it has a physical location. Time-bounded takes
        priority over physical location in classification algorithm. Events
        typically have no roles.
        """
        raw_data = {
            "name": "Edinburgh Padel Open 2024",
            "type": "tournament",
            "start_datetime": "2024-05-15T09:00:00Z",
            "end_datetime": "2024-05-17T18:00:00Z",
            "location": "Oriam",
            "latitude": 55.9,
            "longitude": -3.1,
            "categories": ["tournament", "event"],
            "activities": ["padel"],
        }

        result = resolve_entity_class(raw_data)

        assert result["entity_class"] == "event"
        assert result["canonical_roles"] == []  # events typically have no roles
        assert "padel" in result["canonical_activities"]

    def test_tournament_at_venue_prioritizes_time_bounded(self):
        """
        Test: Tournament at physical venue → event (time-bounded takes priority).

        Rationale: Even though the tournament has both start/end times AND a
        physical location, the time-bounded nature takes priority in the
        classification algorithm.
        """
        raw_data = {
            "name": "Padel tournament at Oriam",
            "type": "event",
            "start_datetime": "2024-06-10T10:00:00Z",
            "end_datetime": "2024-06-10T18:00:00Z",
            "location": "Oriam Sports Centre",
            "address": "Heriot-Watt University, Edinburgh",
            "latitude": 55.9,
            "longitude": -3.1,
            "categories": ["tournament"],
            "activities": ["padel"],
        }

        result = resolve_entity_class(raw_data)

        assert result["entity_class"] == "event"  # time-bounded takes priority
        assert result["canonical_roles"] == []
        assert "padel" in result["canonical_activities"]

    def test_multi_sport_venue_resolves_to_place(self):
        """
        Test: Multi-sport venue → place with multiple activities.

        Rationale: Powerleague Portobello has physical location with multiple
        sports facilities, so classified as 'place'. Multiple activities stored
        in canonical_activities array.
        """
        raw_data = {
            "name": "Powerleague Portobello",
            "address": "Portobello, Edinburgh",
            "latitude": 55.95,
            "longitude": -3.11,
            "categories": ["sports centre", "multi-sport venue"],
            "activities": ["football", "padel"],
            "has_courts": True,
            "has_pitches": True,
            "place_type": ["sports_centre", "outdoor_facility"],  # Explicit place_types
        }

        result = resolve_entity_class(raw_data)

        assert result["entity_class"] == "place"
        assert "provides_facility" in result["canonical_roles"]
        assert "football" in result["canonical_activities"]
        assert "padel" in result["canonical_activities"]
        assert "sports_centre" in result["canonical_place_types"] or \
               "outdoor_facility" in result["canonical_place_types"]

    def test_invalid_entity_class_raises_assertion_error(self):
        """
        Test: Invalid entity_class value raises AssertionError.

        Rationale: entity_class must be one of: place, person, organization,
        event, thing. Any other value should raise an error.
        """
        with pytest.raises(AssertionError, match="entity_class must be one of"):
            # Simulate internal function that tries to set invalid entity_class
            from engine.extraction.entity_classifier import validate_entity_class
            validate_entity_class("club")  # "club" is WRONG - use "place" + roles

    def test_organization_without_location(self):
        """
        Test: Membership organization without fixed location → organization.

        Rationale: Entity with membership/group nature but no fixed physical
        location defaults to 'organization'.
        """
        raw_data = {
            "name": "Scottish Tennis League",
            "type": "league",
            "categories": ["league", "organization"],
            "activities": ["tennis"],
        }

        result = resolve_entity_class(raw_data)

        assert result["entity_class"] == "organization"
        assert "tennis" in result["canonical_activities"]


class TestClassificationPriority:
    """Test priority-based classification algorithm."""

    def test_priority_order_time_bounded_highest(self):
        """
        Test: Time-bounded (event) has highest priority.

        If entity has start/end times, classify as 'event' regardless of
        other attributes like physical location.
        """
        # Has time bounds + location + membership
        raw_data = {
            "name": "Annual Tennis Tournament",
            "start_datetime": "2024-07-01T09:00:00Z",
            "end_datetime": "2024-07-03T18:00:00Z",
            "location": "Tennis Club",
            "address": "123 Court Street",
            "membership_required": True,
            "activities": ["tennis"],
        }

        result = resolve_entity_class(raw_data)

        # Time-bounded takes priority over location
        assert result["entity_class"] == "event"

    def test_priority_order_location_over_organization(self):
        """
        Test: Physical location has priority over organization classification.

        If entity has physical location (lat/lng or street address) but no
        time bounds, classify as 'place' even if it's also a membership org.
        """
        raw_data = {
            "name": "Tennis Club with Courts",
            "address": "456 Sport Road",
            "latitude": 55.9,
            "longitude": -3.1,
            "membership_required": True,
            "categories": ["club"],
            "activities": ["tennis"],
        }

        result = resolve_entity_class(raw_data)

        # Physical location takes priority over membership org nature
        assert result["entity_class"] == "place"
        # But membership captured in roles
        assert "membership_org" in result["canonical_roles"]

    def test_person_for_named_individual(self):
        """
        Test: Named individual → person.

        If entity represents a named individual with no time bounds or
        primary physical location, classify as 'person'.
        """
        raw_data = {
            "name": "John Smith",
            "type": "person",  # Use universal type
            "activities": ["padel"],
        }

        result = resolve_entity_class(raw_data)

        assert result["entity_class"] == "person"


class TestAntiPatterns:
    """Test that anti-patterns are prevented."""

    def test_never_use_entity_class_for_business_type(self):
        """
        Test: ANTI-PATTERN - Never use entity_class to encode business type.

        "club" is NOT a valid entity_class. Use "place" + "membership_org" role.
        """
        # This should be handled gracefully - no "club" entity_class should exist
        raw_data = {
            "name": "Some Tennis Club",
            "address": "123 Court Road",
            "type": "club",
            "categories": ["tennis club"],
        }

        result = resolve_entity_class(raw_data)

        # Should resolve to place, not "club"
        assert result["entity_class"] != "club"
        assert result["entity_class"] == "place"

    def test_roles_not_primary_classification(self):
        """
        Test: ANTI-PATTERN - Never use roles as primary classification.

        entity_class is the primary classification. Roles are supplementary
        functions/capabilities.
        """
        raw_data = {
            "name": "Coaching Venue",
            "address": "789 Coach Street",
            "provides_instruction": True,  # Use universal flag
            "has_courts": True,
        }

        result = resolve_entity_class(raw_data)

        # Primary classification is place (has address/courts)
        assert result["entity_class"] == "place"
        # Coaching is captured in roles, not entity_class
        assert "provides_instruction" in result["canonical_roles"]
