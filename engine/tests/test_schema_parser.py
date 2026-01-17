"""
Tests for YAML schema parser.

This module tests the parsing and validation of YAML schema files
into internal SchemaDefinition and FieldDefinition objects.
"""

import pytest
from pathlib import Path
from engine.schema.parser import (
    SchemaParser,
    SchemaDefinition,
    FieldDefinition,
    SchemaValidationError,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def schemas_dir(tmp_path):
    """Create a temporary schemas directory for testing."""
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    return schema_dir


@pytest.fixture
def valid_base_yaml(schemas_dir):
    """Create a valid base.yaml for testing."""
    content = """
schema:
  name: Listing
  description: Base schema for all entity types
  extends: null

fields:
  - name: listing_id
    type: string
    description: Unique identifier
    nullable: false
    required: false
    primary_key: true
    exclude: true
    default: cuid()

  - name: entity_name
    type: string
    description: Official name of the entity
    nullable: false
    required: true
    index: true
    search:
      category: identity
      keywords:
        - name
        - called

  - name: categories
    type: list[string]
    description: Raw free-form categories
    nullable: true
    search:
      category: categories
      keywords:
        - categories
        - type
"""
    file_path = schemas_dir / "base.yaml"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def inherited_yaml(schemas_dir):
    """Create a schema that extends base."""
    content = """
schema:
  name: Venue
  description: Venue-specific schema
  extends: base

fields:
  - name: listing_id
    type: string
    description: Foreign key to parent Listing
    nullable: false
    foreign_key: listings.listing_id
    primary_key: true
    exclude: true

  - name: tennis
    type: boolean
    description: Whether tennis is available
    nullable: true
    search:
      category: racquet_sports
      keywords:
        - tennis
        - courts
"""
    file_path = schemas_dir / "venue.yaml"
    file_path.write_text(content)
    return file_path


# ============================================================
# PARSER INITIALIZATION TESTS
# ============================================================

def test_parser_initialization():
    """Test that parser can be initialized."""
    parser = SchemaParser()
    assert parser is not None


# ============================================================
# BASIC PARSING TESTS
# ============================================================

def test_parse_valid_yaml(valid_base_yaml):
    """Test parsing a valid YAML schema file."""
    parser = SchemaParser()
    schema_def = parser.parse(valid_base_yaml)

    assert isinstance(schema_def, SchemaDefinition)
    assert schema_def.name == "Listing"
    assert schema_def.description == "Base schema for all entity types"
    assert schema_def.extends is None


def test_parse_yaml_with_fields(valid_base_yaml):
    """Test that fields are parsed correctly."""
    parser = SchemaParser()
    schema_def = parser.parse(valid_base_yaml)

    assert len(schema_def.fields) == 3
    assert all(isinstance(f, FieldDefinition) for f in schema_def.fields)


def test_parse_field_attributes(valid_base_yaml):
    """Test that field attributes are parsed correctly."""
    parser = SchemaParser()
    schema_def = parser.parse(valid_base_yaml)

    # Check first field (listing_id)
    listing_id = schema_def.fields[0]
    assert listing_id.name == "listing_id"
    assert listing_id.type == "string"
    assert listing_id.description == "Unique identifier"
    assert listing_id.nullable is False
    assert listing_id.required is False
    assert listing_id.primary_key is True
    assert listing_id.exclude is True
    assert listing_id.default == "cuid()"


def test_parse_field_search_metadata(valid_base_yaml):
    """Test that search metadata is parsed correctly."""
    parser = SchemaParser()
    schema_def = parser.parse(valid_base_yaml)

    # Check second field (entity_name)
    entity_name = schema_def.fields[1]
    assert entity_name.search_category == "identity"
    assert entity_name.search_keywords == ["name", "called"]


def test_parse_list_type(valid_base_yaml):
    """Test that list types are parsed correctly."""
    parser = SchemaParser()
    schema_def = parser.parse(valid_base_yaml)

    # Check third field (categories)
    categories = schema_def.fields[2]
    assert categories.type == "list[string]"
    assert categories.nullable is True


def test_parse_inherited_schema(inherited_yaml):
    """Test parsing a schema that extends another."""
    parser = SchemaParser()
    schema_def = parser.parse(inherited_yaml)

    assert schema_def.name == "Venue"
    assert schema_def.extends == "base"
    assert len(schema_def.fields) == 2


# ============================================================
# VALIDATION TESTS
# ============================================================

def test_validate_missing_schema_section(schemas_dir):
    """Test that missing schema section raises error."""
    content = """
fields:
  - name: test
    type: string
"""
    file_path = schemas_dir / "invalid.yaml"
    file_path.write_text(content)

    parser = SchemaParser()
    with pytest.raises(SchemaValidationError, match="Missing required 'schema' section"):
        parser.parse(file_path)


def test_validate_missing_schema_name(schemas_dir):
    """Test that missing schema name raises error."""
    content = """
schema:
  description: Test schema

fields:
  - name: test
    type: string
"""
    file_path = schemas_dir / "invalid.yaml"
    file_path.write_text(content)

    parser = SchemaParser()
    with pytest.raises(SchemaValidationError, match="Missing required field 'name'"):
        parser.parse(file_path)


def test_validate_missing_fields_section(schemas_dir):
    """Test that missing fields section raises error."""
    content = """
schema:
  name: Test
  description: Test schema
"""
    file_path = schemas_dir / "invalid.yaml"
    file_path.write_text(content)

    parser = SchemaParser()
    with pytest.raises(SchemaValidationError, match="Missing required 'fields' section"):
        parser.parse(file_path)


def test_validate_empty_fields(schemas_dir):
    """Test that empty fields list raises error."""
    content = """
schema:
  name: Test
  description: Test schema

fields: []
"""
    file_path = schemas_dir / "invalid.yaml"
    file_path.write_text(content)

    parser = SchemaParser()
    with pytest.raises(SchemaValidationError, match="fields' section cannot be empty"):
        parser.parse(file_path)


def test_validate_field_missing_name(schemas_dir):
    """Test that field without name raises error."""
    content = """
schema:
  name: Test
  description: Test schema

fields:
  - type: string
    description: Field without name
"""
    file_path = schemas_dir / "invalid.yaml"
    file_path.write_text(content)

    parser = SchemaParser()
    with pytest.raises(SchemaValidationError, match="Field missing required attribute 'name'"):
        parser.parse(file_path)


def test_validate_field_missing_type(schemas_dir):
    """Test that field without type raises error."""
    content = """
schema:
  name: Test
  description: Test schema

fields:
  - name: test_field
    description: Field without type
"""
    file_path = schemas_dir / "invalid.yaml"
    file_path.write_text(content)

    parser = SchemaParser()
    with pytest.raises(SchemaValidationError, match="Field 'test_field' missing required attribute 'type'"):
        parser.parse(file_path)


def test_validate_invalid_field_type(schemas_dir):
    """Test that invalid field type raises error."""
    content = """
schema:
  name: Test
  description: Test schema

fields:
  - name: test_field
    type: invalid_type
    description: Field with invalid type
"""
    file_path = schemas_dir / "invalid.yaml"
    file_path.write_text(content)

    parser = SchemaParser()
    with pytest.raises(SchemaValidationError, match="Invalid type 'invalid_type'"):
        parser.parse(file_path)


def test_validate_supported_types(schemas_dir):
    """Test that all supported types are valid."""
    supported_types = [
        "string", "integer", "float", "boolean", "datetime", "json",
        "list[string]", "list[integer]"
    ]

    for field_type in supported_types:
        content = f"""
schema:
  name: Test
  description: Test schema

fields:
  - name: test_field
    type: {field_type}
    description: Test field
"""
        file_path = schemas_dir / "test.yaml"
        file_path.write_text(content)

        parser = SchemaParser()
        schema_def = parser.parse(file_path)
        assert schema_def.fields[0].type == field_type


# ============================================================
# MALFORMED YAML TESTS
# ============================================================

def test_parse_invalid_yaml_syntax(schemas_dir):
    """Test that invalid YAML syntax raises error."""
    content = """
schema:
  name: Test
  description: [unclosed bracket
"""
    file_path = schemas_dir / "invalid.yaml"
    file_path.write_text(content)

    parser = SchemaParser()
    with pytest.raises(SchemaValidationError, match="Failed to parse YAML"):
        parser.parse(file_path)


def test_parse_empty_file(schemas_dir):
    """Test that empty file raises error."""
    file_path = schemas_dir / "empty.yaml"
    file_path.write_text("")

    parser = SchemaParser()
    with pytest.raises(SchemaValidationError, match="Empty YAML file"):
        parser.parse(file_path)


def test_parse_non_existent_file():
    """Test that non-existent file raises error."""
    parser = SchemaParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("non_existent_file.yaml"))


# ============================================================
# DEFAULT VALUE TESTS
# ============================================================

def test_field_default_values():
    """Test that field attributes have correct default values."""
    parser = SchemaParser()

    content = """
schema:
  name: Test
  description: Test schema

fields:
  - name: minimal_field
    type: string
    description: Minimal field definition
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(content)
        f.flush()

        schema_def = parser.parse(Path(f.name))
        field = schema_def.fields[0]

        # Check default values
        assert field.nullable is True
        assert field.required is False
        assert field.index is False
        assert field.unique is False
        assert field.exclude is False
        assert field.primary_key is False
        assert field.foreign_key is None
        assert field.search_category is None
        assert field.search_keywords is None
        assert field.default is None
