# Operations Runbook

This document covers common operational tasks for maintaining the Edinburgh Finds platform.

## Deployment

Currently, the platform is designed for local or server-based execution.

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

### Backend (Engine)
1. Pull the latest code.
2. Update virtual environment: `pip install -r engine/requirements.txt`.
3. Run database migrations: `npx prisma migrate deploy --schema=engine/schema.prisma`.

### Frontend (Web)
1. `cd web`.
2. `npm install`.
3. `npm run build`.
4. Start with `npm run start` (or use a process manager like PM2).

## Monitoring

### Logs
- **Backend**: Logs are typically sent to `stdout`. Use `LOG_LEVEL=DEBUG` in `.env` for more detail.
- **Frontend**: Check the Next.js server logs for API errors.

### Database Health
Monitor the `FailedExtraction` table for high failure rates, which might indicate:
- LLM API outages.
- Changes in raw data format from sources.
- Overly strict validation rules in Pydantic models.

## Troubleshooting

### "Anthropic API Rate Limit Reached"
- **Symptom**: Extraction slows down or logs "429 Too Many Requests".
- **Fix**: Reduce concurrency in `engine/config/extraction.yaml` or wait for the quota to reset.

### "Prisma Client Not Generated"
- **Symptom**: Python or JS errors about missing Prisma client.
- **Fix**: 
  - Python: `python -m prisma generate --schema=engine/schema.prisma`
  - JS: `cd web && npx prisma generate --schema=../engine/schema.prisma`

### Entities not appearing in UI
- **Check**: Ensure the entities have a `LensEntity` membership record.
- **Check**: Verify the `status` in the `RawIngestion` table is `success`.
- **Check**: Use `python engine/inspect_db.py` to query the database directly.
