# How-To: Run Extraction

This guide explains how to run the extraction pipeline to process raw ingested data into structured entities.

## Prerequisites

- Ensure you have run an ingestion script (e.g., `python engine/ingest.py`) and have records in the `RawIngestion` table.
- Ensure your `.env` file has a valid `ANTHROPIC_API_KEY`.

## Basic Usage

The primary entry point for extraction is `scripts/run_lens_aware_extraction.py`. This script is "lens-aware," meaning it will use the rules defined in a specific lens to guide the extraction.

### Running for a specific Lens

To run extraction for the "Edinburgh Finds" lens:

```bash
python scripts/run_lens_aware_extraction.py --lens edinburgh_finds
```

### Options

- `--lens`: (Required) The name of the lens to use (e.g., `edinburgh_finds`, `wine_discovery`).
- `--limit`: Limit the number of records to process (useful for testing).
- `--force`: Re-extract records that have already been processed.

## Advanced: Running the Engine Directly

You can also run the core extraction logic without lens-specific orchestration using the engine's internal CLI:

```bash
python -m engine.extraction.run --source google_places
```

Note: This will use the generic engine rules and may not populate lens-specific dimensions as effectively as the lens-aware script.

## Monitoring Extraction

Extraction progress and logs are visible in the console. You can also check the `ExtractedEntity` and `FailedExtraction` tables in the database to see the results.

### Checking for Failures

If extraction fails for certain records, they will be logged in the `FailedExtraction` table with an error message. Common causes include:
- API rate limits (Anthropic).
- Malformed raw data.
- LLM hallucination/validation errors (Pydantic).
