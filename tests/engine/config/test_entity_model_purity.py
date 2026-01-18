"""
Test suite for entity_model.yaml purity.

Validates that the entity model configuration is 100% vertical-agnostic
with zero domain-specific concepts.
"""

import os
import pytest
import yaml
from pathlib import Path


# Forbidden vertical-specific keywords
FORBIDDEN_VERTICAL_KEYWORDS = {
    # Sports vertical
    "padel", "tennis", "gym", "swimming", "football", "basketball",
    "court", "pitch", "field", "pool", "track", "rink",
    "sports", "fitness", "athletic", "coach", "instructor",

    # Wine vertical
    "wine", "winery", "vineyard", "tasting", "cellar",

    # Food service
    "cafe", "restaurant", "bar", "kitchen", "dining",

    # Old entity type labels (replaced by entity_class + roles)
    "venue", "retailer", "club", "league",

    # Domain modules (belong in lens layer)
    "sports_facility", "wine_production", "fitness_facility",
    "food_service", "aquatic_facility", "tasting_room"
}

# Required dimension names (actual DB column names)
REQUIRED_DIMENSIONS = {
    "canonical_activities",
    "canonical_roles",
    "canonical_place_types",
    "canonical_access"
}

# Required entity classes
REQUIRED_ENTITY_CLASSES = {
    "place", "person", "organization", "event", "thing"
}

# Required universal modules
REQUIRED_UNIVERSAL_MODULES = {
    "core", "location", "contact", "hours", "amenities", "time_range"
}

# Required universal amenities (ONLY these allowed)
REQUIRED_UNIVERSAL_AMENITIES = {
    "wifi", "parking_available", "disabled_access"
}


def load_entity_model():
    """Load entity_model.yaml configuration."""
    config_path = Path(__file__).parent.parent.parent.parent / "engine" / "config" / "entity_model.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestEntityModelPurity:
    """Test entity_model.yaml is vertical-agnostic."""

    def test_file_exists(self):
        """entity_model.yaml must exist."""
        config_path = Path(__file__).parent.parent.parent.parent / "engine" / "config" / "entity_model.yaml"
        assert config_path.exists(), "entity_model.yaml not found"

    def test_no_forbidden_keywords(self):
        """Entity model must not contain vertical-specific keywords."""
        config_path = Path(__file__).parent.parent.parent.parent / "engine" / "config" / "entity_model.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read().lower()

        found_forbidden = []
        for keyword in FORBIDDEN_VERTICAL_KEYWORDS:
            # Skip matches in comments explaining what NOT to do
            # Allow in negative examples like "NO sports_facility"
            lines_with_keyword = [
                line for line in content.split('\n')
                if keyword in line.lower()
            ]

            # Filter out comments and forbidden lists
            violations = [
                line for line in lines_with_keyword
                if not (
                    line.strip().startswith('#') or
                    'forbidden' in line.lower() or
                    'no ' in line.lower() or
                    'not ' in line.lower() or
                    'removed' in line.lower() or
                    'belong in lens' in line.lower() or
                    'examples:' in line.lower() or
                    'example:' in line.lower() or
                    line.strip() == 'fields:' or  # YAML structure key, not domain concept
                    line.strip().endswith('fields:')  # YAML structure key indented
                )
            ]

            if violations:
                found_forbidden.append((keyword, violations))

        assert not found_forbidden, (
            f"Found forbidden vertical-specific keywords:\n" +
            "\n".join(f"  - {kw}: {lines}" for kw, lines in found_forbidden)
        )

    def test_entity_classes_defined(self):
        """All required entity classes must be defined."""
        config = load_entity_model()
        assert 'entity_classes' in config, "entity_classes section missing"

        defined_classes = set(config['entity_classes'].keys())
        assert defined_classes == REQUIRED_ENTITY_CLASSES, (
            f"Entity classes mismatch. Expected: {REQUIRED_ENTITY_CLASSES}, "
            f"Got: {defined_classes}"
        )

    def test_dimensions_use_db_column_names(self):
        """Dimensions must use actual DB column names (canonical_*)."""
        config = load_entity_model()
        assert 'dimensions' in config, "dimensions section missing"

        defined_dimensions = set(config['dimensions'].keys())
        assert defined_dimensions == REQUIRED_DIMENSIONS, (
            f"Dimensions must use actual DB column names. "
            f"Expected: {REQUIRED_DIMENSIONS}, Got: {defined_dimensions}"
        )

    def test_dimensions_marked_as_opaque(self):
        """Dimensions must be explicitly marked as opaque."""
        config = load_entity_model()
        dimensions = config.get('dimensions', {})

        for dim_name, dim_config in dimensions.items():
            # Check for opaque keyword in description or notes
            description = dim_config.get('description', '').lower()
            notes = str(dim_config.get('notes', [])).lower()

            assert 'opaque' in description or 'opaque' in notes, (
                f"Dimension '{dim_name}' must be explicitly marked as opaque"
            )

    def test_dimensions_are_postgres_arrays(self):
        """Dimensions must be stored as Postgres text[] arrays."""
        config = load_entity_model()
        dimensions = config.get('dimensions', {})

        for dim_name, dim_config in dimensions.items():
            storage_type = dim_config.get('storage_type', '')
            assert storage_type == 'text[]', (
                f"Dimension '{dim_name}' must use storage_type: 'text[]', "
                f"got: '{storage_type}'"
            )

    def test_dimensions_have_gin_indexes(self):
        """Dimensions must be GIN indexed."""
        config = load_entity_model()
        dimensions = config.get('dimensions', {})

        for dim_name, dim_config in dimensions.items():
            indexed = dim_config.get('indexed', '')
            assert indexed == 'GIN', (
                f"Dimension '{dim_name}' must be GIN indexed, got: '{indexed}'"
            )

    def test_universal_modules_only(self):
        """Only universal modules must be defined."""
        config = load_entity_model()
        assert 'modules' in config, "modules section missing"

        defined_modules = set(config['modules'].keys())
        assert defined_modules == REQUIRED_UNIVERSAL_MODULES, (
            f"Only universal modules allowed. "
            f"Expected: {REQUIRED_UNIVERSAL_MODULES}, Got: {defined_modules}"
        )

    def test_amenities_module_universal_only(self):
        """Amenities module must contain ONLY universal amenities."""
        config = load_entity_model()
        amenities = config.get('modules', {}).get('amenities', {})
        fields = amenities.get('fields', [])

        field_names = {field['name'] for field in fields}

        # Must have exactly the universal amenities
        assert field_names == REQUIRED_UNIVERSAL_AMENITIES, (
            f"Amenities must contain ONLY universal amenities. "
            f"Expected: {REQUIRED_UNIVERSAL_AMENITIES}, Got: {field_names}"
        )

        # Check notes mention NO food service
        notes = amenities.get('notes', [])
        notes_text = ' '.join(notes).lower()
        assert 'no food service' in notes_text or 'no cafe' in notes_text, (
            "Amenities notes must explicitly state NO food service amenities"
        )

    def test_no_domain_modules(self):
        """Domain modules must not be defined in entity model."""
        config = load_entity_model()
        modules = config.get('modules', {})

        # These domain modules must NOT appear
        forbidden_modules = {
            'sports_facility', 'wine_production', 'fitness_facility',
            'food_service', 'aquatic_facility', 'tasting_room'
        }

        defined_modules = set(modules.keys())
        violations = defined_modules & forbidden_modules

        assert not violations, (
            f"Domain modules must not be in entity model. "
            f"Found: {violations}. These belong in lens layer."
        )

    def test_entity_classes_have_required_modules(self):
        """Each entity class must specify required_modules."""
        config = load_entity_model()
        entity_classes = config.get('entity_classes', {})

        for class_name, class_config in entity_classes.items():
            assert 'required_modules' in class_config, (
                f"Entity class '{class_name}' missing required_modules"
            )

            required = class_config['required_modules']
            assert isinstance(required, list), (
                f"required_modules for '{class_name}' must be a list"
            )

            # All required modules must be universal modules
            for module in required:
                assert module in REQUIRED_UNIVERSAL_MODULES, (
                    f"Entity class '{class_name}' requires '{module}', "
                    f"but it's not a universal module"
                )

    def test_core_module_always_required(self):
        """Core module must be required by all entity classes."""
        config = load_entity_model()
        entity_classes = config.get('entity_classes', {})

        for class_name, class_config in entity_classes.items():
            required = class_config.get('required_modules', [])
            assert 'core' in required, (
                f"Entity class '{class_name}' must require 'core' module"
            )


class TestEntityModelStructure:
    """Test entity_model.yaml structure and completeness."""

    def test_has_all_required_sections(self):
        """Entity model must have all required sections."""
        config = load_entity_model()

        required_sections = {'entity_classes', 'dimensions', 'modules'}
        assert all(section in config for section in required_sections), (
            f"Missing required sections. Expected: {required_sections}"
        )

    def test_dimensions_have_descriptions(self):
        """All dimensions must have descriptions."""
        config = load_entity_model()
        dimensions = config.get('dimensions', {})

        for dim_name, dim_config in dimensions.items():
            assert 'description' in dim_config, (
                f"Dimension '{dim_name}' missing description"
            )
            assert dim_config['description'].strip(), (
                f"Dimension '{dim_name}' has empty description"
            )

    def test_modules_have_descriptions(self):
        """All modules must have descriptions."""
        config = load_entity_model()
        modules = config.get('modules', {})

        for module_name, module_config in modules.items():
            assert 'description' in module_config, (
                f"Module '{module_name}' missing description"
            )
            assert module_config['description'].strip(), (
                f"Module '{module_name}' has empty description"
            )

    def test_module_fields_well_formed(self):
        """Module fields must be well-formed."""
        config = load_entity_model()
        modules = config.get('modules', {})

        for module_name, module_config in modules.items():
            assert 'fields' in module_config, (
                f"Module '{module_name}' missing fields"
            )

            fields = module_config['fields']
            assert isinstance(fields, list), (
                f"Module '{module_name}' fields must be a list"
            )

            for field in fields:
                assert 'name' in field, (
                    f"Field in module '{module_name}' missing 'name'"
                )
                assert 'type' in field, (
                    f"Field '{field.get('name')}' in module '{module_name}' missing 'type'"
                )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
