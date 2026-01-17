"""
TypeScript Generator

Generates TypeScript interfaces and Zod schemas from YAML schemas.
Part of Phase 8 of the YAML Schema track.
"""

from typing import List
from datetime import datetime
from engine.schema.parser import SchemaDefinition, FieldDefinition


class TypeScriptGenerator:
    """
    Generates TypeScript interfaces and Zod schemas from YAML SchemaDefinition.

    Handles type mapping, interface generation, and optional Zod schema generation
    for runtime validation.
    """

    # Type mapping from YAML to TypeScript
    TYPE_MAP = {
        "string": "string",
        "integer": "number",
        "float": "number",
        "boolean": "boolean",
        "datetime": "Date",
        "json": "Record<string, any>",
        "list[string]": "string[]",
        "list[integer]": "number[]",
        "list[float]": "number[]",
        "list[boolean]": "boolean[]",
    }

    # Type mapping from YAML to Zod validators
    ZOD_MAP = {
        "string": "z.string()",
        "integer": "z.number().int()",
        "float": "z.number()",
        "boolean": "z.boolean()",
        "datetime": "z.date()",
        "json": "z.record(z.string(), z.any())",
        "list[string]": "z.array(z.string())",
        "list[integer]": "z.array(z.number().int())",
        "list[float]": "z.array(z.number())",
        "list[boolean]": "z.array(z.boolean())",
    }

    def __init__(self, include_zod: bool = False):
        """
        Initialize TypeScript generator.

        Args:
            include_zod: Whether to generate Zod schemas for runtime validation
        """
        self.include_zod = include_zod

    def _map_type(self, field: FieldDefinition) -> str:
        """
        Map YAML field type to TypeScript type.

        Args:
            field: FieldDefinition from YAML

        Returns:
            TypeScript type string (e.g., "string", "number | null")

        Raises:
            ValueError: If field type is not supported
        """
        if field.type not in self.TYPE_MAP:
            raise ValueError(
                f"Unsupported type '{field.type}'. "
                f"Supported types: {', '.join(sorted(self.TYPE_MAP.keys()))}"
            )

        base_type = self.TYPE_MAP[field.type]

        # Add null union if nullable
        if field.nullable:
            return f"{base_type} | null"

        return base_type

    def _map_zod_type(self, field: FieldDefinition) -> str:
        """
        Map YAML field type to Zod validator.

        Args:
            field: FieldDefinition from YAML

        Returns:
            Zod validator string (e.g., "z.string()", "z.number().nullable()")

        Raises:
            ValueError: If field type is not supported
        """
        if field.type not in self.ZOD_MAP:
            raise ValueError(
                f"Unsupported type '{field.type}' for Zod schema. "
                f"Supported types: {', '.join(sorted(self.ZOD_MAP.keys()))}"
            )

        base_validator = self.ZOD_MAP[field.type]

        # Add nullable modifier if nullable
        if field.nullable:
            return f"{base_validator}.nullable()"

        return base_validator

    def generate_interface(self, schema: SchemaDefinition) -> str:
        """
        Generate TypeScript interface from SchemaDefinition.

        Args:
            schema: SchemaDefinition from YAML

        Returns:
            TypeScript interface as string
        """
        lines = []

        # Interface declaration with optional extends
        if schema.extends:
            lines.append(f"export interface {schema.name} extends {schema.extends} {{")
        else:
            lines.append(f"export interface {schema.name} {{")

        # Generate fields
        for field in schema.fields:
            # Add JSDoc comment with description
            if field.description:
                # Escape special characters in description
                safe_description = field.description.replace("*/", "*\\/")
                lines.append(f"  /** {safe_description} */")

            # Generate field with type
            ts_type = self._map_type(field)
            lines.append(f"  {field.name}: {ts_type};")

        # Close interface
        lines.append("}")

        return "\n".join(lines)

    def generate_zod_schema(self, schema: SchemaDefinition) -> str:
        """
        Generate Zod schema from SchemaDefinition.

        Args:
            schema: SchemaDefinition from YAML

        Returns:
            Zod schema as string
        """
        lines = []

        # Schema declaration
        lines.append(f"export const {schema.name}Schema = z.object({{")

        # Generate fields
        for field in schema.fields:
            zod_validator = self._map_zod_type(field)
            lines.append(f"  {field.name}: {zod_validator},")

        # Close schema
        lines.append("});")

        return "\n".join(lines)

    def _generate_header(self, schema: SchemaDefinition) -> str:
        """
        Generate file header with warning and metadata.

        Args:
            schema: SchemaDefinition from YAML

        Returns:
            Header comment as string
        """
        yaml_file = f"engine/config/schemas/{schema.name.lower()}.yaml"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header = f"""// GENERATED FILE - DO NOT EDIT
// This file is auto-generated from YAML schema definitions.
// Any manual changes will be overwritten on next generation.
//
// Source: {yaml_file}
// Generated on: {timestamp}
"""
        return header

    def _generate_imports(self, schema: SchemaDefinition) -> str:
        """
        Generate import statements.

        Args:
            schema: SchemaDefinition from YAML

        Returns:
            Import statements as string
        """
        imports = []

        # Import Zod if needed
        if self.include_zod:
            imports.append('import { z } from "zod";')

        # Import base interface if extends is specified
        if schema.extends:
            base_name_lower = schema.extends.lower()
            imports.append(f'import {{ {schema.extends} }} from "./{base_name_lower}";')

        # Add blank line after imports if any exist
        if imports:
            imports.append("")

        return "\n".join(imports)

    def generate_file(self, schema: SchemaDefinition) -> str:
        """
        Generate complete TypeScript file with interface and optional Zod schema.

        Args:
            schema: SchemaDefinition from YAML

        Returns:
            Complete TypeScript file content as string
        """
        parts = []

        # Add header
        parts.append(self._generate_header(schema))
        parts.append("")

        # Add imports
        imports = self._generate_imports(schema)
        if imports:
            parts.append(imports)

        # Add interface
        parts.append(self.generate_interface(schema))

        # Add Zod schema if requested
        if self.include_zod:
            parts.append("")
            parts.append(self.generate_zod_schema(schema))

        # Join all parts with proper spacing
        return "\n".join(parts) + "\n"
