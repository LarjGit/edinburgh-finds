"""
Tests for lens configuration loader.

Validates that VerticalLens correctly loads and validates lens.yaml files,
with fail-fast behavior on validation errors.
"""

import pytest
import yaml
from pathlib import Path

from engine.lenses.loader import VerticalLens, LensConfigError
from engine.lenses.validator import ValidationError


class TestVerticalLensLoading:
    """Test VerticalLens loading and validation."""

    def test_load_valid_config_succeeds(self, tmp_path):
        """Loading a valid lens.yaml should succeed."""
        config_path = tmp_path / "lens.yaml"

        valid_config = {
            "facets": {
                "activity": {
                    "dimension_source": "canonical_activities",
                    "display_name": "Activity",
                    "display_in_ui": True
                }
            },
            "values": [
                {
                    "key": "padel",
                    "facet": "activity",
                    "display_name": "Padel"
                }
            ],
            "mapping_rules": [
                {
                    "raw": ["paddle tennis"],
                    "canonical": "padel"
                }
            ]
        }

        # Write valid config to file
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(valid_config, f)

        # Should load successfully
        lens = VerticalLens(config_path)

        # Verify config was loaded
        assert lens.facets == valid_config["facets"]
        assert lens.values == valid_config["values"]
        assert lens.mapping_rules == valid_config["mapping_rules"]

    def test_load_invalid_config_fails_immediately(self, tmp_path):
        """Loading lens.yaml with invalid dimension_source should fail at load time."""
        config_path = tmp_path / "lens.yaml"

        invalid_config = {
            "facets": {
                "activity": {
                    "dimension_source": "invalid_dimension",  # Invalid!
                    "display_name": "Activity"
                }
            },
            "values": [],
            "mapping_rules": []
        }

        # Write invalid config to file
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config, f)

        # Should fail immediately with clear error message
        with pytest.raises(LensConfigError, match="Invalid lens config"):
            VerticalLens(config_path)

    def test_error_message_identifies_contract_violation(self, tmp_path):
        """Error message should clearly identify which contract was violated."""
        config_path = tmp_path / "lens.yaml"

        invalid_config = {
            "facets": {
                "activity": {
                    "dimension_source": "invalid_dimension",
                    "display_name": "Activity"
                }
            },
            "values": [],
            "mapping_rules": []
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config, f)

        # Should mention dimension_source in error
        with pytest.raises(LensConfigError, match="dimension_source"):
            VerticalLens(config_path)

    def test_nonexistent_file_raises_error(self, tmp_path):
        """Loading non-existent file should raise clear error."""
        config_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(LensConfigError, match="not found"):
            VerticalLens(config_path)

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Loading malformed YAML should raise clear error."""
        config_path = tmp_path / "invalid.yaml"

        # Write invalid YAML
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write("facets:\n  - this is: [invalid yaml syntax")

        with pytest.raises(LensConfigError, match="Failed to parse YAML"):
            VerticalLens(config_path)

    def test_non_dict_config_raises_error(self, tmp_path):
        """Loading YAML that doesn't parse to dict should raise clear error."""
        config_path = tmp_path / "list.yaml"

        # Write YAML that parses to list, not dict
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(["item1", "item2"], f)

        with pytest.raises(LensConfigError, match="Expected dict"):
            VerticalLens(config_path)


class TestVerticalLensProperties:
    """Test VerticalLens property accessors."""

    def test_facets_property(self, tmp_path):
        """facets property should return facets section."""
        config_path = tmp_path / "lens.yaml"

        config = {
            "facets": {
                "activity": {
                    "dimension_source": "canonical_activities",
                    "display_name": "Activity"
                }
            },
            "values": [],
            "mapping_rules": []
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        lens = VerticalLens(config_path)
        assert lens.facets == config["facets"]

    def test_values_property(self, tmp_path):
        """values property should return values section."""
        config_path = tmp_path / "lens.yaml"

        config = {
            "facets": {
                "activity": {
                    "dimension_source": "canonical_activities",
                    "display_name": "Activity"
                }
            },
            "values": [
                {"key": "padel", "facet": "activity", "display_name": "Padel"}
            ],
            "mapping_rules": []
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        lens = VerticalLens(config_path)
        assert lens.values == config["values"]

    def test_mapping_rules_property(self, tmp_path):
        """mapping_rules property should return mapping_rules section."""
        config_path = tmp_path / "lens.yaml"

        config = {
            "facets": {
                "activity": {
                    "dimension_source": "canonical_activities",
                    "display_name": "Activity"
                }
            },
            "values": [
                {"key": "padel", "facet": "activity", "display_name": "Padel"}
            ],
            "mapping_rules": [
                {"raw": ["paddle tennis"], "canonical": "padel"}
            ]
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        lens = VerticalLens(config_path)
        assert lens.mapping_rules == config["mapping_rules"]

    def test_missing_sections_return_defaults(self, tmp_path):
        """Missing sections should return sensible defaults."""
        config_path = tmp_path / "lens.yaml"

        # Minimal valid config (only facets)
        config = {
            "facets": {
                "activity": {
                    "dimension_source": "canonical_activities",
                    "display_name": "Activity"
                }
            }
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        lens = VerticalLens(config_path)

        # Missing sections should return empty collections
        assert lens.values == []
        assert lens.mapping_rules == []
        assert lens.derived_groupings == []
        assert lens.domain_modules == {}
        assert lens.module_triggers == []


class TestFailFastBehavior:
    """Test that validation is fail-fast at load time, not runtime."""

    def test_validation_runs_at_init_not_runtime(self, tmp_path):
        """Validation should run at __init__ time, not when accessing properties."""
        config_path = tmp_path / "lens.yaml"

        invalid_config = {
            "facets": {
                "activity": {
                    "dimension_source": "invalid_dimension"
                }
            },
            "values": [],
            "mapping_rules": []
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config, f)

        # Should fail at initialization
        with pytest.raises(LensConfigError):
            lens = VerticalLens(config_path)
            # Should never reach here
            _ = lens.facets  # This line should not execute

    def test_multiple_contract_violations_reports_first(self, tmp_path):
        """When multiple contracts are violated, should report the first one encountered."""
        config_path = tmp_path / "lens.yaml"

        # Multiple violations: invalid dimension_source AND invalid facet reference
        invalid_config = {
            "facets": {
                "activity": {
                    "dimension_source": "invalid_dimension",  # Violation 1
                    "display_name": "Activity"
                }
            },
            "values": [
                {
                    "key": "padel",
                    "facet": "nonexistent_facet",  # Violation 2
                    "display_name": "Padel"
                }
            ],
            "mapping_rules": []
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config, f)

        # Should fail on first violation (dimension_source)
        with pytest.raises(LensConfigError, match="dimension_source"):
            VerticalLens(config_path)
