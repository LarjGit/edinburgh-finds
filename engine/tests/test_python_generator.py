"""
Tests for Python FieldSpec Generator

Tests the generation of Python listing.py files from YAML schemas.
Following TDD approach for Phase 2 of YAML Schema track.
"""

import unittest
from pathlib import Path
from engine.schema.parser import SchemaParser, FieldDefinition, SchemaDefinition
from engine.schema.generators.python_fieldspec import PythonFieldSpecGenerator


class TestTypeMapping(unittest.TestCase):
    """Test YAML type to Python type annotation mapping."""

    def setUp(self):
        self.generator = PythonFieldSpecGenerator()

    def test_string_type_required(self):
        """string type with required=True -> str"""
        field = FieldDefinition(
            name="test_field",
            type="string",
            description="Test",
            nullable=False,
            required=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "str")

    def test_string_type_nullable(self):
        """string type with nullable=True -> Optional[str]"""
        field = FieldDefinition(
            name="test_field",
            type="string",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Optional[str]")

    def test_integer_type_required(self):
        """integer type with nullable=False -> int"""
        field = FieldDefinition(
            name="test_field",
            type="integer",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "int")

    def test_integer_type_nullable(self):
        """integer type with nullable=True -> Optional[int]"""
        field = FieldDefinition(
            name="test_field",
            type="integer",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Optional[int]")

    def test_float_type_required(self):
        """float type with nullable=False -> float"""
        field = FieldDefinition(
            name="test_field",
            type="float",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "float")

    def test_float_type_nullable(self):
        """float type with nullable=True -> Optional[float]"""
        field = FieldDefinition(
            name="test_field",
            type="float",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Optional[float]")

    def test_boolean_type_required(self):
        """boolean type with nullable=False -> bool"""
        field = FieldDefinition(
            name="test_field",
            type="boolean",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "bool")

    def test_boolean_type_nullable(self):
        """boolean type with nullable=True -> Optional[bool]"""
        field = FieldDefinition(
            name="test_field",
            type="boolean",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Optional[bool]")

    def test_json_type_required(self):
        """json type with nullable=False -> Dict[str, Any]"""
        field = FieldDefinition(
            name="test_field",
            type="json",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Dict[str, Any]")

    def test_json_type_nullable(self):
        """json type with nullable=True -> Optional[Dict[str, Any]]"""
        field = FieldDefinition(
            name="test_field",
            type="json",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Optional[Dict[str, Any]]")

    def test_list_string_type_required(self):
        """list[string] type with nullable=False -> List[str]"""
        field = FieldDefinition(
            name="test_field",
            type="list[string]",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "List[str]")

    def test_list_string_type_nullable(self):
        """list[string] type with nullable=True -> Optional[List[str]]"""
        field = FieldDefinition(
            name="test_field",
            type="list[string]",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Optional[List[str]]")

    def test_datetime_type_required(self):
        """datetime type with nullable=False -> datetime"""
        field = FieldDefinition(
            name="test_field",
            type="datetime",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "datetime")

    def test_datetime_type_nullable(self):
        """datetime type with nullable=True -> Optional[datetime]"""
        field = FieldDefinition(
            name="test_field",
            type="datetime",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Optional[datetime]")

    def test_unsupported_type(self):
        """Unsupported type should raise ValueError"""
        field = FieldDefinition(
            name="test_field",
            type="unsupported_type",
            description="Test"
        )
        with self.assertRaises(ValueError):
            self.generator._map_type(field)


class TestImportGeneration(unittest.TestCase):
    """Test import statement generation."""

    def setUp(self):
        self.generator = PythonFieldSpecGenerator()

    def test_imports_for_simple_types(self):
        """Simple types (str, int, float, bool) still need List for field list declaration"""
        fields = [
            FieldDefinition(name="name", type="string", description="Name", nullable=False),
            FieldDefinition(name="age", type="integer", description="Age", nullable=False),
        ]
        imports = self.generator._generate_imports(fields)
        # Should have basic imports, List is always included for the field list
        self.assertIn("from .core import FieldSpec", imports)
        self.assertIn("List", imports)  # Always needed for List[FieldSpec]
        self.assertNotIn("Optional", imports)
        self.assertNotIn("Dict", imports)

    def test_imports_for_optional_types(self):
        """Optional types need Optional import"""
        fields = [
            FieldDefinition(name="name", type="string", description="Name", nullable=True),
        ]
        imports = self.generator._generate_imports(fields)
        self.assertIn("Optional", imports)

    def test_imports_for_list_types(self):
        """List types need List import"""
        fields = [
            FieldDefinition(name="tags", type="list[string]", description="Tags", nullable=False),
        ]
        imports = self.generator._generate_imports(fields)
        self.assertIn("List", imports)

    def test_imports_for_json_types(self):
        """JSON types need Dict and Any imports"""
        fields = [
            FieldDefinition(name="meta", type="json", description="Metadata", nullable=False),
        ]
        imports = self.generator._generate_imports(fields)
        self.assertIn("Dict", imports)
        self.assertIn("Any", imports)

    def test_imports_for_datetime_types(self):
        """datetime types need datetime import"""
        fields = [
            FieldDefinition(name="created_at", type="datetime", description="Created", nullable=False),
        ]
        imports = self.generator._generate_imports(fields)
        self.assertIn("from datetime import datetime", imports)


class TestFileGeneration(unittest.TestCase):
    """Test complete Python file generation from schema."""

    def setUp(self):
        self.generator = PythonFieldSpecGenerator()

    def test_generate_complete_file(self):
        """Generate complete Python module from schema"""
        schema = SchemaDefinition(
            name="Listing",
            description="Base schema for all entity types",
            fields=[
                FieldDefinition(
                    name="listing_id",
                    type="string",
                    description="Unique identifier",
                    nullable=False,
                    required=False,
                    primary_key=True,
                    exclude=True,
                    default="cuid()"
                ),
                FieldDefinition(
                    name="entity_name",
                    type="string",
                    description="Name of entity",
                    nullable=False,
                    required=True,
                    index=True,
                    search_category="identity",
                    search_keywords=["name", "called"]
                ),
                FieldDefinition(
                    name="summary",
                    type="string",
                    description="Description",
                    nullable=True
                ),
            ]
        )

        result = self.generator.generate(schema)

        # Check for header comment
        self.assertIn("GENERATED FILE - DO NOT EDIT", result)
        self.assertIn("Generated from:", result)

        # Check for imports
        self.assertIn("from typing import", result)
        self.assertIn("from .core import FieldSpec", result)

        # Check for LISTING_FIELDS declaration
        self.assertIn("LISTING_FIELDS: List[FieldSpec] = [", result)

        # Check for field generation
        self.assertIn('name="listing_id"', result)
        self.assertIn('name="entity_name"', result)
        self.assertIn('name="summary"', result)

    def test_generated_file_imports_correctly(self):
        """Generated file should be valid Python that imports without errors"""
        schema = SchemaDefinition(
            name="Listing",
            description="Test schema",
            fields=[
                FieldDefinition(
                    name="test_field",
                    type="string",
                    description="Test",
                    nullable=True
                ),
            ]
        )

        result = self.generator.generate(schema)

        # Should be valid Python (no syntax errors)
        try:
            compile(result, '<generated>', 'exec')
        except SyntaxError as e:
            self.fail(f"Generated code has syntax error: {e}")

    def test_sa_column_handling(self):
        """Handle sa_column metadata from python section"""
        field = FieldDefinition(
            name="categories",
            type="list[string]",
            description="Categories",
            nullable=True,
            python={"sa_column": "Column(ARRAY(String))"}
        )

        result = self.generator._generate_fieldspec(field)
        self.assertIn('sa_column="Column(ARRAY(String))"', result)


class TestSchemaInheritance(unittest.TestCase):
    """Test schema inheritance handling."""

    def setUp(self):
        self.generator = PythonFieldSpecGenerator()

    def test_generate_child_schema(self):
        """Generate child schema that extends parent"""
        schema = SchemaDefinition(
            name="Venue",
            description="Venue-specific fields",
            extends="Listing",
            fields=[
                FieldDefinition(
                    name="tennis",
                    type="boolean",
                    description="Tennis available",
                    nullable=True
                ),
            ]
        )

        result = self.generator.generate(schema)

        # Should import from parent
        self.assertIn("from .listing import LISTING_FIELDS", result)

        # Should use VENUE_SPECIFIC_FIELDS name (not VENUE_FIELDS)
        self.assertIn("VENUE_SPECIFIC_FIELDS", result)
        self.assertNotIn("VENUE_FIELDS", result)

        # Should still have the field
        self.assertIn('name="tennis"', result)

    def test_generate_base_schema(self):
        """Generate base schema without inheritance"""
        schema = SchemaDefinition(
            name="Listing",
            description="Base schema",
            extends=None,
            fields=[
                FieldDefinition(
                    name="entity_name",
                    type="string",
                    description="Name",
                    nullable=False
                ),
            ]
        )

        result = self.generator.generate(schema)

        # Should NOT import from parent
        self.assertNotIn("from .listing import", result)

        # Should use LISTING_FIELDS name
        self.assertIn("LISTING_FIELDS", result)


class TestFieldSpecGeneration(unittest.TestCase):
    """Test FieldSpec code generation from FieldDefinition."""

    def setUp(self):
        self.generator = PythonFieldSpecGenerator()

    def test_simple_field_generation(self):
        """Generate FieldSpec for a simple required string field"""
        field = FieldDefinition(
            name="entity_name",
            type="string",
            description="Official name of the entity",
            nullable=False,
            required=True,
            index=True
        )
        result = self.generator._generate_fieldspec(field)

        # Check that it contains the key elements
        self.assertIn('FieldSpec(', result)
        self.assertIn('name="entity_name"', result)
        self.assertIn('type_annotation="str"', result)
        self.assertIn('description="Official name of the entity"', result)
        self.assertIn('nullable=False', result)
        self.assertIn('required=True', result)
        self.assertIn('index=True', result)

    def test_optional_field_generation(self):
        """Generate FieldSpec for an optional field"""
        field = FieldDefinition(
            name="summary",
            type="string",
            description="A short description",
            nullable=True,
            required=False
        )
        result = self.generator._generate_fieldspec(field)

        self.assertIn('name="summary"', result)
        self.assertIn('type_annotation="Optional[str]"', result)
        self.assertIn('nullable=True', result)

    def test_field_with_search_metadata(self):
        """Generate FieldSpec with search metadata"""
        field = FieldDefinition(
            name="entity_name",
            type="string",
            description="Name",
            search_category="identity",
            search_keywords=["name", "called", "named"]
        )
        result = self.generator._generate_fieldspec(field)

        self.assertIn('search_category="identity"', result)
        self.assertIn('search_keywords=["name", "called", "named"]', result)

    def test_field_with_primary_key(self):
        """Generate FieldSpec for primary key field"""
        field = FieldDefinition(
            name="listing_id",
            type="string",
            description="Unique identifier",
            nullable=False,
            required=False,
            primary_key=True,
            exclude=True,
            default="cuid()"
        )
        result = self.generator._generate_fieldspec(field)

        self.assertIn('primary_key=True', result)
        self.assertIn('exclude=True', result)
        self.assertIn('default="None"', result)  # Special handling for cuid()

    def test_field_with_unique_constraint(self):
        """Generate FieldSpec for unique field"""
        field = FieldDefinition(
            name="slug",
            type="string",
            description="URL-safe name",
            unique=True,
            index=True
        )
        result = self.generator._generate_fieldspec(field)

        self.assertIn('unique=True', result)
        self.assertIn('index=True', result)

    def test_list_field_generation(self):
        """Generate FieldSpec for list field"""
        field = FieldDefinition(
            name="categories",
            type="list[string]",
            description="Categories",
            nullable=True
        )
        result = self.generator._generate_fieldspec(field)

        self.assertIn('type_annotation="Optional[List[str]]"', result)

    def test_json_field_generation(self):
        """Generate FieldSpec for JSON field"""
        field = FieldDefinition(
            name="attributes",
            type="json",
            description="Structured attributes",
            nullable=True
        )
        result = self.generator._generate_fieldspec(field)

        self.assertIn('type_annotation="Optional[Dict[str, Any]]"', result)


if __name__ == "__main__":
    unittest.main()
