# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Documentation Lookup Strategy

**ALWAYS use Context7 for library documentation lookups.** Before implementing features or debugging issues with external libraries (Next.js, React, Prisma, Pydantic, pytest, Tailwind, shadcn/ui, Anthropic SDK, etc.), use the Context7 MCP tools to retrieve up-to-date documentation and code examples:

1. Use `resolve-library-id` to find the correct library ID
2. Use `query-docs` with the library ID to get relevant documentation
3. This ensures you're working with current API patterns and best practices

Example workflow:
- Need to implement Prisma query → Context7 lookup → Implement with current syntax
- Debugging Next.js App Router issue → Context7 lookup → Apply current patterns
- Using Pydantic validators → Context7 lookup → Use latest validator syntax

## Core Concept: Universal Entity Framework

This is a **vertical-agnostic discovery platform** powered by AI-scale data ingestion. The architecture separates a universal **Entity Engine** (Python) from vertical-specific **Lens Layers** (YAML config).

**Key Principle:** The engine knows nothing about "Padel" or "Wine". It works with generic `entity_class` (place, person, organization, event, thing), multi-valued dimension arrays (`canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`), and flexible JSON `modules`. Vertical logic lives in Lens YAML configs only.

**Scaling Strategy:** Adding a new vertical (e.g., Wine Discovery, Restaurant Finder) should require ZERO engine code changes - only a new `lens.yaml` configuration file.

## Project Structure

```
edinburgh_finds/
├── engine/                    # Python ETL pipeline (data ingestion & extraction)
│   ├── config/schemas/        # YAML schemas (single source of truth)
│   ├── ingestion/             # Connectors for raw data fetching
│   │   └── connectors/        # 6 data sources (Serper, GooglePlaces, OSM, etc.)
│   ├── extraction/            # Hybrid extraction (deterministic + LLM)
│   │   ├── extractors/        # Per-source extractors
│   │   └── prompts/           # LLM prompts for unstructured data
│   ├── orchestration/         # Intelligent query orchestration (runtime control plane)
│   ├── lenses/                # Lens layer for vertical-specific interpretation
│   ├── schema/                # Schema generation system
│   │   └── generators/        # Auto-generate Python, Prisma, TypeScript from YAML
│   └── data/raw/              # Stored raw ingestion data
├── web/                       # Next.js 16 (React 19) frontend
│   ├── app/                   # Next.js App Router
│   ├── lib/                   # Shared utilities
│   └── prisma/                # Prisma schema (auto-generated)
└── conductor/                 # Gemini Conductor workflow (Context-Driven Development)
    └── tracks/                # Development tracks with specs and plans
```

## Development Commands

### Setup
```bash
# Frontend (Next.js)
cd web && npm install

# Backend (Python Engine)
python -m pip install -r engine/requirements.txt
```

### Daily Development
```bash
# Frontend
cd web
npm run dev          # Start Next.js dev server (http://localhost:3000)
npm run build        # Production build
npm run lint         # ESLint

# Backend (Engine)
pytest                        # Run all tests
pytest -m "not slow"          # Run fast tests only (excludes @pytest.mark.slow)
pytest --cov=engine --cov-report=html  # Generate coverage report (target: >80%)
pytest engine/orchestration/  # Run specific module tests
```

### Schema Management (CRITICAL)
```bash
# YAML schemas are the single source of truth
# Location: engine/config/schemas/*.yaml

# Validate schemas before committing
python -m engine.schema.generate --validate

# Regenerate all derived schemas (Python FieldSpecs, Prisma, TypeScript)
python -m engine.schema.generate --all

# When you modify a YAML schema:
# 1. Edit engine/config/schemas/<entity>.yaml
# 2. Run: python -m engine.schema.generate --all
# 3. Generated files are marked "DO NOT EDIT" - never modify them directly
```

### Data Pipeline Commands
```bash
# Ingestion (fetch raw data)
python -m engine.ingestion.cli run --query "padel courts Edinburgh"

# Extraction (structured data from raw)
python -m engine.extraction.cli single <raw_ingestion_id>
python -m engine.extraction.cli source serper --limit 10

# Orchestration (intelligent multi-source query)
python -m engine.orchestration.cli run "padel clubs in Edinburgh"
```

## Architecture Principles

### 1. Engine Purity (Vertical-Agnostic)
- **NEVER** hardcode vertical-specific terms ("Padel", "Wine", "Tennis") in engine code
- Use `entity_class` (place/person/organization/event/thing) not "Venue" or domain types
- Store dimensions as Postgres arrays: `canonical_activities TEXT[]`, `canonical_roles TEXT[]`
- Vertical-specific data goes in JSON `modules` field, interpreted by Lenses
- If you need to add domain logic, it belongs in a Lens YAML config, NOT engine code

### 2. Schema Single Source of Truth
- All schema definitions live in `engine/config/schemas/*.yaml`
- YAML auto-generates:
  - Python FieldSpecs → `engine/schema/<entity>.py`
  - Prisma schemas → `web/prisma/schema.prisma` and `engine/prisma/schema.prisma`
  - TypeScript interfaces → `web/lib/types/generated/<entity>.ts`
- **NEVER** edit generated files directly - they are overwritten on regeneration
- This eliminates schema drift and enables horizontal scaling (new verticals = new YAML file)

### 3. Test-Driven Development (TDD)
- **Red → Green → Refactor** workflow is mandatory for all tasks
- Write failing tests FIRST, confirm they fail, then implement
- Coverage target: >80% for all new code
- Use `pytest.mark.slow` for tests >1 second (allows `pytest -m "not slow"` for fast iteration)

### 4. Data Flow: Ingest → Extract → Merge → Display
1. **Ingestion** (`engine/ingestion/`): Connectors fetch raw data from 6 sources → `RawIngestion` records
2. **Extraction** (`engine/extraction/`): Hybrid engine (deterministic rules + LLM) → structured entities
3. **Deduplication** (`engine/extraction/deduplication.py`): External ID → Slug → Fuzzy match
4. **Merging** (`engine/extraction/merging.py`): Field-level trust hierarchy (Admin > Official > Crowdsourced)
5. **Display** (`web/`): Next.js frontend with Prisma queries

### 5. Orchestration: Intelligent Multi-Source Queries
- **Orchestration kernel** (`engine/orchestration/`) provides runtime-safe, phase-ordered control plane
- Registry (`registry.py`): Central metadata for all 6 connectors (cost, trust, phase, timeout)
- Planner (`planner.py`): Query analysis → intelligent connector selection → execution plan
- Adapters (`adapters.py`): Bridge async connectors to orchestrator, normalize results
- Deduplication runs at orchestration level (cross-source) before database persistence
- CLI: `python -m engine.orchestration.cli run "your query here"`

## Conductor Workflow (Context-Driven Development)

This project uses **Gemini Conductor** methodology for structured development:

- **Location:** `conductor/tracks/<track_id>/` contains `spec.md`, `plan.md`, `metadata.json`
- **Active Track:** Check `conductor/tracks.md` for current track
- **Workflow:** All tasks follow strict TDD lifecycle (see `conductor/workflow.md`)
  1. Mark task `[~]` in `plan.md` before starting
  2. Write failing tests (Red)
  3. Implement to pass (Green)
  4. Refactor
  5. Commit with git notes
  6. Update `plan.md` with commit SHA
- **Phase Completion:** Triggers verification protocol (automated tests + manual verification + checkpoint commit)
- **Quality Gates:** All tests pass, >80% coverage, no linting errors, docs updated

**When working on tasks:**
- Always check the current track's `plan.md` for next available task
- Follow the 11-step Standard Task Workflow in `conductor/workflow.md`
- Phase completions trigger the full checkpointing protocol
- Tech stack changes must update `conductor/tech-stack.md` BEFORE implementation

## Tech Stack

### Frontend
- **Framework:** Next.js 16 (App Router), React 19
- **Styling:** Tailwind CSS v4, shadcn/ui components
- **Language:** TypeScript
- **ORM:** Prisma 7.3+ (PostgreSQL via Supabase)

### Backend (Engine)
- **Language:** Python 3.x
- **Validation:** Pydantic (schema-driven)
- **LLM:** Instructor + Anthropic Claude (for unstructured data extraction)
- **ORM:** Prisma Client Python
- **Testing:** pytest (with coverage, markers for `slow` tests)

### Database
- **Primary:** Supabase (PostgreSQL)
- **Indexes:** Multi-valued dimensions use Postgres `TEXT[]` arrays with GIN indexes
- **Modules:** JSONB for flexible vertical-specific attributes

## Content & Voice Guidelines

### Tone: "The Knowledgeable Local Friend"
- Warm, helpful, authoritative - never generic AI-sounding
- **Prohibited phrases:** "Located at," "Features include," "A great place for," "Welcome to"
- **Required style:** Contextual bridges like "Just a short walk from [Landmark]" or "Perfect for those who prefer [Specific Need]"
- Utility over hype: If expensive, say "Premium-priced". If basic, say "Functional and focused"

### Design Philosophy: "The Sophisticated Canvas"
- Agnostic elegance: No vertical tropes (no "neon green for Padel")
- Premium neutral aesthetic (shadcn/ui "neutral" base)
- Transform raw data (opening hours, specs) into visual components (tags, icons) not text blocks

### Technical Quality
- SEO: Every page needs unique meta-description, proper H-tag hierarchy (Next.js dynamic metadata)
- Data freshness: Always display "Last Verified" date or "Confidence Score"
- Performance: Aim for 100/100 Core Web Vitals (use Next.js ISR)
- Accessibility: WCAG 2.1 AA compliance

## Common Gotchas

### 1. Schema Changes Require Regeneration
When you modify `engine/config/schemas/*.yaml`:
```bash
python -m engine.schema.generate --all  # Must regenerate Python/Prisma/TypeScript
```
Never manually edit generated files - they have "DO NOT EDIT" headers.

### 2. Tests Use CI=true for Non-Interactive Mode
```bash
CI=true npm test  # Frontend: Prevents watch mode
pytest            # Backend: Already non-interactive
```

### 3. Entity Class vs. Vertical-Specific Types
**WRONG:**
```python
if entity_type == "Venue":  # ❌ Vertical-specific
    ...
```

**RIGHT:**
```python
if entity.entity_class == "place":  # ✅ Universal
    # Use lenses/modules for vertical interpretation
```

### 4. Pytest Markers for Test Performance
```bash
pytest                    # All tests (some slow)
pytest -m "not slow"      # Fast tests only (for quick iteration)
```
Mark slow tests with `@pytest.mark.slow` decorator.

### 5. Commit Message Format
```
<type>(<scope>): <description>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```
Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `conductor(plan)`, `conductor(checkpoint)`

### 6. Orchestration Registry
When adding a new connector to the orchestration system:
1. Add to `engine/orchestration/registry.py` with `ConnectorSpec` (cost, trust, phase, timeout)
2. Add adapter mapping in `engine/orchestration/adapters.py`
3. Write tests in `tests/engine/orchestration/test_registry.py`

## Key Files to Reference

- **Architecture:** `ARCHITECTURE.md` (system design, component interactions, data flows)
- **Product Mission:** `conductor/product.md` (core mission, USP, target audience)
- **Tech Stack:** `conductor/tech-stack.md` (deliberate technology choices)
- **Workflow:** `conductor/workflow.md` (TDD workflow, phase protocols, quality gates)
- **Design Guidelines:** `conductor/product-guidelines.md` (tone, UX principles, quality standards)
- **Current Work:** `conductor/tracks.md` → active track → `plan.md`

## Testing Strategy

### Unit Tests
- Every module must have corresponding tests
- Mock external dependencies (API calls, LLM calls)
- Test both success and failure cases
- Use fixtures for common setup

### Integration Tests
- Test complete data flows (ingest → extract → dedupe → merge)
- Verify database transactions
- Snapshot testing for extraction outputs

### Coverage Requirements
```bash
pytest --cov=engine --cov-report=html  # Generate HTML coverage report
# Target: >80% coverage for all modules
```

## Before Committing

1. **Schema validation:** `python -m engine.schema.generate --validate`
2. **Run tests:** `pytest` (backend), `cd web && npm run build` (frontend)
3. **Check linting:** `cd web && npm run lint`
4. **Verify coverage:** `pytest --cov=engine` (should be >80%)
5. **Update plan:** If working on Conductor task, update `plan.md` with commit SHA
6. **Git notes:** Attach task summary to commit using `git notes add -m "..." <commit_hash>`

## Environment Setup

### Required Environment Variables
```bash
# Engine (.env or environment)
ANTHROPIC_API_KEY=<your_key>      # For LLM extraction
SERPER_API_KEY=<your_key>         # For Serper connector
GOOGLE_PLACES_API_KEY=<your_key>  # For Google Places connector

# Web (web/.env)
DATABASE_URL=<supabase_postgres_url>
```

### Database Setup
```bash
cd web
npx prisma generate  # Generate Prisma client from schema
npx prisma db push   # Sync schema to Supabase (dev)
npx prisma migrate dev  # Create migration (production)
```

## Mobile-First Development

- Mobile view = "tool" (prioritize 'Directions' and 'Call' buttons)
- Desktop view = "resource" (prioritize 'Comparison' and 'Deep Research')
- Touch targets: 44x44px minimum
- Test on actual iPhone when possible
- Performance target: Acceptable on 3G/4G

## Support Resources

- **Conductor Tracks:** `conductor/tracks.md` lists all development tracks
- **Documentation:** `engine/docs/` contains detailed guides for extraction, ingestion, schema management
- **Test Examples:** Browse `tests/engine/` for testing patterns and fixtures
