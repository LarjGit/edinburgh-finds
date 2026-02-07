# Configuration Guide

**Generated:** 2026-02-06
**Status:** Auto-generated documentation

---

## Overview

Edinburgh Finds uses a combination of environment variables, YAML configuration files, and auto-generated schemas. This document covers all configuration surfaces.

---

## Environment Variables

### Required Variables

| Variable | Layer | Description | Example |
|----------|-------|-------------|---------|
| `DATABASE_URL` | Both | PostgreSQL connection string (Supabase) | `postgresql://user:pass@host:5432/db` |
| `ANTHROPIC_API_KEY` | Engine | Anthropic Claude API key for LLM extraction | `sk-ant-...` |
| `SERPER_API_KEY` | Engine | Serper web search API key | `4d814abf...` |
| `GOOGLE_PLACES_API_KEY` | Engine | Google Places API key | `AIzaSy...` |

### Optional Variables

| Variable | Layer | Description | Default |
|----------|-------|-------------|---------|
| `LENS_ID` | Engine | Default lens identifier | None (explicit selection required) |
| `NODE_ENV` | Frontend | Node.js environment | `development` |
| `CI` | Tests | Non-interactive test mode | Not set |

### Environment File Locations

| File | Purpose | Committed? |
|------|---------|-----------|
| `.env` (root) | Engine environment variables | No (gitignored) |
| `web/.env` | Frontend environment variables | No (gitignored) |
| `engine/config/sources.yaml` | Connector API keys and configs | No (gitignored) |

---

## Configuration Files

### `engine/config/app.yaml` — Application Config

Controls lens resolution precedence (architecture.md 3.1):

```yaml
# Lens resolution precedence:
#   1. CLI override (--lens flag)
#   2. Environment variable (LENS_ID)
#   3. Application config (this file → default_lens)
#   4. Dev/Test fallback (not implemented yet)

default_lens: null  # null = require explicit selection
```

### `engine/config/extraction.yaml` — Extraction Config

Controls LLM model selection and trust levels:

```yaml
llm:
  model: "claude-haiku-4-5"

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

### `engine/config/sources.yaml` — Connector Config

**Not committed to git.** Copy from `sources.yaml.example`:

```bash
cp engine/config/sources.yaml.example engine/config/sources.yaml
```

Contains per-connector configuration:
- API keys
- Base URLs
- Timeouts
- Rate limits
- Default parameters

**Connectors configured:**
- `serper` — Web search (gl: uk, hl: en, num: 10)
- `google_places` — Places API v1 (field mask, location bias)
- `openstreetmap` — Overpass API (50km radius, Edinburgh center)
- `open_charge_map` — EV charging (GB, max 100 results)
- `sport_scotland` — WFS (Edinburgh bounding box, EPSG:4326)
- `edinburgh_council` — Council data (disabled by default)

### `engine/config/schemas/entity.yaml` — Entity Schema

**Single source of truth** for the Entity data model. Defines all fields, types, validation rules, and generation hints.

```bash
# Validate
python -m engine.schema.generate --validate

# Regenerate all derived schemas
python -m engine.schema.generate --all
```

### `engine/config/entity_model.yaml` — Entity Model Config

Additional entity model configuration.

### `engine/config/monitoring_alerts.yaml` — Monitoring

Alert configuration for system monitoring.

---

## Lens Configuration

Each lens is a comprehensive YAML file defining all domain knowledge.

**Location:** `engine/lenses/<lens_id>/lens.yaml`

**Current lenses:**
- `engine/lenses/edinburgh_finds/lens.yaml` — Sports discovery in Edinburgh
- `engine/lenses/wine/lens.yaml` — Wine discovery (skeleton)

**Lens structure:**
```yaml
schema: lens/v1           # Schema version (required)

vocabulary:               # Query interpretation vocabulary
  activity_keywords: [...]
  location_indicators: [...]
  facility_keywords: [...]

connector_rules:          # Connector routing rules
  sport_scotland:
    priority: high
    triggers: [...]

facets:                   # Dimension display configuration
  activity:
    dimension_source: canonical_activities
    ui_label: "Activities"

values:                   # Canonical value registry
  - key: padel
    facet: activity
    display_name: "Padel"

mapping_rules:            # Raw data -> canonical dimension rules
  - id: map_padel_from_name
    pattern: "(?i)padel"
    canonical: "padel"

module_triggers:          # When to attach domain modules
  - when: { facet: activity, value: padel }
    add_modules: [sports_facility]

modules:                  # Module schemas and extraction rules
  sports_facility:
    field_rules: [...]

confidence_threshold: 0.7  # Minimum confidence for mapping
```

---

## Connector Registry (`engine/orchestration/registry.py`)

Hardcoded connector metadata (not YAML-configured):

| Connector | Phase | Cost/Call | Trust | Timeout | Daily Limit |
|-----------|-------|-----------|-------|---------|-------------|
| serper | discovery | $0.010 | 0.75 | 30s | 2,500 |
| google_places | enrichment | $0.017 | 0.95 | 30s | 1,000 |
| openstreetmap | discovery | $0.000 | 0.70 | 60s | 10,000 |
| sport_scotland | enrichment | $0.000 | 0.90 | 60s | 10,000 |
| edinburgh_council | enrichment | $0.000 | 0.90 | 60s | 10,000 |
| open_charge_map | enrichment | $0.000 | 0.80 | 60s | 10,000 |

---

## Frontend Configuration

### `web/tsconfig.json` — TypeScript Config

Standard Next.js TypeScript configuration with path alias `@/` mapping to project root.

### `web/postcss.config.mjs` — PostCSS

Tailwind CSS v4 integration via `@tailwindcss/postcss`.

### `web/eslint.config.mjs` — ESLint

Next.js default ESLint configuration.

### `web/next.config.ts` — Next.js Config

Next.js 16 configuration (default settings).

---

## Third-Party Service Setup

### Supabase (PostgreSQL)

1. Create a project at [supabase.com](https://supabase.com)
2. Copy the connection string from Settings > Database
3. Set as `DATABASE_URL` in both `.env` and `web/.env`

### Anthropic Claude

1. Get API key from [console.anthropic.com](https://console.anthropic.com)
2. Set as `ANTHROPIC_API_KEY`
3. Model: `claude-haiku-4-5` (configured in `extraction.yaml`)

### Serper

1. Sign up at [serper.dev](https://serper.dev)
2. Copy API key
3. Add to `engine/config/sources.yaml`

### Google Places

1. Enable Places API at [Google Cloud Console](https://console.cloud.google.com)
2. Create API key with Places API restriction
3. Add to `engine/config/sources.yaml`

### Sport Scotland

1. Register at [Spatial Hub Scotland](https://data.spatialhub.scot)
2. Get JWT token
3. Add to `engine/config/sources.yaml`

---

## Related Documentation

- **Onboarding:** [ONBOARDING.md](ONBOARDING.md) — Setup walkthrough
- **Backend:** [BACKEND.md](BACKEND.md) — Module descriptions
- **Deployment:** [DEPLOYMENT.md](DEPLOYMENT.md) — Environment setup
