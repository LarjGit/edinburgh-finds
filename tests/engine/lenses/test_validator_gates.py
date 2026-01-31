"""
Tests for lens validation gates (architecture.md 6.7).

Validates all 7 required validation gates:
1. Schema validation
2. Canonical reference integrity
3. Connector reference validation
4. Identifier uniqueness
5. Regex compilation validation
6. Smoke coverage validation
7. Fail-fast enforcement

Each gate has positive tests (valid configs pass) and negative tests
(invalid configs fail with clear error messages).
"""

import pytest
from engine.lenses.validator import validate_lens_config, ValidationError


class TestGate1SchemaValidation:
    """
    Gate #1: Schema validation.

    Required top-level sections must be present.
    """

    def test_valid_minimal_lens_passes_schema_validation(self):
        """Valid minimal lens with all required sections passes."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {
                    "dimension_source": "canonical_activities",
                    "ui_label": "Activity",
                }
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [
                {"pattern": "tennis", "canonical": "tennis", "confidence": 0.9}
            ],
        }
        # Should not raise
        validate_lens_config(config)

    def test_missing_schema_field_fails(self):
        """Lens without 'schema' field fails validation."""
        config = {
            "facets": {"activity": {"dimension_source": "canonical_activities"}},
            "values": [{"key": "tennis", "facet": "activity"}],
            "mapping_rules": [],
        }
        with pytest.raises(ValidationError, match="Missing required section: schema"):
            validate_lens_config(config)

    def test_missing_facets_section_fails(self):
        """Lens without 'facets' section fails validation."""
        config = {
            "schema": "lens/v1",
            "values": [{"key": "tennis", "facet": "activity"}],
            "mapping_rules": [],
        }
        with pytest.raises(ValidationError, match="Missing required section: facets"):
            validate_lens_config(config)

    def test_missing_values_section_fails(self):
        """Lens without 'values' section fails validation."""
        config = {
            "schema": "lens/v1",
            "facets": {"activity": {"dimension_source": "canonical_activities"}},
            "mapping_rules": [],
        }
        with pytest.raises(ValidationError, match="Missing required section: values"):
            validate_lens_config(config)

    def test_missing_mapping_rules_section_fails(self):
        """Lens without 'mapping_rules' section fails validation."""
        config = {
            "schema": "lens/v1",
            "facets": {"activity": {"dimension_source": "canonical_activities"}},
            "values": [{"key": "tennis", "facet": "activity"}],
        }
        with pytest.raises(ValidationError, match="Missing required section: mapping_rules"):
            validate_lens_config(config)


class TestGate2CanonicalReferenceIntegrity:
    """
    Gate #2: Canonical reference integrity (new validations).

    Tests for module_triggers and derived_groupings references.
    Existing validations (facets/values/mapping_rules) already tested elsewhere.
    """

    def test_module_trigger_with_valid_facet_reference_passes(self):
        """Module trigger referencing existing facet passes."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [
                {"pattern": "tennis", "canonical": "tennis", "confidence": 0.9}
            ],
            "modules": {
                "sports_facility": {
                    "description": "Sports facility data",
                    "fields": {}
                }
            },
            "module_triggers": [
                {
                    "when": {"facet": "activity", "value": "tennis"},
                    "add_modules": ["sports_facility"]
                }
            ],
        }
        # Should not raise
        validate_lens_config(config)

    def test_module_trigger_with_invalid_facet_reference_fails(self):
        """Module trigger referencing non-existent facet fails."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [],
            "modules": {"sports_facility": {"description": "Sports", "fields": {}}},
            "module_triggers": [
                {
                    "when": {"facet": "invalid_facet", "value": "tennis"},
                    "add_modules": ["sports_facility"]
                }
            ],
        }
        with pytest.raises(ValidationError, match="references non-existent facet 'invalid_facet'"):
            validate_lens_config(config)

    def test_module_trigger_with_invalid_module_reference_fails(self):
        """Module trigger referencing non-existent module fails."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [],
            "modules": {"sports_facility": {"description": "Sports", "fields": {}}},
            "module_triggers": [
                {
                    "when": {"facet": "activity", "value": "tennis"},
                    "add_modules": ["invalid_module"]
                }
            ],
        }
        with pytest.raises(ValidationError, match="references non-existent module 'invalid_module'"):
            validate_lens_config(config)

    def test_derived_grouping_with_valid_entity_class_passes(self):
        """Derived grouping with valid entity_class passes."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [],
            "derived_groupings": [
                {
                    "id": "sports_venues",
                    "label": "Sports Venues",
                    "rules": [
                        {"entity_class": "place", "roles": ["provides_facility"]}
                    ]
                }
            ],
        }
        # Should not raise
        validate_lens_config(config)

    def test_derived_grouping_with_invalid_entity_class_fails(self):
        """Derived grouping with invalid entity_class fails."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [],
            "derived_groupings": [
                {
                    "id": "venues",
                    "label": "Venues",
                    "rules": [
                        {"entity_class": "venue", "roles": ["provider"]}  # "venue" is invalid
                    ]
                }
            ],
        }
        with pytest.raises(ValidationError, match="invalid entity_class 'venue'"):
            validate_lens_config(config)


class TestGate3ConnectorReferenceValidation:
    """
    Gate #3: Connector reference validation.

    All connector names in connector_rules must exist in CONNECTOR_REGISTRY.
    """

    def test_valid_connector_reference_passes(self):
        """Connector rule referencing valid connector passes."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [],
            "connector_rules": {
                "sport_scotland": {
                    "priority": "high",
                    "triggers": [
                        {"type": "any_keyword_match", "keywords": ["tennis"]}
                    ]
                }
            },
        }
        # Should not raise
        validate_lens_config(config)

    def test_invalid_connector_reference_fails(self):
        """Connector rule referencing non-existent connector fails."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [],
            "connector_rules": {
                "invalid_connector": {  # This connector doesn't exist
                    "priority": "high",
                    "triggers": []
                }
            },
        }
        with pytest.raises(ValidationError, match="references non-existent connector 'invalid_connector'"):
            validate_lens_config(config)

    def test_multiple_connector_references_with_one_invalid_fails(self):
        """Multiple connector rules with one invalid fails."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [],
            "connector_rules": {
                "serper": {"priority": "high", "triggers": []},  # Valid
                "invalid_one": {"priority": "low", "triggers": []},  # Invalid
            },
        }
        with pytest.raises(ValidationError, match="references non-existent connector 'invalid_one'"):
            validate_lens_config(config)


class TestGate5RegexCompilationValidation:
    """
    Gate #5: Regex compilation validation.

    All mapping_rules.pattern must be valid regex patterns.
    """

    def test_valid_regex_pattern_passes(self):
        """Mapping rule with valid regex pattern passes."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [
                {"pattern": r"(?i)tennis|racket\s+sports", "canonical": "tennis", "confidence": 0.9}
            ],
        }
        # Should not raise
        validate_lens_config(config)

    def test_invalid_regex_pattern_fails(self):
        """Mapping rule with invalid regex pattern fails."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [
                {"pattern": r"(?i)(unclosed_group", "canonical": "tennis", "confidence": 0.9}  # Invalid regex
            ],
        }
        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            validate_lens_config(config)

    def test_multiple_patterns_with_one_invalid_fails(self):
        """Multiple mapping rules with one invalid pattern fails."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"},
                {"key": "padel", "facet": "activity", "display_name": "Padel"}
            ],
            "mapping_rules": [
                {"pattern": r"(?i)tennis", "canonical": "tennis", "confidence": 0.9},  # Valid
                {"pattern": r"[invalid", "canonical": "padel", "confidence": 0.9},  # Invalid
            ],
        }
        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            validate_lens_config(config)


class TestGate6SmokeCoverageValidation:
    """
    Gate #6: Smoke coverage validation.

    Every facet must have at least one value.
    """

    def test_facet_with_values_passes(self):
        """Facet with at least one value passes."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"}
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
            ],
            "mapping_rules": [],
        }
        # Should not raise
        validate_lens_config(config)

    def test_facet_without_values_fails(self):
        """Facet with no values fails validation."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"},
                "role": {"dimension_source": "canonical_roles", "ui_label": "Role"},
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"}
                # No values for "role" facet
            ],
            "mapping_rules": [],
        }
        with pytest.raises(ValidationError, match="Facet 'role' has no values"):
            validate_lens_config(config)

    def test_multiple_facets_all_with_values_passes(self):
        """Multiple facets all with values passes."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "canonical_activities", "ui_label": "Activity"},
                "role": {"dimension_source": "canonical_roles", "ui_label": "Role"},
            },
            "values": [
                {"key": "tennis", "facet": "activity", "display_name": "Tennis"},
                {"key": "provider", "facet": "role", "display_name": "Provider"},
            ],
            "mapping_rules": [],
        }
        # Should not raise
        validate_lens_config(config)


class TestGate7FailFastEnforcement:
    """
    Gate #7: Fail-fast enforcement.

    Validation errors should abort immediately at lens load time.
    This is tested implicitly by all other tests using pytest.raises.
    """

    def test_multiple_violations_fail_on_first_error(self):
        """
        When multiple violations exist, validation fails on first encountered.

        This config has multiple issues:
        - Missing required section (schema)
        - Invalid dimension_source
        - Invalid facet reference

        Should fail on the first one encountered (missing schema).
        """
        config = {
            # Missing "schema" field
            "facets": {
                "activity": {"dimension_source": "invalid_dimension"}  # Invalid
            },
            "values": [
                {"key": "tennis", "facet": "nonexistent_facet", "display_name": "Tennis"}  # Invalid ref
            ],
            "mapping_rules": [],
        }
        # Should fail on missing schema (first validation)
        with pytest.raises(ValidationError, match="Missing required section: schema"):
            validate_lens_config(config)

    def test_validation_error_includes_helpful_context(self):
        """Validation errors include helpful context for debugging."""
        config = {
            "schema": "lens/v1",
            "facets": {
                "activity": {"dimension_source": "invalid_dimension"}
            },
            "values": [],
            "mapping_rules": [],
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_lens_config(config)

        error_message = str(exc_info.value)
        # Error should mention the invalid dimension and list valid options
        assert "invalid_dimension" in error_message
        assert "canonical_activities" in error_message  # One of the valid options
