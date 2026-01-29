# Lens Mapping and Module Extraction Design

**Date:** 2026-01-29
**Status:** Design Approved
**Goal:** Achieve "One Perfect Entity" validation by implementing lens-driven canonical dimension population and module extraction

---

## Problem Statement

The current codebase has a 60% complete pipeline:
- ✅ Ingestion → Extraction (primitives) → Classification → Merge → Persistence works
- ❌ **Lens Application layer missing** (Phase 2 extraction)
- ❌ Canonical dimensions (`canonical_activities`, `canonical_place_types`) not populated
- ❌ Module extraction system not implemented
- ❌ Engine purity violations (hardcoded domain logic in `entity_classifier.py`)

**Target:** Get "Powerleague Portobello" entity flowing end-to-end with lens-populated canonical dimensions and at least one module field, satisfying system-vision.md Section 6 validation requirements.

---

## Architectural Foundation

All design decisions derive from:
- **docs/system-vision.md** — Immutable invariants (Engine Purity, Lens Ownership, Determinism)
- **docs/architecture.md** — Concrete contracts (Extraction Boundary, Mapping Semantics, Module Architecture)

**Critical Architectural Constraints:**

### Extraction Boundary (architecture.md 4.2)
- **Phase 1 (Source Extraction):** Extractors return ONLY primitives + raw_observations
- **Phase 2 (Lens Application):** Populate canonical_* dimensions + modules
- Extractors MUST NEVER emit canonical dimensions or modules

### Mapping Rule Execution (architecture.md 6.4)
- Rules execute over union of declared `source_fields`
- First match wins per rule
- Multiple rules may contribute to same dimension
- Deduplication + deterministic lexicographic ordering

### Module Extraction (architecture.md 7.5)
- Deterministic extractors execute first
- Source-aware applicability filtering
- Normalizer pipeline applied after extraction
- LLM extraction deferred (Phase 2 builds deterministic extractors only)

### Engine Purity (system-vision.md Invariant 1)
- Zero domain knowledge in engine code
- No hardcoded domain terms, taxonomies, or logic
- All semantics live exclusively in lens contracts

---

## Design Overview

### Three-Phase Sequential Implementation

**Phase 1: Lens Mapping Engine** → Populates canonical dimensions from lens mapping rules
**Phase 2: Module Extraction Engine** → Populates module fields using deterministic extractors
**Phase 3: Classifier Refactoring** → Removes domain logic, enforces engine purity

Each phase has clear validation gates with database inspection.

---

## Phase 1: Lens Mapping Engine

### Architecture

**New Component:** `engine/lenses/mapping_engine.py`

```python
def apply_lens_mapping(entity: dict, ctx: ExecutionContext) -> dict:
    """
    Main entry point: Apply lens mapping rules to populate canonical dimensions.

    Called after Phase 1 extraction (primitives), before classification.
    """

def execute_mapping_rules(rules: list, entity: dict) -> dict:
    """
    Execute all mapping rules against entity, collect matches.

    Per architecture.md 6.4:
    - First match wins per rule
    - Multiple rules may contribute to same dimension
    """

def match_rule_against_entity(rule: dict, entity: dict) -> Optional[dict]:
    """
    Pattern matching: regex against union of source_fields.

    Returns: {"dimension": str, "value": str} or None
    """

def stabilize_canonical_dimensions(dimensions: dict) -> dict:
    """
    Deduplicate values, lexicographically sort for determinism.
    """
```

### Lens Configuration

**File:** `engine/lenses/edinburgh_finds/lens.yaml`

```yaml
# Canonical registry (architecture.md 6.2)
canonical_values:
  padel:
    display_name: "Padel"
    seo_slug: "padel"
  sports_facility:
    display_name: "Sports Facility"
    seo_slug: "sports-facility"

# Mapping rules (architecture.md 6.3)
mapping_rules:
  - id: map_padel_from_name
    pattern: "(?i)padel"
    dimension: canonical_activities
    value: padel
    source_fields: [entity_name, description, raw_categories]
    confidence: 0.95

  - id: map_sports_facility_type
    pattern: "(?i)sports centre|sports facility|leisure centre"
    dimension: canonical_place_types
    value: sports_facility
    source_fields: [raw_categories, entity_name]
    confidence: 0.85
```

### Pipeline Integration

**Modified Files:**
- `engine/extraction/base.py` or extraction coordinator
  - Wire `apply_lens_mapping()` after Phase 1 extraction
  - Pass ExecutionContext

- `engine/extraction/extractors/*.py`
  - Update signatures: `extract(raw_data, *, ctx: ExecutionContext)`

- `engine/lenses/loader.py`
  - Add canonical registry validation (orphaned refs fail fast)
  - Compute lens content hash for reproducibility

### Validation Gate 1

```bash
# Run orchestration
python -m engine.orchestration.cli run "powerleague portobello edinburgh"

# Inspect entity
psql $DATABASE_URL -c "
SELECT entity_name, canonical_activities, canonical_place_types
FROM entities
WHERE entity_name ILIKE '%powerleague%portobello%';"
```

**Expected:**
```
canonical_activities: ['padel']
canonical_place_types: ['sports_facility']
```

**Pass Criteria:** Both canonical dimension arrays contain at least one value.

---

## Phase 2: Module Extraction Engine

### Architecture

**New Component:** `engine/extraction/module_extractor.py`

```python
def apply_module_extraction(entity: dict, ctx: ExecutionContext) -> dict:
    """
    Main entry: Evaluate module triggers, extract fields.

    Called after lens mapping (once canonical dimensions populated).
    """

def evaluate_module_triggers(triggers: list, entity: dict) -> list:
    """
    Determine which modules to attach based on canonical dimensions.

    Example: canonical_activities contains 'padel' → attach 'sports_facility'
    """

def execute_field_rules(rules: list, entity: dict, source: str) -> dict:
    """
    Execute field rules with applicability filtering (source, entity_class).

    Deterministic extractors only (Phase 2 scope).
    """

def apply_normalizers(value: Any, normalizers: list) -> Any:
    """
    Execute normalizer pipeline left-to-right.

    Examples: trim → numeric_parser → round_integer
    """
```

### Deterministic Extractor Vocabulary

**New Directory:** `engine/lenses/extractors/`

Implement generic extractors per architecture.md 7.4:
- `numeric_parser.py` — Extract numbers from text
- `regex_capture.py` — Pattern-based field extraction
- `json_path.py` — Navigate JSON structures
- `boolean_coercion.py` — Convert to boolean
- `normalizers.py` — trim, lowercase, uppercase, round_integer, list_wrap

### Lens Configuration Updates

```yaml
# Module triggers (architecture.md 7.2)
module_triggers:
  - when:
      dimension: canonical_activities
      values: [padel, tennis, squash]
    add_modules: [sports_facility]

# Module definitions (architecture.md 7.3)
modules:
  sports_facility:
    field_rules:
      - rule_id: extract_padel_court_count
        target_path: padel_courts.total
        source_fields: [description, raw_categories]
        extractor: regex_capture
        pattern: "(?i)(\d+)\s*padel\s*courts?"
        confidence: 0.85
        applicability:
          source: [serper, google_places]
          entity_class: [place]
        normalizers: [numeric_parser, round_integer]
```

### Pipeline Integration

**Modified Files:**
- Extraction coordinator: Call `apply_module_extraction()` after lens mapping
- Pass source metadata for applicability filtering

### Validation Gate 2

```bash
# Run orchestration
python -m engine.orchestration.cli run "powerleague portobello edinburgh"

# Inspect modules
psql $DATABASE_URL -c "
SELECT entity_name, modules::text
FROM entities
WHERE entity_name ILIKE '%powerleague%portobello%';"
```

**Expected:**
```
modules: {"sports_facility": {"padel_courts": {"total": 5}}}
```

**Pass Criteria:** `modules.sports_facility` exists with at least one non-null field.

---

## Phase 3: Classifier Refactoring

### Problem

`engine/extraction/entity_classifier.py` violates engine purity (Invariant 1):
- Lines 102-120 contain hardcoded domain terms: "retailer", "shop", "league", "club"
- Classification logic uses domain-specific category checks

### Target Architecture

Classification uses **only structural rules**:

```python
# ✅ PERMITTED: Structural classification
if has_street_address and (has_latitude or has_postcode):
    entity_class = "place"

elif has_email and has_phone:
    if has_organization_structural_signals():
        entity_class = "organization"
    else:
        entity_class = "person"

elif has_start_date or has_end_date:
    entity_class = "event"

else:
    entity_class = "thing"
```

### Refactoring Tasks

1. Remove hardcoded domain logic from `entity_classifier.py` (lines 102-120)
2. Replace with structural-only rules
3. Add purity validation test:

```python
def test_classifier_contains_no_domain_literals():
    """Detect domain terms in classifier code"""
    source = inspect.getsource(entity_classifier)
    forbidden = ["padel", "tennis", "wine", "restaurant", "league", "club"]
    for term in forbidden:
        assert term.lower() not in source.lower()
```

### Validation Gate 3

```bash
# Run purity test
pytest tests/engine/extraction/test_entity_classifier.py::test_classifier_contains_no_domain_literals -v

# Verify Powerleague still classifies correctly
python -m engine.orchestration.cli run "powerleague portobello edinburgh"

# Expected: entity_class = 'place' (via structural rules: has address + geo)
```

**Pass Criteria:** No domain terms in classifier, Powerleague still classifies as "place".

---

## Testing Strategy

### TDD Workflow (Red → Green → Refactor)

1. **Red:** Write failing test first
2. **Green:** Implement minimum code to pass
3. **Refactor:** Improve while keeping tests green
4. **Commit:** Conventional commit with co-author

### Example Test Progression

**Phase 1: Mapping Engine**

```python
# Test 1: Pattern matching
def test_simple_pattern_match_populates_dimension():
    rule = {"pattern": r"(?i)padel", "dimension": "canonical_activities",
            "value": "padel", "source_fields": ["entity_name"]}
    entity = {"entity_name": "Powerleague Padel Club"}

    result = match_rule_against_entity(rule, entity)
    assert result == {"dimension": "canonical_activities", "value": "padel"}

# Test 2: Multiple rules
def test_multiple_rules_append_to_same_dimension():
    # Multiple rules can contribute different values to same dimension

# Test 3: Deduplication
def test_canonical_dimensions_deduplicated_and_sorted():
    # Duplicates removed, lexicographic ordering applied

# Test 4: Registry validation
def test_orphaned_canonical_reference_fails_validation():
    # Mapping rule references non-existent value → ValidationError
```

**Phase 2: Module Extraction**

```python
# Test 1: Module triggers
def test_module_trigger_attaches_module():
    # When canonical_activities contains 'padel' → attach sports_facility

# Test 2: Field extraction
def test_regex_capture_extractor():
    # Extract court count from description using regex pattern

# Test 3: Applicability
def test_field_rule_skipped_when_source_mismatch():
    # Rule only runs for matching sources

# Test 4: Normalizers
def test_normalizers_applied_in_order():
    # Pipeline execution: trim → numeric_parser → round_integer
```

---

## Success Criteria (One Perfect Entity)

Per system-vision.md Section 6, the system is validated when Powerleague Portobello produces:

```sql
entity_name: Powerleague Portobello
entity_class: place
canonical_activities: ['padel']
canonical_place_types: ['sports_facility']
modules: {"sports_facility": {"padel_courts": {"total": 5}}}
```

**Pass Criteria:**
1. ✅ Correct entity_class
2. ✅ At least one value in canonical_activities (lens mapping worked)
3. ✅ At least one value in canonical_place_types (lens mapping worked)
4. ✅ At least one module field populated (module extraction worked)
5. ✅ All tests pass
6. ✅ No domain terms in entity_classifier.py (purity validated)
7. ✅ Lens contract validates at bootstrap

**Fail Criteria:**
- Tests pass but entity data incomplete/incorrect (reality validation failure)
- Canonical dimensions empty when evidence exists
- Modules field null or empty

---

## Trade-offs and Decisions

### Decision 1: Deterministic Extractors Only (Phase 2)
**Choice:** Defer LLM extraction to later phase
**Rationale:** Reduces complexity, validates architecture with simpler extractors first
**Trade-off:** May not extract all possible module fields, but sufficient for validation

### Decision 2: Minimal Lens Configuration
**Choice:** Only configure rules needed for Powerleague Portobello
**Rationale:** Validates architecture without premature taxonomy expansion
**Trade-off:** Limited coverage initially, but extensible incrementally

### Decision 3: Sequential Phases with Gates
**Choice:** Validate each phase before proceeding
**Rationale:** Clear checkpoints, easier debugging, architectural validation at each step
**Trade-off:** Slower than parallel development, but lower risk

### Decision 4: Fix Classifier Purity in Phase 3
**Choice:** Include classifier refactoring in this migration
**Rationale:** Ensures clean foundations before scaling lens system
**Trade-off:** Slightly larger scope, but prevents building on architectural violations

---

## Risks and Mitigations

| Risk | Impact | Mitigation | Rollback |
|------|--------|------------|----------|
| Breaking existing extractors | High | Update signatures incrementally, test after each | Make ExecutionContext optional initially |
| Lens validation too strict | Medium | Start with warnings, promote to errors after validation | Downgrade to warnings temporarily |
| Module extraction complexity | Medium | Phase 2 implements only deterministic extractors | Feature flag, can be disabled |
| Performance regression | Low | Mapping/modules are post-processing, not blocking | Feature flag if needed |

---

## Next Steps

1. **Approve Design** — Confirm alignment with system-vision.md + architecture.md
2. **Setup Implementation Environment** — Consider using git worktree for isolation
3. **Begin Phase 1** — Start TDD for lens mapping engine
4. **Validate Phase 1** — Confirm canonical dimensions populated
5. **Proceed to Phase 2** — Module extraction engine
6. **Final Validation** — One perfect entity end-to-end

---

## References

- **docs/system-vision.md** — Architectural constitution, immutable invariants
- **docs/architecture.md** — Runtime contracts and concrete semantics
- **CLAUDE.md** — Development workflow, TDD requirements, quality gates
