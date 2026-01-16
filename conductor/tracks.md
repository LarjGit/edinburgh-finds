# Project Tracks

This file tracks all major tracks for the project. Each track has its own detailed plan in its respective folder.

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

## [ ] Track: Data Extraction Engine
*Link: [./conductor/tracks/data_extraction_engine_20260115/](./conductor/tracks/data_extraction_engine_20260115/)*
**Status:** Ready for Implementation
**Dependencies:** Data Ingestion Pipeline (completed)
**Description:** Build modular, intelligent extraction engine that transforms raw ingested data into structured, validated listings. Implements hybrid extraction strategy (deterministic for clean APIs: Google Places, Sport Scotland, Edinburgh Council, OpenChargeMap; LLM-based for unstructured: Serper, OSM). Features include: schema-driven attribute splitting (defined fields → attributes, discovered → discovered_attributes), field-level trust scoring with configurable hierarchy, multi-source deduplication and merging, special field processing (phone/postcode formatting, opening hours, multi-stage summary synthesis), rich text capture for quality summaries, quarantine pattern for failed extractions, comprehensive observability (health dashboard, structured logging, cost tracking), and flexible CLI (single record, per-source, batch all, retry modes). Includes updates to ingestion connectors for rich text capture (Google Places reviews/editorials, Serper snippets). Phase 2 of overall ETL pipeline, complementing completed ingestion system. 10 phases, ~150 tasks, TDD throughout.

---

## [ ] Track: YAML Schema - Single Source of Truth
*Link: [./conductor/tracks/yaml_schema_source_of_truth_20260116/](./conductor/tracks/yaml_schema_source_of_truth_20260116/)*
**Status:** Ready for Implementation
**Priority:** High
**Dependencies:** None
**Description:** Eliminate schema drift by implementing YAML-based single source of truth for all schema definitions. Currently, Prisma schema, Python FieldSpecs, and TypeScript types are maintained separately with no synchronization, creating high risk of drift and blocking horizontal scaling. This track creates a YAML schema format that generates all schemas automatically. From `engine/config/schemas/*.yaml`, generate: (1) Prisma schema for database, (2) Python FieldSpecs for extraction engine, (3) TypeScript types for frontend (optional). Includes validation tests to prevent drift, CLI tool for generation, and migration of existing schemas. Enables adding new entity types (WINERY, RESTAURANT) without code changes - just create new YAML file. Foundational infrastructure for true horizontal scaling across multiple verticals. 8 phases: YAML format & parser, Python generator, Prisma generator, migration & validation, CLI tool, documentation, replacement & cleanup, TypeScript generator (optional).

---

## [ ] Track: Ecosystem Graph - Relationship Extraction
**Status:** Planned (Blocked by Data Extraction Engine)
**Dependencies:** Data Extraction Engine must complete first
**Description:** Extract and validate relationships between entities (coaches→venues, clubs→venues, events→venues) to build the ecosystem graph. Populate `ListingRelationship` table with relationship types (teaches_at, plays_at, based_at, etc.) using LLM analysis of discovered_attributes and cross-entity references. Enable hyper-specific SEO pages ("Coaches at [Venue]", "Clubs in [Area]"). Implement relationship confidence scoring and business claim verification workflow. Future track - will be planned after extraction engine completion.

---
