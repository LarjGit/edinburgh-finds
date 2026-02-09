# Edinburgh Finds

An intelligent data ingestion and extraction system for discovering and cataloguing local venues, services, and points of interest in Edinburgh. The system uses AI-powered extraction with configurable lenses to transform raw data from multiple sources into structured, searchable entities.

## Architecture Overview

Edinburgh Finds follows a three-stage pipeline:

1. **Ingestion**: Fetch raw data from multiple sources (Google Places, OpenStreetMap, Serper, etc.)
2. **Extraction**: Use AI (Anthropic Claude) to extract structured entities from raw data
3. **Orchestration**: Intelligent coordination of ingestion and extraction with deduplication

The system uses **lenses** - YAML configuration files that define domain-specific extraction rules, entity schemas, and confidence thresholds.

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+ (for web interface)
- PostgreSQL database
- API keys for data sources

### Installation

1. **Clone and setup Python environment**:
```bash
git clone <repository-url>
cd edinburgh-finds
cd engine
pip install -r requirements.txt
```

2. **Setup database**:
```bash
# Configure your PostgreSQL connection
cp .env.example .env
# Edit .env with your DATABASE_URL and API keys

# Run Prisma migrations
npx prisma migrate dev
```

3. **Setup web interface** (optional):
```bash
cd web
npm install
npm run dev
```

### Basic Usage

**Run intelligent orchestration** (recommended):
```bash
# Set your lens
export LENS_ID=edinburgh_finds

# Run orchestrated ingestion with extraction
python -m engine.orchestration.cli run "tennis courts Edinburgh" --persist
```

**Run individual connectors**:
```bash
# Fetch from Google Places
python -m engine.ingestion.cli google_places "padel courts edinburgh"

# Fetch from OpenStreetMap
python -m engine.ingestion.cli openstreetmap "tennis"

# Check ingestion status
python -m engine.ingestion.cli status
```

**Extraction maintenance**:
```bash
# Retry failed extractions
python -m engine.extraction.cli --retry-failed
```

## Key Concepts

### Lenses

Lenses are YAML configuration files that define how to extract structured data from raw sources. They specify:

- **Query vocabulary**: Keywords for activity types, locations, and facilities
- **Connector rules**: Which data sources to prioritise for different queries
- **Facets**: How to categorise and display extracted entities
- **Mapping rules**: Transform raw data into canonical values
- **Domain modules**: Specialised extraction logic with field-specific rules

Example from `engine/lenses/edinburgh_finds/lens.yaml`:

```yaml
# Schema version (required)
schema: lens/v1

# Query vocabulary for orchestration
vocabulary:
  activity_keywords:
    - padel
    - tennis
    - squash
    - badminton
  location_indicators:
    - edinburgh
    - leith
    - portobello

# Connector selection rules
connector_rules:
  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [padel, tennis, squash, sports, facilities]

# Facets define how dimensions are displayed
facets:
  activity:
    dimension_source: canonical_activities
    ui_label: "Activities"
    display_mode: tags
    show_in_filters: true

# Canonical values registry
values:
  - key: padel
    facet: activity
    display_name: "Padel"
    description: "Racquet sport combining elements of tennis and squash"
    search_keywords: ["padel", "racket sport"]

# Mapping rules (raw data → canonical values)
mapping_rules:
  - id: map_padel_from_name
    pattern: "(?i)padel"
    canonical: "padel"
    confidence: 0.95

# Domain modules with field extraction rules
modules:
  sports_facility:
    field_rules:
      - rule_id: extract_padel_court_count
        target_path: padel_courts.total
        extractor: regex_capture
        pattern: "(?i)(\\d+)\\s+(?:fully\\s+)?(?:covered(?:,\\s*|\\s+and\\s+)?)?(?:heated\\s+)?courts?"
        confidence: 0.85
```

### Data Sources

The system supports multiple connectors:

- **google_places**: Google Places API for venue data
- **openstreetmap**: OpenStreetMap Overpass API for geographic data
- **serper**: Web search results via Serper API
- **open_charge_map**: Electric vehicle charging points
- **sport_scotland**: Scottish sports facility database
- **edinburgh_council**: Edinburgh Council facility data

### Orchestration Modes

- **discover_many**: Find multiple entities matching a query (default)
- **resolve_one**: Focus on resolving a specific entity with high confidence

## CLI Reference

### Orchestration CLI

The main interface for intelligent ingestion:

```bash
# Basic usage
python -m engine.orchestration.cli run "query string"

# With options
python -m engine.orchestration.cli run "tennis courts" \
  --mode discover_many \
  --persist \
  --lens edinburgh_finds
```

**Options**:
- `--mode`: `discover_many` or `resolve_one`
- `--persist`: Save extracted entities to database
- `--lens`: Override lens ID
- `--allow-default-lens`: Allow fallback to default lens (dev/test)

### Ingestion CLI

For running individual data source connectors:

```bash
# Run specific connector
python -m engine.ingestion.cli <connector> "query"

# Available connectors
python -m engine.ingestion.cli --list

# Check ingestion statistics
python -m engine.ingestion.cli status

# Verbose output
python -m engine.ingestion.cli -v serper "padel edinburgh"
```

**Available Connectors**:
- `serper` - Web search results
- `google_places` - Google Places API
- `openstreetmap` - OpenStreetMap data
- `open_charge_map` - EV charging stations
- `sport_scotland` - Sports facilities
- `edinburgh_council` - Council facilities

### Extraction CLI

For maintenance and troubleshooting:

```bash
# Retry failed extractions
python -m engine.extraction.cli --retry-failed

# Limit retries
python -m engine.extraction.cli --retry-failed --limit 10 --max-retries 3
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database (required)
DATABASE_URL="postgresql://user:pass@localhost:5432/edinburgh_finds"

# API Keys
ANTHROPIC_API_KEY="sk-ant-api03-..."  # Required for extraction
GOOGLE_PLACES_API_KEY="your-key"      # For Google Places connector
SERPER_API_KEY="your-key"             # For Serper connector

# Lens Configuration
LENS_ID="edinburgh_finds"             # Default lens to use

# Optional
LOG_LEVEL="INFO"
NODE_ENV="development"
```

### Lens Configuration

Lenses are stored in `engine/lenses/<lens_id>/lens.yaml`. The system loads lenses during bootstrap and validates their configuration.

**Lens Resolution Order**:
1. CLI argument (`--lens`)
2. Environment variable (`LENS_ID`)
3. Application config (`engine/config/app.yaml`)
4. Dev fallback (`--allow-default-lens`)

**Key Lens Components**:
- **Vocabulary**: Keywords that trigger specific connectors
- **Connector Rules**: Priority and trigger conditions for data sources
- **Facets**: UI categories like "Activities" and "Venue Type"
- **Values**: Canonical entities (e.g., "padel" → "Padel" with metadata)
- **Mapping Rules**: Regex patterns to extract canonical values from raw text
- **Modules**: Domain-specific extraction rules (e.g., court counts for sports facilities)

## Development

### Project Structure

```
edinburgh-finds/
├── engine/                 # Python backend
│   ├── ingestion/         # Data source connectors
│   ├── extraction/        # AI-powered entity extraction
│   ├── orchestration/     # Intelligent coordination
│   ├── lenses/           # Domain configuration
│   └── requirements.txt
├── web/                   # Next.js frontend
│   ├── package.json
│   └── src/
├── prisma/               # Database schema
└── .env.example         # Configuration template
```

### Key Dependencies

**Python (engine)**:
- `prisma` - Database ORM
- `anthropic` - AI extraction via Claude
- `aiohttp` - Async HTTP client
- `pydantic` - Data validation
- `instructor` - Structured AI outputs

**Node.js (web)**:
- `next` - React framework
- `@prisma/client` - Database client
- `tailwindcss` - Styling
- `lucide-react` - Icons

### Running Tests

```bash
# Python tests
cd engine
python -m pytest

# Node.js tests
cd web
npm test
```

### Database Migrations

```bash
# Create new migration
npx prisma migrate dev --name description

# Reset database
npx prisma migrate reset

# Generate client
npx prisma generate
```

## Monitoring and Troubleshooting

### Check System Status

```bash
# Ingestion statistics
python -m engine.ingestion.cli status

# Recent ingestions and failures
python -m engine.ingestion.cli --status
```

### Common Issues

**Database Connection Errors**:
- Verify `DATABASE_URL` in `.env`
- Ensure PostgreSQL is running
- Check database exists and is accessible

**API Key Errors**:
- Verify API keys in `.env`
- Check API quotas and limits
- Ensure keys have required permissions

**Extraction Failures**:
- Check `ANTHROPIC_API_KEY` is valid
- Review extraction logs for specific errors
- Use `--retry-failed` to reprocess failed extractions

**Lens Configuration Errors**:
- Validate YAML syntax in lens files
- Check lens exists in `engine/lenses/<lens_id>/`
- Verify `LENS_ID` environment variable

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Code Style

- Python: Follow PEP 8, use type hints
- TypeScript: Follow project ESLint configuration
- Commit messages: Use conventional commits format

## License

[Add your license information here]

## Support

For issues and questions:
- Check the troubleshooting section above
- Review CLI help: `python -m engine.orchestration.cli --help`
- Check ingestion status: `python -m engine.ingestion.cli status`
