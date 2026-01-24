# Extraction CLI Reference

Complete reference for the Data Extraction Engine CLI tools.

## Overview

The extraction engine provides three CLI scripts for transforming raw ingested data into structured, validated listings:

1. **`engine/extraction/run.py`** - Single record and per-source extraction
2. **`engine/extraction/run_all.py`** - Batch extraction of all unprocessed records
3. **`engine/extraction/health.py`** - Health dashboard and diagnostics

## Quick Start

```bash
# Extract a single record by ID (verbose output)
python -m engine.extraction.run --raw-id=<uuid>

# Extract all records from a specific source
python -m engine.extraction.run --source=google_places

# Extract all unprocessed records (batch mode)
python -m engine.extraction.run_all

# View health dashboard
python -m engine.extraction.health
```

## CLI Commands

### Single Record Extraction

Extract and display results for a single RawIngestion record.

```bash
python -m engine.extraction.run --raw-id=<uuid> [OPTIONS]
```

**Required:**
- `--raw-id=<uuid>` - ID of the RawIngestion record to extract

**Options:**
- `--verbose` - Display detailed field-by-field extraction results (default: True)
- `--quiet` - Minimal output, only show status (overrides --verbose)
- `--dry-run` - Simulate extraction without saving to database
- `--force-retry` - Re-extract even if already processed

**Examples:**

```bash
# Extract with verbose output
python -m engine.extraction.run --raw-id=abc123

# Extract with minimal output
python -m engine.extraction.run --raw-id=abc123 --quiet

# Test extraction without saving (dry run)
python -m engine.extraction.run --raw-id=abc123 --dry-run

# Re-extract an already processed record
python -m engine.extraction.run --raw-id=abc123 --force-retry
```

**Output (Verbose):**

```
================================================================================
EXTRACTION RESULT
================================================================================
Status:       SUCCESS
Raw ID:       abc123
Source:       google_places
Extracted ID: xyz789
Entity Type:  VENUE

--------------------------------------------------------------------------------
SCHEMA-DEFINED FIELDS
--------------------------------------------------------------------------------
  entity_name          = Game4Padel Edinburgh
  slug                 = game4padel-edinburgh
  latitude             = 55.953251
  longitude            = -3.188267
  ...

--------------------------------------------------------------------------------
DISCOVERED ATTRIBUTES
--------------------------------------------------------------------------------
  opening_hours        = {"monday": {"open": "09:00", "close": "22:00"}, ...}
  amenities            = ["parking", "changing_rooms", "cafe"]
  ...

--------------------------------------------------------------------------------
EXTERNAL IDs
--------------------------------------------------------------------------------
  google_places_id     = ChIJN1t_tDeuEmsRUsoyG83frY4
================================================================================
```

**Output (Quiet):**

```
✓ Extraction successful: xyz789
```

### Per-Source Batch Extraction

Extract all RawIngestion records from a specific source.

```bash
python -m engine.extraction.run --source=<source_name> [OPTIONS]
```

**Required:**
- `--source=<source_name>` - Source to extract from:
  - `google_places`
  - `sport_scotland`
  - `edinburgh_council`
  - `open_charge_map`
  - `serper`
  - `osm`

**Options:**
- `--limit=N` - Limit the number of records to process (for testing)
- `--dry-run` - Simulate extraction without saving to database
- `--force-retry` - Re-extract even if already processed

**Examples:**

```bash
# Extract all Google Places records
python -m engine.extraction.run --source=google_places

# Extract first 10 OSM records (for testing)
python -m engine.extraction.run --source=osm --limit=10

# Test extraction on Serper data without saving
python -m engine.extraction.run --source=serper --dry-run

# Re-extract all Sport Scotland records
python -m engine.extraction.run --source=sport_scotland --force-retry
```

**Output:**

```
================================================================================
BATCH EXTRACTION SUMMARY
================================================================================
Source:            google_places
Total Records:     127
✓ Successful:      125
✗ Failed:          2
⊙ Already Extracted: 0
Duration:          45.32s
Avg per record:    0.36s
LLM Calls:         0
Success Rate:      98.4%
================================================================================
```

### Batch All Extraction

Extract all unprocessed RawIngestion records, grouped by source.

```bash
python -m engine.extraction.run_all [OPTIONS]
```

**Options:**
- `--limit=N` - Limit total number of records to process (for testing)
- `--dry-run` - Simulate extraction without saving to database
- `--force-retry` - Re-extract even if already processed

**Examples:**

```bash
# Extract all unprocessed records
python -m engine.extraction.run_all

# Extract first 50 records across all sources (for testing)
python -m engine.extraction.run_all --limit=50

# Dry run to preview what would be extracted
python -m engine.extraction.run_all --dry-run --limit=10

# Re-extract everything
python -m engine.extraction.run_all --force-retry
```

**Output:**

```
Extracting google_places: 100%|████████████| 127/127 [00:45<00:00, 2.81record/s]
Extracting serper: 100%|█████████████████████| 43/43 [00:12<00:00, 3.58record/s]
Extracting osm: 100%|██████████████████████████| 89/89 [00:31<00:00, 2.87record/s]

================================================================================
BATCH ALL EXTRACTION SUMMARY
================================================================================
Total Records:       259
✓ Successful:        254
✗ Failed:            5
⊙ Already Extracted:  0
Duration:            88.45s
Avg per record:      0.34s
LLM Calls:           132
Estimated Cost:      $0.2640
Success Rate:        98.1%

--------------------------------------------------------------------------------
PER-SOURCE BREAKDOWN
--------------------------------------------------------------------------------

google_places:
  Total:      127
  ✓ Success:  125
  ✗ Failed:   2
  ⊙ Skipped:  0

serper:
  Total:      43
  ✓ Success:  42
  ✗ Failed:   1
  ⊙ Skipped:  0
  LLM Calls:  42
  Cost:       $0.0840

osm:
  Total:      89
  ✓ Success:  87
  ✗ Failed:   2
  ⊙ Skipped:  0
  LLM Calls:  87
  Cost:       $0.1740

================================================================================
```

### Health Dashboard

View extraction system health metrics and diagnostics.

```bash
python -m engine.extraction.health
```

**Output:**

```
================================================================================
EXTRACTION ENGINE HEALTH DASHBOARD
================================================================================

📊 RECORD STATUS
--------------------------------------------------------------------------------
Unprocessed Records:        127
Extracted Records:          1,234
Failed Extractions:         12
Quarantined Records:        5

⚡ SUCCESS RATES (by source)
--------------------------------------------------------------------------------
google_places:              98.4% (125/127)
sport_scotland:             100% (45/45)
edinburgh_council:          99.2% (124/125)
open_charge_map:            97.8% (44/45)
serper:                     95.3% (41/43)
osm:                        96.6% (86/89)

🔍 FIELD QUALITY
--------------------------------------------------------------------------------
Null Rate (entity_name):    0.2%  ✓
Null Rate (latitude):       1.4%  ✓
Null Rate (longitude):      1.4%  ✓
Null Rate (address):        8.7%  ⚠️
Null Rate (phone):          45.2% ⚠️

💰 LLM USAGE (last 30 days)
--------------------------------------------------------------------------------
Total Calls:                1,432
Total Cost:                 $2.86
Avg Cost per Call:          $0.002
Model:                      claude-3-haiku-20240307

🚨 RECENT FAILURES (last 10)
--------------------------------------------------------------------------------
[2026-01-15 14:32] serper | raw-id: abc123 | KeyError: 'organic'
[2026-01-15 12:18] osm | raw-id: def456 | Invalid coordinates
[2026-01-14 09:45] google_places | raw-id: ghi789 | Timeout

⚠️  MERGE CONFLICTS
--------------------------------------------------------------------------------
Unresolved Conflicts:       3

✅ OVERALL STATUS: HEALTHY
================================================================================
```

## CLI Flags Reference

### --dry-run

**Purpose:** Simulate extraction without making any database writes.

**Use Cases:**
- Test extraction logic on new data sources
- Preview extraction results before committing
- Debug extraction issues without creating records
- Estimate processing time and cost

**Behavior:**
- Reads RawIngestion records normally
- Performs full extraction and validation
- **Does not** create ExtractedListing records
- **Does not** record failed extractions to FailedExtraction table
- Displays `[DRY RUN]` marker in output
- Returns simulated extraction ID: `"dry-run-simulation"`

**Examples:**

```bash
# Preview extraction for a single record
python -m engine.extraction.run --raw-id=abc123 --dry-run

# Test batch extraction on first 10 records
python -m engine.extraction.run --source=serper --limit=10 --dry-run

# Estimate cost of processing all records
python -m engine.extraction.run_all --dry-run
```

### --force-retry

**Purpose:** Re-extract records that have already been processed.

**Use Cases:**
- Fix extraction after improving extractor logic
- Re-run extraction with updated LLM prompts
- Recover from incorrect extractions
- Refresh stale data

**Behavior:**
- Bypasses "already extracted" check
- Creates new ExtractedListing record (original remains)
- Useful for A/B testing extraction improvements
- Can be combined with `--dry-run` to test changes

**Examples:**

```bash
# Re-extract a single record
python -m engine.extraction.run --raw-id=abc123 --force-retry

# Re-extract all Google Places records
python -m engine.extraction.run --source=google_places --force-retry

# Test re-extraction without saving (dry run + force retry)
python -m engine.extraction.run --source=osm --limit=5 --dry-run --force-retry
```

**Note:** Using `--force-retry` without `--dry-run` will create duplicate ExtractedListing records. You may want to manually delete old records after verifying the new extraction is correct.

### --limit=N

**Purpose:** Limit the number of records processed (for testing).

**Use Cases:**
- Test extraction logic on a small sample
- Quick validation before full batch run
- Iterative development and debugging
- Cost control during experimentation

**Behavior:**
- Passed to `find_many()` as `take` parameter
- Limits total records queried from database
- Records are processed in `created_at` order (oldest first)
- Works with all extraction modes (single, source, batch all)

**Examples:**

```bash
# Extract first 5 Google Places records
python -m engine.extraction.run --source=google_places --limit=5

# Extract first 100 records across all sources
python -m engine.extraction.run_all --limit=100

# Test extraction on 10 records without saving
python -m engine.extraction.run --source=serper --limit=10 --dry-run
```

### --verbose / --quiet

**Purpose:** Control output verbosity (single record mode only).

**Behavior:**
- `--verbose` (default): Shows field-by-field extraction results
- `--quiet`: Shows only status line (success/failure)
- `--quiet` overrides `--verbose` if both are present
- Only applies to single record extraction (`--raw-id`)
- Batch modes always show summary report

**Examples:**

```bash
# Verbose output (default)
python -m engine.extraction.run --raw-id=abc123

# Quiet output
python -m engine.extraction.run --raw-id=abc123 --quiet

# Explicit verbose
python -m engine.extraction.run --raw-id=abc123 --verbose
```

## Flag Combinations

Flags can be combined for powerful workflows:

### Development & Testing

```bash
# Test extraction on 10 records without saving
python -m engine.extraction.run --source=google_places --limit=10 --dry-run

# Preview re-extraction without creating duplicates
python -m engine.extraction.run_all --limit=20 --dry-run --force-retry
```

### Production Re-extraction

```bash
# Re-extract all Serper data (after improving prompts)
python -m engine.extraction.run --source=serper --force-retry

# Re-extract first 100 records to verify improvements
python -m engine.extraction.run_all --limit=100 --force-retry
```

### Cost Estimation

```bash
# Estimate LLM cost for full extraction
python -m engine.extraction.run_all --dry-run

# Check summary report for "Estimated Cost" line
```

## Exit Codes

All CLI commands return standard exit codes:

- **0**: Success (all records processed successfully, or no records to process)
- **1**: Failure (some records failed, or database connection error)

**Note:** Partial success (some records succeeded, some failed) returns exit code 0 if at least one record succeeded.

## Environment Variables

The extraction engine respects the following environment variables:

- `DATABASE_URL` - Prisma database connection string
- `ANTHROPIC_API_KEY` - Required for LLM-based extractors (Serper, OSM)

## Common Workflows

### Initial Setup & Testing

```bash
# 1. Verify extraction works on sample data
python -m engine.extraction.run --source=google_places --limit=5 --dry-run

# 2. Extract sample data to database
python -m engine.extraction.run --source=google_places --limit=5

# 3. View health dashboard
python -m engine.extraction.health
```

### Full Production Extraction

```bash
# 1. Extract all unprocessed records
python -m engine.extraction.run_all

# 2. Check health dashboard for issues
python -m engine.extraction.health

# 3. Retry any failed extractions (manual intervention)
python -m engine.extraction.run --raw-id=<failed_id> --verbose
```

### Improving Extractors

```bash
# 1. Test improved extractor on sample (dry run)
python -m engine.extraction.run --source=serper --limit=10 --dry-run --force-retry

# 2. Compare results (check verbose output)
python -m engine.extraction.run --raw-id=<test_id> --dry-run --force-retry --verbose

# 3. Re-extract all records with improved extractor
python -m engine.extraction.run --source=serper --force-retry
```

### Debugging Failed Extractions

```bash
# 1. View health dashboard to identify failures
python -m engine.extraction.health

# 2. Extract failed record with verbose output
python -m engine.extraction.run --raw-id=<failed_id> --verbose

# 3. Fix extractor code based on error

# 4. Re-extract to verify fix
python -m engine.extraction.run --raw-id=<failed_id> --force-retry
```

## Performance Tips

1. **Batch by source**: Use `--source` for better progress tracking and error isolation
2. **Use --limit for testing**: Always test with `--limit` before full batch runs
3. **Monitor LLM costs**: Use `--dry-run` to estimate costs before expensive operations
4. **Parallelize manually**: Run multiple source extractions in parallel terminals:
   ```bash
   # Terminal 1
   python -m engine.extraction.run --source=google_places

   # Terminal 2
   python -m engine.extraction.run --source=serper

   # Terminal 3
   python -m engine.extraction.run --source=osm
   ```

## Troubleshooting

### "No records found"

**Cause:** No unprocessed RawIngestion records for the specified source.

**Solution:**
- Run ingestion first: `python -m engine.ingestion.run --source=<source>`
- Check if records already extracted (use `--force-retry` to re-extract)

### "ExtractedListing already exists"

**Cause:** Record has already been extracted (not an error).

**Solution:**
- Use `--force-retry` to re-extract
- Or skip the record (it's already processed)

### High failure rate

**Cause:** Raw data format changed, or extractor needs improvement.

**Solution:**
1. Check failed record details: `python -m engine.extraction.run --raw-id=<failed_id> --verbose`
2. Inspect raw data file: `cat <file_path>`
3. Update extractor to handle new data format
4. Re-extract: `python -m engine.extraction.run --raw-id=<failed_id> --force-retry`

### LLM timeout or rate limit

**Cause:** Anthropic API rate limits or network issues.

**Solution:**
- Retry failed extractions later (they're automatically quarantined)
- Reduce batch size with `--limit`
- Check `ANTHROPIC_API_KEY` environment variable

## See Also

- [Extraction Engine Overview](extraction_engine_overview.md) - Architecture and design
- [Adding New Extractors](adding_new_extractor.md) - Step-by-step guide
- [Troubleshooting Guide](troubleshooting_extraction.md) - Common issues and solutions
