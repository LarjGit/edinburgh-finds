"""Test QueryLens loader (TDD - tests first)."""

import pytest
from pathlib import Path
from engine.lenses.query_lens import load_query_lens, QueryLens, QueryLensConfig


def test_load_query_lens_raises_error_for_missing_lens():
    """Test that loading non-existent lens raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_query_lens("nonexistent_lens")


def test_query_lens_loads_activity_keywords():
    """Test that QueryLens loads activity keywords from YAML."""
    # This will fail until we create Padel lens config
    lens = load_query_lens("padel")

    keywords = lens.get_activity_keywords()

    assert isinstance(keywords, list)
    assert len(keywords) > 0
    assert "padel" in keywords


def test_query_lens_loads_location_indicators():
    """Test that QueryLens loads location indicators from YAML."""
    lens = load_query_lens("padel")

    indicators = lens.get_location_indicators()

    assert isinstance(indicators, list)
    assert "edinburgh" in indicators
    assert "near" in indicators


def test_query_lens_loads_facility_keywords():
    """Test that QueryLens loads facility keywords from YAML."""
    lens = load_query_lens("padel")

    keywords = lens.get_facility_keywords()

    assert isinstance(keywords, list)
    assert "centre" in keywords or "center" in keywords


def test_get_connectors_for_sports_query():
    """Test connector selection for sports query."""
    lens = load_query_lens("padel")

    # Mock query features (we'll define this interface)
    class MockFeatures:
        looks_like_category_search = True
        has_location_indicator = True

    connectors = lens.get_connectors_for_query("padel courts edinburgh", MockFeatures())

    assert isinstance(connectors, list)
    assert "sport_scotland" in connectors


def test_lens_caching():
    """Test that lens instances are cached."""
    from engine.lenses.query_lens import get_active_lens

    lens1 = get_active_lens("padel")
    lens2 = get_active_lens("padel")

    # Should return same cached instance
    assert lens1 is lens2


def test_wine_lens_loads_successfully():
    """Test that Wine lens loads (validates extensibility)."""
    lens = load_query_lens("wine")

    keywords = lens.get_activity_keywords()

    assert "wine" in keywords
    assert "winery" in keywords
    assert lens.lens_name == "wine"


def test_wine_lens_routes_correctly():
    """Test Wine lens connector routing."""
    lens = load_query_lens("wine")

    class MockFeatures:
        looks_like_category_search = True
        has_location_indicator = True

    connectors = lens.get_connectors_for_query("wineries in scotland", MockFeatures())

    # Wine lens should route to wine_searcher (hypothetical connector)
    assert "wine_searcher" in connectors or "edinburgh_council" in connectors
