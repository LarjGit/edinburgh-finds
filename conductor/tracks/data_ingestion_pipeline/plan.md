# Track: Data Ingestion Pipeline

## Overview
Build a modular, two-stage data pipeline that separates raw data ingestion from structured extraction. Stage 1 (this track) focuses on gathering raw data from multiple sources and storing it with metadata for later processing.

## Architecture Principles
- **Modular:** Each source connector is standalone and implements common interface
- **Separation:** Raw data (filesystem) + metadata (database table)
- **Portable:** Filesystem storage compatible with future Supabase migration
- **Extensible:** Easy to add new sources without changing core infrastructure

## Storage Strategy
- **Raw Content:** `engine/data/raw/<source>/<timestamp>_<id>.json`
- **Metadata:** `RawIngestion` table in Prisma schema
  - Fields: `source`, `source_url`, `file_path`, `status`, `ingested_at`, `hash`, `metadata_json`

## Source Categories
1. **Primary Sources:** Core entity data (venues, coaches, retailers, clubs)
2. **Enrichment Sources:** Additional attributes (EV charging, transit access, etc.)

---

## Phase 1: Foundation

### Tasks
- [x] Add `RawIngestion` model to Prisma schema with fields: id, source, source_url, file_path, status, ingested_at, hash, metadata_json (a47c3e8)
- [x] Run Prisma migration to create table (a47c3e8)
- [x] Create `engine/ingestion/` module structure (697d91a)
- [x] Write tests for base connector interface (900e128)
- [x] Implement `base.py` with abstract `BaseConnector` class (fetch, save, deduplicate methods) (17208ef)
- [x] Write tests for filesystem storage helpers (0eca636)
- [x] Implement filesystem storage helpers (create dirs, save JSON, generate paths) (1309aa3)
- [x] Write tests for deduplication logic (hash-based) (39c1e14)
- [x] Implement deduplication logic (033274a)
- [x] Create `engine/config/sources.yaml` template for API keys and rate limits (46b16a4)

**Success Criteria:**
- RawIngestion table exists in database
- BaseConnector interface is tested and documented
- Filesystem storage creates valid paths and saves JSON
- Hash-based deduplication prevents duplicate ingestion

---

## Phase 2: Primary Connectors

### Tasks
- [x] Write tests for Serper API connector (4e9f518)
- [x] Implement `serper.py` connector (search queries, save results) (6e0f6bf)
- [x] Test Serper connector with sample Padel query (4002dbe)
- [x] Write tests for Google Places API connector (c07b328)
- [x] Implement `google_places.py` connector (place search, place details) (6f0dc54)
- [x] Test Google Places connector with Edinburgh Padel venues (4824a2c)
- [x] Upgrade Google Places connector to new Places API (not deprecated) (c31298b)
- [x] Write tests for OSM Overpass API connector (6b53005)
- [x] Implement `open_street_map.py` connector (sports facilities query) (fee0fff)
- [x] Test OSM connector with Padel/sports facility queries (92d5a67)
- [x] Create CLI script to run individual connectors (e.g., `python -m engine.ingestion.serper "padel edinburgh"`) (8f0c1eb)

**Success Criteria:**
- ✅ Each connector successfully fetches and saves raw data
- ✅ RawIngestion records created for each fetch
- ✅ Deduplication prevents re-ingesting same URLs
- ✅ CLI allows manual testing of each connector
- ✅ All tests pass with >80% coverage (117/117 = 100%)

**Phase Status:** ✅ COMPLETE (Checkpoint: 4a9558a)

---

## Phase 3: Enrichment Connectors

### Tasks
- [x] Write tests for OpenChargeMap API connector (7e17e10)
- [x] Implement `open_charge_map.py` connector (nearby charging stations by lat/lng) (46dec5b)
- [x] Test OpenChargeMap connector with known venue coordinates (ec2a25c)
- [x] Research and document additional enrichment sources (SportScotland, Edinburgh Council Open Data) (9e8f1d9)
- [x] Write tests for SportScotland Open Data connector (11a91e3)
- [x] Implement `sport_scotland.py` connector (7830afb)
- [x] Test SportScotland connector with real WFS endpoint (ad8b353)
- [x] Write tests for Edinburgh Council Open Data connector (4b13fd6)
- [x] Implement `edinburgh_council.py` connector (1135019)
- [x] Create documentation for adding new connectors (69cff57)

**Success Criteria:**
- Enrichment connectors fetch supplementary data
- Clear pattern established for adding new sources
- Documentation enables future connector development
- All tests pass with >80% coverage

**Phase Status:** ✅ COMPLETE (Checkpoint: 08dc8c7)

---

## Phase 4: Quality & Observability

### Tasks
- [x] Write tests for logging infrastructure (f89f431)
- [x] Implement structured logging (source, timestamp, status, errors) (f89f431)
- [x] Write tests for rate limiting decorator (80f98c8)
- [x] Implement rate limiting with configurable limits per source (793a527)
- [x] Write tests for retry logic with exponential backoff (4d38829)
- [x] Implement retry logic for failed requests (26d5dad)
- [x] Create CLI status command to view ingestion statistics (a28da23)
- [x] Write tests for ingestion health checks (6421f91)
- [x] Implement health check: failed ingestions, stale data, API quota usage (aa3b239)
- [x] Create ingestion summary report (records by source, success rate, errors) (c55b4a4)

**Success Criteria:**
- ✅ All connector errors logged with context
- ✅ Rate limiting prevents API quota exhaustion
- ✅ Failed requests retry with backoff
- ✅ CLI provides clear status overview
- ✅ Health checks identify issues proactively
- ✅ All tests pass with >80% coverage (367/367 = 100%)

**Phase Status:** ✅ COMPLETE (Checkpoint: a561f71)

---

## Future Considerations (Not in Scope)
- Extraction engine (Phase 2 of overall data pipeline)
- Automated scheduling/orchestration
- Real-time ingestion triggers
- Data quality scoring
- Source prioritization logic

---

## Success Metrics (Overall Track)
- [ ] Raw data from 5+ sources successfully ingested
- [ ] Zero duplicate ingestions for same source URLs
- [ ] Filesystem storage organized and queryable via RawIngestion table
- [ ] Test coverage >80% across all modules
- [ ] Documentation enables adding new sources in <1 hour
- [ ] System ready for extraction stage development
