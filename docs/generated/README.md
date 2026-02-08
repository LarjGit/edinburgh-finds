# Universal Entity Extraction Engine - Documentation

**Generated:** 2026-02-08
**Project:** Edinburgh Finds (Reference Application)
**System:** Universal Entity Extraction Engine

---

## Overview

The **Universal Entity Extraction Engine** is a vertical-agnostic discovery platform that transforms natural language queries into complete, structured entity records through AI-powered multi-source orchestration.

Unlike traditional domain-specific scrapers, this engine operates as a **horizontal infrastructure layer** that can serve unlimited verticals (sports discovery, wine discovery, restaurants, events) without requiring engine code changes. All domain knowledge lives in pluggable YAML Lens configurations.

**Key Principles:**
- **Engine Purity:** Zero domain knowledge in engine code
- **Lens Ownership:** All semantics in YAML configuration
- **Data Quality First:** Deterministic, idempotent, auditable pipelines
- **Production-Ready:** >80% test coverage, strict validation, comprehensive error handling

---

## 🎯 Quick Start

### New Developers
- **[Onboarding Guide](./ONBOARDING.md)** — Complete walkthrough from setup to first query
- **[Development Guide](./DEVELOPMENT.md)** — Daily workflow, TDD practices, common tasks

### Operators & DevOps
- **[Deployment Guide](./DEPLOYMENT.md)** — Production deployment for frontend and backend
- **[Configuration Reference](./CONFIGURATION.md)** — Environment variables, schemas, lens contracts

### Architects & Technical Leads
- **[System Vision](../target/system-vision.md)** — 10 immutable invariants (architectural constitution)
- **[Architecture Specification](../target/architecture.md)** — 11-stage pipeline, contracts, execution semantics

---

## 📚 Core Documentation

### System Architecture
- **[Architecture Overview](./ARCHITECTURE.md)** — Comprehensive system architecture covering the 10 immutable invariants, 11-stage data pipeline, Engine vs Lens separation, subsystem design, module dependencies, and extensibility patterns. Essential reading for understanding the complete system.

### Database & Schema
- **[Database Schema](./DATABASE.md)** — Entity model, canonical dimensions, modules system, pipeline tables, Postgres TEXT[] arrays with GIN indexes, schema generation workflow, and data integrity patterns. Authoritative reference for the universal vertical-agnostic data model.

### Backend (Python Engine)
- **[Backend Architecture](./BACKEND.md)** — Python ETL pipeline covering orchestration, multi-source ingestion (6 connectors), hybrid extraction (deterministic + LLM), lens application, deduplication, merge, entity finalization, and testing strategy. Core reference for backend development.

### Frontend (Next.js)
- **[Frontend Architecture](./FRONTEND.md)** — Next.js 16 (App Router) + React 19 architecture, Server Components, Prisma integration, Tailwind CSS v4, shadcn/ui components, type safety, performance optimization, and mobile-first design patterns.

### Features & Capabilities
- **[Features Documentation](./FEATURES.md)** — Complete feature catalog: multi-source orchestration, hybrid extraction, lens-driven configuration, cross-source deduplication, deterministic merge, data quality & provenance, performance & scalability, developer experience.

### API Reference
- **[API Documentation](./API.md)** — Python Orchestration CLI, network architecture, request/response schemas, error handling, pagination & filtering, versioning strategy, and client integration examples. HTTP REST endpoints are planned but not yet implemented.

### Configuration & Setup
- **[Configuration Reference](./CONFIGURATION.md)** — Comprehensive guide to YAML schemas, lens contracts, connector registry, environment variables, validation rules, module schemas, canonical value registries, and configuration best practices.

### Development Workflow
- **[Development Guide](./DEVELOPMENT.md)** — Test-Driven Development (TDD) workflow, entity lifecycle, daily commands, schema management, testing strategy, code quality gates, Git workflow, and troubleshooting. Follows reality-based incremental alignment methodology.

### Deployment & Operations
- **[Deployment Guide](./DEPLOYMENT.md)** — Infrastructure architecture (Vercel/Cloud Run/Supabase), environment setup, frontend deployment (Next.js), backend deployment (Python engine), monitoring, CI/CD pipeline, scaling strategies, security hardening, disaster recovery.

### Project History
- **[Changelog](./CHANGELOG.md)** — Documentation generation history, timeline of parallel agent runs, validation gates, review cycles, and file-level statistics.

---

## 📊 Diagrams

### System Overview
- **[Architecture Diagram](./diagrams/architecture.mmd)** — Complete system architecture showing Applications Layer, Lens Layer (vocabulary, routing rules, mapping rules, module triggers, canonical registry), and Engine Layer (orchestration, ingestion, extraction, lenses, deduplication, merge, finalization, persistence). Visualizes the Engine vs Lens separation.

- **[Pipeline Diagram](./diagrams/pipeline.mmd)** — 11-stage data flow from query input through Lens Resolution → Planning → Connector Execution → Raw Ingestion → Extraction → Lens Application → Classification → Deduplication → Merge → Finalization → Display. Complete end-to-end pipeline visualization.

- **[Entity Model Diagram](./diagrams/entity_model.mmd)** — Entity-Relationship Diagram showing Entity, ExtractedEntity, RawIngestion, OrchestrationRun relationships. Includes universal entity classification, canonical dimensions (TEXT[] arrays), modules system (JSONB), provenance tracking, and confidence scoring.

### Detailed System Views

#### C4 Model
- **[C4 Context Diagram](./diagrams/c4.mmd)** — System context showing Universal Entity Extraction Engine, external actors (End Users, Lens Designers, AI Agents), and external systems (Supabase, Anthropic Claude API, data sources: Serper, Google Places, OSM, etc.).

- **[Component Diagram](./diagrams/component.mmd)** — Internal component structure: Orchestration System (Planner, Router, Budget Manager), Ingestion System (6 connectors), Extraction System (extractors + LLM), Lens System (loader, interpreter), Persistence Layer (finalizer, slug generator, provenance tracker).

#### Technical Architecture
- **[Dependency Graph](./diagrams/dependency.mmd)** — Module-level dependency hierarchy from top-level CLI/Web through orchestration, ingestion, extraction, lenses, schema, down to shared utilities. Shows clean separation and unidirectional data flow.

- **[Network Diagram](./diagrams/network.mmd)** — Physical deployment architecture: CDN (Vercel Edge), Web Tier (Next.js Server Components), API Gateway, Engine Cluster (Python workers), Database Cluster (Supabase Postgres), and external services. Includes network security zones and data flow paths.

- **[Deployment Diagram](./diagrams/deployment.mmd)** — Infrastructure-as-code deployment view showing Vercel Platform (Next.js frontend), Google Cloud Run (Python engine workers), Supabase (Postgres + connection pooling), external APIs, and environment configurations.

#### Process & State
- **[Sequence Diagram](./diagrams/sequence.mmd)** — End-to-end execution flow timing diagram showing interactions between User, Orchestrator, QueryPlanner, LensSystem, Connectors, Extractors, EntityFinalizer, and Database. Illustrates the complete request-response lifecycle.

- **[State Diagram](./diagrams/state.mmd)** — Entity lifecycle state machine from Query Received → Lens Loaded → Planning → Ingestion → Extraction → Lens Application → Deduplication → Merge → Finalization → Published. Shows failure states, retry logic, and state transitions.

- **[User Journey Diagram](./diagrams/user_journey.mmd)** — User experience flow for four personas: End User (discovery journey), Developer (building features), Lens Designer (creating verticals), and System Operator (monitoring & scaling).

---

## 🔑 Architectural Authorities

### Immutable Documents (READ THESE FIRST)

These two documents form the **architectural constitution** and govern ALL development decisions:

1. **[System Vision](../target/system-vision.md)** — The Architectural Constitution
   - Defines 10 immutable invariants that MUST remain true for the system's lifetime
   - Specifies the Engine vs Lens boundary (Engine = domain-blind, Lenses = all semantics)
   - Defines success criteria: "One Perfect Entity" end-to-end validation requirement
   - Violations are architectural defects regardless of whether functionality appears to work
   - **This document is IMMUTABLE** — treat it as the ultimate authority

2. **[Architecture Specification](../target/architecture.md)** — The Runtime Implementation Specification
   - Concrete execution pipeline, contracts, and validation rules
   - Operationalizes the system-vision.md invariants into runtime behavior
   - Defines the 11-stage pipeline: Lens Resolution → Planning → Ingestion → Extraction → Lens Application → Classification → Deduplication → Merge → Finalization
   - Specifies the locked extraction contract (Phase 1: primitives only, Phase 2: lens application)
   - May evolve deliberately but MUST preserve system-vision.md invariants

### Before Making ANY Architectural Change

**ENFORCEMENT RULE:** You MUST explicitly read `docs/target/system-vision.md` and `docs/target/architecture.md` BEFORE proposing any architectural plan or change.

**Ask These Questions:**
- Does this preserve engine purity? (No domain semantics in engine code)
- Does this maintain determinism and idempotency?
- Does this keep all domain knowledge in Lens contracts only?
- Would this improve data quality in the entity store?

**If uncertain, read system-vision.md first.** It defines what must remain true.

---

## 🛠️ Common Tasks

### Getting Started
```bash
# Clone and setup
git clone <repository>
cd edinburgh_finds

# Backend setup
python -m pip install -r engine/requirements.txt

# Frontend setup
cd web && npm install
```

### Running the System
```bash
# Start frontend dev server
cd web && npm run dev  # http://localhost:3000

# Execute end-to-end query
python -m engine.orchestration.cli run "padel courts Edinburgh"

# Run tests
pytest                    # Backend tests
pytest -m "not slow"      # Fast tests only
cd web && npm run build   # Frontend build validation
```

### Schema Management
```bash
# Validate YAML schemas
python -m engine.schema.generate --validate

# Regenerate all derived schemas (Python, Prisma, TypeScript)
python -m engine.schema.generate --all

# Sync database schema
cd web && npx prisma db push
```

### Quality Checks
```bash
# Test coverage
pytest --cov=engine --cov-report=html  # Target: >80%

# Linting
cd web && npm run lint

# Type checking
cd web && npm run type-check
```

---

## 🧭 Navigation Tips

### By Role

**New Developer?**
1. Read [Onboarding Guide](./ONBOARDING.md)
2. Execute "Your First Query" section
3. Review [Development Guide](./DEVELOPMENT.md) for workflow
4. Study [Architecture Overview](./ARCHITECTURE.md) for system understanding

**Backend Developer?**
1. Read [Backend Architecture](./BACKEND.md)
2. Study [Pipeline Diagram](./diagrams/pipeline.mmd)
3. Review [Database Schema](./DATABASE.md)
4. Check [Configuration Reference](./CONFIGURATION.md)

**Frontend Developer?**
1. Read [Frontend Architecture](./FRONTEND.md)
2. Review [API Documentation](./API.md)
3. Study [Entity Model Diagram](./diagrams/entity_model.mmd)
4. Check [Development Guide](./DEVELOPMENT.md)

**Architect/Technical Lead?**
1. **MUST READ:** [System Vision](../target/system-vision.md)
2. **MUST READ:** [Architecture Specification](../target/architecture.md)
3. Review [Architecture Diagram](./diagrams/architecture.mmd)
4. Study [Features Documentation](./FEATURES.md)

**DevOps/SRE?**
1. Read [Deployment Guide](./DEPLOYMENT.md)
2. Review [Network Diagram](./diagrams/network.mmd)
3. Study [Configuration Reference](./CONFIGURATION.md)
4. Check [Deployment Diagram](./diagrams/deployment.mmd)

### By Task

**Understanding the System:**
- Architecture → [ARCHITECTURE.md](./ARCHITECTURE.md)
- Data Model → [DATABASE.md](./DATABASE.md)
- Pipeline Flow → [diagrams/pipeline.mmd](./diagrams/pipeline.mmd)

**Building Features:**
- Backend → [BACKEND.md](./BACKEND.md)
- Frontend → [FRONTEND.md](./FRONTEND.md)
- API → [API.md](./API.md)

**Configuration:**
- Setup → [CONFIGURATION.md](./CONFIGURATION.md)
- Environment → [DEPLOYMENT.md](./DEPLOYMENT.md)
- Schema → [DATABASE.md](./DATABASE.md)

**Development:**
- Workflow → [DEVELOPMENT.md](./DEVELOPMENT.md)
- Testing → [BACKEND.md](./BACKEND.md#testing)
- Quality → [DEVELOPMENT.md](./DEVELOPMENT.md#code-quality)

---

## 📖 Reading Order for New Team Members

### Week 1: Foundations
1. [Onboarding Guide](./ONBOARDING.md) — Setup and first query
2. [Architecture Overview](./ARCHITECTURE.md) — System design
3. [Pipeline Diagram](./diagrams/pipeline.mmd) — Data flow
4. [Development Guide](./DEVELOPMENT.md) — Daily workflow

### Week 2: Deep Dive
5. [System Vision](../target/system-vision.md) — Architectural invariants
6. [Architecture Specification](../target/architecture.md) — Runtime mechanics
7. [Backend Architecture](./BACKEND.md) OR [Frontend Architecture](./FRONTEND.md)
8. [Database Schema](./DATABASE.md) — Data model

### Week 3: Specialization
9. [Features Documentation](./FEATURES.md) — Capabilities
10. [Configuration Reference](./CONFIGURATION.md) — Configuration system
11. [API Documentation](./API.md) — Integration patterns
12. Role-specific diagrams and guides

---

## 🔍 Finding What You Need

### Search Strategy

**Looking for architecture decisions?**
→ [System Vision](../target/system-vision.md) + [Architecture Specification](../target/architecture.md)

**Looking for implementation details?**
→ [Backend Architecture](./BACKEND.md) + [Frontend Architecture](./FRONTEND.md)

**Looking for data structures?**
→ [Database Schema](./DATABASE.md) + [Entity Model Diagram](./diagrams/entity_model.mmd)

**Looking for configuration?**
→ [Configuration Reference](./CONFIGURATION.md) + [Deployment Guide](./DEPLOYMENT.md)

**Looking for examples?**
→ [Onboarding Guide](./ONBOARDING.md) + [API Documentation](./API.md)

**Looking for visual overview?**
→ [Architecture Diagram](./diagrams/architecture.mmd) + [Pipeline Diagram](./diagrams/pipeline.mmd)

---

## 📝 Contributing

### Before Contributing

1. **Read the architectural authorities:**
   - [System Vision](../target/system-vision.md) — Immutable invariants
   - [Architecture Specification](../target/architecture.md) — Runtime contracts

2. **Understand the development workflow:**
   - [Development Guide](./DEVELOPMENT.md) — TDD practices, quality gates

3. **Study relevant subsystems:**
   - Backend → [Backend Architecture](./BACKEND.md)
   - Frontend → [Frontend Architecture](./FRONTEND.md)
   - Database → [Database Schema](./DATABASE.md)

### Development Philosophy

This project follows **Test-Driven Development (TDD)** with strict quality gates:

- **Red → Green → Refactor** — Write failing tests first
- **>80% test coverage** — All new code must be tested
- **Engine purity** — No domain semantics in engine code
- **Schema-driven** — YAML schemas are single source of truth
- **Reality-based** — Work in ultra-small, testable chunks

See [Development Guide](./DEVELOPMENT.md) for complete workflow details.

---

## 🆘 Getting Help

### Troubleshooting
- [Development Guide - Troubleshooting](./DEVELOPMENT.md#troubleshooting)
- [Deployment Guide - Troubleshooting](./DEPLOYMENT.md#troubleshooting)
- [Configuration Reference - Troubleshooting](./CONFIGURATION.md#troubleshooting)

### Documentation Issues
- Check [Changelog](./CHANGELOG.md) for generation history
- Verify diagram rendering in Mermaid viewer
- Review source files referenced in document headers

### Architectural Questions
1. Read [System Vision](../target/system-vision.md) Section 8: "How Humans and AI Agents Should Use This Document"
2. Check [Architecture Specification](../target/architecture.md) for concrete contracts
3. Review [Architecture Overview](./ARCHITECTURE.md) for system design patterns

---

## 📦 Document Metadata

### Generation Information
- **Generated:** 2026-02-08
- **Generator:** Claude Sonnet 4.5 (Parallel Background Agents v4)
- **Strategy:** Full regeneration with validation gates
- **Total Files:** 23 (10 docs + 11 diagrams + 2 navigation)
- **Total Content:** 20,073 lines, 577 KB documentation

### Document Status
- ✅ All 10 core documents generated and validated
- ✅ All 11 diagrams generated and reviewed
- ✅ All files have substantial content (>800 lines each)
- ✅ All files have proper section structure (>75 sections each)
- ✅ Zero architectural violations detected

### Source Authority
- **Architectural Constitution:** `docs/target/system-vision.md` (immutable)
- **Runtime Specification:** `docs/target/architecture.md` (deliberate evolution)
- **Code Reality:** Live codebase in `engine/` and `web/` directories
- **Schema Definitions:** `engine/config/schemas/*.yaml` (single source of truth)

---

## 🚀 Quick Links

**Essential Reading:**
- [Onboarding](./ONBOARDING.md) | [Architecture](./ARCHITECTURE.md) | [Development](./DEVELOPMENT.md)

**Technical References:**
- [Backend](./BACKEND.md) | [Frontend](./FRONTEND.md) | [Database](./DATABASE.md) | [API](./API.md)

**Operations:**
- [Configuration](./CONFIGURATION.md) | [Deployment](./DEPLOYMENT.md) | [Features](./FEATURES.md)

**Architectural Authority:**
- [System Vision](../target/system-vision.md) | [Architecture Specification](../target/architecture.md)

**Diagrams:**
- [Architecture](./diagrams/architecture.mmd) | [Pipeline](./diagrams/pipeline.mmd) | [Entity Model](./diagrams/entity_model.mmd)

---

**Built with:** Python 3.x, Next.js 16, React 19, PostgreSQL, Prisma, Anthropic Claude
**Reference Application:** Edinburgh Finds (Padel/Sports Discovery)
**License:** [See repository root]
**Documentation Generator:** Claude Sonnet 4.5 + Parallel Background Agents
