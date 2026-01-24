Audience: Developers

# Managing the Extraction Quarantine

When the extraction engine fails to process a raw record (e.g., due to LLM errors, schema validation failures, or classification ambiguity), the record is moved to the **Quarantine**.

## Why Records are Quarantined

1.  **LLM Failure:** The AI provider returned an error or an unparsable response.
2.  **Schema Validation:** The extracted data does not match the Pydantic models (e.g., missing required fields, invalid types).
3.  **Classification Drift:** The record was initially classified as relevant but the extraction phase determined it does not belong to any active Lens.
4.  **Rate Limits:** Multiple retries failed due to API throttling.

## Inspecting Quarantined Records

You can view quarantined records directly in the database or via the CLI.

### Via CLI
```bash
python -m engine.extraction.cli --status
```

### Via SQL
```sql
SELECT id, connector, status, last_error FROM "RawIngestion" WHERE status = 'quarantined';
```

## Retrying Extractions

If you have fixed a bug or updated the extraction logic, you can attempt to re-process quarantined records.

```bash
# Retry all quarantined records
python -m engine.extraction.cli --retry-failed

# Retry with a limit
python -m engine.extraction.cli --retry-failed --limit 50
```

## Handling Persistent Failures

If a record continues to fail:

1.  **Analyze the `last_error`:** This field in the `RawIngestion` table contains the traceback or error message from the last attempt.
2.  **Check the Raw Data:** Sometimes the source data is simply too noisy or corrupted for extraction.
3.  **Manual Cleanup:** If the data is truly useless, you can delete the records from the `RawIngestion` table.
4.  **Adjust Classification:** If a source consistently produces irrelevant "garbage," update the classification rules in `extraction.yaml` or the Lens configuration.

## Best Practices

- **Monitor Daily:** In production, check the quarantine count daily. A sudden spike usually indicates an API change or an LLM service regression.
- **Don't Retry Indefinitely:** Use the `--max-retries` flag to prevent wasting LLM tokens on records that will never succeed.
