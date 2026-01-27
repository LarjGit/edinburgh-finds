# Codebase Structure

**Analysis Date:** 2026-01-27

## Directory Layout

```
edinburgh_finds/
├── engine/                           # Python ETL pipeline (data ingestion & extraction)
│   ├── config/
│   │   └── schemas/                  # YAML schemas (single source of truth)
│   │       └── entity.yaml           # Universal Entity schema (generates Python/Prisma/TS)
│   ├── ingestion/                    # Raw data fetching from 6 sources
│   │   ├── base.py                   # BaseConnector interface
│   │   ├── connectors/               # 6 data source implementations
│   │   │   ├── serper.py
│   │   │   ├── google_places.py
│   │   │   ├── open_street_map.py
│   │   │   ├── sport_scotland.py
│   │   │   ├── edinburgh_council.py
│   │   │   └── open_charge_map.py
│   │   ├── cli.py                    # CLI: python -m engine.ingestion.cli run --query "..."
│   │   ├── deduplication.py          # Duplicate detection
│   │   ├── storage.py                # Filesystem save operations
│   │   ├── health_check.py           # Connector health/rate limit checks
│   │   ├── retry_logic.py            # Exponential backoff
│   │   └── rate_limiting.py          # Token bucket rate limiter
│   ├── extraction/                   # Structured data extraction (deterministic + LLM)
│   │   ├── base.py                   # BaseExtractor interface
│   │   ├── extractors/               # Per-source extractors (deterministic extraction)
│   │   ├── models/                   # Extraction Pydantic models (LLM output schemas)
│   │   ├── prompts/                  # LLM prompts for unstructured data
│   │   ├── run.py                    # Main extraction logic (heuristic → extractor → LLM)
│   │   ├── cli.py                    # CLI: python -m engine.extraction.cli single <id>
│   │   ├── llm_client.py             # Anthropic API wrapper
│   │   ├── llm_cache.py              # In-memory LLM caching by request hash
│   │   ├── deduplication.py          # ID → Slug → Fuzzy match
│   │   ├── merging.py                # Field merging with trust hierarchy
│   │   ├── entity_classifier.py      # Deterministic entity_class assignment
│   │   ├── validation/               # Custom validators (phone, URL, postcode)
│   │   ├── health_check.py           # Extraction system health
│   │   ├── quarantine.py             # Failed extraction tracking
│   │   ├── logging_config.py         # Structured logging setup
│   │   └── cost_report.py            # LLM cost tracking
│   ├── orchestration/                # Intelligent multi-source control plane
│   │   ├── orchestrator.py           # Main execution loop (phase barriers, early stopping)
│   │   ├── planner.py                # Query analysis → connector selection → execution plan
│   │   ├── registry.py               # Connector metadata registry (6 connectors defined)
│   │   ├── adapters.py               # Async → sync bridge for connectors
│   │   ├── execution_context.py      # Shared mutable state (candidates, accepted, metrics)
│   │   ├── execution_plan.py         # ExecutionPhase, ConnectorSpec, ExecutionPlan models
│   │   ├── conditions.py             # Early stopping conditions (budget, confidence, quality)
│   │   ├── query_features.py         # Query analysis (category search detection)
│   │   ├── extraction_integration.py # Bridge to extraction system
│   │   ├── persistence.py            # Save accepted entities to database
│   │   ├── types.py                  # Common types (IngestRequest, IngestionMode)
│   │   ├── cli.py                    # CLI: python -m engine.orchestration.cli run "query"
│   │   └── [*_test.py]               # Comprehensive unit tests (16 test modules)
│   ├── lenses/                       # Vertical-specific interpretation (stub)
│   │   └── [future lens implementations]
│   ├── schema/                       # Schema generation system (single source of truth)
│   │   ├── parser.py                 # YAML schema parser
│   │   ├── core.py                   # Core schema data structures
│   │   ├── types.py                  # Type definitions
│   │   ├── generators/               # Code generation backends
│   │   │   ├── python_fieldspec.py   # Generates engine/schema/entity.py
│   │   │   ├── prisma.py             # Generates web/prisma/schema.prisma
│   │   │   ├── pydantic_extraction.py # Generates extraction Pydantic models
│   │   │   └── typescript.py         # Generates web/lib/types/generated/*.ts
│   │   ├── generate.py               # Main generator (coordinates all backends)
│   │   ├── cli.py                    # CLI: python -m engine.schema.generate --all
│   │   └── __main__.py               # Entry point
│   ├── data/
│   │   └── raw/                      # Persisted raw ingestion data (organized by source)
│   │       ├── serper/
│   │       ├── google_places/
│   │       ├── openstreetmap/
│   │       ├── sport_scotland/
│   │       ├── edinburgh_council/
│   │       └── open_charge_map/
│   ├── docs/                         # Backend documentation
│   ├── migrations/                   # Prisma migrations
│   └── [root-level utility scripts]
│       ├── ingest.py                 # Quick ingestion test
│       ├── run_seed.py               # Seed database with test data
│       └── [other dev scripts]
│
├── web/                              # Next.js 16 (React 19) frontend
│   ├── app/                          # Next.js App Router
│   │   ├── page.tsx                  # Home page (entity listing + filtering examples)
│   │   ├── layout.tsx                # Root layout
│   │   └── globals.css               # Global Tailwind styles
│   ├── lib/                          # Shared utilities
│   │   ├── prisma.ts                 # Prisma client singleton
│   │   ├── entity-queries.ts         # High-level Prisma queries (findMany, filters)
│   │   ├── entity-helpers.ts         # Entity parsing (dimensions, modules)
│   │   ├── lens-query.ts             # Lens query builder (vertical-specific filters)
│   │   ├── utils.ts                  # Helper functions (formatting, parsing JSON)
│   │   └── types/                    # TypeScript type definitions
│   │       └── generated/            # Auto-generated types from YAML schemas (do not edit)
│   ├── prisma/                       # Prisma ORM configuration
│   │   ├── schema.prisma             # Generated database schema (do not edit)
│   │   └── migrations/               # Automatic migration history
│   ├── public/                       # Static assets
│   ├── types/                        # Legacy types (consolidate into lib/types/)
│   ├── package.json                  # Dependencies: Next.js 16, React 19, Prisma 7, Tailwind 4
│   ├── tsconfig.json                 # TypeScript configuration
│   ├── next.config.ts                # Next.js configuration
│   └── docs/                         # Frontend documentation
│
├── conductor/                        # Gemini Conductor development workflow
│   ├── tracks.md                     # Current active development track
│   ├── tracks/                       # Development tracks (phases)
│   │   ├── orchestration_persistence_20260127/  # Current track
│   │   │   ├── spec.md               # Feature specifications
│   │   │   ├── plan.md               # Task breakdown with checkboxes
│   │   │   └── metadata.json         # Track metadata (dates, status)
│   │   └── [archived tracks]/
│   ├── product.md                    # Product vision & USP
│   ├── product-guidelines.md         # Design tone, UX principles
│   ├── tech-stack.md                 # Technology choices & rationale
│   ├── workflow.md                   # Standard development workflow (TDD, phases)
│   └── archive/                      # Completed/archived tracks
│
├── tests/                            # Test suite (mirrors engine structure)
│   ├── engine/
│   │   ├── config/
│   │   ├── extraction/
│   │   ├── orchestration/            # 16+ comprehensive orchestration tests
│   │   └── [other test modules]
│   ├── lenses/
│   ├── modules/
│   ├── query/
│   └── [test utilities]
│
├── docs/                             # Project documentation (guides, decisions)
├── scripts/                          # Developer utility scripts
├── logs/                             # Runtime logs
├── .planning/                        # GSD codebase mapping (this directory)
│   └── codebase/
│       ├── ARCHITECTURE.md           # This document (layers, data flow, abstractions)
│       ├── STRUCTURE.md              # Directory layout, file purposes, where to add code
│       ├── STACK.md                  # Technology stack analysis
│       ├── INTEGRATIONS.md           # External services & APIs
│       ├── CONVENTIONS.md            # Coding patterns & style
│       ├── TESTING.md                # Testing framework & patterns
│       └── CONCERNS.md               # Technical debt & issues
│
└── [root configs]
    ├── CLAUDE.md                     # Project guidelines (architecture principles, commands)
    ├── .env                          # Environment variables (keys, database URL)
    ├── .env.example                  # Template for .env
    ├── .eslintrc.json                # ESLint configuration
    ├── .prettierrc.json              # Prettier code formatting
    └── [git, github, obsidian configs]
```

## Directory Purposes

**`engine/`:**
- Purpose: Python backend - data ingestion, extraction, orchestration
- Contains: Connectors, extractors, orchestration control plane, schema generation
- Key files: `orchestration/cli.py` (main entry), `schema/generate.py` (single source of truth)
- Language: Python 3.x with Pydantic + Prisma + Instructor

**`engine/config/schemas/`:**
- Purpose: Single source of truth for all data models
- Contains: YAML schema files (currently: `entity.yaml`)
- Key files: `entity.yaml` (universal entity schema for all verticals)
- Generated from: Python FieldSpecs, Prisma schema, TypeScript interfaces

**`engine/ingestion/`:**
- Purpose: Fetch raw data from 6 external sources
- Contains: 6 connector implementations, deduplication, health checks
- Key files: `registry.py` is dynamically loaded by orchestration
- Pattern: Each connector inherits BaseConnector, implements fetch() → save()

**`engine/extraction/`:**
- Purpose: Transform raw payloads into structured entities
- Contains: Per-source extractors, LLM client, deduplication, merging
- Key files: `run.py` (main extraction logic), `entity_classifier.py` (determine entity_class)
- Pattern: Heuristic check → source extractor → LLM if needed → validate → split attributes

**`engine/orchestration/`:**
- Purpose: Intelligent multi-source query orchestration
- Contains: Planner, Orchestrator, Registry, ExecutionContext, Adapters, Persistence
- Key files: `cli.py` (user entry), `planner.py` (connector selection), `orchestrator.py` (execution loop)
- Test coverage: 16 test modules with 100+ test cases

**`engine/schema/`:**
- Purpose: Code generation from YAML schemas
- Contains: YAML parser, 4 code generators (Python, Prisma, Pydantic, TypeScript)
- Key files: `generate.py` (main generator), `generators/` (backend implementations)
- Usage: `python -m engine.schema.generate --all` regenerates all derived files

**`engine/data/raw/`:**
- Purpose: Persisted raw ingestion payloads (for audit trail & reprocessing)
- Contains: Subdirectories per source, JSON files organized by timestamp
- Pattern: `<source>/<timestamp>_<hash>.json` naming convention
- Lifecycle: Created by connectors, referenced by ExtractedEntity records

**`web/`:**
- Purpose: Next.js 16 discovery UI
- Contains: App Router pages, Prisma client, styling
- Key files: `app/page.tsx` (home page), `lib/prisma.ts` (DB client), `prisma/schema.prisma` (auto-generated)
- Dependencies: React 19, Tailwind 4, Prisma 7, shadcn/ui

**`web/app/`:**
- Purpose: Next.js App Router pages
- Contains: `page.tsx` (home), `layout.tsx` (root layout), `globals.css`
- Pattern: Server components by default, can use "use client" for interactivity
- Entry: Home page queries all entities, renders with example filters

**`web/lib/`:**
- Purpose: Shared utilities & database access
- Contains: Prisma client, entity queries, helpers, types
- Key files: `prisma.ts` (singleton), `entity-queries.ts` (Prisma wrappers)
- Pattern: Pure functions, no side effects (except DB queries in lib/)

**`web/prisma/`:**
- Purpose: Database schema and migrations
- Contains: `schema.prisma` (auto-generated, do not edit), migrations history
- Generation: From `engine/config/schemas/entity.yaml` via `python -m engine.schema.generate`
- Lifecycle: Edit YAML → regenerate → run `npx prisma migrate dev`

**`conductor/`:**
- Purpose: Gemini Conductor development workflow tracking
- Contains: Tracks (phases), specifications, plans, product guidelines
- Key files: `tracks.md` (active track), `workflow.md` (development process)
- Pattern: Structured task breakdown, checkpoint testing, TDD enforcement

**`tests/`:**
- Purpose: Test suite (unit + integration)
- Contains: Mirrors `engine/` structure, comprehensive orchestration tests
- Key files: `engine/orchestration/` has 16+ test modules
- Pattern: Pytest with markers (`@pytest.mark.slow` for >1s tests)
- Coverage target: >80% for all engine modules

**`.planning/codebase/`:**
- Purpose: Codebase analysis documents for GSD (Get-Shit-Done) workflow
- Contains: This STRUCTURE.md, ARCHITECTURE.md, STACK.md, CONVENTIONS.md, TESTING.md, CONCERNS.md
- Generated: Via `/gsd:map-codebase` orchestrator commands
- Consumed: By `/gsd:plan-phase` and `/gsd:execute-phase` commands

## Key File Locations

**Entry Points:**
- Backend orchestration: `engine/orchestration/cli.py`
- Backend extraction (direct): `engine/extraction/cli.py`
- Backend ingestion (direct): `engine/ingestion/cli.py`
- Schema generation: `engine/schema/generate.py`
- Frontend: `web/app/page.tsx`

**Configuration:**
- YAML schemas: `engine/config/schemas/entity.yaml`
- Prisma schema: `web/prisma/schema.prisma` (auto-generated)
- Environment: `.env` (API keys, DATABASE_URL)
- TypeScript: `web/tsconfig.json`, `web/next.config.ts`

**Core Logic:**
- Connector interface: `engine/ingestion/base.py`
- Extractor interface: `engine/extraction/base.py`
- Entity schema: `engine/schema/entity.py` (auto-generated)
- Orchestration: `engine/orchestration/orchestrator.py`
- Registry: `engine/orchestration/registry.py` (6 connectors defined)

**Testing:**
- Orchestration tests: `tests/engine/orchestration/` (16 test files)
- Extraction tests: `tests/engine/extraction/`
- Config tests: `tests/engine/config/`
- Lens tests: `tests/lenses/`

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `entity_classifier.py`, `llm_cache.py`)
- TypeScript files: `kebab-case.tsx` or `kebab-case.ts` (e.g., `entity-queries.ts`, `entity-helpers.ts`)
- Schema files: `snake_case.yaml` (e.g., `entity.yaml`)
- Test files: `*_test.py` or `test_*.py` (e.g., `orchestrator_test.py`)
- Generated files: Have "DO NOT EDIT" header comment

**Directories:**
- Source packages: `snake_case/` (e.g., `extraction/`, `orchestration/`)
- URL routes: `kebab-case/` (e.g., `api/entities/`, `[entity-id]/`)
- Feature directories: `snake_case/` matching feature name (e.g., `lenses/`, `modules/`)

**Classes & Types:**
- Python classes: `PascalCase` (e.g., `BaseConnector`, `ExecutionContext`, `ConnectorSpec`)
- TypeScript types: `PascalCase` (e.g., `Entity`, `ExtractedEntity`)
- Enums: `UPPER_SNAKE_CASE` in Python, `PascalCase` in TypeScript
- Constants: `UPPER_SNAKE_CASE` (e.g., `FUZZY_MATCH_THRESHOLD = 85`)

**Functions & Variables:**
- Python: `snake_case` (e.g., `select_connectors()`, `_normalize_name()`)
- TypeScript: `camelCase` (e.g., `formatAttributeKey()`, `parseModules()`)
- Private: Prefix with `_` (e.g., `_apply_budget_gating()`)
- Async: No special naming, use `async def` keyword

## Where to Add New Code

**New Feature (Full Vertical):**
- Primary code: `engine/orchestration/planner.py` for routing, `engine/lenses/` for YAML config
- Tests: `tests/engine/orchestration/` for new connector selection logic
- Schema: Extend `engine/config/schemas/entity.yaml` if new canonical dimensions needed
- Frontend: `web/app/` for new pages, `web/lib/` for queries

**New Connector:**
1. Implementation: `engine/ingestion/connectors/<connector_name>.py` (inherit BaseConnector)
2. Registry: Add entry to `engine/orchestration/registry.py` with ConnectorSpec
3. Extractor: `engine/extraction/extractors/<connector_name>.py` (inherit BaseExtractor)
4. Adapter: Entry in `engine/orchestration/adapters.py` for async bridge
5. Tests: `tests/engine/orchestration/` with connector selection test
6. No schema changes needed (universal entity model)

**New Dimension (e.g., canonical_certifications):**
1. Schema: Add field to `engine/config/schemas/entity.yaml`
2. Regenerate: `python -m engine.schema.generate --all`
3. Migrate: `cd web && npx prisma migrate dev`
4. Lens config: Update YAML lens config if vertical-specific mapping needed
5. Tests: Add to orchestration/extraction tests for coverage

**New Query Feature:**
1. Feature detection: `engine/orchestration/query_features.py`
2. Selection logic: `engine/orchestration/planner.py:select_connectors()`
3. Tests: `tests/engine/orchestration/test_planner.py`
4. CLI: `engine/orchestration/cli.py` handles formatting

**Frontend Page/Component:**
1. Page: `web/app/<feature>/page.tsx` or modify `web/app/page.tsx`
2. Queries: `web/lib/entity-queries.ts` for new Prisma queries
3. Styling: Use Tailwind classnames in component, `web/app/globals.css` for global
4. Types: Use auto-generated types from `web/lib/types/generated/`

**Utilities:**
- Shared helpers: `web/lib/utils.ts` (TypeScript) or `engine/extraction/utils/` (Python)
- Extractors: `engine/extraction/extractors/` for per-source logic
- Validators: Inline in extractors or in `engine/extraction/validation/`

## Special Directories

**`engine/data/raw/`:**
- Purpose: Persisted raw ingestion payloads
- Generated: Yes (created by connectors at runtime)
- Committed: No (gitignored)
- Lifecycle: Connectors write, Extraction reads, can be deleted (re-ingestion regenerates)

**`web/prisma/migrations/`:**
- Purpose: Database migration history
- Generated: Yes (created by `prisma migrate dev`)
- Committed: Yes (track schema evolution)
- Manual editing: Not recommended (Prisma manages)

**`web/lib/types/generated/`:**
- Purpose: Auto-generated TypeScript types from YAML schemas
- Generated: Yes (from `engine/schema/generate.py`)
- Committed: Yes (but marked "DO NOT EDIT")
- Manual editing: Never - regenerate via Python schema tool

**`engine/schema/` generated files:**
- `engine/schema/entity.py` → Pydantic FieldSpec for extraction validation
- `web/prisma/schema.prisma` → Prisma database schema
- `web/lib/types/generated/*.ts` → TypeScript types
- All marked with "DO NOT EDIT - AUTO-GENERATED" headers
- All generated together via `python -m engine.schema.generate --all`

**`conductor/tracks/<track_id>/`:**
- Purpose: Phase/sprint tracking with specifications
- Structure: `spec.md` (requirements), `plan.md` (tasks), `metadata.json` (dates)
- Lifecycle: Active track in `conductor/tracks.md`, completed tracks moved to `conductor/archive/`
- TDD enforcement: Tasks marked with status checkboxes ([~] in progress, [x] complete)

---

*Structure analysis: 2026-01-27*
