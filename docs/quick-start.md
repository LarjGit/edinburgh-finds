# Quick Start Guide

Welcome to Edinburgh Finds! This guide will get you up and running with the system in minutes.

## Overview

Edinburgh Finds is a universal data ingestion and entity extraction platform that discovers, processes, and presents information about places, people, organisations, and events. The system uses AI-powered extraction to transform raw data from multiple sources into structured, searchable entities.

## Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL database
- Anthropic API key (for AI extraction)
- Optional: Google Places API key, Serper API key

## Quick Setup

### 1. Clone and Install

```bash
git clone <repository-url>
cd edinburgh_finds

# Install Python dependencies
pip install -r engine/requirements.txt

# Install web dependencies
cd web
npm install
cd ..
```

### 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
ANTHROPIC_API_KEY=sk-ant-api03-your_key_here
DATABASE_URL="postgresql://postgres:password@localhost:5432/edinburgh_finds?schema=public"
GOOGLE_PLACES_API_KEY=your-google-places-api-key  # Optional
SERPER_API_KEY=your-serper-api-key  # Optional
```

### 3. Database Setup

Create database and generate Prisma clients:

```bash
# Create PostgreSQL database
createdb edinburgh_finds

# Generate Prisma client for Python engine
prisma generate --schema engine/schema.prisma

# Generate Prisma client for web
cd web
npx prisma generate
cd ..

# Apply database schema
npx prisma db push --schema web/prisma/schema.prisma
```

### 4. Verify Installation

Run the verification script:

```bash
python verify_phase1.py
```

## Your First Data Pipeline

### 1. Set Up Lens

Configure the default lens for domain knowledge:

```bash
# Set lens environment variable
export LENS_ID=edinburgh_finds

# On Windows:
set LENS_ID=edinburgh_finds
```

### 2. Ingest Sample Data

Start with a simple data source:

```bash
# Ingest from Serper (requires API key)
python -m engine.ingestion.cli serper "padel courts Edinburgh"

# Or use OpenStreetMap (no API key required)
python -m engine.ingestion.cli openstreetmap "amenity=restaurant"

# Check ingestion status
python -m engine.ingestion.cli status
```

### 3. Run Orchestrated Processing

Process data using the lens-aware orchestration system:

```bash
# Run orchestrated ingestion and extraction (dry-run)
python -m engine.orchestration.cli run "padel courts Edinburgh"

# With database persistence
python -m engine.orchestration.cli run "tennis clubs Edinburgh" --persist
```

### 4. View Results

Check your extracted entities:

```bash
# Inspect database contents
python engine/inspect_db.py

# Verify extraction results
python verify_phase1.py
```

### 5. Launch Web Interface

Start the web application:

```bash
cd web
npm run dev
```

Visit `http://localhost:3000` to browse your extracted entities.

## Key Concepts

### Data Flow

1. **Ingestion**: Raw data from external APIs → `RawIngestion` table
2. **Orchestration**: Lens-aware processing with connector selection
3. **Extraction**: Raw data → structured entities via AI → `ExtractedEntity` table
4. **Presentation**: Entities displayed via web interface with faceted search

### Entity Types

The system recognises five universal entity classes:

- **place**: Venues, locations, facilities
- **person**: Individuals, coaches, staff
- **organization**: Companies, clubs, institutions
- **event**: Activities, classes, competitions
- **thing**: Products, equipment, resources

### Lenses

Lenses provide vertical-specific knowledge for different domains:

- Define facets (searchable dimensions like "activity", "place_type")
- Map raw data to canonical values ("padel", "sports_facility")
- Configure connector selection and module triggers
- Located in `engine/lenses/<lens_id>/lens.yaml`

## Common Tasks

### Add a New Data Source

1. Create connector in `engine/ingestion/connectors/`
2. Implement `BaseConnector` interface
3. Add to connector registry in `engine/ingestion/cli.py`
4. Test with: `python -m engine.ingestion.cli your_source "query"`

### Configure Extraction

1. Edit extraction settings in `engine/config/extraction.yaml`
2. Modify LLM model, trust levels, and processing rules
3. Test with orchestration: `python -m engine.orchestration.cli run "test query"`

### Customise Lens Configuration

1. Edit `engine/lenses/edinburgh_finds/lens.yaml`
2. Add new canonical values, mapping rules, or module triggers
3. Test with: `python -m engine.orchestration.cli run --lens edinburgh_finds "query"`

### Monitor System Health

```bash
# Check ingestion status
python -m engine.ingestion.cli status

# Run live system test
python scripts/test_orchestration_live.py

# Retry failed extractions
python -m engine.extraction.cli --retry-failed
```

## Development Workflow

### 1. Make Changes

Edit code in your preferred IDE. The system uses:

- **Backend**: Python with Prisma ORM
- **Frontend**: Next.js with TypeScript
- **Database**: PostgreSQL
- **AI**: Anthropic Claude for extraction

### 2. Test Changes

```bash
# Run specific tests
pytest tests/engine/extraction/

# Run all tests
pytest

# Live orchestration test
python scripts/test_orchestration_live.py --verbose
```

### 3. Validate System

```bash
# Validate documentation
python scripts/validate_docs.py

# Check database state
python engine/inspect_db.py
```

## Troubleshooting

### Common Issues

**"No module named 'prisma'"**
```bash
pip install -r engine/requirements.txt
prisma generate --schema engine/schema.prisma
```

**"Database connection failed"**
- Check `DATABASE_URL` in `.env` points to PostgreSQL
- Ensure PostgreSQL is running: `pg_ctl status`
- Create database: `createdb edinburgh_finds`
- Apply schema: `npx prisma db push --schema web/prisma/schema.prisma`

**"Anthropic API error"**
- Verify `ANTHROPIC_API_KEY` in `.env`
- Check API quota and billing at console.anthropic.com

**"No lens specified"**
- Set `LENS_ID=edinburgh_finds` in environment
- Or use `--lens edinburgh_finds` flag
- For testing: use `--allow-default-lens` flag

**"No entities extracted"**
- Check raw data exists: `python -m engine.ingestion.cli status`
- Verify lens configuration: `engine/lenses/edinburgh_finds/lens.yaml`
- Try with `--persist` flag to save results

### Getting Help

1. Check the logs in orchestration output
2. Review ingestion status: `python -m engine.ingestion.cli status`
3. Inspect database state: `python engine/inspect_db.py`
4. Run with verbose logging: `--verbose` flag

## Next Steps

Once you have the system running:

1. **Explore the Architecture**: Read `docs/target-architecture.md`
2. **Add Your Data Sources**: Follow connector development patterns
3. **Customise Lens Configuration**: Modify `engine/lenses/edinburgh_finds/lens.yaml`
4. **Create Domain Modules**: Add field extraction rules
5. **Deploy to Production**: Set up PostgreSQL hosting and environment

## Configuration Files

Key configuration locations:

- `.env` - Environment variables and API keys
- `engine/config/extraction.yaml` - Extraction settings (LLM model, trust levels)
- `engine/lenses/edinburgh_finds/lens.yaml` - Default lens configuration
- `web/package.json` - Frontend dependencies and scripts

## CLI Commands

The system exposes several CLI interfaces:

- `python -m engine.ingestion.cli` - Data ingestion commands
- `python -m engine.extraction.cli` - Extraction maintenance (retry failed)
- `python -m engine.orchestration.cli` - Lens-aware orchestrated processing
- `python -m engine.schema.generate` - Schema generation tools

For programmatic access, import modules directly or use the Prisma client for database operations.

---

**Need more help?** Check the detailed documentation in `docs/` or examine the test files in `tests/` for usage examples.
