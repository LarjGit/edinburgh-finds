"""
Python FieldSpec Generator

Generates Python listing.py files with FieldSpec definitions from YAML schemas.
Part of Phase 2 of the YAML Schema track.
"""

from typing import List, Set
from engine.schema.parser import SchemaDefinition, FieldDefinition


class PythonFieldSpecGenerator:
    """
    Generates Python FieldSpec code from YAML SchemaDefinition.

    Handles type mapping, import generation, and complete file generation.
    """

    # Type mapping from YAML to Python
    TYPE_MAP = {
        "string": "str",
        "integer": "int",
        "float": "float",
        "boolean": "bool",
        "datetime": "datetime",
        "json": "Dict[str, Any]",
        "list[string]": "List[str]",
        "list[integer]": "List[int]",
        "list[float]": "List[float]",
        "list[boolean]": "List[bool]",
    }

    def _map_type(self, field: FieldDefinition) -> str:
        """
        Map YAML field type to Python type annotation.

        Args:
            field: FieldDefinition from YAML

        Returns:
            Python type annotation string (e.g., "str", "Optional[int]")

        Raises:
            ValueError: If field type is not supported
        """
        # Check for explicit type_annotation override in python metadata
        if field.python and "type_annotation" in field.python:
            base_type = field.python["type_annotation"]
        else:
            if field.type not in self.TYPE_MAP:
                raise ValueError(
                    f"Unsupported type '{field.type}'. "
                    f"Supported types: {', '.join(sorted(self.TYPE_MAP.keys()))}"
                )
            base_type = self.TYPE_MAP[field.type]

        # Wrap in Optional if nullable
        if field.nullable:
            return f"Optional[{base_type}]"

        return base_type

    def _generate_imports(self, fields: List[FieldDefinition]) -> str:
        """
        Generate import statements based on field types.

        Args:
            fields: List of FieldDefinition objects

        Returns:
            Import statements as a string
        """
        # Always include core imports
        imports = set()
        imports.add("from .core import FieldSpec")

        # Track which typing imports we need
        typing_imports = set()
        needs_datetime = False
        needs_entity_type = False

        # Always need List for the LISTING_FIELDS/VENUE_SPECIFIC_FIELDS declaration
        typing_imports.add("List")

        for field in fields:
            # Check if we need Optional
            if field.nullable:
                typing_imports.add("Optional")

            # Check for List types in field definitions
            if field.type.startswith("list["):
                typing_imports.add("List")

            # Check for Dict/Any (json type)
            if field.type == "json":
                typing_imports.add("Dict")
                typing_imports.add("Any")

            # Check for datetime
            if field.type == "datetime":
                needs_datetime = True

            # Check for custom type annotations
            if field.python and "type_annotation" in field.python:
                type_annotation = field.python["type_annotation"]
                if "EntityType" in type_annotation:
                    needs_entity_type = True

        # Build import lines
        import_lines = []

        # Add typing imports if needed
        if typing_imports:
            typing_list = ", ".join(sorted(typing_imports))
            import_lines.append(f"from typing import {typing_list}")

        # Add datetime import if needed
        if needs_datetime:
            import_lines.append("from datetime import datetime")

        # Add core import
        import_lines.append("from .core import FieldSpec")

        # Add EntityType import if needed
        if needs_entity_type:
            import_lines.append("from .types import EntityType")

        return "\n".join(import_lines)

    def _generate_fieldspec(self, field: FieldDefinition) -> str:
        """
        Generate FieldSpec constructor code for a single field.

        Args:
            field: FieldDefinition from YAML

        Returns:
            FieldSpec constructor call as a string
        """
        # Get type annotation
        type_annotation = self._map_type(field)

        # Start building FieldSpec parameters
        params = []
        params.append(f'name="{field.name}"')
        params.append(f'type_annotation="{type_annotation}"')
        params.append(f'description="{field.description}"')
        params.append(f'nullable={field.nullable}')
        params.append(f'required={field.required}')

        # Add optional parameters only if they differ from defaults
        if field.index:
            params.append('index=True')

        if field.unique:
            params.append('unique=True')

        if field.primary_key:
            params.append('primary_key=True')

        if field.foreign_key:
            params.append(f'foreign_key="{field.foreign_key}"')

        if field.exclude:
            params.append('exclude=True')

        # Handle default value
        # Check for python-specific default override first
        if field.python and "default" in field.python:
            params.append(f'default="{field.python["default"]}"')
        # Special case: cuid() in YAML becomes "None" in Python
        elif field.default is not None:
            if field.default == "cuid()":
                params.append('default="None"')
            elif field.default == "null":
                params.append('default="None"')
            else:
                params.append(f'default="{field.default}"')

        # Add search metadata
        if field.search_category:
            params.append(f'search_category="{field.search_category}"')

        if field.search_keywords:
            keywords_str = '["' + '", "'.join(field.search_keywords) + '"]'
            params.append(f'search_keywords={keywords_str}')

        # Handle sa_column from python metadata
        if field.python and "sa_column" in field.python:
            sa_column = field.python["sa_column"]
            params.append(f'sa_column="{sa_column}"')

        # Build the FieldSpec call with proper indentation
        fieldspec = "    FieldSpec(\n"
        for param in params:
            fieldspec += f"        {param},\n"
        fieldspec += "    )"

        return fieldspec

    def generate(self, schema: SchemaDefinition, source_file: str = "listing.yaml") -> str:
        """
        Generate complete Python module with FieldSpec definitions.

        Args:
            schema: SchemaDefinition parsed from YAML
            source_file: Name of the source YAML file

        Returns:
            Complete Python module as a string
        """
        from datetime import datetime

        lines = []

        # Generate header comment
        lines.append("# " + "=" * 60)
        lines.append("# GENERATED FILE - DO NOT EDIT")
        lines.append("# " + "=" * 60)
        lines.append("#")
        lines.append(f"# Generated from: engine/config/schemas/{source_file}")
        lines.append(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("#")
        lines.append("# To make changes:")
        lines.append(f"# 1. Edit engine/config/schemas/{source_file}")
        lines.append("# 2. Run: python -m engine.schema.generate")
        lines.append("#")
        lines.append("# " + "=" * 60)
        lines.append("")

        # Generate imports
        imports = self._generate_imports(schema.fields)
        lines.append(imports)

        # If schema extends another, import parent fields
        if schema.extends:
            parent_module = schema.extends.lower()
            parent_fields = f"{schema.extends.upper()}_FIELDS"
            lines.append(f"from .{parent_module} import {parent_fields}")

        lines.append("")

        # Generate schema description comment
        lines.append("# " + "=" * 60)
        if schema.extends:
            lines.append(f"# {schema.name.upper()}-SPECIFIC FIELDS")
        else:
            lines.append(f"# {schema.name.upper()} FIELDS")
        lines.append("# " + "=" * 60)
        lines.append("#")
        lines.append(f"# {schema.description}")
        if schema.extends:
            lines.append(f"# Extends: {schema.extends}")
        lines.append("#")
        lines.append("# " + "=" * 60)
        lines.append("")

        # Generate field list declaration
        # Child schemas use {SCHEMA}_SPECIFIC_FIELDS, base schemas use {SCHEMA}_FIELDS
        if schema.extends:
            field_list_name = f"{schema.name.upper()}_SPECIFIC_FIELDS"
        else:
            field_list_name = f"{schema.name.upper()}_FIELDS"

        lines.append(f"{field_list_name}: List[FieldSpec] = [")

        # Generate each FieldSpec
        for i, field in enumerate(schema.fields):
            fieldspec = self._generate_fieldspec(field)
            if i < len(schema.fields) - 1:
                # Add comma for all but last field
                lines.append(fieldspec + ",")
            else:
                # No comma for last field
                lines.append(fieldspec)

        # Close the list
        lines.append("]")
        lines.append("")

        # Determine the field list name to use in helper functions
        if schema.extends:
            parent_fields = f"{schema.extends.upper()}_FIELDS"
            combined_fields = f"{schema.name.upper()}_FIELDS"

            # Add combined fields list for inherited schemas
            lines.append(f"{combined_fields}: List[FieldSpec] = {parent_fields} + {field_list_name}")
            lines.append("")
            lines.append("")

            fields_var = combined_fields
        else:
            # For base schemas, use the field list directly
            fields_var = field_list_name

        # Add helper functions for all schemas (base and inherited)
        lines.append("def get_field_by_name(name: str) -> Optional[FieldSpec]:")
        lines.append("    \"\"\"Get field spec by name.\"\"\"")
        lines.append(f"    for field_spec in {fields_var}:")
        lines.append("        if field_spec.name == name:")
        lines.append("            return field_spec")
        lines.append("    return None")
        lines.append("")
        lines.append("")
        lines.append("def get_fields_with_search_metadata() -> List[FieldSpec]:")
        lines.append(f"    \"\"\"Get all {schema.name} fields that have search metadata.\"\"\"")
        lines.append(f"    return [f for f in {fields_var} if f.search_category is not None]")
        lines.append("")
        lines.append("")
        lines.append("def get_extraction_fields() -> List[FieldSpec]:")
        lines.append(f"    \"\"\"Get all {schema.name} fields for LLM extraction (excludes internal fields).\"\"\"")
        lines.append(f"    return [f for f in {fields_var} if not f.exclude]")
        lines.append("")
        lines.append("")
        lines.append("def get_database_fields() -> List[FieldSpec]:")
        lines.append(f"    \"\"\"Get all {schema.name} fields for database (includes internal/excluded fields).\"\"\"")
        lines.append(f"    return {fields_var}")
        lines.append("")

        return "\n".join(lines)
