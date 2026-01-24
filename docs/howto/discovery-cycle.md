Audience: Developers

# Running a Discovery Cycle

A discovery cycle is the process of fetching raw data from external sources, extracting structured entities, and merging them into the unified database.

## Phase 1: Ingestion

Ingestion pulls raw data into the `RawIngestion` table. You can run ingestion manually for a specific source or use the orchestrator.

### Manual Ingestion
```bash
# Fetch from OpenStreetMap
python -m engine.ingestion.cli osm "padel"

# Fetch from Serper (Google Search Results)
python -m engine.ingestion.cli serper "padel courts edinburgh"
```

### Checking Ingestion Status
```bash
python -m engine.ingestion.cli status
```

## Phase 2: Extraction

Extraction uses LLMs to process `pending` records in the `RawIngestion` table.

### Run Extraction for a Lens
```bash
python -m engine.orchestration.orchestrator --lens edinburgh_finds --mode extract
```

This will:
1.  Load the Lens configuration.
2.  Find pending records matching the Lens classification.
3.  Send them to the LLM for structured extraction.
4.  Create or update `Entity` records.
5.  Link sources via `EntitySourceLink`.

## Phase 3: Merging & Deduplication

The engine automatically handles merging when it detects high-similarity entities.

- **Trust Levels:** Defined in `engine/config/extraction.yaml`. Higher trust sources will overwrite fields from lower trust sources.
- **Deduplication:** Uses fuzzy matching on names and spatial proximity for coordinates.

## Full Automation

To run a complete cycle (Ingest -> Extract -> Merge) for a specific Lens:

```bash
python -m engine.orchestration.orchestrator --lens edinburgh_finds --full
```

## Monitoring the Run

- **Logs:** Check `engine/logs/orchestrator.log` for execution details.
- **Costs:** Monitor `engine/logs/llm_usage.log` to track token usage and estimated costs.
- **Errors:** Check the `RawIngestion` table for records with `status = 'quarantined'`.

## Periodic Runs

It is recommended to run discovery cycles periodically (e.g., weekly) to keep the data fresh. Use a cron job or a task scheduler to automate the `--full` command.
