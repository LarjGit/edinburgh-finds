# Troubleshooting Guide

This guide helps diagnose and resolve common issues encountered during development and operation of the Edinburgh Finds platform.

## Common Error Patterns

### 1. Rate Limit Exhaustion (`RateLimitExceeded`)
- **Symptoms**: `RateLimitExceeded` exception in logs; ingestion jobs pausing or failing with 429 errors.
- **Cause**: The connector has exceeded the per-minute or per-hour quota defined in `engine/config/sources.yaml`.
- **Resolution**:
    - Check the quota settings for the source in `sources.yaml`.
    - Increase the `retry_delay` or decrease the `max_requests_per_minute`.
    - If using Google Places, check the Google Cloud Console for billing or quota caps.

### 2. LLM Extraction Failures
- **Symptoms**: `logger.error("Failed to extract ...")` in logs; `ExtractedEntity` table has records with low confidence or missing data.
- **Cause**:
    - **Token Limit**: Raw data is too large for the LLM context window.
    - **Schema Mismatch**: The raw data format has changed and the extractor can't parse it.
    - **LLM Downtime**: API errors from Anthropic.
- **Resolution**:
    - Review the raw JSON in `engine/data/raw/` to ensure it's not malformed.
    - Check `engine/extraction/cost_report.py` to see if budgets are being exceeded.
    - Run the extraction CLI with `--limit 1` and debug output enabled.

### 3. Engine Purity Violations
- **Symptoms**: CI pipeline fails at the `engine-purity` step.
- **Cause**: A file in the `engine/` directory is importing from `lenses/` or contains domain-specific hardcoded logic.
- **Resolution**:
    - Move domain-specific logic to a `lens.yaml` file.
    - Ensure communication between engine and lenses happens only via the `LensContract` interface.
    - Run `bash scripts/check_engine_purity.sh` locally to find the offending file.

### 4. Database Sync Issues
- **Symptoms**: Python backend works but Next.js frontend shows errors or missing fields.
- **Cause**: Prisma schemas are out of sync.
- **Resolution**:
    - Re-run the generator: `python -m engine.schema.generate`.
    - Re-run Prisma generate in the web folder: `cd web && npx prisma generate`.
    - Check for pending migrations: `npx prisma migrate status`.

## Diagnostic Commands

### View Ingestion Health
```bash
python -m engine.ingestion.cli status
```

### Check Database sample
```bash
python -m engine.check_data
```

### Validate a Lens
```bash
python scripts/validate_wine_lens.py
```

## Log Locations
- **Standard Out**: Most CLIs log to stdout/stderr.
- **File Logs**: `engine/logs/ingestion.log` contains detailed records of API interactions and errors.

---
*Evidence: engine/ingestion/rate_limiting.py, engine/extraction/run.py, scripts/check_engine_purity.sh*
