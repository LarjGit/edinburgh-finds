# Edinburgh Finds - System Vision

**Last Updated:** 2026-01-29 (Decision 5: Deterministic Multi-Source Entity Merge added)
**Purpose:** Define the architectural principles and success criteria for the Edinburgh Finds universal entity extraction platform.

---

## Core Mission

**Build a horizontal, vertical-agnostic entity extraction engine that transforms natural language queries into complete, accurate entity records through AI-powered multi-source orchestration.**

The engine is **universal** - it stores and processes entities using generic classifications and opaque dimensions. All vertical-specific logic (sports, wine, restaurants, events) lives in **pluggable Lens configurations**.

**Edinburgh Finds** is the first vertical lens - an Edinburgh-centric discovery platform for sports venues, retailers, clubs, events, and coaches. It proves the system's vertical independence and serves as the reference implementation.

**Scaling Strategy:** Adding a new vertical (Wine Discovery, Restaurant Finder, Event Calendar) requires **ZERO engine code changes** - only a new Lens configuration.

---

## Architectural Principles

### 1. Engine Purity (Vertical-Agnostic)

The engine is **completely domain-blind**. It must never know about specific verticals.

**Forbidden in Engine Code:**
- Domain-specific terms: "tennis", "wine", "restaurant", "vintage", "court"
- Vertical-specific logic: "if activity is padel..."
- Hardcoded taxonomies: lists of sports, wine regions, cuisine types

**Engine Responsibilities:**
- Classify entities by universal type: `place`, `person`, `organization`, `event`, `thing`
- Store multi-valued dimensions as opaque Postgres `text[]` arrays with GIN indexes
- Orchestrate multi-source data fetching using Lens-provided routing rules
- Extract structured data from raw sources
- Apply Lens mapping rules to populate canonical dimensions
- Merge and deduplicate entities across sources
- Store universal modules: `core`, `location`, `contact`, `hours`, `amenities`, `time_range`

**Enforcement:** Automated purity tests (`tests/engine/test_purity.py`) prevent engine code from importing Lens modules or performing literal string comparisons on dimension values.

### 2. Lens Layer (Vertical-Specific Interpretation)

Lenses provide **all domain knowledge** through YAML configuration files. The engine consumes these configurations but never hardcodes their content.

**Lens Responsibilities:**
- Define domain vocabulary (activity keywords, location indicators, facility types)
- Provide connector routing rules (which data sources to use for this vertical)
- Define mapping rules (raw observations → canonical dimension values)
- Define module triggers (when to attach domain-specific data modules)
- Provide canonical value metadata (display names, SEO slugs, icons, descriptions)
- Define derived groupings for navigation (e.g., "Coaches & Instructors" = people with role "provides_instruction")

**Lens Configuration Structure:**
```yaml
# lenses/edinburgh_finds/lens.yaml
vocabulary:
  activity_keywords: [tennis, padel, squash, swimming, gym, yoga]
  location_indicators: [edinburgh, leith, portobello]

connector_rules:
  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [tennis, padel, squash]

mapping_rules:
  - pattern: "(?i)tennis|racket sports"
    dimension: canonical_activities
    value: tennis
    confidence: 0.95

module_triggers:
  - when:
      dimension: canonical_activities
      values: [tennis]
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

canonical_values:
  tennis:
    display_name: "Tennis"
    seo_slug: "tennis"
    icon: "racquet"
    description: "Tennis courts and clubs"
```

**Current Status:** Query vocabulary and connector routing are implemented and working. Mapping rules and module triggers are designed but not yet wired up in extraction flow.

### 3. Lens Injection Architecture (Engine-Lens Integration)

The engine consumes lens configurations through a strict **orchestrator-owned, context injection** pattern. This ensures engine purity, avoids global state, and enables multi-lens support without refactoring.

#### Core Principle: Orchestrator Owns, Extractors Consume

**Rule:** Only orchestration/bootstrap code may load `lens.yaml` from disk. Extractors NEVER load lenses directly and MUST NOT access LensRegistry.

**Pattern:**
1. **CLI/Bootstrap** resolves lens_id (via precedence rules), loads and validates lens.yaml once
2. **ExecutionContext** created with lens_id, lens_contract dict, optional lens_hash
3. **Context flows** through pipeline: CLI → Planner → extraction_integration → extractors
4. **Extractors** receive `ctx` parameter, use `ctx.lens_contract` when needed

#### Lens Selection Precedence

Lens is selected using first-match precedence:

1. **CLI flag:** `--lens wine_discovery` (override for testing/debugging)
2. **Environment variable:** `LENS_ID=edinburgh_finds` (environment-specific defaults)
3. **Config file:** `engine/config/app.yaml` → `default_lens: edinburgh_finds` (project default)
4. **Hardcoded fallback:** `"edinburgh_finds"` (absolute safety net)

**Config file structure:**
```yaml
# engine/config/app.yaml
default_lens: edinburgh_finds
```

**Rationale:** Allows environment-specific defaults (dev/prod), CLI override when needed, and zero code changes to modify defaults.

#### ExecutionContext Structure

ExecutionContext is a simple, explicit carrier object for run metadata:

```python
@dataclass
class ExecutionContext:
    """Runtime context passed through extraction pipeline"""

    lens_id: str                    # Which lens is active ("edinburgh_finds")
    lens_contract: dict             # Full lens.yaml content (validated once)
    lens_hash: Optional[str] = None # For reproducibility/debugging
```

**Properties:**
- **Immutable:** Created once at bootstrap, never modified
- **Plain dict contract:** Engine consumes dict, never touches YAML loader
- **Validated once:** lens.yaml validated at load time (fail-fast if malformed)
- **Complete contract:** Contains entire lens.yaml (vocabulary, connector_rules, mapping_rules, modules, module_triggers, canonical_values)

#### Code Flow: CLI → Planner → Extractors

**Bootstrap (CLI Entry Point):**
```python
# engine/orchestration/cli.py
def run_query(query: str, lens_override: Optional[str] = None):
    # 1. Resolve lens_id using precedence
    lens_id = resolve_lens_id(
        cli_flag=lens_override,
        env_var=os.getenv("LENS_ID"),
        config_file="engine/config/app.yaml",
        fallback="edinburgh_finds"
    )

    # 2. Load and validate lens.yaml (fails fast if broken)
    lens = LensRegistry.load_lens(lens_id)  # Disk I/O happens ONLY here
    lens_contract = lens.to_dict()          # Plain dict for engine consumption

    # 3. Create execution context
    ctx = ExecutionContext(
        lens_id=lens_id,
        lens_contract=lens_contract,
        lens_hash=hash_dict(lens_contract)  # Optional: for debugging
    )

    # 4. Pass context to orchestrator
    planner = OrchestrationPlanner(ctx)
    planner.execute_query(query)
```

**Orchestration (Planner):**
```python
# engine/orchestration/planner.py
class OrchestrationPlanner:
    def __init__(self, ctx: ExecutionContext):
        self.ctx = ctx  # Store context, never loads from disk

    def execute_query(self, query: str):
        # Use ctx.lens_contract for connector routing
        connector_rules = self.ctx.lens_contract["connector_rules"]

        # After ingestion, pass ctx to extraction
        extraction_integration.extract_entities(raw_ingestions, ctx=self.ctx)
```

**Extraction (Integration Layer):**
```python
# engine/orchestration/extraction_integration.py
def extract_entities(raw_ingestions: List[RawIngestion], *, ctx: ExecutionContext):
    for raw in raw_ingestions:
        extractor = get_extractor(raw.source)

        # Pass ctx to extractor (context flows through)
        extracted = extractor.extract(raw.payload, ctx=ctx)
```

**Extractor (Implementation):**
```python
# engine/extraction/extractors/google_places.py
class GooglePlacesExtractor(BaseExtractor):
    def extract(self, raw_data: dict, *, ctx: ExecutionContext) -> dict:
        # Step 1: Extract basic fields (source-specific logic)
        basic_fields = self._extract_basic_fields(raw_data)

        # Step 2: Apply lens contract for canonical dimensions and modules
        lens_fields = self.apply_lens_contract(raw_data, ctx=ctx)

        # Step 3: Merge and return
        return {**basic_fields, **lens_fields}
```

#### BaseExtractor API Update

**Updated Abstract Interface:**
```python
# engine/extraction/base.py
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, raw_data: Dict, *, ctx: ExecutionContext) -> Dict:
        """
        Transform raw data into extracted entity fields.

        Args:
            raw_data: Raw ingestion payload for a single record
            ctx: Execution context (includes lens_contract)

        Returns:
            Dict: Extracted fields with canonical dimensions populated
        """
        pass

    def apply_lens_contract(
        self,
        raw_data: Dict,
        *,
        ctx: ExecutionContext,
        source_name: str
    ) -> Dict:
        """
        Apply lens mapping rules and module triggers.

        Centralized lens usage - extractors call this helper method
        instead of accessing ctx.lens_contract directly.

        Args:
            raw_data: Original raw data
            ctx: Execution context with lens_contract
            source_name: Connector name for applicability filtering

        Returns:
            Dict: Extracted fields with canonical dimensions and modules populated
        """
        if not ctx or not ctx.lens_contract:
            raise ValueError("Missing lens_contract in execution context")

        return extract_with_lens_contract(
            raw_data,
            ctx.lens_contract,
            source_name=source_name
        )
```

**Implementation Pattern:**

The `extract_with_lens_contract(raw_data, lens_contract)` function produces **lens-derived fields only**:
- Canonical dimensions: `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`
- Domain modules: Lens-triggered modules (e.g., `sports_facility`) with populated fields

Each extractor is responsible for:
1. Extracting **basic fields** (entity_name, latitude, longitude, street_address, phone, etc.)
2. Calling `apply_lens_contract(raw_data, ctx=ctx)` to get lens-derived fields
3. **Merging** both outputs before returning

**Example extractor implementation:**
```python
def extract(self, raw_data: Dict, *, ctx: ExecutionContext) -> Dict:
    # Step 1: Extract basic fields (source-specific logic)
    basic_fields = {
        "entity_name": raw_data.get("name"),
        "latitude": raw_data.get("lat"),
        "longitude": raw_data.get("lng"),
        # ... other basic fields
    }

    # Step 2: Get lens-derived fields (canonical dimensions + modules)
    lens_fields = self.apply_lens_contract(
        raw_data,
        ctx=ctx,
        source_name=self.source_name  # Required for applicability filtering
    )

    # Step 3: Merge and return
    return {**basic_fields, **lens_fields}
```

**Migration:** All 6 extractors (GooglePlacesExtractor, SportScotlandExtractor, EdinburghCouncilExtractor, OSMExtractor, SerperExtractor, OpenChargeMapExtractor) updated in single pass to accept `ctx` parameter.

#### Enforcement and Validation

**Design Guarantees:**

1. **Single Load:** lens.yaml loaded exactly once at bootstrap (CLI validates and caches)
2. **No Global State:** Context passed explicitly, no singletons or module-level variables
3. **Fail Fast:** Lens validation happens at startup (malformed lens crashes before any extraction)
4. **Testable:** Tests create ExecutionContext with mock lens_contract dict
5. **Multi-Lens Ready:** Different contexts can be created for different lenses (future: parallel processing)
6. **Engine Purity:** Engine only consumes plain dict, never imports lens loader

**Purity Test Update:**
```python
# tests/engine/test_purity.py
def test_extractors_never_load_lenses():
    """Extractors must not import or use LensRegistry"""
    for extractor_module in get_all_extractor_modules():
        source = inspect.getsource(extractor_module)
        assert "LensRegistry" not in source
        assert "load_lens" not in source
        assert "lens.yaml" not in source
```

#### Implementation Notes

**Lens Contract Normalization:**
- Lens loaded as YAML, validated against schema
- Converted to plain dict before storing in ExecutionContext
- `raw_categories` normalized to strings before regex matching
- Empty module definitions (`{}`) allowed if module not in lens_contract["modules"]

**Context Lifecycle:**
- Created: Once at CLI bootstrap
- Validated: Immediately after creation (fail-fast)
- Immutable: Never modified after creation
- Scope: Entire query execution (bootstrap → ingestion → extraction → finalization)

**Error Handling:**
- Missing lens file: Crash at startup with clear error
- Malformed lens.yaml: Crash at validation with schema errors
- Missing ctx in extractor: Raise ValueError immediately
- Missing lens_contract in ctx: Raise ValueError immediately

**Future Extensions:**
- Multi-lens queries: Create separate ExecutionContext per lens
- Lens versioning: Add lens_version to ExecutionContext
- Lens hot-reload: Create new ExecutionContext with reloaded lens.yaml (ctx remains immutable)

---

### 4. The Four Dimensions (Universal Structure, Vertical Values)

Entities are classified along four multi-valued dimensions. The **structure** is universal (same four dimensions for all verticals), but the **values** are vertical-specific (defined by Lenses).

```sql
-- Postgres schema (universal structure)
CREATE TABLE entities (
  canonical_activities TEXT[] DEFAULT '{}',    -- GIN indexed
  canonical_roles TEXT[] DEFAULT '{}',         -- GIN indexed
  canonical_place_types TEXT[] DEFAULT '{}',   -- GIN indexed
  canonical_access TEXT[] DEFAULT '{}',        -- GIN indexed
  ...
);

-- Lens provides the values
-- Edinburgh Finds lens: ["tennis", "padel", "swimming"]
-- Wine Discovery lens: ["wine_tasting", "vineyard_tour", "wine_pairing"]
-- Engine just stores and indexes - never interprets
```

#### Dimension 1: `canonical_activities` - What Happens Here

**Semantic meaning:** Activities provided, supported, or facilitated by this entity.

**Edinburgh Finds values:** `tennis`, `padel`, `squash`, `badminton`, `swimming`, `gym`, `yoga`, `pilates`, `football`, `rugby`

**Wine Discovery values:** `wine_tasting`, `vineyard_tour`, `wine_pairing`, `wine_education`, `vertical_tasting`

**Restaurant Finder values:** `fine_dining`, `casual_dining`, `takeaway`, `brunch`, `afternoon_tea`

**Engine behavior:** Stores as opaque strings, provides GIN index for fast `WHERE 'tennis' = ANY(canonical_activities)` queries. Never interprets meaning.

#### Dimension 2: `canonical_roles` - What Function This Entity Serves

**Semantic meaning:** The roles or functions this entity plays in the ecosystem. Uses universal function-style keys.

**Universal values (cross-vertical):**
- `provides_facility`: Operates a physical facility (sports centre, vineyard, restaurant)
- `provides_instruction`: Teaches or coaches (tennis coach, sommelier, chef instructor)
- `sells_goods`: Retail operation (sports shop, wine merchant, kitchenware store)
- `membership_org`: Membership-based organization (tennis club, wine society, dining club)
- `produces_goods`: Manufactures or produces (N/A for sports, winery, brewery)

**Engine behavior:** Stores as opaque strings. Lens interprets for display (e.g., `provides_instruction` → "Coach" in Edinburgh Finds, "Sommelier" in Wine Discovery).

**Design note:** Roles use universal function keys to enable cross-lens queries and prevent explosion of vertical-specific role types.

#### Dimension 3: `canonical_place_types` - Physical Place Classification

**Semantic meaning:** What kind of physical place this is (applies only to `entity_class: place`).

**Edinburgh Finds values:** `sports_centre`, `tennis_club`, `swimming_pool`, `gym`, `outdoor_facility`, `multi_sport_complex`

**Wine Discovery values:** `winery`, `vineyard`, `wine_bar`, `wine_shop`, `tasting_room`, `wine_cellar`

**Restaurant Finder values:** `restaurant`, `cafe`, `pub`, `bistro`, `food_truck`, `catering_kitchen`

**Engine behavior:** Only populated for `entity_class: place`. Stores as opaque strings, GIN indexed for fast filtering.

#### Dimension 4: `canonical_access` - How You Engage

**Semantic meaning:** Access model or engagement requirements.

**Universal values (cross-vertical):**
- `membership`: Members-only access
- `pay_and_play`: Pay per use, no membership required
- `free`: Free public access
- `booking_required`: Reservation or booking mandatory
- `drop_in`: Walk-in accepted
- `private`: Private/invitation only

**Engine behavior:** Stores as opaque strings. Lens provides display interpretation.

**Design note:** Access models are largely universal across verticals - a tennis club and a wine society both use "membership", a public park and a free wine tasting both use "free".

### 5. Module Architecture (Namespaced JSONB)

Entity data is organized into **modules** - namespaced JSONB structures that separate universal fields from domain-specific fields.

#### Module Field Extraction (Decision 3)

**Core Principle:** Module field extraction is **declarative, lens-owned, schema-driven, and executed by a generic engine interpreter**. The Lens defines extraction rules, the engine executes them generically, and no module-specific or domain-specific logic exists in engine code.

**Architectural Requirements:**
- Module field extraction rules live in the Lens contract (not Python code)
- Engine executes rules generically using a small, stable extractor vocabulary
- No module-specific branching or domain semantics in engine code
- Each module declares structured field rules with full metadata
- Engine remains domain-blind and only executes extractor types

**Module Field Rule Structure:**

Each module in the Lens contract declares extraction rules with the following components:

```yaml
modules:
  sports_facility:
    field_rules:
      - rule_id: extract_football_pitch_count
        target_path: football_pitches.five_a_side.total
        source_fields: [NumPitches, pitches_total, facility_count]
        extractor: numeric_parser
        confidence: 0.90
        applicability:
          source: [sport_scotland, edinburgh_council]
          entity_class: [place]
        normalizers: [round_integer]

      - rule_id: extract_surface_type
        target_path: football_pitches.five_a_side.surface
        source_fields: [Surface, surface_type, pitch_surface]
        extractor: regex_capture
        pattern: "(?i)(3G|4G|grass|artificial|astro)"
        confidence: 0.85
        normalizers: [lowercase, list_wrap]
```

**Extractor Vocabulary (Generic, Engine-Owned):**

The engine maintains a small, stable vocabulary of generic extractors:

**Deterministic Extractors:**
- `numeric_parser`: Extract numbers from strings or numeric fields
- `regex_capture`: Extract values matching regex pattern
- `json_path`: Extract value at JSON path
- `boolean_coercion`: Convert values to boolean
- `coalesce`: Try multiple source fields, use first non-null
- `normalize`: Apply normalization functions (lowercase, trim, etc.)
- `array_builder`: Construct array from multiple fields or split strings

**LLM Extractors:**
- `llm_structured`: Schema-bound structured extraction via Instructor
- Only used when deterministic extraction insufficient
- Must include Pydantic schema for validation
- Evidence-anchored where possible

**No extractor may encode domain semantics.** Adding new extractor types should be rare and justified.

**LLM/Instructor Constraints (Mandatory):**

LLM-assisted extraction is allowed only under strict guardrails:

1. **Schema-bound only:** Instructor or equivalent validation; no free-form JSON
2. **Evidence anchored:** Values without evidence may be rejected or confidence-capped
3. **Deterministic-first:** Deterministic rules run first; LLM fills only missing or explicitly LLM-only fields
4. **Batch per module:** At most one LLM call per module per source payload (not per field)
5. **Confidence caps:** LLM-derived values treated as weaker than official structured sources during merge
6. **Full provenance:** rule_id, source, confidence, and method retained

**Execution Semantics:**

For each entity and each required module:

1. **Select applicable rules** based on source and entity_class
2. **Run deterministic rules first** and populate fields
3. **Identify remaining fields** needing LLM extraction
4. **Build schema** for only those fields if needed
5. **Execute single Instructor call** per module if needed
6. **Validate, normalize, enforce** evidence and confidence constraints
7. **Write results** into module using target_path
8. **Do not resolve cross-source conflicts** here (merge remains separate)

**Source Awareness (Mandatory):**

Module field rules require source awareness for applicability and LLM behavior. The module extraction path (`extract_with_lens_contract` or equivalent) must receive either:
- `source_name` explicitly, OR
- Full `ExecutionContext` that includes source

This is the only required touch to that function for Decision 3.

**Purity Rules (Non-Negotiable):**

- Engine code must NOT contain domain concepts, module-specific branching, or hardcoded field semantics
- All semantics live in the Lens contract
- The Lens is treated as opaque configuration by the engine
- Engine only consumes and executes generic extractor types

**Example: Football Pitch Extraction**

```yaml
# Lens contract (lenses/edinburgh_finds/lens.yaml)
modules:
  sports_facility:
    field_rules:
      # Deterministic extraction from structured source
      - rule_id: football_pitch_total_sport_scotland
        target_path: football_pitches.five_a_side.total
        source_fields: [NumPitches]
        extractor: numeric_parser
        confidence: 0.95
        applicability:
          source: [sport_scotland]
          entity_class: [place]

      # LLM extraction from unstructured description
      - rule_id: football_pitch_llm_google
        target_path: football_pitches.five_a_side
        source_fields: [description, editorial_summary]
        extractor: llm_structured
        schema:
          total: integer
          indoor: integer
          outdoor: integer
          surface: array[string]
        confidence: 0.70  # LLM confidence capped
        applicability:
          source: [google_places, serper]
          entity_class: [place]
        conditions:
          - field_not_populated: football_pitches.five_a_side.total
```

**Engine Implementation (Generic):**

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
    Generic module field extractor - domain-agnostic.

    Executes field rules from lens contract without knowing
    what "football" or "sports_facility" means.

    Args:
        raw_data: Raw payload from connector (complete dict)
        module_def: Module definition from lens (includes field_rules)
        source_name: Connector name (e.g., "sport_scotland")
        entity_class: Entity class (e.g., "place")

    Returns:
        dict: Extracted module fields (may be incomplete if rules fail)

    Note: This is the ONLY place llm_structured extractor runs.
          Batch ≤ 1 LLM call per module per payload.
    """
    module_data = {}
    field_rules = module_def.get("field_rules", [])

    # Phase 1: Deterministic extraction
    for rule in field_rules:
        if not is_applicable(rule, source_name, entity_class):
            continue

        if rule["extractor"] in DETERMINISTIC_EXTRACTORS:
            try:
                value = execute_deterministic(rule, raw_data)
                if value is not None:
                    set_at_path(module_data, rule["target_path"], value)
            except Exception as e:
                # Graceful degradation: log failure, continue
                log_rule_failure(rule["rule_id"], source_name, e)

    # Phase 2: LLM extraction (batch per module, ≤ 1 call)
    llm_rules = [r for r in field_rules
                 if r["extractor"] == "llm_structured"
                 and is_applicable(r, source_name, entity_class)
                 and evaluate_conditions(r, module_data)]

    if llm_rules:
        try:
            # Single Instructor call for all LLM fields
            llm_values = execute_llm_batch(llm_rules, raw_data)
            for rule, value in zip(llm_rules, llm_values):
                set_at_path(module_data, rule["target_path"], value)
        except Exception as e:
            # Graceful degradation: log failure, continue with partial data
            log_llm_failure(source_name, module_def["name"], e)

    return module_data
```

**Implementation Specifications:**

**Canonical Function Signature:**
```python
# engine/extraction/base.py
def extract_with_lens_contract(
    raw_data: dict,
    lens_contract: dict,
    *,
    source_name: str  # Required for field_rules applicability
) -> dict:
    """
    Apply lens mapping rules and module field extraction.

    Args:
        raw_data: Raw payload (complete dict, not subset)
        lens_contract: Full lens.yaml as dict
        source_name: Connector name (e.g., "sport_scotland")

    Returns:
        dict: canonical dimensions + modules populated per lens rules
    """
```

This signature is REQUIRED everywhere `extract_with_lens_contract` is called.

**Mapping Rules Execution:**
- Mapping runs over **union of declared source_fields** per rule
- NOT hardcoded to `raw_data["raw_categories"]`
- Engine iterates: `for field in rule["source_fields"]: check raw_data.get(field)`
- First match wins per rule, all rules may contribute to dimensions

**LLM Integration Point:**
- `llm_structured` extractor runs ONLY inside `extract_module_fields()` (module_extractor.py)
- NOT inside per-source extractors, NOT per-field
- Batch ≤ 1 Instructor call per module per payload
- Single schema for all LLM fields in that module

**Error Handling Policy:**
- Deterministic rule failures: log with rule_id/source, skip field, continue
- LLM extraction failures: log with module name/source, continue with partial data
- Never crash entire entity extraction on rule failure
- Partial module population succeeds (some fields may remain null)
- Lens validation failures (schema/reference errors) fail-fast at bootstrap

**Rule Conflict Resolution:**
- Multiple rules targeting same `target_path`: first-match wins
- Conditions (`field_not_populated`) prevent re-extraction
- LLM rules should check conditions to avoid overwriting deterministic values

**Normalizer Pipeline:**
- Execute as ordered pipeline: `[trim, lowercase, list_wrap]` runs left-to-right
- Each normalizer is pure function (string → string or string → list)
- Common normalizers: `trim`, `lowercase`, `uppercase`, `list_wrap`, `comma_split`, `round_integer`
- Normalizers run per-rule after extraction, before writing to target_path

**Condition Vocabulary:**
- `field_not_populated`: Skip if target_path already has value
- `any_field_missing`: Run only if any listed field is null
- `source_has_field`: Skip if raw_data missing required field
- `value_present`: Run only if specific field has specific value
- Conditions evaluated before rule execution

**Extractor Vocabulary (Exhaustive List):**

Deterministic extractors (8 core):
- `numeric_parser`: Extract number from string or numeric field
- `regex_capture`: Extract value matching regex pattern
- `json_path`: Extract value at JSON path (e.g., `data.items[0].count`)
- `boolean_coercion`: Convert truthy/falsy to boolean
- `coalesce`: Try multiple source_fields, use first non-null
- `normalize`: Apply normalization function
- `array_builder`: Construct array from multiple fields or split string
- `string_template`: Build string from template (e.g., `"{city}, {country}"`)

LLM extractors (1):
- `llm_structured`: Instructor-based schema extraction (batch per module)

**Adding new extractors requires:**
- Architecture review (justify why existing extractors insufficient)
- Purity validation (no domain semantics)
- Documentation with examples
- Test coverage

**Implementation Sequencing:**
1. **MVP: Deterministic-only** (5–10 rules for Powerleague)
2. Prove end-to-end deterministic extraction from Sport Scotland
3. Add LLM extraction after deterministic path proven
4. Validate ≤ 1 LLM call per module per payload

**Validation & Acceptance:**

Decision 3 is complete when:

- ✅ Modules are no longer empty placeholders
- ✅ **At least one field_rules rule produces a non-null value persisted under target_path in modules JSONB for a real fixture/entity** (explicit non-empty requirement)
- ✅ Deterministic extraction works for structured sources (test with Sport Scotland fixture)
- ✅ LLM-assisted extraction works under constraints above (test with Google Places fixture)
- ✅ No engine purity violations exist (no domain logic in module_extractor.py)
- ✅ Tests exist using real payload fixtures (not mocks)
- ✅ Source awareness properly implemented (applicability filtering works)
- ✅ Error handling gracefully degrades (partial data succeeds)
- ✅ ≤ 1 LLM call per module per payload (batch efficiency verified)

**Storage format:**
```json
{
  "modules": {
    "core": {
      "entity_id": "ent_abc123",
      "entity_name": "Craiglockhart Sports Centre",
      "slug": "craiglockhart-sports-centre",
      "summary": "Multi-sport facility..."
    },
    "location": {
      "street_address": "177 Colinton Road",
      "city": "Edinburgh",
      "postcode": "EH14 1BZ",
      "latitude": 55.920654,
      "longitude": -3.237891
    },
    "contact": {
      "phone": "+441314447100",
      "email": "info@craiglockhart.com",
      "website_url": "https://...",
      "instagram_url": "https://..."
    },
    "hours": {
      "opening_hours": {
        "monday": {"open": "06:00", "close": "22:00"}
      }
    },
    "sports_facility": {
      "tennis_courts": {
        "total": 12,
        "indoor": 8,
        "outdoor": 4,
        "surfaces": ["hard", "clay"],
        "booking_url": "https://..."
      },
      "padel_courts": {
        "total": 4,
        "indoor": 4
      },
      "swimming_pool": {
        "indoor": true,
        "length_m": 25,
        "lanes": 6
      }
    }
  }
}
```

**Universal Modules** (engine-defined, always available):
- `core`: entity_id, entity_name, slug, summary
- `location`: street_address, city, postcode, country, latitude, longitude, locality
- `contact`: phone, email, website_url, social media URLs
- `hours`: opening_hours, special_hours
- `amenities`: wifi, parking_available, disabled_access (ONLY universal amenities)
- `time_range`: start_datetime, end_datetime, timezone, recurrence (for events)

**Domain Modules** (lens-defined, conditionally attached):
- `sports_facility`: Sports-specific inventory (courts, pitches, pools, equipment)
  - *Migration note:* Field schema should reference `engine/old_db_models.py` Venue table for existing field names (tennis_total_courts, padel_indoor_courts, etc.)
- `wine_production`: Vineyard acreage, production volume, grape varieties
- `fitness_facility`: Gym equipment, class schedules, trainer availability
- `food_service`: Cuisine types, dietary options, seating capacity, menu pricing

**Module Triggers** (Lens-defined rules):
```yaml
# When to attach domain modules
module_triggers:
  - when:
      dimension: canonical_activities
      values: [tennis]
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

  - when:
      dimension: canonical_activities
      values: [wine_tasting]
    add_modules: [wine_production, food_service]
    conditions:
      - entity_class: place
```

**Validation:** Module validator (`engine/modules/validator.py`) enforces namespaced structure and rejects flattened data to prevent field collisions.

#### Domain Module Field Examples

To illustrate the **depth and granularity** of data Edinburgh Finds captures, here are specific field examples for the `sports_facility` module. This level of detail is what makes Edinburgh Finds valuable - complete facility inventories, not just name and address.

**Racquet Sports:**
```yaml
tennis_courts:
  total: 12
  indoor: 8
  outdoor: 4
  covered: 8
  floodlit: 4
  surfaces: [hard, clay]
  coaching_available: true

padel_courts:
  total: 4
  indoor: 4

squash_courts:
  total: 3
  glass_back_courts: 1

badminton_courts:
  total: 6

table_tennis:
  tables: 2
```

**Football Pitches:**
```yaml
football_5_a_side:
  pitches: 4
  indoor: 2
  outdoor: 2

football_7_a_side:
  pitches: 2

football_11_a_side:
  pitches: 1
  surface: grass
```

**Swimming:**
```yaml
swimming_pool:
  indoor: true
  length_m: 25
  lanes: 6
  outdoor: false
  family_swim: true
  adult_only_swim: true
  lessons_available: true
  learner_pool: true
  learner_pool_depth_m: 0.8
```

**Gym & Classes:**
```yaml
gym:
  available: true
  size_stations: 120
  free_weights: true
  cardio_equipment: true
  functional_training_zone: true

classes:
  per_week: 60
  types: [yoga, hiit, pilates, spin, strength, zumba]
  cycling_studio: true
```

**Spa & Wellness:**
```yaml
spa:
  available: true
  sauna: true
  steam_room: true
  hydro_pool: true
  ice_cold_plunge: true
  relaxation_area: true
  hot_tub: false
  outdoor_spa: false
```

**Family & Kids:**
```yaml
family:
  creche_available: true
  creche_age_min: 6
  creche_age_max: 12
  kids_swimming_lessons: true
  kids_tennis_lessons: true
  holiday_club: true
  play_area: false
```

**Parking & Transport:**
```yaml
parking:
  spaces: 80
  disabled_parking: true
  parent_child_parking: true
  ev_charging: true
  ev_connectors: 4

transport:
  public_transport_nearby: true
  nearest_railway_station: "Slateford"
  bus_routes: ["10", "27", "45"]
```

**Reviews & Social Proof:**
```yaml
reviews:
  average_rating: 4.2
  total_count: 340
  google_count: 340
  tripadvisor_count: 0

social:
  facebook_likes: 1250
  instagram_followers: 850
```

This is what makes Edinburgh Finds valuable: **complete facility data with quantitative details**, not just contact information. Every court, every pool dimension, every amenity - captured and structured.

#### Field Name Reconciliation (Decision 4)

**Core Principle:** Entity schema field names are the **single canonical universal keys** across the entire pipeline. No translation layers, no legacy naming, no connector-specific field names survive past extraction.

**Architectural Requirements:**
- Schema (`engine/config/schemas/entity.yaml`) is the sole authority for universal field names
- All extractors emit schema-aligned field names directly
- EntityFinalizer consumes schema-aligned field names directly
- No permanent mapping or translation layer between extraction and finalization
- Validation fails loudly on non-canonical field names to prevent silent data loss

**The Problem:**

Historical drift caused a field name mismatch between extractor output and EntityFinalizer expectations:

| Schema Field (Canonical) | Extractor Outputs | EntityFinalizer Expected (Wrong) |
|--------------------------|-------------------|----------------------------------|
| `entity_name` | `entity_name` ✅ | `name` ❌ |
| `latitude` | `latitude` ✅ | `location_lat` ❌ |
| `longitude` | `longitude` ✅ | `location_lng` ❌ |
| `street_address` | `street_address` ✅ | `address_full` ❌ |
| `phone` | `phone` ✅ | `contact_phone` ❌ |
| `email` | `email` ✅ | `contact_email` ❌ |
| `website_url` | `website` ⚠️ | `contact_website` ❌ |

**Observation:** Most extractors already emit schema-aligned names. The primary fix is updating EntityFinalizer to consume canonical names, plus standardizing `website` → `website_url` globally.

**What Extractors Emit:**

Extractors emit **schema-defined universal fields** as observed from sources, plus any **raw source-specific observations** for downstream use.

**Universal Fields (Schema Authority):**
- Refer to `engine/config/schemas/entity.yaml` for the complete, authoritative list
- Schema is the sole canonical contract - do not maintain duplicate field lists in code or docs
- Common examples: `entity_name`, `latitude`, `longitude`, `street_address`, `city`, `postcode`, `phone`, `email`, `website_url`

**Raw Source Observations (Permitted):**
- Source-specific fields not in schema (e.g., `facility_type`, `NumPitches` from Sport Scotland WFS)
- Passed through for use by lens mapping rules and module field extraction
- Not part of universal contract but necessary for extraction pipeline

**Extractors DO NOT Emit (Boundary Enforcement):**
- `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access` → Lens mapping rules populate these
- `modules` → Module field extraction populates these (Decision 3)
- Any lens-derived or module-derived semantics → Keep extraction focused on schema primitives

**Boundary Clarity:**
- **Schema primitives** (extractors produce: entity_name, lat/lng, address, contact from entity.yaml)
- **Lens-interpreted dimensions** (mapping rules produce: canonical_activities, canonical_roles)
- **Structured module data** (field rules produce: sports_facility.tennis_courts.total)

**Implementation:**

**Primary Fix: EntityFinalizer**
```python
# engine/orchestration/entity_finalizer.py - _finalize_single()

# BEFORE (wrong - legacy field names):
"latitude": attributes.get("location_lat"),
"longitude": attributes.get("location_lng"),
"street_address": attributes.get("address_full"),
"phone": attributes.get("contact_phone"),
"email": attributes.get("contact_email"),
"website_url": attributes.get("contact_website"),

# AFTER (correct - schema canonical names):
"latitude": attributes.get("latitude"),
"longitude": attributes.get("longitude"),
"street_address": attributes.get("street_address"),
"phone": attributes.get("phone"),
"email": attributes.get("email"),
"website_url": attributes.get("website_url"),
```

**Global Standardization: website → website_url**

Search entire codebase for `website` field usage and standardize to `website_url`. This applies to:
- All 6 extractors (google_places, sport_scotland, serper, osm, edinburgh_council, open_charge_map)
- Any utility functions or validation logic
- Test fixtures and assertions

**Validation Strategy (Permissive of Raw Observations):**

```python
# engine/extraction/validation.py
def validate_extractor_fields(extracted: Dict, source: str) -> None:
    """
    Validate canonical field names without blocking raw observations.

    Strategy: Only validate fields that CLAIM to be canonical.
    Do NOT reject unknown keys (they may be legitimate raw observations).
    """
    # Detect legacy naming patterns (location_*, contact_*, address_*)
    legacy_patterns = {k for k in extracted.keys()
                       if k.startswith(("location_", "contact_", "address_"))}

    if legacy_patterns:
        msg = f"{source}: Legacy field names detected: {legacy_patterns}"
        if os.getenv("STRICT_FIELD_VALIDATION") == "true":
            raise ValueError(msg)  # Hard error in CI
        else:
            logger.warning(msg)  # Warn only during migration

    # Note: Unknown fields are NOT rejected - they may be raw observations
    # for mapping rules or module extraction (e.g., NumPitches, facility_type)
```

**Validation Scope:**
- **Validate:** Legacy naming patterns that conflict with schema (location_lat, contact_phone)
- **Allow:** Raw source-specific observations (NumPitches, facility_type, surface_type)
- **Do NOT:** Maintain hardcoded "allowed" field lists (schema is authority)

**Phase 1 (Migration):** Warn on legacy patterns, allow execution
**Phase 2 (Post-Migration):** Hard error on legacy patterns (via `STRICT_FIELD_VALIDATION=true` in CI)

**Regression Test:**

```python
# tests/engine/orchestration/test_field_name_alignment.py
def test_canonical_field_alignment():
    """Verify schema-defined universal fields survive extraction → finalization"""
    # Use real fixture
    fixture = load_fixture("google_places/powerleague.json")
    extracted = GooglePlacesExtractor().extract(fixture)
    finalized = EntityFinalizer(db)._finalize_single(extracted)

    # Assert sample schema fields preserved (examples - not exhaustive)
    # For complete list, refer to entity.yaml
    assert finalized["entity_name"] == extracted["entity_name"]
    assert finalized["latitude"] == extracted["latitude"]
    assert finalized["longitude"] == extracted["longitude"]
    assert finalized["street_address"] == extracted["street_address"]
    assert finalized["phone"] == extracted.get("phone")
    assert finalized["email"] == extracted.get("email")
    assert finalized["website_url"] == extracted.get("website_url")

    # Scope: Only test schema primitives (entity_name, lat/lng, address, contact)
    # Do NOT test canonical dimensions (lens mapping) or modules (field extraction)
```

**Validation & Acceptance:**

Decision 4 is complete when:

- ✅ EntityFinalizer reads schema-aligned field names (no `location_lat`, `contact_phone`, etc.)
- ✅ All extractors emit `website_url` consistently (no `website`)
- ✅ Validation warns on legacy field names (or errors in CI)
- ✅ Regression test passes with real fixtures
- ✅ No silent data loss occurs due to field name mismatches
- ✅ Future extractors cannot accidentally introduce legacy naming (validation catches)

**Non-Goals:**

- ❌ Do NOT introduce permanent mapping/translation layers
- ❌ Do NOT allow multiple competing naming conventions long-term
- ❌ Do NOT embed connector-specific naming logic in EntityFinalizer
- ❌ Do NOT blur boundaries between universal fields, canonical dimensions, and modules
- ❌ Do NOT maintain separate "canonical field lists" in code or constants (schema is sole authority)

**Impact:** Eliminates silent data loss, simplifies connector additions, establishes schema as unambiguous authority for universal field contracts.

#### Deterministic Multi-Source Entity Merge (Decision 5)

**Core Principle:** Multi-source entity merging is a **deterministic, field-aware, metadata-driven contract** that runs after deduplication grouping and before persistence. Merge logic is domain-blind, idempotent, and consumes connector trust/priority metadata without hardcoding connector names.

**Architectural Requirements:**
- Merge runs **only after deduplication grouping** (post-dedup, pre-persistence boundary)
- Trust model is **connector-metadata-driven** (uses `trust_tier` and `default_priority` from connector registry)
- Field-group strategy handles different data types appropriately
- All tie-breakers are deterministic (ensures idempotency across runs)
- Merge logic is **domain-blind** (no "if football then..." branching)
- No domain interpretation occurs during merge (lens semantics already applied during extraction)

**Trust Model (Metadata-Driven):**

Trust hierarchy comes from connector registry metadata, not hardcoded connector names:

```python
# engine/orchestration/registry.py - ConnectorSpec metadata
ConnectorSpec(
    name="sport_scotland",
    trust_tier="high",           # official/authoritative
    default_priority=1,          # Lower number = higher priority
    ...
)

ConnectorSpec(
    name="google_places",
    trust_tier="medium",         # verified crowdsourced
    default_priority=2,
    ...
)
```

**Merge operates on metadata values, never connector names in merge logic.**

**Field-Group Merge Strategy:**

Different field types require different merge strategies:

**1. Identity/Core Display Fields** (entity_name, summary, address):
- Prefer higher `trust_tier` unless empty or less usable
- Deterministic quality: prefer non-null, then longer/more complete values
- Tie-break: `default_priority` → lexicographic `source_name`

**2. Geo Primitives** (latitude, longitude):
- Prefer explicit precision metadata if provided by connector
- Else prefer higher `trust_tier`
- Else prefer coordinates with more decimal precision
- Tie-break: `default_priority` → lexicographic `source_name`
- **Do NOT compute centroids** (avoid invalid midpoints)

**3. Contact & Presence Fields** (phone, email, website_url, social URLs):
- **Quality scoring** (deterministic, structure-based only):
  - **Phone**: parseable international format > contains country code > greater digit count > non-empty
  - **Email**: valid RFC format > non-free-provider domain > longer normalized length > non-empty
  - **Website/URL**: HTTPS preferred > path depth preferred > absence of tracking params > longer URL > non-empty
- Allow higher-quality crowdsourced to win if official source is null/sparse
- Tie-break: quality score → `trust_tier` → `default_priority` → lexicographic `source_name`

**4. Canonical Dimension Arrays** (canonical_activities, canonical_roles, canonical_place_types, canonical_access):
- **Union** all sources (no overwriting)
- **Deduplicate** (remove exact duplicates)
- **Lexicographic sort** (stable ordering for idempotency)
- No weighting or ranking logic in storage

**5. Modules JSONB** (core, location, contact, hours, sports_facility, etc.):
- **Deep merge recursively**:
  - `object` vs `object` → deep merge recursively
  - `array` vs `array`:
    - **Arrays of scalars** (strings, numbers, booleans) → concatenate + deduplicate + lexicographic sort
    - **Arrays of objects** → selected wholesale from winner using deterministic cascade (trust → confidence → completeness → priority → lex source)
    - No partial deep merge of object arrays without explicit stable IDs
  - Type mismatch (object vs array vs scalar) → higher `trust_tier` wins wholesale
- **Per-leaf selection** (object fields, scalar values): trust → confidence (if present) → completeness
- **Confidence usage**: Confidence is used only when present in extraction metadata; otherwise merger ignores confidence and proceeds to next tie-breaker (completeness)
- Normalize confidence scores internally to 0.0–1.0 before comparison
- Record provenance if structural conflict occurs (optional but encouraged)

**6. Provenance/External IDs** (source_info, external_ids, discovered_by):
- **Always union** (never overwrite)
- Track all contributors
- `primary_source`: highest `trust_tier` contributor
- `discovered_by`: union of all source names

**Deterministic Tie-Breakers (Cascade):**

When multiple sources have identical trust/quality/completeness:

1. **Trust tier** (high > medium > low)
2. **Quality score** (for contact fields: structure-based metrics)
3. **Completeness** (non-null > longer string > more array elements)
4. **Connector default_priority** (from registry metadata)
5. **Lexicographic source_name** (alphabetical, ensures stable output)

**Merge Execution Semantics:**

```python
def merge_entities(entity_group: List[ExtractedEntity]) -> Entity:
    """
    Deterministic multi-source merge with field-aware strategies.

    Input: Grouped entities from deduplication (same real-world entity)
    Output: Single merged entity with best data from all sources

    Guarantees:
    - Idempotent: Same inputs always produce identical output
    - Domain-blind: No vertical-specific branching
    - Metadata-driven: Uses connector registry trust/priority
    - Deterministic: All tie-breakers cascade to lexicographic
    """
    # Sort by trust_tier, then default_priority
    sorted_entities = sort_by_trust_metadata(entity_group)

    # Merge field groups using appropriate strategies
    merged = {}
    merged.update(merge_identity_fields(sorted_entities))
    merged.update(merge_geo_fields(sorted_entities))
    merged.update(merge_contact_fields(sorted_entities))
    merged["canonical_activities"] = union_and_sort(
        [e.canonical_activities for e in sorted_entities]
    )
    merged["modules"] = deep_merge_modules(sorted_entities)
    merged["source_info"] = union_provenance(sorted_entities)

    return merged
```

**Validation & Acceptance:**

Decision 5 is complete when:

- ✅ Merge runs **after deduplication grouping** and **before persistence**
- ✅ Trust model uses connector registry metadata (no hardcoded connector names in merge logic)
- ✅ All field-group strategies implemented (identity, geo, contact, canonical arrays, modules, provenance)
- ✅ Contact field quality scoring is deterministic and structure-based only
- ✅ Geo precision uses decimal precision (no centroid calculation)
- ✅ Modules deep merge handles object/array/type mismatches gracefully
- ✅ Canonical arrays are unioned, deduped, and lexicographically sorted
- ✅ All tie-breakers are deterministic (cascading to lexicographic source_name)
- ✅ Repeated runs produce identical output (idempotency verified)
- ✅ Tests use real fixtures (e.g., Powerleague Portobello from multiple sources)
- ✅ No domain-specific logic in merge code (engine purity maintained)

**Test Scenarios (Acceptance Criteria):**

Using real Powerleague Portobello group from Google Places + Sport Scotland:

1. **Contact override**: Crowdsourced phone/website fills official nulls → Verify contact fields populated
2. **Inventory conflict**: Official facility count beats crowdsourced conflicting count → Verify trust hierarchy
3. **Canonical union**: Activities from both sources unioned and stable → Verify lexicographic ordering
4. **Tie-break determinism**: Repeated runs produce identical output → Verify idempotency
5. **Same-trust conflict**: Multiple sources with `trust_tier=high` → Verify priority cascade works
6. **All-null inputs**: All sources have null for a field → Verify graceful handling
7. **Module structural mismatch**: Object vs array conflict → Verify higher trust wins wholesale

**Non-Goals:**

- ❌ Do NOT introduce domain-specific branching ("if padel then...")
- ❌ Do NOT hardcode connector names in merge logic (use metadata only)
- ❌ Do NOT compute geographic centroids (prefer deterministic selection)
- ❌ Do NOT introduce permanent naming translation layer (Decision 4 stands)
- ❌ Do NOT make network calls for quality validation (structure-based only)

**Impact:** Enables accurate, complete entity records from multiple imperfect sources while maintaining engine purity, idempotency, and architectural scalability.

### 6. Infinite Connector Extensibility

The system is designed for **unlimited growth** in data sources. Connectors are pluggable, self-describing components that integrate through a standardized interface.

**Current Prototype:** 6 connectors operational
- **General Search:** Serper (Google Search API), Google Places API
- **Geographic Data:** OpenStreetMap (Overpass QL)
- **Domain-Specific:** Sport Scotland (WFS), Edinburgh Council (ArcGIS), Open Charge Map (EV charging)

**Connector Growth Strategies:**

**1. New Verticals Bring New Connectors**

When adding a new vertical, bring specialized data sources:

```yaml
# Wine Discovery vertical adds wine-specific connectors
wine_discovery:
  connectors:
    - vivino_api          # Wine ratings and reviews
    - wine_searcher       # Wine retail and pricing
    - decanter_magazine   # Editorial content and awards
    - vinous_reviews      # Professional tasting notes
    - local_wine_board    # Regional wine authority data
```

**2. Existing Verticals Get Enriched**

Verticals continuously improve by adding more data sources:

```yaml
# Edinburgh Finds enrichment roadmap
edinburgh_finds:
  phase_1_connectors:  # Current (6 connectors)
    - serper
    - google_places
    - openstreetmap
    - sport_scotland
    - edinburgh_council
    - open_charge_map

  phase_2_enrichment:  # Next wave
    - tripadvisor_api     # Reviews and ratings
    - yelp_api            # User reviews and photos
    - visit_scotland      # Official tourism data
    - edinburgh_leisure   # Municipal facility data
    - active_places       # UK sports facility database

  phase_3_enrichment:  # Future
    - strava_heatmaps     # Activity popularity data
    - instagram_places    # Social media presence
    - local_news_apis     # Venue news and updates
```

**Connector Architecture:**

**Standardized Interface** (`engine/ingestion/base.py`):
```python
class BaseConnector(ABC):
    @abstractmethod
    async def fetch(self, query: str) -> RawData:
        """Fetch raw data from source"""

    @abstractmethod
    async def is_duplicate(self, data: RawData) -> bool:
        """Check if data already ingested"""

    @abstractmethod
    async def save(self, data: RawData) -> str:
        """Save to storage and database"""
```

**Self-Describing Metadata** (`engine/orchestration/registry.py`):
```python
ConnectorSpec(
    name="tripadvisor_api",
    cost_tier="paid",           # free | paid | premium
    trust_tier="medium",        # high | medium | low (merge contract)
    default_priority=3,         # Lower wins (merge tie-breaker)
    phase=ExecutionPhase.ENRICHMENT,
    timeout_seconds=10,
    rate_limit=RateLimit(per_minute=60, per_hour=1000),
    capabilities=["reviews", "ratings", "photos", "hours"]
)
```

**Pluggable Integration:**
- New connector = New Python class + Registry entry
- Zero changes to orchestration logic
- Automatic phase ordering and rate limiting
- Trust-based conflict resolution built-in

**Scaling Properties:**

**Horizontal Scaling (More Verticals):**
- Wine Discovery vertical → Add wine-specific connectors
- Restaurant Finder vertical → Add food/dining connectors
- Event Calendar vertical → Add ticketing/venue connectors
- Each vertical brings 5-15 specialized connectors

**Vertical Scaling (Enrich Existing):**
- Edinburgh Finds starts with 6 connectors
- Add TripAdvisor → Richer reviews and ratings
- Add Yelp → More user photos and check-ins
- Add VisitScotland → Official tourism data
- No limit to connector count per vertical

**Cross-Vertical Connectors:**

Some connectors serve multiple verticals:

```yaml
# Google Places used by all verticals
google_places:
  used_by:
    - edinburgh_finds    # Sports venues, gyms
    - wine_discovery     # Wineries, wine bars
    - restaurant_finder  # Restaurants, cafes
    - event_calendar     # Venue locations

# Each vertical configures routing rules differently
# Same connector, different lens interpretation
```

**Connector Lifecycle:**
1. **Development:** Implement BaseConnector interface
2. **Registration:** Add to connector registry with metadata
3. **Lens Routing:** Configure which lenses use this connector
4. **Testing:** Validate data quality and deduplication
5. **Production:** Orchestrator auto-includes based on lens rules
6. **Monitoring:** Track cost, latency, failure rates, data quality

**Quality Control:**

Each connector self-reports quality metrics:
- **Coverage:** Percentage of queries returning results
- **Freshness:** Average age of data
- **Confidence:** Field-level confidence scores
- **Cost:** API cost per entity extracted
- **Latency:** Response time percentiles

**Example: Adding TripAdvisor Connector**

```python
# Step 1: Implement connector
class TripAdvisorConnector(BaseConnector):
    source_name = "tripadvisor_api"

    async def fetch(self, query: str) -> RawData:
        # API call to TripAdvisor
        return response

# Step 2: Register in engine/orchestration/registry.py
CONNECTOR_SPECS["tripadvisor_api"] = ConnectorSpec(
    name="tripadvisor_api",
    cost_tier="paid",
    trust_tier="medium",        # high | medium | low
    default_priority=3,         # Lower number wins
    phase=ExecutionPhase.ENRICHMENT,
    timeout_seconds=5
)

# Step 3: Add lens routing rule
# lenses/edinburgh_finds/lens.yaml
connector_rules:
  tripadvisor_api:
    priority: medium
    triggers:
      - type: entity_enrichment
        entity_types: [venue, restaurant]

# DONE - No orchestration code changes required
```

**Result:** System can grow from 6 connectors (current) to 100+ connectors across multiple verticals without architectural changes. Each vertical brings specialized data sources, and existing verticals continuously improve with enrichment connectors.

---

## Complete Data Flow

### End-to-End Pipeline

```
User Query: "padel courts in Edinburgh"
    ↓
┌─────────────────────────────────────────────────┐
│ 1. QUERY INTERPRETATION (Lens-Driven)          │
│    - Extract features using Lens vocabulary    │
│    - Detect: activity="padel", location="edinburgh" │
│    - Intent: category_search (not specific venue)  │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 2. CONNECTOR ORCHESTRATION (Lens-Driven)       │
│    - Apply Lens connector_rules                │
│    - Select sources: Serper, Google Places,     │
│      Sport Scotland, Edinburgh Council          │
│    - Phase 1: Discovery (free sources)         │
│    - Phase 2: Enrichment (paid/specialized)    │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 3. RAW INGESTION (Source-Specific)             │
│    - Each connector fetches raw data           │
│    - Deduplication (SHA-256 hash)              │
│    - Store: RawIngestion table + filesystem    │
│    - Metadata: source, timestamp, hash         │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 4. EXTRACTION (Hybrid Deterministic + LLM)     │
│    - Extractor reads raw data                  │
│    - Extract universal fields (name, address)  │
│    - Extract raw_categories (LLM observations) │
│    - Example: ["Sports Centre", "Racquet Club"]│
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 5. LENS MAPPING (Raw → Canonical)              │
│    - Apply Lens mapping_rules (regex patterns) │
│    - "Sports Centre" + "Racquet Club"          │
│      → canonical_place_types: ["sports_centre"]│
│      → canonical_activities: ["tennis", "padel"]│
│      → canonical_access: ["membership", "pay_and_play"] │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 6. CLASSIFICATION (Universal)                   │
│    - Resolve entity_class (deterministic rules)│
│    - Has coordinates? → "place"                │
│    - Has start_datetime? → "event"             │
│    - Has is_individual flag? → "person"        │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 7. MODULE ATTACHMENT (Lens-Driven)             │
│    - Check module_triggers                     │
│    - canonical_activities contains "padel"?    │
│    - entity_class is "place"?                  │
│    - → Attach sports_facility module           │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 8. MODULE POPULATION (Domain-Specific)         │
│    - Organize extracted data into modules      │
│    - Universal: core, location, contact, hours │
│    - Domain: sports_facility (court inventory) │
│    - Namespace: {"sports_facility": {...}}    │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 9. CROSS-SOURCE DEDUPLICATION                  │
│    - Tier 1: External ID matching              │
│      (e.g., "ChIJabc..." = "EH-PAD-001"?)     │
│    - Tier 2: Geo-based (name + lat/lng)       │
│      (e.g., name similarity + distance < 50m)  │
│    - Tier 3: SHA-1 fallback (content hash)    │
│    - Group duplicate ExtractedEntity records   │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 10. ENTITY MERGING (Per Dedup Group)          │
│     - EntityMerger: Merges each dedup group   │
│     - Trust hierarchy resolves conflicts       │
│     - Field-group strategies applied           │
│     - Deterministic tie-breakers cascade       │
│     - Output: Single merged entity per group   │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 11. ENTITY FINALIZATION                        │
│     - SlugGenerator: Creates URL-safe slugs    │
│       (e.g., "Powerleague Portobello" → "powerleague-portobello") │
│     - EntityFinalizer: Upserts merged entity   │
│     - Upsert to Entity table (idempotent)      │
│     - Store source_info (provenance tracking)  │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 12. FRONTEND DISPLAY (Lens Interpretation)     │
│     - Query Entity table with dimension filters│
│     - Lens provides display labels, icons      │
│     - canonical_activities: "padel" → "Padel"  │
│     - canonical_roles: "provides_facility" →   │
│       "Sports Facility"                        │
└─────────────────────────────────────────────────┘
    ↓
Result: Complete entity records with rich facility data
```

### Critical Flow Characteristics

**Idempotent:** Re-running the same query updates existing entities rather than creating duplicates.

**Lens-Driven:** Steps 1, 2, 5, 7 are driven by Lens configuration. Changing the Lens changes behavior without code changes.

**Hybrid Extraction:** Step 4 uses deterministic rules for structured data (addresses, coordinates) and LLM for unstructured data (descriptions, amenities).

**Trust-Based:** Step 10 uses connector trust levels to resolve conflicts. Example:
```
Field: tennis_total_courts
  - Google Places: null
  - Edinburgh Leisure API: 12 courts (trust: official)
  - Sport Scotland: 12 courts (trust: official)
  → Winner: 12 courts (official sources agree)

Field: website_url
  - Google Places: "https://edinburghleisure.co.uk" (trust: crowdsourced)
  - Edinburgh Leisure API: "https://www.edinburghleisure.co.uk/venues/craiglockhart" (trust: official)
  → Winner: Official source (more specific URL)
```

**Source Provenance:** Every entity tracks which sources contributed data and when it was verified.

---

## What Success Looks Like

### Completeness: All Available Data Populated

**Principle:** Empty fields should be exceptions (facility doesn't exist, data unavailable from all sources), not the norm.

**Example: Complete Entity**
```json
{
  "entity_name": "Craiglockhart Sports Centre",
  "entity_class": "place",
  "slug": "craiglockhart-sports-centre",

  "canonical_activities": ["tennis", "padel", "swimming", "gym", "squash"],
  "canonical_roles": ["provides_facility"],
  "canonical_place_types": ["sports_centre", "swimming_pool"],
  "canonical_access": ["membership", "pay_and_play"],

  "modules": {
    "core": {
      "summary": "Multi-sport facility in South Edinburgh offering tennis, swimming, gym, and spa facilities with extensive class programs"
    },
    "location": {
      "street_address": "177 Colinton Road",
      "city": "Edinburgh",
      "postcode": "EH14 1BZ",
      "latitude": 55.920654,
      "longitude": -3.237891
    },
    "contact": {
      "phone": "+441314447100",
      "email": "info@craiglockhart.com",
      "website_url": "https://www.edinburghleisure.co.uk/venues/craiglockhart",
      "instagram_url": "https://instagram.com/edinburghleisure",
      "facebook_url": "https://facebook.com/craiglockhartsports"
    },
    "hours": {
      "opening_hours": {
        "monday": {"open": "06:00", "close": "22:00"},
        "tuesday": {"open": "06:00", "close": "22:00"},
        "wednesday": {"open": "06:00", "close": "22:00"},
        "thursday": {"open": "06:00", "close": "22:00"},
        "friday": {"open": "06:00", "close": "22:00"},
        "saturday": {"open": "08:00", "close": "20:00"},
        "sunday": {"open": "08:00", "close": "20:00"}
      }
    },
    "sports_facility": {
      "tennis_courts": {
        "total": 12,
        "indoor": 8,
        "outdoor": 4,
        "covered": 8,
        "floodlit": 4,
        "surfaces": ["hard", "clay"],
        "coaching_available": true
      },
      "padel_courts": {
        "total": 4,
        "indoor": 4
      },
      "swimming_pool": {
        "indoor": true,
        "length_m": 25,
        "lanes": 6,
        "family_swim": true,
        "adult_only_swim": true,
        "lessons_available": true
      },
      "gym": {
        "available": true,
        "size_stations": 120,
        "classes_per_week": 60,
        "class_types": ["yoga", "hiit", "pilates", "spin", "strength"]
      },
      "spa": {
        "available": true,
        "sauna": true,
        "steam_room": true,
        "hydro_pool": true
      },
      "amenities": {
        "cafe": true,
        "creche": true,
        "creche_age_min": 6,
        "creche_age_max": 12
      },
      "parking": {
        "spaces": 80,
        "disabled_parking": true,
        "ev_charging": true,
        "ev_connectors": 4
      }
    }
  },

  "source_info": {
    "discovered_by": ["google_places", "edinburgh_leisure_api", "sport_scotland"],
    "primary_source": "edinburgh_leisure_api",
    "verified_date": "2026-01-28"
  },

  "external_ids": {
    "google_places": "ChIJabcdef123456",
    "edinburgh_leisure": "CRAIG-001",
    "sport_scotland": "EH-MULTI-014"
  }
}
```

This is **complete** - every facility the venue offers is captured with quantitative details.

**Example: Incomplete Entity (Current Problem)**
```json
{
  "entity_name": "Craiglockhart Sports Centre",
  "entity_class": "place",
  "slug": "craiglockhart-sports-centre",

  "canonical_activities": [],  // ❌ Should have activities
  "canonical_roles": [],       // ❌ Should have roles
  "canonical_place_types": [], // ❌ Should have place types
  "canonical_access": [],      // ❌ Should have access models

  "modules": {
    "core": {
      "summary": null  // ❌ Should have description
    },
    "location": {
      "street_address": "177 Colinton Road, Edinburgh EH14 1BZ",
      "city": null,     // ❌ Should parse from address
      "postcode": null  // ❌ Should parse from address
    },
    "contact": {
      "phone": null,    // ❌ Missing - available from source
      "website_url": null // ❌ Missing - available from source
    }
    // ❌ Missing sports_facility module entirely
  }
}
```

This is **incomplete** - has basic location but missing all valuable facility data and canonical dimensions.

### Exception Categories

**1. Facility Doesn't Exist** - ACCEPTABLE
- `outdoor_pool: false` for indoor-only venue
- `bar: false` for facility without bar
- **Not a data gap** - accurate representation of reality

**2. Data Not Available from Sources** - TRACK & IMPROVE
- Reviews not provided by API
- Court surfaces not mentioned in source data
- **Action:** Add more data sources, improve extraction prompts

**3. Extraction Failed** - BUG, MUST FIX
- LLM missed court count mentioned in description
- Parser failed to extract opening hours
- **Action:** Fix extraction logic, improve prompts, add validation

**4. Data Quality Issue** - MERGE LOGIC NEEDED
- Google says 10 courts, official API says 12 courts
- Conflicting opening hours from different sources
- **Action:** Implement field-level trust hierarchy, conflict resolution

### Accuracy: Correct Classification, No Hallucinations

**Entity Class Accuracy:**
- Venues correctly classified as `entity_class: place`
- Events correctly classified as `entity_class: event`
- Coaches correctly classified as `entity_class: person`
- Clubs correctly classified as `entity_class: organization`
- Equipment correctly classified as `entity_class: thing`

**Goal:** 100% accuracy (deterministic classification, no LLM guessing)

**Canonical Dimension Accuracy:**
- Only activities actually offered appear in `canonical_activities`
- Only roles actually played appear in `canonical_roles`
- No hallucinated facilities (e.g., entity doesn't have tennis but LLM invents it)

**Goal:** 100% accuracy with confidence tracking on uncertain values

**Deduplication Accuracy:**
- Same entity from multiple sources merged into single record
- Different entities never merged (no false positives)

**Goal:** >99% accuracy (edge cases tracked for manual review)

---

## Lens Configuration Architecture

### Lens Responsibilities Summary

A Lens is a **complete vertical interpretation layer** defined in YAML. It teaches the engine:
- What to look for (vocabulary)
- Where to find it (connector routing)
- How to interpret it (mapping rules, canonical values)
- What to store (domain modules)
- How to display it (UI metadata, SEO templates)

### Full Lens Structure

```yaml
# lenses/edinburgh_finds/lens.yaml

# ============================================================
# METADATA
# ============================================================
lens_id: edinburgh_finds
display_name: "Edinburgh Finds"
description: "Discover sports venues, coaches, clubs, and events in Edinburgh"
version: "1.0.0"

# ============================================================
# QUERY INTERPRETATION
# ============================================================
vocabulary:
  activity_keywords:
    - tennis
    - padel
    - squash
    - badminton
    - swimming
    - gym
    - yoga
    - pilates
    - football
    - rugby

  location_indicators:
    - edinburgh
    - leith
    - portobello
    - stockbridge
    - morningside

  facility_keywords:
    - centre
    - club
    - facility
    - venue
    - pool
    - court

# ============================================================
# CONNECTOR ROUTING
# ============================================================
connector_rules:
  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [tennis, padel, squash, swimming, football, rugby]
    conditions:
      - location: edinburgh

  edinburgh_leisure_api:
    priority: high
    triggers:
      - type: location_match
        locations: [edinburgh]
    conditions:
      - category_search: true

  google_places:
    priority: medium
    triggers:
      - type: always
    budget_limit: 100  # Max API calls per query

# ============================================================
# MAPPING RULES (Raw → Canonical)
# ============================================================
# NOTE: Mapping runs over union of declared source_fields per rule,
#       NOT hardcoded to raw_categories. Engine must match this contract.
mapping_rules:
  # Activities
  - id: activity_tennis_explicit
    pattern: "(?i)\\btennis\\b|racket sports"
    dimension: canonical_activities
    value: tennis
    source_fields: [raw_categories, types, name, description]
    confidence: 0.95

  - id: activity_padel_explicit
    pattern: "(?i)\\bpadel\\b|pádel"
    dimension: canonical_activities
    value: padel
    source_fields: [raw_categories, types, name]
    confidence: 0.98

  - id: activity_swimming_explicit
    pattern: "(?i)swimming|pool|aquatic"
    dimension: canonical_activities
    value: swimming
    source_fields: [raw_categories, types, name, description]
    confidence: 0.90

  # Place Types
  - id: place_type_sports_centre
    pattern: "(?i)sports? centre|multi.?sport"
    dimension: canonical_place_types
    value: sports_centre
    source_fields: [raw_categories, types]
    confidence: 0.95
    applicability:
      entity_class: [place]

  - id: place_type_tennis_club
    pattern: "(?i)tennis club"
    dimension: canonical_place_types
    value: tennis_club
    source_fields: [raw_categories, types, name]
    confidence: 0.98
    applicability:
      entity_class: [place]

  # Roles
  - id: role_facility_provider
    pattern: "(?i)facility|venue|centre"
    dimension: canonical_roles
    value: provides_facility
    source_fields: [raw_categories, types]
    confidence: 0.90

  - id: role_instruction_provider
    pattern: "(?i)coach|instructor|trainer"
    dimension: canonical_roles
    value: provides_instruction
    source_fields: [raw_categories, types, name]
    confidence: 0.95

  # Access
  - id: access_membership_only
    pattern: "(?i)members?.?only|private club"
    dimension: canonical_access
    value: membership
    source_fields: [raw_categories, description]
    confidence: 0.95

  - id: access_pay_and_play
    pattern: "(?i)pay.?and.?play|drop.?in|casual"
    dimension: canonical_access
    value: pay_and_play
    source_fields: [raw_categories, description]
    confidence: 0.90

# ============================================================
# CANONICAL VALUES (Display Metadata)
# ============================================================
canonical_values:
  # Activities
  tennis:
    display_name: "Tennis"
    display_name_plural: "Tennis"
    seo_slug: "tennis"
    icon: "racquet"
    description: "Tennis courts and clubs"
    search_keywords: [tennis, racquet, racket]

  padel:
    display_name: "Padel"
    display_name_plural: "Padel"
    seo_slug: "padel"
    icon: "padel-racquet"
    description: "Padel courts and facilities"
    search_keywords: [padel, pádel]

  swimming:
    display_name: "Swimming"
    display_name_plural: "Swimming"
    seo_slug: "swimming"
    icon: "waves"
    description: "Swimming pools and aquatic centres"
    search_keywords: [swimming, pool, aquatic, swim]

  # Place Types
  sports_centre:
    display_name: "Sports Centre"
    display_name_plural: "Sports Centres"
    seo_slug: "sports-centres"
    icon: "building-columns"
    description: "Multi-sport facilities"

  # Roles
  provides_facility:
    display_name: "Sports Facility"
    display_name_plural: "Sports Facilities"
    seo_slug: "facilities"
    description: "Venues providing sports facilities"

  provides_instruction:
    display_name: "Coach"
    display_name_plural: "Coaches"
    seo_slug: "coaches"
    description: "Coaches and instructors"

  # Access
  membership:
    display_name: "Members Only"
    icon: "lock"
    description: "Membership required"

  pay_and_play:
    display_name: "Pay & Play"
    icon: "credit-card"
    description: "Pay per use, no membership needed"

# ============================================================
# DOMAIN MODULES
# ============================================================
modules:
  sports_facility:
    description: "Sports-specific facility attributes with inventory structure"
    fields:
      # Inventory structure (per-sport)
      tennis_courts:
        type: object
        fields:
          total: integer
          indoor: integer
          outdoor: integer
          covered: integer
          floodlit: integer
          surfaces: array[string]
          coaching_available: boolean
          booking_url: string

      padel_courts:
        type: object
        fields:
          total: integer
          indoor: integer
          outdoor: integer

      swimming_pool:
        type: object
        fields:
          indoor: boolean
          outdoor: boolean
          length_m: integer
          lanes: integer
          family_swim: boolean
          adult_only_swim: boolean
          lessons_available: boolean

      gym:
        type: object
        fields:
          available: boolean
          size_stations: integer
          classes_per_week: integer
          class_types: array[string]

      amenities:
        type: object
        fields:
          cafe: boolean
          restaurant: boolean
          bar: boolean
          creche: boolean
          creche_age_min: integer
          creche_age_max: integer

      parking:
        type: object
        fields:
          spaces: integer
          disabled_parking: boolean
          ev_charging: boolean
          ev_connectors: integer

    # Module field extraction rules (Decision 3)
    field_rules:
      # Deterministic extraction from structured sources
      - rule_id: tennis_courts_total_sport_scotland
        target_path: tennis_courts.total
        source_fields: [TennisCourts, NumTennisCourts]
        extractor: numeric_parser
        confidence: 0.95
        applicability:
          source: [sport_scotland, edinburgh_council]
          entity_class: [place]

      - rule_id: swimming_pool_length
        target_path: swimming_pool.length_m
        source_fields: [PoolLength, pool_length_meters]
        extractor: numeric_parser
        confidence: 0.95
        applicability:
          source: [sport_scotland]

      # LLM extraction from unstructured descriptions
      - rule_id: facility_amenities_llm
        target_path: amenities
        source_fields: [description, editorial_summary, about]
        extractor: llm_structured
        schema:
          cafe: boolean
          restaurant: boolean
          bar: boolean
          creche: boolean
        confidence: 0.70
        applicability:
          source: [google_places, serper]
        conditions:
          - any_field_missing: [cafe, restaurant, bar]

# ============================================================
# MODULE TRIGGERS
# ============================================================
module_triggers:
  - when:
      dimension: canonical_activities
      values: [tennis, padel, squash, badminton]
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

  - when:
      dimension: canonical_activities
      values: [swimming]
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

  - when:
      dimension: canonical_activities
      values: [gym, yoga, pilates]
    add_modules: [sports_facility]
    conditions:
      - entity_class: place

# ============================================================
# DERIVED GROUPINGS (View-Only, Computed at Query Time)
# ============================================================
derived_groupings:
  coaches_and_instructors:
    name: "Coaches & Instructors"
    description: "Individual coaches and training providers"
    filters:
      - entity_class: person
      - canonical_roles: provides_instruction

  members_clubs:
    name: "Members Clubs"
    description: "Private membership clubs"
    filters:
      - entity_class: organization
      - canonical_access: membership

  pay_and_play_venues:
    name: "Pay & Play Venues"
    description: "Facilities accepting casual bookings"
    filters:
      - entity_class: place
      - canonical_access: pay_and_play

# ============================================================
# SEO TEMPLATES
# ============================================================
seo_templates:
  entity_page:
    title: "{entity_name} | Edinburgh Finds"
    description: "{summary}"

  category_page:
    title: "{activity_name} in Edinburgh | Edinburgh Finds"
    description: "Discover the best {activity_name} venues in Edinburgh"

  location_page:
    title: "{activity_name} in {location} | Edinburgh Finds"
    description: "Find {activity_name} facilities in {location}, Edinburgh"
```

### Current Implementation Status

**Implemented (Working):**
- ✅ Query vocabulary (`vocabulary`)
- ✅ Connector routing (`connector_rules`)

**Designed but Not Wired Up:**
- ⚠️ Mapping rules (`mapping_rules`) - infrastructure exists (category_mapper.py) but not lens-driven (contains domain literals)
- ⚠️ Module triggers (`module_triggers`) - schema defined, validator built, not used in extraction
- ⚠️ Canonical values (`canonical_values`) - structure designed, not implemented
- ⚠️ Domain modules (`modules`) - schema defined, field extraction rules designed (Decision 3), not yet implemented

**To Be Implemented:**
- ❌ Derived groupings (query-time views)
- ❌ SEO templates (frontend metadata generation)

### Lens Authoring Contract & Canonical Registry (Decision 2)

The lens is not a free-form configuration file - it is a **compiled runtime contract** with strict validation, reproducibility guarantees, and evidence-driven construction.

#### 1. Lens as a Compiled Contract (Not a Draft Artifact)

**Core Principle:** `lens.yaml` is treated as a compiled, deterministic runtime contract consumed by the engine, not as a draft configuration artifact.

**Contract Properties:**
- **Deterministic:** Given the same lens.yaml and raw data, extraction produces identical output
- **Fully Validated:** Lens must pass all validation gates at load time (fail-fast)
- **Versioned:** Lens changes are tracked, lens_hash enables reproducibility debugging
- **Hashable:** Content-addressable via SHA-256 for reproducibility and cache invalidation
- **Test-Backed:** Every mapping rule, trigger, and canonical value must be justified by real connector payload fixtures

**Lens Loading Lifecycle:**
```
1. Load lens.yaml from disk (bootstrap only)
2. Validate schema structure (YAML well-formed)
3. Validate canonical registry integrity (all references resolve)
4. Validate connector references (all exist in engine registry)
5. Compute lens_hash (for reproducibility tracking)
6. Convert to plain dict (lens_contract)
7. Inject into ExecutionContext
8. FAIL FAST if any validation fails (abort before extraction)
```

**Validation Failures Abort Execution:**
- Malformed YAML → Crash with schema error at startup
- Orphaned canonical reference → Crash before orchestration begins
- Missing connector in registry → Crash before query planning
- Duplicate rule identifiers → Crash at validation

**Rationale:** Lens errors must surface immediately at bootstrap, not silently during extraction. A broken lens.yaml should never reach production runtime.

#### 2. Canonical Registry as Single Source of Truth

**Problem:** Without a canonical registry, mapping rules can introduce values that don't exist in display metadata, causing silent failures in the frontend.

**Solution:** All canonical values (activities, roles, place_types, access) must be declared exactly once in a **canonical registry section** within the lens.

**Registry Structure:**
```yaml
# lenses/edinburgh_finds/lens.yaml

canonical_values:
  # Activities (declared once, referenced everywhere)
  tennis:
    display_name: "Tennis"
    seo_slug: "tennis"
    icon: "racquet"

  padel:
    display_name: "Padel"
    seo_slug: "padel"
    icon: "padel-racquet"

  # Roles (universal function keys)
  provides_facility:
    display_name: "Sports Facility"
    seo_slug: "facilities"

  # Place Types
  sports_centre:
    display_name: "Sports Centre"
    seo_slug: "sports-centres"

  # Access Models
  pay_and_play:
    display_name: "Pay & Play"
    icon: "credit-card"
```

**Validation Invariants:**

**Invariant 1: Mapping Rule Completeness**
- Every mapping rule `value` MUST exist in `canonical_values` registry
- Orphaned references cause validation failure at lens load time
- Example violation:
  ```yaml
  mapping_rules:
    - pattern: "(?i)squash"
      value: squash  # ❌ FAIL if "squash" not in canonical_values
  ```

**Invariant 2: Module Reference Integrity**
- Every module referenced in `module_triggers` MUST exist in `modules` registry
- Example violation:
  ```yaml
  module_triggers:
    - add_modules: [wine_production]  # ❌ FAIL if not in modules registry
  ```

**Invariant 3: Connector Reference Validation**
- Every connector referenced in `connector_rules` MUST exist in engine connector registry
- Fail-fast prevents typos and stale references
- Example violation:
  ```yaml
  connector_rules:
    tripadvisor_api:  # ❌ FAIL if not in engine/orchestration/registry.py
      priority: high
  ```

**Invariant 4: No Magic Strings**
- All canonical values referenced outside the registry MUST resolve against it
- Prevents silent drift where dimension values lack display metadata
- Engine consumes opaque strings, lens provides interpretation

**Purpose:**
- **Prevents Silent Drift:** Impossible to add mapping rule without display metadata
- **Enables Validation:** Lens validator can check all references resolve
- **Makes Lenses Portable:** Lens.yaml is self-contained, no hidden dependencies
- **Supports Tooling:** Autocomplete, linting, schema validation all reference registry

#### 3. Structured Mapping Rules (Not Free Regex Lists)

**Problem:** Monolithic regex patterns are hard to audit, test, and maintain. Broad fuzzy matching causes false positives.

**Solution:** Mapping rules must be small, composable, and explicitly structured with metadata.

**Rule Structure:**
```yaml
mapping_rules:
  - id: activity_tennis_explicit      # Unique identifier
    pattern: "(?i)\\btennis\\b"       # Python re syntax (word boundaries)
    dimension: canonical_activities   # Target dimension
    value: tennis                     # Canonical registry reference
    source_fields: [raw_categories, types, name]  # Where to apply
    confidence: 0.95                  # Extraction confidence
    applicability:                    # Optional constraints
      entity_class: [place, organization]

  - id: role_facility_provider
    pattern: "(?i)facility|venue|centre"
    dimension: canonical_roles
    value: provides_facility
    source_fields: [raw_categories, types]
    confidence: 0.90
```

**Rule Metadata Requirements:**
- **id:** Unique identifier for the rule (enables duplicate detection)
- **pattern:** Regex pattern (Python `re` module syntax)
- **dimension:** Which canonical dimension to populate
- **value:** Canonical value reference (MUST exist in canonical_values)
- **source_fields:** Which raw data fields this rule inspects
- **confidence:** Extraction confidence score (0.0-1.0)
- **applicability** (optional): Entity class constraints

**Design Principles:**
- **Small and Composable:** One pattern per rule, not monolithic compound patterns
- **Explicit Positive Rules:** Prefer explicit patterns over broad fuzzy matching
- **Targeted Scope:** Declare which source_fields the rule applies to
- **Testable:** Each rule should have fixture showing it matches correctly
- **Auditable:** Rule id enables tracking which rule fired for debugging

**Anti-Patterns (Forbidden):**
- ❌ Broad patterns: `(?i).*sport.*` (matches too much)
- ❌ Implicit scope: Not declaring which source fields rule applies to
- ❌ Missing confidence: All rules must declare confidence
- ❌ Duplicate ids: Each rule must have unique identifier

#### 4. Evidence-Driven Vocabulary Expansion

**Problem:** Speculative taxonomies diverge from reality. Adding hypothetical categories that never appear in real data wastes effort and creates noise.

**Solution:** Lens vocabulary and mapping rules must be grown from **observed connector payloads**, not speculative taxonomies.

**Evidence Requirement:**
- Every new mapping rule MUST be justified by a real raw ingestion payload
- Raw payload recorded as fixture (not mocked): `tests/fixtures/raw_ingestions/<connector>/<example>.json`
- Fixture documents why rule is needed and what it should extract
- Fixtures are captured real connector responses, not hand-crafted test data

**Expansion Workflow:**
```
1. Run query, collect raw ingestions
2. Inspect payloads for new categories/patterns
3. Create fixture from real payload
4. Write mapping rule to handle observed pattern
5. Add canonical value to registry (with display metadata)
6. Write test validating rule matches fixture
7. Commit fixture + rule + test together
```

**Example Evidence Chain:**
```yaml
# Fixture: tests/fixtures/raw_ingestions/google_places/powerleague_portobello.json
{
  "types": ["sports_complex", "point_of_interest"],
  "name": "Powerleague Portobello"
}

# Mapping Rule (justified by fixture above)
mapping_rules:
  - id: place_type_sports_complex
    pattern: "(?i)sports.?complex"
    dimension: canonical_place_types
    value: sports_centre
    source_fields: [types, raw_categories]
    confidence: 0.95
    # Evidence: tests/fixtures/raw_ingestions/google_places/powerleague_portobello.json
```

**Anti-Patterns (Forbidden):**
- ❌ Adding canonical values without observed payloads
- ❌ Creating mapping rules for hypothetical future data
- ❌ Expanding vocabulary based on "what might exist" vs "what was observed"

**Purpose:**
- **Prevents Taxonomy Drift:** Only add categories that actually appear
- **Prevents Hallucination:** No speculative canonical values
- **Ensures Test Coverage:** Every rule has real payload fixture
- **Documents Provenance:** Clear why each rule exists

#### 5. Minimal Viable Lens First, Then Expand Safely

**Problem:** Trying to build a complete taxonomy upfront is impossible and wasteful. Start small, grow incrementally.

**Solution:** First lens iteration must support **exactly one concrete validation entity** with minimal but complete canonical coverage.

**Minimal Viable Lens Deliverables:**
- **One Validation Entity:** Powerleague Portobello (or equivalent concrete entity)
- **At Least One Value Per Dimension:**
  - `canonical_activities`: At least 1 activity (e.g., "football")
  - `canonical_roles`: At least 1 role (e.g., "provides_facility")
  - `canonical_place_types`: At least 1 place type (e.g., "sports_centre")
  - `canonical_access`: At least 1 access model (e.g., "pay_and_play")
- **At Least One Module Trigger:** Attach sports_facility module for validation entity
- **At Least One Module Field:** Extract at least one facility inventory field

**Acceptance Criteria for MVP Lens:**
```sql
-- Validation query must return non-empty canonical dimensions
SELECT
  entity_name,
  canonical_activities,      -- Expected: non-empty array
  canonical_roles,           -- Expected: non-empty array
  canonical_place_types,     -- Expected: non-empty array (if place)
  canonical_access,          -- Expected: non-empty array
  modules->'sports_facility' -- Expected: non-empty object
FROM entities
WHERE slug = 'powerleague-portobello';

-- All arrays must contain at least 1 value
-- Module must contain at least 1 populated field
```

**Expansion Strategy:**
- **Phase 1:** Single entity, minimal canonical coverage (MVP lens)
- **Phase 2:** Expand to 5-10 entities, add observed canonical values as needed
- **Phase 3:** Expand to 50+ entities, refine mapping rules based on errors
- **Phase 4:** Expand to hundreds, automated quality monitoring

**Rationale:**
- Start with proof of concept (one perfect entity)
- Expand incrementally based on real ingestion coverage
- Prevent premature taxonomy optimization
- Each expansion driven by observed payloads, not speculation

#### 6. Lens Validation Gates (Architectural)

**Problem:** Invalid lenses cause silent failures during extraction. Validation must happen upfront at load time.

**Solution:** Implement comprehensive validation gates that fail-fast before any extraction occurs.

**Validation Gates (All Required):**

**Gate 1: Schema Validation**
- YAML structure matches lens schema
- All required sections present (vocabulary, connector_rules, mapping_rules, modules, module_triggers, canonical_values)
- Field types correct (arrays are arrays, objects are objects)

**Gate 2: Canonical Reference Integrity**
- All mapping rule `value` fields exist in `canonical_values`
- All module trigger `add_modules` exist in `modules` registry
- No orphaned references

**Gate 3: Connector Reference Validation**
- All connectors in `connector_rules` exist in engine connector registry
- Prevents stale references or typos
- Fails with clear error listing missing connectors

**Gate 4: Duplicate Identifier Validation**
- All mapping rule `id` fields are unique
- All module trigger `id` fields are unique
- Prevents conflicts and ambiguity
- Fails with list of duplicate ids

**Gate 5: Pattern Compilation Validation**
- All mapping rule `pattern` fields compile as valid Python regex
- Patterns validated at lens load time using `re.compile()`
- Fails with rule `id` and regex error if pattern invalid
- Prevents runtime regex compilation errors

**Gate 6: Smoke Coverage Validation**
- At least one fixture validates each mapping rule
- Validation entity produces non-empty canonical dimensions
- At least one module trigger fires for validation entity

**Gate 7: Fail-Fast Enforcement**
- ANY validation failure aborts execution immediately
- Clear error messages indicating which gate failed
- No silent fallback behavior
- Lens errors never reach production runtime

**Validation Execution:**
```python
# engine/lenses/loader.py
def load_lens(lens_id: str) -> VerticalLens:
    # 1. Load YAML from disk
    raw_yaml = load_yaml_file(f"lenses/{lens_id}/lens.yaml")

    # 2. Schema validation (Gate 1)
    validate_lens_schema(raw_yaml)

    # 3. Canonical reference integrity (Gate 2)
    validate_canonical_references(raw_yaml)

    # 4. Connector reference validation (Gate 3)
    # Fail if lens references connectors not in engine registry
    # Lens only defines rules for connectors it uses
    validate_connector_references(raw_yaml)

    # 5. Duplicate identifier validation (Gate 4)
    validate_unique_rule_ids(raw_yaml)

    # 6. Pattern compilation validation (Gate 5)
    # All mapping rule patterns must compile as valid Python regex
    validate_pattern_compilation(raw_yaml)

    # 7. Smoke coverage validation (Gate 6)
    # Performed after lens object creation via tests

    # 8. Create VerticalLens object (Gate 7: fail-fast on any error)
    lens = VerticalLens.from_dict(raw_yaml)

    # If we reach here, lens is valid
    return lens

# All validation failures raise LensValidationError
# Bootstrap crashes before orchestration begins
```

**Error Handling:**
- Validation errors are fatal (crash with clear error message)
- No recovery or fallback behavior
- Broken lens.yaml must be fixed before system can run
- Validation errors surface in development, never production

**Purpose:**
- **Fail Fast:** Catch errors at bootstrap, not during extraction
- **Clear Feedback:** Validation errors indicate exactly what's wrong
- **Prevents Silent Failures:** Broken lenses never reach runtime
- **Enforces Quality:** Lens must be valid before acceptance

---

## Architectural Boundaries

### What Lives in Engine vs. Lens

| Concern | Engine | Lens |
|---------|--------|------|
| **Entity classification** | ✅ `entity_class` (place/person/org/event/thing) | ❌ No domain-specific types |
| **Dimension storage** | ✅ Four text[] arrays with GIN indexes | ❌ No interpretation of values |
| **Dimension values** | ❌ Never hardcoded | ✅ Defined in canonical_values |
| **Mapping rules** | ❌ No domain patterns | ✅ Regex patterns for raw → canonical |
| **Module schemas** | ✅ Universal modules (core, location, contact) | ✅ Domain modules (sports_facility) |
| **Module population** | ⚠️ Organizes data into modules | ✅ Defines what data to capture |
| **Query interpretation** | ⚠️ Generic feature extraction | ✅ Vocabulary and routing rules |
| **Connector selection** | ✅ Orchestration logic | ✅ Routing rules (which connectors) |
| **Deduplication** | ✅ Cross-source matching | ❌ No domain-specific logic |
| **Display labels** | ❌ Never displays dimension values | ✅ Display names, icons, descriptions |
| **SEO metadata** | ❌ No content generation | ✅ Templates and slug generation |

### Enforcement Mechanisms

**Import Boundary Test** (`tests/engine/test_purity.py`):
- Prevents `engine/` code from importing `lenses/` modules
- Ensures engine cannot directly access lens logic

**Structural Purity Test** (`tests/engine/test_purity.py`):
- Prevents literal string comparisons on dimension values
- Blocks: `if "tennis" in canonical_activities` (violates vertical-agnostic principle)
- Allows: `if len(canonical_activities) > 0` (generic logic)

**Entity Model Purity Test** (`tests/engine/config/test_entity_model_purity.py`):
- Validates `entity_model.yaml` has no domain-specific keywords
- Ensures all dimensions use `canonical_*` naming
- Restricts modules to universal set

---

## Scaling to New Verticals

### Adding Wine Discovery (Zero Engine Changes)

**Step 1:** Create Lens configuration
```bash
mkdir -p lenses/wine_discovery
touch lenses/wine_discovery/lens.yaml
```

**Step 2:** Define domain vocabulary
```yaml
# lenses/wine_discovery/lens.yaml
vocabulary:
  activity_keywords:
    - wine_tasting
    - vineyard_tour
    - wine_pairing
    - sommelier_course

  location_indicators:
    - bordeaux
    - burgundy
    - napa
    - tuscany
```

**Step 3:** Define connector routing
```yaml
connector_rules:
  vivino_api:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [wine, winery, vineyard]

  wine_searcher:
    priority: medium
    triggers:
      - type: category_search
```

**Step 4:** Define mapping rules
```yaml
mapping_rules:
  - pattern: "(?i)winery|vineyard|wine estate"
    dimension: canonical_place_types
    value: winery
    confidence: 0.95

  - pattern: "(?i)wine tasting|tasting room"
    dimension: canonical_activities
    value: wine_tasting
    confidence: 0.98
```

**Step 5:** Define domain module
```yaml
modules:
  wine_production:
    description: "Wine production and vineyard attributes"
    fields:
      vineyard_acres: integer
      production_volume_cases: integer
      grape_varieties: array[string]
      wine_styles: array[string]
      tasting_room: boolean
      tours_available: boolean
```

**Step 6:** Define module triggers
```yaml
module_triggers:
  - when:
      dimension: canonical_place_types
      values: [winery, vineyard]
    add_modules: [wine_production]
    conditions:
      - entity_class: place
```

**Result:** Wine Discovery vertical operational with **ZERO engine code changes**. Same database schema, same extraction pipeline, same orchestration logic - just new Lens configuration.

### Multi-Vertical Entities

**Scenario:** A venue offers both sports facilities and wine events (e.g., tennis club with wine bar).

**Solution:** Entity belongs to multiple lenses.

```sql
-- LensEntity join table
INSERT INTO lens_entities (lens_id, entity_id) VALUES
  ('edinburgh_finds', 'ent_abc123'),
  ('wine_discovery', 'ent_abc123');
```

**Data model:**
```json
{
  "entity_name": "The Tennis & Wine Club",
  "entity_class": "place",

  "canonical_activities": ["tennis", "wine_tasting"],
  "canonical_roles": ["provides_facility"],
  "canonical_place_types": ["tennis_club", "wine_bar"],

  "modules": {
    "sports_facility": {
      "tennis_courts": {...}
    },
    "wine_production": {
      "tasting_room": true,
      "wine_styles": ["red", "white", "sparkling"]
    }
  }
}
```

**Display:**
- Appears in Edinburgh Finds as "Sports Facility with Wine Events"
- Appears in Wine Discovery as "Wine Bar with Tennis Courts"
- Same entity, different lens interpretation

---

## Guiding Principles

### 1. Complete Data Over Partial Data
Capture ALL available information. Empty fields should be exceptions (facility doesn't exist, data not available) not the norm.

**Target:** >80% field population for entities where data is publicly available.

### 2. Reality Over Tests
Validate with real queries, real connectors, real Entity table inspection. Tests that pass with mock data but fail with real connectors are worse than no tests.

**Fixtures are not mocks** — they are recorded real connector payloads and are required for mapping rule validation. Each mapping rule must be backed by an observed real payload fixture.

**Validation strategy:** End-to-end smoke tests with actual API calls, database inspection.

### 3. Accuracy Over Coverage
100 perfectly accurate entities > 500 entities with wrong classifications and missing data.

**Quality gate:** Manual review of first 100 entities from each vertical before scaling up.

### 4. Incremental Validation
Fix one thing (e.g., classification), validate end-to-end (run query, inspect Entity table), THEN fix next thing.

**Anti-pattern:** Fix 10 things in code, run once, discover broken. **Pattern:** Fix 1 thing, validate, commit, repeat.

### 5. Rich Facility Data is the Differentiator
Basic listings (name/address/phone) are commodity data. Comprehensive facility details (court counts, pool specs, amenities, pricing, reviews) are the unique value.

**Edinburgh Finds USP:** "Know before you go" - complete facility inventory, not just contact info.

### 6. Source Provenance Always Tracked
Every entity should track which sources contributed, when it was verified, what external IDs exist. Enables debugging, trust decisions, and incremental updates.

**Implementation:** `source_info` field captures discovered_by, primary_source, verified_date.

### 7. Vertical-Agnostic is Non-Negotiable
If adding a new vertical requires engine code changes, the architecture has failed. Lens configuration should be sufficient.

**Enforcement:** Purity tests fail CI builds if engine references domain-specific terms.

---

## Success Metrics

### Entity Quality Metrics

**Completeness:**
- Universal fields populated: >95% (name, location, contact)
- Canonical dimensions populated: >90% (activities, roles, place types, access)
- Modules attached: 100% where triggered
- Module fields populated: >80% where applicable

**Accuracy:**
- entity_class classification: 100% (deterministic, no errors)
- Canonical dimension accuracy: >99% (validated against ground truth)
- Deduplication accuracy: >99% (same entity merged, different entities separated)
- No hallucinations: 100% (LLM only extracts observed data, never invents)

**Freshness:**
- source_info.verified_date within 30 days: >80%
- Incremental updates on entity revisit
- Stale data flagged for re-ingestion

### System Quality Metrics

**Engine Purity:**
- Zero domain-specific imports in engine code
- Zero literal string comparisons on dimension values
- Zero domain keywords in entity_model.yaml

**Lens Coverage:**
- Query interpretation: 100% (all queries use lens vocabulary)
- Connector routing: 100% (all connectors selected via lens rules)
- Mapping rules: Target 100% (all raw categories mapped to canonical)
- Module population: Target 100% (all triggered modules populated)

**Operational:**
- API cost per entity: <$0.10
- Extraction latency: <5 seconds per entity
- Orchestration latency: <30 seconds per query
- Database write latency: <1 second per entity

---

## Current Implementation Status

### What's Complete ✅

1. **Database schema migrated** - New model with entity_class, four dimensions, modules JSONB is live
2. **Query orchestration** - Lens-driven connector routing operational
3. **Entity classification** - Deterministic entity_class resolution works
4. **Infrastructure built** - Validators, module system, deduplication logic exist
5. **Connector registry** - 6 connectors integrated with metadata

### What's Incomplete ❌

1. **Extractor updates** - Don't populate canonical dimension arrays
2. **Lens mapping rules** - Not wired up in extraction flow
3. **Module population** - Extractors don't organize data into modules; field extraction rules designed (Decision 3) but not yet implemented
4. **Module triggers** - Defined in schema but not applied during extraction
5. **Full lens.yaml** - Only query vocabulary and connector rules exist; mapping rules, module definitions with field_rules, and canonical values need to be added

### What's Misaligned ⚠️

1. **category_mapper.py** - Mapping algorithm can stay in engine but must be purely lens-driven via ctx.lens_contract rules (no domain literals)
2. **Dimension extractor functions** - Exist but not called (orphaned code)
3. **EntityFinalizer expectations** - Reads fields extractors don't populate

### Implementation Roadmap

**Phase 1: Wire Up Mapping Rules (Critical)**
1. Update category_mapper to consume ctx.lens_contract rules (remove domain literals)
2. Update extractors to populate raw_categories
3. Apply lens mapping_rules during extraction/finalization
4. Validate canonical dimension arrays populated

**Definition of Done:** Running a real query results in non-empty `canonical_*` arrays in the Entity table. Validation query:
```sql
SELECT canonical_activities, canonical_roles, canonical_place_types, canonical_access
FROM entities
LIMIT 10;
-- Expected: Populated arrays where data is available (not empty {})
```

**Phase 2: Module Population (High Priority)**
1. Implement generic module field extractor (Decision 3: declarative, lens-driven)
2. Implement extractor vocabulary (numeric_parser, regex_capture, llm_structured, etc.)
3. Add field_rules to lens module definitions
4. Apply module_triggers to attach domain modules
5. Validate modules JSONB populated with namespaced data using lens field rules

**Phase 3: Full Lens System (Medium Priority)**
1. Implement canonical_values for display metadata
2. Build derived_groupings for query-time views
3. Create SEO templates for frontend

**Phase 4: Cleanup (Low Priority)**
1. Delete old_db_models.py
2. Remove orphaned dimension extractor functions
3. Consolidate lens configuration files

---

## Conclusion

Edinburgh Finds is a **universal entity extraction engine** with **pluggable vertical interpretations**. The architecture cleanly separates what the engine stores (universal classifications, opaque dimensions, namespaced modules) from what the lens interprets (domain vocabulary, mapping rules, display metadata).

**The north star:** Adding a new vertical (Wine Discovery, Restaurant Finder, Event Calendar) requires **ZERO engine code changes** - only a new Lens YAML configuration.

**Current status:** Infrastructure is 90% complete. Extraction layer needs updates to populate canonical dimensions and modules. Lens system needs full mapping_rules and module_triggers implementation.

**Next milestone:** Complete Phase 1 (wire up mapping rules) to prove end-to-end data flow from raw ingestion → canonical dimensions → Entity table → frontend display.

This document defines the architectural principles and success criteria. Implementation plans live in `docs/plans/` (e.g., `2026-01-28-end-to-end-extraction-implementation.md`).

---

## Implementation Guidance

Every implementation plan should:
- ✅ **Reference this vision** to ensure architectural alignment
- ✅ **Define success as "Entity table has complete, accurate data"** - validate with real database queries, not mocks
- ✅ **Include before/after validation with real queries** - run actual queries, inspect Entity table, verify canonical dimensions populated
- ✅ **Focus on outcomes (data completeness, accuracy)** not process - tests measure data quality, not code coverage
- ✅ **Be small and focused** - fix ONE specific gap at a time (e.g., "wire up mapping rules" not "fix extraction")
- ✅ **Use component names** - EntityFinalizer, SlugGenerator, ModuleValidator (helps locate code to modify)
- ✅ **Track exceptions** - document why fields are null (facility doesn't exist vs. extraction failed)

**Reality Checks:**
- Run `SELECT canonical_activities, canonical_roles FROM entities LIMIT 10` - are arrays populated?
- Run `SELECT modules FROM entities WHERE entity_class = 'place' LIMIT 5` - is JSONB namespaced correctly?
- Run orchestration with real query - does Entity table have complete data?

---

**Last Updated:** 2026-01-29
**Document Status:** Definitive architectural specification
**Reference Implementation:** Edinburgh Finds (first vertical lens)
