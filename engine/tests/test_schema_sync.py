"""
Schema Synchronization Tests (Phase 4, Task 4.3)

These tests validate that:
1. Generated Python schemas match manual versions
2. YAML is the single source of truth
3. Manual edits to generated files are detected
"""

import unittest
from pathlib import Path
from engine.schema.parser import SchemaParser
from engine.schema.generators.python_fieldspec import PythonFieldSpecGenerator
from engine.schema.listing import LISTING_FIELDS as manual_listing_fields
from engine.schema.venue import VENUE_SPECIFIC_FIELDS as manual_venue_fields


class TestSchemaSync(unittest.TestCase):
    """Test that YAML schemas match manual Python schemas"""

    def setUp(self):
        """Set up test fixtures"""
        self.schema_dir = Path(__file__).parent.parent / "config" / "schemas"
        self.parser = SchemaParser()
        self.py_generator = PythonFieldSpecGenerator()

    def test_listing_yaml_field_count_matches_manual(self):
        """Test that listing.yaml has same number of fields as manual listing.py"""
        listing_yaml = self.schema_dir / "listing.yaml"
        schema = self.parser.parse(listing_yaml)

        self.assertEqual(
            len(schema.fields),
            len(manual_listing_fields),
            f"listing.yaml has {len(schema.fields)} fields but manual listing.py has {len(manual_listing_fields)}"
        )

    def test_venue_yaml_field_count_matches_manual(self):
        """Test that venue.yaml has same number of fields as manual venue.py"""
        venue_yaml = self.schema_dir / "venue.yaml"
        schema = self.parser.parse(venue_yaml)

        self.assertEqual(
            len(schema.fields),
            len(manual_venue_fields),
            f"venue.yaml has {len(schema.fields)} fields but manual venue.py has {len(manual_venue_fields)}"
        )

    def test_listing_field_names_match(self):
        """Test that listing.yaml fields match manual listing.py field names and order"""
        listing_yaml = self.schema_dir / "listing.yaml"
        schema = self.parser.parse(listing_yaml)

        yaml_field_names = [f.name for f in schema.fields]
        manual_field_names = [f.name for f in manual_listing_fields]

        self.assertEqual(
            yaml_field_names,
            manual_field_names,
            "listing.yaml field names/order don't match manual listing.py"
        )

    def test_venue_field_names_match(self):
        """Test that venue.yaml fields match manual venue.py field names and order"""
        venue_yaml = self.schema_dir / "venue.yaml"
        schema = self.parser.parse(venue_yaml)

        yaml_field_names = [f.name for f in schema.fields]
        manual_field_names = [f.name for f in manual_venue_fields]

        self.assertEqual(
            yaml_field_names,
            manual_field_names,
            "venue.yaml field names/order don't match manual venue.py"
        )

    def test_listing_field_attributes_match(self):
        """Test that listing.yaml field attributes match manual listing.py"""
        listing_yaml = self.schema_dir / "listing.yaml"
        schema = self.parser.parse(listing_yaml)

        for yaml_field, manual_field in zip(schema.fields, manual_listing_fields):
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

    def test_venue_field_attributes_match(self):
        """Test that venue.yaml field attributes match manual venue.py"""
        venue_yaml = self.schema_dir / "venue.yaml"
        schema = self.parser.parse(venue_yaml)

        for yaml_field, manual_field in zip(schema.fields, manual_venue_fields):
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
                self.assertEqual(yaml_field.foreign_key, manual_field.foreign_key, f"Foreign key mismatch for {manual_field.name}")

                # Test search metadata
                self.assertEqual(yaml_field.search_category, manual_field.search_category, f"Search category mismatch for {manual_field.name}")
                self.assertEqual(yaml_field.search_keywords, manual_field.search_keywords, f"Search keywords mismatch for {manual_field.name}")

    def test_listing_generation_produces_valid_python(self):
        """Test that generating listing.py from YAML produces valid Python code"""
        listing_yaml = self.schema_dir / "listing.yaml"
        schema = self.parser.parse(listing_yaml)

        # Generate Python code
        generated_code = self.py_generator.generate(schema, source_file="listing.yaml")

        # Check that it's valid Python (can be compiled)
        try:
            compile(generated_code, "<generated>", "exec")
        except SyntaxError as e:
            self.fail(f"Generated listing.py has syntax errors: {e}")

        # Check for required imports
        self.assertIn("from .core import FieldSpec", generated_code)
        self.assertIn("from .types import EntityType", generated_code)
        self.assertIn("LISTING_FIELDS", generated_code)

    def test_venue_generation_produces_valid_python(self):
        """Test that generating venue.py from YAML produces valid Python code"""
        venue_yaml = self.schema_dir / "venue.yaml"
        schema = self.parser.parse(venue_yaml)

        # Generate Python code
        generated_code = self.py_generator.generate(schema, source_file="venue.yaml")

        # Check that it's valid Python (can be compiled)
        try:
            compile(generated_code, "<generated>", "exec")
        except SyntaxError as e:
            self.fail(f"Generated venue.py has syntax errors: {e}")

        # Check for required imports
        self.assertIn("from .core import FieldSpec", generated_code)
        self.assertIn("from .listing import LISTING_FIELDS", generated_code)
        self.assertIn("VENUE_SPECIFIC_FIELDS", generated_code)

    def test_yaml_is_parseable(self):
        """Test that all YAML schema files can be parsed without errors"""
        listing_yaml = self.schema_dir / "listing.yaml"
        venue_yaml = self.schema_dir / "venue.yaml"

        # Should not raise any exceptions
        listing_schema = self.parser.parse(listing_yaml)
        venue_schema = self.parser.parse(venue_yaml)

        self.assertIsNotNone(listing_schema)
        self.assertIsNotNone(venue_schema)
        self.assertEqual(listing_schema.name, "Listing")
        self.assertEqual(venue_schema.name, "Venue")
        self.assertEqual(venue_schema.extends, "Listing")


class TestSchemaIntegrity(unittest.TestCase):
    """Test schema integrity and consistency"""

    def test_no_duplicate_field_names_in_listing(self):
        """Test that listing.py has no duplicate field names"""
        field_names = [f.name for f in manual_listing_fields]
        duplicates = set([name for name in field_names if field_names.count(name) > 1])

        self.assertEqual(
            len(duplicates),
            0,
            f"Duplicate field names in listing.py: {duplicates}"
        )

    def test_no_duplicate_field_names_in_venue(self):
        """Test that venue.py has no duplicate field names"""
        field_names = [f.name for f in manual_venue_fields]
        duplicates = set([name for name in field_names if field_names.count(name) > 1])

        self.assertEqual(
            len(duplicates),
            0,
            f"Duplicate field names in venue.py: {duplicates}"
        )

    def test_required_fields_have_consistent_nullable(self):
        """Test that required=True fields have nullable=False"""
        all_fields = manual_listing_fields + manual_venue_fields

        for field in all_fields:
            if field.required:
                with self.subTest(field=field.name):
                    self.assertFalse(
                        field.nullable,
                        f"Field {field.name} is required=True but nullable=True (inconsistent)"
                    )


if __name__ == "__main__":
    unittest.main()
