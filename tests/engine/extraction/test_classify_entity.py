"""Test entity classification (TDD)."""

import pytest
from engine.extraction.entity_classifier import classify_entity


def test_classify_entity_as_place():
    """Test that entities with location are classified as place."""
    attributes = {
        "name": "Test Venue",
        "location_lat": 55.9533,
        "location_lng": -3.1883,
        "address_full": "123 Test St"
    }

    entity_class = classify_entity(attributes)

    assert entity_class == "place"


def test_classify_entity_as_event():
    """Test that time-bounded entities are classified as event."""
    attributes = {
        "name": "Padel Tournament",
        "start_date": "2026-02-01",
        "end_date": "2026-02-02"
    }

    entity_class = classify_entity(attributes)

    assert entity_class == "event"


def test_classify_entity_as_person():
    """Test that entities with person indicators are classified as person."""
    attributes = {
        "name": "John Smith",
        "entity_type": "person",
        "contact_email": "john@example.com"
    }

    entity_class = classify_entity(attributes)

    assert entity_class == "person"


def test_classify_entity_as_organization():
    """Test that non-place organizations are classified as organization."""
    attributes = {
        "name": "Tennis Scotland",
        "entity_type": "organization",
        "contact_website": "https://tennisscotland.org"
        # No location coordinates
    }

    entity_class = classify_entity(attributes)

    assert entity_class == "organization"


def test_classify_entity_defaults_to_thing():
    """Test that unclassifiable entities default to thing."""
    attributes = {
        "name": "Some Item"
    }

    entity_class = classify_entity(attributes)

    assert entity_class == "thing"
