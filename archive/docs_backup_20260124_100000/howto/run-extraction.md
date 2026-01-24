# How to Run Data Extraction

Audience: Data Engineers.

After ingesting raw data, you need to extract structured entities.

## Manual Trigger

To retry failed extractions or process a specific batch:

```bash
# Retry up to 10 failed items
python -m engine.extraction.cli --retry-failed --limit 10
```

## Scheduled Extraction

Extraction is typically run as a background worker or cron job. Ensure the process:
1.  Queries `RawIngestion` records with `status='pending'`.
2.  Passes text to the LLM.
3.  Saves result to `Entity` and `ExtractedEntity`.

Evidence: `engine/extraction/cli.py`
