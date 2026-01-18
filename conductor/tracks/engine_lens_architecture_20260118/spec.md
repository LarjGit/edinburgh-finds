# Track: Engine-Lens Architecture Refactor

## Status
**Ready for Implementation**

## Problem Statement

The current architecture mixes vertical-specific concepts (padel, tennis, gym, coach, venue) with the universal entity engine. This creates several critical issues:

### Current Issues

1. **❌ Engine contains vertical-specific domain knowledge**
   - Sports-specific modules (sports_facility) defined in engine layer
   - Activity-specific triggers (padel → sports_facility module)
   - Domain amenities (cafe, restaurant, bar) in universal amenities module
   - Entity classification tied to vertical vocabulary (VENUE, COACH)

2. **❌ Dimensions stored as JSON instead of Postgres arrays**
   - Activities, roles, place_types stored in JSONB
   - No GIN indexes for efficient faceted filtering
   - Query performance degraded for multi-facet searches
   - Cannot use Prisma array filters (has, hasSome, hasEvery)

3. **❌ No clear separation between engine and lens layers**
   - Canonical taxonomy mixed with interpretation logic
   - Mapping rules embedded in engine code
   - UI labels and SEO slugs scattered across codebase
   - No formal facet system for navigation/filtering

4. **❌ Module triggers based on string values, not structured metadata**
   - Implicit value-based triggers (e.g., "padel" string → sports_facility)
   - Key collisions between facets (activity vs place_type)
   - No explicit facet attribution for canonical values

5. **❌ Role concept conflated with entity_class**
   - Roles like "provides_facility", "sells_goods" stored inconsistently
   - No internal-only facets (role facet needed but not exposed to UI)
   - Vertical-specific role labels (Venue, Coach, Retailer) hardcoded

6. **❌ Blocks horizontal scaling to new verticals**
   - Adding wine discovery requires engine code changes
   - Cannot reuse same dimensions (canonical_activities) for different interpretations
   - Each vertical duplicates taxonomy and mapping infrastructure

### Root Cause

**No formal architectural boundary** between:
- **Engine Layer** (universal, vertical-agnostic entity management)
- **Lens Layer** (vertical-specific interpretation, UI, taxonomy, domain modules)

## Vision

**Separate a universal, vertical-agnostic Entity Engine from vertical-specific Lens Layer.**

We are separating a universal, vertical-agnostic entity engine from a lens layer that owns all interpretation, taxonomy, and domain behavior, with strict contracts and zero leakage between layers.

```
┌─────────────────────────────────────────────────────────────────┐
│ LENS LAYER (Vertical-Specific)                                 │
│ - Facet definitions (activity, role, place_type, access)       │
│ - Canonical values with interpretation (labels, icons, colors) │
│ - Mapping rules (raw categories → canonical values)            │
│ - Derived groupings (entity_class + roles logic)               │
│ - Domain modules (sports_facility, wine_production)            │
│ - Module triggers (value-based, explicit list format)          │
│ - SEO templates, UI config                                     │
│ - Produces: LensContract (plain data object/dict)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓ LensContract
┌─────────────────────────────────────────────────────────────────┐
│ ENGINE LAYER (Vertical-Agnostic)                                │
│ - Consumes: LensContract ONLY (never imports from lenses/)     │
│ - entity_class (place, person, organization, event, thing)     │
│ - Dimensions as Postgres text[] arrays:                        │
│   • canonical_activities (String[], GIN indexed)               │
│   • canonical_roles (String[], GIN indexed)                    │
│   • canonical_place_types (String[], GIN indexed)              │
│   • canonical_access (String[], GIN indexed)                   │
│ - Modules as JSONB (flexible attribute storage)                │
│ - Universal modules only (core, location, contact, hours)      │
│ - Opaque dimension values (zero interpretation)                │
│ - Entity-class-based module triggers only                      │
│ - Structural purity: No literal string comparisons on values   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

#### Engine Layer (Vertical-Agnostic)

**Core Responsibilities:**
- **LensContract consumption**: Engine consumes LensContract ONLY (never imports from lenses/)
  - Application bootstrap wires lens → engine
  - LensContract is a plain data object/dict produced by lenses/loader
- **entity_class** (required, single-valued): place, person, organization, event, thing
- **Multi-valued dimensions**: Stored as **Postgres text[] arrays (String[])** with GIN indexes
  - `canonical_activities` (e.g., ["padel", "tennis"])
  - `canonical_roles` (e.g., ["provides_facility", "sells_goods"])
  - `canonical_place_types` (e.g., ["sports_centre", "outdoor_facility"])
  - `canonical_access` (e.g., ["membership", "pay_and_play"])
  - **FIXED DIMENSION SET**: All future facets MUST map onto these four canonical_* dimensions
  - **Semantic overload accepted**: No new engine dimensions or dimension bags introduced
- **Universal modules only**: core, location, contact, hours, amenities (universal amenities: wifi, parking_available, disabled_access)
- **Opaque dimension values**: Engine treats all canonical values as strings with ZERO interpretation
- **NO vertical concepts**: No references to sports, padel, wine, gym, coach, venue, etc.
- **NO domain modules**: No sports_facility, wine_production, fitness_facility in engine

**Structural Purity Rules (Engine Code):**
- ❌ **FORBIDDEN**: Literal string comparisons against dimension values (e.g., `if "padel" in activities`)
- ✅ **ALLOWED**: Branching on entity_class (e.g., `if entity_class == "place"`)
- ✅ **ALLOWED**: Set/collection operations on opaque strings (union, intersection, membership)
- ✅ **ALLOWED**: Emptiness/existence checks (e.g., `if canonical_activities`)
- ✅ **ALLOWED**: Passing opaque strings through unchanged

**Deterministic Classification Rules (Priority Order):**
1. **Time-bounded** (has start/end times) → `event`
2. **Physical location** (lat/lng or street address) → `place`
3. **Membership/group** entity with no fixed location → `organization`
4. **Named individual** → `person`
5. **Tie-breaker**: Primary physical site → `place`, otherwise → `organization`

**Module Triggers (Engine):**
- ONLY entity_class-based triggers (e.g., place → location module)
- NO value-based triggers (no "padel" → sports_facility)
- **NOTE**: Engine module triggers are entity_class-based; lens module triggers are value-based (via LensContract)

#### Lens Layer (Vertical-Specific)

**Core Responsibilities:**
- **Facets**: UI groupings that map to engine dimensions (includes internal-only role facet)
  - Facet config includes: dimension_source (DB column), ui_label, display_mode, order, icons
- **Canonical values**: Vertical-specific taxonomy with ALL interpretation (labels, slugs, icons, colors)
  - **Role keys**: Stored as universal function-style keys (provides_facility, sells_goods, provides_instruction, membership_org)
  - **display_name**: Lens labels roles with vertical/product terminology via display_name
- **Mapping rules**: Raw categories → canonical values (regex-based)
  - **NOTE**: Confidence thresholds live in LensContract/lens config, not hardcoded in engine
- **Domain modules**: Vertical-specific attribute modules (sports_facility, wine_production)
- **Module triggers**: Value-based triggers with explicit facet/value pairs
  - Format: `{when: {facet: activity, value: "padel"}, add_modules: ["sports_facility"]}`
  - **Note**: `facet` refers to the canonical value's facet key as defined by the lens (lens.facets keys), NOT the DB column name
- **Derived groupings**: Compute UI groupings from entity_class + roles (no listing_type facet)
  - **NOTE**: Groupings are derived/view-only (not stored in database)
  - AND logic within rule: entity must match all conditions in a rule
  - OR logic across rules: entity matches if any rule matches
- **SEO templates**: URL patterns and page metadata generation

**Hybrid Config Approach:**
- YAML for facet definitions, values, mapping rules, module definitions
- Python helpers for generic transformations only (no vertical-specific logic)

### Module System

**Engine Modules (Universal Only):**
- core, location, contact, hours, amenities (universal amenities: wifi, parking_available, disabled_access)
- NO cafe, restaurant, bar (these are food service specific)
- NO court_count, sports fields (these are domain specific)

**Lens Modules (Domain Specific):**
- sports_facility (inventory JSON structure for per-activity courts/facilities)
- food_service (cafe, restaurant, bar)
- wine_production, fitness_facility, etc.

**Composition Rules:**
- No inheritance in v1
- **Module namespacing required**: No flattened modules JSONB (must be namespaced)
- **No duplicate module keys**: Each module appears once in modules JSONB
- **Field names may duplicate across modules**: Namespacing makes this safe (e.g., sports_facility.name and wine_production.name allowed)

## Goals

### Must-Have (Core Track)

1. **Engine Purity**
   - ✅ Remove all vertical-specific concepts from engine layer
   - ✅ Remove domain modules from engine (sports_facility, etc.)
   - ✅ Universal modules only (core, location, contact, hours, amenities)
   - ✅ Universal amenities only (wifi, parking_available, disabled_access)
   - ✅ Opaque dimension values (engine has zero interpretation)
   - ✅ Entity-class-based module triggers only

2. **Postgres Text[] Arrays for Dimensions**
   - ✅ Migrate dimensions from JSONB to `String[]` (Postgres text[] arrays)
   - ✅ Create GIN indexes on all dimension arrays
   - ✅ Update Prisma schema with array types and defaults
   - ✅ Implement Prisma array filter queries (has, hasSome, hasEvery)

3. **Lens Layer Implementation**
   - ✅ Create lens configuration structure (YAML)
   - ✅ Implement facet system with dimension_source mapping
   - ✅ Define canonical values with full interpretation metadata
   - ✅ Implement mapping rules (raw → canonical)
   - ✅ Create role facet (internal-only, not shown in UI)
   - ✅ Universal role keys (provides_facility, sells_goods, provides_instruction, membership_org)
   - ✅ Role display_name for vertical-specific labeling
   - ✅ Implement derived groupings with AND/OR logic
   - ✅ Define domain modules in lens only
   - ✅ Implement explicit module triggers (list format with facet/value)

4. **Data Flow Integration**
   - ✅ Update extraction pipeline to use lens mapping
   - ✅ Build facet_to_dimension lookup from lens config
   - ✅ Initialize canonical_values_by_facet with empty lists for all lens facets
   - ✅ Distribute canonical values to dimensions by facet
   - ✅ Deduplicate dimension arrays (dedupe_preserve_order)
   - ✅ Apply lens module triggers (explicit list format)
   - ✅ Implement query layer with Prisma array filters
   - ✅ Transform entities using lens interpretation

5. **Migration Strategy**
   - ✅ Schema migration (rename table, add columns, create GIN indexes)
   - ✅ Data transformation (entityType → entity_class + canonical_roles)
   - ✅ Re-extraction with lens-aware pipeline
   - ✅ Validation (compare old vs new)

6. **Second Vertical Validation**
   - ✅ Create Wine Discovery lens (validates zero engine changes)
   - ✅ Different interpretation of same dimensions
   - ✅ Domain modules (wine_production) defined in lens only

### Nice-to-Have (Future Extensions)

7. **Advanced Query Features**
   - Complex multi-facet queries with AND/OR logic
   - Facet value counts for UI filters
   - Query optimization with EXPLAIN ANALYZE

8. **Lens Registry**
   - Multi-lens support (switch between verticals)
   - Lens inheritance (shared base lens)
   - Lens versioning

9. **UI Generation**
   - Auto-generate filter components from facet config
   - SEO page generation from templates
   - Navigation menu generation from derived groupings

## Success Criteria

### Engine Purity (100% Vertical-Agnostic)
1. ✅ Engine is 100% vertical-agnostic: Zero references to sports, wine, coach, venue, etc.
2. ✅ Domain modules in lens only: sports_facility, wine_production not in engine
3. ✅ Universal amenities only: cafe/restaurant/bar moved out of engine amenities module (only wifi, parking_available, disabled_access remain)
4. ✅ Opaque dimension values: Engine has zero interpretation logic
5. ✅ Module triggers in engine: Entity-class-based only (no value-based)
6. ✅ LensContract boundary: Engine never imports from lenses/, consumes LensContract only
7. ✅ Structural purity enforced: No literal string comparisons against dimension values in engine code
8. ✅ Allowed operations: Only entity_class branching, set operations, emptiness checks, pass-through
9. ✅ Classification priority correct: Time-bounded → event BEFORE physical location → place

### Database & Dimensions
10. ✅ Postgres text[] arrays for dimensions: Use `String[]` with GIN indexes, not Json
11. ✅ JSONB for modules: Use `Json` type for flexible module storage
12. ✅ Actual DB column names: All dimension_source use canonical_activities, canonical_roles, canonical_place_types, canonical_access
13. ✅ GIN indexes: Created on all dimension arrays for fast faceted filtering
14. ✅ Prisma array filters: Use has/hasSome/hasEvery on text[] arrays
15. ✅ Fixed dimension set: All future facets map onto existing four canonical_* dimensions (semantic overload accepted)

### Lens Layer
16. ✅ Explicit module triggers: List format with `when: {facet, value}` avoids collisions
17. ✅ Facet keys are lens-defined: `facet` refers to facet key as defined by the lens (lens.facets), NOT DB column name
18. ✅ Role facet (internal-only): Maps to canonical_roles, not shown in UI
19. ✅ Universal role keys: Stored as function-style keys (provides_facility, sells_goods, provides_instruction, membership_org, produces_goods)
20. ✅ Role display_name: Lens labels roles with vertical/product terminology via display_name
21. ✅ Module triggers in lens: Value-based triggers (explicit list format) in lens config
22. ✅ Derived grouping logic: AND within rule, OR across rules (DerivedGrouping.matches())

### Data Flow & Extraction
23. ✅ Dimension array deduplication: dedupe_preserve_order applied to canonical_values and all dimension arrays
24. ✅ canonical_values_by_facet initialization: Initialized with empty lists for all lens facets
25. ✅ Extraction builds facet_to_dimension: From lens.facets, maps facet key to DB column name
26. ✅ Extraction distributes values: By facet to correct dimension arrays
27. ✅ Extraction applies triggers: Using canonical_values_by_facet dict

### Module System
28. ✅ private_club in access facet: Moved from place_type to access
29. ✅ Inventory JSON structure: sports_facility uses inventory JSON, not per-activity fields
30. ✅ Module field collision relaxed: Duplicate field names allowed across different modules (namespacing makes this safe)
31. ✅ Module namespace enforcement: No flattened modules JSONB, no duplicate module keys

### Validation
32. ✅ Second vertical works: Wine Discovery lens loads successfully
33. ✅ Different interpretation: Same dimensions (Postgres text[] arrays), different lens interpretation
34. ✅ Zero engine changes: Adding wine vertical requires no engine code changes

## Non-Goals (Explicitly Out of Scope)

- ❌ **Multi-tenant lens switching**: Runtime lens selection (single lens per deployment for now)
- ❌ **Lens inheritance**: Shared base lens with vertical extensions (flat lens only for v1)
- ❌ **Auto-generated UI components**: Manual UI implementation (lens provides config only)
- ❌ **Migration of existing data**: Clean slate acceptable (can rebuild data)
- ❌ **Backward compatibility**: Breaking changes acceptable (major refactor)
- ❌ **TypeScript lens loader**: Python-only lens system (frontend uses API)

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ APPLICATION BOOTSTRAP                                            │
│ - Load lens from lenses/loader                                  │
│ - Produce LensContract (plain data object/dict)                 │
│ - Wire LensContract → Engine (one-way dependency)               │
└─────────────────────────────────────────────────────────────────┘
    ↓ LensContract
Raw Data Sources (Google Places, OSM, Serper, etc.)
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ EXTRACTION PIPELINE (Lens-Aware via LensContract)               │
│ 1. Collect raw categories from source                           │
│ 2. Map to canonical values using LensContract mapping rules     │
│ 3. Distribute values to dimensions by facet (using LensContract)│
│ 4. Deduplicate dimension arrays (dedupe_preserve_order)         │
│ 5. Resolve entity_class (deterministic engine rules)            │
│ 6. Compute required modules (engine + LensContract triggers)    │
│ 7. Extract module attributes                                     │
│ 8. Store entity with text[] arrays + JSONB modules              │
│ NOTE: Engine NEVER imports from lenses/, only uses LensContract │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ DATABASE (Postgres/Supabase)                                    │
│ Entity Model:                                                    │
│   - entity_class: String (place|person|organization|event|thing)│
│   - canonical_activities: String[] (text[], GIN indexed)        │
│   - canonical_roles: String[] (text[], GIN indexed)             │
│   - canonical_place_types: String[] (text[], GIN indexed)       │
│   - canonical_access: String[] (text[], GIN indexed)            │
│   - modules: Json (JSONB: {location: {...}, sports_facility})   │
│   - raw_categories: Json (JSONB: provenance)                    │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ QUERY LAYER (Prisma Array Filters)                              │
│ - hasSome (OR): entity has ANY of these activities              │
│ - hasEvery (AND): entity has ALL of these activities            │
│ - has: entity has this specific value                           │
│ - Complex queries: AND across facets (activity + place_type)    │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ LENS TRANSFORMATION (via LensContract)                          │
│ - Apply interpretation to opaque values                         │
│ - Compute derived groupings (entity_class + roles)              │
│ - Generate UI-ready entities with labels, icons, colors         │
│ - SEO page generation from templates                            │
└─────────────────────────────────────────────────────────────────┘
    ↓
Frontend (Next.js) - Display entities with rich metadata
```

### File Structure

```
engine/
├── config/
│   ├── entity_model.yaml          ← NEW: Universal entity classes, dimensions, universal modules
│   └── (canonical_categories.yaml removed)
│
├── extraction/
│   ├── base.py                    ← UPDATE: Lens-aware extraction with facet routing
│   ├── entity_classifier.py      ← NEW: Deterministic entity_class resolution
│   └── (existing extractors updated)
│
└── (NO domain modules in engine)

lenses/
├── loader.py                      ← NEW: Lens loader, produces LensContract (plain data object/dict)
├── edinburgh_finds/
│   └── lens.yaml                  ← NEW: Sports lens (facets, values, mapping, modules, triggers)
└── wine_discovery/
    └── lens.yaml                  ← NEW: Wine lens (validation)

web/
├── prisma/
│   └── schema.prisma              ← UPDATE: String[] for dimensions, Json for modules
├── lib/
│   └── lens-query.ts              ← NEW: Prisma array filter queries + lens transformations
└── (existing components updated)

migrations/
└── xxx_add_dimension_gin_indexes.sql  ← NEW: GIN indexes on dimension arrays
```

### Dimension Design

**Engine Dimensions (Postgres text[] arrays, GIN indexed):**
- `canonical_activities`: Activities provided/supported (e.g., ["padel", "tennis"])
- `canonical_roles`: Roles entity plays (e.g., ["provides_facility", "sells_goods"])
- `canonical_place_types`: Physical place classifications (e.g., ["sports_centre", "outdoor_facility"])
  - **NOTE**: place_type represents the container place classification (sports_centre, leisure_centre, park, gym_facility). Individual facilities (padel courts, tennis courts, pitches, pools, tracks) belong in domain modules (e.g. sports_facility.inventory), NOT as place_type values. A pitch, court, pool, or rink is NOT a place_type.
- `canonical_access`: Access requirements (e.g., ["membership", "pay_and_play"])

**Key Properties:**
- Stored as Postgres text[] arrays (String[] in Prisma)
- Default to empty arrays: `@default([])`
- GIN indexed for fast faceted filtering
- Opaque values (engine performs zero interpretation)
- Multi-valued (0..N cardinality)

### LensContract Design

**Purpose**: Decouple engine from lens layer with a strict contract boundary.

**Contract Properties:**
- **Plain data object/dict**: No class instances, no lens-specific types
- **Produced by**: `lenses/loader.py` (loads and validates lens.yaml)
- **Consumed by**: Engine extraction pipeline and query transformations
- **One-way dependency**: Engine → LensContract (engine NEVER imports from lenses/)
- **Wired at bootstrap**: Application startup loads lens and passes contract to engine

**LensContract Structure (Plain Dict):**
```python
{
  "facets": {
    "activity": {
      "dimension_source": "canonical_activities",
      "ui_label": "What do you want to do?",
      "display_mode": "multi_select",
      "order": 10
    },
    # ... other facets
  },
  "values": [
    # NOTE: values stored as list in contract
    # Engine builds values_by_key index for efficient lookups: {key: value_obj}
    {
      "key": "padel",
      "facet": "activity",
      "display_name": "Padel",
      "seo_slug": "padel-edinburgh",
      "icon_url": "/icons/padel.svg",
      "color": "#FF6B35"
    },
    # ... other values
  ],
  "mapping_rules": [
    {
      "pattern": r'(?i)\bp[aá]d[eé]l\b',
      "canonical": "padel",
      "confidence": 1.0
    },
    # ... other rules
  ],
  "module_triggers": [
    {
      "when": {"facet": "activity", "value": "padel"},
      "add_modules": ["sports_facility"],
      "conditions": [{"entity_class": "place"}]
    },
    # ... other triggers
  ],
  "derived_groupings": [...],
  "modules": {...}
}
```

**Import Boundary Enforcement:**
- ❌ Engine code imports from `lenses/`: FORBIDDEN
- ✅ Engine code receives LensContract dict: ALLOWED
- ✅ Bootstrap code imports from `lenses/loader`: ALLOWED (wiring layer)
- ✅ Lens transformation code imports from `lenses/`: ALLOWED (outside engine)

### Lens Configuration Structure

**lens.yaml Structure:**
```yaml
lens:
  id: edinburgh_finds
  name: "Edinburgh Finds"
  description: "Sports and fitness directory for Edinburgh"

facets:
  activity:
    dimension_source: "canonical_activities"  # Actual DB column name
    ui_label: "What do you want to do?"
    display_mode: "multi_select"
    order: 10

  role:
    dimension_source: "canonical_roles"
    ui_label: null  # Internal-only, not shown in UI
    display_mode: "internal"

values:
  - key: padel
    facet: activity
    display_name: "Padel"
    seo_slug: "padel-edinburgh"
    icon_url: "/icons/padel.svg"
    color: "#FF6B35"

  - key: provides_facility
    facet: role
    display_name: "Venue"  # Vertical-specific label (display only, NOT a structural concept)
    description: "Physical facility providing activities"

mapping_rules:
  - pattern: '(?i)\bp[aá]d[eé]l\b'
    canonical: padel
    confidence: 1.0

derived_groupings:
  - id: places
    label: "Places"
    rules:
      - entity_class: "place"

  - id: people
    label: "Coaches & Instructors"
    rules:
      - entity_class: "person"
        roles: ["provides_instruction"]  # AND logic

modules:
  sports_facility:
    description: "Sports-specific facility attributes with inventory structure"
    fields:
      - name: inventory
        type: json
        description: "Per-activity court/facility inventory"

module_triggers:
  - when:
      facet: activity  # Lens-defined facet key (NOT dimension_source)
      value: padel
    add_modules: ["sports_facility"]
    conditions:
      - entity_class: "place"

# NOTE on naming:
# - facet in module_triggers = lens facet key (activity, role, place_type)
# - dimension_source in facet definition = actual DB column (canonical_activities, canonical_roles, etc.)
# - Example: facet='activity' maps to dimension_source='canonical_activities'
```

### Classification Priority Examples

**Priority Order (Corrected):**
1. Time-bounded (event) → FIRST PRIORITY
2. Physical location (place)
3. Membership/group (organization)
4. Named individual (person)

**Examples:**
- **Padel tournament at Oriam** (has start/end times + physical location)
  - ✅ Classified as: `event` (time-bounded takes priority)
  - ❌ NOT: `place` (despite having physical location)

- **Weekly drop-in session** (recurring time slot + location)
  - ✅ Classified as: `event` (time-bounded takes priority)
  - ❌ NOT: `place`

- **Oriam Sports Centre** (physical location, no specific time bounds)
  - ✅ Classified as: `place`

- **Edinburgh Padel Club** (membership org, no fixed location)
  - ✅ Classified as: `organization`

- **John Smith, Padel Coach** (named individual)
  - ✅ Classified as: `person`

### Structural Purity Examples

**Engine Code Rules (FORBIDDEN vs ALLOWED):**

**❌ FORBIDDEN - Literal string comparisons:**
```python
# WRONG: Engine code branching on dimension values
if "padel" in entity.canonical_activities:
    add_module("sports_facility")

# WRONG: String matching on dimension values
if entity.canonical_place_types[0] == "sports_centre":
    do_something()
```

**✅ ALLOWED - Entity class branching:**
```python
# CORRECT: Branching on entity_class
if entity.entity_class == "place":
    add_module("location")

# CORRECT: Branching on entity_class
if entity.entity_class == "event":
    add_module("event_details")
```

**✅ ALLOWED - Set/collection operations:**
```python
# CORRECT: Union of opaque strings
all_values = set(entity.canonical_activities) | set(entity.canonical_roles)

# CORRECT: Intersection of opaque strings
common_values = set(facet_a_values) & set(facet_b_values)

# CORRECT: Membership test (opaque operation)
has_values = bool(set(required_values) & set(entity.canonical_activities))
```

**✅ ALLOWED - Emptiness checks:**
```python
# CORRECT: Checking if dimension is empty
if entity.canonical_activities:
    # has activities

# CORRECT: Checking if dimension is empty
if not entity.canonical_roles:
    # no roles assigned
```

**✅ ALLOWED - Pass-through unchanged:**
```python
# CORRECT: Passing opaque values to database
db.store(
    canonical_activities=entity.canonical_activities,
    canonical_roles=entity.canonical_roles
)

# CORRECT: Passing to lens transformation layer for interpretation
# Engine passes opaque values to lens layer (outside engine)
# Lens layer (not engine) interprets values using lens_contract dict
transform_with_lens(entity, lens_contract)
```

**Structural Purity Tests (CI/CD):**
- Static analysis: Grep engine code for string literals in dimension comparisons
- AST parsing: Detect `if "literal" in canonical_*` patterns
- Code review: Flag any dimension value branching in engine PRs
- Unit tests: Verify engine functions only branch on entity_class

## Benefits

### For Engine Purity
- ✅ **Zero vertical coupling**: Engine has no knowledge of sports, wine, etc.
- ✅ **Domain modules isolated**: sports_facility, wine_production in lens only
- ✅ **Opaque values**: Engine stores strings with zero interpretation
- ✅ **Universal modules**: Only core, location, contact, hours in engine

### For Performance
- ✅ **GIN indexes**: Fast faceted filtering on text[] arrays
- ✅ **Prisma array filters**: Native has/hasSome/hasEvery operators
- ✅ **Query optimization**: Postgres array operators (&& and @>)
- ✅ **Reduced JSONB parsing**: Dimensions as native arrays

### For Horizontal Scaling
- ✅ **Zero engine changes**: Add wine vertical with lens.yaml only
- ✅ **Reuse dimensions**: canonical_activities for both sports and wine
- ✅ **Different interpretation**: Same data, different lens views
- ✅ **Isolated domain logic**: Domain modules (wine_production) in lens

### For Development
- ✅ **Clear boundaries**: Engine vs lens separation
- ✅ **Explicit triggers**: List format avoids key collisions
- ✅ **Facet system**: Structured navigation/filtering/SEO
- ✅ **Role facet**: Internal-only facets supported

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration breaks existing data | High | Clean slate acceptable, can rebuild data |
| GIN index performance on large datasets | Medium | Test with production-scale data, monitor query performance |
| Lens configuration too complex | Medium | Start simple, validate with wine lens, document patterns |
| Module trigger facet key confusion | Medium | Clear documentation, examples, validation in lens loader |
| Deduplication changes extraction output | Low | Test with existing extraction examples, validate determinism |
| Role facet implementation complexity | Medium | Start with simple role values, expand as needed |
| LensContract import boundary violated | High | Static analysis, import linting, code review enforcement |
| Structural purity rules bypassed | High | AST-based CI checks, grep for forbidden patterns, unit tests |
| Classification priority errors (event vs place) | Medium | Unit tests with time-bounded + location entities, clear examples |
| Module field collision confusion | Low | Clear documentation, validation in lens loader |
| Dimension set expansion temptation | Medium | Explicit rule: semantic overload accepted, no new dimensions |

## Dependencies

- **Requires**:
  - Current entity model (Listing, entityType)
  - Existing extraction pipeline
  - Prisma schema
- **Blocks**: None (foundational refactor)
- **Enables**:
  - Wine Discovery vertical
  - Additional verticals (restaurants, gyms, etc.)
  - Advanced faceted navigation
  - SEO page generation from templates

## Timeline Estimate

- **Phase 1** (Engine Core Design): 4-6 hours
- **Phase 2** (Lens Layer Design): 6-8 hours
- **Phase 3** (Data Flow Integration): 8-10 hours
- **Phase 4** (Migration Strategy): 4-6 hours
- **Phase 5** (Second Vertical Validation): 2-3 hours

**Total**: 24-33 hours of focused work

## Related Documentation

- Current schema: `web/prisma/schema.prisma`
- Current extraction: `engine/extraction/base.py`
- Entity model: `engine/schema/types.py`
- Architecture: `ARCHITECTURE.md`
