"""
Schema Synchronization Tests (Phase 4, Task 4.3)

These tests validate that:
1. Generated Python schemas match manual versions
2. YAML is the single source of truth
3. Manual edits to generated files are detected

NOTE: venue.py has been removed as part of Engine-Lens architecture.
Only universal ENTITY_FIELDS remain in the engine layer.
"""

import unittest
from pathlib import Path
from engine.schema.parser import SchemaParser
from engine.schema.generators.python_fieldspec import PythonFieldSpecGenerator
from engine.schema.entity import ENTITY_FIELDS as manual_entity_fields


class TestSchemaSync(unittest.TestCase):
    """Test that YAML schemas match manual Python schemas"""

    def setUp(self):
        """Set up test fixtures"""
        self.schema_dir = Path(__file__).parent.parent / "config" / "schemas"
        self.parser = SchemaParser()
        self.py_generator = PythonFieldSpecGenerator()

    def test_entity_yaml_field_count_matches_manual(self):
        """Test that entity.yaml has same number of fields as manual entity.py"""
        entity_yaml = self.schema_dir / "entity.yaml"
        schema = self.parser.parse(entity_yaml)

        self.assertEqual(
            len(schema.fields),
            len(manual_entity_fields),
            f"entity.yaml has {len(schema.fields)} fields but manual entity.py has {len(manual_entity_fields)}"
        )


    def test_listing_field_names_match(self):
        """Test that entity.yaml fields match manual entity.py field names and order"""
        entity_yaml = self.schema_dir / "entity.yaml"
        schema = self.parser.parse(entity_yaml)

        yaml_field_names = [f.name for f in schema.fields]
        manual_field_names = [f.name for f in manual_entity_fields]

        self.assertEqual(
            yaml_field_names,
            manual_field_names,
            "entity.yaml field names/order don't match manual entity.py"
        )


    def test_listing_field_attributes_match(self):
        """Test that entity.yaml field attributes match manual entity.py"""
        entity_yaml = self.schema_dir / "entity.yaml"
        schema = self.parser.parse(entity_yaml)

        for yaml_field, manual_field in zip(schema.fields, manual_entity_fields):
            with self.subTest(field=manual_field.name):
                # Test basic attributes
                self.assertEqual(yaml_field.name, manual_field.name, f"Field name mismatch")
                self.assertEqual(yaml_field.description, manual_field.description, f"Description mismatch for {manual_field.name}")
                self.assertEqual(yaml_field.nullable, manual_field.nullable, f"Nullable mismatch for {manual_field.name}")
                self.assertEqual(yaml_field.required, manual_field.required, f"Required mismatch for {manual_field.name}")

                # Test database constraints
                self.assertEqual(yaml_field.index, manual_field.index, f"Index mismatch for {manual_field.name}")
                self.assertEqual(yaml_field.unique, manual_field.unique, f"Unique mismatch for {manual_field.name}")
                self.assertEqual(yaml_field.primary_key, manual_field.primary_key, f"Primary key mismatch for {manual_field.name}")
                self.assertEqual(yaml_field.exclude, manual_field.exclude, f"Exclude mismatch for {manual_field.name}")

                # Test search metadata
                self.assertEqual(yaml_field.search_category, manual_field.search_category, f"Search category mismatch for {manual_field.name}")
                self.assertEqual(yaml_field.search_keywords, manual_field.search_keywords, f"Search keywords mismatch for {manual_field.name}")


    def test_listing_generation_produces_valid_python(self):
        """Test that generating entity.py from YAML produces valid Python code"""
        entity_yaml = self.schema_dir / "entity.yaml"
        schema = self.parser.parse(entity_yaml)

        # Generate Python code
        generated_code = self.py_generator.generate(schema, source_file="entity.yaml")

        # Check that it's valid Python (can be compiled)
        try:
            compile(generated_code, "<generated>", "exec")
        except SyntaxError as e:
            self.fail(f"Generated entity.py has syntax errors: {e}")

        # Check for required imports
        self.assertIn("from .core import FieldSpec", generated_code)
        self.assertIn("from .types import EntityType", generated_code)
        self.assertIn("ENTITY_FIELDS", generated_code)


    def test_yaml_is_parseable(self):
        """Test that YAML schema files can be parsed without errors"""
        entity_yaml = self.schema_dir / "entity.yaml"

        # Should not raise any exceptions
        listing_schema = self.parser.parse(entity_yaml)

        self.assertIsNotNone(listing_schema)
        self.assertEqual(listing_schema.name, "Entity")


class TestSchemaIntegrity(unittest.TestCase):
    """Test schema integrity and consistency"""

    def test_no_duplicate_field_names_in_listing(self):
        """Test that entity.py has no duplicate field names"""
        field_names = [f.name for f in manual_entity_fields]
        duplicates = set([name for name in field_names if field_names.count(name) > 1])

        self.assertEqual(
            len(duplicates),
            0,
            f"Duplicate field names in entity.py: {duplicates}"
        )


    def test_required_fields_have_consistent_nullable(self):
        """Test that required=True fields have nullable=False"""
        all_fields = manual_entity_fields

        for field in all_fields:
            if field.required:
                with self.subTest(field=field.name):
                    self.assertFalse(
                        field.nullable,
                        f"Field {field.name} is required=True but nullable=True (inconsistent)"
                    )


if __name__ == "__main__":
    unittest.main()
