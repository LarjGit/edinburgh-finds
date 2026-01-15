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
