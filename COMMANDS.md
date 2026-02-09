# Commands Reference

Quick reference for all development commands in the Edinburgh Finds project.

---

## Setup Commands

### Frontend (Next.js)
```bash
cd web && npm install
```

### Backend (Python Engine)
```bash
python -m pip install -r engine/requirements.txt
```

---

## Daily Development Commands

### Frontend
```bash
cd web
npm run dev          # Start Next.js dev server (http://localhost:3000)
npm run build        # Production build
npm run lint         # ESLint
```

### Backend (Engine)
```bash
pytest                        # Run all tests
pytest -m "not slow"          # Run fast tests only (excludes @pytest.mark.slow)
pytest --cov=engine --cov-report=html  # Generate coverage report (target: >80%)
pytest engine/orchestration/  # Run specific module tests
```

---

## Schema Management (CRITICAL)

YAML schemas are the single source of truth. Location: `engine/config/schemas/*.yaml`

### Validate schemas before committing
```bash
python -m engine.schema.generate --validate
```

### Regenerate all derived schemas
```bash
python -m engine.schema.generate --all
```

This regenerates:
- Python FieldSpecs → `engine/schema/<entity>.py`
- Prisma schemas → `web/prisma/schema.prisma` and `engine/prisma/schema.prisma`
- TypeScript interfaces → `web/lib/types/generated/<entity>.ts`

### When you modify a YAML schema:
1. Edit `engine/config/schemas/<entity>.yaml`
2. Run: `python -m engine.schema.generate --all`
3. Generated files are marked "DO NOT EDIT" - never modify them directly

---

## Data Pipeline Commands

### Ingestion (fetch raw data)
```bash
python -m engine.ingestion.cli run --query "padel courts Edinburgh"
```

### Extraction (structured data from raw)
```bash
python -m engine.extraction.cli single <raw_ingestion_id>
python -m engine.extraction.cli source serper --limit 10
```

### Orchestration (intelligent multi-source query)
```bash
python -m engine.orchestration.cli run "padel clubs in Edinburgh"
```

---

## Environment Setup

### Required Environment Variables

**Engine (.env or environment):**
```bash
ANTHROPIC_API_KEY=<your_key>      # For LLM extraction
SERPER_API_KEY=<your_key>         # For Serper connector
GOOGLE_PLACES_API_KEY=<your_key>  # For Google Places connector
```

**Web (web/.env):**
```bash
DATABASE_URL=<supabase_postgres_url>
```

### Database Setup
```bash
cd web
npx prisma generate      # Generate Prisma client from schema
npx prisma db push       # Sync schema to Supabase (dev)
npx prisma migrate dev   # Create migration (production)
```

---

## Before Committing Checklist

1. **Schema validation:** `python -m engine.schema.generate --validate`
2. **Run tests:** `pytest` (backend), `cd web && npm run build` (frontend)
3. **Check linting:** `cd web && npm run lint`
4. **Verify coverage:** `pytest --cov=engine` (should be >80%)
5. **Update docs:** If implementation affects architecture or plans, update relevant documentation

---

## Testing Commands

### Unit Tests
```bash
pytest                                    # Run all tests
pytest -m "not slow"                      # Fast tests only
pytest engine/orchestration/              # Specific module
```

### Coverage
```bash
pytest --cov=engine --cov-report=html     # Generate HTML coverage report
# Target: >80% coverage for all modules
```

### Frontend Tests
```bash
cd web
CI=true npm test  # Non-interactive mode (prevents watch mode)
```

---

## Commit Message Format

```
<type>(<scope>): <description>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
