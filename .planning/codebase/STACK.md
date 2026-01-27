# Technology Stack

**Analysis Date:** 2026-01-27

## Languages

**Primary:**
- TypeScript 5.x - Frontend (Next.js App Router, React components)
- Python 3.x - Backend (ETL pipeline, data extraction, orchestration)

**Secondary:**
- JavaScript (configuration files, build scripts)
- YAML (schema definitions, configuration)

## Runtime

**Environment:**
- Node.js - Frontend (Next.js 16.1.1)
- Python 3.x - Backend engine

**Package Manager:**
- npm (Frontend) - `web/package.json`
- pip (Backend) - `engine/requirements.txt`
- Lockfiles: `web/package-lock.json` present

## Frameworks

**Core:**
- Next.js 16.1.1 - Full-stack React framework with App Router
- React 19.2.3 - UI component library
- Tailwind CSS 4.x - Utility-first CSS styling
- shadcn/ui - Component library built on Tailwind

**Backend:**
- Pydantic - Schema validation and data modeling
- Instructor - Structured LLM output extraction wrapper
- Prisma (Python Client) - ORM for database access

**Testing:**
- pytest - Python testing framework (backend)
- (Frontend testing framework not detected in package.json)

**Build/Dev:**
- TypeScript 5.x - Language and type checking
- ESLint 9.x - Linting (Next.js config)
- Tailwind CSS (via @tailwindcss/postcss v4) - CSS compilation
- Prisma CLI - Database schema management

## Key Dependencies

**Critical:**
- @prisma/client 7.3.0 - Database ORM (JavaScript)
- prisma 7.3.0 - Database schema and migrations
- anthropic - Anthropic Claude API for LLM extraction
- instructor - Wraps anthropic client for structured output
- pydantic - Schema validation (Python)
- aiohttp - Async HTTP client for API connectors
- fuzzywuzzy - Fuzzy string matching for deduplication

**Frontend UI:**
- lucide-react 0.562.0 - Icon library
- class-variance-authority 0.7.1 - Component variant utility
- clsx 2.1.1 - Class name concatenation
- tailwind-merge 3.4.0 - Tailwind class conflict resolution

**Infrastructure:**
- python-dotenv - Environment variable loading
- pyyaml - YAML parsing for schemas and configs
- phonenumbers - Phone number validation and formatting
- python-Levenshtein - String similarity algorithms
- tqdm - Progress bar utility

## Configuration

**Environment:**
- Environment variables in root `.env` and `web/.env`
- Critical vars: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `GOOGLE_PLACES_API_KEY`, `SERPER_API_KEY`
- Example config: `.env.example` in project root

**Build:**
- `web/tsconfig.json` - TypeScript compiler configuration
- `web/eslint.config.mjs` - ESLint configuration (Next.js rules)
- `web/next.config.ts` - Next.js configuration (minimal)
- `web/components.json` - shadcn/ui configuration
  - Schema: New York style
  - Base color: Neutral
  - Icon library: Lucide
  - Path aliases: `@/components`, `@/lib`, `@/ui`, etc.

**Frontend:**
- Tailwind CSS PostCSS v4 for styling
- CSS modules via `app/globals.css`

## Platform Requirements

**Development:**
- Node.js (for Next.js frontend)
- Python 3.x (for backend engine)
- PostgreSQL (via Supabase connection)
- Anthropic API key (for LLM extraction)

**Production:**
- Deployment target: Supabase PostgreSQL (cloud)
- Frontend: Next.js server (can deploy to Vercel, self-hosted)
- Backend: Python environment (separate ETL runner or serverless function)
- API keys required: Anthropic, Google Places, Serper, Sport Scotland (free), Edinburgh Council (free), OpenChargeMap (free)

## Database

**Provider:**
- PostgreSQL via Supabase (AWS eu-west-1)
- Connection via Prisma ORM

**Schema:**
- Auto-generated from YAML schemas in `engine/config/schemas/`
- Schema files: `web/prisma/schema.prisma` (JavaScript) and `engine/prisma/schema.prisma` (Python)
- Generated using: `python -m engine.schema.generate --all`

**Key Tables:**
- `Entity` - Unified entity record (place, person, organization, event, thing)
- `EntityRelationship` - Relationships between entities
- `RawIngestion` - Raw data from connectors
- `ExtractedEntity` - Structured extraction results
- `FailedExtraction` - Failed extraction tracking
- `OrchestrationRun` - Query execution tracking
- `LensEntity` - Lens membership (vertical-specific interpretation)
- `MergeConflict` - Field-level merge conflict tracking

---

*Stack analysis: 2026-01-27*
