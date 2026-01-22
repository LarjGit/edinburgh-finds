"""
Tests for the extraction BaseExtractor interface.
"""

import pytest

from engine.extraction.base import BaseExtractor


class MinimalExtractor(BaseExtractor):
    @property
    def source_name(self) -> str:
        return "test_source"

    def extract(self, raw_data: dict) -> dict:
        return {"entity_name": "Test Venue"}

    def validate(self, extracted: dict) -> dict:
        return extracted

    def split_attributes(self, extracted: dict) -> tuple[dict, dict]:
        return extracted, {}


def test_base_extractor_is_abstract():
    """BaseExtractor should not be instantiable."""
    with pytest.raises(TypeError):
        BaseExtractor()


def test_base_extractor_requires_abstract_methods():
    """Missing abstract methods should prevent instantiation."""

    class MissingExtractor(BaseExtractor):
        @property
        def source_name(self) -> str:
            return "missing"

        def extract(self, raw_data: dict) -> dict:
            return raw_data

    with pytest.raises(TypeError):
        MissingExtractor()


def test_minimal_extractor_works():
    """Concrete extractor implementations should be usable."""
    extractor = MinimalExtractor()
    assert extractor.source_name == "test_source"
    assert extractor.extract({})["entity_name"] == "Test Venue"
    assert extractor.validate({"ok": True}) == {"ok": True}
    assert extractor.split_attributes({"a": 1}) == ({"a": 1}, {})

