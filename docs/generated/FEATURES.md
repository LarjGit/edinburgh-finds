# Features

**Generated:** 2026-02-06
**Status:** Auto-generated documentation

---

## Feature Overview

Edinburgh Finds is an AI-powered entity discovery platform. Below are the major features organized by layer.

---

## 1. Multi-Source Data Ingestion

**What it does:** Fetches raw data about real-world entities from 6 independent data sources simultaneously.

**Technical implementation:**
- 6 pluggable connectors implementing `BaseConnector` interface
- Async execution via `aiohttp`
- Content-hash deduplication prevents re-ingesting identical data
- Rate limiting and retry logic per connector
- Raw payloads persisted to disk (`engine/data/raw/`) and tracked in `RawIngestion` table

**Data Sources:**

| Connector | Type | Trust Level | Cost | Data Provided |
|-----------|------|-------------|------|---------------|
| Serper | Web search | 0.75 | $0.01/call | Discovery results, snippets |
| Google Places | Places API | 0.95 | $0.017/call | Authoritative venue data |
| OpenStreetMap | Geo data | 0.70 | Free | Geographic and facility data |
| Sport Scotland | Gov WFS | 0.90 | Free | Official sports facility data |
| Edinburgh Council | Gov API | 0.90 | Free | Local facility data |
| OpenChargeMap | Specialized | 0.80 | Free | EV charging station data |

**Key files:**
- `engine/ingestion/base.py` — BaseConnector interface
- `engine/ingestion/connectors/` — 6 connector implementations
- `engine/ingestion/deduplication.py` — Content hash dedup
- `engine/ingestion/rate_limiting.py` — Rate limiter
- `engine/ingestion/storage.py` — Raw data persistence

---

## 2. Intelligent Query Orchestration

**What it does:** Analyzes natural language queries and intelligently selects which connectors to call, in what order, with what budget.

**Technical implementation:**
- Query feature extraction using lens vocabulary
- Phase-ordered execution: DISCOVERY -> STRUCTURED -> ENRICHMENT
- Connector selection driven by lens routing rules
- Budget management and early stopping
- Full execution tracked in `OrchestrationRun` table

**Key files:**
- `engine/orchestration/orchestrator.py` — Main orchestration loop
- `engine/orchestration/planner.py` — Query analysis and connector selection
- `engine/orchestration/query_features.py` — Feature extraction from queries
- `engine/orchestration/registry.py` — Connector metadata registry
- `engine/orchestration/adapters.py` — Bridge between connectors and orchestrator
- `engine/orchestration/cli.py` — CLI entry point

**Example:**
```bash
python -m engine.orchestration.cli run --lens edinburgh_finds "padel courts in Edinburgh"
```

---

## 3. Hybrid Entity Extraction

**What it does:** Transforms raw connector payloads into structured entity records using both deterministic rules and AI (LLM).

**Technical implementation:**
- Per-source extractors handle source-specific data formats
- Phase 1 (extractors): Emit ONLY schema primitives + raw observations
- Phase 2 (lens application): Populate canonical dimensions + modules
- LLM extraction uses Instructor + Claude for unstructured data
- Schema-validated output — no free-form LLM responses allowed

**Key files:**
- `engine/extraction/base.py` — BaseExtractor interface
- `engine/extraction/extractors/` — 6 source-specific extractors
- `engine/extraction/llm_client.py` — LLM integration
- `engine/extraction/models/entity_extraction.py` — Pydantic models
- `engine/lenses/mapping_engine.py` — Lens rule execution engine

---

## 4. Lens System (Vertical-Agnostic Configuration)

**What it does:** Provides all domain knowledge through YAML configuration files, keeping the engine completely vertical-agnostic.

**Technical implementation:**
- Each lens is a YAML file defining vocabulary, routing rules, mapping rules, canonical values, and module definitions
- Lens loaded once at bootstrap, validated, hashed, and injected into ExecutionContext
- Mapping rules convert raw observations to canonical dimension values
- Module triggers determine which data modules to attach based on entity properties

**Current lenses:**
- `engine/lenses/edinburgh_finds/lens.yaml` — Sports discovery in Edinburgh
- `engine/lenses/wine/lens.yaml` — Wine discovery (skeleton)

**Key files:**
- `engine/lenses/loader.py` — Lens loading and validation
- `engine/lenses/validator.py` — 7 validation gates
- `engine/lenses/mapping_engine.py` — Rule execution engine
- `engine/lenses/extractors/` — Generic extractors (numeric_parser, regex_capture, normalizers)

---

## 5. Cross-Source Deduplication

**What it does:** Groups extracted entities from different sources that represent the same real-world entity.

**Technical implementation:**
- Multi-tier matching: external IDs -> geo proximity -> normalized name similarity
- Uses FuzzyWuzzy for string similarity and geographic distance calculations
- Groups entities into DedupGroups without resolving field conflicts

**Key files:**
- `engine/extraction/deduplication.py` — Deduplication logic
- `engine/ingestion/deduplication.py` — Ingestion-level dedup

---

## 6. Deterministic Multi-Source Merge

**What it does:** Merges multiple extracted records for the same entity into a single canonical record using metadata-driven rules.

**Technical implementation:**
- Field-group strategies: identity fields, geo fields, contact fields, dimensions, modules
- Trust-based conflict resolution (no connector names in merge logic)
- Deterministic tie-breaking cascade: trust -> quality -> confidence -> completeness -> priority -> lexicographic ID
- Merge conflicts recorded in `MergeConflict` table for auditing

**Key files:**
- `engine/extraction/merging.py` — Merge engine
- `engine/orchestration/entity_finalizer.py` — Final entity assembly

---

## 7. Entity Finalization and Persistence

**What it does:** Generates stable slugs, assembles final entity records, and upserts them idempotently to the database.

**Technical implementation:**
- URL-safe slug generation (e.g., "The Padel Club" -> "padel-club")
- Idempotent upsert — re-running same query updates existing entities
- Provenance and external ID preservation

**Key files:**
- `engine/orchestration/entity_finalizer.py` — Slug generation and finalization
- `engine/orchestration/persistence.py` — Database persistence

---

## 8. Faceted Entity Browsing (Frontend)

**What it does:** Displays entities with faceted filtering using native PostgreSQL array queries.

**Technical implementation:**
- Prisma `hasSome` / `has` / `hasEvery` array filters for dimension queries
- OR within facet, AND across facets (standard faceted search semantics)
- Server-side rendering via Next.js App Router
- Responsive design with Tailwind CSS

**Key files:**
- `web/app/page.tsx` — Main entity listing page
- `web/lib/entity-queries.ts` — Faceted query builder
- `web/lib/entity-helpers.ts` — Data parsing utilities

---

## 9. Schema Auto-Generation

**What it does:** Generates Python models, Prisma schemas, and TypeScript interfaces from a single YAML source of truth.

**Technical implementation:**
- YAML schemas define all entity fields, types, validation rules
- Generator produces Python FieldSpecs, Prisma schema, TypeScript interfaces
- Eliminates schema drift across the stack

**Key files:**
- `engine/config/schemas/entity.yaml` — Single source of truth
- `engine/schema/generate.py` — Generation orchestrator
- `engine/schema/generators/` — Per-target generators (pydantic, prisma, typescript)

---

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Multi-source ingestion | Complete | All 6 connectors working |
| Query orchestration | Complete | Phase-ordered execution |
| Source extraction | Complete | All extractors implemented |
| Lens system | Partial | Edinburgh lens working, mapping engine implemented |
| Deduplication | Complete | Multi-tier matching |
| Deterministic merge | Complete | All field-group strategies |
| Entity finalization | Complete | Slug generation + upsert |
| Frontend browsing | Basic | Entity listing with dimensions |
| Schema auto-generation | Complete | YAML -> Python/Prisma/TS |

---

## Related Documentation

- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Backend Details:** [BACKEND.md](BACKEND.md)
- **Frontend Details:** [FRONTEND.md](FRONTEND.md)
- **API Reference:** [API.md](API.md)
