"""
Tests for Prisma Schema Generator

Tests the generation of schema.prisma files from YAML schemas.
Following TDD approach for Phase 3 of YAML Schema track.
"""

import unittest
from pathlib import Path
from engine.schema.parser import SchemaParser, FieldDefinition, SchemaDefinition
from engine.schema.generators.prisma import PrismaGenerator


class TestTypeMapping(unittest.TestCase):
    """Test YAML type to Prisma type mapping."""

    def setUp(self):
        self.generator = PrismaGenerator(database="sqlite")

    def test_string_type_required(self):
        """string type with nullable=False -> String"""
        field = FieldDefinition(
            name="test_field",
            type="string",
            description="Test",
            nullable=False,
            required=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "String")

    def test_string_type_nullable(self):
        """string type with nullable=True -> String?"""
        field = FieldDefinition(
            name="test_field",
            type="string",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "String?")

    def test_integer_type_required(self):
        """integer type with nullable=False -> Int"""
        field = FieldDefinition(
            name="test_field",
            type="integer",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Int")

    def test_integer_type_nullable(self):
        """integer type with nullable=True -> Int?"""
        field = FieldDefinition(
            name="test_field",
            type="integer",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Int?")

    def test_float_type_required(self):
        """float type with nullable=False -> Float"""
        field = FieldDefinition(
            name="test_field",
            type="float",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Float")

    def test_float_type_nullable(self):
        """float type with nullable=True -> Float?"""
        field = FieldDefinition(
            name="test_field",
            type="float",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Float?")

    def test_boolean_type_required(self):
        """boolean type with nullable=False -> Boolean"""
        field = FieldDefinition(
            name="test_field",
            type="boolean",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Boolean")

    def test_boolean_type_nullable(self):
        """boolean type with nullable=True -> Boolean?"""
        field = FieldDefinition(
            name="test_field",
            type="boolean",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "Boolean?")

    def test_datetime_type_required(self):
        """datetime type with nullable=False -> DateTime"""
        field = FieldDefinition(
            name="test_field",
            type="datetime",
            description="Test",
            nullable=False
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "DateTime")

    def test_datetime_type_nullable(self):
        """datetime type with nullable=True -> DateTime?"""
        field = FieldDefinition(
            name="test_field",
            type="datetime",
            description="Test",
            nullable=True
        )
        result = self.generator._map_type(field)
        self.assertEqual(result, "DateTime?")

    def test_json_type_sqlite(self):
        """json type in SQLite -> String"""
        generator = PrismaGenerator(database="sqlite")
        field = FieldDefinition(
            name="test_field",
            type="json",
            description="Test",
            nullable=True
        )
        result = generator._map_type(field)
        self.assertEqual(result, "String?")

    def test_json_type_postgresql(self):
        """json type in PostgreSQL -> Json"""
        generator = PrismaGenerator(database="postgresql")
        field = FieldDefinition(
            name="test_field",
            type="json",
            description="Test",
            nullable=True
        )
        result = generator._map_type(field)
        self.assertEqual(result, "Json?")

    def test_list_type_not_supported(self):
        """list types should raise error (handled by prisma override)"""
        field = FieldDefinition(
            name="test_field",
            type="list[string]",
            description="Test",
            nullable=True
        )
        with self.assertRaises(ValueError):
            self.generator._map_type(field)

    def test_unsupported_type(self):
        """Unsupported type should raise ValueError"""
        field = FieldDefinition(
            name="test_field",
            type="unsupported_type",
            description="Test",
            nullable=False
        )
        with self.assertRaises(ValueError):
            self.generator._map_type(field)


class TestFieldAttributes(unittest.TestCase):
    """Test field attribute generation (@id, @unique, @default, etc.)."""

    def setUp(self):
        self.generator = PrismaGenerator(database="sqlite")

    def test_primary_key_attribute(self):
        """Primary key field should have @id @default(cuid())"""
        field = FieldDefinition(
            name="id",
            type="string",
            description="Primary key",
            nullable=False,
            primary_key=True,
            default="cuid()"
        )
        field.prisma = {"attributes": ["@id", "@default(cuid())"]}
        attributes = self.generator._generate_field_attributes(field)
        self.assertIn("@id", attributes)
        self.assertIn("@default(cuid())", attributes)

    def test_unique_attribute(self):
        """Unique field should have @unique"""
        field = FieldDefinition(
            name="slug",
            type="string",
            description="Unique slug",
            nullable=False,
            unique=True
        )
        attributes = self.generator._generate_field_attributes(field)
        self.assertIn("@unique", attributes)

    def test_default_now_attribute(self):
        """DateTime with default='now()' should have @default(now())"""
        field = FieldDefinition(
            name="createdAt",
            type="datetime",
            description="Creation timestamp",
            nullable=False,
            default="now()"
        )
        attributes = self.generator._generate_field_attributes(field)
        self.assertIn("@default(now())", attributes)

    def test_updated_at_attribute(self):
        """Field named updatedAt should have @updatedAt"""
        field = FieldDefinition(
            name="updatedAt",
            type="datetime",
            description="Update timestamp",
            nullable=False
        )
        attributes = self.generator._generate_field_attributes(field)
        self.assertIn("@updatedAt", attributes)

    def test_no_attributes(self):
        """Regular field should have no special attributes"""
        field = FieldDefinition(
            name="name",
            type="string",
            description="Name",
            nullable=False
        )
        attributes = self.generator._generate_field_attributes(field)
        self.assertEqual(attributes, [])


class TestFieldGeneration(unittest.TestCase):
    """Test individual Prisma field generation."""

    def setUp(self):
        self.generator = PrismaGenerator(database="sqlite")

    def test_simple_field(self):
        """Generate simple field line"""
        field = FieldDefinition(
            name="entity_name",
            type="string",
            description="Name of entity",
            nullable=False,
            required=True
        )
        result = self.generator._generate_field(field)
        expected = "  entity_name  String"
        self.assertEqual(result, expected)

    def test_nullable_field(self):
        """Generate nullable field line"""
        field = FieldDefinition(
            name="summary",
            type="string",
            description="Summary",
            nullable=True
        )
        result = self.generator._generate_field(field)
        expected = "  summary      String?"
        self.assertEqual(result, expected)

    def test_field_with_attributes(self):
        """Generate field with attributes"""
        field = FieldDefinition(
            name="id",
            type="string",
            description="Primary key",
            nullable=False,
            primary_key=True,
            default="cuid()"
        )
        field.prisma = {"attributes": ["@id", "@default(cuid())"]}
        result = self.generator._generate_field(field)
        expected = "  id           String     @id @default(cuid())"
        self.assertEqual(result, expected)

    def test_field_with_prisma_override(self):
        """Field with prisma.name override should use that name"""
        field = FieldDefinition(
            name="listing_id",
            type="string",
            description="Primary key",
            nullable=False,
            primary_key=True
        )
        field.prisma = {"name": "id", "attributes": ["@id", "@default(cuid())"]}
        result = self.generator._generate_field(field)
        self.assertIn("id", result)
        self.assertNotIn("listing_id", result)

    def test_field_with_prisma_skip(self):
        """Field with prisma.skip should return None"""
        field = FieldDefinition(
            name="categories",
            type="list[string]",
            description="Categories",
            nullable=True
        )
        field.prisma = {"skip": True}
        result = self.generator._generate_field(field)
        self.assertIsNone(result)

    def test_field_with_prisma_type_override(self):
        """Field with prisma.type override should use that type"""
        field = FieldDefinition(
            name="categories",
            type="list[string]",
            description="Categories",
            nullable=True
        )
        field.prisma = {"type": "Category[]"}
        result = self.generator._generate_field(field)
        self.assertIn("Category[]", result)


class TestModelGeneration(unittest.TestCase):
    """Test Prisma model generation."""

    def setUp(self):
        self.generator = PrismaGenerator(database="sqlite")

    def test_simple_model(self):
        """Generate simple model definition"""
        schema = SchemaDefinition(
            name="TestModel",
            description="Test model",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    description="ID",
                    nullable=False,
                    primary_key=True,
                    default="cuid()"
                ),
                FieldDefinition(
                    name="name",
                    type="string",
                    description="Name",
                    nullable=False
                ),
            ]
        )
        schema.fields[0].prisma = {"attributes": ["@id", "@default(cuid())"]}

        result = self.generator._generate_model(schema)

        # Check model declaration
        self.assertIn("model TestModel {", result)

        # Check fields are present
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertIn("String", result)

    def test_model_with_indexes(self):
        """Generate model with @@index directives"""
        schema = SchemaDefinition(
            name="TestModel",
            description="Test",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    description="ID",
                    nullable=False,
                    primary_key=True
                ),
                FieldDefinition(
                    name="indexed_field",
                    type="string",
                    description="Indexed",
                    nullable=False,
                    index=True
                ),
            ]
        )

        result = self.generator._generate_model(schema)
        self.assertIn("@@index([indexed_field])", result)


class TestCompleteSchemaGeneration(unittest.TestCase):
    """Test complete schema.prisma file generation."""

    def setUp(self):
        self.generator = PrismaGenerator(database="sqlite")

    def test_schema_header(self):
        """Generate schema header with generator and datasource"""
        schemas = []
        result = self.generator.generate_schema(schemas)

        # Check for generator block
        self.assertIn("generator client {", result)
        self.assertIn("provider", result)

        # Check for datasource block
        self.assertIn("datasource db {", result)
        self.assertIn("provider = \"sqlite\"", result)

    def test_generated_file_warning(self):
        """Schema should have DO NOT EDIT warning"""
        schemas = []
        result = self.generator.generate_schema(schemas)
        self.assertIn("GENERATED FILE - DO NOT EDIT", result)

    def test_multiple_models(self):
        """Generate schema with multiple models"""
        schema1 = SchemaDefinition(
            name="Model1",
            description="First model",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    description="ID",
                    nullable=False,
                    primary_key=True
                )
            ]
        )

        schema2 = SchemaDefinition(
            name="Model2",
            description="Second model",
            extends=None,
            fields=[
                FieldDefinition(
                    name="id",
                    type="string",
                    description="ID",
                    nullable=False,
                    primary_key=True
                )
            ]
        )

        result = self.generator.generate_schema([schema1, schema2])

        self.assertIn("model Model1 {", result)
        self.assertIn("model Model2 {", result)


class TestDatabaseSpecificHandling(unittest.TestCase):
    """Test database-specific type handling (SQLite vs PostgreSQL)."""

    def test_sqlite_json_as_string(self):
        """SQLite should use String for JSON fields"""
        generator = PrismaGenerator(database="sqlite")
        field = FieldDefinition(
            name="data",
            type="json",
            description="JSON data",
            nullable=True
        )
        prisma_type = generator._map_type(field)
        self.assertEqual(prisma_type, "String?")

    def test_postgresql_json_native(self):
        """PostgreSQL should use Json for JSON fields"""
        generator = PrismaGenerator(database="postgresql")
        field = FieldDefinition(
            name="data",
            type="json",
            description="JSON data",
            nullable=True
        )
        prisma_type = generator._map_type(field)
        self.assertEqual(prisma_type, "Json?")

    def test_sqlite_datasource(self):
        """SQLite generator should output sqlite datasource"""
        generator = PrismaGenerator(database="sqlite")
        result = generator.generate_schema([])
        self.assertIn("provider = \"sqlite\"", result)

    def test_postgresql_datasource(self):
        """PostgreSQL generator should output postgresql datasource"""
        generator = PrismaGenerator(database="postgresql")
        result = generator.generate_schema([])
        self.assertIn("provider = \"postgresql\"", result)


class TestListingYAMLIntegration(unittest.TestCase):
    """Integration tests with actual listing.yaml file."""

    def setUp(self):
        self.generator = PrismaGenerator(database="sqlite")
        self.parser = SchemaParser()

    def test_parse_and_generate_listing(self):
        """Parse listing.yaml and generate Prisma model"""
        schema_path = Path("engine/config/schemas/listing.yaml")

        if not schema_path.exists():
            self.skipTest("listing.yaml not found")

        schema = self.parser.parse(schema_path)
        result = self.generator._generate_model(schema)

        # Check essential fields are present
        self.assertIn("model Listing {", result)
        self.assertIn("entity_name", result)
        self.assertIn("summary", result)


class TestPostgreSQLMigration(unittest.TestCase):
    """Tests for PostgreSQL migration - Engine-Lens Architecture track."""

    def test_postgresql_schema_has_native_arrays(self):
        """PostgreSQL schema should use String[] for dimension fields"""
        generator = PrismaGenerator(database="postgresql")
        parser = SchemaParser()
        schema_path = Path("engine/config/schemas/listing.yaml")

        if not schema_path.exists():
            self.skipTest("listing.yaml not found")

        schema = parser.parse(schema_path)
        result = generator._generate_listing_model(schema)

        # Verify native array types for dimensions (from YAML prisma overrides)
        self.assertIn("String[]", result, "Expected String[] array type for dimension fields")
        # These specific fields should be String[] as per listing.yaml
        self.assertIn("canonical_activities", result)
        self.assertIn("canonical_roles", result)
        self.assertIn("canonical_place_types", result)
        self.assertIn("canonical_access", result)

    def test_postgresql_schema_has_native_json(self):
        """PostgreSQL schema should use Json for modules field"""
        generator = PrismaGenerator(database="postgresql")
        parser = SchemaParser()
        schema_path = Path("engine/config/schemas/listing.yaml")

        if not schema_path.exists():
            self.skipTest("listing.yaml not found")

        schema = parser.parse(schema_path)
        result = generator._generate_listing_model(schema)

        # Verify Json type for modules (from YAML prisma override)
        # The modules field should be Json? not String?
        self.assertIn("modules", result)
        # Check that modules line contains Json (not String)
        for line in result.split('\n'):
            if 'modules' in line and not line.strip().startswith('//'):
                self.assertIn("Json", line, "modules field should use Json type in PostgreSQL")
                self.assertNotIn("String?", line, "modules should not be String? in PostgreSQL")
                break

    def test_postgresql_full_schema_generation(self):
        """Full schema generation should produce PostgreSQL-compatible schema"""
        generator = PrismaGenerator(database="postgresql")
        parser = SchemaParser()

        # Load listing schema
        schema_path = Path("engine/config/schemas/listing.yaml")
        if not schema_path.exists():
            self.skipTest("listing.yaml not found")

        schemas = [parser.parse(schema_path)]
        result = generator.generate_full_schema(schemas, target="engine")

        # Verify PostgreSQL datasource
        self.assertIn('provider = "postgresql"', result)
        # Verify no SQLite limitation comments
        self.assertNotIn("TEMPORARY SQLite LIMITATION", result)
        self.assertNotIn('provider = "sqlite"', result)


if __name__ == "__main__":
    unittest.main()
