"""
Tests for attribute splitting logic.
"""

from engine.extraction.attribute_splitter import split_attributes


def test_attribute_splitter_separates_schema_and_discovered_fields():
    extracted = {"entity_name": "Test Venue", "tennis": True, "custom": 1}
    attributes, discovered = split_attributes(extracted)

    assert attributes["entity_name"] == "Test Venue"
    assert attributes["tennis"] is True
    assert "custom" not in attributes
    assert discovered["custom"] == 1


def test_attribute_splitter_merges_discovered_attributes_dict():
    extracted = {"entity_name": "Test Venue", "discovered_attributes": {"foo": "bar"}}
    attributes, discovered = split_attributes(extracted)

    assert "discovered_attributes" not in attributes
    assert discovered["foo"] == "bar"


def test_attribute_splitter_keeps_non_dict_discovered_attributes():
    extracted = {"discovered_attributes": "raw", "unknown": 2}
    attributes, discovered = split_attributes(extracted)

    assert attributes == {}
    assert discovered["discovered_attributes"] == "raw"
    assert discovered["unknown"] == 2

