Audience: Developers

# CLI Reference

The Edinburgh Finds engine provides several command-line tools for data ingestion, extraction maintenance, and schema management.

## Ingestion CLI (`engine.ingestion.cli`)

Manages the fetching of raw data from external connectors and its storage in the `RawIngestion` table.

### Usage
```bash
python -m engine.ingestion.cli [connector] [query] [options]
```

### Commands
- `[connector] [query]`: Run a specific connector with a search query.
- `status`: Show a comprehensive ingestion status report, including success rates and recent records.

### Options
- `-v`, `--verbose`: Enable detailed output, including database connection and fetch samples.
- `--list`: List all available connectors and their base URLs.
- `--status`: Alias for the `status` command.

### Examples
```bash
# Fetch padel venues from Serper
python -m engine.ingestion.cli serper "padel edinburgh"

# Fetch sports facilities from OpenStreetMap
python -m engine.ingestion.cli openstreetmap "tennis"

# Show ingestion summary
python -m engine.ingestion.cli status
```

---

## Extraction CLI (`engine.extraction.cli`)

Maintenance tool for the extraction engine, focused on managing the quarantine and retry workflows.

### Usage
```bash
python -m engine.extraction.cli [options]
```

### Options
- `--retry-failed`: Attempt to re-extract records that previously failed and are in quarantine.
- `--max-retries [N]`: Maximum number of failed retries allowed before skipping a record (default: 3).
- `--limit [N]`: Limit the number of failed extractions to retry in a single run.

---

## Schema CLI (`engine.schema.generate`)

Generates Python, TypeScript, and Prisma schemas from YAML definitions stored in `engine/config/schemas/`.

### Usage
```bash
python -m engine.schema.generate [options]
```

### Options
- `--validate`: Check if generated Python schemas are in sync with YAML definitions (exit 1 on drift).
- `--schema [NAME]`: Generate only a specific schema (e.g., `entity`).
- `--typescript`: Generate TypeScript interfaces in `web/types/`.
- `--zod`: Generate Zod validation schemas (requires `--typescript`).
- `--pydantic-extraction`: Generate the Pydantic model used by the LLM for extraction.
- `--prisma`: Generate Prisma schema files for both engine and web.
- `--no-prisma`: Skip Prisma generation.
- `--force`: Overwrite existing files without prompting.
- `--format`: Format generated Python files using `black`.
- `--dry-run`: Show what would be generated without writing to disk.

### Examples
```bash
# Full regeneration of all schemas
python -m engine.schema.generate --force --format

# Validate schema sync in CI
python -m engine.schema.generate --validate

# Generate TypeScript types for the frontend
python -m engine.schema.generate --typescript --zod
```
