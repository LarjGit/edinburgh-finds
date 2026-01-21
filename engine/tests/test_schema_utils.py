"""
Tests for extraction schema utilities.
"""

from engine.extraction.schema_utils import (
    get_extraction_fields,
    get_llm_config,
    is_field_in_schema,
)


def test_get_extraction_fields_includes_venue_fields():
    fields = get_extraction_fields()
    field_names = {field.name for field in fields}
    assert "entity_name" in field_names
    assert "tennis" in field_names


def test_get_extraction_fields_returns_universal_fields():
    """Test that get_extraction_fields returns universal entity fields (no entity type discrimination)"""
    fields = get_extraction_fields()
    field_names = {field.name for field in fields}
    assert "entity_name" in field_names
    # Note: Vertical-specific fields like "tennis" are now stored in modules JSON, not as direct fields


def test_is_field_in_schema_true_false():
    assert is_field_in_schema("entity_name") is True
    assert is_field_in_schema("not_a_real_field") is False


def test_is_field_in_schema_excludes_internal_fields():
    assert is_field_in_schema("entity_id") is False


def test_get_llm_config_contains_expected_metadata():
    config = get_llm_config()
    entity_name_config = None
    for item in config:
        if item["name"] == "entity_name":
            entity_name_config = item
            break

    assert entity_name_config is not None
    assert entity_name_config["type"] == "str"
    assert entity_name_config["required"] is True
    assert "name" in entity_name_config["search_keywords"]


def test_get_llm_config_excludes_internal_fields():
    config = get_llm_config()
    names = {item["name"] for item in config}
    assert "entity_id" not in names


def test_get_llm_config_defaults_search_keywords():
    config = get_llm_config()
    facebook_config = None
    for item in config:
        if item["name"] == "facebook_url":
            facebook_config = item
            break

    assert facebook_config is not None
    assert facebook_config["search_keywords"] == []


def test_get_llm_config_for_listing_skips_venue_fields():
    config = get_llm_config("retailer")
    names = {item["name"] for item in config}
    assert "entity_name" in names
    assert "tennis" not in names
