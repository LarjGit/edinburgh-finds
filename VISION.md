# Edinburgh Finds - System Vision

**Last Updated:** 2026-01-28

**Purpose:** Define what success looks like for the complete Edinburgh Finds discovery platform - from natural language query to rich, accurate entity data.

---

## Core Vision

**A horizontal, vertical-agnostic entity extraction engine that transforms natural language queries into complete, accurate entity records through AI-powered multi-source orchestration. The engine is universal - all vertical-specific logic lives in pluggable lens configurations.**

**Edinburgh Finds** is the first vertical lens - an Edinburgh-centric discovery platform for venues, retailers, clubs, events, and coaches - used to prove the system's vertical independence and completeness.

### What This Means

**Universal Engine:**
- Vertical-agnostic architecture: the engine knows nothing about "Padel", "Wine", or domain concepts
- All entities stored as universal `entity_class` (place, person, organization, event, thing)
- Multi-valued dimensions (`canonical_activities`, `canonical_categories`) stored as opaque arrays
- Vertical-specific data lives in JSON `modules`, interpreted by lenses

**Lens Layer (Edinburgh Finds is first):**
- YAML configuration defines domain vocabulary, connector routing, field schemas
- Adding new verticals (Wine Discovery, Restaurant Finder) requires ZERO engine code changes
- Each lens provides query interpretation, data source selection, and display logic

**Infinite Connector Extensibility:**
- Current prototype: 6 connectors (Serper, Google Places, OpenStreetMap, Sport Scotland, Edinburgh Council, Open Charge Map)
- System designed for unlimited connector growth as verticals expand
- **New verticals need new sources:** Wine Discovery adds Vivino, Wine-Searcher, Decanter APIs
- **Existing verticals get enriched:** Edinburgh Finds adds TripAdvisor, Yelp, VisitScotland, Edinburgh Leisure API
- **Connector registry** (`engine/orchestration/registry.py`) provides pluggable architecture - new sources integrate via standardized interface
- Each connector self-describes: cost tier, trust level, orchestration phase, timeout, capabilities

**End-to-End Flow:**

Users ask questions in natural language:
- **Single entity lookup:** "powerleague portobello" → detailed venue record with all facilities
- **General discovery:** "padel courts edinburgh" → all venues offering padel
- **Category search:** "sports facilities with swimming pools" → filtered results

The system automatically:
- **Interprets** the query using lens vocabulary (what are they looking for?)
- **Orchestrates** intelligent data gathering using lens connector rules (which sources to use?)
- **Extracts** structured data from multiple sources using hybrid deterministic + LLM extraction
- **Deduplicates** cross-source matches (same entity from Google, OSM, domain APIs)
- **Merges** conflicting data using trust hierarchies and field-level confidence
- **Finalizes** unified entities with slug generation and entity_class classification
- **Delivers** complete, rich entity records to database

**Success Criteria:**

Entity records that are **complete** (all available data populated, exceptions tracked) and **accurate** (correctly classified, no hallucinations, proper deduplication).

---

## The Three-Layer Architecture

Edinburgh Finds uses a universal data model that separates what the engine stores from how the lens interprets it.

### Layer 1: Universal Fields (Engine-Defined)

Fields every entity has, regardless of vertical:

```
entity_name: "Craiglockhart Sports Centre"
entity_class: "place"
slug: "craiglockhart-sports-centre"
summary: "Multi-sport facility offering tennis, swimming, gym and spa facilities"

latitude: 55.920654
longitude: -3.237891
street_address: "177 Colinton Road"
city: "Edinburgh"
postcode: "EH14 1BZ"
country: "UK"

phone: "+441314447100"
email: "info@craiglockhart.com"
website_url: "https://www.edinburghleisure.co.uk/venues/craiglockhart"
instagram_url: "https://instagram.com/edinburghleisure"
facebook_url: "https://facebook.com/craiglockhartsports"

opening_hours: {
  "monday": {"open": "06:00", "close": "22:00"},
  "tuesday": {"open": "06:00", "close": "22:00"},
  ...
}

source_info: {
  "discovered_by": ["google_places", "edinburgh_leisure_api"],
  "verified_date": "2026-01-28"
}

external_ids: {
  "google_places": "ChIJabcdef123456",
  "edinburgh_leisure": "CRAIG-001"
}
```

### Layer 2: Opaque Dimensions (Engine Stores, Lens Interprets)

Multi-valued arrays stored as PostgreSQL `text[]`. **The engine treats these as opaque** - it stores string identifiers, the Edinburgh Finds lens provides human-readable interpretation:

```
categories: ["Sports Centre", "Swimming Pool", "Gym"]
  ↓ Edinburgh Finds lens interprets as:
  → Navigation taxonomy
  → Search filters
  → Display labels

canonical_categories: ["sports_facility", "swimming_pool", "gym"]
  ↓ Controlled vocabulary for:
  → Consistent categorization
  → Cross-source matching
  → Faceted search
```

**Design Question:** Should lenses also be responsible for populating these opaque dimensions? Or should the engine extract them generically and lenses just interpret?

### Layer 3: Rich Vertical Data (Venue-Specific Fields)

Edinburgh Finds "Venue" entities have comprehensive facility data:

#### Racquet Sports
```
tennis_summary: "8 indoor courts and 4 outdoor clay courts"
tennis: true
tennis_total_courts: 12
tennis_indoor_courts: 8
tennis_outdoor_courts: 4
tennis_covered_courts: 8
tennis_floodlit_courts: 4

padel_summary: "4 indoor courts available for pay-and-play"
padel: true
padel_total_courts: 4

pickleball_summary: "2 dedicated pickleball courts"
pickleball: true
pickleball_total_courts: 2

badminton_summary: "6 courts available for casual play and league matches"
badminton: true
badminton_total_courts: 6

squash_summary: "3 courts including 1 glass-back court"
squash: true
squash_total_courts: 3
squash_glass_back_courts: 1

table_tennis_summary: "2 tables in dedicated area"
table_tennis: true
table_tennis_total_tables: 2
```

#### Football
```
football_summary: "Multiple pitch sizes for 5-a-side, 7-a-side and full 11-a-side matches"
football_5_a_side: true
football_5_a_side_total_pitches: 4
football_7_a_side: true
football_7_a_side_total_pitches: 2
football_11_a_side: true
football_11_a_side_total_pitches: 1
```

#### Swimming
```
swimming_summary: "25m indoor pool with separate learner pool"
indoor_pool: true
indoor_pool_length_m: 25
outdoor_pool: false
outdoor_pool_length_m: null
family_swim: true
adult_only_swim: true
swimming_lessons: true
```

#### Gym & Classes
```
gym_summary: "120-station gym with modern equipment"
gym_available: true
gym_size: 120
classes_summary: "60+ classes per week including yoga, HIIT, spin, pilates and strength"
classes_per_week: 60
hiit_classes: true
yoga_classes: true
pilates_classes: true
strength_classes: true
cycling_studio: true
functional_training_zone: true
```

#### Spa & Wellness
```
spa_summary: "Full spa with sauna, steam room and hydro pool"
spa_available: true
sauna: true
steam_room: true
hydro_pool: true
hot_tub: false
outdoor_spa: false
ice_cold_plunge: true
relaxation_area: true
```

#### Dining & Amenities
```
amenities_summary: "Cafe serving healthy snacks and smoothies"
restaurant: false
bar: false
cafe: true
childrens_menu: false
wifi: true
```

#### Family & Kids
```
family_summary: "Creche available, kids swimming and tennis lessons"
creche_available: true
creche_age_min: 6
creche_age_max: 12
kids_swimming_lessons: true
kids_tennis_lessons: true
holiday_club: true
play_area: false
```

#### Parking & Transport
```
parking_and_transport_summary: "80 spaces including disabled parking, bus routes nearby"
parking_spaces: 80
disabled_parking: true
parent_child_parking: true
ev_charging_available: true
ev_charging_connectors: 4
public_transport_nearby: true
nearest_railway_station: "Slateford"
```

#### Reviews & Social Proof
```
reviews_summary: "4.2 stars from 340 Google reviews"
average_rating: 4.2
review_count: 340
google_review_count: 340
facebook_likes: 1250
```

This is what makes Edinburgh Finds valuable - **complete facility data, not just name and address**.

---

## What Success Looks Like

### Complete Data with Exception Management

**Principle:** ALL available data should be populated. Empty fields should be exceptions with tracked reasons, not arbitrary coverage targets.

For a venue like Craiglockhart Sports Centre:

**Universal Fields:**
- ✅ All fields populated (name, address, coordinates, contact, hours)
- ✅ Multiple contact methods (phone, email, website, social media)
- ✅ Opening hours captured as structured JSON
- ✅ Source provenance tracked
- ⚠️ Exception: twitter_url null (venue doesn't have Twitter) - ACCEPTABLE

**Venue-Specific Fields:**
- ✅ All sports offered correctly identified (tennis, swimming, gym, spa)
- ✅ Quantitative data captured (court counts, pool length, gym size)
- ✅ Facility details complete (indoor/outdoor, surfaces, lighting)
- ✅ Amenities and services listed (creche, cafe, parking)
- ✅ Reviews and ratings captured
- ⚠️ Exception: outdoor_pool null (doesn't have one) - ACCEPTABLE
- ❌ Exception: padel_total_courts null but padel exists (data loss) - NOT ACCEPTABLE

**Exception Categories:**
1. **Facility Doesn't Exist** (outdoor_pool = null for indoor-only venue) → ACCEPTABLE
2. **Data Not Available from Sources** (reviews not provided by API) → TRACK & IMPROVE
3. **Extraction Failed** (LLM missed court count in description) → BUG, MUST FIX
4. **Data Quality Issue** (conflicting counts from different sources) → MERGE LOGIC NEEDED

### Classification Accuracy

**Entity Class (Universal):**
- ✅ Venues correctly classified as entity_class "place"
- ✅ Events correctly classified as entity_class "event"
- ✅ Coaches correctly classified as entity_class "person"
- ✅ Clubs correctly classified as entity_class "organization"
- ✅ Products/Equipment correctly classified as entity_class "thing" (e.g., specific racquet models, equipment rentals)

**No arbitrary percentages** - the goal is 100% accuracy with exceptions tracked and justified.

### Sample "Complete" Entity

```json
{
  "entity_name": "Craiglockhart Sports Centre",
  "entity_class": "place",
  "slug": "craiglockhart-sports-centre",
  "summary": "Multi-sport facility in South Edinburgh offering tennis, swimming, gym, and spa facilities with extensive class programs",

  "categories": ["Sports Centre", "Swimming Pool", "Gym", "Tennis Club"],
  "canonical_categories": ["sports_facility", "swimming_pool", "gym", "tennis_facility"],

  "latitude": 55.920654,
  "longitude": -3.237891,
  "street_address": "177 Colinton Road",
  "city": "Edinburgh",
  "postcode": "EH14 1BZ",
  "country": "UK",

  "phone": "+441314447100",
  "email": "info@craiglockhart.com",
  "website_url": "https://www.edinburghleisure.co.uk/venues/craiglockhart",
  "instagram_url": "https://instagram.com/edinburghleisure",
  "facebook_url": "https://facebook.com/craiglockhartsports",

  "opening_hours": {
    "monday": {"open": "06:00", "close": "22:00"},
    "tuesday": {"open": "06:00", "close": "22:00"},
    "wednesday": {"open": "06:00", "close": "22:00"},
    "thursday": {"open": "06:00", "close": "22:00"},
    "friday": {"open": "06:00", "close": "22:00"},
    "saturday": {"open": "08:00", "close": "20:00"},
    "sunday": {"open": "08:00", "close": "20:00"}
  },

  "tennis_summary": "8 indoor courts and 4 outdoor clay courts with coaching available",
  "tennis": true,
  "tennis_total_courts": 12,
  "tennis_indoor_courts": 8,
  "tennis_outdoor_courts": 4,
  "tennis_covered_courts": 8,
  "tennis_floodlit_courts": 4,

  "padel_summary": "4 indoor courts available for pay-and-play",
  "padel": true,
  "padel_total_courts": 4,

  "pickleball_summary": "2 dedicated pickleball courts",
  "pickleball": true,
  "pickleball_total_courts": 2,

  "badminton_summary": "6 courts available for casual play and league matches",
  "badminton": true,
  "badminton_total_courts": 6,

  "squash_summary": "3 courts including 1 glass-back court",
  "squash": true,
  "squash_total_courts": 3,
  "squash_glass_back_courts": 1,

  "table_tennis_summary": "2 tables in dedicated area",
  "table_tennis": true,
  "table_tennis_total_tables": 2,

  "football_summary": "Multiple pitch sizes for 5-a-side, 7-a-side and full 11-a-side matches",
  "football_5_a_side": true,
  "football_5_a_side_total_pitches": 4,
  "football_7_a_side": true,
  "football_7_a_side_total_pitches": 2,
  "football_11_a_side": true,
  "football_11_a_side_total_pitches": 1,

  "swimming_summary": "25m indoor pool with separate learner pool",
  "indoor_pool": true,
  "indoor_pool_length_m": 25,
  "outdoor_pool": false,
  "outdoor_pool_length_m": null,
  "family_swim": true,
  "adult_only_swim": true,
  "swimming_lessons": true,

  "gym_summary": "120-station gym with modern equipment",
  "gym_available": true,
  "gym_size": 120,
  "classes_summary": "60+ classes per week including yoga, HIIT, spin, pilates and strength",
  "classes_per_week": 60,
  "hiit_classes": true,
  "yoga_classes": true,
  "pilates_classes": true,
  "strength_classes": true,
  "cycling_studio": true,
  "functional_training_zone": true,

  "spa_summary": "Full spa with sauna, steam room and hydro pool",
  "spa_available": true,
  "sauna": true,
  "steam_room": true,
  "hydro_pool": true,
  "hot_tub": false,
  "outdoor_spa": false,
  "ice_cold_plunge": true,
  "relaxation_area": true,

  "amenities_summary": "Cafe serving healthy snacks and smoothies",
  "restaurant": false,
  "bar": false,
  "cafe": true,
  "childrens_menu": false,
  "wifi": true,

  "family_summary": "Creche available, kids swimming and tennis lessons",
  "creche_available": true,
  "creche_age_min": 6,
  "creche_age_max": 12,
  "kids_swimming_lessons": true,
  "kids_tennis_lessons": true,
  "holiday_club": true,
  "play_area": false,

  "parking_and_transport_summary": "80 spaces including disabled parking, bus routes nearby",
  "parking_spaces": 80,
  "disabled_parking": true,
  "parent_child_parking": true,
  "ev_charging_available": true,
  "ev_charging_connectors": 4,
  "public_transport_nearby": true,
  "nearest_railway_station": "Slateford",

  "reviews_summary": "4.2 stars from 340 Google reviews",
  "average_rating": 4.2,
  "review_count": 340,
  "google_review_count": 340,
  "facebook_likes": 1250,

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

### Sample "Incomplete" Entity (Current Problem)

```json
{
  "entity_name": "Craiglockhart Sports Centre",
  "entity_class": "place",
  "slug": "craiglockhart-sports-centre",
  "summary": null,  // ❌ Should have description

  "categories": [],  // ❌ Should have categories

  "latitude": 55.920654,  // ✅ Good
  "longitude": -3.237891,  // ✅ Good
  "street_address": "177 Colinton Road, Edinburgh EH14 1BZ",  // ✅ Good
  "city": null,  // ❌ Should parse from address
  "postcode": null,  // ❌ Should parse from address

  "phone": null,  // ❌ Missing - available from source
  "website_url": null,  // ❌ Missing - available from source

  "tennis": null,  // ❌ Missing - venue HAS tennis
  "swimming_summary": null,  // ❌ Missing
  "gym_available": null,  // ❌ Missing
  "parking_spaces": null  // ❌ Missing
}
```

This is **incomplete** - has location but missing all the valuable facility data.

---

## Intelligent Orchestration

**Design Question:** How should query interpretation and connector selection work together?

### Current Design Approach

**Query:** "padel courts edinburgh"

**Step 1: Query Analysis**
- Detect activity: "padel"
- Detect location: "edinburgh"
- Classify intent: category search (general "courts" not specific venue)

**Step 2: Connector Selection**
Uses Edinburgh Finds lens configuration to select relevant sources:
- **Free/cheap discovery:** Serper, OpenStreetMap, Edinburgh Council API
- **Edinburgh Finds-specific:** Sport Scotland, Edinburgh Leisure API
- **Enrichment:** Google Places (paid, detailed data)

**Step 3: Ordered Execution**
- Phase 1: Discovery (free sources first)
- Phase 2: Enrichment (paid sources if needed)
- Early stopping if sufficient results

**Step 4: Extraction**
- Each connector has specialized extractor
- Hybrid approach: deterministic rules + LLM for unstructured data
- Produces ExtractedEntity records

**Step 5: Cross-Source Deduplication**
- External ID matching: "ChIJabc..." = "EH-PAD-001"?
- Slug matching: "craiglockhart-sports-centre" = "craiglockhart-sports-centre"
- Fuzzy matching: Name similarity + distance < 50m
- Merge duplicates into single entity

**Step 6: Field-Level Merging**
Trust hierarchy resolves conflicts:
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

**Step 7: Entity Finalization**
- Generate slug from name
- Classify entity type
- Upsert to Entity table (idempotent)

**Questions to Resolve:**
1. Should lens configuration drive connector selection entirely, or should there be base orchestration logic?
2. How much query interpretation logic belongs in the lens vs. the engine?
3. Should deduplication and merging be lens-aware, or purely universal?

---

## Lens Responsibilities

The Edinburgh Finds lens provides vertical-specific interpretation:

### 1. Query Vocabulary
Define domain keywords so engine can detect intent:
```yaml
activity_keywords:
  - padel
  - tennis
  - squash
  - swimming
  - gym

location_indicators:
  - edinburgh
  - leith
  - portobello
  - stockbridge

facility_keywords:
  - centre
  - club
  - facility
  - pool
```

### 2. Connector Configuration
Tell orchestrator which data sources are relevant:
```yaml
connectors:
  edinburgh_leisure_api:
    priority: high
    triggers:
      - type: location_match
        locations: [edinburgh]

  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [tennis, padel, squash, swimming, football]
```

### 3. Value Interpretation
Map categories and dimension values to display labels:
```yaml
category_labels:
  sports_facility: "Sports Facility"
  swimming_pool: "Swimming Pool"
  tennis_facility: "Tennis Club"
  gym: "Gym & Fitness"
```

### 4. Field Schema Definition
Define what data to capture for Edinburgh Finds venues (already defined in old_db_models.py - Venue table).

**Design Question:** Should lenses also be responsible for field-level extraction rules, or just schema definition?

---

## Guiding Principles

### 1. Complete Data Over Partial Data
Capture ALL available information. Empty fields should be exceptions (facility doesn't exist, data not available) not the norm.

### 2. Reality Over Tests
Validate with real queries, real connectors, real Entity table inspection. Tests that pass with mock data but fail with real connectors are worse than no tests.

### 3. Accuracy Over Coverage
100 perfectly accurate entities > 500 entities with wrong classifications and missing data.

### 4. Incremental Validation
Fix one thing (e.g., classification), validate end-to-end (run query, inspect Entity table), THEN fix next thing.

### 5. Rich Facility Data is the Differentiator
Basic listings (name/address/phone) are commodity data. Comprehensive facility details (court counts, pool specs, amenities, pricing, reviews) are the unique value.

### 6. Source Provenance Always Tracked
Every entity should track which sources contributed, when it was verified, what external IDs exist. Enables debugging, trust decisions, and incremental updates.

---

**This vision document defines what success looks like for Edinburgh Finds.**

Every implementation plan should:
- ✅ Reference this vision to ensure alignment
- ✅ Define success as "Entity table has complete, accurate data"
- ✅ Include before/after validation with real queries
- ✅ Focus on outcomes (data completeness, accuracy) not process
- ✅ Be small and focused (fix ONE specific gap at a time)
