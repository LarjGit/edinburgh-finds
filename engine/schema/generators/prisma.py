"""
Prisma Schema Generator

Generates schema.prisma files from YAML schemas.
Part of Phase 3 of the YAML Schema track.
"""

from typing import List, Optional
from datetime import datetime
from engine.schema.parser import SchemaDefinition, FieldDefinition


class PrismaGenerator:
    """
    Generates Prisma schema from YAML SchemaDefinition.

    Handles type mapping, field attributes, model generation, and complete schema generation.
    Supports both SQLite and PostgreSQL database providers.
    """

    # Type mapping from YAML to Prisma (base types)
    TYPE_MAP = {
        "string": "String",
        "integer": "Int",
        "float": "Float",
        "boolean": "Boolean",
        "datetime": "DateTime",
    }

    def __init__(self, database: str = "sqlite"):
        """
        Initialize Prisma generator.

        Args:
            database: Database provider ("sqlite" or "postgresql")
        """
        if database not in ["sqlite", "postgresql"]:
            raise ValueError(f"Unsupported database: {database}. Use 'sqlite' or 'postgresql'")
        self.database = database

    def _map_type(self, field: FieldDefinition) -> str:
        """
        Map YAML field type to Prisma type.

        Args:
            field: FieldDefinition from YAML

        Returns:
            Prisma type string (e.g., "String", "Int?", "Json")

        Raises:
            ValueError: If field type is not supported
        """
        # Check for Prisma-specific type override
        if hasattr(field, 'prisma') and field.prisma and 'type' in field.prisma:
            prisma_type = field.prisma['type']
            # Don't add nullable suffix if type already specified
            return prisma_type

        # Handle JSON type (database-specific)
        if field.type == "json":
            base_type = "String" if self.database == "sqlite" else "Json"
            return f"{base_type}?" if field.nullable else base_type

        # Handle list types - not directly supported, should use Prisma override
        if field.type.startswith("list["):
            raise ValueError(
                f"List type '{field.type}' not directly supported in Prisma. "
                f"Use prisma.type or prisma.skip in YAML for relations/arrays."
            )

        # Map standard types
        if field.type not in self.TYPE_MAP:
            raise ValueError(
                f"Unsupported type '{field.type}'. "
                f"Supported types: {', '.join(sorted(self.TYPE_MAP.keys()))}, json"
            )

        base_type = self.TYPE_MAP[field.type]

        # Add nullable suffix if needed
        return f"{base_type}?" if field.nullable else base_type

    def _generate_field_attributes(self, field: FieldDefinition) -> List[str]:
        """
        Generate Prisma field attributes (@id, @unique, @default, etc.).

        Args:
            field: FieldDefinition from YAML

        Returns:
            List of attribute strings
        """
        attributes = []

        # Check for Prisma-specific attributes
        if hasattr(field, 'prisma') and field.prisma and 'attributes' in field.prisma:
            return field.prisma['attributes']

        # Primary key
        if field.primary_key:
            attributes.append("@id")

        # Unique constraint
        if field.unique:
            attributes.append("@unique")

        # Default values
        if field.default:
            if field.default == "cuid()":
                attributes.append("@default(cuid())")
            elif field.default == "now()":
                attributes.append("@default(now())")
            elif field.default == "uuid()":
                attributes.append("@default(uuid())")
            else:
                # Handle other default values
                if field.type == "string":
                    attributes.append(f'@default("{field.default}")')
                else:
                    attributes.append(f"@default({field.default})")

        # Auto-update timestamp
        if field.name == "updatedAt" or field.name == "updated_at":
            attributes.append("@updatedAt")

        return attributes

    def _generate_field(self, field: FieldDefinition) -> Optional[str]:
        """
        Generate a single Prisma field line.

        Args:
            field: FieldDefinition from YAML

        Returns:
            Formatted Prisma field string, or None if field should be skipped
        """
        # Check if field should be skipped
        if hasattr(field, 'prisma') and field.prisma and field.prisma.get('skip'):
            return None

        # Get field name (may be overridden by Prisma config)
        field_name = field.name
        if hasattr(field, 'prisma') and field.prisma and 'name' in field.prisma:
            field_name = field.prisma['name']

        # Get Prisma type
        prisma_type = self._map_type(field)

        # Get attributes
        attributes = self._generate_field_attributes(field)

        # Format field line with proper spacing
        # Use dynamic column widths based on content
        field_with_indent = f"  {field_name}"

        # Align type column at position 15 (or more if field name is long)
        field_width = max(15, len(field_with_indent) + 1)
        field_part = field_with_indent.ljust(field_width)

        if attributes:
            # With attributes: field + type + attributes
            type_part = prisma_type.ljust(11)
            attr_str = " ".join(attributes)
            return f"{field_part}{type_part}{attr_str}"
        else:
            # Without attributes: field + type (but strip trailing spaces)
            return f"{field_part}{prisma_type}"

    def _generate_indexes(self, schema: SchemaDefinition) -> List[str]:
        """
        Generate @@index directives for indexed fields.

        Args:
            schema: SchemaDefinition from YAML

        Returns:
            List of @@index directive strings
        """
        indexes = []

        for field in schema.fields:
            # Skip if field should be skipped
            if hasattr(field, 'prisma') and field.prisma and field.prisma.get('skip'):
                continue

            # Skip if field is primary key or unique (automatically indexed)
            if field.primary_key or field.unique:
                continue

            # Add index if specified
            if field.index:
                field_name = field.name
                if hasattr(field, 'prisma') and field.prisma and 'name' in field.prisma:
                    field_name = field.prisma['name']
                indexes.append(f"  @@index([{field_name}])")

        return indexes

    def _generate_model(self, schema: SchemaDefinition) -> str:
        """
        Generate a complete Prisma model definition.

        Args:
            schema: SchemaDefinition from YAML

        Returns:
            Complete Prisma model as string
        """
        lines = []

        # Model declaration
        lines.append(f"model {schema.name} {{")

        # Generate fields
        for field in schema.fields:
            field_line = self._generate_field(field)
            if field_line:
                lines.append(field_line)

        # Add blank line before indexes
        indexes = self._generate_indexes(schema)
        if indexes:
            lines.append("")
            lines.extend(indexes)

        # Close model
        lines.append("}")

        return "\n".join(lines)

    def generate_schema(self, schemas: List[SchemaDefinition]) -> str:
        """
        Generate complete schema.prisma file from list of schemas.

        Args:
            schemas: List of SchemaDefinition objects

        Returns:
            Complete Prisma schema file as string
        """
        lines = []

        # Header comment
        lines.append("// ============================================================")
        lines.append("// GENERATED FILE - DO NOT EDIT")
        lines.append("// ============================================================")
        lines.append("// This file is automatically generated from YAML schemas.")
        lines.append("// Source: engine/config/schemas/*.yaml")
        lines.append(f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("//")
        lines.append("// To modify the schema:")
        lines.append("// 1. Edit the YAML files in engine/config/schemas/")
        lines.append("// 2. Run: python -m engine.schema.generate")
        lines.append("// 3. Run: prisma migrate dev")
        lines.append("// ============================================================")
        lines.append("")

        # Generator block
        lines.append("generator client {")
        lines.append('  provider = "prisma-client-py"')
        lines.append('  interface = "asyncio"')
        lines.append("}")
        lines.append("")

        # Datasource block
        lines.append("datasource db {")
        lines.append(f'  provider = "{self.database}"')

        # Database-specific URL
        if self.database == "sqlite":
            lines.append('  url      = "file:../web/dev.db"')
        else:  # postgresql
            lines.append('  url      = env("DATABASE_URL")')

        lines.append("}")
        lines.append("")

        # Database-specific notes
        if self.database == "sqlite":
            lines.append("// TODO: When migrating to Supabase (PostgreSQL), replace entityType String with native enum:")
            lines.append("//   enum EntityType { VENUE, RETAILER, COACH, INSTRUCTOR, CLUB, LEAGUE, EVENT, TOURNAMENT }")
            lines.append("//")
            lines.append("// TEMPORARY SQLite LIMITATION: SQLite doesn't support native Prisma enums.")
            lines.append("// EntityType is currently stored as String but validated as Enum in application code.")
            lines.append("// Valid values: VENUE, RETAILER, COACH, INSTRUCTOR, CLUB, LEAGUE, EVENT, TOURNAMENT")
            lines.append("")

        # Generate models
        for i, schema in enumerate(schemas):
            if i > 0:
                lines.append("")  # Blank line between models
            lines.append(self._generate_model(schema))

        return "\n".join(lines) + "\n"

    def generate_to_file(self, schemas: List[SchemaDefinition], output_path: str) -> None:
        """
        Generate schema.prisma file and write to disk.

        Args:
            schemas: List of SchemaDefinition objects
            output_path: Path to write schema.prisma file
        """
        schema_content = self.generate_schema(schemas)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(schema_content)
