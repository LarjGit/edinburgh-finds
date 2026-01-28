# Edinburgh Finds - Vision Document

**Purpose:** Define what success looks like for the intelligent ingestion engine.

---

## Core Vision

**An AI-scale discovery platform that intelligently finds, extracts, and publishes entities across any vertical (Padel, Wine, Restaurants, Gyms) with zero code changes.**

Users should be able to run natural language queries and get high-quality, structured entity data in the database, ready for display.

---

## User Experience

### What Happens When You Run a Query

```bash
python -m engine.orchestration.cli run "padel courts edinburgh" --persist
```

**Expected outcome:**

1. **Intelligent Connector Selection**
   - System analyzes query: "padel" + "courts" + "edinburgh"
   - Selects relevant connectors: Serper, Google Places, Sport Scotland, OpenStreetMap
   - Routes query appropriately (sport_scotland for sports-specific data)

2. **Data Extraction**
   - Fetches raw data from multiple sources
   - Extracts structured entities (names, locations, activities, contact info)
   - Deduplicates across sources (same venue from multiple connectors)

3. **Entity Table Population**
   - 50-200 high-quality entities in Entity table
   - Each entity has:
     - ✅ Correct `entity_class` ("place" for venues, not "thing")
     - ✅ URL-safe `slug` ("game4padel-barnton-park" from "Game4Padel - Barnton Park")
     - ✅ `canonical_activities` (["padel", "tennis"])
     - ✅ `canonical_roles` (["provides_facility"])
     - ✅ Coordinates (`latitude`, `longitude`)
     - ✅ Address (`street_address`, `city`, `postcode`)
     - ✅ Contact info (`phone`, `email`, `website_url`)

4. **User Can Browse Results**
   - Frontend queries Entity table
   - Shows deduplicated, high-quality venues
   - No duplicates, no garbage data

---

## Success Criteria (Concrete)

### Query: "padel courts edinburgh"

**After running orchestration with --persist:**

```sql
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN entity_class = 'place' THEN 1 END) as places,
  COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as with_coords,
  COUNT(CASE WHEN array_length(canonical_activities, 1) > 0 THEN 1 END) as with_activities
FROM "Entity";
```

**Expected:**
- `total`: 50-200 entities
- `places`: 95%+ should be entity_class='place'
- `with_coords`: 80%+ should have coordinates
- `with_activities`: 70%+ should have activities populated

**Sample Entity (inspect one record):**
```json
{
  "entity_name": "Game4Padel Barnton Park",
  "slug": "game4padel-barnton-park",
  "entity_class": "place",
  "canonical_activities": ["padel"],
  "canonical_roles": ["provides_facility"],
  "latitude": 55.9679631,
  "longitude": -3.2790334,
  "street_address": "12 Barnton Park, Edinburgh EH4 6JF",
  "city": "Edinburgh",
  "postcode": "EH4 6JF",
  "phone": "+44 131 XXX XXXX",
  "website_url": "https://game4padel.co.uk"
}
```

---

## Vertical-Agnostic Architecture

### The Core Principle

**Engine knows NOTHING about domains.** All vertical-specific logic lives in configuration files (Lenses).

### Adding a New Vertical

To add "Wine Discovery" or "Restaurant Finder":

1. Create two YAML files:
   - `engine/lenses/wine/query_vocabulary.yaml`
   - `engine/lenses/wine/connector_rules.yaml`

2. **That's it.** Zero Python code changes.

3. System automatically:
   - Routes wine queries to wine-specific connectors
   - Extracts wine-specific attributes to `modules.wine`
   - Uses wine vocabulary for query analysis

### What "Vertical-Agnostic" Means in Practice

**Engine uses generic concepts:**
- `entity_class`: place / person / organization / event / thing
- `canonical_activities`: ["padel"] or ["wine_tasting"] or ["italian_cuisine"]
- `canonical_roles`: ["provides_facility"] or ["sells_goods"] or ["provides_instruction"]
- `modules`: JSON field for vertical-specific attributes

**Lenses provide domain knowledge:**
- Activity keywords for query matching
- Connector routing rules
- Vertical-specific vocabulary

---

## Data Quality Standards

### Minimum Bar for Entity Records

**Every Entity MUST have:**
- ✅ `entity_name` (never "Unknown")
- ✅ `slug` (generated, unique, URL-safe)
- ✅ `entity_class` (correctly classified, not defaulting to "thing")

**Every place Entity SHOULD have:**
- ✅ Coordinates (`latitude`, `longitude`) - 80%+ coverage
- ✅ Address (`street_address` or `city`) - 90%+ coverage
- ✅ Activities (`canonical_activities`) - 70%+ coverage

**Contact info is nice-to-have:**
- Phone: 30%+ coverage
- Website: 50%+ coverage
- Email: 10%+ coverage

### Deduplication Requirements

**No duplicate entities:**
- Same venue from multiple sources → merged into ONE Entity
- Slug-based deduplication works correctly
- External ID matching works (Google Place ID, OSM ID)

**If you search for "Game4Padel", you see ONE entity, not:**
- ❌ "Game4Padel Barnton Park" (from Serper)
- ❌ "Game4Padel | Barnton Park Padel" (from Google Places)
- ❌ "Barnton Park Padel Centre" (from Sport Scotland)

---

## Intelligent Orchestration

### How Connector Selection Works

**Query Analysis:**
```
"padel courts edinburgh"
  ↓
Query Features:
  - looks_like_category_search: true (generic "courts" not specific venue)
  - has_geo_intent: true ("edinburgh")
  - activity: "padel"
```

**Connector Routing (via Lens):**
```yaml
# From padel/connector_rules.yaml
sport_scotland:
  priority: high
  triggers:
    - type: any_keyword_match
      keywords: [padel, tennis, squash]
```

**Result:**
- Base connectors: Serper, Google Places (always run)
- Geo-specific: Edinburgh Council (because "edinburgh")
- Domain-specific: Sport Scotland (because "padel" keyword match)
- Skip: Wine Searcher (no wine keywords)

### Cost Management

**Budget-aware execution:**
- Cheap connectors first (OpenStreetMap, Edinburgh Council - free)
- Medium connectors next (Serper - $0.002/query)
- Expensive connectors if needed (Google Places - $0.017/query)
- Early stopping if sufficient results found

---

## Technical Architecture

### End-to-End Data Flow

```
User Query
  ↓
Orchestrator (analyzes query, selects connectors)
  ↓
Connectors (fetch raw data from 6 sources)
  ↓
RawIngestion table (store raw JSON)
  ↓
Extraction (deterministic rules + LLM for unstructured data)
  ↓
ExtractedEntity table (structured but not deduplicated)
  ↓
EntityFinalizer (deduplicate, generate slugs, classify)
  ↓
Entity table (final, deduplicated, ready for display)
  ↓
Frontend (Next.js queries Entity table)
```

### Key Components

**Orchestration Layer** (`engine/orchestration/`)
- `planner.py`: Intelligent connector selection
- `registry.py`: Connector metadata (cost, trust, capabilities)
- `query_features.py`: Query analysis (Lens-driven)
- `entity_finalizer.py`: ExtractedEntity → Entity

**Extraction Layer** (`engine/extraction/`)
- `entity_classifier.py`: Classify entities (place/person/org/event/thing)
- `deduplication.py`: Match duplicates (external ID, slug, fuzzy)
- `extractors/`: Connector-specific extraction logic

**Lens Layer** (`engine/lenses/`)
- `query_lens.py`: Loads vertical-specific configuration
- `padel/`: Padel lens YAML configs
- `wine/`: Wine lens YAML configs

---

## What "Done" Looks Like

### For a Single Query

Run:
```bash
python -m engine.orchestration.cli run "padel courts edinburgh" --persist
```

Inspect Entity table:
```sql
SELECT entity_name, entity_class, canonical_activities, latitude, longitude, slug
FROM "Entity"
LIMIT 10;
```

**Expected output:**
- 50-200 entities
- 95%+ are `entity_class='place'`
- 80%+ have coordinates
- 70%+ have activities
- All have unique slugs
- No obvious duplicates

### For Vertical Extensibility

Create Wine lens:
```bash
touch engine/lenses/wine/query_vocabulary.yaml
touch engine/lenses/wine/connector_rules.yaml
```

Run:
```bash
python -m engine.orchestration.cli run "wineries in scotland" --persist --lens=wine
```

**Expected:**
- Wine-specific connectors called (wine_searcher)
- Sports connectors NOT called (sport_scotland)
- Entity table populated with wineries
- ZERO Python code changes needed

---

## Current Gaps (What's Broken)

### Known Issues

1. **Classification broken**: Most entities are `entity_class="thing"` instead of `"place"`
   - Root cause: `classify_entity()` logic too simplistic
   - Impact: Entities unusable for frontend filtering

2. **Activities not extracted**: `canonical_activities` is empty for most entities
   - Root cause: Connectors don't extract activities from raw data
   - Impact: Can't filter by activity ("show me padel only")

3. **Inconsistent field names**: Connectors use different field names
   - Example: `latitude` vs `location_lat`, `address` vs `address_full`
   - Impact: EntityFinalizer can't find data in ExtractedEntity

4. **No extraction for Serper**: Serper connector has no extractor
   - Impact: Serper results not persisted (7 failures in latest run)

### Priority Order (What to Fix First)

**P0 - Blocking:**
1. Fix entity classification (thing → place)
2. Fix field name standardization
3. Extract activities from connector data

**P1 - Important:**
4. Add Serper extractor
5. Improve deduplication accuracy
6. Add Sport Scotland extractor improvements

**P2 - Nice to have:**
7. Extract contact info (phone, email, website)
8. Extract opening hours
9. Extract images

---

## Non-Goals (Out of Scope)

**Not trying to build:**
- ❌ Real-time data updates (batch processing is fine)
- ❌ Perfect data (80% good quality is acceptable)
- ❌ Custom web scraping (use existing APIs only)
- ❌ User-generated content (admin-curated only for now)
- ❌ Multi-language support (English only for MVP)

**Not optimizing for:**
- ❌ Sub-second query response (5-30 seconds is acceptable)
- ❌ Unlimited budget (cost per query matters)
- ❌ 100% coverage (missing 20% of venues is acceptable)

---

## How to Validate Changes

### Before Making Changes

1. Run baseline query:
   ```bash
   python -m engine.orchestration.cli run "padel courts edinburgh" --persist
   ```

2. Capture metrics:
   ```sql
   SELECT
     COUNT(*) as total,
     COUNT(CASE WHEN entity_class = 'place' THEN 1 END) as places,
     COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as with_coords
   FROM "Entity";
   ```

### After Making Changes

1. Clear Entity table:
   ```sql
   DELETE FROM "Entity";
   ```

2. Re-run same query

3. Compare metrics - did they improve?

4. Inspect sample entities - do they look better?

### Definition of Improvement

**A change is successful if:**
- Metrics improved (more places, more coords, more activities)
- No regressions (didn't break something else)
- Sample entities look correct when inspected

**A change failed if:**
- Metrics stayed same or got worse
- Tests pass but Entity table still has bad data
- Only works with test data, not real connectors

---

## Guiding Principles

### 1. Reality Over Tests
Tests should validate real connector data, not idealized mock data.

### 2. Outcomes Over Architecture
Success = "Entity table has good data", not "tests pass" or "code is elegant"

### 3. Incremental Over Big Bang
Fix one thing at a time, validate end-to-end, then move to next thing.

### 4. Configuration Over Code
Adding a vertical should require YAML files, not Python changes.

### 5. Good Enough Over Perfect
80% data quality with low cost > 95% data quality with high cost.

---

**This vision document should be the reference for all future plans.**

Every plan should:
1. Reference this vision
2. State which gap it's fixing
3. Define success criteria (what should Entity table look like after?)
4. Validate end-to-end (run real query, check real results)
