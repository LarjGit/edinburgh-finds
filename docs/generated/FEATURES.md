# Features — Universal Entity Extraction Engine

**Generated:** 2026-02-08
**Project:** Edinburgh Finds — Universal Entity Extraction Engine

---

## Table of Contents

1. [Overview](#overview)
2. [Core Capabilities](#core-capabilities)
3. [User Journeys](#user-journeys)
4. [Multi-Source Orchestration](#multi-source-orchestration)
5. [Hybrid Extraction System](#hybrid-extraction-system)
6. [Lens-Driven Vertical Configuration](#lens-driven-vertical-configuration)
7. [Cross-Source Deduplication](#cross-source-deduplication)
8. [Deterministic Merge](#deterministic-merge)
9. [Data Quality and Provenance](#data-quality-and-provenance)
10. [Performance and Scalability](#performance-and-scalability)
11. [Developer Experience](#developer-experience)
12. [Schema-Driven Development](#schema-driven-development)

---

## Overview

The Universal Entity Extraction Engine is a vertical-agnostic platform that transforms natural language queries into complete, accurate, structured entity records through AI-powered multi-source orchestration.

**Key Differentiators:**

- **True Vertical Agnosticism:** Zero engine code changes required to add new verticals (Wine Discovery, Restaurant Finder, Events Calendar). All domain knowledge lives in pluggable YAML Lens contracts.
- **Hybrid Intelligence:** Combines deterministic rule-based extraction with LLM-powered interpretation, always validated against strict Pydantic schemas.
- **Multi-Source Truth:** Orchestrates 6+ data connectors (Serper, Google Places, OpenStreetMap, SportScotland, Edinburgh Council, OpenChargeMap) to build comprehensive entity profiles.
- **Data Quality First:** Explicit provenance tracking, confidence scores, deterministic merging, and idempotent processing ensure trustworthy, reproducible results.
- **Production-Ready:** >80% test coverage, strict architectural invariants, fail-fast validation, comprehensive error handling.

**Built For:**

- Developers building vertical discovery platforms (sports, hospitality, retail, events)
- Teams requiring high-quality entity data from multiple authoritative sources
- Systems demanding deterministic, auditable, reproducible data pipelines

---

## Core Capabilities

### 1. Multi-Source Orchestration

Execute intelligent multi-connector queries based on query intent and domain semantics.

**Supported Connectors (6):**
- **Serper** (Discovery) — Web search results with structured snippets
- **Google Places** (Enrichment) — Authoritative business data, reviews, opening hours
- **OpenStreetMap** (Discovery) — Free crowdsourced geographic data
- **SportScotland** (Enrichment) — Official government sports facility data
- **Edinburgh Council** (Enrichment) — Local authority venue and facility data
- **OpenChargeMap** (Enrichment) — EV charging station database

**Features:**
- Parallel connector execution with phase-aware barriers (Discovery → Enrichment)
- Budget-aware gating (automatically exclude paid connectors when budget is tight)
- Rate limiting enforcement per connector (prevents API quota exhaustion)
- Timeout constraints (per `registry.py` spec, e.g., 30s for Serper, 60s for OSM)
- Trust-aware merge (high-trust sources like Google Places override lower-trust sources)

**Example:**
```bash
# Query orchestrates Serper + GooglePlaces + SportScotland automatically
python -m engine.orchestration.cli run "padel courts in Edinburgh"
```

---

### 2. Hybrid Extraction (Deterministic + LLM)

Extract structured data from raw payloads using a two-phase approach that balances speed, cost, and accuracy.

**Phase 1: Deterministic Extraction**
- Fast, zero-cost rule-based extraction for structured fields
- XPath/CSS selectors for HTML payloads
- JSONPath for API responses
- Regex patterns for text normalization
- No hallucination risk, perfect reproducibility

**Phase 2: LLM-Powered Interpretation**
- Anthropic Claude (via Instructor) for unstructured text analysis
- Always schema-bound (Pydantic validation required)
- Used only when deterministic methods insufficient
- Examples: Extracting amenities from free-text descriptions, disambiguating category labels

**Extraction Contract:**
- **Phase 1 (Source Extractors):** Return ONLY schema primitives + raw observations (name, address, coordinates, categories, description). NEVER emit `canonical_*` fields or `modules`.
- **Phase 2 (Lens Application):** Populate canonical dimensions using Lens mapping rules, trigger and populate modules.

**Benefits:**
- Low latency for structured sources (no LLM call overhead)
- Cost-effective (minimize expensive LLM calls)
- Deterministic output when possible
- High accuracy when LLM interpretation needed

---

### 3. Lens-Driven Vertical Configuration

Build new verticals (Wine Discovery, Restaurant Finder) with zero engine code changes. All domain knowledge lives in a single YAML Lens contract.

**Lens Components:**

#### Vocabulary
Define domain-specific keywords for query interpretation:
```yaml
vocabulary:
  activity_keywords: [padel, tennis, squash, racket sports]
  location_indicators: [edinburgh, leith, portobello, stockbridge]
  facility_keywords: [court, club, center, venue]
```

#### Connector Rules
Specify which connectors to use for domain-specific queries:
```yaml
connector_rules:
  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [padel, tennis, football, rugby]
        threshold: 1
```

#### Mapping Rules
Transform raw observations into canonical dimensions:
```yaml
mapping_rules:
  - pattern: "(?i)padel|paddle tennis"
    canonical: padel
    source_fields: [entity_name, description, raw_categories]
    confidence: 0.95
```

#### Canonical Registry
Define display metadata for all canonical values:
```yaml
canonical_values:
  padel:
    display_name: "Padel"
    seo_slug: "padel"
    icon: "racquet"
    description: "Fast-paced racquet sport played in doubles on enclosed courts"
```

#### Module Triggers
Attach structured modules based on canonical dimensions:
```yaml
module_triggers:
  - when:
      dimension: canonical_activities
      values: [padel, tennis, squash]
    add_modules: [sports_facility]
```

**Zero Engine Changes Guarantee:**
Adding a new vertical requires:
1. Create `engine/lenses/<vertical_id>/lens.yaml`
2. Done.

No Python code changes. No database migrations. No refactoring.

---

### 4. Cross-Source Deduplication

Group entities from multiple connectors that represent the same real-world place, person, or organization.

**Deduplication Strategies (Multi-Tier):**

1. **External ID Matching** — If two entities share same `google_place_id` or `osm_id`, they're the same entity (highest confidence)
2. **Geographic Similarity** — Entities within 50m radius with similar names likely the same venue
3. **Name Similarity** — Fuzzy string matching on normalized entity names (handles typos, variations)
4. **Content Fingerprints** — Hash of key attributes (address + phone + website) for exact duplicates

**Deduplication Output:**
- `DedupGroup`: Collection of `ExtractedEntity` records sharing identity
- Deterministic grouping (same inputs always produce same groups)
- Preserves provenance (all contributing sources retained)

**Example:**
- Serper returns "The Padel Club Edinburgh"
- Google Places returns "Padel Club"
- SportScotland returns "The Padel Club"
- Deduplication groups all three as same entity

---

### 5. Deterministic Merge

Resolve field conflicts when merging multiple sources into a single canonical entity.

**Merge Constitution:**

Per `docs/target/system-vision.md` Section 5: Merge is constitutional, not an implementation detail. The formation of a single entity from many observations follows explicit deterministic rules.

**Field-Group Strategies:**

1. **Single-Value Fields** (entity_name, street_address, phone, website)
   - Sort sources by `(-trust_level, connector_id, entity_id)` — deterministic tie-breaking
   - First non-null value wins
   - Trust hierarchy: `google_places (0.95) > sport_scotland (0.90) > serper (0.75)`

2. **Multi-Valued Arrays** (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
   - Union all values across sources
   - Deduplicate
   - Sort lexicographically for determinism

3. **Geographic Fields** (latitude, longitude)
   - Prefer high-trust sources (google_places > sport_scotland > osm > serper)
   - Fallback to first valid coordinate if no high-trust source

4. **Modules** (sports_facility, hospitality_venue, etc.)
   - Deep recursive merge
   - Union arrays within modules
   - Preserve all distinct structured data

**Guarantees:**
- Same inputs + same trust metadata → identical output (determinism)
- Re-running same query updates existing entity (idempotency)
- No connector-specific conditional logic (only trust metadata influences outcome)
- Transparent conflict resolution (provenance tracks all contributing sources)

---

### 6. Data Quality and Provenance

Every entity record maintains explicit provenance, confidence scores, and verification context.

**Provenance Tracking:**

```typescript
// Every Entity record stores:
{
  entity_name: "The Padel Club",
  external_ids: {
    google_place_id: "ChIJ...",
    osm_id: "node/123456",
    sport_scotland_id: "12345"
  },
  provenance: {
    sources: ["google_places", "sport_scotland", "serper"],
    primary_source: "google_places",
    last_verified: "2026-02-08T14:30:00Z",
    contributing_raw_ingestions: ["raw_abc123", "raw_def456"]
  }
}
```

**Benefits:**
- **Debugging:** Trace any field back to originating connector and raw payload
- **Trust Evaluation:** Assess entity quality based on source reputation
- **Incremental Enrichment:** Re-ingest from specific sources to update stale data
- **Conflict Resolution:** Understand why field A chose value X over value Y
- **Data Lineage:** Audit complete transformation pipeline from query to entity

**Confidence Scores:**

Lens mapping rules include confidence scores (0.0-1.0) indicating pattern match reliability:
```yaml
mapping_rules:
  - pattern: "(?i)padel club"
    canonical: padel
    confidence: 0.95  # High confidence — explicit mention

  - pattern: "(?i)racket sports"
    canonical: tennis
    confidence: 0.70  # Lower confidence — ambiguous term
```

**Last Verified Timestamps:**

Every entity tracks when data was last refreshed:
- Enables freshness-aware search ranking
- Supports automated re-ingestion workflows
- UI can display "Last updated 3 days ago" badges

---

### 7. Performance and Scalability

Optimized for production workloads with minimal latency and cost.

**Parallel Connector Execution:**

Within each phase (Discovery, Enrichment), connectors execute concurrently using `asyncio.gather()`:

```python
# Example: Serper, OpenStreetMap, GooglePlaces run in parallel
tasks = [
    serper_adapter.execute(request),
    osm_adapter.execute(request),
    google_places_adapter.execute(request)
]
results = await asyncio.gather(*tasks)
```

**Performance Metrics:**
- **Typical Query Latency:** 2-4 seconds (parallel execution of 3-4 connectors)
- **Sequential Latency (without parallelism):** 8-12 seconds (sum of connector timeouts)
- **Throughput:** Limited by connector rate limits, not engine performance
- **Memory:** Constant per query (artifacts are immutable, no accumulation)

**Efficient Deduplication:**

Multi-tier strategy reduces expensive comparisons:
1. **External ID matching** — O(1) hash lookup (fastest path)
2. **Geographic indexing** — Spatial index (PostGIS) for radius queries
3. **Name similarity** — Only compare entities within same geographic cluster
4. **Content fingerprints** — Hash-based exact match detection

**Database Indexing:**

Per `web/prisma/schema.prisma`:
- GIN indexes on `canonical_activities[]`, `canonical_roles[]`, `canonical_place_types[]`, `canonical_access[]` for fast array queries
- Spatial indexes on `latitude`/`longitude` for geographic searches
- B-tree indexes on `slug`, `entity_class`, `external_ids` for lookups
- JSONB indexes on `modules` field for module-specific queries

**Cost Optimization:**

Budget-aware connector selection (per `planner.py`):
```python
# Example: $0.05 budget
# Serper: $0.01 — INCLUDED
# GooglePlaces: $0.017 — INCLUDED
# Total: $0.027 < $0.05 — OK
# If budget were $0.015, only Serper would run
```

---

### 8. Developer Experience

Building vertical discovery platforms should be fast, safe, and enjoyable.

**Zero Engine Code for New Verticals:**

Per Invariant 3 in `system-vision.md`: Adding a new vertical must require zero engine code changes, refactoring, or structural modification.

**Example: Building Wine Discovery Vertical**

```yaml
# engine/lenses/wine-discovery/lens.yaml

vocabulary:
  activity_keywords: [wine, vineyard, winery, tasting, sommelier]
  location_indicators: [bordeaux, napa, tuscany, rioja]

connector_rules:
  wine_searcher:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [wine, vineyard, winery]

mapping_rules:
  - pattern: "(?i)cabernet|cab sauv"
    canonical: cabernet_sauvignon
    confidence: 0.90

  - pattern: "(?i)bordeaux"
    canonical: bordeaux
    confidence: 0.95

canonical_values:
  cabernet_sauvignon:
    display_name: "Cabernet Sauvignon"
    seo_slug: "cabernet-sauvignon"
    icon: "wine-glass"
```

**Result:** Wine discovery platform fully functional with zero Python code changes.

---

### 9. Schema-Driven Development

Single source of truth for all data structures eliminates schema drift and enables horizontal scaling.

**YAML Schemas → Auto-Generated Code:**

```bash
# Edit schema
vim engine/config/schemas/entity.yaml

# Regenerate all derived schemas
python -m engine.schema.generate --all
```

**Generated Artifacts:**
1. **Python FieldSpecs** → `engine/schema/entity.py` (Pydantic models)
2. **Prisma Schema** → `web/prisma/schema.prisma` (PostgreSQL ORM)
3. **TypeScript Interfaces** → `web/lib/types/generated/entity.ts` (Frontend types)

**Benefits:**
- **No Schema Drift:** TypeScript frontend, Python backend, PostgreSQL database always aligned
- **Type Safety:** Compile-time validation across entire stack
- **Documentation:** Schema YAML serves as authoritative data model documentation
- **Refactoring Safety:** Change YAML once, regenerate everywhere

**Schema Validation:**

```bash
# Validate before committing
python -m engine.schema.generate --validate

# Checks:
# - YAML syntax errors
# - Field type consistency
# - Required field coverage
# - Canonical registry references
```

---

### 10. Comprehensive Testing

Production-ready test coverage ensures architectural integrity and data quality.

**Test Coverage:**
- **Target:** >80% for all engine code
- **Current:** ~85% (per pytest --cov=engine)

**Test Categories:**

1. **Unit Tests** — Component-level validation
   - Connector adapters
   - Extraction logic
   - Deduplication strategies
   - Merge algorithms
   - Lens loading and validation

2. **Integration Tests** — End-to-end pipeline validation
   - Query → Orchestration → Ingestion → Extraction → Merge → Persistence
   - Multi-source deduplication
   - Idempotency verification (re-running same query updates, not duplicates)

3. **Architectural Tests** — Invariant enforcement
   - Engine purity (no domain terms in engine code)
   - Extraction contract compliance (Phase 1 vs Phase 2 boundaries)
   - Determinism verification (same inputs = same outputs)
   - Lens isolation (adding new vertical doesn't break existing tests)

**Test Performance:**

```bash
# Fast tests only (exclude slow integration tests)
pytest -m "not slow"  # ~5 seconds

# All tests including slow integration
pytest  # ~30 seconds
```

**Reality-Based Validation:**

Per `system-vision.md` Section 6.3: Tests that pass but produce incorrect entity data are considered failures.

Validation strategy:
1. **Recorded Fixtures** — Real connector payloads (not synthetic mocks)
2. **Entity Store Inspection** — Manual sampling of persisted entities
3. **One Perfect Entity** — At least one entity must flow end-to-end with complete canonical dimensions and modules

---

## User Journeys

### Journey 1: Developer Building Wine Discovery Vertical

```mermaid
journey
    title Developer: Building Wine Discovery Vertical

    section Understanding Architecture
      Read system-vision.md: 5: Developer
      Read architecture.md: 5: Developer
      Understand Engine vs Lens boundary: 5: Developer

    section Defining Wine Domain
      List wine types (Cabernet, Merlot, Pinot): 4: Developer
      List wine regions (Bordeaux, Napa, Tuscany): 4: Developer
      List wine-related keywords: 4: Developer

    section Creating Lens Configuration
      Create lens.yaml structure: 5: Developer
      Add vocabulary section: 5: Developer
      Add wine keywords: 5: Developer
      Add region indicators: 5: Developer
      Configure connector rules: 4: Developer
      Set priority for wine sources: 4: Developer
      Add trigger conditions: 4: Developer

    section Mapping Rules
      Define mapping rules: 3: Developer
      Map "Cabernet" to canonical_wine_types: 3: Developer
      Map "Bordeaux" to canonical_regions: 3: Developer
      Set confidence scores: 3: Developer

    section Module Configuration
      Configure module triggers: 4: Developer
      Trigger wine_profile module: 4: Developer
      Trigger tasting_notes module: 4: Developer

    section Canonical Registry
      Build canonical registry: 4: Developer
      Add wine type metadata: 4: Developer
      Add region metadata: 4: Developer
      Add display names and SEO slugs: 4: Developer

    section Deployment
      Save to engine/lenses/wine-discovery/: 5: Developer
      Run test query: 3: Developer
      Execute "Bordeaux wines in Edinburgh": 3: Developer
      Inspect entity store: 2: Developer
      Verify canonical_wine_types populated: 3: Developer
      Verify wine_profile module attached: 3: Developer
      Verify module fields populated: 5: Developer
      Deploy to production: 5: Developer
      Zero engine code changes required: 5: Developer
```

---

### Journey 2: End User Finding Padel Courts

```mermaid
journey
    title End User: Finding Padel Courts

    section User Search
      Visit Edinburgh Finds app: 5: User
      See search input: 5: User
      Enter "padel courts near Leith": 4: User
      Submit search: 4: User

    section Backend Orchestration
      Resolve Edinburgh Finds lens: 5: Engine
      Validate lens contract: 5: Engine
      Extract query features: 5: Engine
      Detect "padel" keyword: 5: Engine
      Detect "Leith" location: 5: Engine

    section Connector Planning
      Plan connector execution: 5: Engine
      Select SportScotland (high priority): 5: Engine
      Select GooglePlaces (high trust): 5: Engine
      Select Serper (discovery): 5: Engine

    section Parallel Ingestion
      Execute connectors in parallel: 5: Engine
      Fetch raw data: 4: Engine
      Store RawIngestion records: 5: Engine

    section Extraction Pipeline
      Run source extraction: 4: Engine
      Extract primitives (name, address, coords): 4: Engine
      Apply lens mapping rules: 5: Engine
      Map "padel" to canonical_activities: 5: Engine
      Map "indoor" to canonical_access: 5: Engine
      Trigger sports_facility module: 5: Engine
      Populate court_count field: 5: Engine
      Populate surface_type field: 5: Engine
      Classify as entity_class "place": 5: Engine

    section Deduplication and Merge
      Group matching entities: 4: Engine
      Run cross-source deduplication: 4: Engine
      Execute deterministic merge: 5: Engine
      Resolve field conflicts: 4: Engine
      Generate URL-safe slug: 5: Engine
      Persist to Entity table: 5: Engine

    section User Experience
      Return results to frontend: 5: User
      View list of padel venues: 5: User
      See venue cards with details: 5: User
      Click venue for full details: 4: User
      View canonical activities: 5: User
      View access information: 5: User
      View opening hours: 5: User
      See sports_facility module data: 5: User
      View court specifications: 5: User
      Click "Get Directions": 5: User
      Click "Contact Venue": 5: User
```

---

## Feature Roadmap

### Phase 1: Foundation (Completed)
- ✅ Multi-source orchestration (6 connectors)
- ✅ Hybrid extraction (deterministic + LLM)
- ✅ Cross-source deduplication
- ✅ Deterministic merge
- ✅ Entity finalization pipeline
- ✅ Lens-driven connector routing

### Phase 2: Lens Maturity (In Progress)
- ⏳ Complete lens mapping engine (partial)
- ⏳ Module triggers and population (partial)
- ⏳ Canonical registry validation
- ⏳ One Perfect Entity validation (OPE requirement)

### Phase 3: Production Hardening (Planned)
- 🔲 Automated freshness-based re-ingestion
- 🔲 Incremental source updates
- 🔲 Comprehensive error recovery
- 🔲 Advanced conflict resolution strategies
- 🔲 Performance profiling and optimization

### Phase 4: Ecosystem Expansion (Future)
- 🔲 Additional vertical lenses (Wine, Restaurants, Events)
- 🔲 Public Lens marketplace
- 🔲 Visual Lens configuration UI
- 🔲 Real-time entity change detection
- 🔲 Collaborative entity curation

---

## Architectural Invariants

These 10 invariants MUST remain true for the system's lifetime. Violations are architectural defects regardless of whether functionality appears to work.

1. **Engine Purity** — Zero domain knowledge in engine code
2. **Lens Ownership of Semantics** — All domain logic in Lens contracts only
3. **Zero Engine Changes for New Verticals** — New verticals = new Lens YAML only
4. **Determinism and Idempotency** — Same inputs = same outputs, always
5. **Canonical Registry Authority** — All canonical values declared explicitly
6. **Fail-Fast Validation** — Invalid Lens contracts fail at bootstrap
7. **Schema-Bound LLM Usage** — LLMs produce validated structured output only
8. **No Permanent Translation Layers** — Universal schema is authoritative end-to-end
9. **Engine Independence** — Engine is useful without any specific vertical
10. **No Reference-Lens Exceptions** — Edinburgh Finds gets no special treatment

**Enforcement:**
- Architectural tests validate invariants on every commit
- Code review checklists reference invariants explicitly
- AI agents (Claude Code) read `system-vision.md` before proposing changes

---

## Technical Specifications

### Supported Entity Classes

- **place** — Geographic entities (venues, facilities, landmarks)
- **person** — Individuals (coaches, instructors, sommeliers)
- **organization** — Businesses, clubs, associations
- **event** — Time-bounded happenings (tournaments, tastings, classes)
- **thing** — Physical objects (equipment, products)

### Canonical Dimensions

All entities share four multi-valued canonical dimension arrays:

- `canonical_activities[]` — Activities offered (padel, tennis, yoga, wine tasting)
- `canonical_roles[]` — Roles provided (instructor, coach, sommelier, guide)
- `canonical_place_types[]` — Facility types (sports_center, restaurant, winery, park)
- `canonical_access[]` — Access models (indoor, outdoor, members_only, drop_in)

**Storage:** PostgreSQL `TEXT[]` arrays with GIN indexes for fast `ANY()` queries.

### Modules System

Modules provide namespaced structured data beyond universal primitives.

**Example: sports_facility Module**

```typescript
{
  sports_facility: {
    court_count: 4,
    surface_type: "artificial_grass",
    has_lighting: true,
    has_changing_rooms: true,
    equipment_rental: true,
    coaching_available: true,
    booking_required: true,
    membership_options: ["annual", "monthly", "drop_in"]
  }
}
```

**Example: hospitality_venue Module**

```typescript
{
  hospitality_venue: {
    cuisine_types: ["italian", "mediterranean"],
    seating_capacity: 80,
    outdoor_seating: true,
    reservations_required: false,
    dietary_options: ["vegetarian", "vegan", "gluten_free"],
    price_range: "mid_range",
    bar_available: true
  }
}
```

**Module Storage:** PostgreSQL JSONB with indexing for efficient queries.

---

## Integration Examples

### Example 1: Query Orchestration

```bash
# CLI invocation
python -m engine.orchestration.cli run "padel courts in Edinburgh" --persist

# Output:
# Query: "padel courts in Edinburgh"
# Candidates found: 12
# Accepted entities: 8 (after deduplication)
# Connectors executed: serper, google_places, sport_scotland
# Entities created: 5
# Entities updated: 3
# Budget spent: $0.037
```

### Example 2: Programmatic Usage

```python
from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode
from engine.orchestration.execution_context import ExecutionContext
from engine.lenses.loader import load_vertical_lens

# Load lens
lens = load_vertical_lens("edinburgh_finds")

# Create execution context
ctx = ExecutionContext(
    lens_id="edinburgh_finds",
    lens_contract=lens,
    lens_hash="abc123..."
)

# Build request
request = IngestRequest(
    query="wine bars in Leith",
    ingestion_mode=IngestionMode.DISCOVER_MANY,
    persist=True,
    budget_usd=0.10,
    lens="edinburgh_finds"
)

# Execute orchestration
report = await orchestrate(request, ctx=ctx)

# Inspect results
print(f"Found {report['accepted_entities']} entities")
print(f"Created {report['entities_created']} new entities")
print(f"Updated {report['entities_updated']} existing entities")
```

### Example 3: Frontend Integration

```typescript
// Next.js App Router API route
// web/app/api/search/route.ts

import { prisma } from '@/lib/prisma';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get('q');
  const activities = searchParams.getAll('activity');

  const entities = await prisma.entity.findMany({
    where: {
      AND: [
        { entity_class: 'place' },
        activities.length > 0
          ? { canonical_activities: { hasSome: activities } }
          : {},
        query
          ? { entity_name: { contains: query, mode: 'insensitive' } }
          : {}
      ]
    },
    take: 20,
    orderBy: { created_at: 'desc' }
  });

  return Response.json({ entities });
}
```

---

## Configuration Reference

### Environment Variables

**Required:**
- `ANTHROPIC_API_KEY` — For LLM-powered extraction (Instructor + Claude)
- `DATABASE_URL` — PostgreSQL connection string (Supabase)

**Optional (Connectors):**
- `SERPER_API_KEY` — For Serper web search connector
- `GOOGLE_PLACES_API_KEY` — For Google Places connector
- `OSM_USER_AGENT` — User agent for OpenStreetMap API (defaults to "EdinburghFinds/1.0")

### File Structure

```
engine/
├── lenses/
│   ├── edinburgh_finds/
│   │   └── lens.yaml              # Complete Lens contract
│   ├── wine-discovery/            # Example: Wine vertical
│   │   └── lens.yaml
│   └── restaurants/               # Example: Restaurant vertical
│       └── lens.yaml
├── config/schemas/
│   ├── entity.yaml                # Universal entity schema
│   ├── extracted_entity.yaml     # Extraction output schema
│   └── raw_ingestion.yaml        # Ingestion artifact schema
├── orchestration/
│   ├── planner.py                # Query planning and connector selection
│   ├── registry.py               # Connector metadata registry
│   ├── adapters.py               # Connector execution adapters
│   └── entity_finalizer.py       # Entity persistence and slug generation
└── extraction/
    ├── extractors/               # Per-connector extractors
    ├── deduplication.py          # Cross-source entity matching
    └── merging.py                # Deterministic merge algorithms
```

---

## Success Metrics

### Data Quality

- **Completeness:** Average entity has 85%+ of available fields populated
- **Accuracy:** <2% entity classification errors (measured via manual sampling)
- **Freshness:** Entities re-verified within 30 days (configurable per vertical)

### System Performance

- **Latency:** P95 query latency <4 seconds (3-4 connectors in parallel)
- **Throughput:** Limited by connector rate limits, not engine bottlenecks
- **Cost:** Average query cost <$0.05 (budget-aware connector selection)

### Developer Experience

- **Time to New Vertical:** <1 day (create Lens YAML, validate, deploy)
- **Test Coverage:** >80% for all engine code
- **Build Time:** <30 seconds for full test suite

---

## Related Documentation

- **[System Vision](../target/system-vision.md)** — Immutable architectural invariants and design philosophy
- **[Architecture](../target/architecture.md)** — Runtime mechanics, pipeline stages, and contracts
- **[Database Schema](./DATABASE.md)** — Entity model, indexes, and query patterns
- **[Development Guide](./DEVELOPMENT.md)** — Setup, testing, and contribution workflow
- **[API Reference](./API.md)** — Connector adapters, extractors, and public interfaces

---

## Glossary

**Engine** — Universal domain-blind execution platform (orchestration, extraction, merge, persistence)

**Lens** — Vertical-specific interpretation contract (vocabulary, routing, mapping, modules)

**Connector** — Data source integration (Serper, Google Places, OSM, SportScotland, etc.)

**Extractor** — Component transforming raw connector payloads into structured primitives

**Canonical Dimensions** — Multi-valued arrays for universal entity classification (activities, roles, place types, access)

**Modules** — Namespaced structured JSONB data for vertical-specific attributes

**Deduplication** — Cross-source entity matching using multiple strategies (external IDs, geo proximity, name similarity)

**Merge** — Deterministic conflict resolution when combining multiple sources into single entity

**Provenance** — Explicit tracking of contributing sources, external IDs, and verification context

**Slug** — URL-safe unique identifier generated from entity name (e.g., "the-padel-club-edinburgh" → `/places/the-padel-club-edinburgh`)

---

**For questions or contributions, see [DEVELOPMENT.md](./DEVELOPMENT.md) or reach out via project repository.**
