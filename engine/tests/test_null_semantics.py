"""
Tests for Null Semantics Enforcement in LLM Extraction

This module ensures that the extraction system correctly handles null semantics:
- null = "information not found or unknown"
- False = "explicitly false" (for booleans)
- Empty string "" is NOT allowed - use null instead

This is critical for data quality and preventing false assumptions.

Test Coverage:
- Boolean null semantics (null ≠ False)
- String null semantics (null for missing, not "Unknown" or "")
- Optional field handling
- Pydantic model validation of null semantics
"""

import pytest
from typing import Optional
from pydantic import BaseModel, Field, ValidationError


class TestBooleanNullSemantics:
    """Test that boolean fields correctly distinguish null from False"""

    def test_null_means_unknown_not_false(self):
        """Test that null is interpreted as 'unknown', not as False"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        # Create extraction with null currently_open
        venue = EntityExtraction(
            entity_name="Test Venue",
            currently_open=None
        )

        # null should be preserved, not coerced to False
        assert venue.currently_open is None
        assert venue.currently_open is not False

    def test_explicit_false_is_different_from_null(self):
        """Test that False explicitly means 'no', different from null ('unknown')"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        # Create extraction with explicitly False currently_open
        venue_closed = EntityExtraction(
            entity_name="Closed Venue",
            currently_open=False
        )

        # Create extraction with null currently_open
        venue_unknown = EntityExtraction(
            entity_name="Unknown Venue",
            currently_open=None
        )

        # False and null should be different
        assert venue_closed.currently_open is False
        assert venue_unknown.currently_open is None
        assert venue_closed.currently_open != venue_unknown.currently_open

    def test_explicit_true_means_yes(self):
        """Test that True explicitly means 'yes'"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        venue = EntityExtraction(
            entity_name="Open Venue",
            currently_open=True
        )

        assert venue.currently_open is True


class TestStringNullSemantics:
    """Test that string fields use null for missing data, not empty strings"""

    def test_optional_string_accepts_null(self):
        """Test that optional string fields accept null values"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        venue = EntityExtraction(
            entity_name="Test Venue",
            street_address=None,
            city=None,
            phone=None,
            website=None
        )

        assert venue.street_address is None
        assert venue.city is None
        assert venue.phone is None
        assert venue.website is None

    def test_empty_string_should_not_be_used_for_missing_data(self):
        """
        Test that empty strings are not used for missing data.
        Note: Pydantic doesn't prevent empty strings by default, but our
        convention is to use null for missing data, not empty strings.
        """
        from engine.extraction.models.entity_extraction import EntityExtraction

        # This documents the convention - prefer null over empty string
        # If a field has no value, use None, not ""
        venue_with_null = EntityExtraction(
            entity_name="Test Venue",
            phone=None  # Correct: Use None for missing data
        )

        # Empty string should fail validation due to E.164 check
        with pytest.raises(ValidationError):
            EntityExtraction(
                entity_name="Test Venue",
                phone=""  # Not recommended: Empty string suggests "no phone" vs "unknown phone"
            )

        # Null is preferred for "unknown"
        assert venue_with_null.phone is None

    def test_required_string_cannot_be_null(self):
        """Test that required string fields (like entity_name) cannot be null"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        with pytest.raises(ValidationError) as exc_info:
            EntityExtraction(
                entity_name=None  # Required field, cannot be null
            )

        errors = exc_info.value.errors()
        assert any(err['loc'] == ('entity_name',) for err in errors)

    def test_required_string_cannot_be_empty(self):
        """Test that required string fields cannot be empty or whitespace"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        # Empty string should fail validation
        with pytest.raises(ValidationError) as exc_info:
            EntityExtraction(entity_name="")

        errors = exc_info.value.errors()
        assert any('entity_name' in str(err) for err in errors)

        # Whitespace-only should fail validation
        with pytest.raises(ValidationError) as exc_info:
            EntityExtraction(entity_name="   ")

        errors = exc_info.value.errors()
        assert any('entity_name' in str(err) for err in errors)


class TestOptionalFieldHandling:
    """Test that optional fields are properly handled with null defaults"""

    def test_optional_fields_default_to_null(self):
        """Test that optional fields have null as default value"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        # Create minimal extraction with only required field
        venue = EntityExtraction(entity_name="Minimal Venue")

        # All optional fields should be None
        assert venue.street_address is None
        assert venue.city is None
        assert venue.postcode is None
        assert venue.phone is None
        assert venue.email is None
        assert venue.website is None
        assert venue.categories is None
        assert venue.rating is None
        assert venue.user_rating_count is None
        assert venue.summary is None
        assert venue.opening_hours is None
        assert venue.currently_open is None
        assert venue.external_id is None
        assert venue.discovered_attributes is None

    def test_optional_fields_can_be_explicitly_set_to_null(self):
        """Test that optional fields can be explicitly set to None"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        venue = EntityExtraction(
            entity_name="Test Venue",
            phone=None,  # Explicitly null
            rating=None,  # Explicitly null
            currently_open=None  # Explicitly null
        )

        assert venue.phone is None
        assert venue.rating is None
        assert venue.currently_open is None


class TestLLMPromptGuidance:
    """
    Test that our model structure guides LLM to use correct null semantics.
    These tests verify that the field descriptions and validation encourage
    proper null usage.
    """

    def test_field_descriptions_mention_null_handling(self):
        """Test that field descriptions explicitly mention null behavior"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        # Check that docstrings mention null behavior
        schema = EntityExtraction.model_json_schema()

        # Check a few key fields have null guidance in description
        properties = schema.get('properties', {})

        # street_address should mention "Null if not found"
        assert 'street_address' in properties
        assert 'null' in properties['street_address']['description'].lower()

        # currently_open should mention null semantics for booleans
        assert 'currently_open' in properties
        description = properties['currently_open']['description'].lower()
        assert 'null' in description or 'unknown' in description

    def test_model_has_example_with_proper_null_usage(self):
        """Test that model includes an example showing correct null usage"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        schema = EntityExtraction.model_json_schema()

        # Should have an example in the schema
        assert 'examples' in schema or 'example' in schema or 'example' in schema.get('$defs', {}).get('Config', {})


class TestDictionaryNullSemantics:
    """Test null semantics for dictionary fields like discovered_attributes"""

    def test_discovered_attributes_can_be_null(self):
        """Test that discovered_attributes can be null when no extra data found"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        venue = EntityExtraction(
            entity_name="Basic Venue",
            discovered_attributes=None  # No extra attributes discovered
        )

        assert venue.discovered_attributes is None

    def test_discovered_attributes_can_be_empty_dict(self):
        """Test that discovered_attributes can be an empty dict vs null"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        # null = "didn't look for extra attributes"
        venue_null = EntityExtraction(
            entity_name="Venue 1",
            discovered_attributes=None
        )

        # {} = "looked for extra attributes, found none"
        venue_empty = EntityExtraction(
            entity_name="Venue 2",
            discovered_attributes={}
        )

        assert venue_null.discovered_attributes is None
        assert venue_empty.discovered_attributes == {}
        assert venue_null.discovered_attributes != venue_empty.discovered_attributes

    def test_discovered_attributes_with_null_values_inside_dict(self):
        """Test that discovered_attributes dict can contain null values"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        venue = EntityExtraction(
            entity_name="Venue",
            discovered_attributes={
                "has_parking": True,
                "wheelchair_accessible": None,  # Unknown
                "has_cafe": False  # Explicitly no
            }
        )

        attrs = venue.discovered_attributes
        assert attrs["has_parking"] is True
        assert attrs["wheelchair_accessible"] is None
        assert attrs["has_cafe"] is False


class TestListNullSemantics:
    """Test null semantics for list fields like categories"""

    def test_categories_can_be_null(self):
        """Test that categories can be null when not found"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        venue = EntityExtraction(
            entity_name="Venue",
            categories=None  # Categories not found
        )

        assert venue.categories is None

    def test_categories_can_be_empty_list(self):
        """Test difference between null list and empty list"""
        from engine.extraction.models.entity_extraction import EntityExtraction

        # null = "didn't find categories"
        venue_null = EntityExtraction(
            entity_name="Venue 1",
            categories=None
        )

        # [] = "found categories list, but it's empty"
        # (This is unlikely in practice, but semantically different)
        venue_empty = EntityExtraction(
            entity_name="Venue 2",
            categories=[]
        )

        assert venue_null.categories is None
        assert venue_empty.categories == []
        assert venue_null.categories != venue_empty.categories
