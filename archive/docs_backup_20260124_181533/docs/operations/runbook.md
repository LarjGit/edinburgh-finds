Audience: Developers, Operations

# Operations Runbook

This runbook provides procedures for deploying, monitoring, and maintaining the Edinburgh Finds system.

## 🚀 Deployment

### Backend (Python Engine)

1.  **Environment:** Ensure the target server has Python 3.10+ and PostgreSQL with PostGIS.
2.  **Pull Changes:** `git pull origin main`
3.  **Install Dependencies:** `pip install -r engine/requirements.txt`
4.  **Database Migration:** `npx prisma db push --schema engine/schema.prisma`
5.  **Environment Variables:** Verify `.env` contains:
    - `DATABASE_URL`
    - `ANTHROPIC_API_KEY` (or OpenAI equivalent)
    - `SERPER_API_KEY`
    - `GOOGLE_PLACES_API_KEY`

### Frontend (Next.js)

1.  **Build:** `cd web && npm install && npm run build`
2.  **Start:** `npm run start` (or use a process manager like PM2)

---

## 📊 Monitoring

Monitoring is configured in `engine/config/monitoring_alerts.yaml`.

### Health Check Dashboard
Run the following command to see a snapshot of the engine's health:
```bash
python -m engine.extraction.health
```

### Key Metrics to Watch
- **Extraction Failure Rate:** Alert if > 10%. Indicates prompt issues or source data drift.
- **LLM Costs:** Alert if daily budget (£50) is exceeded.
- **Cache Hit Rate:** Target > 40%. Low hit rate indicates inefficient prompt hashing.
- **Backlog:** Monitor the count of `pending` records in `RawIngestion`.

---

## 🛠️ Maintenance Tasks

### Clearing the Cache
If you update prompt templates, you may want to invalidate the LLM cache:
```sql
TRUNCATE "LLMCache";
```

### Archiving Raw Data
Old raw data can consume significant disk space. Archive records older than 90 days:
```sql
DELETE FROM "RawIngestion" WHERE created_at < NOW() - INTERVAL '90 days' AND status = 'processed';
```

### Rotating API Keys
1.  Update the key in `engine/config/sources.yaml` or `.env`.
2.  Restart the orchestration engine to pick up the new key.
3.  Run a test ingestion to verify the new key works.

---

## 🚨 Troubleshooting

### High Extraction Failure Rate
1.  Check the `FailedExtraction` table for error messages.
2.  If errors are "Pydantic Validation," the LLM is failing to follow the schema. Update the prompt.
3.  If errors are "Rate Limit," increase the `timeout_seconds` or reduce concurrency in `extraction.yaml`.

### Database Connection Failures
1.  Verify the database is reachable from the application server.
2.  Check for maximum connection limits in PostgreSQL.
3.  Ensure the `DATABASE_URL` uses the correct internal/external IP.

### LLM Costs Spiking
1.  Check if a new Lens has a very broad `seed_query`.
2.  Verify that `deduplication.py` is correctly linking records (to prevent re-extracting the same entity).
3.  Consider switching to a smaller model (e.g., Claude Haiku) for high-volume, low-complexity extractions.
