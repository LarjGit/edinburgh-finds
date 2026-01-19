# Edinburgh Finds

**A hyper-local discovery platform connecting enthusiasts with venues, coaches, and clubs for their hobbies.**

Edinburgh Finds combines AI-driven data extraction with a curated user experience to help people discover the best places to pursue their passions in Edinburgh.

---

## Quick Links

- **[Architecture Documentation](./ARCHITECTURE.md)** - System overview and technical architecture
- **[Conductor (Development Workflow)](./conductor/)** - Context-driven development process
- **[Extraction Engine Docs](./docs/extraction_engine_overview.md)** - Data extraction system documentation

---

## Project Overview

Edinburgh Finds is composed of three primary subsystems:

1. **Frontend (Web Application)**: Next.js-based user interface with SEO optimization
2. **Data Engine (Ingestion & Extraction)**: Python-based autonomous pipeline for data collection and processing
3. **Universal Entity Framework**: Flexible database schema supporting multiple verticals without migrations

**Key Features:**
- Multi-source data aggregation (Google Places, OpenStreetMap, Sport Scotland, Edinburgh Council)
- AI-powered extraction with field-level trust scoring
- Hybrid extraction (deterministic + LLM) for optimal quality and cost
- Automatic deduplication and merging across sources
- Programmatic SEO for thousands of hyper-specific landing pages

---

## Getting Started

### Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.11+ (for data engine)
- **Anthropic API Key** (for LLM extraction)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/edinburgh_finds.git
cd edinburgh_finds

# Install frontend dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Set up database
npx prisma generate
npx prisma migrate dev

# Set environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL="file:./prisma/dev.db"  # SQLite for development

# Anthropic API (required for LLM extraction)
ANTHROPIC_API_KEY="sk-ant-api03-..."

# Optional
LOG_LEVEL="INFO"
```

---

## Extraction Engine Quickstart

The extraction engine transforms raw API data into structured listings ready for display. Follow these steps to run your first extraction.

### Step 1: Ingest Raw Data

First, ingest raw data from a source (e.g., Google Places):

```bash
# Ingest Google Places data for Edinburgh padel venues
python -m engine.ingestion.run_google_places \
  --query="padel courts edinburgh" \
  --limit=10
```

**What this does:**
- Fetches data from Google Places API
- Saves raw JSON files to `data/raw_ingestion/google_places/`
- Creates `RawIngestion` records in database

**Verify ingestion:**
```bash
# Check ingested records
python -c "
from prisma import Prisma
import asyncio

async def check():
    db = Prisma()
    await db.connect()
    count = await db.rawingestion.count(where={'source': 'google_places'})
    print(f'Ingested {count} Google Places records')
    await db.disconnect()

asyncio.run(check())
"
```

### Step 2: Extract Structured Data

Run the extraction engine to transform raw data into structured listings:

```bash
# Extract all Google Places records
python -m engine.extraction.run --source=google_places

# Or extract a specific record for debugging
python -m engine.extraction.run --raw-id=<UUID> --verbose
```

**What this does:**
- Reads raw JSON from `RawIngestion` records
- Applies source-specific extractor (`GooglePlacesExtractor`)
- Validates and normalizes data (phone numbers, postcodes, coordinates)
- Creates `ExtractedListing` records
- Deduplicates and merges with existing listings
- Creates/updates `Listing` records

**Verify extraction:**
```bash
# View extraction results
python -m engine.extraction.health
```

### Step 3: View Extracted Listings

Query the database to see your extracted listings:

```bash
python -c "
from prisma import Prisma
import asyncio

async def view():
    db = Prisma()
    await db.connect()
    listings = await db.listing.find_many(take=5)
    for listing in listings:
        print(f'{listing.entity_name} - {listing.city}')
        print(f'  Source: {listing.source_info}')
        print(f'  Attributes: {listing.attributes}')
        print()
    await db.disconnect()

asyncio.run(view())
"
```

### Step 4: Run Full Extraction Pipeline

Process all unprocessed records from all sources:

```bash
# Run batch extraction
python -m engine.extraction.run_all

# View summary report and health metrics
python -m engine.extraction.health

# Check LLM costs
python -m engine.extraction.cost_report
```

### Common Extraction Workflows

**Test with dry-run (preview without saving):**
```bash
python -m engine.extraction.run --source=google_places --limit=5 --dry-run
```

**Retry failed extractions:**
```bash
python -m engine.extraction.cli --retry-failed
```

**Re-extract after fixing bugs:**
```bash
python -m engine.extraction.run --source=google_places --force-retry
```

**Extract specific source with limit (for testing):**
```bash
python -m engine.extraction.run --source=serper --limit=10
```

### Extraction Documentation

For comprehensive extraction engine documentation, see:

- **[Extraction Engine Overview](./docs/extraction_engine_overview.md)** - Architecture and design decisions
- **[CLI Reference](./docs/extraction_cli_reference.md)** - All commands with examples
- **[Adding a New Extractor](./docs/adding_new_extractor.md)** - Step-by-step guide for new sources
- **[Troubleshooting Guide](./docs/troubleshooting_extraction.md)** - Common errors and solutions
- **[Configuring Trust Levels](./docs/configuring_trust_levels.md)** - Field-level trust configuration
- **[Managing Categories](./docs/managing_categories.md)** - Canonical taxonomy management
- **[Tuning LLM Prompts](./docs/tuning_llm_prompts.md)** - Optimizing LLM extraction quality

---

## Frontend Development

### Running the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

### Building for Production

```bash
npm run build
npm run start
```

---

## Data Sources

The platform aggregates data from multiple authoritative sources:

| Source | Type | Trust Level | Cost | Use Case |
|--------|------|-------------|------|----------|
| **Google Places** | Commercial API | 70 | Paid | Venues, reviews, hours, photos |
| **Sport Scotland** | Government | 90 | Free | Sports facilities, official data |
| **Edinburgh Council** | Government | 85 | Free | Council-owned facilities |
| **Serper** | Search | 50 | Paid | Discovery, unstructured data |
| **OpenStreetMap** | Crowdsourced | 40 | Free | Coordinates, tags, community data |
| **OpenChargeMap** | Crowdsourced | 40 | Free | EV charging stations |

**Trust Levels** determine which source wins when data conflicts. See [Configuring Trust Levels](./docs/configuring_trust_levels.md) for details.

---

## Testing

### Frontend Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch
```

### Extraction Engine Tests

```bash
# Run all extraction tests
pytest engine/extraction/tests -v

# Run specific extractor tests
pytest engine/extraction/tests/test_google_places_extractor.py -v

# Run with coverage report
pytest engine/extraction/tests --cov=engine.extraction --cov-report=html
```

### Architectural Validation (Enforced in CI)

The project enforces strict architectural contracts through automated validation:

**Engine Purity:**
- Engine code remains 100% vertical-agnostic
- No lens imports (LensContract boundary enforced)
- No value-based branching on dimension values
- Validated via: `bash scripts/check_engine_purity.sh`

**Lens Contract Validation:**
- All facets use valid dimension sources (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
- All value.facet references exist in facets section
- All mapping_rules.canonical references exist in values section
- No duplicate value keys
- Validated via: `pytest tests/lenses/test_validator.py -v`

**Module Composition:**
- Modules are properly namespaced in JSONB (no flattened structure)
- Duplicate module keys rejected at YAML load time
- Duplicate field names across different modules allowed (namespacing provides safety)
- Validated via: `pytest tests/modules/test_composition.py -v`

**Deduplication:**
- Deterministic deduplication preserves insertion order
- Validated via: `pytest tests/lenses/test_lens_processing.py::TestDedupePreserveOrder -v`

**Prisma Array Filters:**
- Array operations (has, hasSome, hasEvery) work correctly with Postgres text[] arrays
- GIN indexes used for efficient querying
- Validated via: `pytest tests/query/test_prisma_array_filters.py -v` (requires PostgreSQL)

All validation checks run automatically in CI/CD. PRs must pass all checks before merge.

---

## Project Structure

```
edinburgh_finds/
├── app/                          # Next.js frontend (App Router)
│   ├── (routes)/                 # Route groups
│   ├── components/               # React components
│   └── lib/                      # Frontend utilities
├── conductor/                    # Conductor development workflow
│   ├── product.md                # Product vision and goals
│   ├── tech-stack.md             # Technology choices
│   ├── workflow.md               # Development methodology
│   └── tracks/                   # Implementation tracks
├── docs/                         # Documentation
│   ├── extraction_engine_overview.md
│   ├── extraction_cli_reference.md
│   ├── adding_new_extractor.md
│   └── ...
├── engine/                       # Python data engine
│   ├── ingestion/                # Data ingestion (Stage 1)
│   │   ├── connectors/           # Source-specific connectors
│   │   └── run_*.py              # Ingestion CLIs
│   ├── extraction/               # Data extraction (Stage 2)
│   │   ├── extractors/           # Source-specific extractors
│   │   ├── prompts/              # LLM prompt templates
│   │   ├── utils/                # Special field processors
│   │   ├── run.py                # Extraction CLI
│   │   ├── run_all.py            # Batch extraction CLI
│   │   ├── health.py             # Health dashboard
│   │   └── cost_report.py        # LLM cost tracking
│   ├── config/                   # Configuration files
│   │   ├── extraction.yaml       # Trust levels, LLM settings
│   │   ├── canonical_categories.yaml  # Category taxonomy
│   │   └── sources.yaml          # Ingestion source configs
│   └── schema/                   # Database schema (Prisma)
├── prisma/                       # Prisma ORM
│   ├── schema.prisma             # Database schema
│   └── migrations/               # Database migrations
├── ARCHITECTURE.md               # System architecture documentation
├── CLAUDE.md                     # Project instructions for Claude Code
└── README.md                     # This file
```

---

## Schema Management

### YAML-Based Single Source of Truth

This project uses **YAML schemas** as the single source of truth for all database and extraction schemas. Schema files are located in `engine/config/schemas/`:

```
engine/config/schemas/
├── listing.yaml      # Base entity schema (27 fields)
├── venue.yaml        # Venue-specific fields (85 fields)
└── winery.yaml       # Example: Winery vertical (12 specific fields)
```

### Generating Schemas

All Python FieldSpecs, Prisma schemas, and TypeScript interfaces are auto-generated from YAML:

```bash
# Generate all Python schemas from YAML
python -m engine.schema.generate

# Generate Python and TypeScript schemas
python -m engine.schema.generate --typescript

# Generate TypeScript with Zod validation schemas
python -m engine.schema.generate --typescript --zod

# Generate specific schema
python -m engine.schema.generate --schema=listing

# Validate schemas are in sync (exits 1 if drift detected)
python -m engine.schema.generate --validate

# Preview changes without writing files
python -m engine.schema.generate --dry-run
```

**IMPORTANT**: Never manually edit generated files:
- `engine/schema/listing.py` - Generated from `listing.yaml`
- `engine/schema/venue.py` - Generated from `venue.yaml`
- `prisma/schema.prisma` - Generated from YAML schemas
- `web/types/*.ts` - Generated TypeScript interfaces (when using --typescript)

All generated files include a "GENERATED FILE - DO NOT EDIT" warning.

### Adding a New Field to an Entity

1. Edit the YAML schema (e.g., `engine/config/schemas/venue.yaml`)
2. Add your field with metadata:
   ```yaml
   - name: parking_available
     type: boolean
     nullable: true
     required: false
     description: "Whether the venue has parking facilities"
     search_keywords:
       - parking
       - car park
       - vehicle access
   ```
3. Regenerate schemas:
   ```bash
   python -m engine.schema.generate
   ```
4. Run tests to verify:
   ```bash
   pytest engine/tests/test_schema_sync.py -v
   ```
5. Commit both YAML and generated files

### Adding a New Entity Type

To add a new vertical (e.g., Restaurant, Winery, Gym):

1. Create new YAML schema file: `engine/config/schemas/restaurant.yaml`
2. Define entity with inheritance:
   ```yaml
   schema:
     name: Restaurant
     extends: listing
     description: "Restaurant-specific fields"

   fields:
     - name: cuisine_types
       type: list[string]
       description: "Types of cuisine served"
     - name: michelin_stars
       type: integer
       nullable: true
       description: "Number of Michelin stars (if applicable)"
   ```
3. Generate schemas:
   ```bash
   python -m engine.schema.generate
   ```
4. Update extraction engine to use new entity type
5. Add Prisma migrations if needed

See **[Adding a New Entity Type Guide](./docs/adding_entity_type.md)** for detailed walkthrough.

### Schema Documentation

For comprehensive schema management documentation:

- **[Schema Management Guide](./docs/schema_management.md)** - YAML format reference, field types, attributes
- **[Adding a New Entity Type](./docs/adding_entity_type.md)** - Step-by-step tutorial with winery example
- **[ARCHITECTURE.md - Section 2.4](./ARCHITECTURE.md)** - Schema generation architecture

### Pre-commit Hook (Recommended)

Add a pre-commit hook to prevent schema drift:

```bash
# .git/hooks/pre-commit
#!/bin/bash
python -m engine.schema.generate --validate --no-color
if [ $? -ne 0 ]; then
  echo "Error: Generated schemas are out of sync with YAML"
  echo "Run: python -m engine.schema.generate"
  exit 1
fi
```

---

## Deployment

### Frontend (Vercel)

The frontend is deployed to Vercel with automatic deployments from `main` branch.

```bash
# Deploy to production
vercel --prod
```

### Data Engine (Scheduled Jobs)

The data engine runs as scheduled jobs (cron) on a dedicated server or container:

```bash
# Example cron job (daily at 2 AM)
0 2 * * * cd /path/to/edinburgh_finds && python -m engine.extraction.run_all
```

### Database (Production)

Production uses **Supabase (PostgreSQL)** instead of SQLite.

Update `DATABASE_URL` in production:
```bash
DATABASE_URL="postgresql://user:pass@db.supabase.co:5432/edinburgh_finds"
```

---

## Contributing

### Development Workflow (Conductor)

This project uses **Conductor** for context-driven development. Before implementing features:

1. **Set up Conductor**: `Read conductor/README.md`
2. **Create a track**: Define spec and plan before coding
3. **Follow TDD**: Write tests first, implement to pass, refactor
4. **Commit with plan updates**: Track progress in plan.md

See [Conductor Documentation](./conductor/) for details.

### Adding a New Data Source

To add a new ingestion source and extractor:

1. **Read**: [Adding a New Extractor Guide](./docs/adding_new_extractor.md)
2. **Create connector**: `engine/ingestion/connectors/<source>_connector.py`
3. **Create extractor**: `engine/extraction/extractors/<source>_extractor.py`
4. **Configure trust level**: Edit `engine/config/extraction.yaml`
5. **Write tests**: `engine/extraction/tests/test_<source>_extractor.py`
6. **Test**: `pytest engine/extraction/tests/test_<source>_extractor.py -v`

---

## Troubleshooting

### Common Issues

**Database connection failed:**
```bash
# Verify DATABASE_URL is set
echo $DATABASE_URL

# Regenerate Prisma client
npx prisma generate
```

**Extraction failing with LLM errors:**
```bash
# Verify Anthropic API key
echo $ANTHROPIC_API_KEY

# Check LLM cost and usage
python -m engine.extraction.cost_report
```

**High null rates in extracted data:**
```bash
# Check health dashboard for field quality
python -m engine.extraction.health

# Review source-specific data quality in raw files
ls -la data/raw_ingestion/<source>/
```

For comprehensive troubleshooting, see [Troubleshooting Guide](./docs/troubleshooting_extraction.md).

---

## License

This project is proprietary. All rights reserved.

---

## Contact

For questions or issues, please create an issue on GitHub or contact the development team.

---

**Built with:**
- Next.js 15
- Python 3.11
- Prisma ORM
- Claude AI (Anthropic)
- Vercel
- Supabase
