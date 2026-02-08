# Configuration Guide

**System:** Universal Entity Extraction Engine
**Reference Application:** Edinburgh Finds (reference lens only)

This guide covers all configuration requirements for the Universal Entity Extraction Engine, including environment variables, API keys, database setup, lens configuration, and connector registry settings.

---

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [API Keys](#api-keys)
3. [Database Configuration](#database-configuration)
4. [Lens Configuration](#lens-configuration)
5. [Connector Registry](#connector-registry)
6. [Development vs Production](#development-vs-production)
7. [Security Best Practices](#security-best-practices)

---

## Environment Variables

### Required Variables

The engine requires specific environment variables to function. These should be set in a `.env` file in the project root for local development.

#### Core Engine Variables

```bash
# Anthropic API - Required for LLM-powered extraction
ANTHROPIC_API_KEY=sk-ant-api03-...

# Google Places API - For Places connector
GOOGLE_PLACES_API_KEY=your-google-places-api-key

# Serper API - For search-based discovery
SERPER_API_KEY=your-serper-api-key

# Database - PostgreSQL connection string (Supabase)
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public
```

#### Optional Variables

```bash
# Logging Level
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR

# Node Environment (Frontend)
NODE_ENV=development  # Options: development, production, test

# Lens Selection (Override default)
LENS_ID=edinburgh_finds  # Specify active lens
```

### Setting Up Environment Files

1. **Root `.env` (Engine):**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

2. **Web `.env` (Frontend):**
   ```bash
   cd web
   cp .env.example .env
   # Add DATABASE_URL for Prisma client
   ```

3. **Never commit credentials:**
   - Both `.env` files are in `.gitignore`
   - Use `.env.example` as template only

---

## API Keys

### Anthropic API Key

**Purpose:** Powers LLM-based extraction for unstructured data (reviews, descriptions, social media).

**How to obtain:**
1. Sign up at https://console.anthropic.com/
2. Navigate to API Keys section
3. Create new key with appropriate billing limits
4. Copy key to `ANTHROPIC_API_KEY` environment variable

**Model Used:** `claude-haiku-4-5` (configured in `engine/config/extraction.yaml`)

**Cost Considerations:**
- Extraction uses Haiku model (cost-optimized)
- Average cost: ~$0.001 per entity extraction
- Monitor usage via Anthropic Console

### Google Places API Key

**Purpose:** Enrichment phase connector for authoritative venue data.

**How to obtain:**
1. Visit https://developers.google.com/maps/documentation/places/web-service/get-api-key
2. Create new project in Google Cloud Console
3. Enable Places API (New v1)
4. Create API credentials
5. Copy key to `GOOGLE_PLACES_API_KEY`

**Rate Limits:**
- 60 requests/minute
- 2000 requests/hour (default configuration)
- Free tier: $200 credit/month

**Field Mask Configuration:**
Default fields (configured in `engine/config/sources.yaml`):
```
places.id, places.displayName, places.formattedAddress, places.location,
places.rating, places.userRatingCount, places.types, places.googleMapsUri,
places.editorialSummary, places.reviews, places.regularOpeningHours
```

### Serper API Key

**Purpose:** Discovery phase connector for web search results.

**How to obtain:**
1. Sign up at https://serper.dev/
2. Navigate to API dashboard
3. Copy API key to `SERPER_API_KEY`

**Rate Limits:**
- 60 requests/minute
- 1000 requests/hour
- Free tier: 2500 searches/month

**Default Parameters:**
```yaml
gl: "uk"    # Geolocation: United Kingdom
hl: "en"    # Language: English
num: 10     # Results per query
```

### SportScotland API Key

**Purpose:** Official Scottish sports facility data (WFS service).

**How to obtain:**
1. Register at https://data.spatialhub.scot/
2. Request access to Sports Facilities dataset
3. Obtain JWT token
4. Add to `engine/config/sources.yaml` under `sport_scotland.api_key`

**Note:** This is a WFS (Web Feature Service) endpoint using British National Grid coordinates (EPSG:27700).

**Rate Limits:**
- 10 requests/minute (conservative)
- 200 requests/hour

### OpenChargeMap API Key

**Purpose:** EV charging station enrichment data.

**How to obtain:**
1. Sign up at https://openchargemap.org/site/develop/api
2. Generate API key
3. Add to `engine/config/sources.yaml` under `open_charge_map.api_key`

**Rate Limits:**
- 60 requests/minute
- 1000 requests/hour

### OpenStreetMap (No Key Required)

**Purpose:** Geographic and facility data (discovery phase).

**Configuration:**
- Public Overpass API
- No authentication required
- Respectful rate limiting: 2 requests/minute, 100 requests/hour

---

## Database Configuration

### PostgreSQL via Supabase

The engine uses **Supabase** for PostgreSQL database hosting with Prisma ORM.

#### Connection String Format

```bash
DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public"
```

**Example (Supabase):**
```bash
DATABASE_URL="postgresql://postgres.abcdefghijklmnop:your_password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true&connection_limit=1"
```

#### Setup Steps

1. **Create Supabase Project:**
   - Visit https://supabase.com/
   - Create new project
   - Copy connection string from Settings → Database

2. **Configure Environment:**
   ```bash
   # Root .env
   DATABASE_URL=your_supabase_connection_string

   # web/.env
   DATABASE_URL=your_supabase_connection_string
   ```

3. **Initialize Database Schema:**
   ```bash
   cd web
   npx prisma generate  # Generate Prisma client
   npx prisma db push   # Sync schema to Supabase (dev)
   ```

4. **Production Migrations:**
   ```bash
   cd web
   npx prisma migrate dev --name init
   npx prisma migrate deploy  # Production deployment
   ```

#### Database Features

**Multi-valued Dimensions:**
Canonical dimensions use PostgreSQL `TEXT[]` arrays with GIN indexes:
```sql
canonical_activities TEXT[]
canonical_roles TEXT[]
canonical_place_types TEXT[]
canonical_access TEXT[]
```

**Flexible Modules:**
Domain-specific attributes stored as JSONB:
```sql
modules JSONB
```

**Auto-generated Schema:**
Prisma schema is generated from `engine/config/schemas/entity.yaml`. Never edit `web/prisma/schema.prisma` directly.

---

## Lens Configuration

### Lens Resolution Precedence

Lenses define vertical-specific domain knowledge. The system resolves which lens to use via this precedence chain:

1. **CLI Override** (Highest priority)
   ```bash
   python -m engine.orchestration.cli run "padel Edinburgh" --lens edinburgh_finds
   ```

2. **Environment Variable**
   ```bash
   export LENS_ID=edinburgh_finds
   ```

3. **Application Default** (`engine/config/app.yaml`)
   ```yaml
   default_lens: edinburgh_finds  # Or null for explicit selection
   ```

4. **Dev/Test Fallback** (Not yet implemented)

### Default Lens Setting

Located in `engine/config/app.yaml`:

```yaml
# Set to null to require explicit lens selection
default_lens: null

# Or specify a default lens
default_lens: edinburgh_finds
```

**Recommendation:** Set to `null` in production to prevent accidental lens usage.

### Lens Directory Structure

```
engine/lenses/
├── edinburgh_finds/
│   └── lens.yaml          # Reference lens for sports discovery
└── wine/
    └── lens.yaml          # Example: wine discovery vertical
```

### Lens Configuration File (`lens.yaml`)

Each lens defines:

1. **Vocabulary:** Keywords for query feature detection
   ```yaml
   vocabulary:
     activity_keywords: [padel, tennis, squash]
     location_indicators: [edinburgh, leith]
     facility_keywords: [sports centre, club, courts]
   ```

2. **Connector Rules:** Intelligent connector selection
   ```yaml
   connector_rules:
     sport_scotland:
       priority: high
       triggers:
         - type: any_keyword_match
           keywords: [padel, tennis, sports]
   ```

3. **Mapping Rules:** Raw data → canonical dimensions
   ```yaml
   mapping_rules:
     - pattern: "(?i)padel"
       canonical: "padel"
       confidence: 0.95
   ```

4. **Module Triggers:** When to attach domain modules
   ```yaml
   module_triggers:
     - when:
         facet: activity
         value: padel
       add_modules: [sports_facility]
   ```

5. **Canonical Values:** Registry of all domain values
   ```yaml
   values:
     - key: padel
       facet: activity
       display_name: "Padel"
       seo_slug: "padel"
       icon_url: "/icons/padel.svg"
   ```

### Creating a New Lens

**Future (when lens system is complete):**
1. Create `engine/lenses/<vertical_id>/lens.yaml`
2. Define vocabulary, connector rules, mapping rules, module triggers
3. **DONE** - Zero engine code changes required

**Current (partial implementation):**
- Lens vocabulary and connector routing work
- Canonical dimension extraction not yet wired up
- Some extractor modifications still needed

---

## Connector Registry

The connector registry (`engine/orchestration/registry.py`) defines metadata for all 6 data sources.

### Connector Specifications

Each connector has:
- **Phase:** discovery or enrichment
- **Cost per call:** USD cost per API request
- **Trust level:** 0.0 to 1.0 (1.0 = authoritative)
- **Timeout:** Maximum execution time in seconds
- **Rate limit:** Maximum requests per day

### Current Connectors

| Connector | Phase | Cost/Call | Trust | Timeout | Rate Limit/Day |
|-----------|-------|-----------|-------|---------|----------------|
| serper | discovery | $0.01 | 0.75 | 30s | 2,500 |
| google_places | enrichment | $0.017 | 0.95 | 30s | 1,000 |
| openstreetmap | discovery | $0.00 | 0.70 | 60s | 10,000 |
| sport_scotland | enrichment | $0.00 | 0.90 | 60s | 10,000 |
| edinburgh_council | enrichment | $0.00 | 0.90 | 60s | 10,000 |
| open_charge_map | enrichment | $0.00 | 0.80 | 60s | 10,000 |

### Trust Level Configuration

Trust levels (configured in `engine/config/extraction.yaml`):

```yaml
trust_levels:
  manual_override: 100
  sport_scotland: 90
  edinburgh_council: 85
  google_places: 70
  serper: 50
  osm: 40
  open_charge_map: 40
  unknown_source: 10
```

These values determine merge priority when combining data from multiple sources.

### Rate Limiting

Global rate limit settings (`engine/config/sources.yaml`):

```yaml
global:
  retry:
    max_attempts: 3
    backoff_factor: 2  # Exponential: 1s, 2s, 4s
    retry_on_status_codes: [429, 500, 502, 503, 504]

  user_agent: "EdinburghFinds/0.1.0 Data Ingestion"

  logging:
    level: "INFO"
    log_api_requests: true
    log_api_responses: false  # Set true for debugging
```

### Adding a New Connector

1. **Update Registry** (`engine/orchestration/registry.py`):
   ```python
   "new_connector": ConnectorSpec(
       name="new_connector",
       connector_class="engine.ingestion.connectors.new_connector.NewConnector",
       phase="discovery",  # or "enrichment"
       cost_per_call_usd=0.0,
       trust_level=0.80,
       timeout_seconds=30,
       rate_limit_per_day=10000,
   )
   ```

2. **Add Adapter** (`engine/orchestration/adapters.py`):
   ```python
   _CONNECTOR_CLASSES["new_connector"] = NewConnector
   ```

3. **Configure Source** (`engine/config/sources.yaml`):
   ```yaml
   new_connector:
     enabled: true
     api_key: "your-key"
     base_url: "https://api.example.com"
     timeout_seconds: 30
     rate_limits:
       requests_per_minute: 60
       requests_per_hour: 1000
   ```

4. **Add to Lens Rules** (`engine/lenses/<lens_id>/lens.yaml`):
   ```yaml
   connector_rules:
     new_connector:
       priority: medium
       triggers:
         - type: always
   ```

---

## Development vs Production

### Development Configuration

**Characteristics:**
- Verbose logging (`LOG_LEVEL=DEBUG`)
- Relaxed rate limits
- Direct Prisma DB pushes (`npx prisma db push`)
- Local testing with mock data

**Setup:**
```bash
# .env (development)
NODE_ENV=development
LOG_LEVEL=DEBUG
ANTHROPIC_API_KEY=sk-ant-api03-...
DATABASE_URL=postgresql://localhost:5432/edinburgh_finds_dev
```

**Commands:**
```bash
# Frontend
cd web && npm run dev  # http://localhost:3000

# Backend
pytest -m "not slow"  # Fast tests
python -m engine.orchestration.cli run "padel Edinburgh"
```

### Production Configuration

**Characteristics:**
- Minimal logging (`LOG_LEVEL=INFO` or `WARNING`)
- Strict rate limits
- Prisma migrations (`npx prisma migrate deploy`)
- Connection pooling enabled
- Environment variable validation

**Setup:**
```bash
# .env (production)
NODE_ENV=production
LOG_LEVEL=WARNING
ANTHROPIC_API_KEY=sk-ant-api03-...
DATABASE_URL=postgresql://user:password@production-host:6543/db?pgbouncer=true
```

**Pre-deployment Checklist:**
1. Schema validation: `python -m engine.schema.generate --validate`
2. Run all tests: `pytest --cov=engine`
3. Build frontend: `cd web && npm run build`
4. Lint checks: `cd web && npm run lint`
5. Database migration: `cd web && npx prisma migrate deploy`
6. Verify environment variables are set

### CI/CD Configuration

**Environment Variable Management:**
- Use secrets management (GitHub Secrets, AWS Secrets Manager)
- Never commit `.env` files to version control
- Use `.env.example` as template for required variables

**Test Configuration:**
```bash
CI=true npm test  # Frontend: non-interactive mode
pytest  # Backend: already non-interactive
```

---

## Security Best Practices

### API Key Management

**DO:**
- Store keys in `.env` files (gitignored)
- Use environment-specific keys (dev/staging/prod)
- Rotate keys regularly (every 90 days recommended)
- Set billing limits on API accounts
- Use read-only keys where possible

**DON'T:**
- Commit API keys to version control
- Share keys via Slack/email/docs
- Use production keys in development
- Hardcode keys in source files
- Store keys in browser localStorage

### Database Security

**Connection Strings:**
- Use connection pooling in production (`pgbouncer=true`)
- Set `connection_limit=1` for serverless environments
- Use SSL/TLS for all connections
- Rotate database passwords regularly

**Access Control:**
- Create separate database users for dev/staging/prod
- Grant minimum required permissions
- Use row-level security (RLS) in Supabase for frontend access
- Never expose direct database credentials to frontend

### Environment Variable Validation

The engine validates required variables at startup:

```python
# Pseudo-code validation (not implemented yet)
required_vars = [
    "ANTHROPIC_API_KEY",
    "DATABASE_URL",
]

for var in required_vars:
    if not os.getenv(var):
        raise EnvironmentError(f"Missing required variable: {var}")
```

**Recommendation:** Add validation to `engine/__init__.py` or startup script.

### Lens Configuration Security

**Lens YAML files are code:**
- Treat lens configurations as executable code
- Review changes in pull requests
- Validate lens schema at load time (fail-fast)
- Never load lenses from user-provided sources

**Fail-Fast Validation:**
```python
# Engine loads lens.yaml at bootstrap
# Invalid lens → immediate failure (no silent fallbacks)
if not validate_lens_schema(lens_config):
    raise LensValidationError("Invalid lens schema")
```

### Rate Limiting

**Connector Rate Limits:**
- Configured per connector in `engine/config/sources.yaml`
- Enforced via global retry settings
- Exponential backoff on 429 (rate limit exceeded)

**Production Recommendations:**
- Monitor API usage via connector dashboards
- Set up alerts for rate limit violations
- Implement request queuing for high-volume scenarios
- Use cached results where appropriate

### Logging and Monitoring

**Safe Logging Practices:**
- Never log API keys or credentials
- Redact sensitive fields in logs (emails, phone numbers)
- Use structured logging (JSON format)
- Set `log_api_responses: false` in production

**Monitoring:**
- Track connector error rates
- Monitor database connection pool usage
- Alert on failed extractions
- Log all lens loading failures

---

## Configuration Validation

### Pre-Commit Checklist

Before committing configuration changes:

1. **Schema Validation:**
   ```bash
   python -m engine.schema.generate --validate
   ```

2. **Lens Validation:**
   ```bash
   # TODO: Add lens validation command
   python -m engine.lenses.validate
   ```

3. **Test Configuration:**
   ```bash
   pytest engine/config/  # Config-specific tests
   ```

4. **Lint YAML:**
   ```bash
   # Use yamllint or similar
   yamllint engine/config/
   ```

### Common Configuration Errors

**1. Missing API Keys:**
```bash
# Error: ANTHROPIC_API_KEY not found
# Fix: Add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

**2. Invalid DATABASE_URL:**
```bash
# Error: Could not connect to database
# Fix: Verify connection string format
postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public
```

**3. Lens Not Found:**
```bash
# Error: Lens 'wine' not found
# Fix: Verify lens directory exists
ls engine/lenses/wine/lens.yaml
```

**4. Schema Drift:**
```bash
# Error: Generated schema out of sync
# Fix: Regenerate schemas
python -m engine.schema.generate --all
cd web && npx prisma generate
```

### Troubleshooting

**Enable Debug Logging:**
```bash
LOG_LEVEL=DEBUG python -m engine.orchestration.cli run "query"
```

**Check Connector Health:**
```bash
# TODO: Add health check command
python -m engine.orchestration.cli health-check
```

**Validate All Configurations:**
```bash
pytest tests/engine/config/  # Config validation tests
```

---

## Summary

**Critical Configuration Points:**

1. **Environment Variables:** Set `ANTHROPIC_API_KEY`, API keys, `DATABASE_URL` in `.env`
2. **Lens Selection:** Configure via CLI, `LENS_ID` env var, or `app.yaml`
3. **Connector Registry:** Metadata defines cost, trust, phase for intelligent routing
4. **Database:** PostgreSQL via Supabase with auto-generated Prisma schema
5. **Security:** Never commit credentials, validate at startup, use fail-fast validation

**Configuration Files:**
- `engine/config/app.yaml` - Lens defaults
- `engine/config/extraction.yaml` - LLM model, trust levels
- `engine/config/sources.yaml` - Connector API keys, rate limits
- `engine/lenses/<lens_id>/lens.yaml` - Vertical-specific domain knowledge
- `engine/orchestration/registry.py` - Connector metadata registry

**Next Steps:**
1. Copy `.env.example` to `.env` and add API keys
2. Configure Supabase database connection
3. Select or create lens for your vertical
4. Run schema validation: `python -m engine.schema.generate --validate`
5. Test orchestration: `python -m engine.orchestration.cli run "test query"`

For architectural decisions, consult `docs/target/system-vision.md` (immutable invariants) and `docs/target/architecture.md` (runtime specification).
