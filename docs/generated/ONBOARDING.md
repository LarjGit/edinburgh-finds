# Onboarding Guide — Universal Entity Extraction Engine

**Welcome to the Universal Entity Extraction Engine!**

This guide will help you understand, set up, and start building with a vertical-agnostic discovery platform that transforms natural language queries into complete, accurate entity records through AI-powered multi-source orchestration.

---

## Table of Contents

1. [Welcome](#welcome)
2. [Getting Started](#getting-started)
3. [Your First Query](#your-first-query)
4. [Understanding the Architecture](#understanding-the-architecture)
5. [Developer Workflow](#developer-workflow)
6. [Building Your First Vertical](#building-your-first-vertical)
7. [Architectural Deep Dive](#architectural-deep-dive)
8. [Common Gotchas](#common-gotchas)
9. [Next Steps](#next-steps)

---

## Welcome

### What Is This System?

The Universal Entity Extraction Engine is a **horizontal, vertical-agnostic platform** that extracts, enriches, and persists structured entity data from multiple sources. It's designed to power discovery applications across unlimited domains (sports, restaurants, wine, events, etc.) without requiring code changes for new verticals.

**Core Principle: Engine vs Lens Separation**

The architecture separates a universal **Entity Engine** (Python) from vertical-specific **Lens Layers** (YAML config):

- **Engine** (domain-blind): Orchestrates data flow, extraction, deduplication, merge, and persistence. Knows nothing about "Padel" or "Wine".
- **Lenses** (domain-aware): Provide vocabulary, mapping rules, and interpretation logic as YAML configuration files.

**Scaling Strategy:** Adding a new vertical (Wine Discovery, Restaurant Finder) requires ZERO engine code changes—only a new `lens.yaml` configuration file.

### Project Overview

This codebase includes:

- **Python ETL Engine** (`engine/`): Multi-source ingestion, hybrid extraction (deterministic + LLM), lens-driven interpretation, deduplication, merge, and persistence.
- **Next.js 16 Frontend** (`web/`): React 19 application with Tailwind CSS v4 and shadcn/ui components.
- **PostgreSQL Database** (Supabase): Stores canonical entities with multi-valued dimension arrays (GIN indexes) and JSONB modules.
- **Reference Application**: Edinburgh Finds (padel/sports discovery) validates the architecture—it's not the architecture itself.

### Why This Architecture?

Traditional discovery platforms hardcode domain logic, making scaling painful. This system:

- Treats entity extraction as a **universal pipeline** operating on generic structures.
- Interprets all domain semantics through **pluggable Lens contracts**.
- Maintains **determinism and idempotency** across all stages.
- Prioritizes **data quality** over superficial coverage.

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.x** (for the engine)
- **Node.js 18+** (for the frontend)
- **PostgreSQL** (Supabase recommended)
- **Git** (to clone the repository)
- **API Keys**:
  - Anthropic API key (for LLM extraction)
  - Serper API key (for web search connector)
  - Google Places API key (optional, for enrichment)

### Clone the Repository

```bash
git clone https://github.com/yourusername/edinburgh_finds.git
cd edinburgh_finds
```

### Install Backend Dependencies

```bash
# Install Python dependencies
python -m pip install -r engine/requirements.txt

# Verify installation
pytest --version
```

### Install Frontend Dependencies

```bash
# Navigate to web directory
cd web

# Install Node.js dependencies
npm install

# Verify installation
npm run build
```

### Environment Setup

#### Backend Environment (.env)

Create a `.env` file in the project root:

```bash
# Anthropic API for LLM extraction
ANTHROPIC_API_KEY=sk-ant-...

# Serper API for web search
SERPER_API_KEY=your_serper_key

# Google Places API (optional)
GOOGLE_PLACES_API_KEY=your_google_key

# Default Lens (for development)
LENS_ID=edinburgh_finds
```

#### Frontend Environment (web/.env)

Create a `web/.env` file:

```bash
# Supabase PostgreSQL connection
DATABASE_URL=postgresql://user:password@host:5432/database?schema=public

# Next.js environment
NODE_ENV=development
```

### Database Setup

```bash
# Navigate to web directory
cd web

# Generate Prisma client from schema
npx prisma generate

# Sync schema to Supabase (development)
npx prisma db push

# Or create a migration (production)
npx prisma migrate dev --name init
```

### Verify Installation

Run the test suites to confirm everything is working:

```bash
# Backend tests
pytest

# Frontend build
cd web
npm run build
```

If all tests pass and the frontend builds successfully, you're ready to proceed!

---

## Your First Query

Let's run your first entity extraction query end-to-end.

### Step 1: Run the Orchestrator CLI

The orchestration CLI executes the full pipeline: query analysis → connector selection → ingestion → extraction → lens application → merge → persistence.

```bash
# From project root
python -m engine.orchestration.cli run "padel courts in Edinburgh"
```

**What Happens:**

1. **Lens Resolution**: Loads the Edinburgh Finds lens (configured via `LENS_ID`)
2. **Planning**: Analyzes query features ("padel", "Edinburgh") and selects connectors (SportScotland, GooglePlaces, Serper)
3. **Ingestion**: Fetches raw data from multiple sources in parallel
4. **Extraction**: Transforms raw payloads into structured primitives
5. **Lens Application**: Populates canonical dimensions (`canonical_activities`, `canonical_place_types`)
6. **Deduplication**: Groups entities representing the same real-world place
7. **Merge**: Deterministically combines multi-source data
8. **Finalization**: Generates slugs and persists to the Entity table

### Step 2: Understand the Results

The CLI outputs execution metadata:

```
Execution ID: exec_20260208_143022
Lens: edinburgh_finds (hash: a3f9c2...)
Connectors executed: sport_scotland, google_places, serper
Raw ingestions: 18 records
Extracted entities: 15 records
Merged entities: 8 records
Persisted entities: 8 records
```

### Step 3: Inspect the Database

Connect to your Supabase database and query the Entity table:

```sql
SELECT
    entity_name,
    entity_class,
    canonical_activities,
    canonical_place_types,
    modules->'sports_facility' as sports_data
FROM "Entity"
WHERE canonical_activities @> ARRAY['padel'];
```

You should see persisted entities with:

- **entity_class**: `place`
- **canonical_activities**: `["padel", "tennis"]`
- **canonical_place_types**: `["sports_facility", "indoor_sports_venue"]`
- **modules**: Structured JSONB data (e.g., `sports_facility.padel_courts.total: 3`)

### Step 4: View in the Web App

Start the Next.js development server:

```bash
cd web
npm run dev
```

Navigate to `http://localhost:3000` and search for "padel Edinburgh". You should see the entities you just extracted rendered as rich venue cards.

**Congratulations!** You've run your first end-to-end query through the Universal Entity Extraction Engine.

---

## Understanding the Architecture

The system operates as a strictly ordered, deterministic pipeline that transforms queries into canonical structured entities.

### Engine vs Lens Separation

The architecture enforces an absolute boundary between universal execution (Engine) and domain interpretation (Lens):

```mermaid
graph TD
    A[Query Input] --> B[Engine: Lens Resolution]
    B --> C[Engine: Planning]
    C --> D[Engine: Connector Execution]
    D --> E[Engine: Raw Ingestion]
    E --> F[Engine: Source Extraction]
    F --> G[Lens: Mapping Rules]
    G --> H[Engine: Classification]
    H --> I[Engine: Deduplication]
    I --> J[Engine: Merge]
    J --> K[Engine: Persistence]
    K --> L[Entity Database]
```

**Engine Responsibilities:**

- Universal entity classification (`place`, `person`, `organization`, `event`, `thing`)
- Storage and indexing of canonical dimensions as opaque values
- Orchestration, extraction, deduplication, merge, persistence
- Determinism, idempotency, and provenance tracking

**Lens Responsibilities:**

- Domain vocabulary (keywords, location indicators)
- Connector routing rules (which sources to use for which queries)
- Mapping rules (pattern → canonical dimension value)
- Module triggers (when to attach structured modules)
- Canonical value registry (display names, SEO slugs, icons)

### The 11-Stage Pipeline

Every execution flows through these stages in strict order:

1. **Input**: Accept natural-language query or entity identifier
2. **Lens Resolution & Validation**: Load and validate lens contract, compute hash
3. **Planning**: Derive query features, select connector execution plan
4. **Connector Execution**: Fetch raw data from multiple sources (parallel)
5. **Raw Ingestion Persistence**: Store immutable raw payloads
6. **Source Extraction**: Transform raw data into schema primitives (extractors MUST NOT emit canonical dimensions)
7. **Lens Application**: Populate canonical dimensions using mapping rules
8. **Classification**: Determine entity_class using universal rules
9. **Deduplication**: Group entities representing the same real-world entity
10. **Deterministic Merge**: Combine multi-source data using metadata-driven rules
11. **Finalization & Persistence**: Generate slugs, upsert to Entity table

**Critical Contracts:**

- **Extraction Boundary**: Extractors return ONLY schema primitives + raw observations (no `canonical_*` fields, no `modules`)
- **Lens Application**: Mapping rules populate canonical dimensions; module triggers attach structured data
- **Deterministic Merge**: Same inputs + lens contract → identical outputs (always)

### Data Flow Diagram

```mermaid
journey
    title Universal Entity Engine Data Flow
    section Ingestion
      Query arrives: 5: User
      Lens resolves: 5: Engine
      Connectors execute: 4: Engine
      Raw data persisted: 5: Engine
    section Extraction
      Source extraction: 4: Engine
      Lens mapping rules applied: 5: Lens
      Canonical dimensions populated: 5: Engine
    section Finalization
      Deduplication groups entities: 4: Engine
      Deterministic merge: 5: Engine
      Entity persisted: 5: Engine
    section Display
      Frontend queries Entity table: 5: User
      Rich venue cards displayed: 5: User
```

### Key Architectural Invariants

These 10 invariants MUST remain true for the system's lifetime (see `docs/target/system-vision.md`):

1. **Engine Purity**: Zero domain knowledge in engine code
2. **Lens Ownership of Semantics**: All domain logic in Lens contracts only
3. **Zero Engine Changes for New Verticals**: New verticals = new Lens YAML only
4. **Determinism and Idempotency**: Same inputs = same outputs, always
5. **Canonical Registry Authority**: All canonical values declared explicitly
6. **Fail-Fast Validation**: Invalid Lens contracts fail at bootstrap
7. **Schema-Bound LLM Usage**: LLMs produce validated structured output only
8. **No Permanent Translation Layers**: Universal schema is authoritative end-to-end
9. **Engine Independence**: Engine is useful without any specific vertical
10. **No Reference-Lens Exceptions**: Edinburgh Finds gets no special treatment

**Violations are architectural defects regardless of whether functionality appears to work.**

---

## Developer Workflow

This project follows **Test-Driven Development (TDD)** with strict quality gates.

### TDD Cycle: Red → Green → Refactor

```mermaid
graph LR
    A[Write Failing Test] --> B[Confirm Test Fails]
    B --> C[Implement Minimum Code]
    C --> D[Test Passes]
    D --> E[Refactor for Quality]
    E --> F[Tests Still Pass]
    F --> G[Commit with Co-Author]
```

**Example Workflow:**

```bash
# 1. Red: Write failing test
# Edit tests/engine/extraction/test_extractor.py
def test_extract_coordinates_from_serper_payload():
    raw_payload = {"coordinates": {"lat": 55.9533, "lng": -3.1883}}
    extractor = SerperExtractor()
    result = extractor.extract(raw_payload)
    assert result["latitude"] == 55.9533
    assert result["longitude"] == -3.1883

# 2. Confirm it fails
pytest tests/engine/extraction/test_extractor.py::test_extract_coordinates_from_serper_payload
# Expected: FAILED (key error or assertion failure)

# 3. Green: Implement extraction logic
# Edit engine/extraction/extractors/serper.py
def extract(self, raw_payload: dict) -> dict:
    coords = raw_payload.get("coordinates", {})
    return {
        "latitude": coords.get("lat"),
        "longitude": coords.get("lng"),
    }

# 4. Confirm it passes
pytest tests/engine/extraction/test_extractor.py::test_extract_coordinates_from_serper_payload
# Expected: PASSED

# 5. Refactor: Improve code quality
# Add validation, error handling, type hints

# 6. Commit with co-author attribution
git add .
git commit -m "feat(extraction): extract coordinates from Serper payload

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Schema Changes Workflow

**CRITICAL:** YAML schemas are the single source of truth. All Python, Prisma, and TypeScript schemas are auto-generated.

```bash
# 1. Edit YAML schema
# File: engine/config/schemas/entity.yaml
# Add a new field to universal schema

# 2. Validate schema
python -m engine.schema.generate --validate

# 3. Regenerate all derived schemas
python -m engine.schema.generate --all
# Regenerates:
#   - engine/schema/entity.py (Python FieldSpecs)
#   - web/prisma/schema.prisma (Prisma schema)
#   - engine/prisma/schema.prisma (Prisma Python schema)
#   - web/lib/types/generated/entity.ts (TypeScript interfaces)

# 4. Never manually edit generated files
# They have "DO NOT EDIT" headers and will be overwritten
```

### Running Tests

```bash
# Run all tests (backend)
pytest

# Run fast tests only (excludes @pytest.mark.slow)
pytest -m "not slow"

# Run specific module tests
pytest engine/orchestration/

# Run with coverage report
pytest --cov=engine --cov-report=html
# Target: >80% coverage for all new code

# View coverage report
open htmlcov/index.html
```

```bash
# Frontend tests
cd web
CI=true npm test  # Non-interactive mode

# Linting
npm run lint

# Build (catches type errors)
npm run build
```

### Quality Gates (All Required)

Before committing, ensure:

- ✅ All tests pass (`pytest` for backend, `npm run build` for frontend)
- ✅ >80% test coverage (`pytest --cov=engine`)
- ✅ No linting errors (`npm run lint` for frontend)
- ✅ Schema validation passes (`python -m engine.schema.generate --validate`)

### Commit Message Format

Use conventional commits with co-author attribution:

```
<type>(<scope>): <description>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**

```
feat(lenses): add wine discovery lens with grape variety mapping
fix(merge): prevent duplicate canonical values in array merge
docs(onboarding): add setup instructions for PostgreSQL
test(extraction): add fixtures for SportScotland API responses
refactor(orchestration): simplify connector selection logic
```

---

## Building Your First Vertical

Let's build a simple "Wine Discovery" vertical to demonstrate how Lens contracts enable zero-code extensibility.

### Step 1: Define Vocabulary

Identify the domain-specific terms your vertical needs:

**Wine Discovery Vocabulary:**

- **Activity keywords**: wine tasting, vineyard tours, wine education
- **Location indicators**: wine regions (Bordeaux, Tuscany, Napa Valley)
- **Role keywords**: winery, wine bar, wine merchant, sommelier
- **Canonical wine types**: red, white, rosé, sparkling, fortified
- **Grape varieties**: Cabernet Sauvignon, Chardonnay, Pinot Noir, Merlot

### Step 2: Create Lens YAML Structure

Create a new lens directory:

```bash
mkdir -p engine/lenses/wine_discovery
touch engine/lenses/wine_discovery/lens.yaml
```

### Step 3: Define Lens Contract

Edit `engine/lenses/wine_discovery/lens.yaml`:

```yaml
lens_id: wine_discovery
version: "1.0.0"
display_name: "Wine Discovery"
description: "Discover wineries, wine bars, and wine experiences"

vocabulary:
  activity_keywords:
    - wine tasting
    - vineyard tour
    - wine education
    - wine pairing
    - cellar door

  location_indicators:
    - bordeaux
    - tuscany
    - napa valley
    - barossa valley
    - marlborough

  role_keywords:
    - winery
    - wine bar
    - wine merchant
    - wine shop
    - tasting room
    - vineyard

connector_rules:
  serper:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [winery, wine bar, vineyard, wine tasting]

  google_places:
    priority: medium
    triggers:
      - type: any_keyword_match
        keywords: [winery, wine bar]

mapping_rules:
  - rule_id: map_cabernet_sauvignon
    pattern: "(?i)cabernet\\s*sauvignon|cab\\s*sauv"
    dimension: canonical_wine_types
    value: cabernet_sauvignon
    source_fields: [description, raw_categories, entity_name]
    confidence: 0.95

  - rule_id: map_chardonnay
    pattern: "(?i)chardonnay"
    dimension: canonical_wine_types
    value: chardonnay
    source_fields: [description, raw_categories]
    confidence: 0.95

  - rule_id: map_winery_role
    pattern: "(?i)winery|vineyard|estate"
    dimension: canonical_roles
    value: winery
    source_fields: [raw_categories, entity_name]
    confidence: 0.90

  - rule_id: map_wine_bar_role
    pattern: "(?i)wine\\s*bar|wine\\s*lounge"
    dimension: canonical_roles
    value: wine_bar
    source_fields: [raw_categories, entity_name]
    confidence: 0.90

module_triggers:
  - when:
      dimension: canonical_roles
      values: [winery]
    add_modules: [wine_profile]

  - when:
      dimension: canonical_roles
      values: [wine_bar, wine_merchant]
    add_modules: [wine_selection]

modules:
  wine_profile:
    description: "Profile for wine producers and vineyards"
    field_rules:
      - rule_id: extract_grape_varieties
        target_path: grape_varieties
        source_fields: [description, VarietiesGrown]
        extractor: regex_capture
        pattern: "(?i)(cabernet|chardonnay|pinot noir|merlot|syrah)"
        confidence: 0.85
        normalizers: [lowercase, list_wrap]

      - rule_id: extract_wine_types
        target_path: wine_types
        source_fields: [description]
        extractor: regex_capture
        pattern: "(?i)(red|white|rosé|sparkling|fortified)"
        confidence: 0.80
        normalizers: [lowercase, list_wrap]

  wine_selection:
    description: "Wine selection offered by bars and merchants"
    field_rules:
      - rule_id: extract_wine_count
        target_path: wines_available
        source_fields: [description, NumWines]
        extractor: numeric_parser
        confidence: 0.85

canonical_values:
  cabernet_sauvignon:
    display_name: "Cabernet Sauvignon"
    seo_slug: "cabernet-sauvignon"
    icon: "wine-glass"
    category: red

  chardonnay:
    display_name: "Chardonnay"
    seo_slug: "chardonnay"
    icon: "wine-glass"
    category: white

  winery:
    display_name: "Winery"
    seo_slug: "winery"
    icon: "vineyard"

  wine_bar:
    display_name: "Wine Bar"
    seo_slug: "wine-bar"
    icon: "wine-bar"
```

### Step 4: Test with Queries

Run test queries to validate the lens:

```bash
# Set the active lens
export LENS_ID=wine_discovery

# Run a test query
python -m engine.orchestration.cli run "Cabernet Sauvignon wineries in Napa Valley"
```

**Expected Behavior:**

1. Lens resolution loads `wine_discovery` lens
2. Planning detects "cabernet sauvignon", "winery", "napa valley" keywords
3. Connectors (Serper, GooglePlaces) fetch raw data
4. Extraction produces primitives (entity_name, latitude, etc.)
5. Lens application:
   - Maps "cabernet sauvignon" → `canonical_wine_types: ["cabernet_sauvignon"]`
   - Maps "winery" → `canonical_roles: ["winery"]`
   - Triggers `wine_profile` module
   - Populates `wine_profile.grape_varieties`, `wine_profile.wine_types`
6. Entity persisted with canonical dimensions and modules

### Step 5: Inspect Entity Store

Verify module fields were populated:

```sql
SELECT
    entity_name,
    canonical_roles,
    canonical_wine_types,
    modules->'wine_profile'->'grape_varieties' as grapes
FROM "Entity"
WHERE canonical_roles @> ARRAY['winery'];
```

**Congratulations!** You've built your first vertical with ZERO engine code changes.

---

## Architectural Deep Dive

Now that you've experienced the system hands-on, let's explore the architectural philosophy that makes this possible.

### Step 1: Read the Architectural Constitution

Before contributing, you MUST read:

**`docs/target/system-vision.md`** (30 minutes)

This document defines:

- The core mission (horizontal, vertical-agnostic entity extraction)
- 10 immutable invariants that govern all decisions
- Engine vs Lens boundaries
- Success criteria: "One Perfect Entity" validation requirement
- What the system explicitly does NOT do

**Key Takeaways:**

- Engine purity is non-negotiable (zero domain knowledge)
- Lenses own ALL semantics (vocabulary, mapping, interpretation)
- Determinism and idempotency are mandatory
- Data quality (entity store) is the ultimate correctness signal

### Step 2: Read the Runtime Specification

**`docs/target/architecture.md`** (60 minutes)

This document defines:

- Concrete execution pipeline and artifact flow
- Locked extraction contract (Phase 1: primitives only, Phase 2: lens application)
- Deterministic merge semantics
- Canonical data model and dimensions
- Module architecture and field extraction
- Connector extensibility

**Key Takeaways:**

- Pipeline stages execute in strict order
- Artifacts are immutable once created
- Extractors MUST NOT emit `canonical_*` fields or `modules`
- Merge is metadata-driven (no connector-specific logic)

### Step 3: Understand the 10 Invariants

These invariants define what must remain true forever:

1. **Engine Purity**: No domain-specific terms, taxonomies, or logic in engine code
2. **Lens Ownership of Semantics**: All interpretation lives in Lens YAML contracts
3. **Zero Engine Changes for New Verticals**: New behavior = new Lens config only
4. **Determinism and Idempotency**: Same inputs → same outputs, always
5. **Canonical Registry Authority**: All canonical values explicitly declared
6. **Fail-Fast Validation**: Invalid Lens contracts abort at bootstrap
7. **Schema-Bound LLM Usage**: LLMs produce validated structured output only
8. **No Permanent Translation Layers**: Universal schema is authoritative
9. **Engine Independence**: Engine is useful without any specific vertical
10. **No Reference-Lens Exceptions**: Edinburgh Finds gets no special treatment

**Enforcement:** Violations are architectural defects, even if functionality appears correct.

### Step 4: Explore the Codebase

**Engine Layer (`engine/`):**

- `config/schemas/*.yaml`: Universal schema definitions (single source of truth)
- `ingestion/connectors/`: Data source integrations (Serper, GooglePlaces, OSM, etc.)
- `extraction/extractors/`: Per-source extractors (emit primitives only)
- `orchestration/`: Runtime control plane (planning, execution, merge)
- `lenses/`: Lens contracts (YAML configs for vertical interpretation)
- `schema/generators/`: Auto-generate Python/Prisma/TypeScript from YAML

**Frontend Layer (`web/`):**

- `app/`: Next.js App Router pages
- `lib/`: Shared utilities, types, Prisma client
- `prisma/schema.prisma`: Auto-generated from YAML schemas

**Documentation (`docs/`):**

- `target/system-vision.md`: Immutable architectural constitution
- `target/architecture.md`: Runtime implementation specification
- `plans/`: Phase-by-phase implementation plans
- `generated/`: Auto-generated documentation suite

### Step 5: Validate Your Understanding

Ask yourself:

- Can I explain the difference between Engine and Lens responsibilities?
- Do I understand why extractors must not emit canonical dimensions?
- Can I describe how a new vertical is added (Lens YAML only)?
- Do I know where to find schema definitions (YAML, not Python/Prisma)?
- Can I explain why determinism is mandatory?

If uncertain on any question, re-read the corresponding section in `system-vision.md` or `architecture.md`.

---

## Common Gotchas

Avoid these common pitfalls when working with the codebase:

### 1. Lens Implementation is Incomplete

**Issue:** The canonical dimension extraction system is partially implemented. Extractors currently don't populate `canonical_activities`, `canonical_roles`, `canonical_place_types`, or `canonical_access` arrays from lens mapping rules.

**Workaround:** Manual population or extraction logic until lens-driven extraction is wired up. The system requires at least one "perfect entity" flowing end-to-end through the complete pipeline.

**Reference:** `docs/target/architecture.md` Section 4 (Orchestration Pipeline), `docs/target/system-vision.md` Section 6.3 (One Perfect Entity).

### 2. Schema Changes Require Regeneration

**Issue:** Manually editing generated files (Python FieldSpecs, Prisma schemas, TypeScript interfaces) causes inconsistencies.

**Solution:** ALWAYS edit YAML schemas and regenerate:

```bash
# Edit YAML schema
vim engine/config/schemas/entity.yaml

# Regenerate ALL derived schemas
python -m engine.schema.generate --all
```

**Never manually edit files with "DO NOT EDIT" headers.**

### 3. Tests Use CI=true for Non-Interactive Mode

**Issue:** Frontend tests enter watch mode by default, blocking CI pipelines.

**Solution:**

```bash
# Frontend: Prevents watch mode
CI=true npm test

# Backend: Already non-interactive
pytest
```

### 4. Entity Class vs Vertical-Specific Types

**Issue:** Using domain-specific types like "Venue" or "Restaurant" in engine code.

**Wrong:**

```python
if entity_type == "Venue":  # ❌ Vertical-specific
    ...
```

**Right:**

```python
if entity.entity_class == "place":  # ✅ Universal
    # Use lenses/modules for vertical interpretation
```

### 5. Pytest Markers for Test Performance

**Issue:** Some tests are slow (>1 second), blocking fast iteration.

**Solution:** Mark slow tests with `@pytest.mark.slow`:

```python
@pytest.mark.slow
def test_full_extraction_pipeline():
    # Slow integration test
    ...
```

```bash
# Run fast tests only
pytest -m "not slow"

# Run all tests
pytest
```

### 6. Orchestration Registry Metadata

**Issue:** Adding a new connector without registering metadata breaks orchestration.

**Solution:** When adding a connector:

1. Implement `BaseConnector` interface
2. Add to `engine/orchestration/registry.py` with `ConnectorSpec` (cost, trust, phase, timeout)
3. Add adapter mapping in `engine/orchestration/adapters.py`
4. Write tests in `tests/engine/orchestration/test_registry.py`

### 7. Extraction Boundary Violations

**Issue:** Extractors emit `canonical_activities` or `modules` fields, violating the extraction contract.

**Solution:** Extractors MUST return ONLY:

- Schema primitives (entity_name, latitude, street_address, phone, etc.)
- Raw observations (raw_categories, description, connector-native fields)

Canonical dimensions and modules are populated by lens application (Phase 2), not extractors (Phase 1).

**Reference:** `docs/target/architecture.md` Section 4.2 (Extraction Boundary).

---

## Next Steps

### For Contributors

1. **Read the Golden Docs** (Required):
   - `docs/target/system-vision.md` (30 min)
   - `docs/target/architecture.md` (60 min)
   - `CLAUDE.md` (15 min)

2. **Set Up Your Environment**:
   - Complete [Getting Started](#getting-started)
   - Run [Your First Query](#your-first-query)
   - Verify all quality gates pass

3. **Explore the Codebase**:
   - Browse `engine/` and `web/` directories
   - Read test examples in `tests/engine/`
   - Study existing Lens configs in `engine/lenses/`

4. **Build Your First Feature**:
   - Follow [Developer Workflow](#developer-workflow)
   - Practice TDD (Red → Green → Refactor)
   - Ensure >80% test coverage

5. **Understand Data Flow**:
   - Trace a query through the 11-stage pipeline
   - Inspect `RawIngestion`, `ExtractedEntity`, and `Entity` tables
   - Use CLI tools to observe execution metadata

### For Product Teams

1. **Define Your Vertical**:
   - Identify domain vocabulary (keywords, roles, place types)
   - Map domain terms to canonical dimensions
   - Define module schemas for structured data

2. **Create a Lens Contract**:
   - Follow [Building Your First Vertical](#building-your-first-vertical)
   - Write mapping rules backed by real fixtures
   - Configure connector routing rules

3. **Validate Data Quality**:
   - Run test queries for your vertical
   - Inspect entity store for completeness
   - Verify canonical dimensions and modules are populated

4. **Build Frontend Components**:
   - Query Entity table via Prisma
   - Render vertical-specific UI (venue cards, filters, maps)
   - Display canonical dimensions and module data

### For Architects

1. **Study Architectural Invariants**:
   - Internalize the 10 immutable invariants
   - Understand Engine vs Lens boundary enforcement
   - Learn deterministic merge semantics

2. **Explore Extensibility**:
   - Trace how new connectors integrate (registry metadata)
   - Understand how new lenses enable verticals (zero code changes)
   - Study module architecture (namespaced structured data)

3. **Contribute to Architecture**:
   - Propose new extractor types (with purity validation)
   - Design new canonical dimensions (requires architectural review)
   - Improve merge strategies (metadata-driven, domain-blind)

### Additional Resources

- **Implementation Plans**: `docs/plans/` (phase-by-phase feature development)
- **Engine Documentation**: `engine/docs/` (detailed guides for ingestion, extraction, schema management)
- **Test Examples**: `tests/engine/` (testing patterns and fixtures)
- **Mermaid Diagrams**: `docs/generated/diagrams/` (visual architecture references)

### Community & Support

- **GitHub Issues**: Report bugs, request features
- **Discussions**: Ask questions, share ideas
- **Pull Requests**: Contribute code, documentation, lenses

**Welcome to the community!** We're excited to see what verticals you'll build.

---

## Summary

You've now learned:

- **What the Universal Entity Extraction Engine is** (vertical-agnostic discovery platform)
- **How to set up your environment** (Python, Node.js, PostgreSQL, API keys)
- **How to run your first query** (CLI → entity store → web app)
- **The Engine vs Lens architecture** (universal execution + domain interpretation)
- **The 11-stage pipeline** (ingestion → extraction → lens application → merge → persistence)
- **The TDD workflow** (Red → Green → Refactor → Commit)
- **How to build a new vertical** (Lens YAML only, zero code changes)
- **The 10 architectural invariants** (what must remain true forever)
- **Common gotchas** (lens implementation status, schema regeneration, extraction boundary)

**Key Takeaway:** This system treats entity extraction as a universal pipeline and interprets all domain semantics through pluggable Lens contracts. Adding a new vertical (Wine, Restaurants, Events) requires ZERO engine code changes—only a new `lens.yaml` configuration file.

**Next Steps:** Read `docs/target/system-vision.md` and `docs/target/architecture.md` to understand the architectural philosophy, then start building your first vertical!

---

**Generated:** 2026-02-08
**System:** Universal Entity Extraction Engine
**Reference Application:** Edinburgh Finds
