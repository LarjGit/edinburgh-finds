"""Tests for query lens loader (query_lens.py)."""

import pytest
from pathlib import Path
from engine.lenses.query_lens import (
    load_query_lens,
    get_active_lens,
    QueryLens,
    QueryLensConfig,
)


def test_load_padel_lens():
    """Test loading Padel lens from YAML files."""
    lens = load_query_lens("padel")

    assert lens.lens_name == "padel"
    assert isinstance(lens, QueryLens)


def test_get_activity_keywords():
    """Test retrieving activity keywords from Padel lens."""
    lens = get_active_lens("padel")

    keywords = lens.get_activity_keywords()

    assert isinstance(keywords, list)
    assert len(keywords) > 0
    assert "padel" in keywords
    assert "tennis" in keywords
    assert "sport" in keywords


def test_get_location_indicators():
    """Test retrieving location indicators from Padel lens."""
    lens = get_active_lens("padel")

    indicators = lens.get_location_indicators()

    assert isinstance(indicators, list)
    assert len(indicators) > 0
    assert "edinburgh" in indicators
    assert "near" in indicators
    assert "in" in indicators


def test_get_facility_keywords():
    """Test retrieving facility keywords from Padel lens."""
    lens = get_active_lens("padel")

    keywords = lens.get_facility_keywords()

    assert isinstance(keywords, list)
    assert len(keywords) > 0
    assert "centre" in keywords or "center" in keywords
    assert "facility" in keywords


def test_get_connectors_for_sports_query():
    """Test connector selection for sports-related query."""
    lens = get_active_lens("padel")

    # Query with sports keywords
    query = "padel courts edinburgh"
    connectors = lens.get_connectors_for_query(query)

    assert isinstance(connectors, list)
    assert "sport_scotland" in connectors  # Should trigger on sports keywords
    assert "edinburgh_council" in connectors  # Should trigger on Edinburgh location


def test_get_connectors_for_generic_query():
    """Test connector selection for non-sports query."""
    lens = get_active_lens("padel")

    # Query without sports keywords
    query = "coffee shops near me"
    connectors = lens.get_connectors_for_query(query)

    # Should not trigger domain-specific connectors
    assert "sport_scotland" not in connectors
    assert "edinburgh_council" not in connectors


def test_get_connectors_for_location_query():
    """Test connector selection for Edinburgh-specific query."""
    lens = get_active_lens("padel")

    # Query with Edinburgh location but no sports keywords
    query = "leisure centre in leith"
    connectors = lens.get_connectors_for_query(query)

    # Edinburgh Council should trigger on Edinburgh locations
    assert "edinburgh_council" in connectors


def test_lens_caching():
    """Test that lens instances are cached."""
    lens1 = get_active_lens("padel")
    lens2 = get_active_lens("padel")

    # Should return same instance (cached)
    assert lens1 is lens2


def test_invalid_lens_raises_error():
    """Test that loading non-existent lens raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_query_lens("nonexistent_lens")


def test_connector_trigger_any_keyword_match():
    """Test 'any_keyword_match' trigger type."""
    lens = get_active_lens("padel")

    # Query with multiple sports keywords
    query = "tennis and swimming facilities"
    connectors = lens.get_connectors_for_query(query)

    # Should match sport_scotland (threshold: 1 keyword)
    assert "sport_scotland" in connectors


def test_connector_trigger_location_match():
    """Test 'location_match' trigger type."""
    lens = get_active_lens("padel")

    # Query with Edinburgh location
    query = "facilities in portobello"
    connectors = lens.get_connectors_for_query(query)

    # Should match edinburgh_council (location: portobello)
    assert "edinburgh_council" in connectors


def test_default_lens_is_padel():
    """Test that default lens when none specified is Padel."""
    lens = get_active_lens()  # No lens_name specified

    assert lens.lens_name == "padel"
