# Architecture

**Analysis Date:** 2026-01-27

## Pattern Overview

**Overall:** Vertical-agnostic ETL platform with engine-lens separation and intelligent orchestration

**Key Characteristics:**
- **Universal Entity Framework:** Single Python engine works with generic `entity_class` (place/person/organization/event/thing), not vertical-specific types
- **Lens Layer Separation:** Vertical-specific logic (Padel, Wine, etc.) lives in YAML configurations only - engine has zero vertical awareness
- **Intelligent Orchestration:** Runtime control plane with phase-ordered connector execution (discovery → enrichment), budget gating, and cross-source deduplication
- **Schema-Driven Code Generation:** Single YAML source of truth generates Python FieldSpecs, Prisma schemas, and TypeScript interfaces - no manual schema editing
- **Multi-Dimensional Faceting:** Postgres TEXT[] arrays with GIN indexes for fast faceted filtering across `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`

## Layers

**Ingestion Layer:**
- Purpose: Fetch raw data from 6 external sources (Serper, Google Places, OSM, Sport Scotland, Edinburgh Council, Open Charge Map)
- Location: `engine/ingestion/`
- Contains: Connector implementations, base interface, deduplication logic
- Depends on: External APIs, filesystem storage
- Used by: Orchestration layer

**Extraction Layer:**
- Purpose: Transform raw payloads into structured entity fields using hybrid approach (deterministic rules + LLM)
- Location: `engine/extraction/`
- Contains: Per-source extractors, LLM client with caching, deduplication by ID/slug/fuzzy, field merging with trust hierarchy
- Depends on: Ingestion data, Anthropic Claude API, Prisma ORM
- Used by: Orchestration persistence, direct extraction CLI

**Orchestration Layer:**
- Purpose: Intelligent runtime control plane - query analysis, connector selection, phase ordering, budget management, deduplication
- Location: `engine/orchestration/`
- Contains: Registry (connector metadata), Planner (selection logic), Orchestrator (execution loop), ExecutionContext (shared state), Adapters (async bridges), Persistence (database save)
- Depends on: Ingestion layer, Extraction integration, Registry specs
- Used by: CLI, web API (future)

**Lens Layer:**
- Purpose: Vertical-specific interpretation of opaque engine data
- Location: `engine/lenses/` and `engine/config/schemas/`
- Contains: YAML lens configs with canonical value mappings, module triggers, filtering rules
- Depends on: Entity schema definitions
- Used by: Frontend for display logic, extraction for module determination

**Schema Generation Layer:**
- Purpose: Single source of truth - auto-generates derived schemas from YAML
- Location: `engine/schema/`
- Contains: YAML parser, generators for Python/Prisma/TypeScript, validation
- Depends on: YAML schema files
- Used by: Build pipeline, developers regenerating schemas

**Frontend Layer:**
- Purpose: Next.js 16 discovery UI with Prisma querying
- Location: `web/`
- Contains: App Router pages, Prisma client, entity helpers, styling with Tailwind
- Depends on: Prisma generated client, PostgreSQL database
- Used by: End users discovering entities

## Data Flow

**Complete Orchestration Flow:**

1. **Query Ingestion** → CLI receives "padel courts Edinburgh"
   - Located: `engine/orchestration/cli.py`
   - Parses IngestRequest with query, mode (RESOLVE_ONE or DISCOVER_MANY), optional budget

2. **Query Feature Extraction** → Analyze query characteristics
   - Located: `engine/orchestration/query_features.py`
   - Detects: category search vs specific search, domain keywords
   - Determines initial connector hints

3. **Intelligent Connector Selection** → Plan which connectors to run
   - Located: `engine/orchestration/planner.py:select_connectors()`
   - Logic:
     - RESOLVE_ONE mode: Prioritize high-trust enrichment (google_places)
     - DISCOVER_MANY mode: Start with discovery (serper, openstreetmap), then enrichment
     - Sports queries: Add sport_scotland connector
     - Budget constraints: Filter out paid connectors if budget tight
   - Returns: Ordered list of connector names (discovery phase first)

4. **Phase-Ordered Execution** → Run connectors with phase barriers
   - Located: `engine/orchestration/orchestrator.py`
   - Phases: DISCOVERY (free, broad) → ENRICHMENT (paid/specialized)
   - Per-connector:
     - Adapter (`engine/orchestration/adapters.py`) bridges async connector to sync orchestrator
     - Connector fetches raw data, saves to `engine/data/raw/<source>/`
     - Updates shared ExecutionContext with candidates
     - Tracks: latency, cost, candidates found
   - Stops when: Budget exhausted or high confidence reached

5. **Cross-Source Deduplication** → Merge duplicate candidates
   - Located: `engine/orchestration/execution_context.py`
   - Strategy: External ID → Slug match → Fuzzy name match (threshold: 85%)
   - Merges: Latest values from trusted sources win
   - Output: Set of accepted_entities with merged fields

6. **Extraction (On-Demand)** → Parse raw data into structured fields
   - Located: `engine/orchestration/extraction_integration.py` and `engine/extraction/run.py`
   - For each accepted entity:
     - Determine if LLM extraction needed (heuristic: check if key fields present)
     - Route to per-source extractor (GooglePlacesExtractor, etc.)
     - Extractor: validates, splits schema fields from discovered_attributes, classifies entity_class
     - Outputs: Validated candidate with all Entity fields populated

7. **Persistence to Database** → Save to PostgreSQL
   - Located: `engine/orchestration/persistence.py`
   - Creates: RawIngestion record (lineage), ExtractedEntity record (structured data)
   - Links: raw_ingestion → extracted_entity → [eventual Entity merge]

8. **Frontend Display** → Query and render
   - Located: `web/app/page.tsx`, `web/lib/entity-queries.ts`
   - Prisma query: findMany() with dimension filters (canonical_activities = ["padel"])
   - Renders: Entity cards with location, contact, modules data

**State Management:**
- Shared ExecutionContext passed through entire orchestration
- Mutable collections: candidates, accepted_entities, accepted_entity_keys, evidence, seeds, metrics, errors
- Never recreated during execution - single container for consistency

## Key Abstractions

**Entity:**
- Purpose: Universal data model for any vertical (place, person, org, event, thing)
- Examples: `web/prisma/schema.prisma` Entity model, `engine/schema/entity.py` FieldSpec
- Pattern: Fixed schema fields (name, address, contact) + flexible arrays (canonical_activities) + JSONB modules for vertical specifics

**ExecutionContext:**
- Purpose: Shared mutable state container for orchestration
- Located: `engine/orchestration/execution_context.py`
- Pattern: Initialized empty, populated during phase execution, supports deduplication via accepted_entity_keys set

**ConnectorSpec:**
- Purpose: Immutable metadata for connectors (cost, trust, phase, timeout)
- Located: `engine/orchestration/registry.py`
- Pattern: Dataclass used by Planner to make intelligent selection decisions
- Registry: Central CONNECTOR_REGISTRY dict with all 6 connectors defined

**BaseConnector & BaseExtractor:**
- Purpose: Abstract base classes defining interface contracts
- Located: `engine/ingestion/base.py`, `engine/extraction/base.py`
- Pattern: All concrete implementations inherit and override abstract methods
- Ensures consistency: fetch() → save() → extract() → validate() → split_attributes()

**Lens:**
- Purpose: Vertical-specific interpretation layer
- Located: `engine/lenses/` and `engine/config/schemas/`
- Pattern: YAML config maps opaque engine values to UI-friendly labels
- Example: engine value "padel_court" → lens maps to display name "Padel Court"

**QueryFeatures:**
- Purpose: Extracted query characteristics for intelligent routing
- Located: `engine/orchestration/query_features.py`
- Pattern: Dataclass with boolean flags (looks_like_category_search, needs_location) used by Planner

## Entry Points

**Backend Data Pipeline:**
- Location: `engine/orchestration/cli.py`
- Triggers: `python -m engine.orchestration.cli run "query string"`
- Responsibilities: Parse IngestRequest, call orchestrate(), format and print report
- Environment: Requires ANTHROPIC_API_KEY, SERPER_API_KEY, GOOGLE_PLACES_API_KEY, DATABASE_URL

**Direct Extraction (Development):**
- Location: `engine/extraction/cli.py`
- Triggers: `python -m engine.extraction.cli single <raw_ingestion_id>`
- Responsibilities: Extract single RawIngestion record, validate, save ExtractedEntity
- Use case: Testing extraction without full orchestration

**Direct Ingestion (Development):**
- Location: `engine/ingestion/cli.py`
- Triggers: `python -m engine.ingestion.cli run --query "search term"`
- Responsibilities: Fetch from single connector, save raw data
- Use case: Testing individual connectors

**Frontend Discovery:**
- Location: `web/app/page.tsx`
- Triggers: Browser request to http://localhost:3000
- Responsibilities: Query database via Prisma, render entity cards
- Environment: Requires DATABASE_URL for Prisma client

**Schema Generation:**
- Location: `engine/schema/generate.py`
- Triggers: `python -m engine.schema.generate --all` or `--validate`
- Responsibilities: Parse YAML schemas, generate Python/Prisma/TypeScript files
- Use case: After modifying `engine/config/schemas/*.yaml`

## Error Handling

**Strategy:** Distributed error collection with graceful degradation

**Patterns:**

**Connector Failures:**
- Location: `engine/orchestration/adapters.py:execute_connector_safe()`
- Pattern: Try-catch wraps connector execution, error appended to context.errors
- Behavior: One connector failure does not stop orchestration - continues with other connectors
- Logging: Structured logging with connector name, error type, timestamp

**Extraction Failures:**
- Location: `engine/extraction/run.py` and per-source extractors
- Pattern: Failed extractions saved to FailedExtraction model for later retry
- Behavior: Quarantine records with extraction_hash to prevent duplicate failures
- LLM errors: Fallback to deterministic extraction if LLM fails

**Validation Failures:**
- Location: Per-source extractor validate() method
- Pattern: Returns normalized/coerced values on type mismatch
- Examples: Phone number validator coerces to E.164, URL validator ensures http(s)://
- Strict: Extraction still fails if required fields missing after validation

**Database Persistence Failures:**
- Location: `engine/orchestration/persistence.py:persist_entities()`
- Pattern: Individual entity persistence wrapped in try-catch
- Behavior: One entity failure doesn't block others - error logged with candidate details
- Logging: Full traceback captured for debugging

**Budget Overrun:**
- Location: `engine/orchestration/planner.py:_apply_budget_gating()`
- Pattern: Pre-flight check calculates total cost, filters expensive connectors
- Behavior: Early exit if budget exhausted before execution
- Reporting: Cost report in orchestration report shows per-connector spend

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module with custom configuration
- Pattern: Each module gets named logger via `logging.getLogger(__name__)`
- Locations: `engine/ingestion/logging_config.py`, `engine/extraction/logging_config.py`, `engine/orchestration/` (implicit)
- Levels: DEBUG for detailed trace, INFO for milestones, ERROR for failures
- Structured: Messages include connector name, operation (fetch/extract/dedupe), timing

**Validation:**
- Framework: Pydantic for extraction-level schemas
- Location: `engine/extraction/` per-source extractors
- Patterns:
  - Phone: E.164 UK format (`+441315397071`)
  - URL: Must start with http(s)://
  - Postcode: UK postcode format with spacing
  - Custom validators: Defined in YAML as validator directives
- Behavior: Validates after extraction, before storing

**Authentication:**
- Strategy: Environment variables for API keys
- Keys: ANTHROPIC_API_KEY, SERPER_API_KEY, GOOGLE_PLACES_API_KEY
- Pattern: Loaded via `dotenv` at module import time
- Scope: Engine-wide, not per-request (stateless design)

**Deduplication:**
- First: External ID matching (absolute, connector-specific)
- Second: Slug matching (deterministic, name-derived)
- Third: Fuzzy name matching (threshold 85, handles typos)
- Trust hierarchy: Admin > Official > Crowdsourced (determines field winner on conflict)
- Execution: Cross-source deduplication in orchestration layer BEFORE extraction

**Caching:**
- LLM Cache: Located `engine/extraction/llm_cache.py`
- Strategy: Cache by request hash to avoid duplicate LLM calls
- Scope: Per-process in-memory (not persistent)
- Use case: Multiple entities with identical extraction needs

---

*Architecture analysis: 2026-01-27*
