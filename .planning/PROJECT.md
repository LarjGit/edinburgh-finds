# Edinburgh Finds: Entity Engine Pipeline Repair

## What This Is

A horizontal entity discovery engine that intelligently orchestrates data from 6+ connectors (Google Places, Serper, OpenStreetMap, Sport Scotland, etc.) to build comprehensive entity records. The system is designed to be vertical-agnostic - it works with generic entity classes (place/person/organization/event/thing) and uses Lens layers for domain-specific interpretation (Padel, Wine, Sports, etc.). Currently, the core data pipeline is broken: orchestration runs, connectors fetch data, but entities never reach the final database table due to incomplete persistence wiring.

## Core Value

When a user queries "powerleague portobello" with the `--persist` flag, the system must deliver complete, deduplicated entity records in the Entity table - not orphaned intermediate records. The end-to-end pipeline (orchestration → ingestion → extraction → deduplication → merging → persistence) must work reliably for any query, any vertical.

## Requirements

### Validated

- ✓ Intelligent orchestration system with phase-based connector execution — existing
- ✓ 6 production connectors (Serper, Google Places, OSM, Sport Scotland, Edinburgh Council, Open Charge Map) — existing
- ✓ Cross-source deduplication via external ID → slug → fuzzy matching — existing
- ✓ Schema-driven code generation from YAML (Python FieldSpecs, Prisma, TypeScript) — existing
- ✓ Vertical-agnostic engine with Lens layer separation — existing
- ✓ Hybrid extraction (deterministic rules + LLM for unstructured data) — existing
- ✓ Trust hierarchy for field-level merging (Admin > Official > Crowdsourced) — existing
- ✓ Next.js 16 frontend with Prisma queries — existing

### Active

- [ ] Complete persistence pipeline: orchestration → Entity table (currently stops at ExtractedEntity)
- [ ] Fix async/event loop handling causing silent persistence failures
- [ ] Integration bridge between orchestration and extraction layers
- [ ] Integration bridge between extraction and merging layers
- [ ] Connector selection improvements (use 4+ connectors for relevant queries, not just 2)
- [ ] Sports keyword detection expanded (add "powerleague", "goals", "nuffield", "david lloyd", "arena", "leisure")
- [ ] Google Places data persistence (currently lost due to async context issues)
- [ ] End-to-end test: CLI query → verified Entity table record
- [ ] Idempotent persistence (re-running same query updates, doesn't duplicate)
- [ ] Edinburgh location trigger (activate edinburgh_council connector for Edinburgh queries)
- [ ] EV charging trigger (activate open_charge_map for EV/charging queries)
- [ ] Free connector prioritization (prefer OSM, Sport Scotland over paid sources when appropriate)

### Out of Scope

- LLM extraction improvements (use existing prompts as-is) — extraction quality is acceptable
- New connectors beyond the 6 existing ones — sufficient coverage for current use case
- Web UI for persistence — CLI-only feature for now
- Real-time updates — batch processing sufficient
- Advanced deduplication algorithms — existing slug-based logic works
- Manual merge conflict resolution UI — automated trust hierarchy sufficient for now
- Confidence scoring — defer to later phase
- Incremental updates (delta detection) — full re-ingestion acceptable
- Entity relationship extraction — single entities only for now

## Context

**System Architecture:**
The engine follows a pure separation: the core engine knows nothing about domains (Padel, Wine, Tennis), working only with generic entity_class and flexible dimension arrays. Vertical-specific logic lives exclusively in YAML Lens configs. This horizontal purity is mechanically enforced by import boundary tests.

**Data Flow (Intended):**
Query → Intelligent Connector Selection (Registry-based with cost/trust/phase metadata) → Phase-Ordered Execution (Discovery → Enrichment) → Cross-Source Deduplication (ExecutionContext) → Extraction (Hybrid rules + LLM) → Merging (Trust Hierarchy) → Entity Table → Frontend Display

**Data Flow (Current - Broken):**
Query → Intelligent Connector Selection → Phase-Ordered Execution → Cross-Source Deduplication → Persistence creates RawIngestion + ExtractedEntity → **STOPS HERE** ❌ (no extraction invocation, no merging, no Entity table records)

**Critical Disconnects Identified:**
1. Persistence layer (`engine/orchestration/persistence.py`) creates intermediate records but never invokes extraction pipeline
2. Extraction layer (`engine/extraction/`) exists but is decoupled from orchestration - no integration bridge
3. Merging layer (`engine/extraction/merging.py`) implements trust hierarchy but never called by persistence
4. Async handling uses event loop detection that silently fails, returning `persisted_count: 0` with no exception

**Known Working Components:**
- Individual connectors fetch and save raw data correctly
- Deduplication logic in ExecutionContext works (tested with 11 test cases)
- Extraction works when invoked manually via `python -m engine.extraction.cli`
- Merging logic exists and is tested
- Schema generation system fully functional
- Frontend queries work on manually-created Entity records

**Brownfield Context:**
Extensive infrastructure exists: 6 connectors implemented, orchestration layer with intelligent planner, registry-based connector specs, phase barriers, budget gating, extraction prompts, trust hierarchy rules, comprehensive test suite (~90% unit coverage). The issue is not missing components but incomplete wiring between layers.

## Constraints

- **Technical:** Python 3.x backend, Next.js 16 frontend, PostgreSQL via Supabase, Prisma ORM for both Python and TypeScript
- **Architecture:** Engine must remain vertical-agnostic (no domain-specific logic hardcoded)
- **Schema:** Single source of truth in YAML, auto-generate Python/Prisma/TypeScript
- **Testing:** TDD workflow mandatory, >80% coverage required
- **Cost:** Minimize LLM calls (use structured data from connectors when possible), respect budget gating
- **Performance:** Extraction < 2s per entity, merging < 500ms per entity, total persistence < 5s for 10 entities
- **Data Lineage:** Raw payloads saved to disk, RawIngestion links to file_path, ExtractedEntity links to RawIngestion, Entity tracks source_info

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fix existing pipeline before adding features | Broken end-to-end flow blocks all downstream work | — Pending |
| Reuse existing extraction/merging layers | Well-tested, working components - just need integration | — Pending |
| Make persistence fully async | Remove event loop detection anti-pattern causing silent failures | — Pending |
| Expand sports keywords incrementally | Start with major chains (Powerleague, Goals, Nuffield, David Lloyd), avoid ML complexity | — Pending |
| Prioritize free connectors | OSM and Sport Scotland provide good data at $0 cost - use them more | — Pending |
| CLI-only persistence for v1 | Avoid web UI complexity, focus on core pipeline reliability | — Pending |

---
*Last updated: 2026-01-27 after initialization*
