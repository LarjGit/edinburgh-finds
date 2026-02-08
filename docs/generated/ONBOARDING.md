# Developer Onboarding Guide

**System:** Universal Entity Extraction Engine
**Reference Application:** Edinburgh Finds (demonstration lens only)

This guide will help you set up your local development environment and make your first contribution to this vertical-agnostic discovery platform.

## Prerequisites

Before starting, ensure you have these tools installed:

### Required Software

- **Python 3.10+** (for the engine)
  - Check: `python --version` or `python3 --version`
  - Install: [python.org](https://www.python.org/downloads/)

- **Node.js 18+** (for the frontend)
  - Check: `node --version`
  - Install: [nodejs.org](https://nodejs.org/) or use `nvm`

- **Git** (for version control)
  - Check: `git --version`
  - Install: [git-scm.com](https://git-scm.com/)

- **PostgreSQL** (via Supabase or local installation)
  - Supabase (recommended): [supabase.com](https://supabase.com/)
  - Local PostgreSQL: [postgresql.org](https://www.postgresql.org/)

### Required API Keys

You'll need these API keys for full functionality:

- **Anthropic API Key** (for LLM-based extraction)
  - Get: [console.anthropic.com](https://console.anthropic.com/)

- **Serper API Key** (for web search connector)
  - Get: [serper.dev](https://serper.dev/)

- **Google Places API Key** (for Google Places connector)
  - Get: [console.cloud.google.com](https://console.cloud.google.com/)

- **Supabase Database URL** (for PostgreSQL)
  - Get: [supabase.com/dashboard](https://supabase.com/dashboard) → Project Settings → Database → Connection String

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd edinburgh_finds
```

### 2. Environment Configuration

Create environment files for both frontend and backend:

**Backend (.env in project root):**
```bash
# Create .env file in project root
cat > .env << 'EOF'
ANTHROPIC_API_KEY=your_anthropic_key_here
SERPER_API_KEY=your_serper_key_here
GOOGLE_PLACES_API_KEY=your_google_places_key_here
EOF
```

**Frontend (web/.env):**
```bash
# Create .env file in web directory
cat > web/.env << 'EOF'
DATABASE_URL=your_supabase_postgres_url_here
EOF
```

**Security Note:** Never commit `.env` files. They're included in `.gitignore`.

### 3. Backend Setup (Python Engine)

```bash
# Install Python dependencies
python -m pip install -r engine/requirements.txt

# Verify installation
python -c "import pydantic, prisma, instructor; print('Backend dependencies installed successfully')"
```

**Optional: Use a virtual environment (recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
python -m pip install -r engine/requirements.txt
```

### 4. Frontend Setup (Next.js)

```bash
# Navigate to web directory
cd web

# Install Node.js dependencies
npm install

# Return to project root
cd ..
```

### 5. Database Setup (Prisma + Supabase)

```bash
cd web

# Generate Prisma client
npx prisma generate

# Push schema to database (development)
npx prisma db push

# Return to project root
cd ..
```

**For production migrations:**
```bash
cd web
npx prisma migrate dev --name init
cd ..
```

## Verify Your Setup

Run these commands to ensure everything is working:

### Backend Tests
```bash
# Run all tests
pytest

# Run fast tests only (excludes slow tests)
pytest -m "not slow"

# Check test coverage (target: >80%)
pytest --cov=engine --cov-report=html
```

### Frontend Build
```bash
cd web
npm run build
cd ..
```

### Schema Validation
```bash
python -m engine.schema.generate --validate
```

If all commands succeed, your environment is ready.

## Development Workflow

### Daily Commands

**Start Frontend Dev Server:**
```bash
cd web
npm run dev
# Visit http://localhost:3000
```

**Run Backend Tests:**
```bash
pytest                        # All tests
pytest -m "not slow"          # Fast tests only
pytest engine/orchestration/  # Specific module
```

**Lint Frontend:**
```bash
cd web
npm run lint
```

### Working with Schemas

The schema system is the single source of truth. All schemas are defined in YAML and auto-generate Python, Prisma, and TypeScript code.

**Schema Workflow:**
1. Edit YAML schema: `engine/config/schemas/<entity>.yaml`
2. Validate: `python -m engine.schema.generate --validate`
3. Regenerate: `python -m engine.schema.generate --all`
4. Never manually edit generated files (marked "DO NOT EDIT")

**Generated Files:**
- Python FieldSpecs → `engine/schema/<entity>.py`
- Prisma schemas → `web/prisma/schema.prisma` and `engine/prisma/schema.prisma`
- TypeScript interfaces → `web/lib/types/generated/<entity>.ts`

### Data Pipeline Commands

**Ingestion (fetch raw data):**
```bash
python -m engine.ingestion.cli run --query "padel courts Edinburgh"
```

**Extraction (structured data from raw):**
```bash
python -m engine.extraction.cli single <raw_ingestion_id>
python -m engine.extraction.cli source serper --limit 10
```

**Orchestration (intelligent multi-source query):**
```bash
python -m engine.orchestration.cli run "padel clubs in Edinburgh"
```

## Understanding the Architecture

This platform separates a universal **Entity Engine** (Python) from vertical-specific **Lens Layers** (YAML config).

### Core Principle: Engine Purity

The engine knows nothing about verticals like "Padel" or "Wine". It works with:

- **Generic entity classes:** `place`, `person`, `organization`, `event`, `thing`
- **Canonical dimensions:** `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`
- **Flexible modules:** JSONB field for vertical-specific attributes

All domain knowledge lives in Lens YAML configs only.

### 11-Stage Pipeline

```
Query → Lens Resolution → Planning → Ingestion → Raw Storage
      ↓
Source Extraction (primitives only) → Lens Application (canonical dimensions)
      ↓
Classification → Deduplication → Merge → Finalization → Entity Store
```

### Key Architectural Documents

Before making architectural changes, read these immutable documents:

1. **`docs/target/system-vision.md`** - Architectural Constitution (10 immutable invariants)
2. **`docs/target/architecture.md`** - Runtime Implementation Specification

### Project Structure

```
edinburgh_finds/
├── engine/                    # Python ETL pipeline
│   ├── config/schemas/        # YAML schemas (single source of truth)
│   ├── ingestion/connectors/  # 6 data sources (Serper, GooglePlaces, OSM, etc.)
│   ├── extraction/            # Hybrid extraction (deterministic + LLM)
│   ├── orchestration/         # Intelligent query orchestration
│   └── lenses/                # Lens layer (vertical-specific interpretation)
├── web/                       # Next.js 16 frontend
│   ├── app/                   # Next.js App Router
│   └── prisma/                # Prisma schema (auto-generated)
└── docs/                      # Documentation
    ├── target/                # Architectural authority
    └── plans/                 # Implementation plans
```

## Making Your First Contribution

### Development Methodology

This project uses strict reality-based incremental alignment:

1. **Read actual code first** (no assumptions)
2. **Work in ultra-small chunks** (1-2 files max)
3. **User approval checkpoints** (before and after execution)
4. **Track all work** in `docs/progress/audit-catalog.md`

**Primary Reference:** `docs/development-methodology.md`

### Test-Driven Development (TDD)

All code follows the Red → Green → Refactor cycle:

1. **Red:** Write failing tests first
2. **Green:** Implement minimum code to pass tests
3. **Refactor:** Improve code while keeping tests green
4. **Commit:** Use conventional commits with co-author attribution

**Quality Gates (all required):**
- All tests pass (`pytest` for backend, `npm run build` for frontend)
- Coverage >80% (`pytest --cov=engine`)
- No linting errors (`npm run lint`)
- Schema validation passes (`python -m engine.schema.generate --validate`)

### Commit Message Format

```
<type>(<scope>): <description>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Example:**
```
feat(extraction): add canonical dimension population

Implement lens-driven mapping rules for canonical_activities
extraction from raw observations.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Before Committing

Run this pre-commit checklist:

```bash
# 1. Schema validation
python -m engine.schema.generate --validate

# 2. Run tests
pytest                # Backend
cd web && npm run build  # Frontend

# 3. Check linting
cd web && npm run lint

# 4. Verify coverage
pytest --cov=engine  # Should be >80%

# 5. Update docs if architectural changes were made
```

## Common Tasks

### Adding a New Connector

1. Add to `engine/orchestration/registry.py` with `ConnectorSpec`
2. Add adapter mapping in `engine/orchestration/adapters.py`
3. Write tests in `tests/engine/orchestration/test_registry.py`
4. Follow TDD workflow

### Modifying the Data Schema

1. Edit `engine/config/schemas/<entity>.yaml`
2. Validate: `python -m engine.schema.generate --validate`
3. Regenerate: `python -m engine.schema.generate --all`
4. Update database: `cd web && npx prisma db push`
5. Write tests for schema changes

### Adding a New Lens (Future)

When lens system is complete:
1. Create `engine/lenses/<vertical_id>/lens.yaml` with full configuration
2. No code changes needed

Currently requires some extractor modifications until lens extraction bridge is built.

## Troubleshooting

### "Module not found" errors

**Backend:**
```bash
# Reinstall dependencies
python -m pip install -r engine/requirements.txt

# Verify PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # On Windows: set PYTHONPATH=%PYTHONPATH%;%cd%
```

**Frontend:**
```bash
cd web
rm -rf node_modules package-lock.json
npm install
```

### Database connection errors

1. Verify DATABASE_URL in `web/.env`
2. Check Supabase project is running
3. Regenerate Prisma client: `cd web && npx prisma generate`
4. Push schema: `cd web && npx prisma db push`

### Prisma schema out of sync

```bash
cd web
npx prisma generate
npx prisma db push
```

### Tests failing after schema changes

1. Regenerate schemas: `python -m engine.schema.generate --all`
2. Regenerate Prisma client: `cd web && npx prisma generate`
3. Clear pytest cache: `pytest --cache-clear`
4. Re-run tests: `pytest`

### API key errors

1. Verify `.env` file exists in project root
2. Check API keys are valid and not expired
3. Ensure no extra whitespace in `.env` file
4. Restart terminal/IDE to reload environment variables

### "CI=true npm test" hangs

Use the build command instead:
```bash
cd web
npm run build  # Non-interactive
```

For interactive testing (development):
```bash
cd web
npm test  # Runs in watch mode
```

## Learning Resources

### Documentation

- **`docs/target/system-vision.md`** - Immutable architectural invariants
- **`docs/target/architecture.md`** - Concrete pipeline and contracts
- **`docs/plans/`** - Phase-by-phase implementation strategies
- **`docs/development-methodology.md`** - Incremental alignment workflow
- **`CLAUDE.md`** - Development workflow and common gotchas

### Code Examples

- **Tests:** Browse `tests/engine/` for testing patterns
- **Extractors:** Check `engine/extraction/extractors/` for extraction patterns
- **Connectors:** See `engine/ingestion/connectors/` for connector implementations

### External Documentation

Use Context7 MCP tools for up-to-date library documentation:

1. Use `resolve-library-id` to find correct library ID
2. Use `query-docs` to get relevant documentation
3. Ensures current API patterns (Next.js, React, Prisma, Pydantic, etc.)

## Getting Help

### Before Asking

1. Check `CLAUDE.md` for common gotchas
2. Read relevant architectural docs (`docs/target/`)
3. Search existing tests for similar patterns
4. Verify environment setup is correct

### Architecture Questions

Read these in order:
1. `docs/target/system-vision.md` (immutable invariants)
2. `docs/target/architecture.md` (runtime specification)
3. `CLAUDE.md` (development workflow)

### Critical Operating Rules

When working on this codebase:

1. **Preserve Engine Purity:** Never add domain-specific terms to engine code
2. **Respect Extraction Contract:** Phase 1 = primitives only, Phase 2 = lens application
3. **Maintain Determinism:** Same inputs + lens → identical outputs
4. **Validate Against Reality:** Entity database is ultimate correctness signal
5. **Fail Fast:** Invalid contracts fail at bootstrap, no silent fallbacks
6. **No Vertical Exceptions:** Reference lens gets no special treatment

## Next Steps

1. **Run the test suite** to verify setup: `pytest`
2. **Start the dev server** to see the frontend: `cd web && npm run dev`
3. **Read architectural docs** to understand system design:
   - `docs/target/system-vision.md`
   - `docs/target/architecture.md`
4. **Review development methodology:** `docs/development-methodology.md`
5. **Make your first contribution** following TDD workflow

Welcome to the Universal Entity Extraction Engine. The architecture is designed for extensibility through configuration, not code changes. Focus on understanding the Engine vs Lens separation, and you'll be productive quickly.
