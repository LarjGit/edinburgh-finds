# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Edinburgh Finds is a local discovery platform built on a dual-stack architecture:
- **Frontend**: Next.js 16 (React 19) with TypeScript and Tailwind CSS v4
- **Backend/ETL**: Python 3.12+ data ingestion and extraction engine
- **Database**: PostgreSQL (Supabase) accessed via Prisma ORM from both stacks
- **AI/LLM**: Anthropic Claude via `instructor` for structured data extraction

The system uses a **Universal Entity** model where vertical-specific logic (e.g., "Sports", "Wine", "Pottery") is defined via configuration "Lenses" rather than hardcoded schemas. The engine processes raw data into structured entities, while lenses provide domain-specific interpretation.

## Critical Architecture Principles

### 1. YAML-First Schema Management

**⚠️ NEVER EDIT `schema.prisma` OR `entity.py` MANUALLY**

The project uses a YAML-first approach where all schema definitions live in YAML files and generate artifacts for multiple targets:

- **Source of Truth**: `engine/config/schemas/*.yaml`
- **Generated Artifacts**:
  - `engine/schema/entity.py` (Pydantic models + FieldSpecs)
  - `web/prisma/schema.prisma` (Prisma schema)
  - TypeScript types (if applicable)

**Schema Workflow**:
```bash
# 1. Edit YAML definitions
# Edit: engine/config/schemas/*.yaml

# 2. Generate all artifacts
python -m engine.schema.generate

# 3. Validate generation
python -m engine.schema.generate --validate

# 4. Create database migration
npx prisma migrate dev --name <migration_name> --schema=web/prisma/schema.prisma

# 5. Generate Prisma clients for both Python and JavaScript
npx prisma generate --schema=web/prisma/schema.prisma
```

### 2. Engine-Lens Architecture

The **engine** is vertical-agnostic and knows only about:
- `Entity` (the universal data model)
- `Dimensions` (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
- `Modules` (namespaced JSONB structures)

**Lenses** provide domain-specific interpretation:
- Located in: `lenses/<lens_name>/` (e.g., `lenses/edinburgh_finds/`)
- Define facets, categories, and UI mapping rules
- Map raw categories to canonical dimension values

The engine NEVER contains domain logic like "this is a sports venue" - that interpretation happens in lenses.

### 3. Prisma Client Parity

Both `web` (JavaScript/TypeScript) and `engine` (Python) use Prisma clients that must be kept in sync:
- **Always run** `npx prisma generate --schema=web/prisma/schema.prisma` after schema changes
- This generates clients for both languages from the same schema

## Common Development Commands

### Initial Setup

```bash
# Frontend dependencies
cd web
npm install

# Backend dependencies (from root)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r engine/requirements.txt

# Database setup
npx prisma generate --schema=web/prisma/schema.prisma
npx prisma migrate dev --schema=web/prisma/schema.prisma
```

### Daily Development

```bash
# Frontend development server
cd web
npm run dev  # Access at http://localhost:3000

# Frontend linting
cd web
npm run lint

# Run Python tests
pytest                    # All tests
pytest -m "not slow"      # Fast tests only
pytest path/to/test.py    # Single test file

# Test with coverage
pytest --cov=engine --cov-report=html
```

### Schema Management

```bash
# Generate all schema artifacts from YAML
python -m engine.schema.generate

# Validate schema without writing
python -m engine.schema.generate --validate

# Generate specific schema
python -m engine.schema.generate --schema entity --force

# After YAML changes, apply to database
npx prisma migrate dev --name <migration_name> --schema=web/prisma/schema.prisma
npx prisma generate --schema=web/prisma/schema.prisma
```

### Data Ingestion & Extraction

```bash
# Run individual connectors (Stage 1: Raw Data Collection)
python engine/run_osm_manual.py
python engine/scripts/run_serper_connector.py
python engine/scripts/run_google_places_connector.py
python engine/scripts/run_sport_scotland_connector.py

# Run lens-aware extraction (Stage 2: Entity Extraction)
python engine/scripts/run_lens_aware_extraction.py

# Manage extraction queue
python -m engine.extraction.cli --retry-failed --max-retries 3
```

### Pre-Commit Checks

```bash
# Frontend build verification
cd web && npm run build

# Schema drift check
python -m engine.schema.generate --validate

# All tests must pass
pytest
```

## Key Architectural Patterns

### Entity Classification System

Entities use a **universal classification** via `entity_class` field:
- `place` - Physical locations
- `person` - Individuals (coaches, instructors)
- `organization` - Clubs, leagues, businesses
- `event` - Time-bound occurrences
- `thing` - Products, equipment

### Dimension Arrays

Multi-valued facets stored as PostgreSQL `text[]` arrays with GIN indexes:
- `canonical_activities[]` - Activities provided (e.g., "padel", "tennis")
- `canonical_roles[]` - Functional roles (e.g., "provides_facility", "teaches")
- `canonical_place_types[]` - Place classifications (e.g., "sports_centre", "park")
- `canonical_access[]` - Access requirements (e.g., "public", "members_only")
- `raw_categories[]` - Unprocessed discovery signals (NOT indexed, NOT queried)

These are **opaque to the engine** - lenses provide interpretation via mapping rules.

### Module System

The `modules` JSONB field stores namespaced module data:
```json
{
  "core": {"entity_id": "...", "entity_name": "..."},
  "location": {"street_address": "...", "city": "..."},
  "sports_facility": {"court_count": 4, "surface_type": "artificial_grass"}
}
```

Universal modules (core, location, contact, hours) + lens-specific modules determined by module triggers.

## File Structure Reference

```
engine/                          # Python backend/ETL
├── config/schemas/*.yaml        # YAML schema definitions (SOURCE OF TRUTH)
├── schema/                      # Schema generation tooling
│   ├── cli.py                   # Schema generation CLI
│   ├── entity.py                # Generated Pydantic models (DO NOT EDIT)
│   ├── parser.py                # YAML parser
│   └── generators/              # Code generators for different targets
├── extraction/                  # LLM-based entity extraction
│   ├── base.py                  # Core extraction logic
│   ├── entity_classifier.py    # entity_class determination
│   ├── llm_client.py            # Anthropic integration
│   └── extractors/              # Lens-specific extractors
├── ingestion/                   # Raw data collection
│   ├── connectors/              # API connectors (Google, OSM, etc.)
│   ├── cli.py                   # Ingestion CLI
│   └── storage.py               # RawIngestion storage
├── lenses/                      # Lens registry and operations
│   ├── loader.py                # Lens configuration loader
│   └── validator.py             # Lens validation
├── modules/                     # Module validation system
│   └── validator.py             # Module schema validator
└── scripts/                     # ETL job entry points

web/                             # Next.js frontend
├── app/                         # App Router pages
│   ├── layout.tsx               # Root layout
│   └── page.tsx                 # Home page
├── lib/                         # Shared utilities
│   ├── entity-queries.ts        # Entity database queries
│   ├── lens-query.ts            # Lens-aware query logic
│   └── prisma.ts                # Prisma client singleton
├── prisma/
│   └── schema.prisma            # Generated Prisma schema (DO NOT EDIT)
└── types/                       # TypeScript type definitions

lenses/                          # Lens configurations (domain logic)
├── edinburgh_finds/             # Edinburgh vertical
└── wine_discovery/              # Wine vertical
```

## Testing Strategy

### Python Testing

- Test framework: pytest
- Test files: Located alongside source files with `_test.py` or `test_*.py` naming
- Coverage target: >80%
- Markers: Use `@pytest.mark.slow` for long-running tests

### Test-Driven Development

Follow TDD workflow (see `conductor/workflow.md`):
1. **Red**: Write failing tests that define expected behavior
2. **Green**: Write minimum code to pass tests
3. **Refactor**: Improve code while keeping tests green

## Environment Variables

Required in `.env` file at project root:

- `DATABASE_URL` - PostgreSQL connection string (required)
- `ANTHROPIC_API_KEY` - For LLM extraction (required)
- `GOOGLE_PLACES_API_KEY` - For Google Places connector (optional)
- `SERPER_API_KEY` - For Serper search connector (optional)
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `NODE_ENV` - Environment mode (default: development)

## Database Notes

- **Database**: PostgreSQL 14+ (uses native features: ARRAY types, GIN indexes, JSONB)
- **NOT SQLite compatible** - relies on Postgres-specific features
- **Migrations**: Always use Prisma migrate, never manual SQL
- **Access**: Use Prisma Client from both Python and JavaScript

## Conductor Integration

This project uses **Conductor** for context-driven development:
- Product context: `conductor/product.md`
- Tech stack: `conductor/tech-stack.md`
- Workflow: `conductor/workflow.md`
- Tracks: `conductor/tracks.md` (master list)
- Track plans: `conductor/tracks/<track_id>/plan.md`

See the CLAUDE.md [GLOBAL RULES] section for Conductor workflows and protocols.
