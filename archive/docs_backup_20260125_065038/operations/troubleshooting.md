# Troubleshooting Guide

This guide helps diagnose and resolve common issues encountered while running the Edinburgh Finds platform.

## 1. Checking Logs
Logs are the first place to look for errors during ingestion.

### Log Locations
- **Ingestion Logs**: `engine/logs/ingestion.log`
- **Unmapped Categories**: `logs/unmapped_categories.log`
- **Application Logs**: Console output during `npm run dev`.

### Common Log Patterns
- `HTTP 429`: Rate limiting from an external provider (Google, Serper). Check your API quotas.
- `LLM Parse Error`: The LLM failed to return valid JSON. Check `engine/extraction/cost_report.py` for extraction health.

## 2. Database Issues

### Schema Drift
If you see errors related to missing columns or table mismatches:
1. Ensure you've run the generator: `python -m engine.schema.generate`
2. Run migrations: `cd web && npx prisma migrate dev`

### Connectivity
Ensure your `DATABASE_URL` is correct and the database is reachable.
Use `engine/inspect_db.py` to verify the connection and basic stats.

## 3. Ingestion Failures

### Failed Extractions
Check the `FailedExtraction` table in the database:
```bash
npx prisma studio
```
Look for common error messages in the `error_message` column to identify patterns (e.g., specific websites failing consistently).

### Raw Data Inspection
If an entity looks incorrect, find its `RawIngestion` record to see exactly what was received from the source. Raw files are stored in `engine/data/raw/<source>/`.

## 4. Environment Issues

### Missing API Keys
Ensure all required keys are in your `.env` file. Many connectors will skip execution or fail silently if their required keys are missing.

---
*Evidence: engine/logs/, engine/inspect_db.py, and database schema.*
