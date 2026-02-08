# Development Guide

**Project:** Universal Entity Extraction Engine
**Reference Application:** Edinburgh Finds (Padel/Sports Discovery)
**Last Generated:** 2026-02-08

---

## Table of Contents

1. [Overview](#overview)
2. [Development Workflow](#development-workflow)
3. [Entity Lifecycle](#entity-lifecycle)
4. [Daily Commands](#daily-commands)
5. [Schema Management](#schema-management)
6. [Testing Strategy](#testing-strategy)
7. [Code Quality](#code-quality)
8. [Git Workflow](#git-workflow)
9. [Adding Features](#adding-features)
10. [Common Tasks](#common-tasks)
11. [Troubleshooting](#troubleshooting)

---

## Overview

### Development Philosophy

The Universal Entity Extraction Engine follows a **reality-based incremental alignment methodology** designed to prevent AI agent drift and ensure architectural compliance with golden documents.

**Core Principles:**

- **Test-Driven Development (TDD):** Write failing tests first, implement minimum code to pass, refactor while keeping tests green
- **Ultra-Small Work Units:** Change 1-2 files maximum per iteration
- **Reality-Based Planning:** Read actual code before planning, verify all assumptions
- **User-Driven Validation:** User approves plans before execution and validates outcomes after
- **Golden Doc Supremacy:** `docs/target/system-vision.md` and `docs/target/architecture.md` govern all decisions
- **Foundation Permanence:** Completed work is never revisited, each change is production-quality

### Architectural Constraints

Before starting ANY development work, you must understand:

1. **Engine Purity (Invariant 1):** The engine contains ZERO domain knowledge. No "Padel", "Wine", "Tennis" in engine code.
2. **Lens Ownership (Invariant 2):** ALL domain semantics live exclusively in Lens YAML configs.
3. **Extraction Contract (Architecture 4.2):**
   - Phase 1 (extractors): Return ONLY schema primitives + raw observations
   - Phase 2 (lens application): Populate canonical dimensions + modules
4. **Determinism (Invariant 4):** Same inputs + lens contract = same outputs, always.

**READ THESE FIRST (mandatory):**
- `docs/target/system-vision.md` (30 min) — The immutable architectural constitution
- `docs/target/architecture.md` (45 min) — Runtime implementation specification
- `docs/development-methodology.md` (15 min) — Development process and constraints

---

## Development Workflow

### Micro-Iteration Process (8 Steps with User Checkpoints)

This is the ONLY approved development workflow. Deviations are not permitted.

#### Step 1: Select Next Item

**If `docs/progress/audit-catalog.md` exists:**
1. Read the catalog
2. Check "Current Phase" field
3. Use Decision Logic (methodology Section 8) to select next item
4. Work items are sorted by priority: Foundational Level 1 (critical) → Level 2 (important) → Level 3 (feature)

**If catalog does NOT exist:**
1. Run initial audit (methodology Section 12, Step 2)
2. Create `docs/progress/audit-catalog.md` using template (methodology Section 10)
3. Catalog all architectural violations from system-vision.md Invariants 1-10
4. Return to Step 1

#### Step 2: Code Reality Audit (MANDATORY)

**Before planning anything, read the actual code:**

1. Identify files that will be touched (primary file, dependencies, tests)
2. Read ALL files using Read tool
3. Document actual structure (function signatures, class definitions, imports)
4. List explicit assumptions and verify by reading code
5. NEVER guess, assume, or use mental models

**Red Flag:** If you find yourself saying "I assume..." → STOP and read the code.

#### Step 3: Write Micro-Plan

Create a **half-page maximum** plan:

**Header:**
- Catalog Item ID: EP-001
- Golden Doc Reference: system-vision.md Invariant 1 (Engine Purity)
- Files Touched: `engine/extraction/entity_classifier.py` (1 file)

**Current State (from Step 2 audit):**
```python
# Lines 102-120 in entity_classifier.py contain:
if "padel" in raw_categories or "tennis" in raw_categories:
    return "place"
# (hardcoded domain terms - violates Invariant 1)
```

**Change:**
- Remove domain-specific terms from lines 102-120
- Replace with structural classification based on schema primitives

**Pass Criteria:**
- Test `test_classifier_contains_no_domain_literals()` passes
- Existing entity classification tests still pass
- Entity still classifies correctly as "place"

**Estimated Scope:** 20 lines changed, 1 file

#### User Checkpoint 1: Approve Micro-Plan (1-2 min)

**Agent presents:** "Next item: [ID]. Will change [specific function in file]. Here's the micro-plan. Approve?"

**User reviews:**
- Is scope small enough? (1-2 files)
- Is golden doc reference correct?
- Does current state match reality?
- Is pass criteria clear?

**User decides:**
- ✅ Approve → proceed
- 🔄 Revise → agent updates plan
- ❌ Reject → agent selects different item

#### Step 4: Review Constraints (Agent Self-Check)

Before executing, verify all constraints satisfied:

- ✅ Single architectural principle addressed
- ✅ All assumptions verified from actual code (not guessed)
- ✅ Pass criteria references golden docs explicitly
- ✅ No more than one "seam" crossed (one architectural boundary)
- ✅ Maximum 2 files changed (excluding tests)
- ✅ Maximum 100 lines of code changed
- ✅ Test-first approach planned
- ✅ Extraction helpers perform ONLY validation/normalization (never interpretation)

**If any constraint violated → return to Step 3, revise plan.**

#### Step 5: Execute with TDD

**Red → Green → Refactor:**

1. **Write failing test FIRST:**
   ```python
   def test_classifier_contains_no_domain_literals():
       """Validates Invariant 1: Engine Purity"""
       source = inspect.getsource(entity_classifier)
       forbidden = ["padel", "tennis", "wine", "restaurant"]
       for term in forbidden:
           assert term.lower() not in source.lower()
   ```

2. **Confirm test fails (RED):**
   ```bash
   pytest tests/engine/extraction/test_entity_classifier.py::test_classifier_contains_no_domain_literals
   # Should fail with current code
   ```

3. **Implement minimum code to pass (GREEN):**
   - Make the change described in micro-plan
   - Run test until it passes

4. **Refactor while keeping tests green:**
   - Improve code quality
   - Maintain test passing

5. **Run full test suite:**
   ```bash
   pytest engine/extraction/
   # Ensure no regressions
   ```

**Key Rule:** If assumptions were wrong or blockers appear → STOP, return to Step 2 (Code Reality Audit).

#### Step 6: Validate Against Golden Docs

Before marking complete:

1. **Re-read relevant section of golden docs** (system-vision.md or architecture.md)
2. **Manual verification:** "Does this change uphold the principle?"
3. **Check test explicitly validates golden doc compliance**
4. **Ensure no new violations introduced elsewhere**

#### User Checkpoint 2: Validate Result (2-3 min)

**Agent presents:** "Complete. Changed [files]. Test passes: [test name]. All gates passed. Review?"

**User validates:**
1. **Look at diff:**
   ```bash
   git diff engine/extraction/entity_classifier.py
   ```
2. **Run tests yourself:**
   ```bash
   pytest tests/engine/extraction/test_entity_classifier.py -v
   ```
3. **Verify scope:** Only planned files changed?
4. **Check golden doc alignment:** Does it uphold the principle?

**User decides:**
- ✅ Approve → proceed to Step 7
- 🔄 Revise → agent fixes issues
- ❌ Reject → revert changes, return to planning

#### Step 7: Mark Complete & Commit

**Only after user approval:**

1. **Update catalog:**
   - Mark item as `[x]` complete
   - Add completion date + commit hash + **executable proof**
   - Update "Last Updated" timestamp

2. **Commit with conventional commit message:**
   ```bash
   git add engine/extraction/entity_classifier.py tests/engine/extraction/test_entity_classifier.py

   git commit -m "fix(extraction): remove domain terms from classifier (Invariant 1)

   Replaced hardcoded domain-specific category checks with structural
   classification rules. Classifier now uses only universal type indicators
   and structural field checks, preserving engine purity.

   Validates: system-vision.md Invariant 1 (Engine Purity)
   Catalog Item: EP-001

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

3. **Foundation is now solid** — never needs to be revisited

#### Step 8: Compounding (Mandatory, Lightweight)

After completing Step 7, answer three questions:

1. **Pattern Candidate?**
   - Yes / No
   - If yes: Describe pattern in 1-2 sentences + reference concrete example

2. **Documentation Clarity Improvement?**
   - Yes / No
   - If yes: Identify relevant section + propose one-line clarification

3. **Future Pitfall Identified?**
   - Yes / No
   - If yes: State pitfall in single sentence

**Rules:**
- Compounding observations are proposals, not automatic changes
- User decides whether to ignore, defer, or promote to documentation
- No files are required to be updated during this step

**Key Principle:** If a lesson was learned and not recorded, it will be relearned the hard way later.

### The Three Development Phases

#### Phase 1: Foundation (Architectural Integrity)

**Goal:** Fix all blocking architectural violations from golden docs.

**Source of Work:** Audit `docs/target/system-vision.md` Invariants 1-10:
- Engine Purity (Invariant 1): No domain terms in engine code
- Lens Ownership (Invariant 2): All semantics in lens configs
- Zero Engine Changes (Invariant 3): New verticals require no engine changes
- Determinism (Invariant 4): Same inputs → same outputs
- Canonical Registry Authority (Invariant 5): All values declared
- Fail-Fast Validation (Invariant 6): Invalid contracts fail at bootstrap
- Schema-Bound LLMs (Invariant 7): Only validated output
- No Translation Layers (Invariant 8): Universal schema end-to-end
- Engine Independence (Invariant 9): Useful without specific vertical
- No Reference-Lens Exceptions (Invariant 10): No special treatment

**Completion Criteria:**
- All **Level-1 violations on the runtime path for the validation entity** resolved
- Bootstrap validation gates implemented and enforced
- No domain terms in engine code on validation entity's path
- All boundaries correct for validation entity flow

**Transition to Phase 2:** Blocking Level-1 violations resolved + bootstrap gates enforced.

**Note:** Remaining Level-2/Level-3 violations remain cataloged and can be addressed during or after Phase 2. This prevents perfectionism paralysis.

#### Phase 2: Core Pipeline Implementation

**Goal:** Implement complete orchestration pipeline per architecture.

**Source of Work:** `docs/target/architecture.md` Section 4.1 - Pipeline Stages.

The 11 stages in canonical order:
1. Input
2. Lens Resolution and Validation
3. Planning
4. Connector Execution
5. Raw Ingestion Persistence
6. Source Extraction
7. Lens Application
8. Classification
9. Cross-Source Deduplication Grouping
10. Deterministic Merge
11. Finalization and Persistence

**Critical Constraint: Explicit Lens Resolution Required**
- Validation entity work MUST use explicit lens resolution (CLI flag `--lens`, environment variable `LENS_ID`, or config)
- Dev/Test lens fallback (architecture.md 3.1) is FORBIDDEN for "One Perfect Entity" proof
- Fallback only permitted for local unit tests, never integration/validation work

**Completion Criteria:**
- All 11 pipeline stages implemented and working
- One perfect entity flows end-to-end correctly (system-vision.md Section 6.3)
- Database inspection shows correct entity data
- All pipeline tests pass

**Transition to Phase 3:** Complete pipeline operational + validation entity correct.

#### Phase 3: System Expansion

**Goal:** Add more connectors, lenses, coverage.

**Source of Work:** Business/product priorities (not in golden docs):
- More connectors for existing verticals
- New vertical lenses
- More edge cases and entities
- Performance optimization
- Operational improvements

**Note:** Foundation and pipeline never change in Phase 3.

---

## Entity Lifecycle

### Pipeline States

The following Mermaid diagram shows the entity lifecycle through the 11-stage pipeline:

```mermaid
stateDiagram-v2
    note right of [*]
        Universal Entity Extraction Engine
        State Transitions & Execution Flow
    end note

    %% Entity Lifecycle States
    [*] --> QuerySubmitted: User submits query

    QuerySubmitted --> LensResolved: Lens resolution & validation
    LensResolved --> PlanCreated: Orchestrator creates execution plan
    PlanCreated --> ConnectorDispatch: Dispatch connectors by phase

    ConnectorDispatch --> RawDataIngested: All connectors complete
    RawDataIngested --> Extracted: Per-source extraction

    Extracted --> LensMapped: Apply mapping rules
    LensMapped --> Classified: Determine entity_class

    Classified --> Deduplicated: Cross-source grouping
    Deduplicated --> Merged: Deterministic merge

    Merged --> Finalized: Generate slugs, upsert
    Finalized --> [*]: Entity persisted

    %% Failure paths
    LensResolved --> [*]: Lens validation fails
    ConnectorDispatch --> PartialIngestion: Some connectors fail
    PartialIngestion --> RawDataIngested: Continue with available data
    Extracted --> [*]: Critical extraction failure
    Merged --> [*]: Persistence failure

    %% Connector Execution States (nested)
    state ConnectorDispatch {
        [*] --> Planned
        Planned --> Queued: Added to phase queue
        Queued --> Executing: Connector invoked

        Executing --> RateLimited: Rate limit hit
        RateLimited --> Executing: Retry after backoff

        Executing --> Success: Data returned
        Executing --> Timeout: Execution timeout
        Executing --> Failed: Network/API error

        Success --> Persisting: Save raw artifact
        Persisting --> Completed: Artifact persisted

        Completed --> [*]
        Timeout --> [*]
        Failed --> [*]
    }

    %% Annotations
    note right of LensResolved
        Bootstrap validation gates:
        - Schema validation
        - Canonical registry integrity
        - Connector references
        - Regex compilation
    end note

    note right of Extracted
        Phase 1 (Extractors):
        Schema primitives + raw observations only
        NO canonical_* or modules
    end note

    note right of LensMapped
        Phase 2 (Lens Application):
        Populate canonical dimensions
        Execute module triggers
        Deterministic rules first
    end note

    note right of Merged
        Deterministic merge cascade:
        trust_tier → quality → confidence
        → completeness → priority → connector_id
    end note
```

### Key Pipeline Stages

**Stage 2: Lens Resolution and Validation**
- Validate lens contract structure
- Check canonical registry integrity
- Verify connector references
- Compile regex patterns
- **Fail fast if invalid** (system-vision.md Invariant 6)

**Stage 6: Source Extraction**
- Extractors emit ONLY schema primitives + raw observations
- NO canonical dimensions or modules (extraction boundary contract)
- Deterministic rules preferred over LLM where possible
- LLM output must be schema-validated via Pydantic + Instructor

**Stage 7: Lens Application**
- Apply mapping rules to populate canonical dimensions
- Execute module triggers
- Deterministic rules processed first
- All interpretation happens here (NOT in extractors)

**Stage 10: Deterministic Merge**
- Merge cascade: trust_tier → quality → confidence → completeness → priority → connector_id
- No connector-specific conditions allowed
- Only metadata-driven merge behavior
- Same inputs = same merged output (idempotent)

**Stage 11: Finalization and Persistence**
- Generate URL-safe slugs
- Upsert to Entity table
- Re-running same query updates existing entities (idempotent)

### Connector Execution States

Connectors progress through these states during Stage 4 (Connector Execution):

1. **Planned:** Connector selected by planner
2. **Queued:** Added to phase queue (Phase 1/2/3)
3. **Executing:** Connector invoked
4. **RateLimited:** Hit rate limit, retry after backoff
5. **Success / Timeout / Failed:** Execution outcome
6. **Persisting:** Saving raw artifact
7. **Completed:** Artifact persisted as RawIngestion record

---

## Daily Commands

### Setup (First Time)

```bash
# Backend (Python Engine)
python -m pip install -r engine/requirements.txt

# Frontend (Next.js)
cd web
npm install

# Database (Prisma)
cd web
npx prisma generate  # Generate Prisma client from schema
npx prisma db push   # Sync schema to Supabase (dev)
```

### Frontend Development

```bash
cd web

# Start Next.js dev server (http://localhost:3000)
npm run dev

# Production build (also runs type checking)
npm run build

# ESLint
npm run lint

# Type checking only
npm run type-check

# Run tests (non-interactive for CI)
CI=true npm test
```

### Backend Development

```bash
# Run all tests
pytest

# Run fast tests only (excludes @pytest.mark.slow)
pytest -m "not slow"

# Run specific module tests
pytest engine/orchestration/
pytest tests/engine/extraction/

# Generate coverage report (target: >80%)
pytest --cov=engine --cov-report=html
# Open htmlcov/index.html to view coverage

# Run with verbose output
pytest -v

# Run specific test
pytest tests/engine/extraction/test_entity_classifier.py::test_classifier_purity -v
```

### Data Pipeline Commands

```bash
# Ingestion (fetch raw data from single source)
python -m engine.ingestion.cli run --query "padel courts Edinburgh"

# Extraction (structured data from raw ingestion)
python -m engine.extraction.cli single <raw_ingestion_id>
python -m engine.extraction.cli source serper --limit 10

# Orchestration (intelligent multi-source query - recommended)
python -m engine.orchestration.cli run "padel clubs in Edinburgh"

# With explicit lens (required for validation entity work)
python -m engine.orchestration.cli run "powerleague portobello edinburgh" --lens edinburgh_finds
```

### Schema Management

```bash
# CRITICAL: YAML schemas are the single source of truth
# Location: engine/config/schemas/*.yaml

# Validate schemas before committing
python -m engine.schema.generate --validate

# Regenerate all derived schemas (Python FieldSpecs, Prisma, TypeScript)
python -m engine.schema.generate --all

# When you modify a YAML schema:
# 1. Edit engine/config/schemas/<entity>.yaml
# 2. Run: python -m engine.schema.generate --all
# 3. Generated files are marked "DO NOT EDIT" - never modify them directly
```

### Database Operations

```bash
cd web

# Generate Prisma client (after schema changes)
npx prisma generate

# Push schema changes to database (development)
npx prisma db push

# Create migration (production)
npx prisma migrate dev --name <migration_name>

# Open Prisma Studio (database GUI)
npx prisma studio

# Inspect entity data (validation)
psql $DATABASE_URL -c "
SELECT entity_name, entity_class, canonical_activities, canonical_place_types, modules
FROM entities
WHERE entity_name ILIKE '%powerleague%portobello%';"
```

### Git Operations

```bash
# Check current branch
git branch

# Check status (never use -uall flag - can cause memory issues)
git status

# View diff
git diff engine/extraction/entity_classifier.py

# Stage specific files (preferred over "git add .")
git add engine/extraction/entity_classifier.py tests/engine/extraction/test_entity_classifier.py

# Commit with conventional commit message
git commit -m "$(cat <<'EOF'
fix(extraction): remove domain terms from classifier (Invariant 1)

Replaced hardcoded domain-specific category checks with structural
classification rules. Classifier now uses only universal type indicators
and structural field checks, preserving engine purity.

Validates: system-vision.md Invariant 1 (Engine Purity)
Catalog Item: EP-001

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"

# View recent commits
git log --oneline -10

# View specific commit
git show <commit_hash>
```

---

## Schema Management

### YAML Schemas: Single Source of Truth

All schema definitions live in `engine/config/schemas/*.yaml`. These YAML files auto-generate:

- **Python FieldSpecs:** `engine/schema/<entity>.py`
- **Prisma schemas:** `web/prisma/schema.prisma` and `engine/prisma/schema.prisma`
- **TypeScript interfaces:** `web/lib/types/generated/<entity>.ts`

**NEVER edit generated files directly** — they are overwritten on regeneration. Generated files have "DO NOT EDIT" headers.

### Schema Workflow

#### 1. Edit YAML Schema

```yaml
# engine/config/schemas/entity.yaml
fields:
  - name: entity_name
    type: string
    required: true
    description: "The primary name or title of the entity"

  - name: canonical_activities
    type: array
    items: string
    required: false
    description: "Multi-valued dimension for activity classifications"
    # This field is populated in Phase 2 (Lens Application)
```

#### 2. Validate Schema

```bash
python -m engine.schema.generate --validate
# Checks YAML syntax, required fields, type consistency
```

#### 3. Regenerate All Schemas

```bash
python -m engine.schema.generate --all
# Generates Python FieldSpecs, Prisma schemas, TypeScript interfaces
```

#### 4. Sync to Database

```bash
cd web

# Development: Push schema changes directly
npx prisma db push

# Production: Create migration
npx prisma migrate dev --name add_canonical_activities_field

# Regenerate Prisma client
npx prisma generate
```

#### 5. Verify Changes

```bash
# Check generated Python schema
cat engine/schema/entity.py

# Check generated Prisma schema
cat web/prisma/schema.prisma

# Check generated TypeScript interface
cat web/lib/types/generated/entity.ts

# Verify all have "DO NOT EDIT" headers
```

### Common Schema Patterns

#### Adding a New Canonical Dimension

```yaml
# engine/config/schemas/entity.yaml
fields:
  - name: canonical_roles
    type: array
    items: string
    required: false
    description: "Multi-valued dimension for role classifications (e.g., coach, player, referee)"
    # Populated in Phase 2 (Lens Application)
    # Values defined in lens canonical registry
```

Then regenerate:
```bash
python -m engine.schema.generate --all
cd web && npx prisma db push && npx prisma generate
```

#### Adding a Module Field

Modules are namespaced JSONB structures. Define module schemas in lens configs, not in universal schema.

```yaml
# engine/lenses/edinburgh_finds/lens.yaml (example, not in universal schema)
modules:
  sports_facility:
    fields:
      - name: padel_courts
        type: object
        properties:
          indoor_count: integer
          outdoor_count: integer
          surface_type: string
```

The universal entity schema has a generic `modules` JSONB field. Specific module structures are defined in lens contracts only.

### Schema Validation Rules

1. **Required fields must have default values or be nullable**
2. **Array fields must specify item type**
3. **Enum fields must list allowed values**
4. **Foreign key references must exist**
5. **Type consistency across Python/Prisma/TypeScript**

Validation runs automatically on `--validate` and before regeneration.

---

## Testing Strategy

### Test Types

#### Unit Tests

- **Scope:** Single module, single function, single class
- **Mock:** External dependencies (API calls, LLM calls, database)
- **Coverage:** Both success and failure cases
- **Location:** `tests/engine/<module>/test_<file>.py`

Example:
```python
# tests/engine/extraction/test_entity_classifier.py
def test_classifier_contains_no_domain_literals():
    """Validates Invariant 1: Engine Purity"""
    source = inspect.getsource(entity_classifier)
    forbidden = ["padel", "tennis", "wine", "restaurant"]
    for term in forbidden:
        assert term.lower() not in source.lower()

def test_classifier_places_have_coordinates():
    """Places require latitude + longitude (structural classification)"""
    data = {"latitude": 55.9533, "longitude": -3.1883, "street_address": "123 Main St"}
    assert classify_entity(data) == "place"

def test_classifier_missing_coordinates_not_place():
    """Entities without coordinates cannot be classified as place"""
    data = {"street_address": "123 Main St"}  # No coordinates
    assert classify_entity(data) != "place"
```

#### Integration Tests

- **Scope:** Complete data flows (ingest → extract → dedupe → merge)
- **Database:** Use test database or transactions
- **Verification:** Database state after pipeline execution
- **Location:** `tests/engine/integration/`

Example:
```python
# tests/engine/integration/test_end_to_end_extraction.py
def test_powerleague_entity_extraction(test_db):
    """Validates end-to-end extraction for Powerleague Portobello"""
    # Run orchestration
    result = orchestrator.run("powerleague portobello edinburgh", lens_id="edinburgh_finds")

    # Verify entity in database
    entity = test_db.query(Entity).filter(Entity.entity_name.ilike("%powerleague%portobello%")).first()

    assert entity is not None
    assert entity.entity_class == "place"
    assert "padel" in entity.canonical_activities
    assert "sports_facility" in entity.modules
```

#### Snapshot Testing

- **Scope:** Extraction outputs
- **Purpose:** Detect unintended changes in extractor behavior
- **Tool:** pytest snapshot plugin
- **Location:** `tests/engine/extraction/snapshots/`

Example:
```python
# tests/engine/extraction/test_serper_extractor.py
def test_serper_extraction_output_stable(snapshot):
    """Extractor output should remain stable across runs"""
    raw_data = load_fixture("serper_powerleague.json")
    extracted = serper_extractor.extract(raw_data)

    # Compare against snapshot
    snapshot.assert_match(extracted.dict(), "serper_powerleague_extraction.json")
```

### Coverage Requirements

```bash
# Generate HTML coverage report
pytest --cov=engine --cov-report=html

# Open htmlcov/index.html to view coverage

# Target: >80% coverage for all modules
# New code must maintain or improve coverage
```

**Coverage checklist:**
- ✅ All public functions covered
- ✅ Success and failure paths tested
- ✅ Edge cases covered
- ✅ Error handling verified

### Test Markers

Use `@pytest.mark.slow` for tests >1 second:

```python
import pytest

@pytest.mark.slow
def test_full_pipeline_integration():
    """Complete pipeline test (takes ~5 seconds)"""
    # This test is skipped when running `pytest -m "not slow"`
    pass

def test_classifier_basic():
    """Fast unit test (<1 second)"""
    # This test runs in both `pytest` and `pytest -m "not slow"`
    pass
```

Run fast tests only:
```bash
pytest -m "not slow"
# Excludes tests marked with @pytest.mark.slow
```

Run all tests including slow:
```bash
pytest
# Runs all tests
```

### Fixture Usage

Use fixtures for common setup:

```python
# tests/conftest.py
import pytest

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for extraction tests"""
    class MockClient:
        def extract(self, prompt, schema):
            return schema(entity_name="Test Entity", entity_class="place")
    return MockClient()

@pytest.fixture
def test_db():
    """Test database with schema applied"""
    db = create_test_database()
    apply_schema(db)
    yield db
    cleanup_database(db)
```

Use in tests:
```python
def test_extraction_with_llm(mock_llm_client):
    """Test extraction using mocked LLM client"""
    extractor = LLMExtractor(client=mock_llm_client)
    result = extractor.extract(raw_data)
    assert result.entity_name == "Test Entity"
```

### Test Organization

```
tests/
├── engine/
│   ├── conftest.py              # Shared fixtures
│   ├── extraction/
│   │   ├── test_entity_classifier.py
│   │   ├── test_serper_extractor.py
│   │   └── snapshots/           # Snapshot test data
│   ├── orchestration/
│   │   ├── test_planner.py
│   │   └── test_registry.py
│   ├── lenses/
│   │   └── test_query_lens.py
│   └── integration/
│       └── test_end_to_end_extraction.py
└── web/
    └── (Next.js tests)
```

---

## Code Quality

### Linting

#### Python

```bash
# Linting is enforced via pytest and type checking
# Type hints required for all public functions

# Example function with proper type hints:
def classify_entity(data: dict[str, Any], ctx: ExecutionContext) -> str:
    """
    Classify entity based on structural signals only.

    Args:
        data: Raw entity data (schema primitives only)
        ctx: Execution context for logging and tracing

    Returns:
        Entity class: "place", "person", "organization", "event", or "thing"
    """
    if has_coordinates(data) and has_street_address(data):
        return "place"
    return "thing"
```

#### TypeScript (Frontend)

```bash
cd web

# Run ESLint
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix

# Type checking
npm run type-check
```

### Type Safety

#### Python (Pydantic)

All data structures use Pydantic schemas:

```python
from pydantic import BaseModel, Field

class ExtractedEntity(BaseModel):
    """
    Phase 1 extraction output (primitives + raw observations only).
    NO canonical dimensions or modules.
    """
    entity_name: str = Field(..., description="Primary name or title")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")
    street_address: str | None = Field(None, description="Street address")
    raw_categories: list[str] = Field(default_factory=list, description="Opaque category observations")
    # NO canonical_activities, canonical_roles, canonical_place_types, canonical_access
    # NO modules
```

#### TypeScript (Frontend)

All types generated from schemas:

```typescript
// web/lib/types/generated/entity.ts (DO NOT EDIT - auto-generated)

export interface Entity {
  id: string;
  entity_name: string;
  entity_class: 'place' | 'person' | 'organization' | 'event' | 'thing';
  canonical_activities: string[];
  canonical_roles: string[];
  canonical_place_types: string[];
  canonical_access: string[];
  modules: Record<string, any>;  // JSONB
  created_at: Date;
  updated_at: Date;
}
```

### Pre-Commit Hooks

Before every commit:

1. **Schema validation:**
   ```bash
   python -m engine.schema.generate --validate
   ```

2. **Run tests:**
   ```bash
   pytest  # Backend
   cd web && npm run build  # Frontend (includes type checking)
   ```

3. **Check linting:**
   ```bash
   cd web && npm run lint
   ```

4. **Verify coverage:**
   ```bash
   pytest --cov=engine  # Should be >80%
   ```

5. **Update docs:** If implementation affects architecture or plans, update relevant documentation.

---

## Git Workflow

### Conventional Commits

Every commit message follows this format:

```
<type>(<scope>): <description>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature change)
- `test`: Adding or updating tests
- `chore`: Build, CI, or tooling changes

**Example:**
```bash
git commit -m "$(cat <<'EOF'
fix(extraction): remove domain terms from classifier (Invariant 1)

Replaced hardcoded domain-specific category checks with structural
classification rules. Classifier now uses only universal type indicators
and structural field checks, preserving engine purity.

Validates: system-vision.md Invariant 1 (Engine Purity)
Catalog Item: EP-001

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### Co-Author Attribution

All AI-assisted commits include co-author attribution:

```
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

This is added to the footer of every commit message.

### Branch Strategy

```bash
# Main branch (production)
main

# Development work
git checkout -b feature/add-wine-discovery-lens
git checkout -b fix/extraction-boundary-violation

# After work complete and approved:
git checkout main
git merge feature/add-wine-discovery-lens
git push origin main
```

### Staging Files

**Prefer staging specific files** rather than using `git add .` or `git add -A`:

```bash
# GOOD: Specific files
git add engine/extraction/entity_classifier.py tests/engine/extraction/test_entity_classifier.py

# BAD: Can accidentally include sensitive files (.env, credentials) or large binaries
git add .
git add -A
```

### Safety Protocol

**NEVER run destructive git commands without explicit user request:**

- ❌ `git push --force`
- ❌ `git reset --hard`
- ❌ `git checkout .`
- ❌ `git restore .`
- ❌ `git clean -f`
- ❌ `git branch -D`

**NEVER skip hooks:**

- ❌ `--no-verify`
- ❌ `--no-gpg-sign`

**NEVER amend commits** unless explicitly requested:

- After pre-commit hook failure, create a NEW commit (don't amend previous)
- Amending after hook failure can destroy previous work

**ALWAYS create NEW commits** rather than amending (unless user explicitly requests amend).

---

## Adding Features

### Before Starting ANY Work

1. **Read golden docs:**
   - `docs/target/system-vision.md` (30 min)
   - `docs/target/architecture.md` (45 min)

2. **Check architectural invariants:**
   - Does this preserve engine purity? (No domain semantics in engine code)
   - Does this maintain determinism and idempotency?
   - Does this keep all domain knowledge in Lens contracts only?
   - Would this improve data quality in the entity store?

3. **If uncertain, read system-vision.md first.** It defines what must remain true.

### Feature Development Process

#### 1. Write Tests First (TDD)

```python
# tests/engine/extraction/test_new_feature.py
def test_new_feature_validates_invariant():
    """Test that new feature upholds architectural principle"""
    # Write failing test first
    result = new_feature(input_data)
    assert result.meets_requirement()
```

#### 2. Confirm Test Fails (RED)

```bash
pytest tests/engine/extraction/test_new_feature.py::test_new_feature_validates_invariant
# Should fail - feature not implemented yet
```

#### 3. Implement Minimum Code (GREEN)

```python
# engine/extraction/new_feature.py
def new_feature(input_data: dict) -> Result:
    """
    Implement minimum code to make test pass.

    CRITICAL: Preserve architectural boundaries:
    - NO domain-specific terms
    - NO canonical dimension interpretation
    - Only schema primitives and structural signals
    """
    # Minimal implementation
    pass
```

Run test:
```bash
pytest tests/engine/extraction/test_new_feature.py::test_new_feature_validates_invariant
# Should pass now
```

#### 4. Refactor While Keeping Tests Green

- Improve code quality
- Add error handling
- Improve type hints
- Keep tests passing

#### 5. Validate Against Golden Docs

- Re-read relevant section of system-vision.md or architecture.md
- Question: "Does this change uphold the stated principles?"
- Evidence: Point to specific code demonstrating compliance

#### 6. Run Full Test Suite

```bash
pytest
pytest --cov=engine --cov-report=html
# All tests pass, coverage >80%
```

#### 7. Update Documentation

If feature affects architecture or public APIs:
- Update `docs/target/architecture.md` (if runtime behavior changed)
- Update `CLAUDE.md` (if development workflow affected)
- Add examples to relevant documentation

**NEVER update `docs/target/system-vision.md`** — it is immutable.

---

## Common Tasks

### Add a New Connector

**Prerequisites:** Read `docs/target/architecture.md` Section 5 (Connector Architecture).

#### 1. Create Connector Class

```python
# engine/ingestion/connectors/wine_api_connector.py
from engine.ingestion.base import BaseConnector, IngestionResult
from pydantic import BaseModel

class WineAPIConnector(BaseConnector):
    """
    Connector for Wine API data source.

    CRITICAL: Connector is domain-blind. It fetches raw data only.
    Domain interpretation happens in Lens Application (Phase 2).
    """

    async def fetch(self, query: str, ctx: ExecutionContext) -> IngestionResult:
        """
        Fetch raw data from Wine API.

        Args:
            query: User query (opaque to connector)
            ctx: Execution context for logging and tracing

        Returns:
            IngestionResult with raw payload
        """
        # Fetch raw data from API
        raw_data = await self._call_api(query)

        return IngestionResult(
            connector_id="wine_api",
            raw_payload=raw_data,
            metadata={"source": "Wine API", "query": query}
        )
```

#### 2. Register Connector in Registry

```python
# engine/orchestration/registry.py
from engine.orchestration.types import ConnectorSpec, TrustTier

CONNECTOR_REGISTRY = {
    # ... existing connectors ...

    "wine_api": ConnectorSpec(
        connector_id="wine_api",
        trust_tier=TrustTier.MEDIUM,
        cost_per_call=0.005,  # $0.005 per call
        phase=2,  # Phase 2 connector (runs after primary sources)
        timeout=10000,  # 10 second timeout
        rate_limit=10,  # 10 calls per minute
    ),
}
```

#### 3. Add Adapter Mapping

```python
# engine/orchestration/adapters.py
from engine.ingestion.connectors.wine_api_connector import WineAPIConnector

CONNECTOR_ADAPTERS = {
    # ... existing adapters ...
    "wine_api": WineAPIConnector(),
}
```

#### 4. Write Tests

```python
# tests/engine/ingestion/connectors/test_wine_api_connector.py
import pytest
from engine.ingestion.connectors.wine_api_connector import WineAPIConnector

@pytest.mark.asyncio
async def test_wine_api_connector_fetch(mock_execution_context):
    """Test Wine API connector fetches raw data"""
    connector = WineAPIConnector()
    result = await connector.fetch("bordeaux wines", mock_execution_context)

    assert result.connector_id == "wine_api"
    assert result.raw_payload is not None
    assert "source" in result.metadata

def test_wine_api_registered_in_registry():
    """Test Wine API connector is registered"""
    from engine.orchestration.registry import CONNECTOR_REGISTRY
    assert "wine_api" in CONNECTOR_REGISTRY

    spec = CONNECTOR_REGISTRY["wine_api"]
    assert spec.trust_tier == TrustTier.MEDIUM
    assert spec.phase == 2
```

#### 5. Run Tests

```bash
pytest tests/engine/ingestion/connectors/test_wine_api_connector.py -v
pytest tests/engine/orchestration/test_registry.py -v
```

#### 6. Commit

```bash
git add engine/ingestion/connectors/wine_api_connector.py
git add engine/orchestration/registry.py
git add engine/orchestration/adapters.py
git add tests/engine/ingestion/connectors/test_wine_api_connector.py

git commit -m "$(cat <<'EOF'
feat(ingestion): add Wine API connector

Added new connector for Wine API data source. Connector is domain-blind
and fetches raw data only. Registered in orchestration registry with
Phase 2 priority (medium trust tier).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### Extend Entity Schema

**Prerequisites:** Read Schema Management section above.

#### 1. Edit YAML Schema

```yaml
# engine/config/schemas/entity.yaml
fields:
  # ... existing fields ...

  - name: canonical_dietary_preferences
    type: array
    items: string
    required: false
    description: "Multi-valued dimension for dietary classifications (e.g., vegan, gluten_free, halal)"
    # Populated in Phase 2 (Lens Application)
    # Values defined in lens canonical registry
```

#### 2. Validate Schema

```bash
python -m engine.schema.generate --validate
# Should pass validation
```

#### 3. Regenerate All Schemas

```bash
python -m engine.schema.generate --all
# Generates Python FieldSpecs, Prisma schemas, TypeScript interfaces
```

#### 4. Sync to Database

```bash
cd web
npx prisma db push  # Development
# OR
npx prisma migrate dev --name add_canonical_dietary_preferences  # Production
npx prisma generate
```

#### 5. Write Tests

```python
# tests/engine/schema/test_entity_schema.py
def test_canonical_dietary_preferences_field_exists():
    """Test new canonical dimension exists in schema"""
    from engine.schema.entity import ENTITY_FIELDS
    field_names = [f.name for f in ENTITY_FIELDS]
    assert "canonical_dietary_preferences" in field_names

def test_canonical_dietary_preferences_is_array():
    """Test new canonical dimension is array type"""
    from engine.schema.entity import ENTITY_FIELDS
    field = next(f for f in ENTITY_FIELDS if f.name == "canonical_dietary_preferences")
    assert field.type == "array"
    assert field.items == "string"
```

#### 6. Run Tests

```bash
pytest tests/engine/schema/test_entity_schema.py -v
```

#### 7. Commit

```bash
git add engine/config/schemas/entity.yaml
git add engine/schema/entity.py  # Generated file
git add web/prisma/schema.prisma  # Generated file
git add engine/prisma/schema.prisma  # Generated file
git add web/lib/types/generated/entity.ts  # Generated file
git add tests/engine/schema/test_entity_schema.py

git commit -m "$(cat <<'EOF'
feat(schema): add canonical_dietary_preferences dimension

Added new canonical dimension for dietary classifications. This is a
multi-valued array populated in Phase 2 (Lens Application). Values are
defined in lens canonical registry only.

Regenerated all schemas (Python FieldSpecs, Prisma, TypeScript).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### Create a New Lens

**Prerequisites:** Read `docs/target/system-vision.md` Section 3 (Architectural Boundaries).

#### 1. Create Lens Directory

```bash
mkdir -p engine/lenses/wine-discovery
```

#### 2. Create lens.yaml Configuration

```yaml
# engine/lenses/wine-discovery/lens.yaml
lens_id: wine-discovery
version: 1.0.0
description: "Wine Discovery vertical for finding wines, vineyards, and wine bars"

vocabulary:
  activity_keywords:
    - wine tasting
    - wine pairing
    - sommelier
    - vineyard
    - cellar

  location_indicators:
    - bordeaux
    - burgundy
    - napa
    - tuscany

  role_keywords:
    - sommelier
    - winemaker
    - viticulturist

connector_rules:
  wine_api:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [wine, vineyard, sommelier]

  google_places:
    priority: medium
    triggers:
      - type: any_keyword_match
        keywords: [wine bar, vineyard]

mapping_rules:
  - pattern: "(?i)red wine|cabernet|merlot|pinot noir"
    dimension: canonical_wine_types
    value: red_wine
    confidence: 0.95

  - pattern: "(?i)white wine|chardonnay|sauvignon blanc"
    dimension: canonical_wine_types
    value: white_wine
    confidence: 0.95

  - pattern: "(?i)bordeaux|burgundy"
    dimension: canonical_regions
    value: france
    confidence: 0.9

module_triggers:
  - when:
      dimension: canonical_wine_types
      values: [red_wine, white_wine]
    add_modules: [wine_profile]

canonical_values:
  red_wine:
    display_name: "Red Wine"
    seo_slug: "red-wine"
    icon: "wine-glass-red"

  white_wine:
    display_name: "White Wine"
    seo_slug: "white-wine"
    icon: "wine-glass-white"

  france:
    display_name: "France"
    seo_slug: "france"
    icon: "flag-france"
```

#### 3. Validate Lens Configuration

```python
# tests/engine/lenses/test_wine_discovery_lens.py
def test_wine_discovery_lens_loads():
    """Test wine-discovery lens loads without errors"""
    from engine.lenses.query_lens import load_lens
    lens = load_lens("wine-discovery")
    assert lens is not None
    assert lens.lens_id == "wine-discovery"

def test_wine_discovery_vocabulary():
    """Test wine-discovery vocabulary contains expected keywords"""
    from engine.lenses.query_lens import load_lens
    lens = load_lens("wine-discovery")
    assert "wine tasting" in lens.vocabulary.activity_keywords
    assert "sommelier" in lens.vocabulary.role_keywords

def test_wine_discovery_connector_rules():
    """Test wine-discovery connector routing rules"""
    from engine.lenses.query_lens import load_lens
    lens = load_lens("wine-discovery")
    assert "wine_api" in lens.connector_rules
    assert lens.connector_rules["wine_api"].priority == "high"
```

#### 4. Run Tests

```bash
pytest tests/engine/lenses/test_wine_discovery_lens.py -v
```

#### 5. Test End-to-End

```bash
# Run query with new lens
python -m engine.orchestration.cli run "bordeaux wines" --lens wine-discovery

# Inspect entity data
psql $DATABASE_URL -c "
SELECT entity_name, entity_class, canonical_wine_types, canonical_regions, modules
FROM entities
WHERE entity_name ILIKE '%bordeaux%';"
```

#### 6. Commit

```bash
git add engine/lenses/wine-discovery/lens.yaml
git add tests/engine/lenses/test_wine_discovery_lens.py

git commit -m "$(cat <<'EOF'
feat(lenses): add wine-discovery vertical lens

Added new lens for Wine Discovery vertical. Defines vocabulary for wine
terminology, connector routing rules for wine_api, mapping rules for
wine types and regions, and canonical value registry.

This demonstrates Invariant 3: Zero Engine Changes for New Verticals.
No engine code was modified to add this vertical.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### Add a Module Type

**Prerequisites:** Modules are namespaced JSONB structures defined in lens configs.

#### 1. Define Module in Lens Config

```yaml
# engine/lenses/wine-discovery/lens.yaml
modules:
  wine_profile:
    description: "Structured data for wine entities"
    fields:
      - name: grape_varieties
        type: array
        items: string
        description: "Grape varieties used (e.g., Cabernet Sauvignon, Merlot)"

      - name: vintage
        type: integer
        description: "Wine vintage year"

      - name: alcohol_percentage
        type: number
        description: "Alcohol by volume percentage"

      - name: tasting_notes
        type: object
        properties:
          aroma: string
          flavor: string
          finish: string
```

#### 2. Create Module Extractor

```python
# engine/extraction/modules/wine_profile_extractor.py
from pydantic import BaseModel, Field

class WineProfileModule(BaseModel):
    """
    Wine profile module structure.

    This module is attached in Phase 2 (Lens Application) when
    canonical_wine_types contains red_wine or white_wine.
    """
    grape_varieties: list[str] = Field(default_factory=list)
    vintage: int | None = None
    alcohol_percentage: float | None = None
    tasting_notes: dict[str, str] | None = None

def extract_wine_profile(raw_data: dict, ctx: ExecutionContext) -> WineProfileModule:
    """
    Extract wine profile module from raw observations.

    Args:
        raw_data: Raw observations from extractor
        ctx: Execution context

    Returns:
        WineProfileModule with populated fields
    """
    # Extract structured module data from raw observations
    return WineProfileModule(
        grape_varieties=raw_data.get("grape_varieties", []),
        vintage=raw_data.get("vintage"),
        alcohol_percentage=raw_data.get("alcohol_percentage"),
        tasting_notes=raw_data.get("tasting_notes"),
    )
```

#### 3. Write Tests

```python
# tests/engine/extraction/modules/test_wine_profile_extractor.py
def test_wine_profile_extraction(mock_execution_context):
    """Test wine profile module extraction"""
    raw_data = {
        "grape_varieties": ["Cabernet Sauvignon", "Merlot"],
        "vintage": 2018,
        "alcohol_percentage": 13.5,
        "tasting_notes": {
            "aroma": "Blackberry, vanilla, oak",
            "flavor": "Rich and full-bodied",
            "finish": "Long and smooth"
        }
    }

    module = extract_wine_profile(raw_data, mock_execution_context)

    assert module.grape_varieties == ["Cabernet Sauvignon", "Merlot"]
    assert module.vintage == 2018
    assert module.alcohol_percentage == 13.5
    assert module.tasting_notes["aroma"] == "Blackberry, vanilla, oak"
```

#### 4. Run Tests

```bash
pytest tests/engine/extraction/modules/test_wine_profile_extractor.py -v
```

#### 5. Commit

```bash
git add engine/lenses/wine-discovery/lens.yaml
git add engine/extraction/modules/wine_profile_extractor.py
git add tests/engine/extraction/modules/test_wine_profile_extractor.py

git commit -m "$(cat <<'EOF'
feat(modules): add wine_profile module type

Added wine_profile module for structured wine data. Module is attached
in Phase 2 (Lens Application) when canonical_wine_types contains wine
values. Module extractor populates grape varieties, vintage, alcohol
percentage, and tasting notes from raw observations.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Troubleshooting

### Common Issues

#### Schema Changes Not Reflected in Database

**Symptoms:**
- Database queries fail with "column does not exist"
- Prisma client errors about missing fields

**Solution:**
```bash
# Regenerate schemas
python -m engine.schema.generate --all

# Push to database
cd web
npx prisma db push

# Regenerate Prisma client
npx prisma generate

# Verify schema
npx prisma studio
```

#### Tests Pass But Entity Data Incorrect

**This is a FAILURE per system-vision.md Section 6.3.**

**Symptoms:**
- Unit tests pass
- Integration tests pass
- But database inspection shows incomplete or incorrect entity data

**Solution:**
1. **Inspect database:**
   ```bash
   psql $DATABASE_URL -c "
   SELECT entity_name, entity_class, canonical_activities, modules
   FROM entities
   WHERE entity_name ILIKE '%expected_entity%';"
   ```

2. **Identify gap:**
   - Missing canonical dimension values?
   - Empty modules?
   - Incorrect entity_class?

3. **Fix root cause:**
   - Check lens mapping rules
   - Check module triggers
   - Check extraction boundary (Phase 1 vs Phase 2)

4. **Add reality validation test:**
   ```python
   def test_entity_data_reality_validation():
       """Validate entity data in database (Gate 6: Reality Validation)"""
       # Run pipeline
       orchestrator.run("query", lens_id="lens_id")

       # Inspect database
       entity = db.query(Entity).filter(...).first()

       # Verify reality
       assert entity.canonical_activities == ["expected_value"]
       assert "expected_module" in entity.modules
   ```

#### Extractor Emitting Canonical Dimensions

**This violates the extraction boundary contract (architecture.md 4.2).**

**Symptoms:**
- Extractor directly emits `canonical_activities`, `canonical_roles`, etc.
- Modules attached in Phase 1 instead of Phase 2

**Solution:**
1. **Identify violation:**
   ```bash
   grep -r "canonical_" engine/extraction/extractors/
   ```

2. **Fix extractor to emit only primitives:**
   ```python
   # WRONG (Phase 1 extractor emitting canonical dimensions)
   return ExtractedEntity(
       entity_name="Example",
       canonical_activities=["tennis"]  # ❌ Violation
   )

   # RIGHT (Phase 1 extractor emitting only primitives)
   return ExtractedEntity(
       entity_name="Example",
       raw_categories=["tennis court", "racket sports"]  # ✅ Correct
   )
   ```

3. **Move interpretation to Phase 2:**
   - Add mapping rules to lens config
   - Lens Application stage will populate canonical dimensions

#### Domain Terms in Engine Code

**This violates Engine Purity (Invariant 1).**

**Symptoms:**
- Grep finds domain-specific terms in engine code
- Tests like `test_classifier_contains_no_domain_literals()` fail

**Solution:**
1. **Find violations:**
   ```bash
   grep -r "padel\|tennis\|wine\|restaurant" engine/
   ```

2. **Remove domain terms:**
   ```python
   # WRONG (domain-specific terms in engine)
   if "padel" in raw_categories:  # ❌ Violation
       return "place"

   # RIGHT (structural classification)
   if has_coordinates(data) and has_street_address(data):  # ✅ Correct
       return "place"
   ```

3. **Move semantics to lens:**
   - Add domain terms to lens vocabulary
   - Add mapping rules to lens config
   - Engine operates on opaque values only

#### Lens Validation Failing

**Symptoms:**
- Lens fails to load
- Error: "Invalid lens contract"
- Bootstrap validation fails

**Solution:**
1. **Validate lens structure:**
   ```bash
   python -m engine.lenses.validate wine-discovery
   ```

2. **Check common issues:**
   - YAML syntax errors
   - Missing required fields
   - Invalid connector references
   - Regex compilation errors
   - Orphaned canonical value references

3. **Fix and retry:**
   ```yaml
   # Fix YAML syntax
   # Add missing required fields
   # Verify connector exists in registry
   # Test regex patterns
   # Declare all canonical values in registry
   ```

#### Tests Slow During Development

**Solution:**
Use fast test subset:
```bash
# Run only fast tests
pytest -m "not slow"

# Mark slow tests with decorator
@pytest.mark.slow
def test_full_pipeline():
    pass
```

#### Coverage Too Low

**Symptoms:**
- `pytest --cov=engine` shows coverage <80%
- Uncovered lines in new code

**Solution:**
1. **Identify uncovered lines:**
   ```bash
   pytest --cov=engine --cov-report=html
   # Open htmlcov/index.html
   ```

2. **Write missing tests:**
   - Cover success and failure paths
   - Cover edge cases
   - Cover error handling

3. **Re-run coverage:**
   ```bash
   pytest --cov=engine --cov-report=term
   # Verify coverage >80%
   ```

---

## Environment Setup

### Required Environment Variables

```bash
# Backend (.env or environment)
ANTHROPIC_API_KEY=<your_key>      # For LLM extraction
SERPER_API_KEY=<your_key>         # For Serper connector
GOOGLE_PLACES_API_KEY=<your_key>  # For Google Places connector

# Web (web/.env)
DATABASE_URL=<supabase_postgres_url>
NEXT_PUBLIC_API_URL=http://localhost:3000
```

### Database Setup

```bash
# First time setup
cd web

# Generate Prisma client from schema
npx prisma generate

# Push schema to database (development)
npx prisma db push

# Create migration (production)
npx prisma migrate dev --name initial_schema

# Verify database
npx prisma studio  # Opens GUI at http://localhost:5555
```

### Verify Setup

```bash
# Backend
pytest -v  # All tests should pass

# Frontend
cd web
npm run build  # Should build without errors
npm run dev  # Should start on http://localhost:3000

# Database
psql $DATABASE_URL -c "SELECT 1;"  # Should return 1

# Pipeline
python -m engine.orchestration.cli run "test query" --lens edinburgh_finds
# Should execute without errors
```

---

## Additional Resources

- **Architectural Authority:** `docs/target/system-vision.md` — Immutable constitution
- **Runtime Specification:** `docs/target/architecture.md` — Concrete implementation
- **Development Methodology:** `docs/development-methodology.md` — Process and constraints
- **Implementation Plans:** `docs/plans/` — Phase-by-phase strategies
- **Schema Definitions:** `engine/config/schemas/*.yaml` — Data models
- **Test Examples:** `tests/engine/` — Testing patterns and fixtures

---

**End of Development Guide**
