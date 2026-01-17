"""
YAML Schema Parser

Parses YAML schema files into internal SchemaDefinition and FieldDefinition objects.
Validates schema structure and field types.
"""

from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from typing import Optional, List, Any, Dict
import yaml


# ============================================================
# EXCEPTIONS
# ============================================================

class SchemaValidationError(Exception):
    """Raised when schema validation fails."""
    pass


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class FieldDefinition:
    """
    Represents a single field in a schema.

    This is the internal representation of a field parsed from YAML.
    Generators will transform this into Python FieldSpec, Prisma fields, etc.
    """
    name: str
    type: str
    description: str
    nullable: bool = True
    required: bool = False

    # Database constraints
    index: bool = False
    unique: bool = False
    default: Optional[str] = None

    # Special handling
    exclude: bool = False
    primary_key: bool = False
    foreign_key: Optional[str] = None

    # Search metadata
    search_category: Optional[str] = None
    search_keywords: Optional[List[str]] = None

    # Generator-specific metadata
    python: Optional[Dict[str, Any]] = None
    prisma: Optional[Dict[str, Any]] = None


@dataclass
class SchemaDefinition:
    """
    Represents a complete schema parsed from YAML.

    Contains metadata about the schema and all field definitions.
    """
    name: str
    description: str
    extends: Optional[str] = None
    fields: List[FieldDefinition] = dataclass_field(default_factory=list)


# ============================================================
# PARSER
# ============================================================

class SchemaParser:
    """
    Parses YAML schema files into SchemaDefinition objects.

    Validates structure, field types, and constraints.
    """

    # Supported field types
    SUPPORTED_TYPES = {
        "string", "integer", "float", "boolean", "datetime", "json",
        "list[string]", "list[integer]", "list[float]", "list[boolean]"
    }

    def parse(self, file_path: Path) -> SchemaDefinition:
        """
        Parse a YAML schema file.

        Args:
            file_path: Path to YAML file

        Returns:
            SchemaDefinition object

        Raises:
            FileNotFoundError: If file doesn't exist
            SchemaValidationError: If schema is invalid
        """
        # Read and parse YAML
        yaml_data = self._load_yaml(file_path)

        # Validate and extract schema metadata
        schema_meta = self._validate_schema_section(yaml_data)

        # Validate and extract fields
        fields_data = self._validate_fields_section(yaml_data)

        # Parse fields
        fields = [self._parse_field(field_data) for field_data in fields_data]

        # Create SchemaDefinition
        return SchemaDefinition(
            name=schema_meta["name"],
            description=schema_meta["description"],
            extends=schema_meta.get("extends"),
            fields=fields
        )

    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse YAML file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Schema file not found: {file_path}")

        try:
            content = file_path.read_text()
            if not content.strip():
                raise SchemaValidationError("Empty YAML file")

            yaml_data = yaml.safe_load(content)
            if yaml_data is None:
                raise SchemaValidationError("Empty YAML file")

            return yaml_data
        except yaml.YAMLError as e:
            raise SchemaValidationError(f"Failed to parse YAML: {e}")

    def _validate_schema_section(self, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the 'schema' section."""
        if "schema" not in yaml_data:
            raise SchemaValidationError("Missing required 'schema' section")

        schema_section = yaml_data["schema"]

        if "name" not in schema_section:
            raise SchemaValidationError("Missing required field 'name' in schema section")

        if "description" not in schema_section:
            raise SchemaValidationError("Missing required field 'description' in schema section")

        return schema_section

    def _validate_fields_section(self, yaml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate the 'fields' section."""
        if "fields" not in yaml_data:
            raise SchemaValidationError("Missing required 'fields' section")

        fields_section = yaml_data["fields"]

        if not isinstance(fields_section, list):
            raise SchemaValidationError("'fields' section must be a list")

        if len(fields_section) == 0:
            raise SchemaValidationError("'fields' section cannot be empty")

        return fields_section

    def _parse_field(self, field_data: Dict[str, Any]) -> FieldDefinition:
        """Parse a single field definition."""
        # Validate required attributes
        if "name" not in field_data:
            raise SchemaValidationError("Field missing required attribute 'name'")

        field_name = field_data["name"]

        if "type" not in field_data:
            raise SchemaValidationError(f"Field '{field_name}' missing required attribute 'type'")

        field_type = field_data["type"]

        # Validate type
        if field_type not in self.SUPPORTED_TYPES:
            raise SchemaValidationError(
                f"Invalid type '{field_type}' for field '{field_name}'. "
                f"Supported types: {', '.join(sorted(self.SUPPORTED_TYPES))}"
            )

        # Description is optional but recommended
        description = field_data.get("description", "")

        # Parse search metadata
        search_category = None
        search_keywords = None
        if "search" in field_data:
            search_section = field_data["search"]
            search_category = search_section.get("category")
            search_keywords = search_section.get("keywords")

        # Create FieldDefinition
        return FieldDefinition(
            name=field_name,
            type=field_type,
            description=description,
            nullable=field_data.get("nullable", True),
            required=field_data.get("required", False),
            index=field_data.get("index", False),
            unique=field_data.get("unique", False),
            default=field_data.get("default"),
            exclude=field_data.get("exclude", False),
            primary_key=field_data.get("primary_key", False),
            foreign_key=field_data.get("foreign_key"),
            search_category=search_category,
            search_keywords=search_keywords,
            python=field_data.get("python"),
            prisma=field_data.get("prisma")
        )
