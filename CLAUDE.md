# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Document Navigation

**Reading Paths:**

**First time in this codebase?**
1. Read "Architectural Authority" + "Core Concept" below (10 min)
2. Read `docs/system-vision.md` (30 min) - immutable architectural constitution
3. Read `docs/development-methodology.md` (15 min) - how to work incrementally
4. Return here for reference

**Starting a task?**
1. Check `docs/progress/audit-catalog.md` for next catalog item
2. Follow `docs/development-methodology.md` Section 5 (8-step micro-iteration process)
3. Use `COMMANDS.md` for commands, `TROUBLESHOOTING.md` for debugging

**Need documentation?**
- **External libraries** (Next.js, Prisma, Pydantic, pytest, etc.) → Context7 MCP tools
- **Architecture decisions** → `docs/system-vision.md` or `docs/target-architecture.md`
- **Process questions** → `docs/development-methodology.md`
- **Commands** → `COMMANDS.md`
- **Debugging** → `TROUBLESHOOTING.md`

**Document Roles:**
- **CLAUDE.md** (this file): Navigation, architectural authority, core concepts, enforcement rules
- **COMMANDS.md**: All development commands (setup, daily dev, schema, pipeline, environment)
- **TROUBLESHOOTING.md**: Common gotchas and debugging guide
- **development-methodology.md**: 8-step micro-iteration process, constraints, validation gates
- **system-vision.md**: Architectural constitution (10 immutable invariants)
- **target-architecture.md**: Runtime execution pipeline (11 stages)

---

## Architectural Authority (READ THIS FIRST)

**CRITICAL:** This project has two immutable architectural documents that govern ALL development decisions:

1. **`docs/system-vision.md`** — The Architectural Constitution
   - Defines 10 immutable invariants that MUST remain true for the system's lifetime
   - Specifies the Engine vs Lens boundary (Engine = domain-blind, Lenses = all semantics)
   - Defines success criteria: "One Perfect Entity" end-to-end validation requirement
   - Violations are architectural defects regardless of whether functionality appears to work
   - **This document is IMMUTABLE** - treat it as the ultimate authority

2. **`docs/target-architecture.md`** — The Runtime Implementation Specification
   - Concrete execution pipeline, contracts, and validation rules
   - Operationalizes the system-vision.md invariants into runtime behavior
   - Defines the 11-stage pipeline: Lens Resolution → Planning → Ingestion → Extraction → Lens Application → Classification → Deduplication → Merge → Finalization
   - Specifies the locked extraction contract (Phase 1: primitives only, Phase 2: lens application)
   - May evolve deliberately but MUST preserve system-vision.md invariants

**ENFORCEMENT RULE:**
The agent MUST explicitly open and read `docs/system-vision.md` and `docs/target-architecture.md` using the Read tool and MUST confirm this in its response BEFORE proposing any plan or change. Until that confirmation appears, NO further actions are permitted.

**Before making ANY architectural change:**
- Ask: Does this preserve engine purity? (No domain semantics in engine code)
- Ask: Does this maintain determinism and idempotency?
- Ask: Does this keep all domain knowledge in Lens contracts only?
- Ask: Would this improve data quality in the entity store?

If uncertain, **read system-vision.md first**. It defines what must remain true.

---

## Development Workflow (READ THIS SECOND)

**CRITICAL:** This project uses a strict reality-based incremental alignment methodology to prevent AI agent drift and ensure golden-doc compliance.

**Primary Reference:** `docs/development-methodology.md` - READ THIS BEFORE STARTING WORK (15 min)

**Before starting ANY work:**
1. Read `docs/development-methodology.md` (15 min) - MANDATORY
2. Check if `docs/progress/audit-catalog.md` exists
3. If exists: Follow Decision Logic (methodology Section 8) to select next item
4. If not exists: Run initial audit (methodology Section 12) to create catalog

**Core Constraints:**
- Work in ultra-small chunks (max 2 files, max 100 lines)
- User approves micro-plan before execution (Checkpoint 1)
- User validates result after execution (Checkpoint 2)
- See methodology Section 6 (8 Mandatory Constraints) and Section 7 (6 Validation Gates)

---

## Documentation Lookup Strategy

**ALWAYS use Context7 MCP tools for library documentation** (Next.js, React, Prisma, Pydantic, pytest, Tailwind, shadcn/ui, Anthropic SDK, etc.):
1. `resolve-library-id` → find library ID
2. `query-docs` → get current API patterns and best practices

---

## Core Concept: Universal Entity Framework

This is a **vertical-agnostic discovery platform** powered by AI-scale data ingestion. The architecture separates a universal **Entity Engine** (Python) from vertical-specific **Lens Layers** (YAML config).

**Key Principle:** The engine knows nothing about "Padel" or "Wine". It works with generic `entity_class` (place, person, organization, event, thing), multi-valued dimension arrays (`canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`), and flexible JSON `modules`. Vertical logic lives in Lens YAML configs only.

**Scaling Strategy:** Adding a new vertical (e.g., Wine Discovery, Restaurant Finder) should require ZERO engine code changes - only a new `lens.yaml` configuration file.

---

## Architecture Principles (Quick Reference)

**For detailed architectural authority, read:**
- **`docs/system-vision.md`** - 10 immutable invariants (THE architectural constitution)
- **`docs/target-architecture.md`** - Runtime pipeline specification (11 stages)

**Quick Reference - Core Principles:**

### 1. Engine Purity (Invariant 1 in system-vision.md)
- Engine code NEVER contains domain-specific terms ("Padel", "Wine", "Tennis")
- Use universal types: `entity_class` (place/person/organization/event/thing)
- Store dimensions as Postgres arrays: `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`
- ALL domain semantics live in Lens YAML configs, NEVER in engine code

### 2. Schema Single Source of Truth
- All schemas defined in `engine/config/schemas/*.yaml`
- YAML auto-generates: Python FieldSpecs, Prisma schemas, TypeScript interfaces
- NEVER edit generated files (marked "DO NOT EDIT")
- Schema regeneration: `python -m engine.schema.generate --all`

### 3. Test-Driven Development (TDD)
- Red → Green → Refactor workflow (mandatory)
- Write failing tests FIRST, confirm they fail, then implement
- Coverage target: >80% for all new code
- Use `@pytest.mark.slow` for tests >1 second

### 4. Data Flow Pipeline
```
Query → Orchestrator → Connectors → RawIngestion → Extraction →
ExtractedEntity → Lens Application → Classification → Deduplication →
Merge → Finalization → Entity (database) → Frontend
```

See `docs/target-architecture.md` Section 4.1 for complete 11-stage pipeline specification.

### 5. Orchestration: Intelligent Multi-Source Queries
- Runtime control plane in `engine/orchestration/`
- Registry-driven connector metadata (cost, trust, phase, timeout)
- Query analysis → intelligent connector selection → execution plan
- CLI: `python -m engine.orchestration.cli run "your query here"`

**⚠️ Known Issue:** Partial lens mapping implementation. `canonical_activities` populates correctly but `canonical_place_types` and `modules` remain empty. End-to-end test `test_one_perfect_entity_end_to_end_validation` currently fails. "One Perfect Entity" constitutional requirement (system-vision.md Section 6.3) not yet achieved. See audit item LA-003.

---

## Lens Configuration System (Quick Reference)

**Lenses provide vertical-specific interpretation of universal engine data.**

**Core Principle:**
- **Engine:** Domain-agnostic (knows nothing about Padel, Wine, Restaurants)
- **Lenses:** YAML configs containing all domain vocabulary and routing rules
- **Extensibility:** Adding new vertical = ZERO engine code changes (just new YAML)

**Lens Structure:** Each lens is a single `engine/lenses/<lens_id>/lens.yaml` file containing:
- Vocabulary (activity_keywords, location_indicators)
- Connector rules (routing priorities, triggers)
- Mapping rules (text patterns → canonical dimensions)
- Module triggers (when to add sports_facility, wine_producer, etc.)
- Canonical value definitions (display names, SEO slugs, icons)

**⚠️ Implementation Status:** Lens architecture partially functional. Query orchestration and connector routing work. Stage 7 (Lens Application) is incomplete: `canonical_activities` mapping works, but `canonical_place_types` and `modules` population failing. Test: `pytest tests/engine/orchestration/test_end_to_end_validation.py::test_one_perfect_entity_end_to_end_validation -v`

**Lens Development Guide:** `docs/lens-development-guide.md`

---

## Tech Stack (Quick Reference)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript | Server/client rendering |
| **Styling** | Tailwind CSS v4, shadcn/ui components | Component library |
| **Backend** | Python 3.x, Pydantic, Instructor + Anthropic Claude | ETL engine, LLM extraction |
| **Database** | Supabase (PostgreSQL), Prisma 7.3+ (ORM) | Entity storage |
| **Testing** | pytest (Python), Jest (frontend) | >80% coverage target |
| **Data Structures** | Postgres `TEXT[]` arrays (dimensions), JSONB (modules) | Multi-valued indexing |

**Key ORM Detail:** Both frontend (`web/prisma`) and backend (`engine/`) use Prisma, but frontend uses Prisma Client JS and backend uses Prisma Client Python.

---

## Quick Commands

**See `COMMANDS.md` for comprehensive command reference.**

**Most common commands:**
```bash
# Daily development
pytest -m "not slow"              # Fast tests
npm run dev                       # Frontend dev server (in web/)

# Schema regeneration (CRITICAL after YAML changes)
python -m engine.schema.generate --all

# Orchestration
python -m engine.orchestration.cli run "your query"
```

**Before committing:** See `COMMANDS.md` "Before Committing Checklist"

**Troubleshooting:** See `TROUBLESHOOTING.md` for common gotchas

---

## Support Resources

- **Architectural Authority:** `docs/system-vision.md` (immutable constitution) + `docs/target-architecture.md` (runtime spec)
- **Process Manual:** `docs/development-methodology.md` (8-step process, constraints, validation gates, recovery protocol)
- **Commands:** `COMMANDS.md` (setup, daily dev, schema, pipeline, environment)
- **Debugging:** `TROUBLESHOOTING.md` (common gotchas, testing strategy)
- **Implementation Examples:** `docs/plans/` (completed plans), `tests/engine/` (testing patterns)

---

## For AI Agents: Critical Operating Rules

When working on this codebase, you MUST:

1. **Preserve Engine Purity** (system-vision.md Invariant 1)
   - NEVER add domain-specific terms ("Padel", "Wine", "Tennis") to engine code
   - ALL domain semantics belong in Lens YAML configs only
   - Engine operates on opaque values: `entity_class`, `canonical_*` arrays, `modules`

2. **Respect the Extraction Contract** (target-architecture.md Section 4.2)
   - **Phase 1 (extractors):** Return ONLY schema primitives + raw observations
   - **Phase 2 (lens application):** Populate canonical dimensions + modules
   - Extractors must NEVER emit `canonical_*` fields or `modules`

3. **Maintain Determinism** (system-vision.md Invariant 4)
   - Given same inputs + lens contract → identical outputs
   - No randomness, iteration-order dependence, or time-based behavior
   - All tie-breaking must be deterministic

4. **Validate Against Reality** (system-vision.md Section 6)
   - The entity database is the ultimate correctness signal
   - Tests that pass but produce incorrect entity data = FAILURE
   - At least one "perfect entity" must flow end-to-end before validation

5. **Fail Fast on Violations** (system-vision.md Invariant 6)
   - Invalid Lens contracts → fail at bootstrap
   - Silent fallback behavior is FORBIDDEN
   - Make errors visible, never hide them

6. **No Vertical Exceptions** (system-vision.md Invariant 10)
   - The reference lens (Edinburgh Finds) gets NO special treatment
   - If a feature can't be expressed through Lens contracts → architectural defect

7. **Extraction Helper Purity** (development-methodology.md Constraint C8)
   - Extraction helpers may ONLY: validate, normalize, track provenance
   - NEVER: interpret, classify, detect semantics, emit `canonical_*` or `modules`
   - Structural signals allowed: counts, presence checks, data completeness (not interpretation)

**When uncertain:** Read `docs/system-vision.md` Section 8 ("How Humans and AI Agents Should Use This Document")

**Process enforcement:** Follow `docs/development-methodology.md` for 8-step micro-iteration process with 8 mandatory constraints and 6 validation gates.
