"""
Tests for TypeScript Generator

Tests TypeScript interface and Zod schema generation from YAML schemas.
Part of Phase 8 of the YAML Schema track.
"""

import pytest
from engine.schema.parser import SchemaDefinition, FieldDefinition
from engine.schema.generators.typescript import TypeScriptGenerator


class TestTypeMapping:
    """Test YAML to TypeScript type mapping."""

    def test_string_type(self):
        """Test string type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="string",
            nullable=False,
            required=True,
            description="Test field"
        )
        assert generator._map_type(field) == "string"

    def test_nullable_string_type(self):
        """Test nullable string type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="string",
            nullable=True,
            required=False,
            description="Test field"
        )
        assert generator._map_type(field) == "string | null"

    def test_integer_type(self):
        """Test integer type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="integer",
            nullable=False,
            required=True,
            description="Test field"
        )
        assert generator._map_type(field) == "number"

    def test_float_type(self):
        """Test float type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="float",
            nullable=False,
            required=True,
            description="Test field"
        )
        assert generator._map_type(field) == "number"

    def test_boolean_type(self):
        """Test boolean type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="boolean",
            nullable=False,
            required=True,
            description="Test field"
        )
        assert generator._map_type(field) == "boolean"

    def test_datetime_type(self):
        """Test datetime type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="datetime",
            nullable=False,
            required=True,
            description="Test field"
        )
        assert generator._map_type(field) == "Date"

    def test_json_type(self):
        """Test JSON type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="json",
            nullable=False,
            required=True,
            description="Test field"
        )
        assert generator._map_type(field) == "Record<string, any>"

    def test_list_string_type(self):
        """Test list[string] type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="list[string]",
            nullable=False,
            required=True,
            description="Test field"
        )
        assert generator._map_type(field) == "string[]"

    def test_list_integer_type(self):
        """Test list[integer] type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="list[integer]",
            nullable=False,
            required=True,
            description="Test field"
        )
        assert generator._map_type(field) == "number[]"

    def test_nullable_list_type(self):
        """Test nullable list type mapping."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="list[string]",
            nullable=True,
            required=False,
            description="Test field"
        )
        assert generator._map_type(field) == "string[] | null"

    def test_unsupported_type(self):
        """Test that unsupported types raise ValueError."""
        generator = TypeScriptGenerator()
        field = FieldDefinition(
            name="test_field",
            type="unsupported_type",
            nullable=False,
            required=True,
            description="Test field"
        )
        with pytest.raises(ValueError, match="Unsupported type"):
            generator._map_type(field)


class TestInterfaceGeneration:
    """Test TypeScript interface generation."""

    def test_simple_interface(self):
        """Test generation of simple interface with basic fields."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Unique identifier"
                ),
                FieldDefinition(
                    name="name",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Entity name"
                ),
            ]
        )

        interface = generator.generate_interface(schema)

        assert "export interface TestEntity {" in interface
        assert "  /** Unique identifier */" in interface
        assert "  id: string;" in interface
        assert "  /** Entity name */" in interface
        assert "  name: string;" in interface
        assert "}" in interface

    def test_interface_with_nullable_fields(self):
        """Test interface generation with nullable fields."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Unique identifier"
                ),
                FieldDefinition(
                    name="optional_field",
                    type="string",
                    nullable=True,
                    required=False,
                    description="Optional field"
                ),
            ]
        )

        interface = generator.generate_interface(schema)

        assert "  id: string;" in interface
        assert "  optional_field: string | null;" in interface

    def test_interface_with_various_types(self):
        """Test interface generation with various field types."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="name",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Name"
                ),
                FieldDefinition(
                    name="count",
                    type="integer",
                    nullable=False,
                    required=True,
                    description="Count"
                ),
                FieldDefinition(
                    name="rating",
                    type="float",
                    nullable=False,
                    required=True,
                    description="Rating"
                ),
                FieldDefinition(
                    name="active",
                    type="boolean",
                    nullable=False,
                    required=True,
                    description="Active status"
                ),
                FieldDefinition(
                    name="tags",
                    type="list[string]",
                    nullable=False,
                    required=True,
                    description="Tags"
                ),
            ]
        )

        interface = generator.generate_interface(schema)

        assert "  name: string;" in interface
        assert "  count: number;" in interface
        assert "  rating: number;" in interface
        assert "  active: boolean;" in interface
        assert "  tags: string[];" in interface

    def test_interface_with_inheritance(self):
        """Test interface generation with inheritance."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="Venue",
            description="Venue entity",
            extends="Listing",
            fields=[
                FieldDefinition(
                    name="capacity",
                    type="integer",
                    nullable=True,
                    required=False,
                    description="Venue capacity"
                ),
            ]
        )

        interface = generator.generate_interface(schema)

        assert "export interface Venue extends Listing {" in interface
        assert "  capacity: number | null;" in interface


class TestZodSchemaGeneration:
    """Test Zod schema generation for runtime validation."""

    def test_simple_zod_schema(self):
        """Test generation of simple Zod schema."""
        generator = TypeScriptGenerator(include_zod=True)
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Unique identifier"
                ),
                FieldDefinition(
                    name="name",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Entity name"
                ),
            ]
        )

        zod_schema = generator.generate_zod_schema(schema)

        assert "export const TestEntitySchema = z.object({" in zod_schema
        assert "  id: z.string()," in zod_schema
        assert "  name: z.string()," in zod_schema
        assert "});" in zod_schema

    def test_zod_schema_with_nullable_fields(self):
        """Test Zod schema with nullable fields."""
        generator = TypeScriptGenerator(include_zod=True)
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Unique identifier"
                ),
                FieldDefinition(
                    name="optional_field",
                    type="string",
                    nullable=True,
                    required=False,
                    description="Optional field"
                ),
            ]
        )

        zod_schema = generator.generate_zod_schema(schema)

        assert "  id: z.string()," in zod_schema
        assert "  optional_field: z.string().nullable()," in zod_schema

    def test_zod_schema_with_various_types(self):
        """Test Zod schema with various field types."""
        generator = TypeScriptGenerator(include_zod=True)
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="name",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Name"
                ),
                FieldDefinition(
                    name="count",
                    type="integer",
                    nullable=False,
                    required=True,
                    description="Count"
                ),
                FieldDefinition(
                    name="rating",
                    type="float",
                    nullable=False,
                    required=True,
                    description="Rating"
                ),
                FieldDefinition(
                    name="active",
                    type="boolean",
                    nullable=False,
                    required=True,
                    description="Active status"
                ),
                FieldDefinition(
                    name="tags",
                    type="list[string]",
                    nullable=False,
                    required=True,
                    description="Tags"
                ),
            ]
        )

        zod_schema = generator.generate_zod_schema(schema)

        assert "  name: z.string()," in zod_schema
        assert "  count: z.number().int()," in zod_schema
        assert "  rating: z.number()," in zod_schema
        assert "  active: z.boolean()," in zod_schema
        assert "  tags: z.array(z.string())," in zod_schema

    def test_zod_schema_with_date(self):
        """Test Zod schema with datetime field."""
        generator = TypeScriptGenerator(include_zod=True)
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="created_at",
                    type="datetime",
                    nullable=False,
                    required=True,
                    description="Creation timestamp"
                ),
            ]
        )

        zod_schema = generator.generate_zod_schema(schema)

        assert "  created_at: z.date()," in zod_schema


class TestCompleteFileGeneration:
    """Test complete TypeScript file generation."""

    def test_generate_complete_file(self):
        """Test generation of complete TypeScript file."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="Listing",
            description="Base listing entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Unique identifier"
                ),
                FieldDefinition(
                    name="name",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Listing name"
                ),
            ]
        )

        file_content = generator.generate_file(schema)

        # Check header
        assert "// GENERATED FILE - DO NOT EDIT" in file_content
        assert "// This file is auto-generated from" in file_content
        assert "// Generated on:" in file_content

        # Check interface
        assert "export interface Listing {" in file_content
        assert "  id: string;" in file_content
        assert "  name: string;" in file_content

    def test_generate_file_with_zod(self):
        """Test generation of file with Zod schemas."""
        generator = TypeScriptGenerator(include_zod=True)
        schema = SchemaDefinition(
            name="Listing",
            description="Base listing entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Unique identifier"
                ),
            ]
        )

        file_content = generator.generate_file(schema)

        # Check Zod import
        assert 'import { z } from "zod";' in file_content

        # Check interface and schema
        assert "export interface Listing {" in file_content
        assert "export const ListingSchema = z.object({" in file_content

    def test_generate_file_for_child_entity(self):
        """Test generation of file for entity with inheritance."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="Venue",
            description="Venue entity",
            extends="Listing",
            fields=[
                FieldDefinition(
                    name="capacity",
                    type="integer",
                    nullable=True,
                    required=False,
                    description="Venue capacity"
                ),
            ]
        )

        file_content = generator.generate_file(schema)

        # Check import of base interface
        assert 'import { Listing } from "./listing";' in file_content

        # Check interface extends
        assert "export interface Venue extends Listing {" in file_content


class TestTypeScriptGeneratorOptions:
    """Test TypeScript generator configuration options."""

    def test_include_zod_option(self):
        """Test include_zod option controls Zod generation."""
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Unique identifier"
                ),
            ]
        )

        # Without Zod
        generator_no_zod = TypeScriptGenerator(include_zod=False)
        file_no_zod = generator_no_zod.generate_file(schema)
        assert "import { z } from" not in file_no_zod
        assert "Schema = z.object" not in file_no_zod

        # With Zod
        generator_with_zod = TypeScriptGenerator(include_zod=True)
        file_with_zod = generator_with_zod.generate_file(schema)
        assert "import { z } from" in file_with_zod
        assert "Schema = z.object" in file_with_zod

    def test_output_format_option(self):
        """Test that output is properly formatted."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Unique identifier"
                ),
            ]
        )

        file_content = generator.generate_file(schema)

        # Check proper indentation (2 spaces)
        lines = file_content.split("\n")
        interface_lines = [l for l in lines if "id: string;" in l]
        assert len(interface_lines) > 0
        # Fields should be indented with 2 spaces
        assert interface_lines[0].startswith("  ")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_schema(self):
        """Test handling of schema with no fields."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="EmptyEntity",
            description="Empty entity",
            extends=None,
            fields=[]
        )

        interface = generator.generate_interface(schema)

        assert "export interface EmptyEntity {" in interface
        assert "}" in interface

    def test_schema_with_special_characters_in_description(self):
        """Test handling of special characters in field descriptions."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="field",
                    type="string",
                    nullable=False,
                    required=True,
                    description='Field with "quotes" and /* comment */'
                ),
            ]
        )

        interface = generator.generate_interface(schema)

        # Should handle special characters in comments
        assert "field: string;" in interface

    def test_snake_case_to_camel_case_conversion(self):
        """Test that snake_case field names are preserved (TypeScript supports them)."""
        generator = TypeScriptGenerator()
        schema = SchemaDefinition(
            name="TestEntity",
            description="Test entity",
            extends=None,
            fields=[
                FieldDefinition(
                    name="snake_case_field",
                    type="string",
                    nullable=False,
                    required=True,
                    description="Snake case field"
                ),
            ]
        )

        interface = generator.generate_interface(schema)

        # TypeScript supports snake_case, so keep as-is
        assert "  snake_case_field: string;" in interface
