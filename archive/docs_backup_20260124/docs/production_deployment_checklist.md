# Production Deployment Checklist - Data Extraction Engine

This checklist ensures safe, reliable deployment of the Edinburgh Finds data extraction engine to production.

## Prerequisites

### Environment Setup

- [ ] **Production database provisioned**
  - PostgreSQL instance configured (when migrating from SQLite)
  - Connection string secured in environment variables
  - Database user with appropriate permissions created

- [ ] **API Keys configured**
  - `ANTHROPIC_API_KEY` set in environment (for LLM extraction)
  - All connector API keys validated in `engine/config/sources.yaml`
  - Keys stored securely (never in version control)

- [ ] **Python environment ready**
  - Python 3.12+ installed
  - Virtual environment created
  - All dependencies installed (`pip install -r requirements.txt`)
  - Prisma client generated (`prisma generate`)

### Database Migrations

- [ ] **Schema migrations applied**
  - All migrations in `web/prisma/migrations/` reviewed
  - Migrations applied to production database (`prisma migrate deploy`)
  - Database indexes verified (performance indexes from Phase 10)
  - No pending schema changes

- [ ] **Data verification**
  - Test query to confirm database connectivity
  - Verify existing data integrity if migrating
  - Backup taken before deployment

## Configuration Review

### Extraction Configuration

- [ ] **Review `engine/config/extraction.yaml`**
  - LLM model appropriate for production (`claude-haiku-20250318` for cost efficiency)
  - Trust levels configured correctly
  - Default parameters validated

- [ ] **Review `engine/config/sources.yaml`**
  - All enabled sources tested
  - Rate limits appropriate for production load
  - Field masks optimized for required data

- [ ] **Review `engine/config/canonical_categories.yaml`**
  - Category taxonomy complete
  - Promotion workflow documented

### Performance Settings

- [ ] **Database indexes present**
  ```sql
  -- Verify indexes exist (from Phase 10):
  - Listing: entityType, city, postcode, (latitude, longitude), createdAt, updatedAt
  - RawIngestion: source, status, hash, ingested_at, (source, status), (status, ingested_at)
  - ExtractedListing: (source, entity_type), createdAt
  - FailedExtraction: last_attempt_at, (retry_count, last_attempt_at)
  ```

- [ ] **LLM caching enabled**
  - `extraction_hash` field populated on ExtractedListing records
  - Cache hit rate monitored
  - Cache invalidation strategy documented

- [ ] **Logging configured**
  - Log level appropriate for production (`INFO` or `WARNING`)
  - Structured logging enabled (JSON format)
  - Log rotation configured to prevent disk fill
  - Sensitive data NOT logged (API keys, PII)

## Testing & Validation

### Pre-Deployment Tests

- [ ] **Unit tests passing**
  ```bash
  cd engine && python -m pytest extraction/tests/ -v
  # Expect: 125+ tests passing, >80% coverage
  ```

- [ ] **Integration tests passing**
  ```bash
  python -m pytest extraction/tests/test_e2e_extraction.py -v
  # Verify end-to-end flow: Ingest → Extract → Merge → Verify
  ```

- [ ] **Snapshot tests passing**
  ```bash
  python -m pytest extraction/tests/test_snapshots.py -v
  # Ensures no extraction regressions
  ```

### Production Dry Run

- [ ] **Test extraction on small dataset**
  ```bash
  python -m engine.extraction.run --source=google_places --limit=10 --dry-run
  # Verify: No errors, expected output, performance acceptable
  ```

- [ ] **Test health dashboard**
  ```bash
  python -m engine.extraction.health
  # Verify: Metrics accurate, no warnings/errors
  ```

- [ ] **Test retry logic**
  ```bash
  python -m engine.extraction.run --retry-failed --limit=5
  # Verify: Failed extractions retry correctly
  ```

## Deployment Steps

### 1. Code Deployment

- [ ] **Deploy application code**
  - Pull latest code from production branch
  - Install/update dependencies
  - Run Prisma generate to update client
  - Verify file permissions

### 2. Database Setup

- [ ] **Run migrations**
  ```bash
  cd web && npx prisma migrate deploy
  ```

- [ ] **Verify schema**
  ```bash
  # Check that all expected tables exist:
  # - Listing, Category, ListingRelationship
  # - RawIngestion, ExtractedListing, FailedExtraction, MergeConflict
  ```

### 3. Initial Data Load

- [ ] **Run initial ingestion** (if starting fresh)
  ```bash
  # Example: Ingest padel venues in Edinburgh
  python -m engine.ingestion.cli google_places "padel edinburgh"
  python -m engine.ingestion.cli serper "padel edinburgh"
  python -m engine.ingestion.cli openstreetmap "padel"
  ```

- [ ] **Run initial extraction**
  ```bash
  python -m engine.extraction.run_all --limit=100
  # Monitor: Success rate, LLM cost, duration
  ```

- [ ] **Verify data quality**
  - Check ExtractedListing records created
  - Verify merged Listing records
  - Inspect sample listings for accuracy

### 4. Monitoring Setup

- [ ] **Configure health checks**
  - Set up cron job or scheduler for periodic health checks
  - Example: Run health dashboard every hour, alert if status not "HEALTHY"

- [ ] **Configure alerts** (see Monitoring Alert Thresholds section below)
  - Failure rate alerts
  - Cost alerts
  - Performance degradation alerts

- [ ] **Set up logging aggregation**
  - Configure log shipping to central logging system (if available)
  - Set up log-based alerts for ERROR level messages

## Post-Deployment Validation

### Immediate Checks (within 1 hour)

- [ ] **Verify extraction running**
  ```bash
  python -m engine.extraction.health
  # Expect: "HEALTHY" status, no critical errors
  ```

- [ ] **Check initial metrics**
  - Extraction success rate >85% for LLM sources, 100% for deterministic
  - Field null rates < 50% for critical fields (entity_name, location)
  - No merge conflicts with severity >0.8

- [ ] **Monitor LLM costs**
  ```bash
  python -m engine.extraction.health | grep "Estimated Cost"
  # Verify cost is within expected range (< £0.50 per 100 records)
  ```

### 24-Hour Checks

- [ ] **Review accumulated logs**
  - No unexpected ERROR or WARNING messages
  - Extraction patterns match expectations
  - No performance degradation over time

- [ ] **Check data completeness**
  - All expected sources processed
  - No large batches of failed extractions
  - Listings created match expected volume

- [ ] **Validate cache effectiveness**
  ```bash
  # Check cache hit rate (should increase over time)
  # Query ExtractedListing for duplicate extraction_hash values
  ```

### Weekly Checks

- [ ] **Review extraction quality**
  - Sample 10-20 listings for accuracy
  - Verify summaries are high quality
  - Check that categories are appropriate

- [ ] **Optimize performance**
  - Review slow queries (use database query logs)
  - Identify bottlenecks
  - Adjust rate limits if needed

- [ ] **Cost analysis**
  - Total LLM costs for the week
  - Cost per listing extracted
  - Identify opportunities for optimization

## Monitoring Alert Thresholds

Configure alerts for the following conditions:

### Critical Alerts (Immediate Action Required)

- **Extraction failure rate > 10%**
  - Indicates system-wide issue
  - Action: Investigate logs, check API keys, verify database connectivity

- **Database connection failures**
  - Check database status
  - Action: Verify connection string, check database health, restart if needed

- **Disk space < 10% free**
  - Raw data files can fill disk
  - Action: Archive/delete old raw files, increase disk capacity

### Warning Alerts (Review Within 24 Hours)

- **LLM cost > £50/day**
  - May indicate runaway costs
  - Action: Review extraction volume, check for retry loops, verify cache hit rate

- **Failed extraction count > 100**
  - Large batch of failures
  - Action: Review error messages, identify common failure patterns

- **Field null rate > 70% for critical fields**
  - Data quality issue
  - Action: Review extraction prompts, check source data quality

- **Cache hit rate < 20%**
  - Not benefiting from caching
  - Action: Verify extraction_hash is being set, check for data variance

### Info Alerts (Review Weekly)

- **Merge conflicts detected**
  - Conflicting data from multiple sources
  - Action: Review conflicts, update trust hierarchy if needed

- **Unprocessed raw records > 1000**
  - Backlog building up
  - Action: Increase extraction frequency, scale processing capacity

## Rollback Plan

If deployment issues occur:

1. **Stop extraction processes**
   ```bash
   # Kill any running extraction jobs
   ps aux | grep "extraction.run" | awk '{print $2}' | xargs kill
   ```

2. **Rollback database migrations** (if schema changes were made)
   ```bash
   # Restore from backup taken before deployment
   # Or manually revert migrations (dangerous - test in staging first)
   ```

3. **Revert code changes**
   ```bash
   git checkout <previous-working-commit>
   pip install -r requirements.txt
   prisma generate
   ```

4. **Verify system health**
   ```bash
   python -m engine.extraction.health
   ```

5. **Document incident**
   - What failed
   - Root cause
   - Resolution steps taken
   - Preventive measures for future

## Production Optimization Opportunities

Post-deployment optimization tasks (non-blocking):

- [ ] **Implement async processing** (if extraction is slow)
  - Parallelize deterministic extractors
  - Use worker queues for high volume

- [ ] **Tune Pydantic validation** (if validation is slow)
  - Use compiled validators
  - Simplify complex validation rules

- [ ] **Add database read replicas** (if queries are slow)
  - Offload health checks to replica
  - Separate read and write workloads

- [ ] **Implement extraction scheduling** (for regular updates)
  - Cron jobs for periodic ingestion
  - Scheduled extraction of new raw data

## Support & Troubleshooting

### Key Documentation

- **Architecture**: `ARCHITECTURE.md`
- **Extraction Engine**: `docs/extraction_engine_overview.md`
- **CLI Reference**: `docs/extraction_cli_reference.md`
- **Troubleshooting**: `docs/troubleshooting_extraction.md`

### Common Issues

See `docs/troubleshooting_extraction.md` for detailed solutions to:

- Extraction failures
- LLM API errors
- Database connection issues
- Performance problems
- Data quality issues

### Emergency Contacts

- **Project Lead**: [Name/Email]
- **Database Admin**: [Name/Email]
- **API Provider Support**: Anthropic support (for LLM issues)

---

**Deployment Date**: _______________
**Deployed By**: _______________
**Version**: _______________
**Sign-off**: _______________
