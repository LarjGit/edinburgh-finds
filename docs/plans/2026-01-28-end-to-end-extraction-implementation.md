# End-to-End Entity Extraction Implementation Plan

**Created:** 2026-01-28
**Status:** Design Phase
**Reference:** VISION.md
**Test Entity:** Powerleague Portobello

---

## Core Objective

Prove the Edinburgh Finds architecture end-to-end with ONE perfect entity flowing through the complete pipeline with ZERO compromises on design principles.

**Success Criteria:**
- Query "Powerleague Portobello" (or similar)
- Complete data flows through: Query → Orchestration → Ingestion → Extraction → Mapping → Classification → Modules → Deduplication → Finalization
- Entity table contains complete, accurate record with all canonical dimensions populated and modules properly structured
- Architecture validated as scalable (no refactoring needed when adding more entities)

**Quality Principles (Non-Negotiable):**
1. **Engine Purity** - No vertical-specific logic in engine code, all domain knowledge in lens
2. **Module Namespace Structure** - Proper JSONB organization, no flattened data
3. **Multi-Source Handling** - Must merge data from multiple connectors correctly
4. **Idempotency** - Re-running same query updates rather than duplicates
5. **Field-Level Trust Hierarchy** - Principled conflict resolution when sources disagree
6. **Banked Progress** - Every phase must be production-quality, no throwaway work

---

## Current State Assessment

### What Works ✅

**Infrastructure:**
- BaseExtractor abstract interface well-designed
- All 6 connectors operational (Serper, Google Places, OSM, Sport Scotland, Edinburgh Council, Open Charge Map)
- Entity classification (resolve_entity_class) deterministic and correct
- Module validator enforces namespacing
- Orchestration planner selects connectors based on query features
- EntityFinalizer generates slugs and upserts to Entity table

**Lens System:**
- VerticalLens loader reads lens.yaml files
- Lens validator enforces architectural contracts
- QueryLens provides lightweight orchestration interface
- ModuleTrigger evaluation logic implemented

### Critical Gaps ❌

**Gap #1: Lens Not Wired to Extraction**
- `extract_with_lens_contract()` function exists but is NEVER CALLED
- No path for lens configuration to reach extractors during extraction
- Canonical dimensions stay empty because mapping rules never applied
- Modules stay empty because triggers never fire

**Gap #2: Edinburgh Finds Lens Doesn't Exist**
- `engine/lenses/edinburgh_finds/` directory exists but empty
- No `lens.yaml` file defining:
  - Query vocabulary (activity keywords, location indicators)
  - Connector routing rules (which sources for which queries)
  - Mapping rules (raw categories → canonical dimensions)
  - Module definitions (sports_facility structure)
  - Module triggers (when to attach domain modules)
  - Canonical value metadata (display names, icons, SEO)

**Gap #3: Module Field Extraction Not Implemented**
- `extract_with_lens_contract()` creates empty module dicts
- No logic to populate sports_facility fields from raw data
- Need: extract_module_fields(raw_data, module_def) implementation

**Gap #4: Field Name Mismatch**
- Extractors produce: `{entity_name, latitude, longitude, street_address, phone}`
- EntityFinalizer expects: `{name, location_lat, location_lng, address_full, contact_phone}`
- Misalignment causes data loss during finalization

**Gap #5: Multi-Source Merging Stubbed Out**
- EntityFinalizer._finalize_group() has `# TODO: Implement proper EntityMerger integration`
- Currently just takes first source, ignores others
- Need: Field-level trust-based conflict resolution

### Architecture Corrections Made ✅

**Fixed During Session:**
- Removed incorrect `lenses/padel/` directory (padel is an activity, not a lens)
- Removed incorrect `lenses/wine/` directory (wine would be a different vertical)
- Created proper `lenses/edinburgh_finds/` directory
- Clarified: Edinburgh Finds is the ONLY lens, covering all Edinburgh activities

---

## 5 Critical Design Decisions

Before any implementation, these architectural decisions must be resolved to prevent refactoring:

### Decision 1: Lens Injection Pattern ✅ RESOLVED

**Problem:** How does VerticalLens configuration reach extractors during extraction?

**DECISION:** Orchestrator-owned, context injection pattern

**Reference:** VISION.md Section 3: Lens Injection Architecture

**Summary:**
- **Who loads lens:** Only CLI/bootstrap (never extractors)
- **How it flows:** CLI → Planner → extraction_integration → extractors
- **What gets passed:** ExecutionContext with lens_id, lens_contract dict, lens_hash
- **Lens selection precedence:** CLI flag → env var → app.yaml config → hardcoded fallback
- **Config file:** `engine/config/app.yaml` with `default_lens: edinburgh_finds`
- **Extractor API:** `extract(raw_data, *, ctx: ExecutionContext)` with mandatory ctx parameter
- **All 6 extractors:** Updated in single pass to accept ctx

**Key Design Points:**
1. CLI loads and validates lens.yaml once at bootstrap (fail-fast)
2. ExecutionContext created with entire lens.yaml as plain dict
3. Context passed explicitly through pipeline (no globals)
4. Extractors call `self.apply_lens_contract(raw_data, ctx=ctx)` to get lens-derived fields
5. Purity enforced: Extractors NEVER import LensRegistry or load files

**Files to Create:**
- `engine/config/app.yaml` (default lens configuration)
- `engine/orchestration/context.py` (ExecutionContext dataclass)

**Files to Update:**
- `engine/extraction/base.py` (BaseExtractor.extract signature, apply_lens_contract helper)
- All 6 extractor implementations (add ctx parameter)
- `engine/orchestration/cli.py` (load lens, create context)
- `engine/orchestration/planner.py` (receive and pass context)
- `engine/orchestration/extraction_integration.py` (pass context to extractors)

**Impact:** Foundation for all subsequent extraction work - implements once, scales forever

---

### Decision 2: Define and Validate the Edinburgh Finds Lens Contract ✅ RESOLVED

**Problem:** `lens.yaml` doesn't exist, and its structure must be defined as a strict runtime contract, not a free-form configuration.

**DECISION:** Lens as a compiled, validated, evidence-driven contract

**Reference:** VISION.md Section: "Lens Authoring Contract & Canonical Registry (Decision 2)"

**Core Principles:**
1. Lens is a **compiled runtime contract** (deterministic, versioned, hashable)
2. **Canonical registry** is single source of truth (no orphaned references)
3. **Structured mapping rules** with explicit metadata (id, confidence, applicability)
4. **Evidence-driven expansion** (every rule backed by real payload fixture)
5. **Minimal viable lens first** (one entity, then expand incrementally)
6. **Validation gates fail-fast** (broken lens aborts at bootstrap)

#### Deliverable 2.1: Canonical Registry Definition

**Objective:** Define the initial canonical registry for all four dimensions, ensuring internal consistency and validation.

**Canonical Values to Define:**

**Activities (Edinburgh-Specific):**
- Minimal set for validation entity: `football`, `padel`
- Expansion driven by observed payloads
- Each value requires: display_name, seo_slug, icon, description

**Roles (Universal Function Keys):**
- Minimal set: `provides_facility`
- Universal across verticals (same keys for sports, wine, restaurants)
- Expansion as new entity types observed

**Place Types (Edinburgh-Specific but Engine-Opaque):**
- Minimal set: `sports_centre`
- Edinburgh interpretation, but engine stores opaque strings
- Expansion based on real facility observations

**Access Models (Universal):**
- Minimal set: `pay_and_play`
- Largely universal (membership, free, booking_required, etc.)
- Expansion as needed

**Registry Structure:**
```yaml
canonical_values:
  # Activities (minimal for Powerleague validation)
  football:
    display_name: "Football"
    seo_slug: "football"
    icon: "football"
    description: "Football pitches and venues"

  padel:
    display_name: "Padel"
    seo_slug: "padel"
    icon: "padel-racquet"
    description: "Padel courts and facilities"

  # Roles (universal)
  provides_facility:
    display_name: "Sports Facility"
    seo_slug: "facilities"
    description: "Provides sports facilities"

  # Place Types
  sports_centre:
    display_name: "Sports Centre"
    seo_slug: "sports-centres"
    description: "Multi-sport facility"

  # Access
  pay_and_play:
    display_name: "Pay & Play"
    icon: "credit-card"
    description: "No membership required"
```

**Validation:**
- No mapping rule may introduce canonical values not in registry
- All references resolve during lens validation
- Fail-fast if orphaned reference detected

**Acceptance Criteria:**
- ✅ Registry contains minimum viable set for validation entity
- ✅ All four dimensions represented
- ✅ Each value has complete display metadata
- ✅ Validation passes (no orphaned references)

#### Deliverable 2.2: Structured Mapping Rule Framework

**Objective:** Define mapping rules that reference canonical registry values with explicit structure and metadata.

**Rule Structure Requirements:**
- **id:** Unique identifier (enables duplicate detection)
- **pattern:** Regex pattern (Python `re` module syntax)
- **dimension:** Target canonical dimension
- **value:** Canonical registry reference (MUST exist in canonical_values)
- **source_fields:** Which raw data fields to inspect
- **confidence:** Extraction confidence (0.0-1.0)
- **applicability** (optional): Entity class constraints

**Minimal Mapping Rules (For Validation Entity):**
```yaml
mapping_rules:
  # Activities
  - id: activity_football_explicit
    pattern: "(?i)\\bfootball\\b|5.?a.?side|7.?a.?side"  # Python re syntax
    dimension: canonical_activities
    value: football
    source_fields: [raw_categories, types, name]
    confidence: 0.95

  - id: activity_padel_explicit
    pattern: "(?i)\\bpadel\\b|pádel"  # Python re syntax
    dimension: canonical_activities
    value: padel
    source_fields: [raw_categories, types, name]
    confidence: 0.98

  # Roles
  - id: role_facility_provider
    pattern: "(?i)facility|venue|centre"
    dimension: canonical_roles
    value: provides_facility
    source_fields: [raw_categories, types]
    confidence: 0.90

  # Place Types
  - id: place_type_sports_complex
    pattern: "(?i)sports.?complex|sports.?centre"
    dimension: canonical_place_types
    value: sports_centre
    source_fields: [types, raw_categories]
    confidence: 0.95

  # Access
  - id: access_pay_and_play
    pattern: "(?i)pay.?and.?play|casual|drop.?in"
    dimension: canonical_access
    value: pay_and_play
    source_fields: [raw_categories, description]
    confidence: 0.90
```

**Evidence Requirement:**
- Each rule must be justified by a real raw ingestion payload (recorded connector response, not mock)
- Fixture stored: `tests/fixtures/raw_ingestions/<connector>/<entity>.json`
- Test validates rule matches fixture correctly
- Fixtures are captured real payloads, not hand-crafted test data

**Acceptance Criteria:**
- ✅ All mapping rule `value` fields exist in canonical_values
- ✅ Each rule has unique `id` (no duplicates)
- ✅ Rules are small and composable (not monolithic)
- ✅ Each rule backed by real payload fixture
- ✅ Validation entity produces non-empty canonical dimensions

#### Deliverable 2.3: Connector Routing Rules

**Objective:** Lens defines routing rules only for connectors it intends to use. Validation must fail if lens references an unknown connector.

**Connector Routing Requirements:**
- Lens defines rules ONLY for connectors it uses (not all registered connectors)
- Referenced connectors MUST exist in engine connector registry (fail-fast validation)
- No requirement to enumerate every connector in the engine
- Unknown connector references cause immediate validation failure

**Routing Rules (Edinburgh Finds Uses 5 Connectors):**
```yaml
connector_rules:
  google_places:
    priority: high
    triggers:
      - type: always
    budget_limit: 100

  serper:
    priority: medium
    triggers:
      - type: always
    budget_limit: 50

  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [football, tennis, padel, squash, swimming, rugby]

  edinburgh_council:
    priority: high
    triggers:
      - type: location_match
        locations: [edinburgh]

  openstreetmap:
    priority: medium
    triggers:
      - type: location_match
        locations: [edinburgh]

# Note: open_charge_map not included (EV charging not relevant to Edinburgh Finds)
# No requirement to enumerate all registered connectors
```

**Validation:**
- Lens validator checks all referenced connectors exist in engine registry
- Unknown connector references cause validation failure
- Fail-fast with clear error: "Connector 'xyz' not found in registry"

**Acceptance Criteria:**
- ✅ All connectors used by this lens have routing rules; no unknown connectors referenced
- ✅ Validation passes (no unknown connector references)
- ✅ Test query selects appropriate subset
- ✅ No requirement to address every registered connector

#### Deliverable 2.4: Module Registry and Trigger Definition

**Objective:** Domain modules declared centrally in lens, triggers reference declared modules and canonical values deterministically.

**Module Registry:**
```yaml
modules:
  sports_facility:
    description: "Sports facility inventory and amenities"
    fields:
      football_pitches:
        type: object
        fields:
          five_a_side:
            type: object
            fields:
              total: integer
              indoor: integer
              outdoor: integer
              surface: array[string]

      padel_courts:
        type: object
        fields:
          total: integer
          indoor: integer
          outdoor: integer

    # Field extraction rules (Decision 3)
    field_rules:
      - rule_id: football_pitch_total_sport_scotland
        target_path: football_pitches.five_a_side.total
        source_fields: [NumPitches]
        extractor: numeric_parser
        confidence: 0.95
        applicability:
          source: [sport_scotland]
          entity_class: [place]

      - rule_id: football_pitch_surface
        target_path: football_pitches.five_a_side.surface
        source_fields: [Surface]
        extractor: regex_capture
        pattern: "(?i)(3G|4G|grass|artificial)"
        confidence: 0.85
```

**Module Triggers:**
```yaml
module_triggers:
  - id: attach_sports_facility_football
    when:
      dimension: canonical_activities
      values: [football, padel, tennis, squash]
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

  - id: attach_sports_facility_swimming
    when:
      dimension: canonical_activities
      values: [swimming]
    add_modules: [sports_facility]
    conditions:
      - entity_class: place
```

**Trigger Validation:**
- All `add_modules` values must exist in `modules` registry
- All `values` in `when` clause must exist in canonical registry
- Triggers are deterministic (same input = same modules attached)

**Acceptance Criteria:**
- ✅ Module registry defines sports_facility structure
- ✅ All triggers reference declared modules only
- ✅ Triggers reference canonical values only
- ✅ Validation entity has sports_facility module attached
- ✅ Module structure validated by ModuleValidator

#### Deliverable 2.5: Validation & Quality Gates

**Objective:** Implement comprehensive validation gates that fail-fast before any extraction occurs.

**Required Validation Gates:**

**Gate 1: Schema Validation**
- YAML structure matches lens schema
- All required sections present
- Field types correct

**Gate 2: Canonical Reference Integrity**
- All mapping rule `value` fields exist in `canonical_values`
- All module trigger `add_modules` exist in `modules`
- No orphaned references

**Gate 3: Connector Reference Validation**
- All connectors in `connector_rules` exist in engine registry
- Clear error listing missing connectors

**Gate 4: Duplicate Identifier Validation**
- All mapping rule `id` fields unique
- All module trigger `id` fields unique
- Prevents conflicts and ambiguity

**Gate 5: Pattern Compilation Validation**
- All mapping rule `pattern` fields compile as valid Python regex
- Patterns validated at lens load time using `re.compile()`
- Fails with rule `id` and regex error if pattern invalid
- Prevents runtime regex compilation errors

**Gate 6: Smoke Coverage Validation**
- At least one fixture for each mapping rule
- Validation entity produces non-empty canonical dimensions
- At least one module trigger fires

**Gate 7: Fail-Fast Enforcement**
- ANY validation failure aborts execution immediately
- Clear error messages indicating which gate failed
- No silent fallback behavior

**Implementation:**
```python
# engine/lenses/loader.py
def load_lens(lens_id: str) -> VerticalLens:
    # Lens content lives at: lenses/<lens_id>/lens.yaml
    # (NOT engine/lenses/ - engine owns loader code only)
    raw_yaml = load_yaml_file(f"lenses/{lens_id}/lens.yaml")

    # Gate 1: Schema validation
    validate_lens_schema(raw_yaml)

    # Gate 2: Canonical reference integrity
    validate_canonical_references(raw_yaml)

    # Gate 3: Connector reference validation
    # Fail if lens references connectors not in engine registry
    validate_connector_references(raw_yaml)

    # Gate 4: Duplicate identifier validation
    validate_unique_rule_ids(raw_yaml)

    # Gate 5: Pattern compilation validation
    # All mapping rule patterns must compile as valid Python regex
    validate_pattern_compilation(raw_yaml)

    # Gate 6: Smoke coverage validation (performed via tests)

    # Create lens object (Gate 7: fail-fast on any error)
    return VerticalLens.from_dict(raw_yaml)
```

**Acceptance Criteria:**
- ✅ All validation gates implemented (1-7)
- ✅ Lens validation failures abort at bootstrap
- ✅ Clear error messages for each gate failure (includes rule `id` for pattern errors)
- ✅ No silent fallback behavior
- ✅ Pattern compilation validated at load time (Python `re.compile()`)
- ✅ Powerleague validation entity passes smoke coverage validation (Gate 6)

**End-to-End Acceptance Criteria:**
```sql
-- After running: python -m engine.orchestration.cli run "Powerleague Portobello"
SELECT
  entity_name,
  canonical_activities,      -- Expected: non-empty array
  canonical_roles,           -- Expected: non-empty array
  canonical_place_types,     -- Expected: non-empty array
  canonical_access,          -- Expected: non-empty array
  modules->'sports_facility' -- Expected: non-empty object
FROM entities
WHERE slug = 'powerleague-portobello';

-- PASS if all canonical dimensions contain at least 1 value
-- PASS if sports_facility module attached and non-empty
```

#### Deliverable 2.6: Evidence-Driven Expansion Policy

**Objective:** Document that new mapping rules, vocabulary, or canonical values require real payload evidence.

**Evidence Requirements:**
- **Real Raw Payload:** New rule must be justified by observed connector payload (recorded response, not mock)
- **Fixture Storage:** Payload stored as `tests/fixtures/raw_ingestions/<connector>/<entity>.json`
- **Explicit Justification:** Fixture documents what pattern was observed and why rule needed
- **Real Connector Response:** Fixtures are captured real data, not hand-crafted test data

**Expansion Workflow:**
```
1. Run query, collect raw ingestions
2. Inspect payloads for new categories/patterns
3. Create fixture from real payload
4. Write mapping rule to handle observed pattern
5. Add canonical value to registry (with metadata)
6. Write test validating rule matches fixture
7. Commit fixture + rule + test together
```

**Anti-Patterns (Forbidden):**
- ❌ Adding canonical values without observed payloads
- ❌ Creating mapping rules for hypothetical data
- ❌ Expanding vocabulary based on speculation

**Acceptance Criteria:**
- ✅ Policy documented in lens README
- ✅ All initial mapping rules backed by fixtures
- ✅ Test coverage for each rule
- ✅ No speculative taxonomy expansion

**Impact:** Ensures lens contract is production-quality, validated, and scales safely

---

### Decision 3: Module Field Extraction Algorithm ✅ RESOLVED

**Problem:** How do we populate module fields from raw source data while maintaining engine purity and lens-driven architecture?

**DECISION:** Declarative, lens-owned, schema-driven extraction with generic engine interpreter

**Reference:** VISION.md Section 5: Module Architecture → Module Field Extraction (Decision 3)

**Summary:**

**Core Principle:**
- Module field extraction is **declarative, lens-owned, schema-driven**
- Lens defines extraction rules, engine executes them generically
- No module-specific or domain-specific logic in engine code
- Engine remains domain-blind

**Module Field Rule Structure:**

Each module declares structured field rules with:
- **rule_id:** Unique identifier
- **target_path:** Dot path inside module JSON (e.g., `football_pitches.five_a_side.total`)
- **source_fields:** Raw payload fields the rule may read
- **extractor:** From generic engine-owned vocabulary
- **confidence:** Extraction confidence score
- **applicability:** Optional (source, entity_class constraints)
- **normalizers:** Optional field transformations
- **llm_config:** Optional (only for LLM extractors)

**Extractor Vocabulary (Small, Stable, Generic):**

**Deterministic Extractors:**
- `numeric_parser`: Extract numbers from strings or numeric fields
- `regex_capture`: Extract values matching regex pattern
- `json_path`: Extract value at JSON path
- `boolean_coercion`: Convert values to boolean
- `coalesce`: Try multiple source fields, use first non-null
- `normalize`: Apply normalization functions
- `array_builder`: Construct array from multiple fields

**LLM Extractors:**
- `llm_structured`: Schema-bound structured extraction via Instructor
- Used only when deterministic insufficient
- Must include Pydantic schema for validation

**LLM/Instructor Constraints (Mandatory):**
1. Schema-bound only (Instructor validation, no free-form JSON)
2. Evidence anchored where possible
3. Deterministic-first (LLM fills only missing fields)
4. Batch per module (max one LLM call per module per source payload)
5. Confidence caps (LLM weaker than official sources in merge)
6. Full provenance (rule_id, source, confidence, method)

**Execution Semantics:**

For each entity and required module:
1. Select applicable field rules (based on source, entity_class)
2. Run deterministic rules first and populate fields
3. Identify remaining fields needing LLM extraction
4. Build schema for only those fields if needed
5. Execute single Instructor call per module if needed
6. Validate, normalize, enforce evidence and confidence constraints
7. Write results into module using target_path
8. Cross-source conflicts resolved during merge (not here)

**Source Awareness (Required):**
- Module extraction path must receive `source_name` or full `ExecutionContext`
- This is the only required touch to `extract_with_lens_contract()` for Decision 3

**Purity Rules (Non-Negotiable):**
- Engine code must NOT contain domain concepts, module-specific branching, or hardcoded field semantics
- All semantics live in the Lens contract
- Lens treated as opaque configuration by engine

**Implementation Specifications:**

**Canonical Function Signature:**
```python
# engine/extraction/base.py
def extract_with_lens_contract(
    raw_data: dict,
    lens_contract: dict,
    *,
    source_name: str  # REQUIRED for field_rules applicability
) -> dict
```

**BaseExtractor Interface Alignment:**
```python
class BaseExtractor(ABC):
    source_name: str  # Class attribute for connector name

    @abstractmethod
    def extract(self, raw_data: Dict, *, ctx: ExecutionContext) -> Dict:
        """Extract entity from raw data with lens context"""

    def apply_lens_contract(
        self,
        raw_data: Dict,
        *,
        ctx: ExecutionContext,
        source_name: str  # Required for applicability filtering
    ) -> Dict:
        """Apply lens mapping + module extraction"""
        return extract_with_lens_contract(
            raw_data,
            ctx.lens_contract,
            source_name=source_name
        )
```

**Mapping Rules Execution:**
- Mapping runs over **union of declared source_fields** per rule (NOT hardcoded to raw_categories)
- Engine iterates: `for field in rule["source_fields"]: check raw_data.get(field)`
- All rules execute, each may contribute to canonical dimensions

**LLM Integration Point:**
- `llm_structured` extractor runs ONLY inside `extract_module_fields()` (module_extractor.py)
- NOT inside per-source extractors, NOT per-field
- Batch ≤ 1 Instructor call per module per payload

**Error Handling:** Graceful degradation (log with rule_id/source, skip field, continue)

**Rule Conflict Resolution:** First-match wins; conditions prevent re-extraction

**Normalizer Pipeline:** Ordered execution (trim → lowercase → list_wrap)

**Condition Vocabulary:** `field_not_populated`, `any_field_missing`, `source_has_field`, `value_present`

**Extractor Vocabulary:** 8 deterministic + 1 LLM (see VISION.md Module Field Extraction section for full list)

**Implementation Sequencing:** Deterministic-only MVP first (5–10 rules), then add LLM

**Validation/Acceptance:**

Decision 3 is complete when:
- ✅ Modules are no longer empty placeholders
- ✅ **At least one field_rules rule produces a non-null value persisted under target_path in modules JSONB for a real fixture/entity** (explicit non-empty requirement)
- ✅ Deterministic extraction works for structured sources (Sport Scotland fixture)
- ✅ LLM-assisted extraction works under constraints (Google Places fixture)
- ✅ No engine purity violations (no domain logic in module_extractor.py)
- ✅ Tests exist using real payload fixtures (not mocks)
- ✅ Source awareness properly implemented (applicability filtering works)
- ✅ Error handling gracefully degrades (partial data succeeds)
- ✅ ≤ 1 LLM call per module per payload (batch efficiency verified)

**Files to Create:**
- `engine/extraction/module_extractor.py` (generic field rule executor)
- `engine/extraction/extractors/` (vocabulary implementations)

**Files to Update:**
- `engine/extraction/base.py` (wire up module field extraction)
- `lenses/edinburgh_finds/lens.yaml` (add field_rules to sports_facility module)

**Impact:** Enables rich facility data extraction while maintaining architectural purity

---

### Decision 4: Field Name Reconciliation ✅ RESOLVED

**Problem:** Field name mismatch between extraction output and Entity schema

**DECISION:** Entity schema field names are canonical across entire pipeline

**Reference:** VISION.md Section 5: Module Architecture → Field Name Reconciliation (Decision 4)

**Summary:**

**Core Principle:**
- Schema (`engine/config/schemas/entity.yaml`) is sole authority for universal field names
- All extractors emit schema-aligned field names
- EntityFinalizer consumes schema-aligned field names
- No translation layers, no legacy naming, no connector-specific names

**Implementation Reality:**
- Most extractors already emit correct schema names (entity_name, latitude, longitude, street_address, phone, email)
- Primary fix: Update EntityFinalizer to read schema names instead of legacy names (location_lat, contact_phone, etc.)
- Global fix: Standardize `website` → `website_url` everywhere

**What Extractors Emit:**
- **Schema primitives:** Refer to `engine/config/schemas/entity.yaml` for authoritative list (entity_name, lat/lng, address, contact fields)
- **Raw observations:** Source-specific fields allowed for downstream use (e.g., NumPitches, facility_type)
- **NOT lens/module semantics:** canonical_*, modules, or any derived data

**Boundary Clarity:**
- Schema primitives (extractors) vs. Lens dimensions (mapping rules) vs. Module data (field rules)
- Schema is sole authority - do not maintain separate field lists in code/docs

**Validation Strategy:**
- Permissive: Only warn on legacy patterns (location_*, contact_*, address_*)
- Allow unknown fields (may be legitimate raw observations)
- Incremental rollout: Warn during migration, error in CI post-migration
- Test validates schema field preservation using real fixtures

**Files to Update:**
- `engine/orchestration/entity_finalizer.py` (_finalize_single method)
- All 6 extractors (website → website_url)
- `engine/extraction/validation.py` (add field name validation)
- `tests/engine/orchestration/test_field_name_alignment.py` (new regression test)

**Impact:** Eliminates silent data loss, simplifies future connector additions, establishes schema as unambiguous authority

---

### Decision 5: Multi-Source Merge Algorithm ✅ RESOLVED

**Problem:** When Google Places and Sport Scotland both return "Powerleague Portobello", how do we merge field-level conflicts, union canonical dimensions, and deep-merge modules while maintaining determinism and engine purity?

**DECISION:** Deterministic, field-aware merge contract that runs after deduplication grouping and before persistence, using connector-metadata-driven trust model

**Reference:** VISION.md Section 5: Module Architecture → Deterministic Multi-Source Entity Merge (Decision 5)

**Summary:**

**Core Principle:**
- Merge is **deterministic, field-aware, and metadata-driven**
- Runs **after deduplication grouping** (entities already grouped by real-world identity)
- Runs **before persistence** (EntityFinalizer receives merged entities)
- Uses connector registry metadata (`trust_tier`, `default_priority`) - never hardcodes connector names
- Domain-blind (no vertical-specific branching in merge logic)
- Idempotent (same inputs always produce identical output)

**Trust Model (Metadata-Driven):**

Trust hierarchy comes from connector registry metadata:

```python
# engine/orchestration/registry.py
ConnectorSpec(
    name="sport_scotland",
    trust_tier="high",           # official/authoritative sources
    default_priority=1,          # Lower number = higher priority
    ...
)

ConnectorSpec(
    name="google_places",
    trust_tier="medium",         # verified crowdsourced
    default_priority=2,
    ...
)

ConnectorSpec(
    name="serper",
    trust_tier="low",            # unverified crowdsourced
    default_priority=3,
    ...
)
```

**Key Design Point:** Merge logic consumes `trust_tier` and `default_priority` values from registry, never references connector names directly (except as tie-breaker).

**Field-Group Merge Strategy:**

Different field types require different strategies to avoid sparsity and maximize completeness:

**1. Identity/Core Display Fields** (entity_name, summary, street_address):
- **Strategy:** Prefer higher `trust_tier` unless empty or less usable
- **Quality heuristic:** Non-null > longer/more complete > title-cased
- **Tie-break:** `trust_tier` → quality → `default_priority` → lexicographic `source_name`
- **Example:** `"Powerleague Portobello"` (concise) preferred over `"Powerleague Edinburgh - Portobello Branch"` (verbose)

**2. Geo Primitives** (latitude, longitude):
- **Strategy:** Prefer most precise/authoritative coordinates
- **Precision measurement:**
  1. If connector provides explicit `precision` or `accuracy` metadata → use higher precision
  2. Else prefer higher `trust_tier`
  3. Else prefer coordinates with more decimal precision (more decimals = more precise)
  4. Else deterministic tie-break
- **NO CENTROID:** Do NOT compute geographic centroid or averages (can produce invalid midpoints)
- **Tie-break:** precision → `trust_tier` → decimal precision → `default_priority` → lexicographic `source_name`
- **Example:** 55.954123, -3.115678 (8 decimals, precise) preferred over 55.9541, -3.1157 (4 decimals)

**3. Contact & Presence Fields** (phone, email, website_url, social_media URLs):
- **Strategy:** Allow higher-quality crowdsourced to win if official is null/sparse
- **Quality scoring (deterministic, structure-based only):**

  **Phone quality signals (descending priority):**
  1. Parseable international format (e.g., E.164 or equivalent)
  2. Contains country code
  3. Greater digit count after normalization
  4. Non-empty

  **Email quality signals:**
  1. Valid RFC-style format
  2. Domain not in common free-email provider list (optional but acceptable)
  3. Longer normalized length (capped at reasonable max)
  4. Non-empty

  **Website/URL quality signals:**
  1. HTTPS preferred over HTTP
  2. Path depth preferred (entity-specific pages over homepage)
  3. Absence of tracking parameters
  4. Longer normalized URL (capped at reasonable max)
  5. Non-empty

- **Rule:** Quality scoring must be deterministic and based only on string structure (no network calls)
- **Tie-break:** quality score → `trust_tier` → `default_priority` → lexicographic `source_name`
- **Example:** Crowdsourced `"+441316696000"` (formatted, international) beats official `null`

**4. Canonical Dimension Arrays** (canonical_activities, canonical_roles, canonical_place_types, canonical_access):
- **Strategy:** Union + dedupe + stable sort
- **Algorithm:**
  1. Collect all values from all sources (union)
  2. Deduplicate exact matches (case-sensitive)
  3. Sort lexicographically (stable ordering for idempotency)
- **No weighting or ranking logic** (all values equal after union)
- **Example:**
  ```python
  Source A: ["football", "padel"]
  Source B: ["football", "tennis"]
  Source C: ["padel"]
  → Union: ["football", "padel", "tennis"]  # Lexicographic order
  ```

**5. Modules JSONB** (core, location, contact, hours, sports_facility, etc.):
- **Strategy:** Deep merge recursively with per-leaf selection
- **Structural conflict resolution:**
  - `object` vs `object` → deep merge recursively
  - `array` vs `array`:
    - **Arrays of scalars** (strings, numbers, booleans) → concatenate + deduplicate + lexicographic sort
    - **Arrays of objects** → selected wholesale from winner using deterministic cascade (no partial deep merge without explicit stable IDs)
  - Type mismatch (object vs array vs scalar) → higher `trust_tier` wins wholesale
- **Per-leaf selection (when both sources have compatible types):**
  1. Compare `trust_tier` (high > medium > low)
  2. If tie, compare `confidence` (if present in extraction metadata, normalized to 0.0–1.0)
  3. If tie, compare completeness (non-null > more nested fields > longer values)
  4. If tie, use `default_priority` → lexicographic `source_name`
- **Confidence usage clarification:** Confidence is used only when present in extraction metadata (attached to ExtractedEntity or field-level provenance). If confidence is absent, merger skips this tie-breaker and proceeds to completeness. The system does not assume confidence is universally available.
- **Confidence normalization:** When confidence is present, normalize to 0.0–1.0 internally before comparison
- **Provenance tracking:** Record `source_name` if structural conflict occurs (optional but encouraged)
- **Example:**
  ```python
  Source A (trust=high): {"football_pitches": {"total": 6}}
  Source B (trust=medium): {"football_pitches": {"total": 8, "indoor": 4}}
  → Merged: {"football_pitches": {"total": 6, "indoor": 4}}  # total from A (higher trust), indoor from B (only source)
  ```

**6. Provenance/External IDs** (source_info, external_ids, discovered_by):
- **Strategy:** Always union, never overwrite
- **Fields:**
  - `discovered_by`: Union of all `source_name` values (array)
  - `primary_source`: Source with highest `trust_tier` (string)
  - `external_ids`: Union all connector-specific IDs (object with source keys)
- **Example:**
  ```python
  Source A: {"discovered_by": ["google_places"], "external_ids": {"google_places": "ChIJabc..."}}
  Source B: {"discovered_by": ["sport_scotland"], "external_ids": {"sport_scotland": "EH-PAD-001"}}
  → Merged: {
      "discovered_by": ["google_places", "sport_scotland"],
      "primary_source": "sport_scotland",  # Assuming trust_tier=high
      "external_ids": {
          "google_places": "ChIJabc...",
          "sport_scotland": "EH-PAD-001"
      }
  }
  ```

**Deterministic Tie-Breakers (Cascade for Idempotency):**

When multiple sources have identical trust/quality/completeness, cascade through:

1. **Trust tier** (`trust_tier` metadata: high > medium > low)
2. **Quality score** (for contact fields: structure-based quality metrics)
3. **Completeness** (non-null > longer string > more array elements > more nested fields)
4. **Connector default_priority** (from registry metadata, lower number = higher priority)
5. **Lexicographic source_name** (alphabetical order, ensures stable output)

**Canonical Function Signature:**

```python
# engine/orchestration/entity_merger.py
def merge_entity_group(
    entity_group: List[ExtractedEntity],
    *,
    connector_registry: ConnectorRegistry
) -> Entity:
    """
    Merge grouped entities (same real-world entity) into single canonical entity.

    Args:
        entity_group: Entities already grouped by deduplication
        connector_registry: Provides trust_tier and default_priority metadata

    Returns:
        Entity: Merged entity with best data from all sources

    Guarantees:
        - Idempotent: Same inputs always produce identical output
        - Domain-blind: No vertical-specific logic
        - Metadata-driven: Uses connector registry, not hardcoded names
        - Deterministic: All conflicts resolved via cascading tie-breakers
    """
    # Implementation follows field-group strategies above
```

**Implementation Sequencing:**

**Phase 1: Core Merge Infrastructure**
1. Create `engine/orchestration/entity_merger.py` with base merge logic
2. Implement deterministic field selectors (identity, geo, contact)
3. Implement canonical array union + sort
4. Wire into EntityFinalizer (receives merged entities, not groups)

**Phase 2: Module Deep Merge**
1. Implement recursive module merger
2. Handle object/array/type mismatches
3. Normalize confidence scores (0.0–1.0)
4. Track structural conflict provenance

**Phase 3: Quality Scoring**
1. Implement contact field quality scoring (phone, email, URL)
2. Structure-based only (no network calls)
3. Deterministic and testable

**Validation & Acceptance Criteria:**

Decision 5 is complete when:

**Core Functionality:**
- ✅ Merge runs after deduplication grouping and before persistence
- ✅ Trust model uses connector registry metadata (no hardcoded connector names in merge logic beyond examples)
- ✅ All 6 field-group strategies implemented (identity, geo, contact, canonical arrays, modules, provenance)
- ✅ Deterministic tie-breakers cascade correctly (trust → quality → completeness → priority → lexicographic)

**Contact Field Quality:**
- ✅ Phone quality: international format > country code > digit count > non-empty
- ✅ Email quality: RFC format > non-free-provider > length > non-empty
- ✅ URL quality: HTTPS > path depth > no tracking params > length > non-empty
- ✅ Quality scoring is deterministic and structure-based only (no network calls)

**Geo Precision:**
- ✅ Precision metadata preferred if provided
- ✅ Else trust tier, else decimal precision
- ✅ NO centroid calculation (deterministic selection only)

**Canonical Arrays:**
- ✅ Union all sources
- ✅ Deduplicate exact matches
- ✅ Lexicographically sorted (stable ordering)

**Modules Deep Merge:**
- ✅ object vs object: deep merge recursively
- ✅ array vs array (scalars): concatenate + dedupe + lexicographic sort
- ✅ array vs array (objects): selected wholesale from winner (trust → confidence → completeness → priority → lex source)
- ✅ No partial deep merge of object arrays without explicit stable IDs
- ✅ Type mismatch: higher trust wins wholesale
- ✅ Confidence used only when present in extraction metadata (skipped if absent)
- ✅ Confidence scores normalized to 0.0–1.0 when present before comparison
- ✅ Structural conflicts logged (provenance tracked)

**Test Scenarios (Real Fixtures):**

Using Powerleague Portobello group (Google Places + Sport Scotland):

**Test 1: Contact Override**
- **Setup:** Official source has null phone/website, crowdsourced has quality values
- **Expected:** Crowdsourced contact fields fill official nulls
- **Verification:** Entity has phone/website from crowdsourced source

**Test 2: Inventory Conflict**
- **Setup:** Official says 6 courts, crowdsourced says 8 courts
- **Expected:** Official count beats crowdsourced
- **Verification:** `sports_facility.football_pitches.total = 6`

**Test 3: Canonical Union**
- **Setup:** Source A has `["football", "padel"]`, Source B has `["football", "tennis"]`
- **Expected:** Union: `["football", "padel", "tennis"]` (lexicographic order)
- **Verification:** Canonical array is stable and deduped

**Test 4: Tie-Break Determinism**
- **Setup:** Run merge twice with same inputs
- **Expected:** Identical output both times
- **Verification:** SHA-256 hash of merged entity matches across runs

**Test 5: Same-Trust Conflict**
- **Setup:** Two sources both have `trust_tier=high`, different field values
- **Expected:** `default_priority` cascade, then lexicographic
- **Verification:** Correct source wins based on priority metadata

**Test 6: All-Null Inputs**
- **Setup:** All sources have null for a particular field
- **Expected:** Merged entity has null (graceful handling)
- **Verification:** No crash, null preserved

**Test 7: Module Structural Mismatch**
- **Setup:** Source A has `{"total": 6}`, Source B has `[{"type": "indoor", "count": 4}]` (object vs array)
- **Expected:** Higher trust source wins wholesale (no partial merge)
- **Verification:** Merged module uses higher-trust structure

**Files to Create:**
- `engine/orchestration/entity_merger.py` (merge logic)
- `engine/orchestration/field_selectors.py` (field-group strategies)
- `engine/orchestration/quality_scoring.py` (contact field quality)
- `tests/engine/orchestration/test_entity_merger.py` (test suite with real fixtures)

**Files to Update:**
- `engine/orchestration/entity_finalizer.py` (wire up merger, receives merged entities)
- `engine/orchestration/registry.py` (ensure trust_tier and default_priority metadata present)

**Non-Goals:**

- ❌ Do NOT introduce domain-specific branching in merge logic ("if padel then...")
- ❌ Do NOT hardcode connector names in merge rules (use metadata only, examples OK)
- ❌ Do NOT compute geographic centroids (prefer deterministic selection)
- ❌ Do NOT introduce permanent naming translation layer (Decision 4 stands)
- ❌ Do NOT make network calls for quality validation (structure-based only)
- ❌ Do NOT block on field-level provenance schema changes (optional enhancement)

**Impact:** Enables accurate, complete entity records from multiple imperfect sources while maintaining engine purity, idempotency, and architectural scalability. Resolves the "winner-take-all" problem where valuable data from secondary sources was discarded.

---

## Implementation Phases

### Phase 0: Design (Before Any Code)

**Duration:** 1-2 days
**Deliverables:** Design documents for all 5 decisions
**Quality Gate:** All design decisions documented and agreed

**Tasks:**
1. Design lens injection pattern → Document: `lens-injection-design.md`
2. Author complete `edinburgh_finds/lens.yaml` (all 6 sections)
3. Design module field extraction algorithm → Document: `module-extraction-design.md`
4. Choose canonical field names → Document: `field-naming-conventions.md`
5. Design multi-source merge algorithm → Document: `entity-merging-algorithm.md`

**Validation:** Review each document against VISION.md principles

---

### Phase 1: Query Vocabulary (First Executable)

**Duration:** 0.5 days
**Scope:** Query interpretation only
**Test Entity:** Powerleague Portobello

**Objective:** Prove query interpretation extracts correct features

**Implementation:**
1. Write `lenses/edinburgh_finds/query_vocabulary.yaml` (activities, locations, facilities)
2. Test: QueryLens correctly parses "5-a-side football in Portobello"
   - Expected: activity_keywords match ["football"]
   - Expected: location_indicators match ["portobello"]

**Quality Gates:**
- ✅ Query features correctly extracted for test queries
- ✅ No hardcoded logic (all vocabulary in YAML)
- ✅ Tests pass with real QueryLens loading

**Deliverable:** Working query vocabulary configuration

---

### Phase 2: Connector Selection Rules

**Duration:** 0.5 days
**Scope:** Orchestration connector routing
**Dependencies:** Phase 1 complete

**Objective:** Prove orchestration selects correct connectors for query

**Implementation:**
1. Write `lenses/edinburgh_finds/connector_rules.yaml` (routing rules for connectors lens uses)
2. Test: Orchestration selects correct connectors for "Powerleague Portobello"
   - Expected: Google Places (always), Sport Scotland (football keyword), OSM (location)
   - Not Expected: Open Charge Map (no EV charging query)

**Quality Gates:**
- ✅ Connector selection driven by lens rules, not hardcoded
- ✅ All connectors used by this lens have routing rules; no unknown connectors referenced
- ✅ Test query selects appropriate subset

**Deliverable:** Working connector routing configuration

---

### Phase 3: Raw Ingestion Validation

**Duration:** 0.5 days
**Scope:** Connector execution and data storage
**Dependencies:** Phase 2 complete

**Objective:** Prove connectors fetch real data and store to RawIngestion table

**Implementation:**
1. Run orchestration with real API calls (not mocks)
2. Inspect RawIngestion table records
3. Verify data stored on filesystem
4. Verify deduplication (SHA-256 hash prevents duplicate ingestion)

**Quality Gates:**
- ✅ Multiple sources return data for Powerleague Portobello
- ✅ Raw JSON stored correctly
- ✅ Deduplication prevents duplicate raw records
- ✅ Source metadata captured (source, timestamp, hash)

**Deliverable:** RawIngestion records for test entity from multiple sources

---

### Phase 4: Field Name Alignment

**Duration:** 0.5 days
**Scope:** Fix field naming throughout pipeline
**Dependencies:** Phase 0 (field naming decision)

**Objective:** Align extractor output → Entity schema → EntityFinalizer expectations

**Implementation:**
1. Update all 6 extractors to use canonical field names
2. Update EntityFinalizer to expect canonical field names
3. Update Entity schema if needed
4. Run end-to-end test: extraction → finalization

**Quality Gates:**
- ✅ All extractors output consistent field names
- ✅ EntityFinalizer reads correct fields
- ✅ No data loss due to field name mismatch
- ✅ Tests updated with new field names

**Deliverable:** Consistent field naming throughout pipeline

---

### Phase 5: Lens Injection Implementation

**Duration:** 1 day
**Scope:** Wire lens configuration into extraction
**Dependencies:** Phase 0 (lens injection design), Phase 4 (field names)

**Objective:** Prove extractors receive and consume VerticalLens configuration

**Implementation:**
1. Implement chosen lens injection pattern (e.g., LensRegistry.get_lens("edinburgh_finds"))
2. Update extract_entity() to load and inject lens
3. Pass lens_contract to extract_with_lens_contract()
4. Test: Extractor receives lens configuration

**Quality Gates:**
- ✅ VerticalLens loaded during extraction
- ✅ lens_contract contains mapping_rules, modules, triggers
- ✅ No hardcoded lens selection (injection pattern is generic)
- ✅ Tests validate lens injection

**Deliverable:** Lens configuration flows to extractors

---

### Phase 6: Mapping Rules Application

**Duration:** 1 day
**Scope:** Apply lens mapping rules to populate canonical dimensions
**Dependencies:** Phase 5 (lens injection)

**Objective:** Prove raw categories → canonical dimensions via mapping rules

**Implementation:**
1. Ensure extractors populate `raw_categories` field
2. Wire up mapping rule application in extract_with_lens_contract()
3. Populate canonical_activities, canonical_roles, canonical_place_types, canonical_access
4. Test: Entity has correct canonical dimensions

**Test Case - Powerleague Portobello:**
```
Input (raw_categories): ["Sports Complex", "Football Facility", "5-a-side venue"]
Mapping rules applied:
  - "(?i)football|5.?a.?side" → canonical_activities: ["football"]
  - "(?i)sports complex" → canonical_place_types: ["sports_centre"]
  - "(?i)facility|venue" → canonical_roles: ["provides_facility"]
Output:
  canonical_activities: ["football", "padel"]  # if both detected
  canonical_roles: ["provides_facility"]
  canonical_place_types: ["sports_centre"]
  canonical_access: ["pay_and_play"]
```

**Quality Gates:**
- ✅ Canonical dimension arrays populated (not empty)
- ✅ Values match lens canonical_values definitions
- ✅ Confidence scores tracked per mapping
- ✅ No hardcoded dimension values in engine code

**Deliverable:** Canonical dimensions correctly populated

---

### Phase 7: Module Triggers & Attachment

**Duration:** 0.5 days
**Scope:** Attach domain modules based on lens triggers
**Dependencies:** Phase 6 (canonical dimensions populated)

**Objective:** Prove module_triggers correctly attach sports_facility module

**Implementation:**
1. Wire up ModuleTrigger evaluation in extract_with_lens_contract()
2. Check: If canonical_activities contains football/padel AND entity_class is place → attach sports_facility
3. Initialize module namespaces in modules JSONB
4. Test: Entity has sports_facility module attached

**Test Case - Powerleague Portobello:**
```
Input:
  canonical_activities: ["football", "padel"]
  entity_class: "place"

Module Trigger:
  when:
    dimension: canonical_activities
    values: [football, padel, tennis]
  add_modules: [sports_facility]
  conditions:
    - entity_class: place

Output:
  modules: {
    "core": {...},
    "location": {...},
    "contact": {...},
    "sports_facility": {}  # ← Attached (empty for now)
  }
```

**Quality Gates:**
- ✅ Triggers evaluate correctly based on canonical dimensions
- ✅ Correct modules attached for entity type
- ✅ Module namespacing enforced (validated by ModuleValidator)
- ✅ No modules attached when triggers don't match

**Deliverable:** Domain modules correctly triggered and attached

---

### Phase 8: Module Field Extraction

**Duration:** 2 days
**Scope:** Implement declarative module field extraction using lens-defined rules
**Dependencies:** Phase 7 (modules attached), Decision 3 (extraction algorithm resolved)

**Objective:** Prove sports_facility module populated with facility inventory using declarative field rules

**Implementation:**

**8.1 Create Generic Module Extractor (Engine)**
```python
# engine/extraction/module_extractor.py
def extract_module_fields(
    raw_data: dict,
    module_def: dict,
    *,
    source_name: str,
    entity_class: str
) -> dict:
    """
    Generic module field extractor - executes lens-defined rules.

    Args:
        raw_data: Raw payload from connector
        module_def: Module definition from lens contract (includes field_rules)
        source_name: Which connector this data came from
        entity_class: Entity class (place, person, etc.)

    Returns:
        dict: Extracted module fields
    """
    # Phase 1: Deterministic extraction
    # Phase 2: LLM extraction (if needed)
    # Returns populated module dict
```

**8.2 Implement Extractor Vocabulary**
```python
# engine/extraction/extractors/deterministic.py
class NumericParser:
    """Extract numeric values from strings or numbers"""

class RegexCapture:
    """Extract values matching regex pattern"""

class JsonPath:
    """Extract value at JSON path"""

class BooleanCoercion:
    """Convert values to boolean"""

# engine/extraction/extractors/llm.py
class LLMStructured:
    """Schema-bound structured extraction via Instructor"""
```

**8.3 Update Lens with Field Rules**
```yaml
# lenses/edinburgh_finds/lens.yaml
modules:
  sports_facility:
    description: "Sports facility inventory"
    field_rules:
      # Deterministic extraction from Sport Scotland
      - rule_id: football_pitch_total_sport_scotland
        target_path: football_pitches.five_a_side.total
        source_fields: [NumPitches, pitches_total]
        extractor: numeric_parser
        confidence: 0.95
        applicability:
          source: [sport_scotland]
          entity_class: [place]

      - rule_id: football_pitch_surface
        target_path: football_pitches.five_a_side.surface
        source_fields: [Surface, surface_type]
        extractor: regex_capture
        pattern: "(?i)(3G|4G|grass|artificial)"
        confidence: 0.85
        normalizers: [lowercase, list_wrap]
        applicability:
          source: [sport_scotland]

      # LLM extraction from unstructured descriptions
      - rule_id: football_pitch_llm_google
        target_path: football_pitches.five_a_side
        source_fields: [description, editorial_summary]
        extractor: llm_structured
        schema:
          total: integer
          indoor: integer
          outdoor: integer
        confidence: 0.70
        applicability:
          source: [google_places, serper]
        conditions:
          - field_not_populated: football_pitches.five_a_side.total
```

**8.4 Wire Up in BaseExtractor**
```python
# engine/extraction/base.py
def extract_with_lens_contract(
    raw_data: dict,
    lens_contract: dict,
    *,
    source_name: str  # REQUIRED for module extraction applicability
) -> dict:
    """
    Apply lens mapping rules and module field extraction.

    CANONICAL SIGNATURE - used everywhere this function is called.

    Args:
        raw_data: Complete raw payload (NOT subset)
        lens_contract: Full lens.yaml as dict
        source_name: Connector name (e.g., "sport_scotland")

    Returns:
        dict: canonical dimensions + modules populated per lens rules
    """
    # Step 1: Extract canonical dimensions using mapping_rules
    # (runs over union of source_fields, NOT hardcoded to raw_categories)
    canonical_dimensions = apply_mapping_rules(
        raw_data,
        lens_contract["mapping_rules"],
        source_name=source_name
    )

    # Step 2: Determine which modules to attach using module_triggers
    entity_class = resolve_entity_class(raw_data)
    required_modules = evaluate_module_triggers(
        canonical_dimensions,
        entity_class,
        lens_contract["module_triggers"]
    )

    # Step 3: Extract module fields using field_rules
    modules_data = {}
    for module_name in required_modules:
        module_def = lens_contract["modules"].get(module_name, {})

        modules_data[module_name] = extract_module_fields(
            raw_data,
            module_def,
            source_name=source_name,  # For applicability filtering
            entity_class=entity_class
        )

    return {
        **canonical_dimensions,
        "modules": modules_data
    }
```

**Extractor Usage:**
```python
# engine/extraction/extractors/sport_scotland.py
class SportScotlandExtractor(BaseExtractor):
    source_name = "sport_scotland"  # Class attribute

    def extract(self, raw_data: Dict, *, ctx: ExecutionContext) -> Dict:
        # Basic fields
        basic = {...}

        # Lens-derived fields
        lens_fields = self.apply_lens_contract(
            raw_data,
            ctx=ctx,
            source_name=self.source_name  # Pass for applicability
        )

        return {**basic, **lens_fields}
```

**Test Case - Powerleague Portobello:**

```
Input (Sport Scotland WFS):
  raw_data: {
    "FacilityType": "Football Pitches",
    "NumPitches": 6,
    "Surface": "3G Artificial",
    "Indoor": 0,
    "Outdoor": 6
  }
  source_name: "sport_scotland"

Lens Field Rules Applied:
  1. rule: football_pitch_total_sport_scotland
     - source_fields: [NumPitches] → 6
     - extractor: numeric_parser
     - target_path: football_pitches.five_a_side.total
     - result: 6

  2. rule: football_pitch_surface
     - source_fields: [Surface] → "3G Artificial"
     - extractor: regex_capture, pattern: "(3G|4G|grass)"
     - normalizers: [lowercase, list_wrap]
     - target_path: football_pitches.five_a_side.surface
     - result: ["3g"]

Output:
  modules: {
    "sports_facility": {
      "football_pitches": {
        "five_a_side": {
          "total": 6,
          "indoor": 0,
          "outdoor": 6,
          "surface": ["3g"]
        }
      }
    }
  }
```

**Quality Gates:**
- ✅ Module fields populated with actual data (not empty)
- ✅ Extraction driven by lens field rules (no hardcoded logic)
- ✅ Nested structure preserved (football_pitches.five_a_side.total)
- ✅ Source-specific extraction rules work (applicability filtering)
- ✅ Deterministic extractors work for structured sources
- ✅ LLM extraction works under constraints (schema-bound, confidence-capped)
- ✅ Null/missing fields handled gracefully
- ✅ ModuleValidator passes (structure correct)
- ✅ Engine purity maintained (no domain logic)
- ✅ Tests use real payload fixtures

**Deliverable:** Rich facility data in modules JSONB, extracted using declarative lens rules

---

### Phase 9: Entity Classification

**Duration:** 0.5 days
**Scope:** Validate entity_class assignment
**Dependencies:** Phase 8 (extraction complete)

**Objective:** Prove entity_class correctly assigned as "place"

**Implementation:**
1. Verify resolve_entity_class() logic
2. Test: Powerleague Portobello classified as "place" (has coordinates, not time-bounded)
3. Test: Coach entity classified as "person"
4. Test: Event classified as "event" (has time_range)

**Quality Gates:**
- ✅ Classification deterministic (no LLM guessing)
- ✅ Priority order correct (time-bounded > place > org > person > thing)
- ✅ 100% accuracy for test cases

**Deliverable:** Correct entity_class for all test entities

---

### Phase 10: Multi-Source Deduplication

**Duration:** 1 day
**Scope:** Group duplicate entities from different sources
**Dependencies:** Phase 9 (classification)

**Objective:** Prove Google Places + Sport Scotland records recognized as same entity

**Implementation:**
1. Implement 3-tier deduplication (external IDs, geo-based, SHA-1)
2. Group ExtractedEntity records by detected duplicates
3. Pass grouped entities to EntityFinalizer

**Test Case - Powerleague Portobello:**
```
Input:
  ExtractedEntity #1 (Google Places):
    entity_name: "Powerleague Portobello"
    latitude: 55.9541
    longitude: -3.1157
    source: "google_places"

  ExtractedEntity #2 (Sport Scotland):
    entity_name: "Powerleague Edinburgh - Portobello"
    latitude: 55.9542
    longitude: -3.1156
    source: "sport_scotland"

Deduplication:
  Tier 1 (External IDs): No match (different ID systems)
  Tier 2 (Geo-based): MATCH (name similarity + distance < 50m)

Output:
  entity_group: [ExtractedEntity #1, ExtractedEntity #2]
```

**Quality Gates:**
- ✅ Same entity from multiple sources correctly grouped
- ✅ Different entities never merged (no false positives)
- ✅ >99% deduplication accuracy on test set

**Deliverable:** Grouped entities ready for merging

---

### Phase 11: Field-Level Merging

**Duration:** 1.5 days
**Scope:** Merge grouped entities with trust-based conflict resolution
**Dependencies:** Phase 10 (deduplication), Phase 0 (merge algorithm design)

**Objective:** Prove field-level trust hierarchy correctly resolves conflicts

**Implementation:**
1. Implement EntityMerger with trust-based field selection
2. Merge universal fields (name, address, contact)
3. Merge canonical dimensions (union arrays, deduplicate)
4. Deep merge modules with trust-based field selection
5. Track source_info provenance

**Test Case - Powerleague Portobello:**
```
Input:
  Google Places (trust: crowdsourced):
    entity_name: "Powerleague Portobello"
    phone: "+441316696000"
    website_url: "https://powerleague.co.uk"
    canonical_activities: ["football"]
    modules.sports_facility: {}  # Empty

  Sport Scotland (trust: official):
    entity_name: "Powerleague Edinburgh - Portobello"
    phone: null
    website_url: null
    canonical_activities: ["football"]
    modules.sports_facility: {
      football_pitches: {five_a_side: {total: 6}}
    }

Merge Output:
  entity_name: "Powerleague Portobello"  # Google (more concise)
  phone: "+441316696000"  # Google (only source)
  website_url: "https://powerleague.co.uk"  # Google (only source)
  canonical_activities: ["football"]  # Union (same value)
  modules.sports_facility: {
    football_pitches: {five_a_side: {total: 6}}  # Sport Scotland (official)
  }
  source_info: {
    discovered_by: ["google_places", "sport_scotland"]
    primary_source: "sport_scotland"  # Official trust
    verified_date: "2026-01-28"
  }
```

**Quality Gates:**
- ✅ Trust hierarchy respected (official > crowdsourced)
- ✅ Field-level decisions correct (most complete + trust)
- ✅ Canonical dimensions unioned correctly
- ✅ Modules deep merged (nested fields)
- ✅ Source provenance tracked

**Deliverable:** Merged entity with best data from all sources

---

### Phase 12: Entity Finalization & Persistence

**Duration:** 0.5 days
**Scope:** Generate slug, upsert to Entity table
**Dependencies:** Phase 11 (merging)

**Objective:** Prove merged entity correctly persisted to database

**Implementation:**
1. EntityFinalizer generates URL-safe slug
2. Upsert to Entity table (idempotent)
3. Store source_info, external_ids
4. Verify Entity record in database

**Test Case - Powerleague Portobello:**
```
Input (merged entity):
  entity_name: "Powerleague Portobello"
  entity_class: "place"
  canonical_activities: ["football", "padel"]
  canonical_roles: ["provides_facility"]
  canonical_place_types: ["sports_centre"]
  canonical_access: ["pay_and_play"]
  modules: {sports_facility: {...}}

EntityFinalizer:
  1. Generate slug: "powerleague-portobello"
  2. Upsert to Entity table

Database Query:
  SELECT * FROM entities WHERE slug = 'powerleague-portobello'

Expected Result:
  entity_id: "ent_abc123"
  entity_name: "Powerleague Portobello"
  slug: "powerleague-portobello"
  entity_class: "place"
  canonical_activities: ["football", "padel"]
  canonical_roles: ["provides_facility"]
  canonical_place_types: ["sports_centre"]
  canonical_access: ["pay_and_play"]
  modules: {
    "core": {...},
    "location": {...},
    "contact": {...},
    "sports_facility": {
      "football_pitches": {...},
      "padel_courts": {...}
    }
  }
  source_info: {
    "discovered_by": ["google_places", "sport_scotland"],
    "primary_source": "sport_scotland",
    "verified_date": "2026-01-28"
  }
```

**Quality Gates:**
- ✅ Slug generation correct (URL-safe, unique)
- ✅ Idempotency proven (re-run updates, doesn't duplicate)
- ✅ All fields populated correctly
- ✅ Canonical dimensions are arrays (not empty)
- ✅ Modules properly namespaced (ModuleValidator passes)
- ✅ Source provenance tracked

**Deliverable:** Complete, accurate Entity record in database

---

### Phase 13: End-to-End Validation

**Duration:** 0.5 days
**Scope:** Prove complete workflow
**Dependencies:** Phase 12 (persistence)

**Objective:** Run one query, validate Entity table has complete data

**Test Execution:**
```bash
# Run orchestration with real query
python -m engine.orchestration.cli run "Powerleague Portobello"

# Inspect Entity table
SELECT
  entity_name,
  entity_class,
  canonical_activities,
  canonical_roles,
  canonical_place_types,
  canonical_access,
  modules->'sports_facility' as facility_data,
  source_info
FROM entities
WHERE slug = 'powerleague-portobello';
```

**Validation Checklist:**
- ✅ Query interpreted correctly (activity: football, location: portobello)
- ✅ Connectors selected correctly (Google Places, Sport Scotland, OSM)
- ✅ RawIngestion records created from multiple sources
- ✅ Extraction produced structured data
- ✅ Mapping rules applied (canonical dimensions populated)
- ✅ Modules triggered and attached (sports_facility)
- ✅ Module fields extracted (football_pitches, padel_courts)
- ✅ Entity classified correctly (entity_class: place)
- ✅ Multi-source deduplication grouped entities
- ✅ Field-level merging applied trust hierarchy
- ✅ Entity finalized with slug and source_info
- ✅ Database record complete and accurate
- ✅ Re-running query updates (not duplicates)

**Success Criteria:**
Entity table contains complete record with:
- ✅ All universal fields (name, location, contact)
- ✅ All canonical dimensions populated (activities, roles, place_types, access)
- ✅ Modules properly structured (namespaced JSONB)
- ✅ Rich facility data (court counts, surfaces, amenities)
- ✅ Source provenance tracked
- ✅ >80% field population where data available

**Deliverable:** Proof of end-to-end architecture working

---

## Testing Strategy

### Unit Tests
- Every function tested in isolation
- Mock external dependencies (API calls, database)
- Test success and failure cases
- Coverage target: >80%

### Integration Tests
- Test complete flows (ingestion → extraction, extraction → finalization)
- Use real connectors with actual API calls (not mocks)
- Validate database transactions
- Snapshot testing for extraction outputs

### End-to-End Tests
- Full pipeline: Query → Entity table
- Real API calls, real database writes
- Idempotency tests (run twice, verify single record)
- Multi-source merge validation

### Validation Tests
- Entity table inspection queries
- Field population completeness checks
- Canonical dimension accuracy validation
- Module structure validation (ModuleValidator)

---

## Quality Gates (Every Phase)

Before marking phase complete:

1. **Tests Pass**
   - All unit tests green
   - Integration tests pass with real data
   - No failing edge cases

2. **Design Principles Validated**
   - Engine purity maintained (no vertical-specific logic)
   - Module namespacing enforced
   - Lens-driven behavior (no hardcoded domain logic)

3. **Real Data Validation**
   - Run with actual API calls (not mocks)
   - Inspect database records
   - Verify field population

4. **Documentation Updated**
   - Code comments clear
   - Design decisions documented
   - Examples provided

5. **Banked Progress Confirmed**
   - No known refactoring needed
   - Architecture scales to next phase
   - Quality production-ready

---

## Risk Mitigation

### Risk 1: API Rate Limits
**Mitigation:** Use cached RawIngestion records for testing, only fetch fresh when testing ingestion

### Risk 2: LLM Extraction Variability
**Mitigation:** Use structured sources (Sport Scotland, Google Places) for initial proof, add LLM extraction later

### Risk 3: Module Extraction Complexity
**Mitigation:** Start with simple module fields (counts, booleans), add complex nested fields incrementally

### Risk 4: Deduplication False Positives
**Mitigation:** Manual review of first 100 grouped entities, tune distance thresholds

### Risk 5: Field Naming Confusion
**Mitigation:** Document canonical field names upfront, enforce in code review

---

## Success Metrics

**Completeness:**
- Universal fields: >95% populated
- Canonical dimensions: >90% populated
- Modules attached: 100% where triggered
- Module fields: >80% where applicable

**Accuracy:**
- entity_class: 100% (deterministic)
- Canonical dimensions: >99% (validated against ground truth)
- Deduplication: >99% (same entity merged, different separated)
- No hallucinations: 100% (extract only observed data)

**Performance:**
- Orchestration latency: <30 seconds per query
- Extraction latency: <5 seconds per entity
- Database write latency: <1 second per entity

**Architecture:**
- Engine purity tests: 100% pass
- Module validation: 100% pass
- Lens-driven behavior: All decisions via lens config

---

## Next Steps

**Immediate:**
1. Review this implementation plan against VISION.md
2. Use superpowers:writing-plans to break Phase 0 into tasks
3. Complete all 5 design decisions before Phase 1 code

**Before Coding:**
- All design decisions documented and agreed
- edinburgh_finds/lens.yaml complete (all 6 sections)
- Field naming conventions established
- Merge algorithm specified

**First Implementation:**
- Phase 1: Query Vocabulary (prove query interpretation)
- Small, testable, foundational

---

## Reference Documents

- **Vision:** `VISION.md` - Architectural principles and success criteria
- **Project Instructions:** `CLAUDE.md` - Development commands and conventions
- **Tech Stack:** `conductor/tech-stack.md` - Technology choices
- **Workflow:** `conductor/workflow.md` - TDD process and quality gates

---

**Document Status:** Draft Implementation Plan
**Requires:** Design decision completion (Phase 0) before execution
**Test Entity:** Powerleague Portobello (concrete validation)
**Quality Principle:** Banked progress only - no throwaway work
