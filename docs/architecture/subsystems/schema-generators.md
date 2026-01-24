Audience: Developers

# Schema Generators Subsystem

## Overview
The Schema Generators subsystem is responsible for transforming framework-neutral `SchemaDefinition` and `FieldDefinition` objects (parsed from YAML) into concrete, framework-specific artifacts. This ensures that the YAML schema remains the single source of truth for the entire platform, from the database layer to the frontend and LLM extraction logic.

## Components

### Prisma Generator (`PrismaGenerator`)
Generates `schema.prisma` files for both the engine (Python/asyncio) and the web (Next.js/JS) environments.

- **Type Mapping**: Maps YAML types like `string`, `integer`, and `json` to Prisma types (`String`, `Int`, `Json`).
- **Infrastructure Models**: Injects standard platform models like `RawIngestion`, `ExtractedEntity`, and `LensEntity` into the generated schema.
- **Overrides**: Supports `prisma.name`, `prisma.type`, and `prisma.skip` metadata in YAML for fine-grained control over the database schema.
- **Targets**: Can generate targeted schemas for `engine` (using `prisma-client-py`) or `web` (using `prisma-client-js`).

Evidence: `engine/schema/generators/prisma.py:17-436`

### Pydantic Extraction Generator (`PydanticExtractionGenerator`)
Creates Pydantic models specifically tuned for LLM structured output extraction.

- **Optionality by Default**: Fields are typically generated as `Optional` to prevent LLM validation errors if a piece of information is missing from the source.
- **Extraction Required**: The `python.extraction_required` flag in YAML can force specific fields to be mandatory for the LLM.
- **Custom Validators**: Automatically generates Pydantic field validators for `non_empty`, `e164_phone`, `url_http`, and `postcode_uk` based on YAML metadata.
- **Instructional Docstrings**: Includes "Null if not found" or "REQUIRED" hints in field descriptions to guide the LLM's behavior.

Evidence: `engine/schema/generators/pydantic_extraction.py:27-440`

### Python FieldSpec Generator (`PythonFieldSpecGenerator`)
Produces the static `ENTITY_FIELDS` list used by the engine's internal logic.

- **Static Generation**: Converts YAML definitions into `FieldSpec` constructor calls in `engine/schema/entity.py`.
- **Inheritance**: Supports schema extension (e.g., a specific lens extending the base Entity) by combining parent and child field lists.
- **Search Metadata**: Persists `search_category` and `search_keywords` into the static Python objects.

Evidence: `engine/schema/generators/python_fieldspec.py:15-207`

### TypeScript Generator (`TypeScriptGenerator`)
Generates frontend types and validation schemas for the web application.

- **Interfaces**: Produces TypeScript `interface` definitions for type safety in React/Next.js.
- **Zod Schemas**: Optionally generates Zod schemas for runtime validation of API responses and form data.
- **JSDoc Integration**: Transfers field descriptions from YAML into JSDoc comments for enhanced IDE support.

Evidence: `engine/schema/generators/typescript.py:16-193`

## Data Flow

1. **Input**: A list of `SchemaDefinition` objects from the `SchemaParser`.
2. **Dispatch**: The `generate` CLI (or orchestration layer) invokes the appropriate generator based on the desired output.
3. **Template/String Construction**: Each generator uses its internal mapping and logic to build the target file content.
4. **Persistence**: The generated code is written to specific locations (e.g., `engine/schema/entity.py`, `engine/schema.prisma`).

## Configuration Surface
The behavior of these generators is controlled via the `python`, `prisma`, and `search` blocks within the field definitions of the YAML schemas:

```yaml
fields:
  - name: phone
    type: string
    python:
      validators: ["e164_phone"]
    prisma:
      attributes: ["@unique"]
    search:
      category: "contact"
```

Evidence: `engine/schema/generators/pydantic_extraction.py:255-265`, `engine/schema/generators/prisma.py:182-192`
