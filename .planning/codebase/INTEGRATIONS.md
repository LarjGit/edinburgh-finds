# External Integrations

**Analysis Date:** 2026-01-27

## APIs & External Services

**Search & Discovery:**
- Serper API - Web search results API
  - SDK/Client: aiohttp (custom HTTP client)
  - Auth: Environment variable `SERPER_API_KEY`
  - Connector: `engine/ingestion/connectors/serper.py`
  - Cost: $0.01 per call (tracked in registry)
  - Trust Level: 0.75 (moderate - web search results)
  - Phase: Discovery
  - Timeout: 30 seconds

**Places & Venue Data:**
- Google Places API - Business/venue information
  - SDK/Client: aiohttp (custom HTTP client)
  - Auth: Environment variable `GOOGLE_PLACES_API_KEY`
  - Connector: `engine/ingestion/connectors/google_places.py`
  - Cost: $0.017 per call (Text Search pricing)
  - Trust Level: 0.95 (very high - authoritative Google data)
  - Phase: Enrichment
  - Timeout: 30 seconds
  - Documentation: https://developers.google.com/maps/documentation/places/web-service

**Geographic & OSM Data:**
- OpenStreetMap API - Free geographic and venue data
  - SDK/Client: aiohttp (custom HTTP client)
  - Connector: `engine/ingestion/connectors/open_street_map.py`
  - Cost: Free
  - Trust Level: 0.70 (moderate - crowdsourced data)
  - Phase: Discovery
  - Timeout: 60 seconds

**Government & Official Data:**
- Sport Scotland API - Official sports facility data
  - SDK/Client: aiohttp (custom HTTP client)
  - Connector: `engine/ingestion/connectors/sport_scotland.py`
  - Cost: Free (official government API)
  - Trust Level: 0.90 (high - official government data)
  - Phase: Enrichment
  - Timeout: 60 seconds

- Edinburgh Council API - Official Edinburgh facilities data
  - SDK/Client: aiohttp (custom HTTP client)
  - Connector: `engine/ingestion/connectors/edinburgh_council.py`
  - Cost: Free (official government API)
  - Trust Level: 0.90 (high - official government data)
  - Phase: Enrichment
  - Timeout: 60 seconds

**Specialized Data:**
- OpenChargeMap API - EV charging station data
  - SDK/Client: aiohttp (custom HTTP client)
  - Connector: `engine/ingestion/connectors/open_charge_map.py`
  - Cost: Free
  - Trust Level: 0.80 (crowdsourced but specialized domain data)
  - Phase: Enrichment
  - Timeout: 60 seconds

## Data Storage

**Databases:**
- PostgreSQL (Supabase)
  - Connection: Environment variable `DATABASE_URL`
  - Client: Prisma ORM (both JavaScript and Python)
  - Location: AWS eu-west-1 region
  - Provider URL: Supabase pooler connection

**File Storage:**
- Local filesystem only
  - Raw ingestion data stored in: `engine/data/raw/<source>/<timestamp>_<id>.json`
  - Path generation: `engine/ingestion/storage.py`
  - Hash tracking for deduplication: SHA256 content hash

**Caching:**
- None detected - no caching infrastructure currently in place

## Authentication & Identity

**Auth Provider:**
- None detected - no user authentication/authorization system currently implemented
- API key authentication only for external service integrations

## LLM & AI Integration

**Primary LLM Provider:**
- Anthropic Claude API
  - SDK/Client: anthropic Python package + instructor wrapper
  - Auth: Environment variable `ANTHROPIC_API_KEY`
  - Integration: `engine/extraction/llm_client.py` (InstructorClient class)
  - Model: claude-haiku-20250318 (configurable via `engine/config/extraction.yaml`)
  - Wrapper: instructor - Enforces structured Pydantic model output
  - Max tokens per call: 4096
  - Retry logic: Up to 2 retries on validation failure
  - Cost tracking: Input ($0.80/MTok) and output ($4.00/MTok) pricing calculated

**Usage:**
- LLM used for structured extraction of unstructured raw data from connectors
- Validation feedback loop: If extraction fails validation, LLM retries with error details
- Token/cost tracking: All calls logged and aggregated in global tracker

## Monitoring & Observability

**Error Tracking:**
- None detected - No external error tracking service (Sentry, Rollbar, etc.)
- In-app error logging: `engine/extraction/logging_config.py`
- Failed extractions tracked in database: `FailedExtraction` model

**Logs:**
- Python logging module with configurable handlers
- Extraction-specific logger: `engine/extraction/logging_config.py`
- Log level configurable via `LOG_LEVEL` environment variable

**Structured Logging:**
- LLM call logging: `engine/extraction/logging_config.py` - logs all extraction calls with token usage and cost
- Usage tracking: `engine/extraction/llm_cost.py` - global tracker for token aggregation

## CI/CD & Deployment

**Hosting:**
- Frontend: Next.js application (can deploy to Vercel, self-hosted, or other Node.js hosts)
- Backend: Python ETL pipeline (scheduled runner or serverless function)
- Database: Supabase PostgreSQL (managed cloud)

**CI Pipeline:**
- None detected - No GitHub Actions, GitLab CI, or other CI service currently configured

**Secrets Management:**
- Environment variables via `.env` files
- Recommended: Use Supabase secrets or platform-specific secret management (Vercel environment secrets, etc.)

## Environment Configuration

**Required env vars:**
- `DATABASE_URL` - PostgreSQL connection string (Supabase)
- `ANTHROPIC_API_KEY` - Claude API authentication key
- `GOOGLE_PLACES_API_KEY` - Google Places API key
- `SERPER_API_KEY` - Serper search API key
- `LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `NODE_ENV` - Node environment (development/production)

**Optional:**
- None explicitly documented, but individual connector classes may read additional config from YAML

## Webhooks & Callbacks

**Incoming:**
- None detected - No webhook endpoints currently implemented

**Outgoing:**
- None detected - No webhook notifications to external services

## API Rate Limits & Costs

**Connector Registry:**
All connectors defined in `engine/orchestration/registry.py` with cost and trust metadata:

| Connector | Cost | Trust | Phase | Timeout |
|-----------|------|-------|-------|---------|
| Serper | $0.01 | 0.75 | Discovery | 30s |
| Google Places | $0.017 | 0.95 | Enrichment | 30s |
| OpenStreetMap | Free | 0.70 | Discovery | 60s |
| Sport Scotland | Free | 0.90 | Enrichment | 60s |
| Edinburgh Council | Free | 0.90 | Enrichment | 60s |
| OpenChargeMap | Free | 0.80 | Enrichment | 60s |

**Cost Tracking:**
- LLM: Token-based cost calculation (Claude Haiku pricing)
- API connectors: Per-call cost configured in registry
- Orchestration runs: Total budget tracked in `OrchestrationRun.budget_spent_usd`

---

*Integration audit: 2026-01-27*
