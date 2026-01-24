# Interfaces Reference

Audience: Developers and Operators.

## CLI Tools

The engine provides several CLI entry points for data management.

### Extraction Maintenance
Managed via `engine/extraction/cli.py`.

```bash
python -m engine.extraction.cli --retry-failed [--limit N]
```
- `--retry-failed`: Re-runs extractions that previously failed (stored in `FailedExtraction` table).
- `--limit`: Restrict the number of records to retry.

Evidence: `engine/extraction/cli.py`

### Ingestion Scripts
Standalone scripts for running specific ingestion pipelines.

- `python engine/run_osm_comprehensive.py`: Runs the OpenStreetMap ingestion.
- `python engine/run_osm_manual.py`: Manual trigger for OSM.
- `python engine/run_seed.py`: Seeds the database with initial data.

Evidence: `engine/` directory listing.

## Web API

The Next.js application exposes API routes for the frontend.

- **Location**: `web/app/api/`
- **Framework**: Next.js Server Actions / API Routes.
