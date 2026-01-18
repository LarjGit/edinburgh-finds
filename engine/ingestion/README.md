# Data Ingestion Connectors

This directory contains connectors for fetching raw data from external sources.

## Quick Links

- **[Connector Development Guide](CONNECTOR_GUIDE.md)** - Complete guide for adding new connectors (800+ lines)
- **[Configuration](../config/sources.yaml)** - API keys and connector settings

## Implemented Connectors

### Primary Sources (Core entity data)

| Connector | Type | Description | Tests | Status |
|-----------|------|-------------|-------|--------|
| **serper.py** | REST API | Google search results | 19 | ✅ Complete |
| **google_places.py** | REST API | Google Places (new v1 API) | 25 | ✅ Complete |
| **open_street_map.py** | Overpass API | OSM sports facilities | 28 | ✅ Complete |

### Enrichment Sources (Supplementary data)

| Connector | Type | Description | Tests | Status |
|-----------|------|-------------|-------|--------|
| **open_charge_map.py** | REST API | EV charging stations | 23 | ✅ Complete |
| **sport_scotland.py** | WFS | SportScotland facilities (GeoServer) | 21 | ✅ Complete |
| **edinburgh_council.py** | ArcGIS REST | Edinburgh Council civic facilities | 22 | ✅ Complete |

## Architecture

All connectors inherit from `BaseConnector` (defined in `base.py`) and implement:

```python
@property
def source_name(self) -> str:
    """Unique identifier (e.g., 'serper')"""

async def fetch(self, query: str) -> dict:
    """Fetch data from external source"""

async def save(self, data: dict, source_url: str) -> str:
    """Save to filesystem + database"""

async def is_duplicate(self, content_hash: str) -> bool:
    """Check if already ingested"""
```

## Data Flow

```
┌─────────────┐
│  Connector  │
└──────┬──────┘
       │
       ├─ fetch(query) → HTTP/WFS request
       │
       ├─ compute_content_hash(data) → SHA-256
       │
       ├─ is_duplicate(hash) → Check DB
       │
       └─ save(data, url)
            ├─ Save JSON: engine/data/raw/<source>/
            └─ Create DB record: RawIngestion table
```

## Adding a New Connector

**See [CONNECTOR_GUIDE.md](CONNECTOR_GUIDE.md) for complete instructions.**

Quick overview:
1. **Research** API (30 mins)
2. **Write tests** - TDD approach (30 mins)
3. **Implement** connector (60-90 mins)
4. **Configure** sources.yaml (10 mins)
5. **Test** with real API (30 mins)

**Total time:** 2-4 hours for typical REST API

## Helper Modules

- **base.py** - BaseConnector interface
- **storage.py** - Filesystem helpers (generate_file_path, save_json)
- **deduplication.py** - Hash utilities (compute_content_hash, check_duplicate)

## Testing

```bash
# Run all connector tests
python -m unittest discover engine/tests -p "test_*_connector.py" -v

# Run specific connector tests
python -m unittest engine.tests.test_serper_connector -v

# Manual testing with real API
python -m engine.scripts.run_serper_connector
```

## Configuration

API keys and settings are in `engine/config/sources.yaml` (gitignored).

Example:
```yaml
my_source:
  enabled: true
  api_key: "YOUR_KEY_HERE"
  base_url: "https://api.example.com"
  timeout_seconds: 30
  rate_limits:
    requests_per_minute: 60
    requests_per_hour: 1000
```

## Next Steps

- See **Phase 4** in track plan for observability features (logging, rate limiting, retry logic)
- See **Phase 2** (overall pipeline) for structured extraction from raw data

---

**For detailed guidance, see [CONNECTOR_GUIDE.md](CONNECTOR_GUIDE.md)**
