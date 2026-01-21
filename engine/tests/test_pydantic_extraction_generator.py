"""
Tests for Pydantic Extraction Generator.
"""

import tempfile
import textwrap
import unittest
from pathlib import Path

from engine.schema.parser import FieldDefinition
from engine.schema.generators.pydantic_extraction import PydanticExtractionGenerator


class TestTypeMapping(unittest.TestCase):
    """Test YAML type to Pydantic type mapping."""

    def setUp(self):
        self.generator = PydanticExtractionGenerator()

    def test_string_type_is_optional(self):
        """string type -> Optional[str]"""
        field = FieldDefinition(
            name="entity_name",
            type="string",
            description="Name",
            nullable=True,
            required=False,
        )
        result = self.generator._get_type_annotation(field)
        self.assertEqual(result, "Optional[str]")

    def test_required_string_is_not_optional(self):
        """extraction_required -> str (non-optional)"""
        field = FieldDefinition(
            name="entity_name",
            type="string",
            description="Name",
            nullable=False,
            required=True,
            python={"extraction_required": True},
        )
        result = self.generator._get_type_annotation(field)
        self.assertEqual(result, "str")

    def test_list_type_is_optional(self):
        """list[string] type -> Optional[List[str]]"""
        field = FieldDefinition(
            name="categories",
            type="list[string]",
            description="Categories",
            nullable=True,
        )
        result = self.generator._get_type_annotation(field)
        self.assertEqual(result, "Optional[List[str]]")

    def test_json_type_is_optional(self):
        """json type -> Optional[Dict[str, Any]]"""
        field = FieldDefinition(
            name="attributes",
            type="json",
            description="Attributes",
            nullable=True,
        )
        result = self.generator._get_type_annotation(field)
        self.assertEqual(result, "Optional[Dict[str, Any]]")

    def test_unsupported_type_raises(self):
        """Unsupported type should raise ValueError."""
        field = FieldDefinition(
            name="unsupported",
            type="unsupported",
            description="Unsupported",
        )
        with self.assertRaises(ValueError):
            self.generator._get_type_annotation(field)


class TestFieldGeneration(unittest.TestCase):
    """Test field generation for extraction."""

    def setUp(self):
        self.generator = PydanticExtractionGenerator()

    def test_field_default_none(self):
        """Optional fields default to None in extraction model."""
        field = FieldDefinition(
            name="entity_name",
            type="string",
            description="Name",
            nullable=True,
            required=False,
        )
        result = self.generator._generate_field(field)
        self.assertIn("entity_name: Optional[str]", result)
        self.assertIn("Field(default=None", result)

    def test_required_field_no_default(self):
        """Required extraction fields omit default=None."""
        field = FieldDefinition(
            name="entity_name",
            type="string",
            description="Name",
            nullable=False,
            required=True,
            python={"extraction_required": True},
        )
        result = self.generator._generate_field(field)
        self.assertIn("entity_name: str", result)
        self.assertNotIn("default=None", result)

    def test_optional_description_mentions_null(self):
        """Optional field descriptions mention null semantics."""
        field = FieldDefinition(
            name="street_address",
            type="string",
            description="Full street address",
            nullable=True,
        )
        description = self.generator._build_description(field)
        self.assertIn("Null", description)


class TestYamlGeneration(unittest.TestCase):
    """Test YAML-driven generation with extraction overrides."""

    def setUp(self):
        self.generator = PydanticExtractionGenerator()

    def _write_yaml(self, content: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "listing.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_extraction_fields_are_included(self):
        """Extra extraction_fields are included in generated output."""
        yaml_content = textwrap.dedent(
            """
            schema:
              name: Entity
              description: Test schema

            fields:
              - name: entity_name
                type: string
                description: Entity name
                nullable: false
                required: true

            extraction_fields:
              - name: rating
                type: float
                description: Average rating
                nullable: true
            """
        ).strip()
        yaml_path = self._write_yaml(yaml_content)
        result = self.generator.generate_from_yaml(yaml_path)
        self.assertIn("rating: Optional[float]", result)

    def test_extraction_name_override(self):
        """extraction_name override renames field in output."""
        yaml_content = textwrap.dedent(
            """
            schema:
              name: Entity
              description: Test schema

            fields:
              - name: entity_name
                type: string
                description: Entity name
                nullable: false
                required: true
              - name: website_url
                type: string
                description: Official website URL
                nullable: true
                python:
                  extraction_name: website
            """
        ).strip()
        yaml_path = self._write_yaml(yaml_content)
        result = self.generator.generate_from_yaml(yaml_path)
        self.assertIn("website: Optional[str]", result)
        self.assertNotIn("website_url: Optional[str]", result)

    def test_validators_are_generated(self):
        """Fields with validators generate field_validator methods."""
        yaml_content = textwrap.dedent(
            """
            schema:
              name: Entity
              description: Test schema

            fields:
              - name: entity_name
                type: string
                description: Entity name
                nullable: false
                required: true
                python:
                  validators:
                    - non_empty
              - name: phone
                type: string
                description: Phone number
                nullable: true
                python:
                  validators:
                    - e164_phone
            """
        ).strip()
        yaml_path = self._write_yaml(yaml_content)
        result = self.generator.generate_from_yaml(yaml_path)
        self.assertIn('@field_validator("phone")', result)
        self.assertIn("validate_phone_e164_format", result)


if __name__ == "__main__":
    unittest.main()
