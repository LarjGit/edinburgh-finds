Audience: Developers

# Schema Core Subsystem

## Overview
The Schema Core subsystem provides a framework-neutral mechanism for defining and managing entity data structures within the Edinburgh Finds platform. It centers around a declarative YAML-based schema definition that is parsed into an internal metadata representation (`FieldSpec`), which then drives various projections including database schemas (Prisma), validation models (Pydantic), and LLM extraction instructions.

## Components

### FieldSpec
The `FieldSpec` dataclass is the universal internal representation of a single data field. It captures semantic, technical, and operational metadata without being tied to a specific framework like SQLAlchemy or Pydantic.

- **Semantic Metadata**: Includes `search_category` and `search_keywords` used by the orchestration layer to map natural language queries to specific fields.
- **Database Constraints**: Captures `index`, `unique`, `primary_key`, and `sa_column` (SQLAlchemy column overrides).
- **Extraction Control**: The `exclude` flag determines if a field should be presented to the LLM during the extraction phase.

Evidence: `engine/schema/core.py:4-31`

### Schema Parser
The `SchemaParser` is responsible for ingesting YAML schema definitions and validating them against a supported set of types (e.g., `string`, `integer`, `json`, `list[string]`).

- **Validation**: Ensures required fields like `name` and `type` are present and that types are within the `SUPPORTED_TYPES` set.
- **Internal Model**: Produces `SchemaDefinition` and `FieldDefinition` objects which serve as the bridge between raw YAML and generated Python code.

Evidence: `engine/schema/parser.py:61-180`

### Entity Definition (`ENTITY_FIELDS`)
The system provides a base `ENTITY_FIELDS` list, which is a generated collection of `FieldSpec` objects defining the universal attributes for all entities (venues, retailers, etc.).

- **Identity**: `entity_id`, `entity_name`, `slug`.
- **Classification**: `entity_class` (universal functional style).
- **Contact & Location**: `street_address`, `postcode`, `latitude`, `longitude`, `phone`, `email`.
- **Extensibility**: `discovered_attributes` and `modules` (JSONB fields) for data that doesn't fit the fixed schema.

Evidence: `engine/schema/entity.py:27-268`

## Data Flow

1. **Definition**: Developers define entity structures in `engine/config/schemas/*.yaml`.
2. **Parsing**: `SchemaParser` reads YAML and produces `SchemaDefinition`.
3. **Generation (Static)**: A generator (referenced in `entity.py` header) produces `engine/schema/entity.py` containing the `ENTITY_FIELDS` list.
4. **Projection (Dynamic)**: Utilities in `generator.py` consume `FieldSpec` lists to create runtime artifacts like Pydantic models.

## Public Interfaces

### Field Helpers
`engine/schema/entity.py` provides several utility functions to filter and access field metadata:
- `get_field_by_name(name)`: Retrieves a specific `FieldSpec`.
- `get_extraction_fields()`: Returns fields intended for LLM extraction (where `exclude=False`).
- `get_fields_with_search_metadata()`: Returns fields tagged for search indexing.

Evidence: `engine/schema/entity.py:270-286`

### Dynamic Model Generation
`engine/schema/generator.py` provides `create_pydantic_model`, which allows the system to generate validation schemas on-the-fly from any list of `FieldSpec` objects.

Evidence: `engine/schema/generator.py:34-70`

## Configuration Surface
The primary configuration for this subsystem is the YAML schema files located in `engine/config/schemas/`. These files define:
- Field names and types.
- Nullability and requirement constraints.
- Search categories for the Lens system.
- Framework-specific overrides (Python/Prisma).

Evidence: `engine/schema/parser.py:126-146`
