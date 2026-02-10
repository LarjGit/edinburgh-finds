"""
Tests for EntityExtraction model - validates universal amenity fields.

Validates LA-017: Universal amenity fields exist in EntityExtraction model
and are correctly typed as Phase-1 primitives.
"""

import pytest
from pydantic import ValidationError

from engine.extraction.models.entity_extraction import EntityExtraction


class TestUniversalAmenityFields:
    """Test that universal amenity fields exist in EntityExtraction model."""

    def test_entity_extraction_has_locality_field(self):
        """Validates LA-017: locality field exists with correct type."""
        # Test that EntityExtraction accepts locality as Optional[str]
        entity = EntityExtraction(
            entity_name="Test Entity",
            locality="Portobello"
        )
        assert entity.locality == "Portobello"

        # Test None is valid
        entity_none = EntityExtraction(
            entity_name="Test Entity",
            locality=None
        )
        assert entity_none.locality is None

    def test_entity_extraction_has_wifi_field(self):
        """Validates LA-017: wifi field exists with correct type."""
        # Test that EntityExtraction accepts wifi as Optional[bool]
        entity = EntityExtraction(
            entity_name="Test Entity",
            wifi=True
        )
        assert entity.wifi is True

        # Test None is valid
        entity_none = EntityExtraction(
            entity_name="Test Entity",
            wifi=None
        )
        assert entity_none.wifi is None

    def test_entity_extraction_has_parking_available_field(self):
        """Validates LA-017: parking_available field exists with correct type."""
        # Test that EntityExtraction accepts parking_available as Optional[bool]
        entity = EntityExtraction(
            entity_name="Test Entity",
            parking_available=True
        )
        assert entity.parking_available is True

        # Test None is valid
        entity_none = EntityExtraction(
            entity_name="Test Entity",
            parking_available=None
        )
        assert entity_none.parking_available is None

    def test_entity_extraction_has_disabled_access_field(self):
        """Validates LA-017: disabled_access field exists with correct type."""
        # Test that EntityExtraction accepts disabled_access as Optional[bool]
        entity = EntityExtraction(
            entity_name="Test Entity",
            disabled_access=True
        )
        assert entity.disabled_access is True

        # Test None is valid
        entity_none = EntityExtraction(
            entity_name="Test Entity",
            disabled_access=None
        )
        assert entity_none.disabled_access is None

    def test_boolean_amenity_fields_accept_none_true_false(self):
        """Validates LA-017: boolean amenity fields accept None/True/False."""
        # Test all combinations of boolean values
        entity_all_true = EntityExtraction(
            entity_name="Test Entity",
            wifi=True,
            parking_available=True,
            disabled_access=True
        )
        assert entity_all_true.wifi is True
        assert entity_all_true.parking_available is True
        assert entity_all_true.disabled_access is True

        entity_all_false = EntityExtraction(
            entity_name="Test Entity",
            wifi=False,
            parking_available=False,
            disabled_access=False
        )
        assert entity_all_false.wifi is False
        assert entity_all_false.parking_available is False
        assert entity_all_false.disabled_access is False

        entity_all_none = EntityExtraction(
            entity_name="Test Entity",
            wifi=None,
            parking_available=None,
            disabled_access=None
        )
        assert entity_all_none.wifi is None
        assert entity_all_none.parking_available is None
        assert entity_all_none.disabled_access is None

    def test_all_four_amenity_fields_together(self):
        """Validates LA-017: all four amenity fields work together."""
        entity = EntityExtraction(
            entity_name="Complete Test Entity",
            locality="Leith",
            wifi=True,
            parking_available=False,
            disabled_access=True
        )
        assert entity.locality == "Leith"
        assert entity.wifi is True
        assert entity.parking_available is False
        assert entity.disabled_access is True


class TestNegativeValidations:
    """Negative tests: amenity fields must NOT exist in wrong places."""

    def test_amenity_fields_not_in_extraction_fields_section(self):
        """Validates LA-017: amenity fields are in fields:, NOT extraction_fields:."""
        import yaml
        from pathlib import Path

        # Load entity.yaml
        schema_path = Path("engine/config/schemas/entity.yaml")
        with open(schema_path, "r") as f:
            schema = yaml.safe_load(f)

        # Check extraction_fields section
        extraction_fields = schema.get("extraction_fields", [])
        extraction_field_names = [field["name"] for field in extraction_fields]

        # Assert amenity fields are NOT in extraction_fields
        assert "locality" not in extraction_field_names, \
            "locality should be in fields:, not extraction_fields:"
        assert "wifi" not in extraction_field_names, \
            "wifi should be in fields:, not extraction_fields:"
        assert "parking_available" not in extraction_field_names, \
            "parking_available should be in fields:, not extraction_fields:"
        assert "disabled_access" not in extraction_field_names, \
            "disabled_access should be in fields:, not extraction_fields:"

    def test_amenity_fields_not_in_entity_model_yaml(self):
        """Validates LA-017: amenity fields are NOT defined in entity_model.yaml."""
        from pathlib import Path

        # Load entity_model.yaml as text (schema may be complex)
        model_path = Path("engine/config/entity_model.yaml")
        with open(model_path, "r") as f:
            content = f.read()

        # String search for field names (should not appear as schema definitions)
        assert "locality:" not in content, \
            "locality should not be defined in entity_model.yaml"
        assert "wifi:" not in content, \
            "wifi should not be defined in entity_model.yaml"
        assert "parking_available:" not in content, \
            "parking_available should not be defined in entity_model.yaml"
        assert "disabled_access:" not in content, \
            "disabled_access should not be defined in entity_model.yaml"

    def test_amenity_fields_are_in_main_fields_section(self):
        """Validates LA-017: amenity fields exist in fields: section with exclude: false."""
        import yaml
        from pathlib import Path

        # Load entity.yaml
        schema_path = Path("engine/config/schemas/entity.yaml")
        with open(schema_path, "r") as f:
            schema = yaml.safe_load(f)

        # Check fields section
        fields = schema.get("fields", [])
        field_dict = {field["name"]: field for field in fields}

        # Assert amenity fields ARE in fields section
        assert "locality" in field_dict, "locality should be in fields: section"
        assert "wifi" in field_dict, "wifi should be in fields: section"
        assert "parking_available" in field_dict, "parking_available should be in fields: section"
        assert "disabled_access" in field_dict, "disabled_access should be in fields: section"

        # Assert exclude: false (or omitted, which defaults to false)
        for field_name in ["locality", "wifi", "parking_available", "disabled_access"]:
            field = field_dict[field_name]
            exclude_value = field.get("exclude", False)  # Default to False if omitted
            assert exclude_value is False, \
                f"{field_name} should have exclude: false (is Phase-1 primitive)"
