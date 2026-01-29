# Edinburgh Finds - System Vision

**Last Updated:** 2026-01-29
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
        # Basic extraction (no lens needed)
        basic_fields = self._extract_basic_fields(raw_data)

        # Apply lens contract for canonical dimensions and modules
        return self.apply_lens_contract(raw_data, basic_fields, ctx=ctx)
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
        ctx: ExecutionContext
    ) -> Dict:
        """
        Apply lens mapping rules and module triggers.

        Centralized lens usage - extractors call this helper method
        instead of accessing ctx.lens_contract directly.

        Args:
            raw_data: Original raw data
            ctx: Execution context with lens_contract

        Returns:
            Dict: Extracted fields with canonical dimensions and modules populated
        """
        if not ctx or not ctx.lens_contract:
            raise ValueError("Missing lens_contract in execution context")

        return extract_with_lens_contract(
            raw_data,
            ctx.lens_contract
        )
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
    trust_level="crowdsourced", # official | verified | crowdsourced
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
    trust_level="crowdsourced",
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
│ 10. FIELD-LEVEL MERGING                        │
│     - Trust hierarchy resolves conflicts       │
│     - Official source > crowdsourced           │
│     - Higher trust level wins                  │
│     - Last writer (alphabetically) on tie      │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ 11. ENTITY FINALIZATION                        │
│     - EntityFinalizer: Groups entities by slug │
│     - SlugGenerator: Creates URL-safe slugs    │
│       (e.g., "The Padel Club" → "padel-club") │
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
mapping_rules:
  # Activities
  - pattern: "(?i)tennis|racket sports"
    dimension: canonical_activities
    value: tennis
    confidence: 0.95

  - pattern: "(?i)padel|pádel"
    dimension: canonical_activities
    value: padel
    confidence: 0.98

  - pattern: "(?i)swimming|pool|aquatic"
    dimension: canonical_activities
    value: swimming
    confidence: 0.90

  # Place Types
  - pattern: "(?i)sports? centre|multi.?sport"
    dimension: canonical_place_types
    value: sports_centre
    confidence: 0.95

  - pattern: "(?i)tennis club"
    dimension: canonical_place_types
    value: tennis_club
    confidence: 0.98

  # Roles
  - pattern: "(?i)facility|venue|centre"
    dimension: canonical_roles
    value: provides_facility
    confidence: 0.90

  - pattern: "(?i)coach|instructor|trainer"
    dimension: canonical_roles
    value: provides_instruction
    confidence: 0.95

  # Access
  - pattern: "(?i)members?.?only|private club"
    dimension: canonical_access
    value: membership
    confidence: 0.95

  - pattern: "(?i)pay.?and.?play|drop.?in|casual"
    dimension: canonical_access
    value: pay_and_play
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
- ⚠️ Domain modules (`modules`) - schema defined, not populated by extractors

**To Be Implemented:**
- ❌ Derived groupings (query-time views)
- ❌ SEO templates (frontend metadata generation)

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
3. **Module population** - Extractors don't organize data into modules
4. **Module triggers** - Defined in schema but not applied during extraction
5. **Full lens.yaml** - Only query vocabulary and connector rules exist

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

**Phase 2: Module Population (High Priority)**
1. Update extractors to organize extracted data into module structure
2. Apply module_triggers to attach domain modules
3. Validate modules JSONB populated with namespaced data

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

This document defines the architectural principles and success criteria. Implementation plans and task tracking live in `conductor/tracks/`.

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
