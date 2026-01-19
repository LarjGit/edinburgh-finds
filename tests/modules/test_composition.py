"""
Tests for module composition validation.

Validates that modules are properly namespaced in JSONB and that duplicate
module keys are rejected at YAML load time.
"""

import pytest
import yaml
from pathlib import Path

from engine.modules.validator import (
    validate_modules_namespacing,
    ModuleValidationError
)


class TestModuleNamespacing:
    """Test module namespacing validation."""

    def test_properly_namespaced_modules_pass(self):
        """Properly namespaced modules should pass validation."""
        modules_data = {
            "location": {
                "latitude": 55.95,
                "longitude": -3.18,
                "street_address": "123 Main St"
            },
            "contact": {
                "phone": "+44 131 555 0100",
                "email": "info@example.com"
            },
            "sports_facility": {
                "inventory": {
                    "tennis": {"total": 6},
                    "padel": {"total": 4}
                }
            }
        }

        # Should not raise
        validate_modules_namespacing(modules_data)

    def test_flattened_modules_raise_error(self):
        """Flattened modules structure should raise ValidationError."""
        flattened_modules = {
            "latitude": 55.95,
            "longitude": -3.18,
            "phone": "+44 131 555 0100",
            "inventory": {"tennis": {"total": 6}}
        }

        with pytest.raises(ModuleValidationError, match="modules JSONB must be namespaced by module key"):
            validate_modules_namespacing(flattened_modules)

    def test_duplicate_field_names_across_modules_allowed(self):
        """Duplicate field names across DIFFERENT modules are allowed due to namespacing."""
        modules_with_duplicate_field_names = {
            "sports_facility": {
                "name": "Tennis Centre",
                "capacity": 100
            },
            "wine_production": {
                "name": "Vineyard Name",
                "capacity": 5000
            }
        }

        # Should not raise - namespacing makes this safe
        validate_modules_namespacing(modules_with_duplicate_field_names)

    def test_empty_modules_allowed(self):
        """Empty modules dict should be allowed."""
        validate_modules_namespacing({})

    def test_module_with_empty_fields_allowed(self):
        """Module with empty fields dict should be allowed."""
        modules_data = {
            "location": {},
            "contact": {"phone": "+44 131 555 0100"}
        }

        validate_modules_namespacing(modules_data)


class TestDuplicateModuleKeys:
    """Test that duplicate module keys are rejected at YAML load time."""

    def test_duplicate_keys_in_yaml_rejected(self, tmp_path):
        """YAML with duplicate module keys should be rejected at load time."""
        yaml_content = """
modules:
  sports_facility:
    description: "First definition"
    fields:
      inventory:
        type: json
  sports_facility:
    description: "Duplicate definition"
    fields:
      capacity:
        type: integer
"""

        yaml_path = tmp_path / "test.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        # Should raise error when loading
        from engine.modules.validator import load_yaml_strict

        with pytest.raises((yaml.YAMLError, ModuleValidationError), match="duplicate"):
            load_yaml_strict(yaml_path)

    def test_unique_module_keys_pass(self, tmp_path):
        """YAML with unique module keys should load successfully."""
        yaml_content = """
modules:
  sports_facility:
    description: "Sports facility info"
    fields:
      inventory:
        type: json
  contact:
    description: "Contact info"
    fields:
      phone:
        type: string
"""

        yaml_path = tmp_path / "test.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        from engine.modules.validator import load_yaml_strict

        # Should load successfully
        data = load_yaml_strict(yaml_path)
        assert "modules" in data
        assert "sports_facility" in data["modules"]
        assert "contact" in data["modules"]


class TestYAMLStrictLoader:
    """Test strict YAML loader that rejects duplicate keys."""

    def test_rejects_duplicate_top_level_keys(self, tmp_path):
        """Duplicate top-level keys should be rejected."""
        yaml_content = """
name: "First"
description: "Something"
name: "Duplicate"
"""

        yaml_path = tmp_path / "test.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        from engine.modules.validator import load_yaml_strict

        with pytest.raises((yaml.YAMLError, ModuleValidationError), match="duplicate"):
            load_yaml_strict(yaml_path)

    def test_rejects_duplicate_nested_keys(self, tmp_path):
        """Duplicate nested keys should be rejected."""
        yaml_content = """
modules:
  location:
    latitude: 55.95
    longitude: -3.18
    latitude: 56.00
"""

        yaml_path = tmp_path / "test.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        from engine.modules.validator import load_yaml_strict

        with pytest.raises((yaml.YAMLError, ModuleValidationError), match="duplicate"):
            load_yaml_strict(yaml_path)

    def test_loads_valid_yaml(self, tmp_path):
        """Valid YAML with no duplicates should load successfully."""
        yaml_content = """
name: "Test"
description: "Valid YAML"
modules:
  location:
    latitude: 55.95
    longitude: -3.18
  contact:
    phone: "+44 131 555 0100"
"""

        yaml_path = tmp_path / "test.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        from engine.modules.validator import load_yaml_strict

        data = load_yaml_strict(yaml_path)
        assert data["name"] == "Test"
        assert "modules" in data
        assert len(data["modules"]) == 2


class TestIntegrationWithLoaders:
    """Test integration with entity_model.yaml and lens.yaml loaders."""

    def test_entity_model_loader_rejects_duplicate_keys(self, tmp_path):
        """entity_model.yaml loader should reject duplicate module keys."""
        # This will be tested once we update the actual loaders
        pass

    def test_lens_loader_rejects_duplicate_keys(self, tmp_path):
        """lens.yaml loader should reject duplicate module keys."""
        # This will be tested once we update the actual loaders
        pass
