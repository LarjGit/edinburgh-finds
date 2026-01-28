"""Test SlugGenerator (TDD)."""

import pytest
from engine.extraction.deduplication import SlugGenerator


def test_slug_basic_generation():
    """Test basic slug generation."""
    generator = SlugGenerator()

    slug = generator.generate("Edinburgh Padel Club")

    assert slug == "edinburgh-padel-club"


def test_slug_removes_articles():
    """Test that articles (the, a, an) are removed."""
    generator = SlugGenerator()

    slug = generator.generate("The Game4Padel")

    assert slug == "game4padel"


def test_slug_handles_special_characters():
    """Test special character removal."""
    generator = SlugGenerator()

    slug = generator.generate("Café Olé - Edinburgh!")

    assert slug == "cafe-ole-edinburgh"


def test_slug_with_location():
    """Test slug generation with location suffix."""
    generator = SlugGenerator()

    slug = generator.generate("Padel Club", location="Portobello")

    assert slug == "padel-club-portobello"


def test_slug_deduplicates_hyphens():
    """Test that multiple hyphens are deduplicated."""
    generator = SlugGenerator()

    slug = generator.generate("Test  --  Venue")

    assert slug == "test-venue"


def test_slug_handles_unicode():
    """Test Unicode character handling (accents, etc)."""
    generator = SlugGenerator()

    slug = generator.generate("Zürich Padel Café")

    assert slug == "zurich-padel-cafe"


def test_slug_handles_numbers():
    """Test that numbers are preserved."""
    generator = SlugGenerator()

    slug = generator.generate("Game4Padel Edinburgh")

    assert slug == "game4padel-edinburgh"
