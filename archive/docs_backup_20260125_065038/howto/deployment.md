# Deployment Guide

Edinburgh Finds is designed to be deployed using modern cloud platforms and managed services.

## Infrastructure
- **Database**: PostgreSQL hosted on **Supabase**.
- **Frontend/API**: **Vercel** or any Node.js-compatible hosting (e.g., Railway, Render).
- **Data Engine**: Can be run as a scheduled task (Cron), a GitHub Action, or on a persistent server/container.

## 1. Database Deployment
1. Create a new project on Supabase.
2. Get the **Connection String (Transaction)**.
3. Set `DATABASE_URL` in your production environment.
4. Apply migrations: `npx prisma migrate deploy`.

## 2. Web App Deployment (Vercel)
1. Connect your repository to Vercel.
2. Set the Environment Variables:
    - `DATABASE_URL`
3. Vercel will automatically detect Next.js and deploy.

## 3. Data Engine (Scheduled Ingestion)
To keep the data fresh, you can set up a scheduled ingestion job.

### Example GitHub Action
```yaml
name: Scheduled Ingestion
on:
  schedule:
    - cron: '0 0 * * *' # Every night at midnight
jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Ingestion
        run: |
          pip install -r engine/requirements.txt
          python engine/run_osm_manual.py --query "New venues in Edinburgh"
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          # ... other keys
```

## 4. Production Considerations
- **Rate Limiting**: Monitor API usage for Google and Serper to avoid unexpected costs.
- **Backups**: Supabase handles daily database backups.
- **Monitoring**: Use the built-in health checks in `engine/extraction/health.py` to monitor extraction quality.

---
*Evidence: conductor/tech-stack.md and .github/workflows/tests.yml.*
