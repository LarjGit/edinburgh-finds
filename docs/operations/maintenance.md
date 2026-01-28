# Maintenance Guide

Routine maintenance tasks to keep the Edinburgh Finds system healthy and up to date.

## Routine Tasks

### 1. Schema & Type Synchronization
Whenever the data model changes, you must synchronize all generated code.
```bash
python -m engine.schema.generate
cd web
npx prisma generate
```

### 2. Database Migrations
After updating the schema, apply migrations to the database.
```bash
npx prisma migrate dev --name <description>
```

### 3. Lens Membership Updates
Periodically refresh which entities belong to which lenses, especially after new ingestion.
```bash
python scripts/run_lens_aware_extraction.py
```

### 4. Cleaning Up Raw Data
Raw ingestion files can accumulate over time.
- **Location**: `engine/data/raw/`
- **Policy**: Archives older than 90 days should be compressed or moved to long-term storage (e.g., S3).

## Data Integrity Checks

### Verify Engine Purity
Run the purity check weekly or as part of every PR.
```bash
bash scripts/check_engine_purity.sh
```

### Validate Documentation
Ensure the documentation suite matches the codebase state.
```bash
python scripts/validate_docs.py
```

### Check for Unmapped Categories
Review logs for categories that the LLM couldn't map to canonical dimensions.
```bash
tail -n 100 logs/unmapped_categories.log
```

## Scaling Considerations
- **Database**: Monitor the size of the `RawIngestion` and `ExtractedEntity` tables. Consider vacuuming or partitioning if performance degrades.
- **LLM Costs**: Monitor `engine/extraction/cost_report.py` output to avoid budget overruns during large ingestion jobs.

---
*Evidence: engine/schema/generate.py, scripts/run_lens_aware_extraction.py, engine/ingestion/storage.py*
