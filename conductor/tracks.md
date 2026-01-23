# Project Tracks

This file tracks all major tracks for the project. Each track has its own detailed plan in its respective folder.

---

## [x] Track: Engine Purity Remediation
*Link: [./conductor/tracks/engine_purity_remediation_20260122/](./conductor/tracks/engine_purity_remediation_20260122/)*
**Status:** Complete
**Completed:** 2026-01-22
**Priority:** Critical
**Description:** Address critical blocking violations and architectural debts identified in the `ENGINE_PURITY_REVIEW.md` (2026-01-22) to ensure a truly vertical-agnostic engine. Completed all 4 phases: (1) Fixed seed & ingest scripts to use Entity model with entity_class, (2) Removed VENUE/entity_type from extractors, (3) Decoupled prompts & category mapper from vertical-specific knowledge, (4) Verified purity and tested end-to-end ingestion. Engine is now 100% vertical-agnostic.

---

## [x] Track: Frontend Foundation
*Link: [./conductor/archive/frontend_foundation_20260113/](./conductor/archive/frontend_foundation_20260113/)*

---

## [x] Track: Core Architecture Refactor
*Link: [./conductor/archive/core_refactor_20260112/](./conductor/archive/core_refactor_20260112/)*

---

## [x] Track: Data Ingestion Pipeline
*Link: [./conductor/archive/data_ingestion_pipeline_20260114/](./conductor/archive/data_ingestion_pipeline_20260114/)*
**Completed:** 2026-01-14
**Description:** Built modular ingestion system to gather raw data from 6 sources (Serper, Google Places, OSM, OpenChargeMap, SportScotland, Edinburgh Council) with hybrid storage (filesystem + metadata table). Includes quality & observability features: structured logging, rate limiting, retry logic, health checks, and reporting.

---

## [x] Track: Create project architecture documentation ARCHITECTURE.md
*Link: [./conductor/archive/architecture_docs_20260114/](./conductor/archive/architecture_docs_20260114/)*
**Completed:** 2026-01-14
**Description:** Created comprehensive architecture documentation including System Overview, Entity Framework (Schema), Data Ingestion Pipeline, and Deployment strategy. Produced Mermaid.js diagrams for core systems and consolidated all information into `ARCHITECTURE.md`.

---

## [x] Track: Architecture Alignment & Ecosystem Graph
*Link: [./conductor/tracks/arch_alignment_20260114/](./conductor/tracks/arch_alignment_20260114/)*
**Completed:** 2026-01-14
**Description:** Aligned codebase with ARCHITECTURE.md vision by implementing the "Flexible Attribute Bucket" strategy across the full stack. Extended schema with ListingRelationship model for ecosystem graph. Built transform pipeline to parse raw connector data into validated attributes. Implemented frontend display of structured attributes and discovered attributes. Completed all 3 phases: Schema Extension (ListingRelationship model + migrations), Engine Alignment (transform module + 27 tests), and Frontend Alignment (attribute display UI). Full data flow operational: Connector → Transform → Ingest → Display.

---

## [x] Track: Refactor EntityType to Enum & Update Architecture
*Link: [./conductor/tracks/entity_type_refactor_20260114/](./conductor/tracks/entity_type_refactor_20260114/)*
**Completed:** 2026-01-15
**Description:** Refactored EntityType from separate model to application-layer Enum across full stack. Removed EntityType model and entityTypeId foreign key, replacing with entityType String field validated as Enum in Python (`engine/schema/types.py`). Updated ARCHITECTURE.md, created validation tests, refactored transform/ingest pipelines, updated seed data, and created migration (20260115003157_entitytype_refactor). Documented as temporary SQLite limitation with clear migration path to native Prisma Enum when moving to Supabase (PostgreSQL). Completed all 3 phases: Documentation & Preparation, Schema & Engine Refactoring, and Database Reset & Verification. All 27 tests passing.

---

## [x] Track: Data Extraction Engine
*Link: [./conductor/tracks/data_extraction_engine_20260115/](./conductor/tracks/data_extraction_engine_20260115/)*
**Completed:** 2026-01-17 (All 10 phases complete, production-ready)
**Description:** Built production-ready modular extraction engine that transforms raw ingested data into structured, validated listings. Implemented hybrid extraction strategy (deterministic for Google Places, Sport Scotland, Edinburgh Council, OpenChargeMap; LLM-based for Serper, OSM). Completed all 10 phases with 150+ tasks. **Phase 1**: Foundation & architecture (base extractors, schema utilities, config, Prisma models). **Phase 2**: Deterministic extractors for 4 sources with phone/postcode formatting. **Phase 3**: LLM extractors with Instructor integration, retry logic, null semantics. **Phase 4**: Special field processing (opening hours, categories, multi-stage summary synthesis with rich text). **Phase 5**: Deduplication & merging (external ID, slug, fuzzy matching; field-level trust hierarchy; conflict detection). **Phase 6**: Error handling & observability (quarantine pattern, health dashboard, structured logging, LLM cost tracking). **Phase 7**: Complete CLI (single, per-source, batch, retry modes; dry-run, limit, force-retry flags). **Phase 8**: Integration & E2E testing (6 scenarios, snapshot validation). **Phase 9**: Comprehensive documentation (7 guides: overview, adding extractors, CLI reference, troubleshooting, trust config, categories, LLM tuning; ARCHITECTURE.md update). **Phase 10**: Production optimization (13 database indexes, LLM caching system with 30-50% cost reduction, production deployment checklist, monitoring alert thresholds). Complete ETL pipeline operational: Ingest → Extract → Merge → Display. 125+ tests passing, >80% coverage. Production-ready with health monitoring, cost tracking, and full observability.

---

## [x] Track: YAML Schema - Single Source of Truth
*Link: [./conductor/tracks/yaml_schema_source_of_truth_20260116/](./conductor/tracks/yaml_schema_source_of_truth_20260116/)*
**Completed:** 2026-01-17 (All 8 phases including optional TypeScript generator)
**Description:** Eliminated schema drift by implementing YAML-based single source of truth for all schema definitions. YAML schemas (`engine/config/schemas/*.yaml`) now auto-generate Python FieldSpecs, Prisma schemas, and TypeScript interfaces. Completed all 8 phases including optional Phase 8 (TypeScript generator with Zod validation). Key deliverables: (1) YAML schema format with parser (19 tests), (2) Python FieldSpec generator (32 tests), (3) Prisma schema generator (35 tests), (4) Migrated listing.yaml (27 fields) and venue.yaml (85 fields), (5) CLI tool with validation/generation commands (--typescript, --zod flags), (6) Comprehensive documentation (800+ lines), (7) README.md Schema Management section, (8) TypeScript generator with 27 tests. Winery entity created as proof-of-concept for horizontal scaling (39 fields). All 125 schema tests passing (98 original + 27 TypeScript). Generated files marked with "DO NOT EDIT" warnings. Full-stack type safety: YAML → Python → Prisma → TypeScript. Track enables adding new verticals (Restaurant, Gym) by creating single YAML file - no code changes required.

---

## [x] Track: Category-Entity Decoupling
*Link: [./conductor/tracks/category_entity_decoupling_20260117/](./conductor/tracks/category_entity_decoupling_20260117/)*
**Completed:** 2026-01-17
**Description:** Refactoring category taxonomy to decouple "Activity" categories (Padel, Tennis) from the "Venue" entity type. Flattening `canonical_categories.yaml` and updating extraction logic to treat categories and entity types as orthogonal concepts, allowing activities to be associated with Coaches, Clubs, and Retailers.

---

## [x] Track: Universal Entity Model Refactor
*Link: [./conductor/tracks/universal_entity_model_refactor_20260117/](./conductor/tracks/universal_entity_model_refactor_20260117/)*
**Completed:** 2026-01-17
**Description:** Refactored extraction models to resolve "naming debt" where `VenueExtraction` is used for all entity types. Renamed to `EntityExtraction`, updated all consumers (Serper, OSM) and tests. Aligned prompts and documentation to use universal entity concepts.

---

## [x] Track: Pydantic Extraction Generator
*Link: [./conductor/archive/pydantic_extraction_generator_20260117/](./conductor/archive/pydantic_extraction_generator_20260117/)*
**Completed:** 2026-01-18
**Description:** Implemented generator that reads `listing.yaml` and auto-generates `entity_extraction.py`, keeping the extraction model (including null semantics and validators) in sync with the Golden Source.

---

## [x] Track: Prisma Schema Generation
*Link: [./conductor/tracks/prisma_schema_generation_20260118/](./conductor/tracks/prisma_schema_generation_20260118/)*
**Completed:** 2026-01-18
**Description:** Automated generation of `schema.prisma` files for both Engine and Web from YAML schemas. Extended schema generation system with PrismaGenerator that converts YAML definitions to Prisma models while preserving infrastructure models (RawIngestion, MergeConflict, etc.). Completed all 4 phases: Analysis & Templating, Generator Implementation, Integration, and Verification. All 144 schema tests passing.

---

## [x] Track: Pytest Collection Conflicts
*Link: [./conductor/tracks/pytest_collection_conflicts_20260118/](./conductor/tracks/pytest_collection_conflicts_20260118/)*
**Completed:** 2026-01-18
**Description:** Resolved pytest collection import mismatches by renaming manual test scripts from `test_*.py` to `run_*.py` and disambiguating logging test files. Pytest collection now passes with 1032 tests (was 834 with 15 errors).

---

## [x] Track: Engine Purity Finalization
*Link: [./conductor/tracks/engine_purity_finalization_20260121/](./conductor/tracks/engine_purity_finalization_20260121/)*
**Completed:** 2026-01-21
**Description:** Finalized engine purity and schema naming cleanup for a vertical-agnostic Entity Engine. Renamed Listing → Entity, removed EntityType and Category, implemented persisted Lens membership (LensEntity table), created lens membership API, updated all documentation. Completed all 4 phases: Schema & DB Migration (Phase 1), Code Refactors (Phase 2), Lens + Category Cleanup (Phase 3), Tests + Validation + Docs (Phase 4). All 27 engine tests passing, engine purity checks passing, all acceptance criteria met.

## [~] Track: Complete Engine-Lens Architecture
*Link: [./conductor/tracks/complete_engine_lens_architecture_20260119/](./conductor/tracks/complete_engine_lens_architecture_20260119/)*
**Status:** Active
**Priority:** Critical
**Description:** Finalize the Engine-Lens separation by migrating to Supabase (Postgres) and removing all remaining legacy/vertical-specific code. Addresses blockers: SQLite limitations, Engine Purity violations, and Classification logic errors.

## [ ] Track: Engine-Lens Architecture Refactor
*Link: [./conductor/tracks/engine_lens_architecture_20260118/](./conductor/tracks/engine_lens_architecture_20260118/)*
**Status:** Ready for Implementation
**Priority:** Critical
**Description:** Refactor Edinburgh Finds to separate a universal, vertical-agnostic **Entity Engine** from vertical-specific **Lens Layer**. The engine models entities using `entity_class`, multi-valued dimensions (roles, activities, place_type, access) stored as Postgres text[] arrays with GIN indexes, and universal attribute modules. All vertical-specific modules, user-facing groupings, labels, and navigation are derived in the lens layer via YAML configuration. Key deliverables: (1) Engine purity (100% vertical-agnostic, no domain modules), (2) Postgres text[] arrays for dimensions with GIN indexes, (3) JSONB for modules, (4) Lens YAML config with facets, canonical values, mapping rules, derived groupings, domain modules, and explicit module triggers, (5) Role facet (internal-only) with universal function-style keys, (6) Lens-aware extraction pipeline with facet routing and deduplication, (7) Query layer with Prisma array filters (has, hasSome, hasEvery), (8) Second vertical validation (Wine Discovery lens with zero engine changes). Enables horizontal scaling to new verticals (wine, restaurants, gyms) by adding lens.yaml configuration only - no engine code changes required.

---

## [ ] Track: Ecosystem Graph - Relationship Extraction
**Status:** Planned (Blocked by Data Extraction Engine)
**Dependencies:** Data Extraction Engine must complete first
**Description:** Extract and validate relationships between entities (coaches→venues, clubs→venues, events→venues) to build the ecosystem graph. Populate `ListingRelationship` table with relationship types (teaches_at, plays_at, based_at, etc.) using LLM analysis of discovered_attributes and cross-entity references. Enable hyper-specific SEO pages ("Coaches at [Venue]", "Clubs in [Area]"). Implement relationship confidence scoring and business claim verification workflow. Future track - will be planned after extraction engine completion.

---

## [x] Track: Conductor Documentation Synchronization
*Link: [./conductor/tracks/conductor_sync_20260123/](./conductor/tracks/conductor_sync_20260123/)*
**Completed:** 2026-01-23
**Description:** Thoroughly reviewed and updated all Conductor documentation to match the current codebase. Synchronized `tech-stack.md` with `package.json` and `requirements.txt`. Aligned `product.md` with the latest Universal Entity Framework and Engine-Lens architecture. Updated `workflow.md` with accurate development commands and testing protocols. Verified `product-guidelines.md` aligns with design goals.

---

- [ ] **Track: feature - Intelligent Ingestion Orchestration**
*Link: [./conductor/tracks/intelligent_ingestion_orchestration_20260123/](./conductor/tracks/intelligent_ingestion_orchestration_20260123/)*
