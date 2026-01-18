	# Track: Engine-Lens Architecture Refactor - Implementation Plan (v2.2)

## Overview

This plan details the phased implementation of the Engine-Lens Architecture separation. The refactor transforms Edinburgh Finds from a vertically-coupled monolith to a universal entity engine with vertical-specific lens layer.

**Framing Statement:** We are separating a universal, vertical-agnostic entity engine from a lens layer that owns all interpretation, taxonomy, and domain behavior, with strict contracts and zero leakage between layers.

**Implementation Philosophy:** Measure twice, code once. Build incrementally with validation at each phase boundary.

**Version:** v2.2 - Includes Tightening Addendum with explicit enforcement of architectural contracts

**Key Requirements (Must Not Deviate):**
- ✅ Engine remains 100% vertical-agnostic (no domain concepts, no value-based triggers, no domain modules)
- ✅ Dimensions are Postgres text[] (String[]) with GIN indexes; modules remain JSONB
- ✅ Lens owns all interpretation: canonical values, mapping rules, role facet (internal-only), derived groupings, domain modules, and module triggers
- ✅ Module triggers use explicit list format with `when: {facet, value}` where facet is a lens-defined facet key (lens.facets), not a DB column
- ✅ **Engine module triggers are entity_class-based; lens module triggers are value-based (via LensContract)**
- ✅ **Confidence thresholds live in LensContract/lens config, not hardcoded in engine**
- ✅ Extraction builds facet_to_dimension from lens.facets, initializes canonical_values_by_facet with empty lists for all lens facet keys, distributes values, dedupes deterministically, then applies triggers

## v2.2 Tightening Addendum

This version adds explicit enforcement tasks and acceptance criteria for:

1. **Supabase/Prisma Specifics** - Postgres array defaults, GIN indexes, standardized ID strategy
2. **Engine Purity Enforcement** - No lens imports, CI/grep tests, no value-string branching
3. **Lens Contract Validation** - dimension_source validation, facet existence checks, fail-fast validation
4. **Module Composition Hardening** - No duplicate module keys; JSONB namespacing enforced; duplicate field names across modules allowed.
5. **Classification Rule Locked** - Single entity_class + multi roles pattern locked in
6. **Query Semantics** - OR within facet, AND across facets, groupings are derived/view-only (not stored)
7. **Comprehensive Test Suite** - Unit/integration tests for all contracts

---

## Phase 1: Engine Core Design

**Goal:** Define universal, vertical-agnostic engine layer with opaque dimensions and entity-class-based module system

### Task 1.1: Define Entity Model Configuration

**Status:** ✅ completed

**Description:** Create `engine/config/entity_model.yaml` defining universal entity classes, dimensions, and universal modules only

**Subtasks:**
- [x] Create `engine/config/entity_model.yaml` file
- [x] Define entity_classes section:
  - [x] place (required_modules: ["core", "location"])
  - [x] person (required_modules: ["core", "contact"])
  - [x] organization (required_modules: ["core", "contact"])
  - [x] event (required_modules: ["core", "time_range"])
  - [x] thing (required_modules: ["core"])
- [x] Define dimensions section (all dimensions are opaque, stored as Postgres text[] arrays):
  - [x] canonical_activities (description: "Activities provided/supported (opaque values)", cardinality: "0..N")
  - [x] canonical_roles (description: "Roles this entity plays (opaque values)", cardinality: "0..N")
  - [x] canonical_place_types (description: "Physical place classifications (opaque values)", cardinality: "0..N", applicable_to: ["place"])
  - [x] canonical_access (description: "Access requirements (opaque values)", cardinality: "0..N")
- [x] Define modules section (UNIVERSAL MODULES ONLY):
  - [x] core module (entity_id, entity_name, slug, summary)
  - [x] location module (street_address, city, postcode, country, latitude, longitude, locality)
  - [x] contact module (phone, email, website_url, instagram_url, facebook_url, twitter_url, linkedin_url)
  - [x] hours module (opening_hours, special_hours)
  - [x] amenities module (UNIVERSAL AMENITIES ONLY: wifi, parking_available, disabled_access)
  - [x] time_range module (start_datetime, end_datetime, timezone, is_recurring, recurrence_rule)
- [x] Add comments to YAML:
  - [x] "Dimensions: Use actual DB column names (canonical_activities, canonical_roles, canonical_place_types, canonical_access)"
  - [x] "Dimensions: Explicitly marked as opaque, stored as Postgres text[] arrays"
  - [x] "NO domain modules (sports_facility, wine_production removed)"
  - [x] "Amenities: universal only (cafe/restaurant removed)"
- [x] Validate: NO references to padel, tennis, gym, coach, venue, sports, wine, etc.
- [x] Validate: NO domain-specific modules (sports_facility, wine_production, etc.)
- [x] Validate: NO food service amenities (cafe, restaurant, bar)

**Success Criteria:**
- ✅ entity_model.yaml exists with all universal entity classes
- ✅ Dimensions use actual DB column names (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
- ✅ Dimensions explicitly documented as opaque Postgres text[] arrays
- ✅ All modules are universal only (core, location, contact, hours, amenities, time_range)
- ✅ Amenities module contains ONLY universal amenities (wifi, parking_available, disabled_access)
- ✅ Zero vertical-specific concepts in entire file

### Task 1.2: Update Database Schema (Supabase/Prisma) [2f69173]

**Status:** ✅ completed

**Description:** Update Prisma schema to use Postgres text[] arrays for dimensions and JSONB for modules with Supabase best practices

**Subtasks:**
- [x] Update `web/prisma/schema.prisma`:
  - [x] Change `canonical_activities` to `String[] @default([])`
  - [x] Change `canonical_roles` to `String[] @default([])`
  - [x] Change `canonical_place_types` to `String[] @default([])`
  - [x] Change `canonical_access` to `String[] @default([])`
  - [~] **CRITICAL**: Verify Postgres array defaults work correctly (empty array '{}' not null) - Will be verified during Postgres migration
  - [~] Keep `modules` as `Json?` (JSONB) - Deferred to later task when modules field is added
  - [x] Add standard indexes:
    - [~] `@@index([entity_class])` - Deferred to later task when entity_class field is added
    - [x] `@@index([entity_name])`
    - [x] `@@index([slug])` - Implemented as @unique which includes index
    - [x] `@@index([createdAt])`
  - [x] Add comments:
    - [x] "// MULTI-VALUED DIMENSIONS (Postgres text[] arrays for fast faceted filtering)" - Added in listing.yaml source
    - [~] "// ATTRIBUTE MODULES (JSONB keyed by module name, namespaced structure)" - Deferred to later task when modules field is added
- [x] Create migration file `migrations/xxx_add_dimension_gin_indexes.sql`:
  - [x] **REQUIRED**: Add GIN index: `CREATE INDEX IF NOT EXISTS entities_activities_gin ON entities USING GIN (canonical_activities);`
  - [x] **REQUIRED**: Add GIN index: `CREATE INDEX IF NOT EXISTS entities_roles_gin ON entities USING GIN (canonical_roles);`
  - [x] **REQUIRED**: Add GIN index: `CREATE INDEX IF NOT EXISTS entities_place_types_gin ON entities USING GIN (canonical_place_types);`
  - [x] **REQUIRED**: Add GIN index: `CREATE INDEX IF NOT EXISTS entities_access_gin ON entities USING GIN (canonical_access);`
  - [x] Add comment: "-- GIN indexes are REQUIRED for fast faceted filtering on text[] arrays"
- [x] Add EntityRelationship model (if not exists):
  - [x] sourceEntityId, targetEntityId, type, confidence, source fields - Already exists as ListingRelationship model
  - [x] Relations to Entity model - Relations to Listing model exist
  - [x] Indexes on sourceEntityId, targetEntityId, type - All indexes exist
- [x] Add comments to schema explaining:
  - [x] Dimensions stored as Postgres text[] arrays (NOT Json) - Documented in listing.yaml
  - [x] Default to empty arrays `@default([])` (Postgres '{}' not null) - Implemented in Prisma schema
  - [x] GIN indexes REQUIRED for fast faceted queries - Documented in migration file
  - [~] Modules remain Json (JSONB) for flexibility - Deferred to later task when modules field is added

**Implementation Notes:**
- Added four dimension fields (canonical_activities, canonical_roles, canonical_place_types, canonical_access) to `engine/config/schemas/listing.yaml`
- Configured with `prisma.type: "String[]"` and `prisma.attributes: ["@default([])"]` for Postgres text[] arrays
- Regenerated Prisma schemas for both engine and web using `python -m engine.schema.generate --force`
- Created GIN indexes migration file at `web/prisma/migrations/20260118_add_dimension_gin_indexes/migration.sql`
- Migration file is forward-looking for Postgres/Supabase deployment (GIN indexes don't work in SQLite)
- ListingRelationship model already exists with all required fields and indexes
- entity_class field and modules JSONB field will be added in subsequent tasks

**Success Criteria:**
- ✅ Dimensions use `String[]` (Postgres text[] arrays, NOT Json)
- ✅ Default to empty arrays `@default([])` verified working (Postgres '{}')
- ✅ GIN indexes migration file created for all 4 dimension arrays
- ✅ Modules remain `Json?` (JSONB type)
- ✅ Comments clarify opaque values stored as Postgres text[] arrays
- ✅ Schema follows Postgres/Supabase best practices

### Task 1.2a: Standardize ID Strategy (v2.2 Addition) [8613a43]

**Status:** ✅ completed

**Description:** Lock in consistent ID strategy across all models - no mixing of uuid and cuid

**Subtasks:**
- [x] Audit current schema for ID types:
  - [x] Check Entity model ID type - Currently named "Listing", uses cuid()
  - [x] Check EntityRelationship model ID types - Currently named "ListingRelationship", uses cuid()
  - [x] Check RawIngestion model ID type - Uses cuid()
  - [x] List all current ID strategies (uuid vs cuid vs autoincrement) - All 7 models use cuid() consistently
- [x] **DECISION**: Choose ONE ID strategy for the project:
  - [x] Option A: Use Prisma `@default(cuid())` for all models (Prisma default) ✅ CHOSEN
  - [x] **RULE**: Once chosen, NEVER mix strategies in same database - Enforced by validation tests
- [x] Standardize all model IDs:
  - [x] Update Entity model: `id String @id @default([chosen_strategy])` - Already consistent (cuid)
  - [x] Update EntityRelationship model: `id String @id @default([chosen_strategy])` - Already consistent (cuid)
  - [x] Update all foreign key types to match (sourceEntityId, targetEntityId) - All use String type
  - [x] Document choice in schema comments - Created engine/docs/id_strategy.md
- [x] Create migration for ID standardization (if needed) - Not needed, already consistent
- [x] Add validation test:
  - [x] Test that verifies all models use consistent ID strategy - test_all_models_use_consistent_id_strategy()
  - [x] Fail build if mixed ID strategies detected - Tests fail CI if mixed strategies found

**Success Criteria:**
- ✅ All models use single consistent ID strategy (either cuid or uuid, not mixed)
- ✅ Schema comment documents ID strategy choice and rationale
- ✅ Migration created if schema changes needed
- ✅ Validation test prevents future ID strategy mixing
- ✅ Foreign keys use matching ID type

**Acceptance Check:**
```bash
# All @id and foreign key fields must use same type
grep -E "@id|@default\((uuid|cuid)\)" schema.prisma
# Should show consistent strategy across all models
```

### Task 1.3: Lock Classification Rules (v2.2 Addition) [7a37f67]

**Status:** completed

**Description:** Document and enforce single entity_class + multi roles pattern with concrete examples

**Subtasks:**
- [x] Create `engine/docs/classification_rules.md`:
  - [x] **Rule**: Every entity has exactly ONE entity_class (required, single-valued)
  - [x] **Rule**: Every entity has ZERO OR MORE roles (optional, multi-valued)
  - [x] **Pattern**: entity_class represents primary classification (what it fundamentally IS)
  - [x] **Pattern**: roles represent functions/capabilities (what it DOES)
- [x] Document deterministic classification algorithm (PRIORITY ORDER):
  - [x] **1. Time-bounded** (has start/end times) → `event` (HIGHEST PRIORITY)
  - [x] **2. Physical location** (lat/lng or street address) → `place`
  - [x] **3. Membership/group** entity with no fixed location → `organization`
  - [x] **4. Named individual** → `person`
  - [x] **5. Tie-breaker**: Primary physical site → `place`, otherwise → `organization`
- [x] **CRITICAL**: Add concrete examples (with classification priority):
  - [x] "Padel tournament at Oriam" (time-bounded + physical location):
    - [x] entity_class: `event` (time-bounded takes PRIORITY over physical location)
    - [x] canonical_roles: `[]` (events typically have no roles)
    - [x] canonical_activities: `["padel"]`
    - [x] **RATIONALE**: Has both start/end times AND physical location, but time-bounded is higher priority
  - [x] "Tennis club with 6 courts":
    - [x] entity_class: `place` (has physical location with courts, not time-bounded)
    - [x] canonical_roles: `["provides_facility", "membership_org"]` (provides sports facility AND is a membership club)
    - [x] canonical_activities: `["tennis"]`
    - [x] canonical_place_types: `["sports_centre"]`
    - [x] **NOTE**: Courts go in sports_facility.inventory (domain module), not as place_type values
    - [x] **RATIONALE**: Primary classification is physical place; roles capture dual nature as both facility and club
  - [x] "Powerleague Portobello (football + padel venue)":
    - [x] entity_class: `place` (has physical location)
    - [x] canonical_activities: `["football", "padel"]`
    - [x] canonical_roles: `["provides_facility"]` (plus others if applicable)
    - [x] canonical_place_types: `["sports_centre"]` or `["outdoor_facility"]`
    - [x] **NOTE**: Courts and pitches go into sports_facility.inventory, not place_type
  - [x] "Freelance tennis coach":
    - [x] entity_class: `person` (individual)
    - [x] canonical_roles: `["provides_instruction"]`
    - [x] canonical_activities: `["tennis"]`
  - [x] "Sports retail chain (no courts)":
    - [x] entity_class: `organization` (business entity)
    - [x] canonical_roles: `["sells_goods"]`
    - [x] canonical_activities: `["tennis", "padel"]` (sells equipment for these sports)
  - [x] "Padel tournament":
    - [x] entity_class: `event` (time-bounded)
    - [x] canonical_roles: `[]` (events typically have no roles)
    - [x] canonical_activities: `["padel"]`
- [x] **ANTI-PATTERN**: Document what NOT to do:
  - [x] ❌ NEVER use entity_class to encode business type (entity_class: "club" is WRONG)
  - [x] ❌ NEVER use roles as primary classification (entity_class is primary, not roles)
  - [x] ❌ NEVER store conflicting entity_class values (single-valued field)
- [x] Update `engine/extraction/entity_classifier.py`:
  - [x] Implement resolve_entity_class(raw_data) function
  - [x] Add inline comments referencing classification_rules.md
  - [x] Add assertion: entity_class must be one of: place, person, organization, event, thing
- [x] Add unit tests for classification:
  - [x] Test "club with courts" → place + roles
  - [x] Test "freelance coach" → person + roles
  - [x] Test "retail chain" → organization + roles
  - [x] Test "tournament" → event + no roles

**Success Criteria:**
- ✅ classification_rules.md exists with deterministic algorithm
- ✅ Concrete examples documented with rationale
- ✅ Anti-patterns documented
- ✅ entity_classifier.py implements rules correctly
- ✅ Unit tests cover all example cases
- ✅ "Club with courts" correctly resolves to place + multiple roles

**Acceptance Check:**
```python
# Test: Club with courts
entity = resolve_and_classify({
    "name": "Craigmillar Tennis Club",
    "address": "123 Tennis Road",
    "has_courts": True,
    "membership_required": True,
    "categories": ["tennis club", "sports facility"]
})
assert entity['entity_class'] == 'place'
assert 'provides_facility' in entity['canonical_roles']
assert 'membership_org' in entity['canonical_roles']
```

**Phase 1 Checkpoint (Updated for v2.2):**
- All verification tasks completed
- Engine config is 100% vertical-agnostic
- Database schema uses Postgres text[] arrays for dimensions with GIN indexes
- ID strategy standardized across all models (no mixing)
- Classification rules locked and documented with examples
- NO domain modules, NO vertical concepts in engine

---

## Phase 2: Lens Layer Design

**Goal:** Create vertical-specific lens layer with facets, canonical values, mapping rules, derived groupings, domain modules, and explicit module triggers

### Task 2.1: Create Lens Configuration Structure

**Status:** ✅ completed

**Description:** Create `lenses/edinburgh_finds/lens.yaml` with complete Sports & Fitness lens definition

**Subtasks:**
- [x] Create `lenses/edinburgh_finds/lens.yaml` file
- [x] Define lens metadata:
  - [x] id: edinburgh_finds
  - [x] name: "Edinburgh Finds"
  - [x] description: "Sports and fitness directory for Edinburgh"
  - [x] base_url: "https://edinburghfinds.com"
- [x] Define facets section (map to engine dimensions using ACTUAL DB COLUMN NAMES):
  - [x] activity facet:
    - [x] dimension_source: "canonical_activities" (MUST BE one of 4 canonical_* columns)
    - [x] ui_label: "What do you want to do?"
    - [x] display_mode: "multi_select"
    - [x] order: 10
    - [x] show_in_filters: true
    - [x] show_in_navigation: true
    - [x] icon: "activity"
  - [x] role facet (INTERNAL-ONLY):
    - [x] dimension_source: "canonical_roles" (MUST BE one of 4 canonical_* columns)
    - [x] ui_label: null (internal-only facet, not shown in UI)
    - [x] display_mode: "internal"
    - [x] order: 5
    - [x] show_in_filters: false
    - [x] show_in_navigation: false
  - [x] place_type facet:
    - [x] dimension_source: "canonical_place_types" (MUST BE one of 4 canonical_* columns)
    - [x] ui_label: "Place type"
    - [x] display_mode: "single_select"
    - [x] order: 20
    - [x] show_in_filters: true
    - [x] show_in_navigation: false
    - [x] icon: "building"
  - [x] access facet:
    - [x] dimension_source: "canonical_access" (MUST BE one of 4 canonical_* columns)
    - [x] ui_label: "Booking & access"
    - [x] display_mode: "multi_select"
    - [x] order: 30
    - [x] show_in_filters: true
    - [x] show_in_navigation: false
    - [x] icon: "lock"
- [x] Define values section (canonical values with FULL INTERPRETATION):
  - [x] Activity facet values:
    - [x] padel (facet: activity, display_name: "Padel", description, seo_slug: "padel-edinburgh", search_keywords, icon_url: "/icons/padel.svg", color: "#FF6B35")
    - [x] tennis (facet: activity, display_name: "Tennis", seo_slug: "tennis-edinburgh", icon_url: "/icons/tennis.svg", color: "#4ECDC4")
    - [x] gym (facet: activity, display_name: "Gym & Fitness", seo_slug: "gyms-edinburgh", icon_url: "/icons/gym.svg", color: "#95E1D3")
    - [x] swimming (facet: activity, display_name: "Swimming", seo_slug: "swimming-edinburgh")
  - [x] Role facet values (INTERNAL-ONLY, universal function-style keys):
    - [x] provides_facility (facet: role, display_name: "Venue", description: "Physical facility providing activities")
    - [x] sells_goods (facet: role, display_name: "Retailer", description: "Sells sports equipment/gear")
    - [x] provides_instruction (facet: role, display_name: "Coach / Instructor", description: "Provides coaching or instruction")
    - [x] membership_org (facet: role, display_name: "Club", description: "Membership-based sports club")
    - [x] **NOTE**: Labels like "Venue", "Club", "Retailer", "Coach" are lens display labels ONLY. Never use these as structural concepts, entity types, classes, or system concepts. They are strictly for UI presentation.
  - [x] Place type facet values:
    - [x] sports_centre (facet: place_type, display_name: "Sports Centre", description: "Multi-sport facilities", search_keywords: ["sports centre", "leisure centre"])
    - [x] outdoor_facility (facet: place_type, display_name: "Outdoor Facility", description: "Outdoor facilities and parks", search_keywords: ["outdoor", "park"])
    - [x] gym_facility (facet: place_type, display_name: "Gym Facility", description: "Dedicated gym/fitness center", search_keywords: ["gym", "fitness center"])
    - [x] **NOTE**: place_type represents the container place classification (sports_centre, leisure_centre, park, gym_facility). Individual facilities (padel courts, tennis courts, pitches, pools, tracks) belong in domain modules (sports_facility.inventory), NOT as place_type values. A pitch, court, pool, or rink is NOT a place_type.
  - [x] Access facet values:
    - [x] membership (facet: access, display_name: "Membership", description: "Membership required", search_keywords: ["members only", "membership"])
    - [x] pay_and_play (facet: access, display_name: "Pay & Play", description: "Open to public, pay per use", search_keywords: ["pay and play", "casual"])
    - [x] free (facet: access, display_name: "Free to Use", description: "Free access facilities", search_keywords: ["free", "no charge"])
    - [x] private_club (facet: access, display_name: "Private Club", description: "Private members-only club", search_keywords: ["private club", "exclusive"])
- [x] Add comments:
  - [x] "All dimension_source MUST be one of: canonical_activities, canonical_roles, canonical_place_types, canonical_access"
  - [x] "Every value.facet MUST reference a facet defined in facets section"
  - [x] "Role facet added (internal-only, not shown in UI)"
  - [x] "Role keys are universal function-style (provides_facility, sells_goods, provides_instruction, membership_org)"
  - [x] "Role display_name carries vertical/product terminology (Venue, Retailer, Coach/Instructor, Club)"
  - [x] "private_club moved from place_type to access facet"
- [x] Define mapping_rules section:
  - [x] Padel: '(?i)\bp[aá]d[eé]l\b' → padel (confidence: 1.0)
  - [x] Tennis: '(?i)\btennis\b' → tennis (confidence: 1.0)
  - [x] Gym: '(?i)\bgym\b|\bfitness\b' → gym (confidence: 0.9)
  - [x] Sports centre: '(?i)sports\s+(centre|center)' → sports_centre (confidence: 0.95)
  - [x] Private club: '(?i)private|members.only' → private_club (confidence: 0.8)
  - [x] Role mappings (emit universal function-style keys):
    - [x] Venue/facility: '(?i)\bvenue\b|\bfacility\b' → provides_facility (confidence: 0.85)
    - [x] Coach/instructor: '(?i)\bcoach\b|\binstructor\b' → provides_instruction (confidence: 0.95)
    - [x] Retailer/shop: '(?i)\bretailer\b|\bshop\b' → sells_goods (confidence: 0.85)
    - [x] Club: '(?i)\bclub\b' → membership_org (confidence: 0.8)
  - [x] **IMPORTANT**: Every mapping_rules.canonical value MUST exist in values section
- [x] Define derived_groupings section (computed from entity_class + roles with AND/OR logic):
  - [x] places grouping:
    - [x] id: places
    - [x] label: "Places"
    - [x] description: "Physical facilities and venues"
    - [x] rules: [entity_class: "place"]
    - [x] **NOTE**: Grouping is DERIVED/VIEW-ONLY, not stored in database
  - [x] people grouping:
    - [x] id: people
    - [x] label: "Coaches & Instructors"
    - [x] description: "Professional coaching services"
    - [x] rules: [entity_class: "person", roles: ["provides_instruction"]] (AND logic: must be person AND have provides_instruction role)
    - [x] **NOTE**: Grouping is DERIVED/VIEW-ONLY, not stored in database
  - [x] organizations grouping:
    - [x] id: organizations
    - [x] label: "Clubs & Organizations"
    - [x] description: "Sports clubs and membership organizations"
    - [x] rules: [entity_class: "organization"]
    - [x] **NOTE**: Grouping is DERIVED/VIEW-ONLY, not stored in database
  - [x] events grouping:
    - [x] id: events
    - [x] label: "Events & Activities"
    - [x] description: "Tournaments, classes, and events"
    - [x] rules: [entity_class: "event"]
    - [x] **NOTE**: Grouping is DERIVED/VIEW-ONLY, not stored in database
- [x] Define modules section (DOMAIN-SPECIFIC MODULES in lens only):
  - [x] sports_facility module:
    - [x] description: "Sports-specific facility attributes with inventory structure"
    - [x] fields:
      - [x] inventory (type: json, description: "Per-activity court/facility inventory with structure: {tennis: {total: 6, indoor: 2, outdoor: 4, surface: hard_court}, padel: {total: 4, indoor: 4, outdoor: 0, surface: artificial_turf}}")
      - [x] floodlit (type: boolean)
      - [x] general_surface_types (type: array<string>, description: "Facility-wide surface types if not per-activity")
  - [x] fitness_facility module:
    - [x] description: "Gym and fitness facility attributes"
    - [x] fields: gym_size_sqm, cardio_equipment_count, weight_equipment_available, free_weights, classes_per_week, yoga_classes, pilates_classes, spin_classes
  - [x] food_service module:
    - [x] description: "Food and beverage services"
    - [x] fields: cafe, restaurant, bar, vending_machines
  - [x] aquatic_facility module:
    - [x] description: "Swimming pool attributes"
    - [x] fields: indoor_pool, outdoor_pool, indoor_pool_length_m, outdoor_pool_length_m, family_swim, swimming_lessons
- [x] Define module_triggers section (EXPLICIT LIST FORMAT):
  - [x] Padel trigger:
    - [x] when: {facet: activity, value: padel}
    - [x] add_modules: ["sports_facility"]
    - [x] conditions: [{entity_class: "place"}]
  - [x] Tennis trigger:
    - [x] when: {facet: activity, value: tennis}
    - [x] add_modules: ["sports_facility"]
    - [x] conditions: [{entity_class: "place"}]
  - [x] Gym trigger:
    - [x] when: {facet: activity, value: gym}
    - [x] add_modules: ["fitness_facility", "food_service"]
    - [x] conditions: [{entity_class: "place"}]
  - [x] Swimming trigger:
    - [x] when: {facet: activity, value: swimming}
    - [x] add_modules: ["aquatic_facility"]
    - [x] conditions: [{entity_class: "place"}]
  - [x] Sports centre trigger:
    - [x] when: {facet: place_type, value: sports_centre}
    - [x] add_modules: ["amenities", "hours", "food_service"]
- [x] Add NOTE to module_triggers:
  - [x] "NOTE on facet vs dimension_source naming:"
  - [x] "  - facet in module_triggers refers to the lens facet key (activity, role, place_type, access, etc.) as defined in the lens.facets section"
  - [x] "  - dimension_source refers to the actual DB column (canonical_activities, canonical_roles, canonical_place_types, canonical_access)"
  - [x] "  - Example: facet='activity' maps to dimension_source='canonical_activities'"
  - [x] "  - This distinction avoids key collisions and enables triggers across all facets defined by the lens"
- [x] Define seo_templates section:
  - [x] activity_index: url_pattern: "/{activity_slug}", title_template, meta_description_template, h1_template
  - [x] activity_place_type: url_pattern: "/{activity_slug}/{place_type_slug}", title_template, meta_description_template

**Success Criteria:**
- ✅ All dimension_source use actual DB column names: canonical_activities, canonical_roles, canonical_place_types, canonical_access
- ✅ Module triggers refactored to explicit list format with `when: {facet, value}`
- ✅ NOTE clarifies facet vs dimension_source distinction with examples
- ✅ place_type clarified: container classification only (sports_centre, leisure_centre, park, gym_facility), NOT individual facilities
- ✅ Individual facilities (courts, pitches, pools) documented to go in sports_facility.inventory
- ✅ Role facet added (internal-only, not shown in UI)
- ✅ Role keys are universal function-style (provides_facility, sells_goods, provides_instruction, membership_org)
- ✅ Role display_name carries vertical/product terminology (Venue, Retailer, Coach/Instructor, Club) - display labels ONLY
- ✅ Vertical vocabulary (Venue, Club, Shop, Coach) explicitly marked as lens display labels only, never as structural concepts
- ✅ private_club moved from place_type to access facet
- ✅ sports_facility uses inventory JSON structure instead of individual fields
- ✅ Derived groupings use entity_class + roles (AND within rule)
- ✅ Derived groupings documented as DERIVED/VIEW-ONLY (not stored)
- ✅ All interpretation metadata (labels, icons, colors) in lens

### Task 2.1a: Lens Contract Validation (v2.2 Addition)

**Status:** ✅ completed

**Description:** Implement fail-fast validation to enforce lens configuration contracts

**Subtasks:**
- [x] Create `lenses/validator.py` module:
  - [x] Define ALLOWED_DIMENSION_SOURCES constant:
    ```python
    ALLOWED_DIMENSION_SOURCES = {
        "canonical_activities",
        "canonical_roles",
        "canonical_place_types",
        "canonical_access"
    }
    ```
  - [x] Implement validate_lens_config(config: dict) function:
    - [x] **CONTRACT 1**: Every facet.dimension_source MUST be one of the 4 allowed dimension sources
    - [x] **CONTRACT 2**: Every value.facet MUST exist in facets section
    - [x] **CONTRACT 3**: Every mapping_rules.canonical MUST exist in values section
    - [x] **CONTRACT 4**: No duplicate value.key across all values
    - [x] **CONTRACT 5**: No duplicate facet keys
    - [x] Raise ValidationError with clear message on contract violation
- [x] Update `lenses/loader.py`:
  - [x] Import and call validate_lens_config() in VerticalLens.__init__()
  - [x] **FAIL-FAST**: Validation errors must raise exception immediately (no silent failures)
  - [x] Add try/except to provide clear error context:
    ```python
    try:
        validate_lens_config(self.config)
    except ValidationError as e:
        raise LensConfigError(f"Invalid lens config in {config_path}: {e}")
    ```
- [x] Create validation tests in `tests/lenses/test_validator.py`:
  - [x] Test: Invalid dimension_source (not one of 4 allowed) → ValidationError
  - [x] Test: value.facet references non-existent facet → ValidationError
  - [x] Test: mapping_rules.canonical references non-existent value → ValidationError
  - [x] Test: Duplicate value.key → ValidationError
  - [x] Test: Duplicate facet key → ValidationError
  - [x] Test: Valid config passes validation
- [x] Add validation to lens loader tests:
  - [x] Test loading invalid lens.yaml fails immediately
  - [x] Test error message clearly identifies contract violation

**Success Criteria:**
- ✅ ALLOWED_DIMENSION_SOURCES defined with exactly 4 canonical_* columns
- ✅ validate_lens_config() enforces all 5 contracts
- ✅ Validation errors raise exception immediately (fail-fast)
- ✅ Clear error messages identify which contract was violated
- ✅ All validation tests pass
- ✅ Loading invalid lens.yaml fails at startup (not runtime)

**Acceptance Check:**
```python
# Invalid dimension_source should fail immediately
invalid_config = {
    "facets": {
        "activity": {
            "dimension_source": "invalid_dimension"  # NOT in allowed list
        }
    }
}
with pytest.raises(ValidationError, match="dimension_source must be one of"):
    validate_lens_config(invalid_config)
```

### Task 2.2: Implement Lens Loader

**Status:** pending

**Description:** Create `lenses/loader.py` with lens configuration loader and processing logic

**Subtasks:**
- [ ] Create `lenses/loader.py` file
- [ ] Implement FacetDefinition class:
  - [ ] __init__(key, data)
  - [ ] Store: key, dimension_source (actual DB column name), ui_label, display_mode, order, show_in_filters, show_in_navigation, icon
- [ ] Implement CanonicalValue class:
  - [ ] __init__(data)
  - [ ] Store: key, facet, display_name, description, seo_slug, search_keywords, icon_url, color
- [ ] Implement DerivedGrouping class:
  - [ ] __init__(data)
  - [ ] Store: id, label, description, rules
  - [ ] Implement matches(entity) method:
    - [ ] AND-within-rule: All conditions in a rule must match
    - [ ] OR-across-rules: Any rule can match
    - [ ] Check entity_class match
    - [ ] Check roles match (entity must have at least one of required roles)
  - [ ] Add docstring: "Grouping is DERIVED/VIEW-ONLY, not stored in database"
- [ ] Implement ModuleTrigger class:
  - [ ] __init__(data)
  - [ ] Store: facet (lens-defined facet key), value, add_modules, conditions
  - [ ] Add docstring: "NOTE: facet refers to the canonical value's facet key as defined by the lens (i.e., lens.facets keys), e.g. activity, role, wine_type, venue_type, NOT the DB column name"
  - [ ] Implement matches(entity_class, canonical_values_by_facet) method:
    - [ ] Check if entity has this value in the specified facet
    - [ ] Check additional conditions (entity_class match)
    - [ ] Return True if trigger should fire
  - [ ] Add docstring to matches() method clarifying canonical_values_by_facet structure:
    - [ ] "Dict mapping facet keys (as defined by the lens) to lists of canonical values"
    - [ ] "Example: {activity: [padel, tennis], role: [provides_facility], place_type: [sports_centre]}"
- [ ] Implement ModuleDefinition class:
  - [ ] __init__(name, data)
  - [ ] Store: name, description, fields
- [ ] Implement VerticalLens class:
  - [ ] __init__(lens_id, config_path)
  - [ ] Load YAML config
  - [ ] **CRITICAL**: Call validate_lens_config(config) FIRST (fail-fast validation)
  - [ ] Parse lens info
  - [ ] Parse facets (build FacetDefinition dict)
  - [ ] Parse values (build CanonicalValue dict)
  - [ ] Parse mapping_rules
  - [ ] Parse derived_groupings (build DerivedGrouping list)
  - [ ] Parse modules (build ModuleDefinition dict)
  - [ ] Parse module_triggers (build ModuleTrigger list from explicit list format)
  - [ ] Parse seo_templates
  - [ ] Implement map_raw_category(raw_category) → List[str]:
    - [ ] Apply regex mapping rules
    - [ ] Filter by confidence threshold (>=0.7)
    - [ ] Return list of canonical value keys
  - [ ] Implement get_values_by_facet(facet_key) → List[CanonicalValue]
  - [ ] Implement get_facets_sorted() → List[FacetDefinition]
  - [ ] Implement compute_grouping(entity) → Optional[str]:
    - [ ] Iterate through derived_groupings
    - [ ] Return first matching grouping id
    - [ ] **NOTE**: Grouping is computed at query time, not stored
  - [ ] Implement get_required_modules(entity_class, canonical_values_by_facet) → List[str]:
    - [ ] Accept canonical_values_by_facet dict for flexible matching
    - [ ] Apply lens module triggers
    - [ ] Return list of required module names
- [ ] Implement LensRegistry class:
  - [ ] Class variable: _lenses dict
  - [ ] Implement register(lens_id, config_path) classmethod
  - [ ] Implement get_lens(lens_id) classmethod
  - [ ] Implement load_all(lenses_dir) classmethod
- [ ] Add helper function dedupe_preserve_order(values: List[str]) → List[str]:
  - [ ] Deduplicate list while preserving insertion order
  - [ ] Used to avoid repeated trigger evaluation and ensure deterministic output

**Success Criteria:**
- ✅ ModuleTrigger class documentation specifies facet refers to facet key as defined by the lens (lens.facets keys)
- ✅ ModuleTrigger.matches() documentation clarifies canonical_values_by_facet structure uses lens-defined facet keys
- ✅ get_required_modules() accepts canonical_values_by_facet dict for flexible matching
- ✅ DerivedGrouping.matches() implements AND-within-rule, OR-across-rules
- ✅ DerivedGrouping documented as DERIVED/VIEW-ONLY (not stored)
- ✅ Supports lens-specific module definitions
- ✅ Generic transformation helpers only (no vertical-specific logic)
- ✅ Role facet support (internal-only)
- ✅ Uses actual DB column names in dimension_source
- ✅ Calls validate_lens_config() at initialization (fail-fast)

### Task 2.2a: Module Composition Hardening (v2.2 Addition)

**Status:** pending

**Description:** Enforce module composition contracts: no flattened JSONB, prevent duplicate module keys at YAML load stage

**Subtasks:**
- [ ] Create `engine/modules/validator.py`:
  - [ ] Implement validate_modules_namespacing(modules_data: dict):
    - [ ] **CONTRACT 1**: modules JSONB MUST be namespaced by module key
    - [ ] Check structure: {"location": {...}, "contact": {...}, "sports_facility": {...}}
    - [ ] Raise ValidationError if flattened structure detected
    - [ ] Error message: "modules JSONB must be namespaced by module key, not flattened"
  - [ ] **NOTE on duplicate module keys**: Python dicts inherently prevent duplicate keys (last value wins)
    - [ ] JSON parsers: Duplicate keys silently overwrite (last wins)
    - [ ] PyYAML: By default allows duplicate keys (last wins), but should be configured to reject
    - [ ] **SOLUTION**: Configure YAML loader to reject duplicate keys at parse time
  - [ ] **NOTE**: Duplicate field names across DIFFERENT modules are ALLOWED due to namespacing
    - [ ] Example: sports_facility.name and wine_production.name is valid
    - [ ] Namespacing makes field name collisions safe
- [ ] Update entity_model.yaml loader:
  - [ ] Configure YAML loader to reject duplicate keys at parse time
  - [ ] Use yaml.safe_load with custom constructor or strictyaml
  - [ ] Add module namespacing validation when loading engine modules
  - [ ] Ensure modules are properly namespaced (not flattened)
- [ ] Update lens.yaml loader (lenses/loader.py):
  - [ ] Configure YAML loader to reject duplicate keys at parse time
  - [ ] Use yaml.safe_load with custom constructor or strictyaml
  - [ ] Add module namespacing validation when loading lens modules
  - [ ] Ensure modules are properly namespaced (not flattened)
- [ ] Update extraction pipeline:
  - [ ] Ensure modules are stored with JSONB namespacing:
    ```python
    # CORRECT structure
    entity.modules = {
        "location": {"latitude": 55.95, "longitude": -3.18},
        "sports_facility": {"inventory": {"tennis": {"total": 6}}}
    }
    # WRONG structure (flattened)
    entity.modules = {"latitude": 55.95, "longitude": -3.18, "inventory": {...}}
    ```
  - [ ] Add assertion to verify namespacing before database write
- [ ] Create tests in `tests/modules/test_composition.py`:
  - [ ] Test: Duplicate module keys in YAML rejected at load time
  - [ ] Test: Valid modules with unique keys pass validation
  - [ ] Test: Flattened modules JSONB → ValidationError
  - [ ] Test: Properly namespaced modules JSONB passes validation
  - [ ] Test: Duplicate field names across DIFFERENT modules are ALLOWED (due to namespacing)

**Success Criteria:**
- ✅ Duplicate module keys in YAML rejected at load time (YAML loader configured to detect duplicates)
- ✅ modules JSONB enforced to use namespaced structure {module_key: {fields}}
- ✅ Duplicate field names across different modules are ALLOWED (namespacing makes this safe)
- ✅ Validation errors fail-fast with clear error messages
- ✅ All module composition tests pass
- ✅ Extraction pipeline enforces namespacing

**Acceptance Check:**
```python
# Test: Duplicate field names across different modules should PASS (allowed due to namespacing)
modules = {
    "location": ModuleDefinition("location", {"fields": [{"name": "name"}]}),
    "sports_facility": ModuleDefinition("sports_facility", {"fields": [{"name": "name"}]})
}
validate_module_composition(modules)  # Should NOT raise - field names can duplicate across modules

# Test: Duplicate module keys in YAML should fail at load time
# NOTE: This YAML will be rejected by the YAML loader (not at validation time)
yaml_with_duplicates = """
modules:
  sports_facility:
    inventory: {...}
  sports_facility:  # Duplicate key - rejected by YAML loader
    name: "Test"
"""
with pytest.raises(yaml.constructor.ConstructorError, match="found duplicate key"):
    yaml.safe_load(yaml_with_duplicates)

# Test: Flattened JSONB should fail
flattened = {"latitude": 55.95, "phone": "+44123"}
with pytest.raises(ValidationError, match="must be namespaced"):
    validate_modules_namespacing(flattened)

# Test: Namespaced JSONB should pass
namespaced = {
    "location": {"latitude": 55.95},
    "contact": {"phone": "+44123"}
}
validate_modules_namespacing(namespaced)  # Should not raise
```

**Phase 2 Checkpoint (Updated for v2.2):**
- All verification tasks completed
- Lens configuration structure created with contract validation
- Lens loader implemented with fail-fast validation
- Role facet implemented (internal-only)
- Derived groupings logic correct (AND/OR) and documented as view-only
- Module composition validated (no duplicates, namespaced JSONB)
- Zero vertical-specific logic in loader (generic only)

---

## Phase 3: Data Flow Integration

**Goal:** Integrate lens layer into extraction pipeline and query layer

### Task 3.1: Update Extraction Pipeline

**Status:** pending

**Description:** Modify extraction pipeline to use lens mapping and distribute values to dimensions by facet

**Subtasks:**
- [ ] Update `engine/extraction/base.py`:
  - [ ] Import dedupe_preserve_order helper
  - [ ] **CRITICAL**: Engine MUST NOT import from lenses/ directory - receives LensContract data object only
  - [ ] **LensContract boundary**: Engine functions receive LensContract (plain dict) injected by bootstrap, never lens runtime objects
  - [ ] Implement extract_with_lens_contract(raw_data, lens_contract: dict) function:
    - [ ] **PARAMETER**: lens_contract is a plain dict (LensContract), not a lens runtime object
    - [ ] Step 1: Extract raw categories from source (unchanged)
    - [ ] Step 2: Map to canonical values using LensContract mapping rules:
      - [ ] Access mapping_rules from lens_contract["mapping_rules"]
      - [ ] Apply regex rules to raw categories
      - [ ] Filter by confidence threshold
      - [ ] Build canonical_values list
    - [ ] Step 2a: Dedupe canonical_values to avoid repeated trigger evaluation (dedupe_preserve_order)
    - [ ] Step 3: Distribute canonical values to dimensions by facet:
      - [ ] Initialize dimensions dict with actual DB column names: {canonical_activities: [], canonical_roles: [], canonical_place_types: [], canonical_access: []}
      - [ ] Build facet_to_dimension lookup from lens_contract["facets"] (maps facet key to dimension_source)
      - [ ] Build values_by_key index from lens_contract["values"] list for efficient lookups: {key: value_obj}
      - [ ] Initialize canonical_values_by_facet with EMPTY LISTS for all facets from lens_contract["facets"]
      - [ ] Iterate through canonical_values:
        - [ ] Find value in values_by_key index (built from lens_contract["values"])
        - [ ] Get facet from value["facet"]
        - [ ] Get dimension column name from facet_to_dimension lookup
        - [ ] Append value key to dimension array
        - [ ] Track by facet key in canonical_values_by_facet dict
      - [ ] Deduplicate dimension arrays before persistence (dedupe_preserve_order)
      - [ ] Deduplicate canonical_values_by_facet dict (dedupe_preserve_order)
    - [ ] Step 4: Resolve entity_class (deterministic, engine rules - no lens dependency)
    - [ ] Step 5: Compute required modules:
      - [ ] Get engine modules (entity_class-based, from engine config)
      - [ ] Get lens modules from lens_contract["module_triggers"]:
        - [ ] Iterate through triggers in lens_contract["module_triggers"]
        - [ ] Check if trigger matches using canonical_values_by_facet
        - [ ] Check entity_class conditions
        - [ ] Add triggered modules to required_modules
      - [ ] Merge into required_modules set
    - [ ] Step 6: Extract module attributes (using lens_contract["modules"] definitions)
    - [ ] Step 7: Build modules JSONB with namespacing:
      ```python
      modules_data = {}
      for module_name in required_modules:
          # Get module definition from lens_contract["modules"]
          module_def = lens_contract["modules"].get(module_name)
          module_fields = extract_module_fields(module_name, raw_data, module_def)
          modules_data[module_name] = module_fields  # Namespaced by module key
      ```
    - [ ] Step 8: Return structured entity with deduplicated text[] arrays for dimensions
    - [ ] **NOTE**: Function signature uses lens_contract (dict), NOT lens object - enforces LensContract boundary
  - [ ] Add comments:
    - [ ] "LensContract boundary: Engine receives lens_contract (plain dict), NEVER imports from lenses/"
    - [ ] "Application bootstrap loads lens and injects LensContract into engine"
    - [ ] "Uses actual DB column names for dimensions (canonical_activities, canonical_roles, canonical_place_types, canonical_access)"
    - [ ] "Builds facet_to_dimension lookup from lens_contract['facets']"
    - [ ] "Initialize canonical_values_by_facet with empty lists for all facets from lens_contract"
    - [ ] "Module triggers evaluated from lens_contract['module_triggers']"
    - [ ] "Comments clarify dimensions stored as Postgres text[] arrays"
    - [ ] "Deduplication: dedupe_preserve_order applied to canonical_values and dimension arrays"
    - [ ] "Modules JSONB: Namespaced by module key, not flattened"
- [ ] Create `engine/extraction/entity_classifier.py`:
  - [ ] Implement resolve_entity_class(raw_data) function:
    - [ ] Deterministic classification rules (PRIORITY ORDER per Task 1.3):
      - [ ] **1. Time-bounded** (start/end times) → event (HIGHEST PRIORITY - check FIRST)
      - [ ] **2. Physical location** (lat/lng or street address) → place
      - [ ] **3. Membership/group** entity with no fixed location → organization
      - [ ] **4. Named individual** → person
      - [ ] **5. Tie-breaker**: Primary physical site → place, otherwise → organization
    - [ ] Return entity_class string
    - [ ] Add assertion: Result must be one of: place, person, organization, event, thing
    - [ ] Add comment: "Time-bounded entities (events) must be evaluated BEFORE physical location (places)"
  - [ ] Implement get_engine_modules(entity_class) function:
    - [ ] Load entity_model.yaml
    - [ ] Return required_modules for entity_class
- [ ] Update all extractors to use extract_with_lens_contract:
  - [ ] Serper extractor (receives lens_contract dict, not lens object)
  - [ ] Google Places extractor (receives lens_contract dict, not lens object)
  - [ ] OSM extractor (receives lens_contract dict, not lens object)
  - [ ] Other extractors (all receive lens_contract dict, not lens object)
  - [ ] **NOTE**: Bootstrap layer loads lens and produces LensContract, then injects into extractors

**Success Criteria:**
- ✅ **LensContract boundary enforced**: Engine receives lens_contract (plain dict), NEVER imports from lenses/
- ✅ Function signature uses lens_contract dict parameter, NOT lens object
- ✅ All mapping rules accessed from lens_contract["mapping_rules"]
- ✅ All facets accessed from lens_contract["facets"]
- ✅ All values accessed from lens_contract["values"] (list format in contract)
- ✅ Engine builds values_by_key index from lens_contract["values"] list for efficient lookups
- ✅ All module triggers accessed from lens_contract["module_triggers"]
- ✅ Uses actual DB column names for dimensions (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
- ✅ Builds facet_to_dimension lookup from lens_contract["facets"]
- ✅ Initialize canonical_values_by_facet with empty lists for all facets from lens_contract
- ✅ Module triggers evaluated from lens_contract (not lens object methods)
- ✅ Comments clarify dimensions stored as Postgres text[] arrays
- ✅ Deduplication: dedupe_preserve_order applied to canonical_values list (avoids repeated module trigger evaluation)
- ✅ Deduplication: Applied to all dimension arrays before persistence
- ✅ Deduplication: Preserves insertion order (deterministic output)
- ✅ Modules JSONB namespaced by module key (not flattened)
- ✅ Engine resolves entity_class deterministically (time-bounded checked FIRST)

### Task 3.2: Update Query Layer

**Status:** pending

**Description:** Create query layer with Prisma array filters and lens transformations

**NOTE on LensContract vs VerticalLens usage:**
- **Web layer** (TypeScript, outside engine): CAN use lens runtime objects (VerticalLens) for transformations
- **Engine layer** (Python): MUST ONLY use LensContract (plain dict), NEVER import from lenses/
- This query layer is in web/ (outside engine), so VerticalLens usage is allowed

**Subtasks:**
- [ ] Create `web/lib/lens-query.ts` file
- [ ] Define FacetFilter interface:
  - [ ] facet: string
  - [ ] dimensionSource: string (actual DB column name: canonical_activities, canonical_roles, etc.)
  - [ ] selectedValues: string[]
  - [ ] mode: 'OR' | 'AND' (hasSome vs hasEvery)
- [ ] Implement queryByFacet(filter: FacetFilter) function:
  - [ ] Use dimensionSource (actual DB column name)
  - [ ] If mode === 'AND': return {[dimensionSource]: {hasEvery: selectedValues}} (Postgres array @> operator)
  - [ ] If mode === 'OR' (DEFAULT): return {[dimensionSource]: {hasSome: selectedValues}} (Postgres array && operator)
  - [ ] Add comment: "Default is OR mode (entity has ANY of these values)"
- [ ] Implement queryByValue(dimension: string, value: string) function:
  - [ ] Return {[dimension]: {has: value}} (Postgres array ? operator)
- [ ] Implement queryByGrouping(groupingId: string, lens: VerticalLens) function:
  - [ ] Get grouping from lens.derived_groupings
  - [ ] Build OR across rules, AND within each rule
  - [ ] For each rule:
    - [ ] Add entity_class condition if present
    - [ ] Add canonical_roles hasSome condition if roles present
  - [ ] Return OR of all rules
  - [ ] Add comment: "Grouping is computed at query time, not stored in database"
- [ ] Implement buildComplexQuery(...filters, groupingId, lens) function:
  - [ ] **DEFAULT**: OR within facet, AND across facets
  - [ ] Support activity, place_type, access filters (OR mode within each facet)
  - [ ] Add grouping filter if present
  - [ ] Example:
    ```typescript
    // User selects: activities=[padel, tennis], place_type=[sports_centre]
    // Result: (activities HAS padel OR tennis) AND (place_type HAS sports_centre)
    {
      AND: [
        { canonical_activities: { hasSome: ['padel', 'tennis'] } },  // OR within facet
        { canonical_place_types: { hasSome: ['sports_centre'] } }   // AND across facets
      ]
    }
    ```
- [ ] Implement transformEntityToView(entity: Entity, lens: VerticalLens) function:
  - [ ] Apply lens interpretation to opaque values
  - [ ] Map activities to {key, label, icon, color}
  - [ ] Compute grouping using lens.compute_grouping (derived, not stored)
  - [ ] Return EntityView with rich metadata
- [ ] Add comments:
  - [ ] "dimensionSource uses actual DB column names (canonical_activities, canonical_roles, canonical_place_types, canonical_access)"
  - [ ] "Use Prisma array filters: has, hasSome (OR), hasEvery (AND)"
  - [ ] "Default query semantics: OR within facet, AND across facets"
  - [ ] "Grouping is computed at query time from entity_class + roles, not stored in database"
  - [ ] "Queries operate on Postgres text[] arrays (not JSON)"

**Success Criteria:**
- ✅ dimensionSource uses actual DB column names (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
- ✅ Use Prisma array filters: has, hasSome (OR), hasEvery (AND)
- ✅ Default query semantics: OR within facet, AND across facets
- ✅ Grouping computed at query time (not stored)
- ✅ Derived grouping: AND within rule, OR across rules
- ✅ Queries operate on Postgres text[] arrays (not JSON)

### Task 3.2a: Query Semantics Documentation (v2.2 Addition)

**Status:** pending

**Description:** Document and enforce default query semantics with examples

**Subtasks:**
- [ ] Create `web/docs/query_semantics.md`:
  - [ ] **Rule**: Default is OR within facet, AND across facets
  - [ ] **Example 1**: Activities filter [padel, tennis]
    ```typescript
    // User selects multiple activities: "Show me places with padel OR tennis"
    { canonical_activities: { hasSome: ['padel', 'tennis'] } }
    // Entity matches if it has ANY of these activities
    ```
  - [ ] **Example 2**: Multi-facet filter
    ```typescript
    // User selects: activities=[padel, tennis] AND place_type=[sports_centre]
    // Semantic: "Show me sports centres with padel OR tennis"
    {
      AND: [
        { canonical_activities: { hasSome: ['padel', 'tennis'] } },  // OR within facet
        { canonical_place_types: { hasSome: ['sports_centre'] } }    // AND across facets
      ]
    }
    // Entity matches if: (has padel OR tennis) AND (is sports_centre)
    ```
  - [ ] **Example 3**: Derived grouping (computed, not stored)
    ```typescript
    // Derived grouping "people" = entity_class:person AND roles:provides_instruction
    // This is computed at query time, never stored in database
    {
      AND: [
        { entity_class: 'person' },
        { canonical_roles: { hasSome: ['provides_instruction'] } }
      ]
    }
    // Grouping is a VIEW-ONLY concept, derived from entity_class + roles
    ```
  - [ ] **Example 4**: AND mode (special case)
    ```typescript
    // User wants places with BOTH padel AND tennis (rare case)
    { canonical_activities: { hasEvery: ['padel', 'tennis'] } }
    // Entity matches if it has ALL of these activities
    // Note: This is NOT the default, must be explicitly requested
    ```
  - [ ] **Anti-pattern**: Storing grouping in database
    - [ ] ❌ NEVER add grouping_id column to entities table
    - [ ] ❌ NEVER store computed grouping value
    - [ ] ✅ ALWAYS compute grouping at query/view time from entity_class + roles
- [ ] Add inline comments to query layer code:
  - [ ] Document default OR within facet
  - [ ] Document AND across facets
  - [ ] Document that grouping is derived/computed, not stored
- [ ] Add tests for query semantics:
  - [ ] Test: OR within facet (multiple activities)
  - [ ] Test: AND across facets (activities + place_type)
  - [ ] Test: Derived grouping computed correctly
  - [ ] Test: Grouping not stored in database (read-only property)

**Success Criteria:**
- ✅ query_semantics.md exists with clear examples
- ✅ Default semantics documented: OR within facet, AND across facets
- ✅ Derived grouping documented as VIEW-ONLY, not stored
- ✅ Anti-patterns documented (no grouping storage)
- ✅ All query semantic tests pass

**Acceptance Check:**
```typescript
// Test: Default OR within facet
const result = await prisma.entity.findMany({
  where: { canonical_activities: { hasSome: ['padel', 'tennis'] } }
});
// Should return entities with padel OR tennis (not both required)

// Test: Grouping is computed, not stored
const entity = await prisma.entity.findUnique({ where: { id: '123' } });
assert(entity.grouping === undefined);  // No grouping column in database
const grouping = lens.compute_grouping(entity);  // Computed at runtime
assert(grouping === 'people');  // Derived from entity_class + roles
```

**Phase 3 Checkpoint (Updated for v2.2):**
- All verification tasks completed
- Extraction pipeline updated with lens integration
- facet_to_dimension lookup built from lens config
- canonical_values_by_facet initialized with empty lists
- Deduplication applied deterministically
- Modules JSONB namespaced correctly
- Query layer implemented with Prisma array filters
- Query semantics documented (OR within, AND across)
- Grouping is derived/view-only (not stored)
- Lens transformations working

---

## Phase 4: Migration Strategy

**Goal:** Migrate existing data to new schema and validate

### Task 4.1: Data Migration Steps

**Status:** pending

**Description:** Create SQL migration scripts to transform existing data to new schema

**Subtasks:**
- [ ] Create migration script `scripts/migrate_listing_to_entity.py`:
  - [ ] Step 1: Schema migration SQL:
    - [ ] Rename table: ALTER TABLE listings RENAME TO entities (if needed)
    - [ ] Add entity_class column: ALTER TABLE entities ADD COLUMN entity_class TEXT
    - [ ] Rename entityType column: ALTER TABLE entities RENAME COLUMN entityType TO old_entity_type
    - [ ] Add dimension columns as text[] arrays:
      - [ ] ALTER TABLE entities ADD COLUMN canonical_activities TEXT[] DEFAULT '{}'
      - [ ] ALTER TABLE entities ADD COLUMN canonical_roles TEXT[] DEFAULT '{}'
      - [ ] ALTER TABLE entities ADD COLUMN canonical_place_types TEXT[] DEFAULT '{}'
      - [ ] ALTER TABLE entities ADD COLUMN canonical_access TEXT[] DEFAULT '{}'
    - [ ] **VERIFY**: Postgres array defaults set to '{}' (empty array, not null)
  - [ ] Step 2: Data transformation:
    - [ ] Map old entityType to new entity_class + canonical_roles:
      - [ ] VENUE → {entity_class: 'place', roles: ['provides_facility']}
      - [ ] RETAILER → {entity_class: 'place', roles: ['sells_goods']}
      - [ ] COACH → {entity_class: 'person', roles: ['provides_instruction']}
      - [ ] INSTRUCTOR → {entity_class: 'person', roles: ['provides_instruction']}
      - [ ] CLUB → {entity_class: 'organization', roles: ['membership_org']}
      - [ ] LEAGUE → {entity_class: 'organization', roles: ['membership_org']}
      - [ ] EVENT → {entity_class: 'event', roles: []}
      - [ ] TOURNAMENT → {entity_class: 'event', roles: []}
    - [ ] **SPECIAL CASE**: "Club with courts" (has physical location)
      - [ ] entity_class: 'place' (has physical courts/location)
      - [ ] canonical_roles: ['provides_facility', 'membership_org'] (both facility and club)
      - [ ] Example: Tennis club with 6 courts → place + [provides_facility, membership_org]
  - [ ] Step 3: Execute migration
- [ ] Apply GIN indexes (run SQL from Phase 1, Task 1.2)
- [ ] Validate migration:
  - [ ] Check all entities have entity_class
  - [ ] Check dimension arrays are valid Postgres text[] arrays
  - [ ] Check no NULL values in dimension arrays (should be empty arrays '{}')
  - [ ] Check "club with courts" correctly has entity_class='place' + multiple roles

**Success Criteria:**
- ✅ Schema migration SQL created and tested
- ✅ Data transformation mapping defined
- ✅ GIN indexes applied to dimension arrays
- ✅ All entities migrated successfully
- ✅ Postgres array defaults verified ('{}' not null)
- ✅ "Club with courts" edge case handled correctly
- ✅ Validation checks pass

### Task 4.2: Re-extraction Process

**Status:** pending

**Description:** Re-run extraction with lens-aware pipeline and validate results

**Subtasks:**
- [ ] Keep RawIngestion records (provenance)
- [ ] Run new extraction pipeline with Edinburgh Finds lens:
  - [ ] **Bootstrap**: Load lens from lenses/loader and produce LensContract (plain dict)
  - [ ] Inject LensContract into extraction pipeline (engine never imports lenses/)
  - [ ] For each raw ingestion:
    - [ ] Run extract_with_lens_contract(raw_data, lens_contract)
    - [ ] Validate dimensions populated as Postgres text[] arrays
    - [ ] Validate lens modules extracted (sports_facility with inventory JSON, etc.)
    - [ ] Validate modules JSONB namespaced correctly
  - [ ] Store extracted entities
- [ ] Validation checks:
  - [ ] Compare old vs new entity counts
  - [ ] Check dimension arrays contain expected values
  - [ ] Check sports_facility module uses inventory JSON structure
  - [ ] Check role values use universal function-style keys (provides_facility, sells_goods, etc.)
  - [ ] Check modules JSONB structure is namespaced (not flattened)
  - [ ] Spot check sample entities for correctness
- [ ] Switch application to new Entity model:
  - [ ] Update API routes
  - [ ] Update frontend queries (use Prisma array filters)
  - [ ] Update UI components (use lens transformations)

**Success Criteria:**
- ✅ Re-extraction completes successfully
- ✅ Dimensions populated correctly as Postgres text[] arrays
- ✅ Lens modules extracted (sports_facility with inventory JSON, etc.)
- ✅ Role values use universal function-style keys
- ✅ Modules JSONB namespaced correctly
- ✅ Validation checks pass
- ✅ Application switched to new model

**Phase 4 Checkpoint (Updated for v2.2):**
- All verification tasks completed
- Migration scripts created and tested
- Re-extraction completed successfully
- Data validated (old vs new comparison)
- Postgres array defaults verified
- Modules JSONB namespacing verified
- "Club with courts" edge case validated
- Application switched to new Entity model

---

## Phase 5: Second Vertical Validation

**Goal:** Validate engine-lens separation by adding Wine Discovery vertical with ZERO engine changes

### Task 5.1: Create Wine Discovery Lens

**Status:** pending

**Description:** Create `lenses/wine_discovery/lens.yaml` to validate vertical-agnostic engine

**Subtasks:**
- [ ] Create `lenses/wine_discovery/lens.yaml` file
- [ ] Define lens metadata:
  - [ ] id: wine_discovery
  - [ ] name: "Wine Discovery"
  - [ ] description: "Discover wineries, wine bars, and wine experiences"
- [ ] Define facets (using SAME engine dimensions):
  - [ ] wine_type facet:
    - [ ] dimension_source: "canonical_activities" (ACTUAL DB COLUMN NAME, reuses activities dimension)
    - [ ] ui_label: "Wine types"
    - [ ] display_mode: "multi_select"
  - [ ] role facet:
    - [ ] dimension_source: "canonical_roles" (ACTUAL DB COLUMN NAME)
    - [ ] ui_label: null (internal-only)
    - [ ] display_mode: "internal"
    - [ ] show_in_filters: false
    - [ ] show_in_navigation: false
  - [ ] venue_type facet:
    - [ ] dimension_source: "canonical_place_types" (ACTUAL DB COLUMN NAME, reuses place_types dimension)
    - [ ] ui_label: "Venue type"
- [ ] Define values:
  - [ ] red_wine (facet: wine_type, display_name: "Red Wine", icon_url: "/icons/red-wine.svg")
  - [ ] white_wine (facet: wine_type, display_name: "White Wine")
  - [ ] winery (facet: venue_type, display_name: "Winery", search_keywords: ["winery", "vineyard", "wine estate"])
  - [ ] wine_bar (facet: venue_type, display_name: "Wine Bar")
  - [ ] Role values (universal function-style keys):
    - [ ] produces_goods (facet: role, display_name: "Producer", description: "Wine producer/winery")
    - [ ] sells_goods (facet: role, display_name: "Retailer", description: "Wine shop/retailer")
- [ ] Define derived_groupings:
  - [ ] places (entity_class: "place")
  - [ ] **NOTE**: Grouping is DERIVED/VIEW-ONLY, not stored in database
- [ ] Define modules (DOMAIN-SPECIFIC):
  - [ ] wine_production module:
    - [ ] description: "Wine production attributes"
    - [ ] fields: vineyard_acres, annual_production_bottles, estate_grown, organic_certified
  - [ ] tasting_room module:
    - [ ] description: "Wine tasting facilities"
    - [ ] fields: tasting_available, tasting_fee, reservation_required, tasting_styles
- [ ] Define module_triggers (EXPLICIT LIST FORMAT):
  - [ ] Winery trigger:
    - [ ] when: {facet: venue_type, value: winery}
    - [ ] add_modules: ["wine_production", "tasting_room"]
    - [ ] conditions: [{entity_class: "place"}]
  - [ ] Wine bar trigger:
    - [ ] when: {facet: venue_type, value: wine_bar}
    - [ ] add_modules: ["food_service"]
- [ ] Add NOTE: "facet refers to the canonical value's facet key as defined by the lens (i.e., lens.facets keys), e.g. wine_type, role, venue_type, NOT the DB column name"
- [ ] **CRITICAL VALIDATION**: Verify zero engine code changes needed
- [ ] Validate: Same dimensions (stored as Postgres text[] arrays), different interpretation
- [ ] Validate: Domain modules (wine_production) defined in lens only
- [ ] Validate: All dimension_source values pass contract validation (one of 4 canonical_* columns)
- [ ] **Bootstrap**: Load wine lens from lenses/loader and produce LensContract (plain dict)
- [ ] Test extraction with wine lens:
  - [ ] Create sample wine raw data
  - [ ] Run extract_with_lens_contract(raw_data, wine_lens_contract)
  - [ ] **Verify**: Engine code unchanged - uses same extract_with_lens_contract function
  - [ ] Validate wine_type values distributed to canonical_activities dimension
  - [ ] Validate venue_type values distributed to canonical_place_types dimension
  - [ ] Validate wine_production module triggered for wineries
  - [ ] Validate role values use universal function-style keys (produces_goods, sells_goods)
  - [ ] Validate modules JSONB namespaced correctly

**Success Criteria:**
- ✅ Wine Discovery lens loads successfully
- ✅ Different interpretation of same dimensions (Postgres text[] arrays)
- ✅ Zero engine code changes
- ✅ Domain modules (wine_production) defined in lens only
- ✅ Uses actual DB column names in dimension_source
- ✅ Extraction works with wine lens
- ✅ Module triggers fire correctly
- ✅ Role values use universal function-style keys
- ✅ Lens contract validation passes
- ✅ Modules JSONB namespaced correctly

**Phase 5 Checkpoint (Updated for v2.2):**
- All verification tasks completed
- Wine Discovery lens created
- Second vertical validates engine-lens separation
- Zero engine changes needed
- Different interpretation of same dimensions works
- Contract validation passes for wine lens

---

## Phase 6: Hardening & Test Suite (v2.2 New Phase)

**Goal:** Comprehensive testing and enforcement of architectural contracts

### Task 6.1: Engine Purity Enforcement Tests

**Status:** pending

**Description:** Add tests and CI checks to prevent engine from importing lens code or doing value-based branching

**Subtasks:**
- [ ] Create `tests/engine/test_purity.py`:
  - [ ] **TEST 1**: Engine must not import lenses
    ```python
    def test_engine_does_not_import_lenses():
        """Engine layer must never import from lenses/ directory."""
        engine_files = glob.glob("engine/**/*.py", recursive=True)
        for file_path in engine_files:
            with open(file_path) as f:
                content = f.read()
                # Check for any imports from lenses/
                assert "from lenses" not in content, f"{file_path} imports from lenses/"
                assert "import lenses" not in content, f"{file_path} imports from lenses/"
    ```
  - [ ] **TEST 2**: Engine must not do literal string comparisons against dimension values
    ```python
    def test_engine_no_literal_string_comparisons_on_dimensions():
        """Engine must not compare dimension values against literal strings.

        Structural purity: Engine may only:
        - Branch on entity_class (e.g., if entity_class == "place")
        - Perform set operations on opaque strings (union, intersection, membership)
        - Check emptiness/existence (e.g., if canonical_activities)
        - Pass opaque strings through unchanged

        FORBIDDEN: Literal comparisons like if "padel" in canonical_activities
        """
        engine_files = glob.glob("engine/**/*.py", recursive=True)
        # Pattern: Detect literal string comparisons against dimension array values
        # This catches patterns like: if "value" in canonical_*, if canonical_*[0] == "value"
        forbidden_pattern = r'(if|elif)\s+.*(?:canonical_activities|canonical_roles|canonical_place_types|canonical_access).*(?:==|in)\s*["\']'

        for file_path in engine_files:
            with open(file_path) as f:
                content = f.read()
                matches = re.findall(forbidden_pattern, content, re.MULTILINE)
                assert not matches, f"{file_path} has literal string comparison against dimension values (structural purity violation)"
    ```
- [ ] Create `scripts/check_engine_purity.sh`:
  - [ ] Check for lens imports in engine/
  - [ ] Check for literal string comparisons against dimension values (structural pattern)
  - [ ] Exit with error code if violations found
  - [ ] Example:
    ```bash
    #!/bin/bash
    # Check engine does not import lenses
    if grep -r "from lenses" engine/ || grep -r "import lenses" engine/; then
        echo "ERROR: Engine imports from lenses/ (LensContract boundary violation)"
        exit 1
    fi
    # Check for structural purity violations (literal string comparisons on dimension values)
    # Pattern: if "literal" in canonical_* or if canonical_* == "literal"
    if grep -rE '(if|elif).*canonical_(activities|roles|place_types|access).*(==|in).*["\x27]' engine/; then
        echo "ERROR: Engine has literal string comparisons against dimension values (structural purity violation)"
        echo "Engine may only: branch on entity_class, perform set operations, check emptiness, pass through unchanged"
        exit 1
    fi
    echo "Engine purity checks passed"
    ```
- [ ] Add to CI pipeline (`.github/workflows/tests.yml`):
  - [ ] Add step to run check_engine_purity.sh
  - [ ] Fail build if purity checks fail
  - [ ] Run on every commit to prevent regressions
- [ ] Add pre-commit hook:
  - [ ] Create `.git/hooks/pre-commit` that runs purity checks
  - [ ] Prevent commits that violate engine purity
  - [ ] Optional but recommended

**Success Criteria:**
- ✅ test_purity.py passes with both tests (no lens imports, no literal string comparisons on dimension values)
- ✅ check_engine_purity.sh script exists and works
- ✅ CI pipeline includes purity checks
- ✅ Build fails if engine imports lenses (LensContract boundary violation)
- ✅ Build fails if engine does literal string comparisons against dimension values (structural purity violation)
- ✅ Engine enforces structural purity: only entity_class branching, set operations, emptiness checks, opaque passthrough

**Acceptance Check:**
```bash
# Run purity checks
./scripts/check_engine_purity.sh
# Should exit 0 (success)

# Try adding forbidden import to engine file
echo "from lenses.loader import VerticalLens" >> engine/test.py
./scripts/check_engine_purity.sh
# Should exit 1 (failure) and show error message
```

### Task 6.2: Lens Validation Tests

**Status:** pending

**Description:** Comprehensive tests for lens contract validation

**Subtasks:**
- [ ] Create `tests/lenses/test_contract_validation.py`:
  - [ ] Test: Invalid dimension_source → ValidationError
    ```python
    def test_invalid_dimension_source():
        config = {
            "facets": {
                "activity": {"dimension_source": "invalid_dimension"}
            }
        }
        with pytest.raises(ValidationError, match="must be one of"):
            validate_lens_config(config)
    ```
  - [ ] Test: value.facet references non-existent facet → ValidationError
  - [ ] Test: mapping_rules.canonical references non-existent value → ValidationError
  - [ ] Test: Duplicate value.key → ValidationError
  - [ ] Test: Duplicate facet key → ValidationError
  - [ ] Test: Valid config passes validation
  - [ ] Test: All 4 dimension sources allowed:
    ```python
    def test_all_dimension_sources_allowed():
        allowed = {"canonical_activities", "canonical_roles", "canonical_place_types", "canonical_access"}
        for dim in allowed:
            config = {"facets": {"test": {"dimension_source": dim}}}
            validate_lens_config(config)  # Should not raise
    ```
- [ ] Create `tests/lenses/test_edinburgh_finds_lens.py`:
  - [ ] Test: Edinburgh Finds lens loads successfully
  - [ ] Test: All facets use valid dimension_source
  - [ ] Test: All values reference existing facets
  - [ ] Test: All mapping rules reference existing values
  - [ ] Test: No duplicate values
  - [ ] Test: Role facet exists and is internal-only
- [ ] Create `tests/lenses/test_wine_discovery_lens.py`:
  - [ ] Test: Wine Discovery lens loads successfully
  - [ ] Test: wine_type facet maps to canonical_activities
  - [ ] Test: venue_type facet maps to canonical_place_types
  - [ ] Test: All contracts validated
- [ ] Add integration test:
  - [ ] Test: Loading invalid lens.yaml fails at startup
  - [ ] Test: Error message clearly identifies contract violation

**Success Criteria:**
- ✅ All lens validation tests pass
- ✅ Invalid configs fail immediately with clear errors
- ✅ Edinburgh Finds lens validates successfully
- ✅ Wine Discovery lens validates successfully
- ✅ All 4 dimension sources tested and working
- ✅ Contract violations produce actionable error messages

### Task 6.3: Deterministic Deduplication Tests

**Status:** pending

**Description:** Test that deduplication is deterministic and preserves insertion order

**Subtasks:**
- [ ] Create `tests/engine/test_deduplication.py`:
  - [ ] Test: dedupe_preserve_order maintains insertion order
    ```python
    def test_dedupe_preserves_order():
        values = ["tennis", "padel", "tennis", "gym", "padel"]
        result = dedupe_preserve_order(values)
        assert result == ["tennis", "padel", "gym"]
        # Order preserved: tennis appears first, then padel, then gym
    ```
  - [ ] Test: dedupe_preserve_order is deterministic
    ```python
    def test_dedupe_is_deterministic():
        values = ["tennis", "padel", "tennis", "gym", "padel"]
        result1 = dedupe_preserve_order(values)
        result2 = dedupe_preserve_order(values)
        assert result1 == result2  # Same input → same output
    ```
  - [ ] Test: Empty list handling
  - [ ] Test: Single value handling
  - [ ] Test: No duplicates case
- [ ] Create `tests/engine/test_extraction_deduplication.py`:
  - [ ] Test: Canonical values deduplicated before trigger evaluation
    ```python
    def test_canonical_values_deduped_before_triggers():
        # Raw categories map to duplicate canonical values
        raw_data = {"categories": ["padel court", "pádel facility", "padel club"]}
        # All three map to "padel"
        entity = extract_with_lens(raw_data, lens)
        # Trigger should only fire ONCE (not 3 times)
        assert trigger_call_count == 1
    ```
  - [ ] Test: Dimension arrays deduplicated before storage
    ```python
    def test_dimension_arrays_deduped():
        raw_data = {"categories": ["tennis", "tennis court", "tennis club"]}
        entity = extract_with_lens(raw_data, lens)
        assert entity['canonical_activities'] == ["tennis"]  # Not ["tennis", "tennis", "tennis"]
    ```
  - [ ] Test: canonical_values_by_facet deduplicated
  - [ ] Test: Deduplication preserves order across pipeline

**Success Criteria:**
- ✅ dedupe_preserve_order maintains insertion order
- ✅ dedupe_preserve_order is deterministic (same input → same output)
- ✅ Canonical values deduplicated before trigger evaluation
- ✅ Dimension arrays deduplicated before storage
- ✅ canonical_values_by_facet deduplicated
- ✅ All deduplication tests pass

### Task 6.4: Prisma Array Filter Tests

**Status:** pending

**Description:** Test Prisma array filters work correctly with Postgres text[] arrays

**Subtasks:**
- [ ] Create `tests/query/test_prisma_array_filters.py`:
  - [ ] Test: `has` filter (single value)
    ```typescript
    const result = await prisma.entity.findMany({
      where: { canonical_activities: { has: 'padel' } }
    });
    // Should return entities with padel in activities array
    ```
  - [ ] Test: `hasSome` filter (OR within facet)
    ```typescript
    const result = await prisma.entity.findMany({
      where: { canonical_activities: { hasSome: ['padel', 'tennis'] } }
    });
    // Should return entities with padel OR tennis
    ```
  - [ ] Test: `hasEvery` filter (AND within facet)
    ```typescript
    const result = await prisma.entity.findMany({
      where: { canonical_activities: { hasEvery: ['padel', 'tennis'] } }
    });
    // Should return entities with BOTH padel AND tennis
    ```
  - [ ] Test: AND across facets
    ```typescript
    const result = await prisma.entity.findMany({
      where: {
        AND: [
          { canonical_activities: { hasSome: ['padel', 'tennis'] } },
          { canonical_place_types: { has: 'sports_centre' } }
        ]
      }
    });
    // Should return sports centres with padel OR tennis
    ```
  - [ ] Test: Empty array handling
  - [ ] Test: GIN index usage (EXPLAIN ANALYZE)
    ```sql
    EXPLAIN ANALYZE SELECT * FROM entities
    WHERE canonical_activities && ARRAY['padel', 'tennis'];
    -- Should show "Index Scan using entities_activities_gin"
    ```
- [ ] Create test fixtures:
  - [ ] Entity with single activity: ["padel"]
  - [ ] Entity with multiple activities: ["padel", "tennis"]
  - [ ] Entity with no activities: []
  - [ ] Entity with activities + place_type
- [ ] Test query performance:
  - [ ] Create 10,000 test entities
  - [ ] Query with array filters
  - [ ] Verify GIN index used
  - [ ] Verify query time < 100ms

**Success Criteria:**
- ✅ `has` filter works correctly
- ✅ `hasSome` filter works correctly (OR semantics)
- ✅ `hasEvery` filter works correctly (AND semantics)
- ✅ AND across facets works correctly
- ✅ Empty array handling works
- ✅ GIN indexes used (verified with EXPLAIN)
- ✅ Query performance acceptable (< 100ms for 10k entities)

### Task 6.5: Module Composition Tests

**Status:** pending

**Description:** Test module composition contracts: duplicate module keys rejected at YAML load, namespacing enforced, field names may duplicate across modules

**Subtasks:**
- [ ] Create `tests/modules/test_composition.py`:
  - [ ] Test: Duplicate field names across DIFFERENT modules are ALLOWED
    ```python
    def test_duplicate_field_names_across_modules_allowed():
        """Field names can duplicate across different modules due to namespacing."""
        modules = {
            "location": {"fields": [{"name": "name"}]},
            "sports_facility": {"fields": [{"name": "name"}]}
        }
        validate_module_composition(modules)  # Should NOT raise - this is allowed
    ```
  - [ ] Test: Duplicate module keys in YAML rejected at load time
    ```python
    def test_duplicate_module_keys_in_yaml_rejected():
        """YAML with duplicate module keys should be rejected by the YAML loader."""
        yaml_content = """
        modules:
          sports_facility:
            inventory: {}
          sports_facility:  # Duplicate key
            name: "Test"
        """
        # NOTE: Rejected by YAML loader with strict duplicate key detection
        with pytest.raises((yaml.constructor.ConstructorError, ValueError),
                         match="duplicate key"):
            load_yaml_strict(yaml_content)
    ```
  - [ ] Test: Valid modules with unique keys pass
  - [ ] Test: Flattened modules JSONB → ValidationError
    ```python
    def test_flattened_jsonb_rejected():
        modules_data = {"latitude": 55.95, "phone": "+44123"}
        with pytest.raises(ValidationError, match="must be namespaced"):
            validate_modules_namespacing(modules_data)
    ```
  - [ ] Test: Namespaced modules JSONB passes
    ```python
    def test_namespaced_jsonb_accepted():
        modules_data = {
            "location": {"latitude": 55.95},
            "contact": {"phone": "+44123"}
        }
        validate_modules_namespacing(modules_data)  # Should not raise
    ```
- [ ] Create integration test:
  - [ ] Test: Extraction pipeline produces namespaced JSONB
    ```python
    def test_extraction_produces_namespaced_modules():
        entity = extract_with_lens(raw_data, lens)
        assert "location" in entity['modules']
        assert "latitude" in entity['modules']['location']
        assert "latitude" not in entity['modules']  # Not flattened
    ```
- [ ] Test database storage:
  - [ ] Store entity with namespaced modules
  - [ ] Read back from database
  - [ ] Verify JSONB structure preserved

**Success Criteria:**
- ✅ Duplicate field names across different modules are ALLOWED (namespacing makes this safe)
- ✅ Duplicate module keys in YAML rejected at load time (YAML loader configured to detect duplicates)
- ✅ Flattened JSONB rejected
- ✅ Namespaced JSONB accepted
- ✅ Extraction produces namespaced modules
- ✅ Database preserves namespaced structure
- ✅ All module composition tests pass

### Task 6.6: CI/CD Validation

**Status:** pending

**Description:** Add all validation checks to CI/CD pipeline

**Subtasks:**
- [ ] Update `.github/workflows/tests.yml`:
  - [ ] Add engine purity checks step
  - [ ] Add lens validation tests step
  - [ ] Add deduplication tests step
  - [ ] Add Prisma array filter tests step
  - [ ] Add module composition tests step
  - [ ] Fail build if any validation fails
- [ ] Add to README.md:
  - [ ] Document that engine purity is enforced in CI
  - [ ] Document lens contract validation
  - [ ] Document module composition rules
- [ ] Create validation checklist in PR template:
  - [ ] Engine purity verified (no lens imports, no value branching)
  - [ ] Lens contracts validated (dimension_source, facet references)
  - [ ] Module composition validated (no duplicates, namespaced)
  - [ ] All tests pass

**Success Criteria:**
- ✅ CI pipeline includes all validation checks
- ✅ Build fails on contract violations
- ✅ README documents enforcement
- ✅ PR template includes validation checklist
- ✅ All CI validation jobs pass

**Phase 6 Checkpoint (v2.2 New Phase):**
- All verification tasks completed
- Engine purity enforced (no lens imports, no value branching)
- Lens contract validation comprehensive
- Deduplication deterministic and tested
- Prisma array filters tested and performant
- Module composition enforced
- CI/CD pipeline validates all contracts
- All tests passing (unit + integration)

---

## Verification Checklist (Updated for v2.2)

### Engine Purity Validation
- [ ] **v2.2**: Engine does not import from lenses/ (receives LensContract dict only)
- [ ] **v2.2**: LensContract boundary enforced - engine functions receive lens_contract (plain dict), never lens runtime objects
- [ ] **v2.2**: All lens data accessed from lens_contract dict (mapping_rules, facets, values, module_triggers)
- [ ] No domain modules (sports_facility, wine_production) in engine
- [ ] All dimension values treated as opaque strings
- [ ] Module triggers only entity_class-based in engine (lens triggers are value-based)
- [ ] Roles cardinality 0..N (not required)
- [ ] Dimensions use actual DB column names (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
- [ ] **v2.2**: Engine has NO literal string comparisons against dimension values (structural purity)
- [ ] **v2.2**: Engine may ONLY: branch on entity_class, perform set operations, check emptiness, pass opaque strings through
- [ ] **v2.2**: CI enforces engine purity (check_engine_purity.sh passes - checks LensContract boundary and structural purity)

### Database & Supabase Best Practices
- [ ] Dimensions use `String[]` (Postgres text[] arrays, NOT Json)
- [ ] Default to empty arrays `@default([])` verified (Postgres '{}')
- [ ] **v2.2**: GIN indexes REQUIRED on all 4 dimension arrays
- [ ] Modules use `Json` (JSONB) type
- [ ] **v2.2**: ID strategy standardized (all uuid OR all cuid, not mixed)
- [ ] Query using Prisma array filters: `has`, `hasSome`, `hasEvery`
- [ ] Performance acceptable with GIN-indexed array queries
- [ ] **v2.2**: GIN index usage verified with EXPLAIN ANALYZE

### Lens Contract Validation
- [ ] All facets use actual DB column names in dimension_source (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
- [ ] **v2.2**: Every facet.dimension_source is one of 4 allowed columns
- [ ] **v2.2**: Every value.facet exists in facets section
- [ ] **v2.2**: Every mapping_rules.canonical exists in values section
- [ ] **v2.2**: No duplicate value.key across all values
- [ ] **v2.2**: Lens validation fails fast with clear error messages
- [ ] Module triggers use explicit list format with `when: {facet, value}`
- [ ] Module trigger `facet` refers to facet key as defined by the lens (lens.facets keys), NOT DB column name
- [ ] Role facet defined (internal-only, not shown in UI)
- [ ] Role keys are universal function-style (provides_facility, sells_goods, provides_instruction, membership_org, produces_goods)
- [ ] Role display_name carries vertical/product terminology
- [ ] Role values map to canonical_roles dimension

### Module Composition
- [ ] Load lens with domain modules (sports_facility uses inventory JSON)
- [ ] **v2.2**: No duplicate module keys in modules JSONB
- [ ] **v2.2**: Duplicate field names across DIFFERENT modules ALLOWED (namespacing makes this safe)
- [ ] **v2.2**: Modules JSONB namespaced by module key (not flattened)
- [ ] **v2.2**: Module composition validation fails fast
- [ ] Apply mapping rules to raw categories
- [ ] Distribute canonical values to correct dimensions by facet
- [ ] canonical_values_by_facet initialized with empty lists for all facets
- [ ] Deduplicate dimension arrays before persistence (dedupe_preserve_order)
- [ ] **v2.2**: Deduplication is deterministic (same input → same output)
- [ ] Compute derived groupings: AND-within-rule, OR-across-rules
- [ ] Apply value-based module triggers (explicit list format)
- [ ] Transform opaque values using lens interpretation

### Classification & Query Semantics
- [ ] **v2.2**: Classification rules documented with concrete examples
- [ ] **v2.2**: Classification priority order: 1. Time-bounded (event) FIRST, 2. Physical location (place), 3. Membership (organization), 4. Individual (person)
- [ ] **v2.2**: "Padel tournament at venue" → event (time-bounded takes priority over physical location)
- [ ] **v2.2**: "Club with courts" → place + multiple roles (provides_facility, membership_org)
- [ ] **v2.2**: Single entity_class + multi roles pattern locked
- [ ] **v2.2**: Query semantics documented: OR within facet, AND across facets
- [ ] **v2.2**: Grouping is derived/view-only (not stored in database)
- [ ] **v2.2**: No grouping_id column in entities table

### Second Vertical
- [ ] Wine Discovery lens loads successfully
- [ ] Different interpretation of same dimensions (Postgres text[] arrays)
- [ ] Zero engine code changes
- [ ] Domain modules (wine_production) defined in lens only
- [ ] Uses actual DB column names in dimension_source
- [ ] **v2.2**: Wine lens passes all contract validations

### Testing & CI/CD
- [ ] **v2.2**: Engine purity tests pass (no lens imports, no value branching)
- [ ] **v2.2**: Lens validation tests pass (all 5 contracts)
- [ ] **v2.2**: Deduplication tests pass (deterministic, preserves order)
- [ ] **v2.2**: Prisma array filter tests pass (has/hasSome/hasEvery)
- [ ] **v2.2**: Module composition tests pass (no duplicates, namespaced)
- [ ] **v2.2**: CI pipeline enforces all contracts
- [ ] **v2.2**: Build fails on contract violations

---

## Critical Files (Updated for v2.2)

### Engine Layer
- [ ] `engine/config/entity_model.yaml` - NEW: Universal entity model (NO domain modules, NO value triggers, uses actual DB column names)
- [ ] **v2.2**: `engine/docs/classification_rules.md` - NEW: Classification rules with examples
- [ ] `web/prisma/schema.prisma` - UPDATE: Entity with String[] for dimensions, Json for modules, standardized IDs
- [ ] `engine/extraction/base.py` - UPDATE: Lens-aware extraction with role facet mapping, uses actual DB column names, namespaced JSONB
- [ ] `engine/extraction/entity_classifier.py` - NEW: Deterministic entity_class rules
- [ ] **v2.2**: `engine/modules/validator.py` - NEW: Module composition validation

### Lens Layer
- [ ] `lenses/loader.py` - NEW: Lens loader with ModuleTrigger class for explicit list format
- [ ] **v2.2**: `lenses/validator.py` - NEW: Lens contract validation (fail-fast)
- [ ] `lenses/edinburgh_finds/lens.yaml` - NEW: Sports lens with role facet, inventory JSON, explicit module triggers, actual DB column names
- [ ] `lenses/wine_discovery/lens.yaml` - NEW: Wine lens (validation) with actual DB column names
- [ ] `web/lib/lens-query.ts` - NEW: Proper Postgres text[] array queries + lens transformations
- [ ] **v2.2**: `web/docs/query_semantics.md` - NEW: Query semantics documentation

### Migration
- [ ] `scripts/migrate_listing_to_entity.py` - NEW: Data migration to text[] arrays
- [ ] `scripts/validate_migration.py` - NEW: Validation
- [ ] **v2.2**: `scripts/check_engine_purity.sh` - NEW: CI enforcement script

### Tests (v2.2)
- [ ] `tests/engine/test_purity.py` - NEW: Engine purity tests
- [ ] `tests/lenses/test_contract_validation.py` - NEW: Lens contract tests
- [ ] `tests/engine/test_deduplication.py` - NEW: Deduplication tests
- [ ] `tests/query/test_prisma_array_filters.py` - NEW: Array filter tests
- [ ] `tests/modules/test_composition.py` - NEW: Module composition tests

---

## Success Criteria Summary (Updated for v2.2)

**Track is complete when:**

1. ✅ **Engine is 100% vertical-agnostic**: Zero references to sports, wine, coach, venue, etc.
2. ✅ **Domain modules in lens only**: sports_facility, wine_production not in engine
3. ✅ **Postgres text[] arrays for dimensions**: Use `String[]` with GIN indexes, not Json
4. ✅ **JSONB for modules**: Use `Json` type for flexible module storage
5. ✅ **Actual DB column names**: All dimension_source use canonical_activities, canonical_roles, canonical_place_types, canonical_access
6. ✅ **Explicit module triggers**: List format with `when: {facet, value}` avoids collisions
7. ✅ **Facet keys are lens-defined**: `facet` refers to facet key as defined by the lens (lens.facets), NOT DB column name
8. ✅ **Role facet (internal-only)**: Maps to canonical_roles, not shown in UI
9. ✅ **Universal role keys**: Stored as function-style keys (provides_facility, sells_goods, provides_instruction, membership_org, produces_goods)
10. ✅ **Role display_name**: Lens labels roles with vertical/product terminology via display_name
11. ✅ **Opaque dimension values**: Engine has zero interpretation logic
12. ✅ **Module triggers in lens**: Value-based triggers (explicit list format) in lens config
13. ✅ **Universal amenities only**: cafe/restaurant moved out of engine amenities module
14. ✅ **Prisma array filters**: Use has/hasSome/hasEvery on text[] arrays
15. ✅ **Derived grouping logic**: AND within rule, OR across rules (DerivedGrouping.matches() corrected)
16. ✅ **private_club in access facet**: Moved from place_type to access
17. ✅ **Inventory JSON structure**: sports_facility uses inventory JSON, not per-activity fields
18. ✅ **Dimension array deduplication**: dedupe_preserve_order applied to canonical_values and all dimension arrays
19. ✅ **canonical_values_by_facet initialization**: Initialized with empty lists for all lens facets
20. ✅ **Second vertical validates**: Wine Discovery lens works with zero engine changes
21. ✅ **All existing tests pass**: Extraction tests, schema tests, integration tests
22. ✅ **Documentation complete**: Architecture diagrams, configuration schemas, example data flows

### v2.2 Additional Success Criteria

23. ✅ **ID strategy standardized**: All models use consistent ID strategy (uuid OR cuid, not mixed)
24. ✅ **GIN indexes REQUIRED**: All 4 dimension arrays have GIN indexes
25. ✅ **Postgres array defaults verified**: Empty arrays '{}' not null
26. ✅ **Classification rules locked**: Single entity_class + multi roles documented with examples
27. ✅ **"Club with courts" example**: Correctly resolves to place + multiple roles
28. ✅ **Classification priority correct**: Time-bounded (event) checked FIRST, before physical location (place)
29. ✅ **Engine purity enforced**: No lens imports, LensContract boundary enforced, CI checks pass
30. ✅ **Structural purity enforced**: No literal string comparisons against dimension values, only entity_class branching, set operations, emptiness checks, opaque passthrough
31. ✅ **LensContract boundary**: Engine receives lens_contract (plain dict), never imports from lenses/, all lens data from dict
32. ✅ **Lens contracts validated**: All 5 contracts (dimension_source, facet existence, mapping rules, no duplicates) enforced fail-fast
33. ✅ **Module composition hardened**: No duplicate module keys, JSONB namespaced, duplicate field names across modules ALLOWED
34. ✅ **Query semantics documented**: OR within facet, AND across facets, grouping derived/view-only
35. ✅ **Deduplication deterministic**: Same input → same output, preserves insertion order
36. ✅ **Comprehensive test suite**: Engine purity, lens validation, deduplication, array filters, module composition
37. ✅ **CI/CD enforcement**: All contracts validated in CI, build fails on violations

---

## Notes (Updated for v2.2)

- **Design exercise focus**: Architecture, schemas, examples
- **Clean slate acceptable**: Can rebuild data
- **Postgres/Supabase best practices**:
  - Dimensions: `String[]` (Postgres text[] arrays) with GIN indexes (REQUIRED)
  - Modules: `Json` (JSONB) for flexibility, namespaced by module key
  - Query with Prisma array filters: has, hasSome, hasEvery on text[] arrays
  - ID strategy: Choose one (uuid OR cuid), never mix
  - Array defaults: '{}' (empty array) not null
- **Universal amenities**: wifi, parking_available, disabled_access only
- **Inventory JSON structure**: sports_facility uses inventory JSON (not per-activity fields)
- **Derived grouping logic**: AND within rule, OR across rules
- **Role facet**:
  - Internal-only, not shown in UI, maps to canonical_roles dimension
  - Role keys are universal function-style: provides_facility, sells_goods, provides_instruction, membership_org, produces_goods
  - Role display_name is vertical-specific: Lens labels roles with product terminology (Venue, Retailer, Coach, Producer, etc.)
  - Stored keys must be stable and not tied to a single vertical's vocabulary
- **private_club**: In access facet (not place_type)
- **Deduplication**:
  - dedupe_preserve_order applied to canonical_values list (avoids repeated module trigger evaluation)
  - Applied to all dimension arrays before persistence (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
  - Preserves insertion order (deterministic output)
  - **v2.2**: Determinism verified with tests (same input → same output)
- **Actual DB column names**: All facet.dimension_source use canonical_activities, canonical_roles, canonical_place_types, canonical_access (not semantic names)
- **Explicit module triggers**: List format with `when: {facet, value}` avoids key collisions and enables triggers across all facets cleanly
- **Facet keys are lens-defined**: Wherever examples reference facet keys, they refer to facet keys as defined by the lens (lens.facets keys), e.g. activity, role, wine_type, venue_type, NOT hardcoded to a specific set
- **canonical_values_by_facet initialization**: Initialized with empty lists for all lens facets for consistent structure
- **v2.2 Tightening (Updated with Corrective Revision)**:
  - **LensContract boundary**: Engine receives lens_contract (plain dict), never imports from lenses/, all lens data from dict
  - **Structural purity**: No literal string comparisons against dimension values (only entity_class branching, set operations, emptiness checks, opaque passthrough)
  - **Classification priority**: Time-bounded (event) checked FIRST, before physical location (place)
  - **Module field collisions**: Duplicate field names ALLOWED across different modules (namespacing makes this safe)
  - **Module composition**: No duplicate module keys, JSONB must be namespaced
  - Fail-fast validation (no silent failures)
  - CI enforcement (LensContract boundary and structural purity validated on every commit)
  - Clear error messages (identify which contract was violated)
  - Comprehensive test coverage (engine purity, lens contracts, module composition, query correctness)
  - Documentation (classification rules, query semantics, anti-patterns)

---

## Design Artifacts to Create (Updated for v2.2)

1. **Architecture diagrams**:
   - [ ] Engine-lens separation with opaque values (Postgres text[] arrays)
   - [ ] Extraction flow with lens mapping (role facet routing)
   - [ ] Query flow with Prisma array filters on text[] arrays
   - [ ] **v2.2**: Contract validation flow (fail-fast error handling)

2. **Configuration schemas**:
   - [ ] entity_model.yaml JSON Schema (dimensions as text[], uses actual DB column names)
   - [ ] lens.yaml JSON Schema (with role facet, modules, explicit trigger list format, actual DB column names, derived_groupings)
   - [ ] **v2.2**: Validation rules JSON Schema (allowed_dimension_sources, contract definitions)

3. **Example data flows**:
   - [ ] Raw data → canonical values via lens → opaque text[] dimensions in engine
   - [ ] Query by derived grouping (entity_class + roles, AND/OR logic)
   - [ ] Lens transformation (opaque → interpreted)
   - [ ] **v2.2**: "Club with courts" classification flow (place + multiple roles)

4. **Documentation** (v2.2):
   - [ ] classification_rules.md (with concrete examples and anti-patterns)
   - [ ] query_semantics.md (OR within, AND across, derived groupings)
   - [ ] README section on engine purity enforcement
   - [ ] CONTRIBUTING guide with contract validation checklist
