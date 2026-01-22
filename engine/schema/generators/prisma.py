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

    ENGINE_GENERATOR_BLOCK = [
        "generator client {",
        '  provider = "prisma-client-py"',
        '  interface = "asyncio"',
        "}",
    ]

    WEB_GENERATOR_BLOCK = [
        "generator client {",
        '  provider = "prisma-client-js"',
        "}",
    ]

    INFRA_MODELS_BEFORE_ENTITY = ""

    INFRA_MODELS_AFTER_ENTITY = """model EntityRelationship {
  id             String  @id @default(cuid())
  sourceEntityId String
  targetEntityId String
  type           String  // e.g., "teaches_at", "plays_at", "part_of"
  confidence     Float?  // Optional confidence score (0.0 - 1.0)
  source         String  // Which connector/source discovered this relationship

  sourceEntity Entity @relation("SourceEntity", fields: [sourceEntityId], references: [id], onDelete: Cascade)
  targetEntity Entity @relation("TargetEntity", fields: [targetEntityId], references: [id], onDelete: Cascade)

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@index([sourceEntityId])
  @@index([targetEntityId])
  @@index([type])
}

model ExtractedEntity {
  id                    String   @id @default(cuid())
  raw_ingestion_id      String
  source                String
  entity_class          String
  attributes            String?
  discovered_attributes String?
  external_ids          String?
  extraction_hash       String?
  model_used            String?

  raw_ingestion RawIngestion @relation(fields: [raw_ingestion_id], references: [id], onDelete: Cascade)

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@index([raw_ingestion_id])
  @@index([source])
  @@index([entity_class])
  @@index([extraction_hash])
  @@index([source, entity_class])
  @@index([createdAt])
}

model FailedExtraction {
  id               String   @id @default(cuid())
  raw_ingestion_id String
  source           String
  error_message    String
  error_details    String?
  retry_count      Int      @default(0)
  last_attempt_at  DateTime?

  raw_ingestion RawIngestion @relation(fields: [raw_ingestion_id], references: [id], onDelete: Cascade)

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@index([raw_ingestion_id])
  @@index([source])
  @@index([retry_count])
  @@index([last_attempt_at])
  @@index([retry_count, last_attempt_at])
}

model MergeConflict {
  id                 String   @id @default(cuid())
  field_name         String
  conflicting_values String
  winner_source      String
  winner_value       String
  trust_difference   Int
  severity           Float
  entity_id          String?
  resolved           Boolean  @default(false)
  resolution_notes   String?
  createdAt          DateTime @default(now())
  updatedAt          DateTime @updatedAt

  @@index([field_name])
  @@index([winner_source])
  @@index([severity])
  @@index([resolved])
  @@index([entity_id])
}

model LensEntity {
  lensId    String
  entityId  String
  entity    Entity   @relation(fields: [entityId], references: [id], onDelete: Cascade)
  createdAt DateTime @default(now())

  @@id([lensId, entityId])
  @@index([lensId])
  @@index([entityId])
}

model RawIngestion {
  id            String   @id @default(cuid())
  source        String   // e.g., "serper", "google_places", "osm"
  source_url    String   // Original URL or query that generated this data
  file_path     String   // Path to raw JSON file: engine/data/raw/<source>/<timestamp>_<id>.json
  status        String   // e.g., "success", "failed", "pending"
  ingested_at   DateTime @default(now())
  hash          String   // Content hash for deduplication
  metadata_json String?  // Additional metadata stored as JSON

  extractedEntities ExtractedEntity[]
  failedExtractions FailedExtraction[]

  @@index([source])
  @@index([status])
  @@index([hash])
  @@index([ingested_at])
  @@index([source, status])
  @@index([status, ingested_at])
}"""

    ENTITY_EXTRA_FIELD_LINES = {
        "attributes": "  attributes   String?",
        "mainImage": "  mainImage     String?",
        "outgoingRelationships": '  outgoingRelationships EntityRelationship[] @relation("SourceEntity")',
        "incomingRelationships": '  incomingRelationships EntityRelationship[] @relation("TargetEntity")',
        "lensMemberships": "  lensMemberships LensEntity[]",
    }

    ENTITY_EXTRA_FIELDS_ORDERED = [
        ("attributes", ENTITY_EXTRA_FIELD_LINES["attributes"]),
        ("mainImage", ENTITY_EXTRA_FIELD_LINES["mainImage"]),
        ("outgoingRelationships", ENTITY_EXTRA_FIELD_LINES["outgoingRelationships"]),
        ("incomingRelationships", ENTITY_EXTRA_FIELD_LINES["incomingRelationships"]),
        ("lensMemberships", ENTITY_EXTRA_FIELD_LINES["lensMemberships"]),
    ]

    ENTITY_EXTRA_FIELDS_BY_ANCHOR = {
        "summary": [ENTITY_EXTRA_FIELDS_ORDERED[0]],
        "linkedin_url": [ENTITY_EXTRA_FIELDS_ORDERED[1]],
        "external_ids": [
            ENTITY_EXTRA_FIELDS_ORDERED[2],
            ENTITY_EXTRA_FIELDS_ORDERED[3],
            ENTITY_EXTRA_FIELDS_ORDERED[4],
        ],
    }

    ENTITY_EXTRA_INDEXES = [
        "  @@index([latitude, longitude])",
        "  @@index([createdAt])",
        "  @@index([updatedAt])",
    ]

    def __init__(self, database: str = "postgresql"):
        """
        Initialize Prisma generator.
        
        Args:
            database: Database provider ("postgresql")
        """
        self.database = database
        if database != "postgresql":
            raise ValueError(f"Unsupported database: {database}. Only 'postgresql' is supported.")

    def _get_prisma_field_name(self, field: FieldDefinition) -> str:
        """Return Prisma field name, honoring prisma.name overrides."""
        if field.prisma and "name" in field.prisma:
            return field.prisma["name"]
        return field.name

    def _is_field_skipped(self, field: FieldDefinition) -> bool:
        """Return True if field is marked to skip in Prisma output."""
        return bool(field.prisma and field.prisma.get("skip"))

    def _format_default_attribute(self, field: FieldDefinition) -> Optional[str]:
        """Format a Prisma @default(...) attribute for supported defaults."""
        if field.default is None:
            return None

        if isinstance(field.default, bool):
            return f"@default({str(field.default).lower()})"

        if isinstance(field.default, (int, float)):
            return f"@default({field.default})"

        if isinstance(field.default, str):
            normalized = field.default.strip()
            if normalized.lower() in {"null", "none"}:
                return None
            if normalized in {"dict", "list"}:
                return None
            if normalized in {"cuid()", "now()", "uuid()"}:
                return f"@default({normalized})"
            if field.type == "string":
                return f'@default("{normalized}")'
            return f"@default({normalized})"

        return None

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

        # Dictionary types -> Json
        if field.type == "json" or field.type.startswith("dict"):
            return "Json"

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
        default_attr = self._format_default_attribute(field)
        if default_attr:
            attributes.append(default_attr)

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
        if self._is_field_skipped(field):
            return None

        # Get field name (may be overridden by Prisma config)
        field_name = self._get_prisma_field_name(field)

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
            if self._is_field_skipped(field):
                continue

            # Skip if field is primary key or unique (automatically indexed)
            if field.primary_key or field.unique:
                continue

            # Add index if specified
            if field.index:
                field_name = self._get_prisma_field_name(field)
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

    def _generate_entity_model(self, schema: SchemaDefinition) -> str:
        """
        Generate Entity model with infrastructure fields and indexes.

        Args:
            schema: SchemaDefinition for Entity

        Returns:
            Complete Prisma model as string
        """
        lines = []

        # Model declaration
        lines.append(f"model {schema.name} {{")

        generated_names = set()
        placed_extra = set()

        # Generate fields with anchored extras
        for field in schema.fields:
            field_line = self._generate_field(field)
            if not field_line:
                continue

            field_name = self._get_prisma_field_name(field)
            generated_names.add(field_name)
            lines.append(field_line)

            anchored_extras = self.ENTITY_EXTRA_FIELDS_BY_ANCHOR.get(field_name, [])
            for extra_name, extra_line in anchored_extras:
                if extra_name in generated_names or extra_name in placed_extra:
                    continue
                lines.append(extra_line)
                placed_extra.add(extra_name)

        # Append any remaining extra fields
        for extra_name, extra_line in self.ENTITY_EXTRA_FIELDS_ORDERED:
            if extra_name in generated_names or extra_name in placed_extra:
                continue
            lines.append(extra_line)
            placed_extra.add(extra_name)

        # Add blank line before indexes
        indexes = self._generate_indexes(schema)
        extra_indexes = [idx for idx in self.ENTITY_EXTRA_INDEXES if idx not in indexes]
        if indexes or extra_indexes:
            lines.append("")
            lines.extend(indexes)
            lines.extend(extra_indexes)

        # Close model
        lines.append("}")

        return "\n".join(lines)

    def generate_model(self, schema: SchemaDefinition) -> str:
        """Public wrapper for generating a single model."""
        return self._generate_model(schema)

    def generate_full_schema(self, schemas: List[SchemaDefinition], target: str) -> str:
        """
        Generate complete schema.prisma file including infrastructure models.

        Args:
            schemas: List of SchemaDefinition objects
            target: "engine" or "web"

        Returns:
            Complete Prisma schema file as string
        """
        if target not in {"engine", "web"}:
            raise ValueError("target must be 'engine' or 'web'")

        if not any(schema.name == "Entity" for schema in schemas):
            raise ValueError("Entity schema is required for full Prisma schema generation")

        lines = []

        # Header comment
        lines.append("// ============================================================")
        lines.append("// GENERATED FILE - DO NOT EDIT")
        lines.append("// ============================================================")
        lines.append("// This file is automatically generated from YAML schemas.")
        lines.append("// Source: engine/config/schemas/*.yaml")
        lines.append(f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"// Target: {target}")
        lines.append("//")
        lines.append("// To modify the schema:")
        lines.append("// 1. Edit the YAML files in engine/config/schemas/")
        lines.append("// 2. Run: python -m engine.schema.generate")
        lines.append("// 3. Run: prisma migrate dev")
        lines.append("// ============================================================")
        lines.append("")

        # Generator block
        generator_block = (
            self.ENGINE_GENERATOR_BLOCK
            if target == "engine"
            else self.WEB_GENERATOR_BLOCK
        )
        lines.extend(generator_block)
        lines.append("")

        # Datasource block
        lines.append("datasource db {")
        lines.append(f'  provider = "{self.database}"')
        lines.append('  url      = env("DATABASE_URL")')
        lines.append("}")
        lines.append("")

        model_blocks = []

        if self.INFRA_MODELS_BEFORE_ENTITY:
            model_blocks.append(self.INFRA_MODELS_BEFORE_ENTITY.strip())

        for schema in schemas:
            if schema.name == "Entity":
                model_blocks.append(self._generate_entity_model(schema))
            else:
                model_blocks.append(self._generate_model(schema))

        if self.INFRA_MODELS_AFTER_ENTITY:
            model_blocks.append(self.INFRA_MODELS_AFTER_ENTITY.strip())

        if model_blocks:
            lines.append("\n\n".join(model_blocks))

        return "\n".join(lines).rstrip() + "\n"

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

        # Generator block (engine defaults)
        lines.extend(self.ENGINE_GENERATOR_BLOCK)
        lines.append("")

        # Datasource block
        lines.append("datasource db {")
        lines.append(f'  provider = "{self.database}"')

        lines.append('  url      = env("DATABASE_URL")')

        lines.append("}")
        lines.append("")

        # Generate models
        for i, schema in enumerate(schemas):
            if i > 0:
                lines.append("")  # Blank line between models
            lines.append(self._generate_model(schema))

        return "\n".join(lines) + "\n"

    def generate_to_file(
        self,
        schemas: List[SchemaDefinition],
        output_path: str,
        target: Optional[str] = None,
    ) -> None:
        """
        Generate schema.prisma file and write to disk.

        Args:
            schemas: List of SchemaDefinition objects
            output_path: Path to write schema.prisma file
            target: Optional target ("engine" or "web") for full schema generation
        """
        if target:
            schema_content = self.generate_full_schema(schemas, target=target)
        else:
            schema_content = self.generate_schema(schemas)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(schema_content)
