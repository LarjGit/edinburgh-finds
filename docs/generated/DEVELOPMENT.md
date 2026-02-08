# Development Guide

**System:** Universal Entity Extraction Engine
**Reference Application:** Edinburgh Finds
**Last Updated:** 2026-02-08

---

## Table of Contents

1. [Development Methodology](#development-methodology)
2. [Development Workflow](#development-workflow)
3. [Code Standards](#code-standards)
4. [Testing Requirements](#testing-requirements)
5. [Commit Message Format](#commit-message-format)
6. [Branch Strategy](#branch-strategy)
7. [Pull Request Process](#pull-request-process)
8. [Quality Gates](#quality-gates)
9. [Architectural Review Process](#architectural-review-process)
10. [How to Add a Connector](#how-to-add-a-connector)
11. [How to Add a Lens](#how-to-add-a-lens)
12. [Debugging Tips](#debugging-tips)

---

## Development Methodology

This project follows **Reality-Based Incremental Alignment** - a strict methodology to prevent AI agent drift and ensure architectural compliance.

### Core Principles

**Reality-Based Planning**
- Read actual code before planning (never assume)
- Verify all assumptions explicitly
- Plan from what exists, not what "should" exist
- No mental models, no guessing

**Ultra-Small Work Units**
- Maximum 1-2 files changed per task
- Single architectural principle addressed
- Single function/class modified
- Single test validates the change

**User-Driven Validation**
- User approves micro-plan before execution (Checkpoint 1)
- User validates outcome after execution (Checkpoint 2)
- User sign-off required to mark complete
- Agent proposes, user decides

**Foundation-First Progression**
- Fix architectural violations before adding features
- Work from catalog of violations sorted by importance
- Each completed change is permanent foundation
- Never revisit completed work

**Golden Doc Supremacy**
- `docs/target/system-vision.md` = immutable constitution
- `docs/target/architecture.md` = runtime specification
- All decisions reference golden docs explicitly
- Conflicts → golden docs always win

### The Three Phases

**Phase 1: Foundation (Architectural Integrity)**
- Fix all architectural violations from golden docs
- Audit `docs/target/system-vision.md` Invariants 1-10
- Complete when: All Level-1 violations on validation entity runtime path resolved + bootstrap gates enforced

**Phase 2: Core Pipeline Implementation**
- Implement complete 11-stage orchestration pipeline (see `docs/target/architecture.md` Section 4.1)
- "One Perfect Entity" validates architecture correctness
- Complete when: All 11 stages implemented + validation entity flows end-to-end correctly

**Phase 3: System Expansion**
- Add more connectors, lenses, coverage
- New vertical lenses, performance optimization
- Foundation and pipeline never change in Phase 3

### The Micro-Iteration Process (8 Steps)

1. **Select Next Item** (Phase-aware, use Decision Logic)
2. **Code Reality Audit** (MANDATORY - read actual files, verify assumptions)
3. **Write Micro-Plan** (Half page max, golden doc reference, pass criteria)
4. **🛑 USER CHECKPOINT 1:** Approve micro-plan (1-2 min)
5. **Review Constraints** (Check all 8 constraints satisfied)
6. **Execute with TDD** (RED → GREEN → Refactor)
7. **Validate Against Golden Docs** (Manual verification)
8. **🛑 USER CHECKPOINT 2:** Validate result (2-3 min)
9. **Mark Complete & Commit** (After user approval only)
10. **Compounding** (Capture pattern candidates, doc clarity improvements, future pitfalls)

### The 8 Mandatory Constraints

1. **Golden Doc Supremacy:** Every change references specific golden doc section
2. **Reality-Based Planning:** MUST read actual code files before planning
3. **Scope Limits:** Max 2 files changed (excluding tests), max 100 lines
4. **Test-First Validation:** Test written BEFORE implementation
5. **Catalog Fidelity:** Only work on items in catalog
6. **Foundation Permanence:** Completed changes NEVER revisited
7. **User Validation Required:** Agent cannot mark complete without user approval
8. **Extraction Helper Purity:** Helpers only validate/normalize, never interpret

### The 6 Validation Gates

All changes must pass ALL gates:

1. **Golden Doc Alignment:** Change upholds stated principle
2. **Test Validation:** Tests pass, >80% coverage, reference principle
3. **Code Reality Check:** Changed code matches plan, no drift
4. **Zero Assumptions:** All code exists, imports resolve, tests prove it works
5. **Catalog Updated:** Item marked complete with date + commit hash + executable proof
6. **Reality Validation:** Database inspection shows correct entity data (for end-to-end work)

**Critical Rule:** Tests that pass but produce incorrect entity data = FAILURE

### Getting Started

**Before starting ANY work:**

1. Read `docs/development-methodology.md` (15 min)
2. Check if `docs/progress/audit-catalog.md` exists
3. If exists: Follow Decision Logic to select next item
4. If not exists: Run initial audit to create catalog

**For detailed methodology:** See `docs/development-methodology.md`

---

## Development Workflow

### TDD Cycle (Red → Green → Refactor)

This project follows strict **Test-Driven Development**:

**1. Red (Write Failing Test First)**
```python
def test_classifier_contains_no_domain_literals():
    """Validates Invariant 1: Engine Purity"""
    source = inspect.getsource(entity_classifier)
    forbidden = ["padel", "tennis", "wine", "restaurant"]
    for term in forbidden:
        assert term.lower() not in source.lower()
```

**2. Confirm Test Fails**
```bash
pytest tests/engine/extraction/test_entity_classifier.py::test_classifier_contains_no_domain_literals
# Should fail with current code (RED)
```

**3. Green (Implement Minimum Code to Pass)**
- Remove hardcoded domain terms
- Replace with structural logic
- Run test until it passes

**4. Refactor (Improve While Keeping Tests Green)**
- Improve code quality
- Maintain test passing

**5. Run Full Test Suite**
```bash
pytest engine/extraction/
# Ensure no regressions
```

### Daily Development Commands

**Backend (Python Engine)**
```bash
# Run all tests
pytest

# Run fast tests only (excludes @pytest.mark.slow)
pytest -m "not slow"

# Generate coverage report (target: >80%)
pytest --cov=engine --cov-report=html

# Run specific module tests
pytest engine/orchestration/
```

**Frontend (Next.js)**
```bash
cd web

# Start dev server
npm run dev  # http://localhost:3000

# Production build
npm run build

# Linting
npm run lint
```

**Schema Management (CRITICAL)**
```bash
# YAML schemas are the single source of truth
# Location: engine/config/schemas/*.yaml

# Validate schemas before committing
python -m engine.schema.generate --validate

# Regenerate all derived schemas (Python, Prisma, TypeScript)
python -m engine.schema.generate --all

# When you modify a YAML schema:
# 1. Edit engine/config/schemas/<entity>.yaml
# 2. Run: python -m engine.schema.generate --all
# 3. Generated files are marked "DO NOT EDIT" - never modify them directly
```

**Data Pipeline Commands**
```bash
# Ingestion (fetch raw data)
python -m engine.ingestion.cli run --query "padel courts Edinburgh"

# Extraction (structured data from raw)
python -m engine.extraction.cli single <raw_ingestion_id>
python -m engine.extraction.cli source serper --limit 10

# Orchestration (intelligent multi-source query)
python -m engine.orchestration.cli run "padel clubs in Edinburgh"
```

---

## Code Standards

### Engine Purity (CRITICAL)

**The engine is completely domain-blind. All domain knowledge lives in Lens YAML configs.**

**❌ WRONG:**
```python
# Hardcoded domain-specific terms in engine code
if entity_type == "Venue":  # ❌ Vertical-specific
    ...

if "padel" in raw_categories:  # ❌ Domain semantics
    return "place"
```

**✅ RIGHT:**
```python
# Universal entity classes
if entity.entity_class == "place":  # ✅ Universal
    # Use lenses/modules for vertical interpretation

# Structural classification (not semantic)
if has_street_address and has_latitude:  # ✅ Structural signals
    return "place"
```

**Enforcement:**
- CI runs `bash scripts/check_engine_purity.sh`
- Tests: `pytest tests/engine/test_purity.py -v`

### Extraction Contract (CRITICAL)

**Phase 1 - Source Extraction (extractors):**
- Outputs: Schema primitives only (`entity_name`, `latitude`, `street_address`, `phone`, `website_url`)
- Outputs: Raw observations (`raw_categories`, `description`, connector-native fields)
- **FORBIDDEN:** `canonical_*` dimensions, `modules`, lens-derived semantics

**Phase 2 - Lens Application:**
- Inputs: Primitives + raw observations from Phase 1
- Outputs: `canonical_*` dimensions + populated `modules`
- Execution: Generic, domain-blind, metadata-driven

**Extractors must NEVER emit:**
- `canonical_activities`
- `canonical_roles`
- `canonical_place_types`
- `canonical_access`
- `modules.*`

### Naming Conventions

**Schema Primitives (Universal):**
- ✅ `entity_name`, `latitude`, `longitude`, `street_address`, `city`, `postcode`
- ✅ `phone`, `email`, `website_url`
- ❌ NEVER: `location_*`, `contact_*`, `address_*`

**Entity Classes (Generic):**
- ✅ `place`, `person`, `organization`, `event`, `thing`
- ❌ NEVER: `Venue`, `Facility`, domain-specific types

**Canonical Dimensions (Lens-Owned):**
- `canonical_activities` (TEXT[])
- `canonical_roles` (TEXT[])
- `canonical_place_types` (TEXT[])
- `canonical_access` (TEXT[])

**Modules (Namespaced JSON):**
- `modules.{namespace}.*`
- Example: `modules.sports_facility.padel_courts`

### Python Style

- PEP 8 compliance
- Type hints for function signatures
- Pydantic models for validation
- Docstrings for all public functions/classes
- Max line length: 100 characters

### TypeScript Style

- Strict mode enabled
- No `any` types (use `unknown` and narrow)
- Prefer functional components (React)
- ESLint rules enforced

---

## Testing Requirements

### Coverage Target

**Minimum: >80% coverage for all new code**

```bash
# Generate HTML coverage report
pytest --cov=engine --cov-report=html

# View report
open htmlcov/index.html
```

### Test Categories

**Unit Tests**
- Every module must have corresponding tests
- Mock external dependencies (API calls, LLM calls)
- Test both success and failure cases
- Use fixtures for common setup

**Integration Tests**
- Test complete data flows (ingest → extract → dedupe → merge)
- Verify database transactions
- Snapshot testing for extraction outputs

**Slow Tests**
```python
import pytest

@pytest.mark.slow
def test_full_pipeline_integration():
    # Tests >1 second marked as slow
    pass
```

Run fast tests only:
```bash
pytest -m "not slow"
```

### Test Naming

```python
# Good test names
def test_classifier_preserves_engine_purity():
    """Validates Invariant 1: Engine Purity"""
    pass

def test_extractor_emits_only_primitives():
    """Validates Phase 1 extraction contract"""
    pass
```

### Architectural Compliance Tests

**Required tests for all engine code:**

1. **Engine Purity Test**
```python
def test_no_domain_literals_in_module():
    source = inspect.getsource(my_module)
    forbidden = ["padel", "tennis", "wine", "restaurant"]
    for term in forbidden:
        assert term.lower() not in source.lower()
```

2. **Extraction Boundary Test**
```python
def test_extractor_emits_only_primitives():
    result = extractor.extract(raw_data)
    assert "canonical_activities" not in result
    assert "modules" not in result
```

3. **Determinism Test**
```python
def test_deterministic_output():
    result1 = process(input_data)
    result2 = process(input_data)
    assert result1 == result2
```

---

## Commit Message Format

### Conventional Commits

```
<type>(<scope>): <description>

[optional body]

[optional footer]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic changes)
- `refactor`: Code refactoring (no functional changes)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

**Feature:**
```
feat(extraction): add lens-driven canonical dimension population

Implements Phase 2 extraction boundary per architecture.md 4.2.
Extractors now emit only primitives, lens application populates
canonical dimensions via mapping rules.

Validates: architecture.md Section 4.2 (Extraction Contract)
Catalog Item: EB-001

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Fix:**
```
fix(extraction): remove domain terms from classifier (Invariant 1)

Replaced hardcoded domain-specific category checks with structural
classification rules. Classifier now uses only universal type
indicators, preserving engine purity.

Validates: system-vision.md Invariant 1 (Engine Purity)
Catalog Item: EP-001

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Documentation:**
```
docs(architecture): clarify extraction boundary contract

Added explicit examples of Phase 1 vs Phase 2 outputs.
Clarifies that extractors must never emit canonical_* fields.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Commit Message Requirements

1. **Golden Doc Reference:** Cite specific section (e.g., "system-vision.md Invariant 1")
2. **Catalog Item:** Reference catalog ID if applicable (e.g., "Catalog Item: EP-001")
3. **Co-Author:** Always include Claude co-author line
4. **Description:** Focus on "why" not "what" (code shows "what")

---

## Branch Strategy

### Main Branches

- **`main`**: Production-ready code (protected)
- **`develop`**: Integration branch for features (optional)

### Feature Branches

```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feat/extraction-lens-application

# Work in micro-iterations (commit after each micro-iteration)
git add <files>
git commit -m "fix(extraction): remove domain terms from classifier"

# Push when ready for PR
git push origin feat/extraction-lens-application
```

### Branch Naming

- `feat/<description>` - New features
- `fix/<description>` - Bug fixes
- `docs/<description>` - Documentation updates
- `refactor/<description>` - Code refactoring

**Examples:**
- `feat/extraction-lens-application`
- `fix/engine-purity-classifier`
- `docs/architecture-extraction-contract`

### Protection Rules

**`main` branch:**
- Require PR approval
- Require all tests passing (CI)
- Require architectural validation checks passing
- No direct commits allowed

---

## Pull Request Process

### 1. Create PR from Template

Use `.github/pull_request_template.md`:

```markdown
## Description
Brief description of changes

## Type of Change
- [x] Bug fix / New feature / Documentation / Refactoring

## Architectural Validation Checklist
- [x] Engine Purity checks pass
- [x] Lens Contract validation passes
- [x] Module Composition tests pass
- [x] All tests pass

## Documentation
- [x] README.md updated (if applicable)
- [x] ARCHITECTURE.md updated (if applicable)

## Related Issues
Closes #123
```

### 2. Run Pre-PR Checklist

**Before opening PR:**

```bash
# 1. Schema validation
python -m engine.schema.generate --validate

# 2. Run all tests
pytest

# 3. Check coverage
pytest --cov=engine

# 4. Lint frontend (if applicable)
cd web && npm run lint

# 5. Engine purity checks
bash scripts/check_engine_purity.sh

# 6. Verify no generated files manually edited
git diff engine/schema/  # Should be empty or regenerated only
git diff web/prisma/schema.prisma  # Should be empty or regenerated only
```

### 3. PR Review Requirements

**Reviewers must verify:**

1. **Architectural Compliance**
   - No domain terms in engine code
   - Extraction boundary respected
   - Golden doc references correct

2. **Test Quality**
   - Tests explicitly validate architectural principles
   - Coverage >80%
   - All tests pass

3. **Code Quality**
   - Follows style guide
   - No "extra" changes beyond scope
   - Generated files not manually edited

4. **Documentation**
   - YAML schemas updated if applicable
   - Inline comments for complex logic
   - Architectural docs updated if needed

### 4. CI Validation

GitHub Actions runs:
- `scripts/check_engine_purity.sh`
- `pytest tests/ -v --cov`
- Specific architectural tests (lens validation, deduplication, etc.)

See `.github/workflows/tests.yml` for full CI pipeline.

### 5. Merge Requirements

**All must pass:**
- ✅ CI tests passing
- ✅ Engine purity checks passing
- ✅ PR approved by reviewer
- ✅ No merge conflicts
- ✅ Architectural validation checklist complete

**Merge strategy:**
- Use "Squash and merge" for small PRs
- Use "Create merge commit" for phase transitions
- Never force push to `main`

---

## Quality Gates

### Before Committing

**ALL required:**

1. **Schema Validation**
   ```bash
   python -m engine.schema.generate --validate
   ```

2. **Run Tests**
   ```bash
   pytest  # Backend
   cd web && npm run build  # Frontend
   ```

3. **Check Linting**
   ```bash
   cd web && npm run lint
   ```

4. **Verify Coverage**
   ```bash
   pytest --cov=engine  # Should be >80%
   ```

5. **Update Documentation**
   - If implementation affects architecture, update golden docs
   - If new feature, update README
   - If schema change, regenerate all schemas

### Before Opening PR

**Additional checks:**

6. **Engine Purity**
   ```bash
   bash scripts/check_engine_purity.sh
   ```

7. **Architectural Tests**
   ```bash
   pytest tests/lenses/test_validator.py -v
   pytest tests/modules/test_composition.py -v
   ```

8. **Manual Testing**
   - Test validation entity flows correctly
   - Inspect database for correct entity data
   - Verify no regressions

### CI Quality Gates

**GitHub Actions enforces:**
- All tests passing
- Engine purity checks passing
- Lens validation tests passing
- Deduplication tests passing
- Module composition tests passing

**If CI fails → PR cannot merge**

---

## Architectural Review Process

### When Required

**Architectural review required for:**
- Changes to `engine/` core modules
- Changes to extraction boundary
- Changes to lens system
- Changes to schema definitions
- New connectors or lenses

**NOT required for:**
- Frontend-only changes
- Documentation updates
- Test additions (no logic changes)

### Review Criteria

**Reviewers check against immutable invariants (system-vision.md):**

1. **Engine Purity (Invariant 1)**
   - No domain-specific terms in engine code?
   - All domain logic in lens configs?

2. **Lens Ownership (Invariant 2)**
   - All semantics in lens YAML configs?
   - No hardcoded domain logic?

3. **Zero Engine Changes (Invariant 3)**
   - Could a new vertical be added without changing this code?

4. **Determinism (Invariant 4)**
   - Same inputs + lens → identical outputs?
   - No randomness, time-based logic, or iteration-order dependence?

5. **Canonical Registry Authority (Invariant 5)**
   - All canonical values declared in registry?

6. **Fail-Fast Validation (Invariant 6)**
   - Invalid contracts fail at bootstrap?
   - No silent fallbacks?

7. **Schema-Bound LLM (Invariant 7)**
   - LLMs produce only validated structured output?

8. **No Translation Layers (Invariant 8)**
   - Universal schema names used end-to-end?

9. **Engine Independence (Invariant 9)**
   - Engine useful without specific vertical?

10. **No Reference-Lens Exceptions (Invariant 10)**
    - Edinburgh Finds gets no special treatment?

### Review Checklist

**Reviewer completes:**

```markdown
- [ ] Read relevant sections of system-vision.md and architecture.md
- [ ] Verify golden doc references are correct
- [ ] Check all 10 invariants preserved
- [ ] Run tests locally
- [ ] Inspect database for correct entity data (if end-to-end)
- [ ] Verify no "extra" changes beyond stated scope
- [ ] Check that generated files not manually edited
- [ ] Approve OR request changes with specific golden doc citations
```

### Rejection Criteria

**PR must be rejected if:**
- Violates any of the 10 immutable invariants
- Introduces domain terms in engine code
- Extractors emit canonical dimensions or modules
- Non-deterministic behavior added
- Silent fallbacks or hidden defaults introduced
- Tests pass but entity data incorrect
- Golden doc references incorrect or missing

**When rejecting:**
- Cite specific invariant violated
- Point to exact line of code
- Reference golden doc section
- Suggest alternative approach aligned with architecture

---

## How to Add a Connector

**Goal:** Add a new data source to the ingestion system.

### Step 1: Add to Orchestration Registry

**File:** `engine/orchestration/registry.py`

```python
from engine.orchestration.registry import ConnectorSpec

connectors = {
    "new_connector": ConnectorSpec(
        name="new_connector",
        cost=0.5,  # Cost per query (arbitrary units)
        trust=0.8,  # Trust score (0.0-1.0)
        phase=1,    # Execution phase (1=primary, 2=secondary)
        timeout_seconds=30,  # Request timeout
    ),
    # ... existing connectors
}
```

**Cost guidelines:**
- API with per-query charges: actual cost
- Free APIs: relative computational cost (0.1-0.5)
- Slow APIs: higher cost to deprioritize

**Trust guidelines:**
- Official sources (Google Places): 0.9-1.0
- Verified aggregators (Serper): 0.7-0.9
- Community sources (OSM): 0.5-0.7
- Unverified sources: 0.3-0.5

**Phase guidelines:**
- Phase 1: Primary sources (fast, reliable)
- Phase 2: Secondary sources (slower, supplementary)

### Step 2: Create Connector Class

**File:** `engine/ingestion/connectors/new_connector.py`

```python
from typing import Optional, Dict, Any
from engine.ingestion.connectors.base import BaseConnector

class NewConnector(BaseConnector):
    """
    Connector for [Data Source Name]

    Fetches [type of data] from [source URL/API]
    """

    async def fetch(self, query: str) -> Dict[str, Any]:
        """
        Fetch raw data from connector.

        Args:
            query: Search query string

        Returns:
            Dict with connector-specific structure
        """
        # Implementation
        response = await self._make_request(query)
        return self._normalize_response(response)

    def _normalize_response(self, response: Any) -> Dict[str, Any]:
        """Normalize connector-specific response to common structure"""
        return {
            "results": [...],
            "metadata": {...},
        }
```

**Must implement:**
- `fetch(query: str) -> Dict[str, Any]`
- Async execution
- Error handling (raise exceptions, don't return None)
- Response normalization

### Step 3: Create Extractor

**File:** `engine/extraction/extractors/new_connector_extractor.py`

```python
from typing import Dict, Any
from engine.extraction.extractors.base import BaseExtractor

class NewConnectorExtractor(BaseExtractor):
    """
    Extracts structured data from NewConnector raw results.

    CRITICAL: Must emit ONLY schema primitives + raw observations.
    FORBIDDEN: canonical_* fields, modules
    """

    def extract(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract schema primitives from raw data.

        Returns:
            Dict with ONLY:
            - Schema primitives (entity_name, latitude, street_address, etc.)
            - Raw observations (raw_categories, description)
        """
        return {
            # Schema primitives only
            "entity_name": raw_data.get("name"),
            "latitude": raw_data.get("lat"),
            "longitude": raw_data.get("lon"),
            "street_address": raw_data.get("address"),
            "phone": raw_data.get("phone"),
            "website_url": raw_data.get("website"),

            # Raw observations (opaque)
            "raw_categories": raw_data.get("categories", []),
            "description": raw_data.get("description"),
        }
```

**Critical rules:**
- Emit ONLY schema primitives (see architecture.md 8.2)
- Emit ONLY raw observations (opaque arrays/strings)
- NEVER emit: `canonical_*` fields, `modules`
- Helpers may ONLY validate/normalize, never interpret

### Step 4: Add Adapter Mapping

**File:** `engine/orchestration/adapters.py`

```python
from engine.ingestion.connectors.new_connector import NewConnector

CONNECTOR_ADAPTERS = {
    "new_connector": NewConnector,
    # ... existing adapters
}
```

### Step 5: Write Tests

**File:** `tests/engine/orchestration/test_registry.py`

```python
def test_new_connector_registered():
    """Test new connector exists in registry"""
    from engine.orchestration.registry import connectors
    assert "new_connector" in connectors

def test_new_connector_spec_valid():
    """Test new connector spec is valid"""
    from engine.orchestration.registry import connectors
    spec = connectors["new_connector"]
    assert 0 < spec.cost < 10
    assert 0 <= spec.trust <= 1.0
    assert spec.phase in [1, 2]
    assert spec.timeout_seconds > 0
```

**File:** `tests/engine/extraction/test_new_connector_extractor.py`

```python
def test_extractor_emits_only_primitives():
    """Test extractor respects extraction boundary (Phase 1)"""
    extractor = NewConnectorExtractor()
    result = extractor.extract(raw_data)

    # Must NOT emit canonical dimensions
    assert "canonical_activities" not in result
    assert "canonical_roles" not in result
    assert "canonical_place_types" not in result
    assert "canonical_access" not in result

    # Must NOT emit modules
    assert "modules" not in result

    # MUST emit schema primitives
    assert "entity_name" in result
```

### Step 6: Update Lens Routing Rules

**File:** `engine/lenses/<lens_id>/lens.yaml`

```yaml
connector_rules:
  new_connector:
    priority: high  # high, medium, low
    triggers:
      - type: any_keyword_match
        keywords: [specific, keywords, for, this, source]
```

**Trigger types:**
- `any_keyword_match`: Query contains any of these keywords
- `all_keywords_match`: Query contains all of these keywords
- `location_context`: Query contains location indicators

### Checklist

- [ ] Connector added to `engine/orchestration/registry.py`
- [ ] Connector class created in `engine/ingestion/connectors/`
- [ ] Extractor created in `engine/extraction/extractors/`
- [ ] Extractor emits ONLY primitives (no canonical_*, no modules)
- [ ] Adapter mapping added to `engine/orchestration/adapters.py`
- [ ] Tests written for registry, connector, extractor
- [ ] Lens routing rules updated
- [ ] All tests pass (`pytest`)
- [ ] Engine purity checks pass (`bash scripts/check_engine_purity.sh`)

---

## How to Add a Lens

**Goal:** Add a new vertical (e.g., Wine Discovery, Restaurant Finder).

**Critical Principle:** Adding a new vertical should require ZERO engine code changes - only a new Lens YAML configuration file.

### Step 1: Create Lens Directory

```bash
mkdir -p engine/lenses/<lens_id>
touch engine/lenses/<lens_id>/lens.yaml
```

**Lens ID conventions:**
- Lowercase, underscore-separated
- Examples: `edinburgh_finds`, `wine_discovery`, `restaurant_finder`

### Step 2: Define Lens Configuration

**File:** `engine/lenses/<lens_id>/lens.yaml`

```yaml
# Lens metadata
id: wine_discovery
version: "1.0"
description: "Wine discovery and tasting venues"

# Vocabulary (for query feature detection)
vocabulary:
  activity_keywords:
    - wine
    - tasting
    - vineyard
    - sommelier
    - cellar

  location_indicators:
    - winery
    - vineyard
    - tasting room

  role_keywords:
    - sommelier
    - winemaker
    - vintner

# Connector routing rules
connector_rules:
  google_places:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [wine, tasting, winery]

  serper:
    priority: medium
    triggers:
      - type: any_keyword_match
        keywords: [wine, vineyard]

# Mapping rules (raw observations → canonical dimensions)
mapping_rules:
  # canonical_activities
  - pattern: "(?i)wine.*tasting"
    dimension: canonical_activities
    value: wine_tasting
    confidence: 0.95

  - pattern: "(?i)vineyard.*tour"
    dimension: canonical_activities
    value: vineyard_tour
    confidence: 0.9

  # canonical_place_types
  - pattern: "(?i)winery|vineyard"
    dimension: canonical_place_types
    value: winery
    confidence: 0.95

  # canonical_roles
  - pattern: "(?i)sommelier"
    dimension: canonical_roles
    value: sommelier
    confidence: 0.95

# Module triggers (when to attach domain modules)
module_triggers:
  - when:
      dimension: canonical_activities
      values: [wine_tasting]
    add_modules: [wine_venue]

  - when:
      dimension: canonical_place_types
      values: [winery]
    add_modules: [wine_venue]

# Canonical values registry
canonical_values:
  wine_tasting:
    display_name: "Wine Tasting"
    seo_slug: "wine-tasting"
    icon: "wine-glass"

  vineyard_tour:
    display_name: "Vineyard Tour"
    seo_slug: "vineyard-tour"
    icon: "grapes"

  winery:
    display_name: "Winery"
    seo_slug: "winery"
    icon: "building"

  sommelier:
    display_name: "Sommelier"
    seo_slug: "sommelier"
    icon: "person"
```

**Critical sections:**

1. **vocabulary:** For query feature detection (orchestration planning)
2. **connector_rules:** Which connectors to use for this vertical
3. **mapping_rules:** Raw observations → canonical dimensions (regex patterns)
4. **module_triggers:** When to attach domain-specific modules
5. **canonical_values:** Display metadata for all canonical values

### Step 3: Add Domain Module Schema (Optional)

**If vertical needs custom structured data:**

**File:** `engine/config/schemas/modules/wine_venue.yaml`

```yaml
module_name: wine_venue
description: "Wine venue specific attributes"

fields:
  varietals:
    type: array
    items: string
    description: "Wine varietals available"

  tasting_fee:
    type: object
    properties:
      amount: number
      currency: string
    description: "Tasting fee"

  cellar_tours:
    type: boolean
    description: "Offers cellar tours"
```

**Then regenerate schemas:**
```bash
python -m engine.schema.generate --all
```

### Step 4: Validate Lens Configuration

**Run lens validation:**
```bash
pytest tests/lenses/test_validator.py -v
```

**Validation checks:**
- All facets reference valid dimensions
- All mapping_rules reference valid canonical values
- No duplicate value keys
- All module triggers reference valid modules
- All connector_rules reference registered connectors

### Step 5: Test End-to-End

**Run test query:**
```bash
python -m engine.orchestration.cli run "wine tasting venues in Napa" --lens wine_discovery
```

**Inspect database:**
```bash
psql $DATABASE_URL -c "
SELECT entity_name, entity_class, canonical_activities, canonical_place_types, modules
FROM entities
WHERE canonical_activities && ARRAY['wine_tasting']
LIMIT 5;"
```

**Validate:**
- Entity exists in database
- `canonical_activities` contains `wine_tasting`
- `canonical_place_types` contains `winery`
- `modules.wine_venue` populated (if module defined)

### Step 6: Write Tests

**File:** `tests/lenses/test_wine_discovery_lens.py`

```python
def test_wine_discovery_lens_loads():
    """Test wine discovery lens loads without errors"""
    from engine.lenses.query_lens import load_lens
    lens = load_lens("wine_discovery")
    assert lens is not None

def test_wine_vocabulary_detected():
    """Test wine keywords detected in query"""
    from engine.orchestration.query_features import extract_features
    features = extract_features("wine tasting venues", lens_id="wine_discovery")
    assert "wine" in features.activity_keywords

def test_wine_mapping_rules_applied():
    """Test wine mapping rules populate canonical dimensions"""
    # Integration test: raw observation → canonical dimension
    pass
```

### Checklist

- [ ] Lens directory created: `engine/lenses/<lens_id>/`
- [ ] Lens configuration written: `lens.yaml`
- [ ] All 5 critical sections defined (vocabulary, connector_rules, mapping_rules, module_triggers, canonical_values)
- [ ] Domain module schema added (if needed): `engine/config/schemas/modules/<module>.yaml`
- [ ] Schemas regenerated: `python -m engine.schema.generate --all`
- [ ] Lens validation passes: `pytest tests/lenses/test_validator.py -v`
- [ ] End-to-end test passes (query → database inspection)
- [ ] Tests written for lens loading, vocabulary, mapping
- [ ] NO engine code changes required (zero engine changes = success)

### Common Pitfalls

1. **Forgetting to register canonical values**
   - Every value in `mapping_rules` must be in `canonical_values`

2. **Incorrect regex patterns**
   - Use `(?i)` for case-insensitive matching
   - Test patterns thoroughly

3. **Missing connector_rules**
   - At least one connector must have `priority: high`

4. **Module triggers not matching**
   - `module_triggers.when` must reference canonical values that actually exist

5. **Modifying engine code**
   - If you modified engine code, the lens architecture is broken
   - Vertical logic belongs in YAML only

---

## Debugging Tips

### Common Issues

#### 1. Tests Failing: "Domain term in engine code"

**Symptom:**
```
AssertionError: Found forbidden term 'padel' in engine/extraction/classifier.py
```

**Solution:**
- Remove hardcoded domain terms
- Replace with structural classification or lens-driven logic
- See CLAUDE.md "Common Gotchas #4"

**Check:**
```bash
bash scripts/check_engine_purity.sh
pytest tests/engine/test_purity.py -v
```

---

#### 2. Extractor Emitting Canonical Dimensions

**Symptom:**
```
AssertionError: Extractor emitted forbidden field 'canonical_activities'
```

**Solution:**
- Extractors must emit ONLY primitives (Phase 1)
- Remove `canonical_*` fields from extractor output
- Lens application (Phase 2) populates canonical dimensions

**Check extraction boundary:**
```python
def test_extractor_emits_only_primitives():
    result = extractor.extract(raw_data)
    assert "canonical_activities" not in result
    assert "modules" not in result
```

---

#### 3. Schema Changes Not Reflected

**Symptom:**
- Modified YAML schema but changes not visible
- TypeScript/Prisma still uses old schema

**Solution:**
```bash
# Regenerate all schemas
python -m engine.schema.generate --all

# Verify generated files updated
git diff engine/schema/
git diff web/prisma/schema.prisma
```

**NEVER edit generated files directly** (marked "DO NOT EDIT")

---

#### 4. Lens Not Loading

**Symptom:**
```
LensNotFoundError: Lens 'wine_discovery' not found
```

**Solutions:**
- Check lens directory exists: `engine/lenses/wine_discovery/`
- Check lens.yaml exists and valid YAML
- Run validation: `pytest tests/lenses/test_validator.py -v`
- Check lens ID matches directory name

---

#### 5. Database Shows Incorrect Entity Data

**Symptom:**
- Tests pass but entity in database has wrong data
- Missing canonical dimensions
- Modules not populated

**Critical:** Tests passing with incorrect DB data = FAILURE (system-vision.md 6.3)

**Solution:**
- Inspect actual database:
  ```bash
  psql $DATABASE_URL -c "SELECT * FROM entities WHERE entity_name ILIKE '%search%';"
  ```
- Trace data flow: Raw ingestion → Extraction → Lens application → Entity
- Verify lens mapping rules applied
- Check module triggers fired

---

#### 6. Slow Tests

**Symptom:**
```
pytest taking >5 minutes to complete
```

**Solution:**
```bash
# Run fast tests only (excludes @pytest.mark.slow)
pytest -m "not slow"

# Mark slow tests
@pytest.mark.slow
def test_full_pipeline_integration():
    pass
```

---

#### 7. Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'engine.extraction'
```

**Solution:**
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or use pytest from project root
cd /path/to/edinburgh_finds
pytest
```

---

#### 8. CI Passing Locally But Failing on GitHub

**Solution:**
- Check GitHub Actions logs: `.github/workflows/tests.yml`
- Verify all dependencies in `engine/requirements.txt`
- Check environment variables set in CI
- Run tests in clean environment:
  ```bash
  # Create fresh venv
  python -m venv test_env
  source test_env/bin/activate
  pip install -r engine/requirements.txt
  pytest
  ```

---

### Debugging Tools

**pytest options:**
```bash
# Verbose output
pytest -v

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Run specific test
pytest tests/engine/extraction/test_classifier.py::test_no_domain_literals

# Show coverage
pytest --cov=engine --cov-report=term-missing

# Show slowest tests
pytest --durations=10
```

**Database inspection:**
```bash
# Connect to database
psql $DATABASE_URL

# Show all entities
SELECT entity_name, entity_class, canonical_activities FROM entities LIMIT 10;

# Find entities by keyword
SELECT * FROM entities WHERE entity_name ILIKE '%padel%';

# Check canonical dimensions populated
SELECT COUNT(*) FROM entities WHERE cardinality(canonical_activities) > 0;
```

**Schema debugging:**
```bash
# Validate schemas
python -m engine.schema.generate --validate

# Show schema diff
git diff engine/config/schemas/

# Regenerate schemas
python -m engine.schema.generate --all
```

**Lens debugging:**
```bash
# Validate lens config
pytest tests/lenses/test_validator.py -v

# Test query routing
python -m engine.orchestration.cli run "test query" --lens <lens_id> --dry-run
```

---

### Getting Help

**Before asking for help:**
1. Read relevant section of `docs/target/system-vision.md`
2. Read relevant section of `docs/target/architecture.md`
3. Check `docs/development-methodology.md` for process questions
4. Search existing tests for examples
5. Run full test suite to isolate issue

**When asking for help:**
- Cite specific golden doc section
- Show actual code causing issue
- Share full error traceback
- Describe what you've tried
- Include test output

**Resources:**
- Architectural Constitution: `docs/target/system-vision.md`
- Runtime Specification: `docs/target/architecture.md`
- Development Methodology: `docs/development-methodology.md`
- Implementation Plans: `docs/plans/`
- Test Examples: `tests/engine/`

---

## Summary

This development guide ensures:
- **Architectural compliance** through strict quality gates
- **Reality-based development** via mandatory code audits
- **Incremental progress** with ultra-small work units
- **User control** via two checkpoints per micro-iteration
- **Foundation permanence** with no revisiting of completed work

**Core principle:** The engine is domain-blind. All domain knowledge lives in Lens YAML configs. Adding a new vertical requires ZERO engine code changes.

**Golden docs are immutable:** `docs/target/system-vision.md` defines what must remain true. Consult it for ANY architectural decision.

**Questions?** Read `docs/development-methodology.md` for detailed process guidance.
