# Edinburgh Finds - Vision Document

**Last Updated:** 2026-01-28

**Purpose:** Define what success looks like for the intelligent ingestion engine.

---

## Core Vision

**An AI-scale discovery platform that captures RICH, domain-specific data across any vertical (Padel, Wine, Restaurants, Hiking) through intelligent multi-source orchestration, with zero engine code changes when adding new verticals.**

Success = Running a natural language query produces high-quality Entity records with:
- ✅ Correct universal classification (entity_class, roles)
- ✅ Rich domain-specific module data (equipment specs, wine varieties, menu items)
- ✅ Accurate location and contact information
- ✅ Deduplicated across sources (one entity, not five duplicates)

---

## The Core Architecture: Universal + Opaque + Modules

### Three-Layer Data Model

#### 1. Universal Fields (Engine-Defined)
Fields every entity has, regardless of vertical:

```
entity_class: "place" | "person" | "organization" | "event" | "thing"
entity_name: "Game4Padel Barnton Park"
slug: "game4padel-barnton-park"
summary: "Indoor padel facility with 6 courts..."
latitude: 55.9679631
longitude: -3.2790334
street_address: "12 Barnton Park, Edinburgh"
phone: "+44 131 XXX XXXX"
website_url: "https://game4padel.co.uk"
```

#### 2. Opaque Dimensions (Engine Stores, Lens Interprets)
Multi-valued arrays stored as PostgreSQL `text[]` with GIN indexes. **The engine treats these as completely opaque** - it stores string identifiers, lenses provide meaning:

```
canonical_activities: ["activity_padel", "activity_tennis"]
  ↓ Padel Lens interprets as:
  → "Padel" (primary activity)
  → "Tennis" (secondary activity)

canonical_place_types: ["facility_indoor_courts", "facility_membership_club"]
  ↓ Padel Lens interprets as:
  → "Indoor Sports Facility"
  → "Membership Club"

canonical_roles: ["provides_facility", "provides_instruction"]
  ↓ Universal (all lenses interpret same):
  → Venue provides equipment/facilities
  → Coaching/instruction available

canonical_access: ["access_pay_and_play", "access_membership"]
  ↓ Padel Lens interprets as:
  → "Pay & Play Available"
  → "Membership Options"
```

**Why opaque?** Adding Wine Discovery doesn't change the engine. Wine lens interprets `["activity_wine_tasting", "activity_retail"]` differently than Padel lens interprets `["activity_padel", "activity_tennis"]`, but the engine just stores strings.

#### 3. Domain Modules (JSONB, Lens-Triggered)
Rich, vertical-specific data in namespaced JSON:

**Padel Venue:**
```json
{
  "modules": {
    "sports_facility": {
      "equipment": [
        {
          "type": "padel_court",
          "count": 4,
          "surface": "artificial_turf",
          "indoor": true,
          "dimensions": "20m x 10m",
          "lighting": "LED",
          "booking_required": true
        },
        {
          "type": "padel_court",
          "count": 2,
          "surface": "artificial_turf",
          "indoor": false,
          "floodlit": true
        }
      ],
      "changing_rooms": true,
      "equipment_rental": ["rackets", "balls"],
      "booking_system": "courtside",
      "peak_pricing": {"weekday": "£40/hr", "weekend": "£50/hr"},
      "membership_options": {
        "individual_monthly": "£60",
        "family_annual": "£600"
      },
      "coaching": {
        "available": true,
        "types": ["group", "1-on-1", "kids"],
        "price_range": "£25-60/session"
      }
    }
  }
}
```

**Winery:**
```json
{
  "modules": {
    "wine_production": {
      "grape_varieties": ["pinot_noir", "chardonnay", "riesling"],
      "wine_styles": ["sparkling", "still_white", "still_red"],
      "production_method": "traditional_method",
      "vineyard_size_acres": 12.5,
      "annual_production_bottles": 15000,
      "tasting_room": {
        "available": true,
        "booking_required": true,
        "tasting_fee": "£15 (redeemable on purchase)",
        "group_size": "2-12 people"
      },
      "retail": {
        "on_site": true,
        "online": true,
        "price_range": "£18-45/bottle"
      },
      "tours": {
        "available": true,
        "duration_mins": 90,
        "includes_tasting": true,
        "price": "£25/person"
      }
    }
  }
}
```

**Restaurant:**
```json
{
  "modules": {
    "food_service": {
      "cuisine_types": ["italian", "mediterranean"],
      "menu_highlights": ["handmade_pasta", "wood_fired_pizza"],
      "dietary_options": ["vegetarian", "vegan", "gluten_free"],
      "price_range": "££" (1-4 scale),
      "seating_capacity": 60,
      "reservations": {
        "required": false,
        "recommended_for": "weekend_dinner",
        "booking_system": "opentable"
      },
      "service_style": "table_service",
      "alcohol_license": true,
      "outdoor_seating": {
        "available": true,
        "capacity": 20,
        "heated": true
      }
    }
  }
}
```

---

## What "Success" Looks Like

### Running a Query

```bash
python -m engine.orchestration.cli run "padel courts edinburgh" --persist
```

### Expected Entity Table Results

**Quantity:**
- 50-200 entities discovered
- 80%+ are `entity_class='place'` (correctly classified)
- <5% duplicates (effective deduplication)

**Universal Data Quality:**
```sql
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN entity_class = 'place' THEN 1 END) as places,
  COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as with_coords,
  COUNT(CASE WHEN array_length(canonical_activities, 1) > 0 THEN 1 END) as with_activities,
  COUNT(CASE WHEN phone IS NOT NULL OR website_url IS NOT NULL THEN 1 END) as with_contact
FROM "Entity";
```

**Target Coverage:**
- `places`: 95%+ (correct classification)
- `with_coords`: 85%+ (geocoded)
- `with_activities`: 75%+ (activities identified)
- `with_contact`: 70%+ (phone or website)

**Module Data Quality (THE DIFFERENTIATOR):**
```sql
SELECT
  COUNT(CASE WHEN modules ? 'sports_facility' THEN 1 END) as with_sports_module,
  COUNT(CASE WHEN modules->'sports_facility' ? 'equipment' THEN 1 END) as with_equipment_detail
FROM "Entity"
WHERE entity_class = 'place';
```

**Target Coverage:**
- `with_sports_module`: 60%+ (rich domain data captured)
- `with_equipment_detail`: 40%+ (deep specs available)

### Sample "Good" Entity

```json
{
  "entity_id": "cm4abc123",
  "entity_name": "Game4Padel Barnton Park",
  "slug": "game4padel-barnton-park",
  "entity_class": "place",
  "summary": "Indoor padel facility with 6 courts offering pay-and-play and membership options. Coaching available for all levels.",

  "canonical_activities": ["activity_padel", "activity_tennis"],
  "canonical_roles": ["provides_facility", "provides_instruction", "membership_org"],
  "canonical_place_types": ["facility_indoor_courts", "facility_membership_club"],
  "canonical_access": ["access_pay_and_play", "access_membership"],

  "latitude": 55.9679631,
  "longitude": -3.2790334,
  "street_address": "12 Barnton Park",
  "city": "Edinburgh",
  "postcode": "EH4 6JF",
  "country": "UK",

  "phone": "+44 131 XXX XXXX",
  "email": "info@game4padel.co.uk",
  "website_url": "https://game4padel.co.uk",
  "instagram_url": "https://instagram.com/game4padel",

  "opening_hours": {
    "monday": {"open": "06:00", "close": "23:00"},
    "tuesday": {"open": "06:00", "close": "23:00"},
    "wednesday": {"open": "06:00", "close": "23:00"},
    "thursday": {"open": "06:00", "close": "23:00"},
    "friday": {"open": "06:00", "close": "23:00"},
    "saturday": {"open": "08:00", "close": "22:00"},
    "sunday": {"open": "08:00", "close": "22:00"}
  },

  "modules": {
    "sports_facility": {
      "equipment": [
        {"type": "padel_court", "count": 4, "indoor": true, "surface": "artificial_turf"},
        {"type": "padel_court", "count": 2, "indoor": false, "floodlit": true}
      ],
      "changing_rooms": true,
      "equipment_rental": ["rackets", "balls"],
      "booking_system": "courtside",
      "coaching_available": true
    }
  },

  "source_info": {
    "discovered_by": ["google_places", "sport_scotland"],
    "primary_source": "google_places",
    "verified_date": "2026-01-28"
  },

  "external_ids": {
    "google_places": "ChIJabcdef123456",
    "sport_scotland": "EH-PADEL-001"
  }
}
```

This is a **10/10 entity** - perfect classification, rich modules, complete contact info, hours, multiple source verification.

### Sample "Bad" Entity (Current Reality)

```json
{
  "entity_id": "cm4xyz789",
  "entity_name": "Game4Padel Barnton Park",
  "slug": "game4padel-barnton-park",
  "entity_class": "thing",  // ❌ WRONG - should be "place"
  "summary": null,

  "canonical_activities": [],  // ❌ EMPTY - should have padel
  "canonical_roles": [],  // ❌ EMPTY - should have provides_facility
  "canonical_place_types": [],
  "canonical_access": [],

  "latitude": 55.9679631,  // ✅ Good
  "longitude": -3.2790334,  // ✅ Good
  "street_address": "12 Barnton Park, Edinburgh EH4 6JF, UK",  // ✅ Good
  "city": null,  // ⚠️ Missing - should parse from address
  "postcode": null,  // ⚠️ Missing

  "phone": null,  // ❌ Missing
  "website_url": null,  // ❌ Missing

  "modules": {}  // ❌ EMPTY - should have sports_facility
}
```

This is a **3/10 entity** - has location but everything else is broken.

---

## How Lenses Enable This

### Lens Responsibilities

**1. Query Interpretation** (`query_vocabulary.yaml`)
Define domain-specific keywords so engine can detect intent:

```yaml
activity_keywords:
  - padel
  - tennis
  - squash
  - court

location_indicators:
  - edinburgh
  - leith
  - portobello

facility_keywords:
  - centre
  - facility
  - venue
  - club
```

**2. Connector Routing** (`connector_rules.yaml`)
Tell orchestrator which data sources are relevant:

```yaml
connectors:
  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [padel, tennis, squash, football]
        threshold: 1
      - type: facility_search
        keywords: [centre, facility, court]
        location_required: true
```

**3. Value Interpretation** (in lens code/config)
Map opaque dimension values to display labels:

```yaml
dimension_labels:
  canonical_activities:
    activity_padel: "Padel"
    activity_tennis: "Tennis"
  canonical_place_types:
    facility_indoor_courts: "Indoor Sports Facility"
    facility_outdoor_courts: "Outdoor Courts"
```

**4. Module Schema Definition** (in lens config)
Define what rich data to extract for this vertical:

```yaml
module_schemas:
  sports_facility:
    equipment:
      - type: string (e.g., "padel_court", "tennis_court")
      - count: integer
      - surface: string
      - indoor: boolean
    coaching_available: boolean
    booking_system: string
```

### Why This Enables Horizontal Scaling

**Adding Wine Discovery:**
1. Create `engine/lenses/wine/query_vocabulary.yaml`
2. Create `engine/lenses/wine/connector_rules.yaml`
3. Define wine module schema (wine_production, retail, tasting_room)
4. **DONE** - Zero engine code changes

Wine queries automatically:
- Use wine vocabulary for query analysis
- Route to wine-specific connectors (Wine Searcher API)
- Extract wine-specific modules (grape varieties, tasting options)
- Display through wine lens interpretation

---

## Intelligent Orchestration

### Query Analysis → Connector Selection

**Query:** "padel courts edinburgh"

**Step 1: Feature Detection** (using Padel lens vocabulary)
```python
QueryFeatures:
  looks_like_category_search: True  # "courts" is generic, not specific venue
  has_geo_intent: True  # "edinburgh" detected
  activity: "padel"  # From lens activity_keywords
```

**Step 2: Connector Selection** (using lens rules + registry)
```python
Selected Connectors:
  Phase 1 (Discovery - free/cheap):
    - serper (base, $0.002/query)
    - openstreetmap (base, free)
    - edinburgh_council (geo-specific, free)
    - sport_scotland (lens-triggered, free)  # ← Lens added this!

  Phase 2 (Enrichment - paid):
    - google_places (base, $0.017/query)
```

**Step 3: Execution** (ordered by cost, early stopping if sufficient results)

**Step 4: Extraction** (connector-specific extractors)
- Serper → LLM extraction from search snippets
- Google Places → Structured API response mapping
- Sport Scotland → WFS geographic layer parsing
- Each produces: ExtractedEntity records

**Step 5: Deduplication** (cross-source)
- External ID matching: "ChIJabc..." from Google = "EH-PAD-001" from Sport Scotland? (no)
- Slug matching: "game4padel-barnton-park" = "game4padel-barnton-park"? (yes!)
- Fuzzy matching: Name similarity + distance < 50m? (yes)
- **Merge into ONE entity**

**Step 6: Merging** (trust hierarchy resolves conflicts)
```
Field: equipment_count
  - Google Places: null
  - Sport Scotland: 6 courts (trust: official)
  → Winner: Sport Scotland (6 courts)

Field: website_url
  - Google Places: "https://game4padel.co.uk" (trust: crowdsourced)
  - Sport Scotland: null
  → Winner: Google Places
```

**Step 7: Finalization**
- Generate slug from name
- Classify entity (place/person/org/event/thing)
- Upsert to Entity table (idempotent)

---

## Data Quality Standards

### Universal Data (All Entities)

**MUST HAVE (100% required):**
- ✅ `entity_name` (never "Unknown")
- ✅ `slug` (auto-generated, unique)
- ✅ `entity_class` (correctly classified)

**SHOULD HAVE (80%+ target):**
- ✅ Coordinates (`latitude`, `longitude`) for places
- ✅ Address (at minimum: `city` or `street_address`)
- ✅ At least one activity in `canonical_activities`
- ✅ At least one contact method (`phone` or `website_url`)

**NICE TO HAVE (50%+ target):**
- ✅ `summary` (brief description)
- ✅ `opening_hours`
- ✅ `canonical_roles` populated
- ✅ Social media links

### Module Data (The Value Proposition)

**For Sports Facilities (Padel lens):**

**MUST HAVE (60%+ of sports venues):**
- ✅ `modules.sports_facility` exists
- ✅ `equipment` array has at least one entry

**SHOULD HAVE (40%+ of sports venues):**
- ✅ Equipment details: type, count, surface, indoor/outdoor
- ✅ Booking info: system, pricing, membership options

**NICE TO HAVE (20%+ of sports venues):**
- ✅ Coaching details: types, pricing
- ✅ Amenities: changing rooms, showers, parking
- ✅ Special features: disability access, cafe, pro shop

**For Wineries (Wine lens):**

**MUST HAVE (60%+ of wineries):**
- ✅ `modules.wine_production` exists
- ✅ `grape_varieties` or `wine_styles` populated

**SHOULD HAVE (40%+ of wineries):**
- ✅ Tasting room info (availability, booking, pricing)
- ✅ Retail info (on-site, online, price range)

**NICE TO HAVE (20%+ of wineries):**
- ✅ Production details: method, annual output, vineyard size
- ✅ Tour details: duration, pricing, what's included

### Deduplication Quality

**Zero Tolerance:**
- ❌ Same entity with same slug appearing twice (critical bug)
- ❌ External IDs not matched (Google Place ID should dedupe)

**Acceptable:**
- ⚠️ Different branches of same chain (e.g., "David Lloyd Edinburgh" vs "David Lloyd Leith") showing as separate (they ARE separate places)
- ⚠️ 5% false negatives (two records that should merge but don't)

**Not Acceptable:**
- ❌ 10%+ false positives (merging different entities)
- ❌ Lost data in merges (fields disappearing after deduplication)

---

## Current State: Gaps Analysis

### Critical Gaps (Blocking)

**1. Classification Broken**
- **Problem:** 95% of entities are `entity_class="thing"` instead of `"place"`
- **Root Cause:** `classify_entity()` requires `location_lat`/`location_lng` but connectors provide `latitude`/`longitude`
- **Impact:** Frontend can't filter by entity type, entities unusable
- **Priority:** P0 - must fix first

**2. Activities Not Extracted**
- **Problem:** `canonical_activities` is empty for 100% of entities
- **Root Cause:** Extractors don't populate activities from connector data
- **Impact:** Can't filter by activity ("show me padel only"), lens routing broken
- **Priority:** P0 - must fix first

**3. Modules Completely Empty**
- **Problem:** `modules` is `{}` for 100% of entities
- **Root Cause:** No module extraction logic exists
- **Impact:** No rich data, no value proposition, just basic listings
- **Priority:** P0 - this is THE differentiator

**4. Field Name Inconsistency**
- **Problem:** Connectors use different field names (`latitude` vs `location_lat`)
- **Root Cause:** No standard extraction contract
- **Impact:** EntityFinalizer can't find data, fields are NULL
- **Priority:** P0 - data loss

### Important Gaps (Degraded Experience)

**5. Roles Not Populated**
- **Problem:** `canonical_roles` is empty
- **Root Cause:** `extract_roles()` checks for fields extractors don't populate
- **Priority:** P1

**6. No Serper Extractor**
- **Problem:** Serper results fail to persist (7 failures per query)
- **Root Cause:** Missing `engine/extraction/extractors/serper.py`
- **Priority:** P1

**7. Poor Deduplication**
- **Problem:** Duplicate entities slipping through
- **Root Cause:** Slug matching works, but fuzzy matching may be too strict
- **Priority:** P1

### Nice-to-Have Gaps

**8. Contact Info Coverage Low**
- **Problem:** Only 30% have phone/website
- **Root Cause:** Google Places doesn't always provide, other sources don't extract
- **Priority:** P2

**9. Opening Hours Rarely Captured**
- **Problem:** <10% have opening_hours populated
- **Root Cause:** Complex to parse, not all sources provide
- **Priority:** P2

---

## Priority Order: What to Fix

### Phase 1: Make Entities Usable (P0 - Blocking)

**Goal:** Get to 7/10 entity quality

1. **Fix field name standardization**
   - Define extraction contract: what fields MUST extractors output?
   - Update all extractors to output standard fields
   - Success: latitude/longitude/address/name consistent across all connectors

2. **Fix entity classification**
   - Classify correctly: places are "place", not "thing"
   - Success: 95%+ entities correctly classified

3. **Extract activities**
   - Populate canonical_activities from raw data
   - Success: 75%+ entities have at least one activity

4. **Extract basic modules**
   - For sports facilities: capture equipment type and count
   - Success: 40%+ sports venues have sports_facility module with equipment

### Phase 2: Rich Module Data (P0 - Differentiator)

**Goal:** Get to 9/10 entity quality

5. **Deep sports facility extraction**
   - Equipment details: surface, indoor/outdoor, lighting
   - Booking info: system, pricing
   - Success: 60%+ sports venues have rich equipment details

6. **Coaching/instruction extraction**
   - Detect coaching availability, types, pricing
   - Populate canonical_roles with "provides_instruction"
   - Success: 40%+ relevant venues have coaching info

7. **Contact info extraction**
   - Phone numbers (E.164 format)
   - Website URLs (validated)
   - Social media (Instagram, Facebook)
   - Success: 70%+ have phone or website

### Phase 3: Robustness (P1)

8. **Add missing extractors** (Serper, Sport Scotland improvements)
9. **Improve deduplication** (reduce false negatives)
10. **Extract opening hours** (structured JSON)

---

## How to Validate Changes

### Before Making ANY Code Changes

**1. Establish Baseline**

Clear Entity table:
```sql
DELETE FROM "Entity";
```

Run baseline query:
```bash
python -m engine.orchestration.cli run "padel courts edinburgh" --persist
```

Capture metrics:
```sql
-- Baseline Metrics
SELECT
  COUNT(*) as total_entities,
  COUNT(CASE WHEN entity_class = 'place' THEN 1 END) as classified_as_place,
  COUNT(CASE WHEN entity_class = 'thing' THEN 1 END) as classified_as_thing,
  COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as with_coordinates,
  COUNT(CASE WHEN array_length(canonical_activities, 1) > 0 THEN 1 END) as with_activities,
  COUNT(CASE WHEN modules != '{}' THEN 1 END) as with_modules,
  COUNT(CASE WHEN modules ? 'sports_facility' THEN 1 END) as with_sports_module
FROM "Entity";
```

Sample inspection:
```sql
SELECT entity_name, entity_class, canonical_activities, modules
FROM "Entity"
LIMIT 5;
```

**Record these numbers!** This is your "before" state.

### After Making Changes

**2. Validate Improvement**

Clear Entity table again:
```sql
DELETE FROM "Entity";
```

Re-run same query:
```bash
python -m engine.orchestration.cli run "padel courts edinburgh" --persist
```

Capture same metrics, compare:
```
Metric                  | Before | After | Change
------------------------|--------|-------|--------
classified_as_place     |   5%   |  95%  | +90% ✅
with_activities         |   0%   |  75%  | +75% ✅
with_modules            |   0%   |  40%  | +40% ✅
with_sports_module      |   0%   |  60%  | +60% ✅
```

**3. Inspect Sample Entities**

Pick random entities and inspect quality:
```sql
SELECT entity_name, entity_class, canonical_activities, latitude, longitude, modules
FROM "Entity"
WHERE entity_class = 'place'
ORDER BY RANDOM()
LIMIT 3;
```

Does the data LOOK correct? Are modules populated? Is classification right?

### Definition of Success

**A change is successful if:**
- ✅ Target metrics improved (more places, more activities, more modules)
- ✅ No regressions (didn't break something else)
- ✅ Sample entities look correct when manually inspected
- ✅ Tests pass with REAL connector data (not mock data)

**A change FAILED if:**
- ❌ Metrics stayed same or got worse
- ❌ Tests pass but Entity table still has bad data
- ❌ Only works with test data, not real queries

---

## Guiding Principles

### 1. Rich Data Over Quantity
100 entities with full modules > 500 entities with just name/address

### 2. Reality Over Tests
Validate with real queries, real connectors, real Entity table inspection.
Tests that pass with mock data but fail with real connectors are WORSE than no tests.

### 3. Outcomes Over Architecture
Success = "Entity table has 9/10 quality data"
NOT = "tests pass" or "code is elegant" or "followed TDD"

### 4. Incremental Over Big Bang
Fix ONE gap (e.g., classification).
Validate end-to-end (run query, check Entity table).
THEN fix next gap.

### 5. Modules Are The Moat
Basic listings (name/address/phone) are commoditized.
Rich modules (equipment specs, pricing, booking details) are the unique value.

### 6. Configuration Over Code
Adding Wine should require:
- 2 YAML files (query_vocabulary, connector_rules)
- 1 module schema definition
- 0 Python code changes

### 7. Opaque By Design
Engine stores `["activity_x", "activity_y"]` without knowing what "x" means.
Lenses interpret. This enables infinite horizontal scaling.

---

**This vision document is the reference for all future plans.**

Every plan should:
1. ✅ Reference which gap it's fixing (use the numbered list above)
2. ✅ Define success criteria (specific Entity table metrics)
3. ✅ Include before/after validation (run query, compare results)
4. ✅ Focus on outcomes (data quality) not process (tests passing)
5. ✅ Be small (3-5 tasks max, fix ONE specific thing)
