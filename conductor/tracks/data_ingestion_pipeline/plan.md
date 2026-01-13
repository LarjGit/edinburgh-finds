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
- [ ] Run Prisma migration to create table
- [ ] Create `engine/ingestion/` module structure
- [ ] Write tests for base connector interface
- [ ] Implement `base.py` with abstract `BaseConnector` class (fetch, save, deduplicate methods)
- [ ] Write tests for filesystem storage helpers
- [ ] Implement filesystem storage helpers (create dirs, save JSON, generate paths)
- [ ] Write tests for deduplication logic (hash-based)
- [ ] Implement deduplication logic
- [ ] Create `engine/config/sources.yaml` template for API keys and rate limits

**Success Criteria:**
- RawIngestion table exists in database
- BaseConnector interface is tested and documented
- Filesystem storage creates valid paths and saves JSON
- Hash-based deduplication prevents duplicate ingestion

---

## Phase 2: Primary Connectors

### Tasks
- [ ] Write tests for Serper API connector
- [ ] Implement `serper.py` connector (search queries, save results)
- [ ] Test Serper connector with sample Padel query
- [ ] Write tests for Google Places API connector
- [ ] Implement `google_places.py` connector (place search, place details)
- [ ] Test Google Places connector with Edinburgh Padel venues
- [ ] Write tests for OSM Overpass API connector
- [ ] Implement `open_street_map.py` connector (sports facilities query)
- [ ] Test OSM connector with Padel/sports facility queries
- [ ] Create CLI script to run individual connectors (e.g., `python -m engine.ingestion.serper "padel edinburgh"`)

**Success Criteria:**
- Each connector successfully fetches and saves raw data
- RawIngestion records created for each fetch
- Deduplication prevents re-ingesting same URLs
- CLI allows manual testing of each connector
- All tests pass with >80% coverage

---

## Phase 3: Enrichment Connectors

### Tasks
- [ ] Write tests for OpenChargeMap API connector
- [ ] Implement `open_charge_map.py` connector (nearby charging stations by lat/lng)
- [ ] Test OpenChargeMap connector with known venue coordinates
- [ ] Research and document additional enrichment sources (SportScotland, Edinburgh Council Open Data)
- [ ] Write tests for SportScotland Open Data connector
- [ ] Implement `sport_scotland.py` connector
- [ ] Write tests for Edinburgh Council Open Data connector
- [ ] Implement `edinburgh_council.py` connector
- [ ] Create documentation for adding new connectors

**Success Criteria:**
- Enrichment connectors fetch supplementary data
- Clear pattern established for adding new sources
- Documentation enables future connector development
- All tests pass with >80% coverage

---

## Phase 4: Quality & Observability

### Tasks
- [ ] Write tests for logging infrastructure
- [ ] Implement structured logging (source, timestamp, status, errors)
- [ ] Write tests for rate limiting decorator
- [ ] Implement rate limiting with configurable limits per source
- [ ] Write tests for retry logic with exponential backoff
- [ ] Implement retry logic for failed requests
- [ ] Create CLI status command to view ingestion statistics
- [ ] Write tests for ingestion health checks
- [ ] Implement health check: failed ingestions, stale data, API quota usage
- [ ] Create ingestion summary report (records by source, success rate, errors)

**Success Criteria:**
- All connector errors logged with context
- Rate limiting prevents API quota exhaustion
- Failed requests retry with backoff
- CLI provides clear status overview
- Health checks identify issues proactively
- All tests pass with >80% coverage

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
