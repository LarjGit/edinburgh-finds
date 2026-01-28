# CLI Reference (Engine)

The Engine is controlled primarily through a Python-based CLI. This reference covers the main commands for ingestion, extraction, and monitoring.

## Ingestion CLI
**Module**: `engine.ingestion.cli`

### `google_places`
Ingest data from Google Places API v1.
```bash
python -m engine.ingestion.cli google_places "<query>"
```
- **Query**: Search string (e.g., "restaurants in Edinburgh").
- **Output**: Raw JSON saved to `engine/data/raw/google_places/`.

### `openstreetmap`
Ingest data from OpenStreetMap via Overpass QL.
```bash
python -m engine.ingestion.cli openstreetmap "<amenity_type>"
```
- **Amenity**: OSM tag value (e.g., "tennis_court").

### `serper`
Ingest web search results from Serper.
```bash
python -m engine.ingestion.cli serper "<query>"
```

### `status`
View the status of ingestion jobs and health metrics.
```bash
python -m engine.ingestion.cli status
```

## Extraction CLI
**Module**: `engine.extraction.cli`

### `run`
Extract structured entities from raw ingestion records.
```bash
python -m engine.extraction.cli run [--source <source>] [--limit <n>]
```

### `report`
Generate a report on extraction quality and costs.
```bash
python -m engine.extraction.cli report
```

## Database CLI
**Module**: `engine.schema`

### `generate`
Generate Prisma, Pydantic, and TypeScript code from YAML schemas.
```bash
python -m engine.schema.generate
```

## Infrastructure CLI
**Script**: `scripts/check_engine_purity.sh`

### `check`
Verify that the engine remains decoupled from specific lenses.
```bash
bash scripts/check_engine_purity.sh
```

---
*Evidence: docs/architecture/subsystems/engine.md, docs/architecture/subsystems/scripts.md*
