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

### Decision 1: Lens Injection Pattern

**Problem:** How does VerticalLens configuration reach extractors during extraction?

**Options:**
- A. Orchestration context carries lens_id → extractor loads lens
- B. LensRegistry.get_lens("edinburgh_finds") called during extract_entity()
- C. Lens config passed through orchestration ExecutionContext
- D. Global context (threading local or dependency injection container)

**Decision Needed:** Choose injection pattern and document interface

**Impact:** All extractors and orchestration code depends on this

---

### Decision 2: Complete Edinburgh Finds Lens Specification

**Problem:** `lens.yaml` doesn't exist, extractors have nothing to consume

**Required Sections:**

**2.1 Query Vocabulary**
```yaml
vocabulary:
  activity_keywords:
    - padel
    - tennis
    - football
    - swimming
    - gym
    - yoga
    # ... all Edinburgh activities

  location_indicators:
    - edinburgh
    - portobello
    - leith
    - morningside
    # ... all Edinburgh areas

  facility_keywords:
    - centre
    - club
    - pitch
    - court
    - pool
    - venue
```

**2.2 Connector Routing Rules**
```yaml
connector_rules:
  google_places:
    priority: high
    triggers:
      - type: always
    budget_limit: 100

  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [football, tennis, padel, swimming]

  # ... rules for all 6 connectors
```

**2.3 Mapping Rules**
```yaml
mapping_rules:
  # Activities
  - pattern: "(?i)padel|pádel"
    dimension: canonical_activities
    value: padel
    confidence: 0.98

  - pattern: "(?i)football|5.?a.?side|7.?a.?side"
    dimension: canonical_activities
    value: football
    confidence: 0.95

  # Place Types
  - pattern: "(?i)sports? centre|multi.?sport"
    dimension: canonical_place_types
    value: sports_centre
    confidence: 0.95

  # Roles
  - pattern: "(?i)facility|venue|centre"
    dimension: canonical_roles
    value: provides_facility
    confidence: 0.90

  # Access
  - pattern: "(?i)pay.?and.?play|casual"
    dimension: canonical_access
    value: pay_and_play
    confidence: 0.90

  # ... comprehensive mapping rules
```

**2.4 Module Definitions**
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
          seven_a_side:
            type: object
            # ...

      padel_courts:
        type: object
        fields:
          total: integer
          indoor: integer
          outdoor: integer

      # ... all facility types
```

**2.5 Module Triggers**
```yaml
module_triggers:
  - when:
      dimension: canonical_activities
      values: [football, padel, tennis, squash]
    add_modules: [sports_facility]
    conditions:
      - entity_class: place
```

**2.6 Canonical Value Metadata**
```yaml
canonical_values:
  padel:
    display_name: "Padel"
    display_name_plural: "Padel"
    seo_slug: "padel"
    icon: "padel-racquet"
    description: "Padel courts and facilities"
    search_keywords: [padel, pádel]

  football:
    display_name: "Football"
    display_name_plural: "Football"
    seo_slug: "football"
    icon: "football"
    description: "Football pitches and venues"
    search_keywords: [football, soccer, 5-a-side, 7-a-side]

  # ... all canonical values
```

**Decision Needed:** Author complete lens.yaml with real Edinburgh Finds data

**Impact:** Everything else consumes this specification

---

### Decision 3: Module Field Extraction Algorithm

**Problem:** How do we populate module fields from raw source data?

**Current State:**
```python
# extract_with_lens_contract() - line ~180 in base.py
for module_name in required_modules:
    module_def = modules_config.get(module_name, {})
    modules_data[module_name] = {}  # ← Empty! No extraction logic
```

**Need to Design:**
1. How to map raw_data fields to module structure
2. How to handle nested module fields (football_pitches.five_a_side.total)
3. How to handle source-specific field names (Google vs Sport Scotland)
4. How to handle missing/null fields gracefully
5. What confidence scores to assign to extracted module fields

**Example Design Question:**
Raw Google Places data: `{"types": ["sports_complex", "point_of_interest"], "formatted_address": "..."}`
Sport Scotland WFS data: `{"FacilityType": "Football Pitches", "NumPitches": 4, "Surface": "3G"}`

How should we extract:
```json
{
  "sports_facility": {
    "football_pitches": {
      "five_a_side": {
        "total": 4,
        "surface": ["3G"]
      }
    }
  }
}
```

**Decision Needed:**
- Design extraction rule format (declarative YAML? imperative Python?)
- Define module field binding strategy
- Document extraction confidence scoring

**Impact:** Determines richness of extracted facility data

---

### Decision 4: Field Name Reconciliation

**Problem:** Field name mismatch between extraction output and Entity schema

**Current Mismatches:**

| Extractor Output | EntityFinalizer Expects | Entity Schema |
|------------------|------------------------|---------------|
| `entity_name` | `name` | `entity_name` |
| `latitude` | `location_lat` | `latitude` |
| `longitude` | `location_lng` | `longitude` |
| `street_address` | `address_full` | `street_address` |
| `phone` | `contact_phone` | `phone` |
| `email` | `contact_email` | `email` |
| `website_url` | `contact_website` | `website_url` |

**Options:**
- A. Change extractors to match EntityFinalizer expectations
- B. Change EntityFinalizer to match extractor output
- C. Create field mapping layer between extraction and finalization
- D. Align both to Entity schema as canonical names

**Decision Needed:** Choose canonical field names throughout pipeline

**Impact:** All extractors and EntityFinalizer need updates

---

### Decision 5: Multi-Source Merge Algorithm

**Problem:** When Google Places and Sport Scotland both return "Powerleague Portobello", how do we merge?

**Design Requirements:**

**5.1 Trust Hierarchy**
```yaml
# Connector trust levels
sport_scotland:
  trust_level: official
  priority: 1

edinburgh_leisure_api:
  trust_level: official
  priority: 1

google_places:
  trust_level: crowdsourced
  priority: 2

serper:
  trust_level: crowdsourced
  priority: 3
```

**5.2 Field-Level Conflict Resolution**

Example conflict:
- **Google Places:** `phone: "+441316696000"`, `website: "https://powerleague.co.uk"`
- **Sport Scotland:** `phone: null`, `website: "https://www.powerleague.co.uk/venues/portobello"`

Resolution strategy:
- Universal fields (name, address): Higher trust wins
- Contact fields: Most complete + higher trust wins
- Module fields: Official sources only (ignore crowdsourced for facility counts)
- Canonical dimensions: Union of all sources (merge arrays, deduplicate)

**5.3 Merge Algorithm**
```python
def merge_entities(entities: List[ExtractedEntity]) -> ExtractedEntity:
    """
    Merge multiple extracted entities into single canonical entity

    Rules:
    1. Sort by trust level (official > verified > crowdsourced)
    2. For each field:
       - If only one source has value, use it
       - If multiple sources, use highest trust
       - If same trust, use most complete (longest string, most array elements)
       - If tie, use alphabetically first source name
    3. canonical_* dimensions: Union all values, deduplicate
    4. modules: Deep merge with trust-based field selection
    """
```

**Decision Needed:**
- Document complete merge algorithm
- Define trust level assignment per connector
- Define field-by-field merge strategy
- Define conflict resolution tie-breakers

**Impact:** Determines accuracy and completeness of final entities

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
1. Write `edinburgh_finds/query_vocabulary.yaml` (activities, locations, facilities)
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
1. Write `edinburgh_finds/connector_rules.yaml` (routing rules for 6 connectors)
2. Test: Orchestration selects correct connectors for "Powerleague Portobello"
   - Expected: Google Places (always), Sport Scotland (football keyword), OSM (location)
   - Not Expected: Open Charge Map (no EV charging query)

**Quality Gates:**
- ✅ Connector selection driven by lens rules, not hardcoded
- ✅ All 6 connectors have routing rules
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
**Scope:** Populate module fields from raw data
**Dependencies:** Phase 7 (modules attached), Phase 0 (module extraction design)

**Objective:** Prove sports_facility module populated with facility inventory

**Implementation:**
1. Implement extract_module_fields(raw_data, module_def) function
2. Extract facility-specific data (court counts, surfaces, equipment)
3. Handle source-specific field names (Google vs Sport Scotland)
4. Populate nested module structure

**Test Case - Powerleague Portobello:**
```
Input (Google Places):
  raw_data: {...types, name, formatted_address...}

Input (Sport Scotland WFS):
  raw_data: {
    "FacilityType": "Football Pitches",
    "NumPitches": 6,
    "Surface": "3G Artificial",
    "Indoor": 0,
    "Outdoor": 6
  }

Output:
  modules: {
    "sports_facility": {
      "football_pitches": {
        "five_a_side": {
          "total": 6,
          "indoor": 0,
          "outdoor": 6,
          "surface": ["3G"]
        }
      },
      "padel_courts": {
        "total": 4,
        "indoor": 4
      }
    }
  }
```

**Quality Gates:**
- ✅ Module fields populated with actual data (not empty)
- ✅ Nested structure preserved (football_pitches.five_a_side.total)
- ✅ Source-specific extraction rules handled
- ✅ Null/missing fields handled gracefully
- ✅ ModuleValidator passes (structure correct)

**Deliverable:** Rich facility data in modules JSONB

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
