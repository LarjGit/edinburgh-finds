# Onboarding Guide

**Generated:** 2026-02-06
**Status:** Auto-generated documentation

---

## Prerequisites

Before starting, ensure you have the following installed:

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.12+ | Backend engine |
| **Node.js** | 20+ | Next.js frontend |
| **npm** | 10+ | Package management |
| **Git** | Latest | Version control |
| **PostgreSQL** | 15+ (or Supabase) | Database |

Optional but recommended:
- **Prisma Studio** — Visual database browser (`npx prisma studio`)
- **VS Code** — Recommended editor with Python and TypeScript extensions

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/LarjGit/edinburgh_finds.git
cd edinburgh_finds
```

### 2. Set Up the Python Engine

```bash
# Install Python dependencies
python -m pip install -r engine/requirements.txt

# Install test dependencies
pip install pytest pytest-cov pytest-asyncio
```

### 3. Set Up the Next.js Frontend

```bash
cd web
npm install
cd ..
```

### 4. Configure Environment Variables

#### Engine Environment

Create a `.env` file in the project root (or set environment variables):

```bash
# Required for LLM extraction
ANTHROPIC_API_KEY=sk-ant-...

# Required for Serper connector
SERPER_API_KEY=your_serper_key

# Required for Google Places connector
GOOGLE_PLACES_API_KEY=AIza...

# Database URL (Supabase PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/database
```

#### Connector Configuration

```bash
# Copy the sources config template
cp engine/config/sources.yaml.example engine/config/sources.yaml

# Edit with your API keys
# (sources.yaml is gitignored — never commit API keys)
```

#### Frontend Environment

Create `web/.env`:

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
```

### 5. Set Up the Database

```bash
cd web

# Generate Prisma client from schema
npx prisma generate

# Sync schema to your database (development)
npx prisma db push

# Or create a migration (production)
npx prisma migrate dev
```

### 6. Verify Setup

```bash
# Run backend tests (should all pass)
pytest -m "not slow"

# Verify schema
python -m engine.schema.generate --validate

# Build frontend (verifies TypeScript compilation)
cd web && npm run build
```

---

## Running the Application

### Start the Frontend

```bash
cd web
npm run dev
# Open http://localhost:3000
```

### Run the Data Pipeline

```bash
# Full orchestration pipeline (fetch + extract + merge + persist)
python -m engine.orchestration.cli run --lens edinburgh_finds "padel courts Edinburgh"

# Ingestion only (just fetch raw data)
python -m engine.ingestion.cli run --query "padel courts Edinburgh"

# Extraction only (process existing raw data)
python -m engine.extraction.cli source serper --limit 10
```

### Browse the Database

```bash
cd web
npx prisma studio
# Opens database GUI at http://localhost:5555
```

---

## Running Tests

### Backend (Python)

```bash
# All tests
pytest

# Fast tests only (excludes @pytest.mark.slow)
pytest -m "not slow"

# Specific module
pytest tests/engine/extraction/ -v

# With coverage
pytest --cov=engine --cov-report=html

# Specific test categories
pytest tests/engine/test_purity.py -v          # Engine purity
pytest tests/lenses/test_validator.py -v        # Lens validation
pytest tests/engine/orchestration/ -v           # Orchestration
```

### Frontend (TypeScript)

```bash
cd web
npm run build    # Type checking + build
npm run lint     # ESLint
```

---

## Project Structure Overview

```
edinburgh_finds/
├── engine/                    # Python ETL pipeline (data ingestion & extraction)
│   ├── config/                # Configuration files and schemas
│   ├── ingestion/             # 6 data source connectors
│   ├── extraction/            # Hybrid extraction (deterministic + LLM)
│   ├── orchestration/         # Pipeline coordination and entity finalization
│   ├── lenses/                # Lens system (vertical-specific YAML configs)
│   ├── schema/                # Schema generation (YAML -> Python/Prisma/TS)
│   └── data/raw/              # Stored raw ingestion data
├── web/                       # Next.js 16 (React 19) frontend
│   ├── app/                   # Next.js App Router pages
│   ├── lib/                   # Shared utilities and query builders
│   └── prisma/                # Prisma schema and migrations
├── tests/                     # Test suite
│   ├── engine/                # Engine tests (extraction, orchestration, lenses)
│   ├── lenses/                # Lens validation tests
│   ├── modules/               # Module composition tests
│   └── query/                 # Prisma query tests
├── docs/                      # Documentation
│   ├── system-vision.md       # Immutable architectural constitution
│   ├── architecture.md        # Runtime implementation specification
│   ├── development-methodology.md # Development workflow
│   └── progress/              # Audit catalog and progress tracking
├── .github/                   # CI/CD configuration
│   ├── workflows/tests.yml    # GitHub Actions test workflow
│   └── pull_request_template.md
└── scripts/                   # Utility scripts
    └── check_engine_purity.sh # Engine purity CI check
```

---

## Key Concepts to Understand

Before working on the codebase, read these in order:

1. **[`docs/system-vision.md`](../system-vision.md)** — The 10 immutable invariants that govern all decisions
2. **[`docs/architecture.md`](../architecture.md)** — The 11-stage pipeline and boundary contracts
3. **[`docs/development-methodology.md`](../development-methodology.md)** — The micro-iteration development workflow
4. **[ARCHITECTURE.md](ARCHITECTURE.md)** — This generated overview

**The single most important concept:** The Engine knows nothing about domains. All domain knowledge lives in Lens YAML configs.

---

## Common Issues

### "Cannot find module '@prisma/client'"
```bash
cd web && npx prisma generate
```

### "Database does not exist" or connection errors
Verify `DATABASE_URL` in `web/.env` points to a running PostgreSQL instance.

### "ANTHROPIC_API_KEY not set"
Set the environment variable before running LLM extraction:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Tests fail with "No module named 'engine'"
Run tests from the project root:
```bash
cd edinburgh_finds  # project root
pytest tests/engine/ -v
```

### Schema validation fails
After modifying YAML schemas, regenerate:
```bash
python -m engine.schema.generate --all
```

---

## Related Documentation

- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Backend:** [BACKEND.md](BACKEND.md)
- **Frontend:** [FRONTEND.md](FRONTEND.md)
- **Configuration:** [CONFIGURATION.md](CONFIGURATION.md)
- **Development Guide:** [DEVELOPMENT.md](DEVELOPMENT.md)
