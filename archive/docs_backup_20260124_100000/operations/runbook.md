# Operations Runbook

Audience: DevOps and Site Reliability Engineers.

## Database Management

### Migrations
We use Prisma for database migrations.

```bash
# Create a new migration based on schema changes
npx prisma migrate dev --name <migration_name>

# Apply migrations to production
npx prisma migrate deploy
```

Evidence: `web/package.json` (prisma dependency), `engine/schema.prisma`.

### Seeding Data
To populate the database with initial data:

```bash
python -m engine.run_seed
```

Evidence: `engine/run_seed.py`.

## Data Pipeline Operations

### Triggering Ingestion
To run the full ingestion pipeline (e.g., for OSM):

```bash
python -m engine.run_osm_comprehensive
```

### Handling Failures
If extraction fails, entities are moved to a quarantine state (`FailedExtraction` table).

To retry failed items:
```bash
python -m engine.extraction.cli --retry-failed
```

Evidence: `engine/extraction/cli.py`.
