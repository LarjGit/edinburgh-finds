# Extraction Engine CLI Reference

## Table of Contents

1. [Overview](#overview)
2. [Command Index](#command-index)
3. [Core Extraction Commands](#core-extraction-commands)
4. [Monitoring & Diagnostics](#monitoring--diagnostics)
5. [Maintenance Commands](#maintenance-commands)
6. [Common Workflows](#common-workflows)
7. [Environment Variables](#environment-variables)
8. [Exit Codes](#exit-codes)

---

## Overview

The extraction engine provides several CLI tools for running extractions, monitoring health, managing costs, and maintaining the system. All commands are run from the project root directory.

**Prerequisites:**
- Python environment activated
- Database accessible (SQLite/PostgreSQL)
- Raw data ingested (`RawIngestion` table populated)

---

## Command Index

| Command | Purpose | Typical Use |
|---------|---------|-------------|
| **`run.py`** | Run extraction workflows | Single record, per-source, or batch extraction |
| **`run_all.py`** | Batch extract all unprocessed | Production batch processing |
| **`health.py`** | View health dashboard | Monitor extraction status & quality |
| **`cost_report.py`** | View LLM usage & costs | Track AI spending |
| **`cli.py`** | Maintenance tasks | Retry failed extractions |

---

## Core Extraction Commands

### 1. Single Record Extraction

Extract a single `RawIngestion` record by ID.

**Command:**
```bash
python -m engine.extraction.run --raw-id=<UUID> [--verbose] [--dry-run] [--force-retry]
```

**Arguments:**
- `--raw-id=<UUID>` **(required)**: ID of the `RawIngestion` record to extract
- `--verbose`: Display field-by-field extraction results (optional)
- `--dry-run`: Simulate extraction without saving to database (optional)
- `--force-retry`: Re-extract even if already processed (optional)

**Example:**
```bash
# Extract a single Google Places record
python -m engine.extraction.run --raw-id=clx123abc456 --verbose

# Dry-run extraction to preview results
python -m engine.extraction.run --raw-id=clx123abc456 --dry-run
```

**Output:**
```
[INFO] Starting single record extraction for raw_id: clx123abc456
[INFO] Found RawIngestion record: source=google_places, status=success
[INFO] Using extractor: GooglePlacesExtractor
[SUCCESS] Extracted 18 fields from record clx123abc456

Fields Extracted:
  entity_name: Game4Padel Edinburgh
  latitude: 55.9533
  longitude: -3.1883
  phone: +441315397071
  postcode: EH12 9GR
  ...

Discovered Attributes:
  has_sauna: true
  parking_available: true
  ...
```

**Use Cases:**
- **Debugging**: Test extraction logic on specific records
- **Verification**: Manually inspect extraction output before batch processing
- **Development**: Test new extractors with sample data

---

### 2. Per-Source Batch Extraction

Extract all unprocessed records from a specific source.

**Command:**
```bash
python -m engine.extraction.run --source=<source_name> [--limit=N] [--dry-run] [--force-retry]
```

**Arguments:**
- `--source=<source_name>` **(required)**: Source name (e.g., `google_places`, `osm`, `serper`)
- `--limit=N`: Process only first N records (optional, for testing)
- `--dry-run`: Simulate extraction without saving to database (optional)
- `--force-retry`: Re-extract even if already processed (optional)

**Available Sources:**
- `google_places`
- `sport_scotland`
- `edinburgh_council`
- `open_charge_map`
- `serper`
- `osm`

**Example:**
```bash
# Extract all Google Places records
python -m engine.extraction.run --source=google_places

# Extract first 10 OSM records (testing)
python -m engine.extraction.run --source=osm --limit=10

# Dry-run extraction for Serper (preview without saving)
python -m engine.extraction.run --source=serper --limit=5 --dry-run

# Force re-extract all Sport Scotland records
python -m engine.extraction.run --source=sport_scotland --force-retry
```

**Output:**
```
[INFO] Starting per-source extraction: google_places
[INFO] Found 42 unprocessed records
[INFO] Processing with limit: 10

Extraction Progress:
100%|████████████████████████████████████████| 10/10 [00:08<00:00,  1.23 records/s]

Summary Report - google_places:
  Total Processed: 10
  Successful: 10
  Failed: 0
  Success Rate: 100.00%
  Duration: 8.2s
  Records/min: 73.2
  Fields/record (avg): 16.3
  LLM Cost: £0.00 (deterministic extractor)
```

**Use Cases:**
- **Source-specific processing**: Extract data from one source at a time
- **Testing new sources**: Validate new extractor with `--limit`
- **Reprocessing**: Re-extract after fixing extractor bugs with `--force-retry`

---

### 3. Batch All Unprocessed Records

Extract all unprocessed records from all sources (production workflow).

**Command:**
```bash
python -m engine.extraction.run_all [--limit=N] [--dry-run] [--force-retry]
```

**Arguments:**
- `--limit=N`: Process only first N records total (optional, for testing)
- `--dry-run`: Simulate extraction without saving to database (optional)
- `--force-retry`: Re-extract even if already processed (optional)

**Example:**
```bash
# Extract all unprocessed records (production)
python -m engine.extraction.run_all

# Test with first 20 records
python -m engine.extraction.run_all --limit=20

# Dry-run to estimate LLM costs
python -m engine.extraction.run_all --limit=100 --dry-run
```

**Output:**
```
[INFO] Starting batch all extraction
[INFO] Found 247 unprocessed records across 6 sources

Processing by source:
  google_places: 85 records
  sport_scotland: 42 records
  edinburgh_council: 63 records
  open_charge_map: 12 records
  serper: 28 records
  osm: 17 records

Extraction Progress:
100%|████████████████████████████████████████| 247/247 [03:42<00:00,  1.11 records/s]

Overall Summary:
  Total Processed: 247
  Successful: 238
  Failed: 9
  Success Rate: 96.36%
  Duration: 3m 42s
  Records/min: 66.7
  Fields/record (avg): 14.8
  LLM Cost: £0.42 (28 LLM calls)

Failed Records: 9 (quarantined for retry)
  serper: 5 failures (LLM timeout)
  osm: 4 failures (missing required fields)

Run 'python -m engine.extraction.cli --retry-failed' to retry quarantined records.
```

**Use Cases:**
- **Production batch processing**: Main workflow for extracting all ingested data
- **Overnight jobs**: Process large batches unattended
- **Cost estimation**: Use `--dry-run --limit` to estimate LLM costs before full run

---

## Monitoring & Diagnostics

### 4. Health Dashboard

View extraction health metrics and system status.

**Command:**
```bash
python -m engine.extraction.health [--no-color]
```

**Arguments:**
- `--no-color`: Disable color output (optional, for logs/CI)

**Example:**
```bash
# View health dashboard with color
python -m engine.extraction.health

# Plain output (for logging)
python -m engine.extraction.health --no-color
```

**Output:**
```
╔══════════════════════════════════════════════════════════════╗
║           EXTRACTION ENGINE HEALTH DASHBOARD                  ║
╚══════════════════════════════════════════════════════════════╝

Generated: 2026-01-17 14:32:15

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OVERALL STATUS: ✓ HEALTHY

Unprocessed Records: 0
Quarantined (Failed): 2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PER-SOURCE METRICS

┌─────────────────────┬──────────┬──────────┬──────────┬────────────┐
│ Source              │ Processed│ Success  │ Failed   │ Success %  │
├─────────────────────┼──────────┼──────────┼──────────┼────────────┤
│ google_places       │ 85       │ 85       │ 0        │ ✓ 100.00%  │
│ sport_scotland      │ 42       │ 42       │ 0        │ ✓ 100.00%  │
│ edinburgh_council   │ 63       │ 63       │ 0        │ ✓ 100.00%  │
│ open_charge_map     │ 12       │ 12       │ 0        │ ✓ 100.00%  │
│ serper              │ 28       │ 26       │ 2        │ ⚠ 92.86%   │
│ osm                 │ 17       │ 17       │ 0        │ ✓ 100.00%  │
└─────────────────────┴──────────┴──────────┴──────────┴────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIELD NULL RATES (Average across all extractions)

┌─────────────────────┬──────────────┬──────────┐
│ Field               │ Null Rate    │ Status   │
├─────────────────────┼──────────────┼──────────┤
│ entity_name         │ 0.00%        │ ✓ Good   │
│ latitude            │ 0.00%        │ ✓ Good   │
│ longitude           │ 0.00%        │ ✓ Good   │
│ phone               │ 34.12%       │ ✓ OK     │
│ postcode            │ 18.45%       │ ✓ Good   │
│ email               │ 67.23%       │ ⚠ High   │
│ website_url         │ 22.34%       │ ✓ Good   │
│ opening_hours       │ 41.56%       │ ⚠ Fair   │
└─────────────────────┴──────────────┴──────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECENT FAILURES (Last 10)

┌──────────────┬──────────┬────────────────────┬────────────────────┐
│ Source       │ Record ID│ Error              │ Time               │
├──────────────┼──────────┼────────────────────┼────────────────────┤
│ serper       │ clx789...│ LLM timeout        │ 2026-01-17 14:15   │
│ serper       │ clx456...│ Invalid JSON       │ 2026-01-17 14:12   │
└──────────────┴──────────┴────────────────────┴────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LLM USAGE & COST

Total LLM Calls: 45
Total Input Tokens: 127,450
Total Output Tokens: 34,220
Estimated Cost: £0.68

Average per call:
  Input Tokens: 2,832
  Output Tokens: 760
  Cost: £0.015

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MERGE CONFLICTS

Total Conflicts: 3

┌──────────────┬──────────────┬──────────────────┬──────────────────┐
│ Listing      │ Field        │ Conflict         │ Resolution       │
├──────────────┼──────────────┼──────────────────┼──────────────────┤
│ Game4Padel   │ phone        │ +4413... vs +... │ Google wins (T70)│
│ Portobello   │ opening_hours│ {...} vs {...}   │ Manual review    │
│ Arthur's Seat│ postcode     │ EH12 vs EH12 9GR │ Council wins(T85)│
└──────────────┴──────────────┴──────────────────┴──────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDATIONS

✓ All sources performing well
⚠ Email field has high null rate (67%) - consider additional sources
⚠ 2 serper failures - review LLM timeout settings
```

**Use Cases:**
- **Daily monitoring**: Check system health before production runs
- **Quality assurance**: Identify fields with poor data quality
- **Cost tracking**: Monitor LLM spending
- **Debugging**: Find recent failures and patterns

---

### 5. LLM Cost Report

View detailed LLM usage and cost breakdown.

**Command:**
```bash
python -m engine.extraction.cost_report [--reset]
```

**Arguments:**
- `--reset`: Reset usage tracker after displaying report (optional)

**Example:**
```bash
# View cost report
python -m engine.extraction.cost_report

# View and reset tracker
python -m engine.extraction.cost_report --reset
```

**Output:**
```
╔══════════════════════════════════════════════════════════════╗
║                  LLM USAGE & COST REPORT                      ║
╚══════════════════════════════════════════════════════════════╝

Tracking Period: 2026-01-17 09:00:00 - 2026-01-17 14:32:15
Model: claude-haiku-20250318

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OVERALL USAGE

Total Calls: 45
Total Input Tokens: 127,450
Total Output Tokens: 34,220
Total Tokens: 161,670

Estimated Cost: £0.68

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USAGE BY SOURCE

┌─────────────────────┬────────┬──────────────┬───────────────┬──────────┐
│ Source              │ Calls  │ Input Tokens │ Output Tokens │ Cost (£) │
├─────────────────────┼────────┼──────────────┼───────────────┼──────────┤
│ serper              │ 28     │ 89,340       │ 21,450        │ £0.46    │
│ osm                 │ 17     │ 38,110       │ 12,770        │ £0.22    │
└─────────────────────┴────────┴──────────────┴───────────────┴──────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AVERAGES PER CALL

Input Tokens: 2,832
Output Tokens: 760
Total Tokens: 3,592
Cost: £0.015

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COST PROJECTIONS

At current rate (3,592 tokens/call):

┌──────────────┬────────────────┬──────────────┐
│ Volume       │ Total Calls    │ Estimated £  │
├──────────────┼────────────────┼──────────────┤
│ 100 records  │ ~40            │ £0.60        │
│ 1,000 records│ ~400           │ £6.00        │
│ 10,000 rec.  │ ~4,000         │ £60.00       │
└──────────────┴────────────────┴──────────────┘

Note: Only LLM-based sources (serper, osm) incur costs.
Deterministic sources (google_places, sport_scotland, etc.) are free.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COST OPTIMIZATION TIPS

✓ Use Haiku model (cheapest: ~£0.25 per 1M tokens)
✓ Implement caching (Phase 10) - reduces costs by 30-50%
✓ Batch deterministic sources first (zero cost)
✓ Use --limit flag for testing before full runs
```

**Use Cases:**
- **Budget tracking**: Monitor AI spending against budget
- **Cost forecasting**: Estimate costs for large batch runs
- **Optimization**: Identify sources with high token usage

---

## Maintenance Commands

### 6. Retry Failed Extractions

Retry records in the quarantine (FailedExtraction table).

**Command:**
```bash
python -m engine.extraction.cli --retry-failed [--max-retries=N] [--limit=N]
```

**Arguments:**
- `--retry-failed` **(required)**: Enable retry mode
- `--max-retries=N`: Maximum retry attempts before skipping (default: 3)
- `--limit=N`: Limit number of failed records to retry (optional)

**Example:**
```bash
# Retry all failed extractions
python -m engine.extraction.cli --retry-failed

# Retry with custom max retries
python -m engine.extraction.cli --retry-failed --max-retries=5

# Retry only first 10 failures (testing)
python -m engine.extraction.cli --retry-failed --limit=10
```

**Output:**
```
[INFO] Starting failed extraction retry
[INFO] Found 9 quarantined records

Retry Progress:
100%|████████████████████████████████████████| 9/9 [00:12<00:00,  0.75 records/s]

Retry Summary:
  Retried:   9
  Succeeded: 7
  Failed:    2

Successfully recovered:
  serper (clx789...): ✓ Retry 2 successful
  serper (clx456...): ✓ Retry 1 successful
  osm (clx234...): ✓ Retry 1 successful
  ...

Still failing (exceeded max retries):
  serper (clx999...): ✗ Failed after 3 retries (LLM timeout)
  osm (clx888...): ✗ Failed after 3 retries (missing coordinates)
```

**Use Cases:**
- **Transient failure recovery**: Retry network errors, rate limits, temporary API issues
- **Post-fix reprocessing**: Retry after fixing extractor bugs
- **Incremental improvement**: Gradually reduce quarantine queue

---

## Common Workflows

### Workflow 1: Daily Production Run

**Scenario:** Extract all new data ingested overnight

```bash
# Step 1: Check health before starting
python -m engine.extraction.health

# Step 2: Run batch extraction
python -m engine.extraction.run_all

# Step 3: Retry any failures
python -m engine.extraction.cli --retry-failed

# Step 4: Check final health status
python -m engine.extraction.health

# Step 5: View LLM costs
python -m engine.extraction.cost_report
```

---

### Workflow 2: Testing New Extractor

**Scenario:** You've added a new `strava` extractor and want to test it

```bash
# Step 1: Dry-run single record
python -m engine.extraction.run --source=strava --limit=1 --dry-run --verbose

# Step 2: Dry-run small batch
python -m engine.extraction.run --source=strava --limit=5 --dry-run

# Step 3: Real extraction (small batch)
python -m engine.extraction.run --source=strava --limit=10

# Step 4: Check results in health dashboard
python -m engine.extraction.health

# Step 5: If successful, extract all
python -m engine.extraction.run --source=strava
```

---

### Workflow 3: Debugging Failed Extraction

**Scenario:** A specific record is failing extraction

```bash
# Step 1: Extract single record with verbose output
python -m engine.extraction.run --raw-id=clx123abc456 --verbose

# Step 2: If it fails, check error in logs
tail -f logs/extraction.log

# Step 3: Fix extractor code

# Step 4: Force retry the record
python -m engine.extraction.run --raw-id=clx123abc456 --force-retry --verbose

# Step 5: Verify success
python -m engine.extraction.health
```

---

### Workflow 4: Reprocessing After Extractor Update

**Scenario:** You've fixed a bug in the Google Places extractor and want to re-extract all records

```bash
# Step 1: Preview impact (dry-run)
python -m engine.extraction.run --source=google_places --limit=5 --dry-run --force-retry

# Step 2: Re-extract all Google Places records
python -m engine.extraction.run --source=google_places --force-retry

# Step 3: Verify improvements
python -m engine.extraction.health
```

---

### Workflow 5: Cost Estimation for Large Batch

**Scenario:** You want to estimate LLM costs before processing 10,000 records

```bash
# Step 1: Reset cost tracker
python -m engine.extraction.cost_report --reset

# Step 2: Dry-run sample (1% of total)
python -m engine.extraction.run_all --limit=100 --dry-run

# Step 3: View cost report with projections
python -m engine.extraction.cost_report

# Output will show: "1,000 records: £X", "10,000 records: £Y"
```

---

## Environment Variables

### Optional Environment Variables

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `DATABASE_URL` | Database connection string | `file:./prisma/dev.db` | `postgresql://user:pass@localhost:5432/db` |
| `ANTHROPIC_API_KEY` | Anthropic API key for LLM extraction | (required for LLM sources) | `sk-ant-api03-...` |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG`, `WARNING`, `ERROR` |

**Setting Environment Variables:**

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-api03-..."
$env:LOG_LEVEL = "DEBUG"
```

**Linux/macOS (Bash):**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export LOG_LEVEL="DEBUG"
```

**Persistent (`.env` file):**
```bash
# .env file in project root
DATABASE_URL="postgresql://user:pass@localhost:5432/edinburgh_finds"
ANTHROPIC_API_KEY="sk-ant-api03-..."
LOG_LEVEL="INFO"
```

---

## Exit Codes

All CLI commands return standard exit codes:

| Code | Meaning | When It Happens |
|------|---------|-----------------|
| **0** | Success | All operations completed successfully |
| **1** | Error | Database connection failed, invalid arguments, or extraction failures |

**Examples:**

```bash
# Success (exit code 0)
python -m engine.extraction.run --source=google_places
echo $?  # Outputs: 0

# Error (exit code 1)
python -m engine.extraction.run --source=invalid_source
echo $?  # Outputs: 1
```

**Use in Scripts:**

```bash
#!/bin/bash

# Run extraction and check exit code
python -m engine.extraction.run_all

if [ $? -eq 0 ]; then
    echo "Extraction successful"
    python -m engine.extraction.cost_report --reset
else
    echo "Extraction failed, retrying quarantined records"
    python -m engine.extraction.cli --retry-failed
fi
```

---

## Quick Reference Card

### Most Common Commands

```bash
# Extract all unprocessed (main workflow)
python -m engine.extraction.run_all

# Extract specific source
python -m engine.extraction.run --source=google_places

# Check system health
python -m engine.extraction.health

# Retry failures
python -m engine.extraction.cli --retry-failed

# View costs
python -m engine.extraction.cost_report
```

### Testing & Debugging

```bash
# Test single record
python -m engine.extraction.run --raw-id=<UUID> --verbose

# Dry-run (preview without saving)
python -m engine.extraction.run --source=<source> --limit=5 --dry-run

# Force re-extract
python -m engine.extraction.run --source=<source> --force-retry
```

### Flags Quick Reference

| Flag | Effect |
|------|--------|
| `--verbose` | Show detailed field-by-field output |
| `--dry-run` | Preview results without saving |
| `--force-retry` | Re-extract even if already processed |
| `--limit=N` | Process only first N records |
| `--no-color` | Disable colored output |
| `--reset` | Reset usage tracker (cost report) |

---

## Next Steps

**For Developers:**
- Read **[Extraction Engine Overview](./extraction_engine_overview.md)** for architecture
- Read **[Adding a New Extractor](./adding_new_extractor.md)** to extend sources
- Read **[Troubleshooting Guide](./troubleshooting_extraction.md)** when issues arise

**For DevOps:**
- Set up cron jobs for daily `run_all` execution
- Configure monitoring alerts based on `health` output
- Implement cost budgets using `cost_report` data

**For Data Analysts:**
- Query `ExtractedListing` table for extraction history
- Analyze `field_confidence` scores for data quality
- Review `FailedExtraction` patterns for source reliability

---

**Document Version:** 1.0
**Last Updated:** 2026-01-17
**Maintained By:** Data Extraction Engine Team
