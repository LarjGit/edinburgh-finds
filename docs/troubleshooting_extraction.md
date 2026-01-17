# Troubleshooting Extraction Engine - Common Errors & Solutions

## Table of Contents

1. [Diagnostic Strategy](#diagnostic-strategy)
2. [Database Errors](#database-errors)
3. [Extractor Errors](#extractor-errors)
4. [LLM Errors](#llm-errors)
5. [Data Quality Issues](#data-quality-issues)
6. [Performance Issues](#performance-issues)
7. [Configuration Errors](#configuration-errors)
8. [Testing & Debugging Tips](#testing--debugging-tips)

---

## Diagnostic Strategy

When encountering extraction issues, follow this systematic approach:

### Step 1: Isolate the Problem

```bash
# Test single record to isolate issue
python -m engine.extraction.run --raw-id=<failing_record_id> --verbose

# Check health dashboard for patterns
python -m engine.extraction.health
```

### Step 2: Check Logs

```bash
# View extraction logs (last 50 lines)
tail -n 50 logs/extraction.log

# Search for specific error
grep "ERROR" logs/extraction.log

# Follow logs in real-time
tail -f logs/extraction.log
```

### Step 3: Verify Prerequisites

```bash
# Check database connection
python -c "from prisma import Prisma; import asyncio; asyncio.run(Prisma().connect())"

# Check raw data exists
python -c "from prisma import Prisma; import asyncio; db = Prisma(); asyncio.run(db.connect()); print(asyncio.run(db.rawingestion.count()))"

# Check environment variables
echo $ANTHROPIC_API_KEY  # (should show key, not empty)
echo $DATABASE_URL       # (should show connection string)
```

### Step 4: Run Tests

```bash
# Run extractor tests to verify code is working
pytest engine/extraction/tests -v

# Run specific extractor test
pytest engine/extraction/tests/test_google_places_extractor.py -v
```

---

## Database Errors

### Error 1: Database Connection Failed

**Symptoms:**
```
ERROR: Database connection failed: Can't reach database server at `localhost:5432`
```

**Causes:**
- Database not running
- Incorrect `DATABASE_URL` environment variable
- Network connectivity issue

**Solutions:**

**Check if database is running:**
```bash
# For PostgreSQL
pg_isready -h localhost -p 5432

# For SQLite (check file exists)
ls -la prisma/dev.db
```

**Verify DATABASE_URL:**
```bash
# Print current DATABASE_URL
echo $DATABASE_URL

# Should be one of:
# SQLite: file:./prisma/dev.db
# PostgreSQL: postgresql://user:pass@localhost:5432/edinburgh_finds
```

**Fix:**
```bash
# Set correct DATABASE_URL
export DATABASE_URL="file:./prisma/dev.db"  # SQLite
# OR
export DATABASE_URL="postgresql://user:pass@localhost:5432/edinburgh_finds"  # PostgreSQL

# Verify connection works
python -m engine.extraction.health
```

---

### Error 2: RawIngestion Record Not Found

**Symptoms:**
```
ERROR: RawIngestion record not found: clx123abc456
```

**Causes:**
- Incorrect record ID
- Record was deleted
- Data not yet ingested

**Solutions:**

**List available raw ingestion records:**
```bash
# Query database for raw records
python -c "
from prisma import Prisma
import asyncio

async def list_raw():
    db = Prisma()
    await db.connect()
    records = await db.rawingestion.find_many(take=10, order={'created_at': 'desc'})
    for r in records:
        print(f'{r.id} | {r.source} | {r.status}')
    await db.disconnect()

asyncio.run(list_raw())
"
```

**Run ingestion first if no records:**
```bash
# Run ingestion for a source
python -m engine.ingestion.run --source=google_places --limit=10
```

---

### Error 3: ExtractedListing Already Exists

**Symptoms:**
```
INFO: Record already extracted: clx789def456
```

**Causes:**
- Record was previously extracted
- Not using `--force-retry` flag

**Solutions:**

**Force re-extraction:**
```bash
python -m engine.extraction.run --raw-id=clx123abc456 --force-retry
```

**Or batch re-extract source:**
```bash
python -m engine.extraction.run --source=google_places --force-retry
```

---

## Extractor Errors

### Error 4: No Extractor Found for Source

**Symptoms:**
```
ERROR: No extractor found for source: strava
Available sources: google_places, sport_scotland, edinburgh_council, ...
```

**Causes:**
- Source name mismatch between `RawIngestion.source` and `EXTRACTOR_MAP`
- Extractor not registered in `run.py`

**Solutions:**

**Check source name in database:**
```bash
# Verify source name in RawIngestion
python -c "
from prisma import Prisma
import asyncio

async def check_sources():
    db = Prisma()
    await db.connect()
    sources = await db.rawingestion.group_by(by=['source'], _count=True)
    for s in sources:
        print(f'{s[\"source\"]}: {s[\"_count\"]} records')
    await db.disconnect()

asyncio.run(check_sources())
"
```

**Register extractor in `run.py`:**

Edit `engine/extraction/run.py`:
```python
from engine.extraction.extractors.strava_extractor import StravaExtractor

extractors = {
    "google_places": GooglePlacesExtractor,
    # ... existing extractors
    "strava": StravaExtractor,  # ADD THIS
}
```

**Ensure source names match exactly:**
- `RawIngestion.source = "strava"`
- `extractor.source_name = "strava"`
- `EXTRACTOR_MAP["strava"]`

---

### Error 5: Failed to Load Raw Data from File

**Symptoms:**
```
ERROR: Failed to load raw data from data/raw_ingestion/google_places/clx123.json: FileNotFoundError
```

**Causes:**
- Raw data file was deleted or moved
- File path in `RawIngestion.file_path` is incorrect
- Permissions issue

**Solutions:**

**Check if file exists:**
```bash
# Verify file at path
ls -la data/raw_ingestion/google_places/clx123.json
```

**Verify file_path in database:**
```bash
# Query database for file path
python -c "
from prisma import Prisma
import asyncio

async def check_path():
    db = Prisma()
    await db.connect()
    raw = await db.rawingestion.find_first(where={'id': 'clx123abc456'})
    print(f'File path: {raw.file_path}')
    await db.disconnect()

asyncio.run(check_path())
"
```

**Fix: Re-ingest data if file is missing:**
```bash
python -m engine.ingestion.run --source=google_places --limit=10
```

---

### Error 6: KeyError or AttributeError in extract()

**Symptoms:**
```
ERROR: KeyError: 'displayName' in google_places_extractor.py line 45
```

**Causes:**
- Raw data format changed (API update)
- Missing optional field accessed without `.get()`
- Fixture data doesn't match real data

**Solutions:**

**Use `.get()` for optional fields:**

**Bad:**
```python
extracted["phone"] = raw_data["contact"]["phone"]  # Crashes if missing!
```

**Good:**
```python
extracted["phone"] = raw_data.get("contact", {}).get("phone")  # Returns None if missing
```

**Inspect actual raw data:**
```bash
# View raw data for failing record
python -c "
import json
from pathlib import Path

# Replace with actual file path from error message
file_path = Path('data/raw_ingestion/google_places/clx123.json')
with open(file_path, 'r') as f:
    data = json.load(f)
    print(json.dumps(data, indent=2))
"
```

**Update extractor to handle new format:**
```python
# Old format
extracted["entity_name"] = raw_data["displayName"]["text"]

# New format (defensive)
display_name = raw_data.get("displayName", {})
if isinstance(display_name, dict):
    extracted["entity_name"] = display_name.get("text")
elif isinstance(display_name, str):
    extracted["entity_name"] = display_name
else:
    extracted["entity_name"] = None
```

---

### Error 7: Validation Failure (Invalid Data)

**Symptoms:**
```
ERROR: Validation failed: latitude 91.5 exceeds valid range (-90 to 90)
```

**Causes:**
- Source provides invalid data
- Data needs normalization

**Solutions:**

**Add validation in `validate()` method:**
```python
def validate(self, extracted: Dict) -> Dict:
    validated = extracted.copy()

    # Validate latitude
    if "latitude" in validated and validated["latitude"]:
        lat = validated["latitude"]
        if not (-90 <= lat <= 90):
            logger.warning(f"Invalid latitude {lat}, setting to None")
            validated["latitude"] = None

    # Validate longitude
    if "longitude" in validated and validated["longitude"]:
        lng = validated["longitude"]
        if not (-180 <= lng <= 180):
            logger.warning(f"Invalid longitude {lng}, setting to None")
            validated["longitude"] = None

    return validated
```

**Handle corrupted data gracefully:**
```python
# Set invalid data to None instead of crashing
try:
    lat = float(raw_data["location"]["lat"])
    if -90 <= lat <= 90:
        extracted["latitude"] = lat
    else:
        extracted["latitude"] = None
except (KeyError, ValueError, TypeError):
    extracted["latitude"] = None
```

---

## LLM Errors

### Error 8: Anthropic API Key Missing

**Symptoms:**
```
ERROR: Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.
```

**Causes:**
- `ANTHROPIC_API_KEY` not set
- API key incorrectly formatted

**Solutions:**

**Set API key:**
```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-api03-..."

# Linux/macOS
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Or add to .env file
echo 'ANTHROPIC_API_KEY="sk-ant-api03-..."' >> .env
```

**Verify key is set:**
```bash
echo $ANTHROPIC_API_KEY  # Should output your key
```

**Test API connection:**
```bash
python -c "
from anthropic import Anthropic
client = Anthropic()
print('API key valid!')
"
```

---

### Error 9: LLM Timeout

**Symptoms:**
```
ERROR: LLM timeout: Request exceeded 30s timeout
```

**Causes:**
- Slow API response
- Large prompt (too many tokens)
- Network latency

**Solutions:**

**Increase timeout (in `llm_client.py`):**
```python
# Current timeout
response = client.messages.create(
    model="claude-haiku-20250318",
    max_tokens=2000,
    timeout=30.0,  # Increase this
    messages=[...]
)

# Increase to 60s
response = client.messages.create(
    model="claude-haiku-20250318",
    max_tokens=2000,
    timeout=60.0,  # Increased
    messages=[...]
)
```

**Reduce prompt size:**
```python
# Trim input text if too long
def _build_prompt(self, raw_data: Dict) -> str:
    description = raw_data.get("description", "")

    # Trim to 2000 characters
    if len(description) > 2000:
        description = description[:2000] + "... [truncated]"

    prompt = f"Extract data from: {description}"
    return prompt
```

**Retry failed extractions later:**
```bash
# Timeouts often succeed on retry
python -m engine.extraction.cli --retry-failed
```

---

### Error 10: LLM Returns Invalid JSON

**Symptoms:**
```
ERROR: Pydantic validation error: field required (entity_name)
```

**Causes:**
- LLM didn't follow schema
- Prompt unclear
- Model hallucination

**Solutions:**

**Enable retries with validation feedback (already implemented):**
```python
# In llm_client.py - instructor already handles this
result = client.chat.completions.create(
    model="claude-haiku-20250318",
    messages=[{"role": "user", "content": prompt}],
    response_model=VenueExtraction,  # Pydantic model enforces schema
    max_retries=2  # Retry up to 2 times with validation feedback
)
```

**Improve prompt clarity:**

**Bad prompt:**
```
Extract data from this text.
```

**Good prompt:**
```
Extract venue information from the text below.

IMPORTANT: Follow these rules strictly:
- entity_name: Required, the venue's name
- latitude/longitude: Required, WGS84 coordinates
- phone: Optional, E.164 format (+44...)
- If a field is unknown, use null (not "unknown" or "N/A")

Text: {description}
```

**Check prompt template:**
```bash
# View prompt template
cat engine/extraction/prompts/serper_extraction.txt
```

---

### Error 11: LLM Cost Exceeds Budget

**Symptoms:**
```
WARNING: LLM cost £12.50 exceeds daily budget of £10.00
```

**Causes:**
- High volume of LLM extractions
- Using expensive model (Opus instead of Haiku)
- No caching implemented

**Solutions:**

**Switch to cheaper model:**

Edit `engine/config/extraction.yaml`:
```yaml
llm:
  model: "claude-haiku-20250318"  # Cheapest: ~£0.25 per 1M tokens
  # NOT: "claude-opus-4-5-20251101"  # Expensive: ~£15 per 1M tokens
```

**Implement caching (Phase 10 task):**
```python
# Planned feature: Check cache before calling LLM
cache_key = hash(raw_data)
if cache_key in extraction_cache:
    return extraction_cache[cache_key]

# Call LLM
result = llm_client.extract(...)

# Cache result
extraction_cache[cache_key] = result
return result
```

**Batch deterministic sources first (zero cost):**
```bash
# Extract free sources first
python -m engine.extraction.run --source=google_places
python -m engine.extraction.run --source=sport_scotland
python -m engine.extraction.run --source=edinburgh_council
python -m engine.extraction.run --source=open_charge_map

# Then LLM sources (costs money)
python -m engine.extraction.run --source=serper --limit=100  # Test with limit first
python -m engine.extraction.run --source=osm --limit=100
```

---

## Data Quality Issues

### Issue 12: High Null Rates for Important Fields

**Symptoms:**
```
WARNING: Field 'phone' has 67% null rate (health dashboard)
```

**Causes:**
- Source doesn't provide the field
- Extraction logic incorrect
- Field name changed in raw data

**Solutions:**

**Verify field exists in raw data:**
```bash
# Check raw data for presence of field
python -c "
import json
from pathlib import Path

file_path = Path('data/raw_ingestion/google_places/clx123.json')
with open(file_path, 'r') as f:
    data = json.load(f)
    print('Has phone:', 'nationalPhoneNumber' in data)
    print('Has international phone:', 'internationalPhoneNumber' in data)
"
```

**Update extractor to use correct field:**
```python
# Try multiple field names
extracted["phone"] = (
    raw_data.get("nationalPhoneNumber") or
    raw_data.get("internationalPhoneNumber") or
    raw_data.get("phoneNumber") or
    None
)
```

**Add additional sources for missing fields:**
- If Google Places doesn't provide emails, add a source that does
- If OSM lacks phone numbers, prioritize Google Places

---

### Issue 13: Duplicate Listings Created

**Symptoms:**
```
ERROR: Duplicate listing created - "Game4Padel" appears twice with different IDs
```

**Causes:**
- Deduplication not working
- External IDs missing
- Slug generation inconsistent

**Solutions:**

**Ensure external IDs are captured:**
```python
def extract(self, raw_data: Dict) -> Dict:
    extracted = {
        # ... other fields
        "external_ids": {
            f"{self.source_name}_id": str(raw_data["id"])  # CRITICAL for deduplication
        }
    }
    return extracted
```

**Check deduplication logic:**
```bash
# Test deduplication
pytest engine/extraction/tests/test_deduplication.py -v
```

**Manually merge duplicates:**
```python
# Planned feature: Manual merge tool
# For now, delete one of the duplicates and re-extract
```

---

### Issue 14: Merge Conflicts (Multiple Sources Disagree)

**Symptoms:**
```
WARNING: Merge conflict on field 'phone' for listing 'Game4Padel'
  Source A (google_places, trust=70): +441315397071
  Source B (osm, trust=40): +441315397072
```

**Causes:**
- Different sources provide different values
- Data changed over time
- Human error in source data

**Solutions:**

**Trust hierarchy resolves most conflicts automatically:**
- Google (trust=70) wins over OSM (trust=40)
- Result: `+441315397071`

**Review conflicts in health dashboard:**
```bash
python -m engine.extraction.health
```

**Manually verify and override if needed:**
```python
# Set manual override (trust=100) in database
await db.listing.update(
    where={"id": "clx123..."},
    data={
        "phone": "+441315397071",
        "source_info": json.dumps({"phone": "manual_override"}),
        "field_confidence": json.dumps({"phone": 100})
    }
)
```

---

## Performance Issues

### Issue 15: Extraction Too Slow

**Symptoms:**
```
INFO: Processed 247 records in 45m 30s (5.4 records/min)
Expected: ~60 records/min for deterministic extractors
```

**Causes:**
- LLM latency (500ms-2s per call)
- Database write bottlenecks
- Single-threaded processing

**Solutions:**

**Profile extraction to find bottleneck:**
```bash
# Run with timing details
python -m cProfile -s tottime -m engine.extraction.run --source=google_places --limit=10
```

**Optimize LLM calls:**
- Implement caching (Phase 10)
- Reduce prompt size
- Use Haiku (faster than Sonnet/Opus)

**Migrate to PostgreSQL (if using SQLite):**
- SQLite = single-writer bottleneck
- PostgreSQL = 10x faster writes

**Implement async processing (Phase 10):**
```python
# Planned feature: Process deterministic extractors in parallel
await asyncio.gather(
    extract_google_places(),
    extract_sport_scotland(),
    extract_edinburgh_council()
)
```

---

### Issue 16: Memory Leak (Long Runs)

**Symptoms:**
```
WARNING: Memory usage 8.2GB after processing 5000 records
Expected: ~200MB
```

**Causes:**
- Large objects not garbage collected
- Database connections not closed
- Caching without limits

**Solutions:**

**Verify memory leak:**
```bash
# Monitor memory during extraction
watch -n 1 "ps aux | grep python"
```

**Check database connections:**
```python
# Ensure database is disconnected
try:
    await db.connect()
    await run_extraction(db)
finally:
    await db.disconnect()  # Always disconnect
```

**Clear caches periodically:**
```python
# If using caching, limit size
from functools import lru_cache

@lru_cache(maxsize=100)  # Limit cache to 100 entries
def expensive_function(data):
    ...
```

**Run in batches:**
```bash
# Instead of processing 10,000 records at once
python -m engine.extraction.run_all

# Process in batches of 1000
for i in {1..10}; do
    python -m engine.extraction.run_all --limit=1000
done
```

---

## Configuration Errors

### Error 17: Trust Level Not Found

**Symptoms:**
```
WARNING: Trust level not found for source 'strava', using default (unknown_source: 10)
```

**Causes:**
- New source not added to `extraction.yaml`
- Typo in source name

**Solutions:**

**Add trust level to config:**

Edit `engine/config/extraction.yaml`:
```yaml
trust_levels:
  manual_override: 100
  sport_scotland: 90
  # ... existing sources
  strava: 65  # ADD YOUR SOURCE
  unknown_source: 10
```

**Ensure source name matches:**
- `extractor.source_name = "strava"`
- `extraction.yaml: strava: 65`

---

### Error 18: Schema Field Not Recognized

**Symptoms:**
```
WARNING: Field 'padel_courts' not in schema, moving to discovered_attributes
```

**Causes:**
- Field not added to schema yet
- Wrong entity type in `split_attributes()`

**Solutions:**

**Add field to schema:**

Edit `engine/schema/venue.py`:
```python
class VenueFieldSpec:
    defined_fields = {
        "padel_courts": {"type": "integer", "nullable": True},
        "indoor_courts": {"type": "integer", "nullable": True},
        # ... existing fields
        "new_field": {"type": "string", "nullable": True},  # ADD THIS
    }
```

**Verify entity type:**
```python
# In split_attributes()
schema_fields = get_extraction_fields("venue")  # Correct entity type?
```

**Regenerate schema if using YAML (future):**
```bash
# Planned feature (Phase: YAML Schema Source of Truth)
python -m engine.schema.generate --source=venue.yaml
```

---

## Testing & Debugging Tips

### Tip 1: Use Dry-Run for Safe Testing

Always test with `--dry-run` before production:

```bash
# Preview results without saving
python -m engine.extraction.run --source=google_places --limit=5 --dry-run
```

### Tip 2: Use Verbose Mode for Debugging

See exactly what's being extracted:

```bash
python -m engine.extraction.run --raw-id=clx123 --verbose
```

### Tip 3: Check Health Dashboard Regularly

Monitor trends over time:

```bash
# Run daily
python -m engine.extraction.health > health_$(date +%Y%m%d).txt
```

### Tip 4: Use Fixtures for Reproducible Tests

Create fixtures from real failing data:

```bash
# Copy failing raw data to fixtures
cp data/raw_ingestion/serper/clx123.json engine/extraction/tests/fixtures/serper_failing_case.json

# Write test with fixture
pytest engine/extraction/tests/test_serper_extractor.py::test_handles_failing_case -v
```

### Tip 5: Enable Debug Logging

See detailed logs during extraction:

```bash
export LOG_LEVEL=DEBUG
python -m engine.extraction.run --source=google_places --limit=1
```

### Tip 6: Use Python Debugger (pdb)

Set breakpoints in extractor code:

```python
def extract(self, raw_data: Dict) -> Dict:
    import pdb; pdb.set_trace()  # Debugger will pause here

    extracted = {
        "entity_name": raw_data.get("name"),
        ...
    }
    return extracted
```

Run extraction, debugger will pause:
```bash
python -m engine.extraction.run --raw-id=clx123
```

### Tip 7: Compare with Snapshot

Verify extraction hasn't regressed:

```bash
# Create snapshot
python -m engine.extraction.run --source=google_places --limit=1 --dry-run > snapshot_before.json

# Make code changes

# Create new snapshot
python -m engine.extraction.run --source=google_places --limit=1 --dry-run > snapshot_after.json

# Compare
diff snapshot_before.json snapshot_after.json
```

---

## Quick Diagnostic Checklist

When extraction fails, check these in order:

- [ ] Database is running and accessible (`python -m engine.extraction.health`)
- [ ] Raw data exists (`ls data/raw_ingestion/<source>/`)
- [ ] Extractor is registered (`grep "<source>" engine/extraction/run.py`)
- [ ] Trust level configured (`grep "<source>" engine/config/extraction.yaml`)
- [ ] API key set if using LLM (`echo $ANTHROPIC_API_KEY`)
- [ ] Tests pass (`pytest engine/extraction/tests/test_<source>_extractor.py`)
- [ ] Logs show specific error (`tail logs/extraction.log`)

---

## Getting Help

If this troubleshooting guide doesn't resolve your issue:

1. **Check GitHub Issues**: [github.com/yourusername/edinburgh-finds/issues](https://github.com/)
2. **Review Code**: Existing extractors in `engine/extraction/extractors/` for examples
3. **Run Tests**: `pytest engine/extraction/tests -v` to verify system integrity
4. **Ask the Team**: Post in Slack #data-extraction channel

**When Asking for Help, Provide:**
- Exact error message (copy/paste from logs)
- Command you ran
- Output of `python -m engine.extraction.health`
- Relevant raw data (sanitized if sensitive)
- What you've already tried

---

## Document Version

**Version:** 1.0
**Last Updated:** 2026-01-17
**Maintained By:** Data Extraction Engine Team

**Related Docs:**
- [Extraction Engine Overview](./extraction_engine_overview.md)
- [Adding a New Extractor](./adding_new_extractor.md)
- [CLI Reference](./extraction_cli_reference.md)
