# Data Ingestion CLI Tools

Command-line tools for running individual data source connectors to fetch and save raw data.

## Available Connectors

- **serper** - Web search results via Serper API
- **google_places** - Venue data via Google Places API (v1)
- **openstreetmap** - Geographic and facility data via Overpass API

## Usage

### Unified CLI

Run any connector using the unified CLI tool:

```bash
# General syntax
python -m engine.ingestion.cli <connector> "<query>"

# Examples
python -m engine.ingestion.cli serper "padel edinburgh"
python -m engine.ingestion.cli google_places "padel courts edinburgh"
python -m engine.ingestion.cli openstreetmap "tennis"

# Verbose output
python -m engine.ingestion.cli -v serper "padel edinburgh"

# List available connectors
python -m engine.ingestion.cli --list
```

### Individual Connector Entry Points

For convenience, each connector has its own entry point:

```bash
# Serper connector
python -m engine.ingestion.run_serper "padel edinburgh"

# Google Places connector
python -m engine.ingestion.run_google_places "padel courts"

# OpenStreetMap connector
python -m engine.ingestion.run_osm "tennis"
```

## Output

The CLI tools perform the following workflow:

1. **Initialize** - Load connector with configuration from `sources.yaml`
2. **Connect** - Connect to Prisma database
3. **Fetch** - Retrieve data from the external API
4. **Deduplicate** - Check if data has already been ingested (hash-based)
5. **Save** - Store raw JSON to filesystem and create database record

### File Storage

Raw data is saved to:
```
engine/data/raw/<source>/<timestamp>_<identifier>_<hash>.json
```

### Database Records

Metadata is stored in the `RawIngestion` table with fields:
- `source` - Connector name
- `source_url` - Original API endpoint
- `file_path` - Location of saved JSON file
- `hash` - Content hash for deduplication
- `status` - Ingestion status
- `ingested_at` - Timestamp
- `metadata_json` - Additional metadata (result count, API version)

## Examples

### Fetch Padel venues via Serper
```bash
python -m engine.ingestion.cli serper "padel edinburgh"
```

Output:
```
================================================================================
Running serper connector
Query: padel edinburgh
Time: 2026-01-13 23:49:11
================================================================================

[3/5] Fetching data from serper...
  ✓ Fetched 10 results

[4/5] Checking for duplicates...
  - Content hash: db0ba2a205613615...
  - Is duplicate: False

[5/5] Saving data...
  ✓ Data saved successfully
  ✓ File: engine/data/raw/serper/20260113_padel_edinburgh_db0ba2a2.json
  ✓ Results: 10

================================================================================
✓ Success!
================================================================================
```

### Fetch Padel courts via Google Places
```bash
python -m engine.ingestion.run_google_places "padel courts edinburgh"
```

Output includes:
- Connector initialization
- Database connection
- API fetch with sample results
- Deduplication check
- File save confirmation

### Fetch Tennis facilities via OpenStreetMap
```bash
python -m engine.ingestion.run_osm "tennis"
```

Note: OSM queries use sport tags, so use single words like "tennis", "padel", "golf".

## Deduplication

The CLI automatically checks for duplicate content using hash-based deduplication:
- If the same query has been run before (identical results), it skips saving
- This prevents duplicate API calls and storage waste
- Duplicate detection is based on content hash, not just query string

## Error Handling

The CLI handles common errors gracefully:
- **HTTP 429** (Rate Limiting) - Displays error message with rate limit details
- **Network Timeouts** - Reports timeout and suggests retry
- **Invalid API Keys** - Shows configuration error with instructions
- **Missing Config** - Prompts to check `sources.yaml` file

## Configuration

Connectors load settings from `engine/config/sources.yaml`:
- API keys and authentication
- Base URLs and endpoints
- Timeout settings
- Rate limits
- Default parameters

See `sources.yaml` for configuration details.

## Development

To add a new connector to the CLI:

1. Create connector class inheriting from `BaseConnector`
2. Add to `CONNECTORS` registry in `cli.py`:
   ```python
   CONNECTORS = {
       'new_connector': NewConnector,
   }
   ```
3. (Optional) Create dedicated entry point: `run_new_connector.py`

## Help

```bash
# Show CLI help
python -m engine.ingestion.cli --help

# List available connectors
python -m engine.ingestion.cli --list
```
