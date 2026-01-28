# Architecture Cleanup & Vertical-Agnostic Refactor Design

**Date:** 2026-01-28
**Status:** Design Review
**Priority:** Critical - Foundation for all future development

---

## Executive Summary

This design addresses critical architectural issues discovered during comprehensive codebase audit:

1. **13 dead files** (~2,500 LOC) from incomplete refactors
2. **3 critical hardcoding violations** breaking vertical-agnostic principle
3. **Zombie tests** claiming 192 tests passing, but heavily mocked (only 2 real integration tests)
4. **Incomplete persistence pipeline** stopping at ExtractedEntity instead of Entity table

**Goal:** Establish a clean, testable, truly vertical-agnostic foundation before adding features.

---

## Design Principles

### 1. Engine Purity (Zero Tolerance)

**Rule:** Engine code MUST NOT contain:
- Domain terms (padel, tennis, wine, restaurant)
- Vertical-specific field names (has_courts, tennis_total_courts)
- Business logic based on domain concepts

**Enforcement:**
- Lens configurations provide all vertical-specific vocabulary
- Engine works with generic entity_class and dimension arrays only
- Automated import boundary tests detect violations

### 2. Configuration Over Code

**Rule:** Adding a new vertical (Wine, Restaurants) should require:
- ✅ New Lens YAML file only
- ❌ NO engine code changes

**Enforcement:**
- Connector selection driven by Lens config
- Query vocabulary loaded from Lens at runtime
- Field extraction routes to modules (interpreted by Lens)

### 3. Test Reality Over Test Count

**Rule:** Tests must validate actual behavior, not mock interactions

**Enforcement:**
- Integration tests marked `@pytest.mark.slow` and run against real database
- Unit tests kept minimal - integration tests are primary validation
- Coverage target: >80% of REAL code paths, not mocked flows

---

## Phase 1: Dead Code Cleanup (No Risk)

### Objective

Remove 13 unused files from previous refactors to reduce maintenance burden and confusion.

### Files to Delete

#### Legacy Test Scripts (3 files)
```
engine/run_osm_comprehensive.py
engine/run_osm_manual.py
```

**Reason:** Manual test scripts predating unified CLI. Functionality available via:
- `python -m engine.ingestion.cli openstreetmap "query"`
- `python -m engine.orchestration.cli run "query"`

#### Legacy CLI Wrappers (3 files)
```
engine/ingestion/run_serper.py
engine/ingestion/run_osm.py
engine/ingestion/run_google_places.py
```

**Reason:** Thin wrappers around `engine.ingestion.cli`. Official docs only reference CLI module.

#### Legacy Connector Test Scripts (5 files)
```
engine/scripts/run_serper_connector.py
engine/scripts/run_google_places_connector.py
engine/scripts/run_edinburgh_council_connector.py
engine/scripts/run_open_charge_map_connector.py
engine/scripts/run_sport_scotland_connector.py
```

**Reason:** 200+ line verbose test scripts superseded by:
- `python -m engine.ingestion.cli <connector> <query>` (single connector)
- `python -m engine.orchestration.cli run "query"` (multi-connector)
- `scripts/test_orchestration_live.py` (comprehensive smoke test)

#### Legacy Direct Ingestion Approach (3 files)
```
engine/run_seed.py
engine/seed_data.py
engine/ingest.py
```

**Reason:** Represents abandoned "direct seed → database" approach that bypasses orchestration pipeline. Current workflow: `orchestration.cli → persistence.py → Entity table`

### Validation

After deletion, verify:
1. No import errors: `python -m pytest --collect-only`
2. All documented CLIs still work (per CLAUDE.md)
3. No references in active code: `grep -r "run_seed\|ingest.py" engine/`

### Documentation Updates

- Update `engine/scripts/README.md` to remove deleted script references
- Update `CLAUDE.md` if any deleted files were mentioned
- Add migration note to `CHANGELOG.md`

---

## Phase 2: Hardcoding Violations - Refactor Design

### 2.1 Query Features - Remove Sports Hardcoding

**Current State (CRITICAL VIOLATION):**

File: `engine/orchestration/query_features.py:96-114`

```python
category_terms = [
    "court", "courts", "padel", "tennis", "football", "rugby",
    "swimming", "gym", "sport", "sports",
]
```

**Problem:**
- Sports terms hardcoded in engine
- Adding Wine vertical requires engine code changes
- Violates vertical-agnostic principle

**Refactored Design:**

```python
# engine/orchestration/query_features.py (refactored)

from engine.lenses.loader import get_active_lens

def extract_features(query: str, lens_name: Optional[str] = None) -> QueryFeatures:
    """Extract query features using Lens-provided vocabulary."""

    # Load vocabulary from active Lens
    lens = get_active_lens(lens_name)
    category_terms = lens.get_activity_keywords()  # Lens provides domain terms
    location_terms = lens.get_location_indicators()

    # Generic pattern detection (no domain knowledge)
    looks_like_category = any(term in normalized_query for term in category_terms)
    has_location = any(term in normalized_query for term in location_terms)

    return QueryFeatures(
        looks_like_category_search=looks_like_category,
        has_location_indicator=has_location,
        query_length=len(query.split()),
    )
```

**Lens Configuration:**

File: `engine/lenses/padel/query_vocabulary.yaml` (NEW)

```yaml
# Padel Lens - Query Vocabulary
activity_keywords:
  - padel
  - tennis
  - football
  - rugby
  - swimming
  - gym
  - fitness
  - sport
  - sports
  - court
  - courts
  - pitch
  - club

location_indicators:
  - in
  - near
  - around
  - edinburgh
  - leith
  - portobello

query_patterns:
  category_search:
    # "padel courts" → category search
    - pattern: "{activity} {facility_type}"
      confidence: high

  specific_search:
    # "Edinburgh Indoor Sports Centre" → specific place search
    - pattern: "{proper_noun} {facility_type}"
      confidence: high
```

File: `engine/lenses/wine/query_vocabulary.yaml` (EXAMPLE - shows extensibility)

```yaml
# Wine Lens - Query Vocabulary (example for horizontal scaling validation)
activity_keywords:
  - wine
  - winery
  - vineyard
  - tasting
  - cellar
  - sommelier
  - bottle
  - vintage

location_indicators:
  - in
  - near
  - region
  - scotland
  - edinburgh
```

**Benefits:**
- Adding Wine vertical: Create `lenses/wine/query_vocabulary.yaml` (NO engine changes)
- Query features module is now generic (detects patterns, not specific domains)
- Lenses compete: Padel Lens scores "padel courts", Wine Lens scores "wine tasting"

---

### 2.2 Orchestration Planner - Remove Sports-Specific Routing

**Current State (CRITICAL VIOLATION):**

File: `engine/orchestration/planner.py:141-175`

```python
def _is_sports_related(query: str) -> bool:
    """Check if query is sports-related."""
    sports_keywords = [
        "padel", "tennis", "football", "rugby", "swimming",
        "pool", "sport", "gym", "fitness", "court", "pitch", "club",
    ]
    return any(keyword in query.lower() for keyword in sports_keywords)

# Later in orchestrate():
if _is_sports_related(request.query):
    connector_names.append("sport_scotland")
```

**Problem:**
- Function name `_is_sports_related()` is domain-specific
- Sports keywords hardcoded in planner
- Wine vertical can't have similar domain-specific connector routing

**Refactored Design:**

```python
# engine/orchestration/planner.py (refactored)

from engine.lenses.loader import get_active_lens

async def orchestrate(request: IngestRequest) -> OrchestrationReport:
    """Main orchestration flow with Lens-driven connector selection."""

    # 1. Extract query features (now Lens-driven)
    query_features = extract_features(request.query, lens_name=request.lens)

    # 2. Load Lens configuration
    lens = get_active_lens(request.lens)

    # 3. Select connectors (generic + Lens-specific)
    connector_names = await _select_connectors(
        request,
        query_features,
        lens
    )

    # ... rest of orchestration
```

```python
async def _select_connectors(
    request: IngestRequest,
    query_features: QueryFeatures,
    lens: Lens
) -> List[str]:
    """Select connectors based on query + Lens rules."""

    # Base connectors (vertical-agnostic)
    connectors = []

    if query_features.looks_like_category_search:
        connectors.append("serper")  # Generic search
        connectors.append("openstreetmap")  # Generic geodata

    if query_features.has_location_indicator:
        connectors.append("google_places")  # Location-specific

    # Lens-specific connectors (NEW: config-driven)
    lens_connectors = lens.get_connectors_for_query(request.query, query_features)
    connectors.extend(lens_connectors)

    return list(dict.fromkeys(connectors))  # Deduplicate, preserve order
```

**Lens Configuration:**

File: `engine/lenses/padel/connector_rules.yaml` (NEW)

```yaml
# Padel Lens - Connector Selection Rules
connectors:
  sport_scotland:
    priority: high
    triggers:
      - any_keyword_match:
          keywords: [padel, tennis, football, rugby, swimming, gym, sport, court, pitch, club]
          threshold: 1  # Match at least 1 keyword

      - category_search:
          activity_keywords: [padel, tennis, sport]

    budget_weight: 0.0  # Free connector
    trust_score: official  # Government data source

  edinburgh_council:
    priority: medium
    triggers:
      - location_match:
          keywords: [edinburgh, leith, portobello]
      - facility_search:
          keywords: [facility, centre, center, venue]

    budget_weight: 0.0
    trust_score: official
```

File: `engine/lenses/wine/connector_rules.yaml` (EXAMPLE)

```yaml
# Wine Lens - Connector Selection Rules (example)
connectors:
  wine_searcher_api:
    priority: high
    triggers:
      - any_keyword_match:
          keywords: [wine, winery, vineyard, tasting, cellar]
          threshold: 1

    budget_weight: 0.05  # $0.05 per query
    trust_score: crowdsourced
```

**Lens Loader Implementation:**

File: `engine/lenses/loader.py` (ENHANCED)

```python
from typing import List, Optional
from pathlib import Path
import yaml
from dataclasses import dataclass

@dataclass
class Lens:
    """Lens configuration container."""
    name: str
    query_vocabulary: dict
    connector_rules: dict

    def get_activity_keywords(self) -> List[str]:
        """Get activity keywords for query feature extraction."""
        return self.query_vocabulary.get("activity_keywords", [])

    def get_location_indicators(self) -> List[str]:
        """Get location indicator words."""
        return self.query_vocabulary.get("location_indicators", [])

    def get_connectors_for_query(
        self,
        query: str,
        query_features: "QueryFeatures"
    ) -> List[str]:
        """Determine which Lens-specific connectors should run."""
        connectors = []
        normalized = query.lower()

        for connector_name, rules in self.connector_rules.get("connectors", {}).items():
            if self._matches_triggers(normalized, query_features, rules["triggers"]):
                connectors.append(connector_name)

        return connectors

    def _matches_triggers(self, query: str, features: "QueryFeatures", triggers: List[dict]) -> bool:
        """Check if query matches any trigger rule."""
        for trigger in triggers:
            if "any_keyword_match" in trigger:
                keywords = trigger["any_keyword_match"]["keywords"]
                threshold = trigger["any_keyword_match"]["threshold"]
                matches = sum(1 for kw in keywords if kw in query)
                if matches >= threshold:
                    return True

            if "location_match" in trigger and features.has_location_indicator:
                keywords = trigger["location_match"]["keywords"]
                if any(kw in query for kw in keywords):
                    return True

        return False


def get_active_lens(lens_name: Optional[str] = None) -> Lens:
    """Load Lens configuration from YAML files."""
    if lens_name is None:
        lens_name = "padel"  # Default lens

    lens_dir = Path(f"engine/lenses/{lens_name}")

    # Load vocabulary
    vocab_path = lens_dir / "query_vocabulary.yaml"
    with vocab_path.open() as f:
        query_vocabulary = yaml.safe_load(f)

    # Load connector rules
    connectors_path = lens_dir / "connector_rules.yaml"
    with connectors_path.open() as f:
        connector_rules = yaml.safe_load(f)

    return Lens(
        name=lens_name,
        query_vocabulary=query_vocabulary,
        connector_rules=connector_rules,
    )
```

**Benefits:**
- Planner is now 100% vertical-agnostic (no domain terms)
- Connector selection is config-driven via Lens YAML
- Adding Wine vertical: Create `lenses/wine/*.yaml` files (NO planner changes)
- Test new lens without touching engine code

---

### 2.3 Entity Classifier - Remove Sports-Specific Fields

**Current State (CRITICAL VIOLATION):**

File: `engine/extraction/entity_classifier.py:141-158`

```python
def extract_roles(raw_data: Dict[str, Any]) -> List[str]:
    roles = []

    # Check for facility provision
    if raw_data.get("has_courts") or raw_data.get("has_pitches"):
        roles.append("provides_facility")

    # Check for instruction provision
    if raw_data.get("provides_coaching"):
        roles.append("provides_instruction")

    return roles
```

**Problem:**
- `has_courts`, `has_pitches` are sports-facility specific
- `provides_coaching` assumes sports/instruction vertical
- Wine vertical would need `has_vineyard`, `provides_tasting` → code changes

**Refactored Design:**

```python
# engine/extraction/entity_classifier.py (refactored)

def extract_roles(raw_data: Dict[str, Any]) -> List[str]:
    """Extract entity roles from raw data (VERTICAL-AGNOSTIC)."""
    roles = []

    # GENERIC: Check for equipment/facility provision
    if raw_data.get("provides_equipment") or raw_data.get("equipment_count", 0) > 0:
        roles.append("provides_facility")

    # GENERIC: Check for instruction/education provision
    if raw_data.get("provides_instruction"):
        roles.append("provides_instruction")

    # GENERIC: Check for membership organization
    if raw_data.get("membership_required") or raw_data.get("is_members_only"):
        roles.append("membership_org")

    # GENERIC: Check for retail
    if raw_data.get("sells_products") or raw_data.get("has_shop"):
        roles.append("provides_retail")

    return roles
```

**Extractor Updates:**

Extractors now populate GENERIC fields:

```python
# engine/extraction/extractors/sport_scotland_extractor.py (updated)

def extract(self, raw_ingestion: RawIngestion) -> ExtractedEntity:
    """Extract from Sport Scotland (domain-specific connector)."""
    data = json.loads(raw_ingestion.raw_payload)

    # Extract to MODULES (vertical-specific data)
    modules = {
        "sports_facility": {
            "equipment": []
        }
    }

    if "tennis" in facility_type.lower():
        modules["sports_facility"]["equipment"].append({
            "type": "tennis_court",
            "count": data.get("number_of_courts", 0),
            "surface": data.get("surface_type")
        })

    # Populate GENERIC top-level fields
    equipment_count = len(modules["sports_facility"]["equipment"])

    return ExtractedEntity(
        entity_class="place",
        canonical_activities=["tennis"],  # From Lens mapping
        provides_equipment=True,  # ✅ GENERIC flag
        equipment_count=equipment_count,  # ✅ GENERIC count
        modules=modules,  # ✅ Vertical-specific details in modules
    )
```

**Benefits:**
- Entity classifier uses generic field patterns
- Domain-specific data lives in `modules` (interpreted by Lens)
- Wine extractor can populate same generic fields:
  ```python
  provides_equipment=True  # Has tasting equipment
  equipment_count=5  # 5 tasting rooms
  modules={"wine_production": {"vineyard_size_ha": 20}}
  ```

---

### 2.4 Persistence Layer - Remove Hardcoded entity_class

**Current State (VIOLATION):**

File: `engine/orchestration/persistence.py:370`

```python
entity_data = {
    "source": source,
    "entity_class": "place",  # ⚠️ HARDCODED
    "attributes": json.dumps(attributes),
}
```

**Problem:**
- All entities forced to `entity_class: "place"`
- People, organizations, events would be misclassified

**Refactored Design:**

```python
# engine/orchestration/persistence.py (refactored)

from engine.extraction.entity_classifier import classify_entity

async def persist_entities(...):
    for candidate in accepted_entities:
        # ... save RawIngestion ...

        if needs_extraction(source):
            extracted_data = await extract_entity(raw_ingestion.id, db)
        else:
            # Deterministic extraction
            attributes = self._extract_entity_from_raw(raw_item, source, orchestration_run_id)

            # ✅ CLASSIFY entity_class from data, don't hardcode
            entity_class = classify_entity(attributes)

            extracted_data = {
                "source": source,
                "entity_class": entity_class,  # ✅ DERIVED from data
                "attributes": json.dumps(attributes),
            }
```

**Benefits:**
- `entity_class` derived from data (time-bounded → event, has location → place, etc.)
- Classifier uses universal rules (location presence, time-boundedness)
- No hardcoding of entity types

---

## Phase 3: Complete Persistence Pipeline

### 3.1 Current State (Broken Pipeline)

**What Works:**
```
Query → Orchestration → Connectors → Deduplication → Persistence
                                                         ↓
                                              RawIngestion (✅)
                                                         ↓
                                              ExtractedEntity (✅)
                                                         ↓
                                                    [STOPS HERE] ❌
```

**What's Missing:**
```
ExtractedEntity → Merging → Entity (final table)
                                ↓
                          Frontend Display
```

### 3.2 Entity Finalization Design

**New Module:** `engine/orchestration/entity_finalizer.py`

```python
"""Entity Finalization - Bridge from ExtractedEntity to Entity table."""

from typing import List, Dict, Optional
from prisma import Prisma
from prisma.models import ExtractedEntity, Entity
from engine.extraction.merging import EntityMerger
from engine.extraction.deduplication import SlugGenerator

class EntityFinalizer:
    """Finalize entities from extraction to published Entity records."""

    def __init__(self, db: Prisma):
        self.db = db
        self.merger = EntityMerger()
        self.slug_generator = SlugGenerator()

    async def finalize_entities(
        self,
        orchestration_run_id: str
    ) -> Dict[str, int]:
        """
        Finalize all ExtractedEntity records for an orchestration run.

        Process:
        1. Load all ExtractedEntity records for this run
        2. Group by deduplication key (slug or external_id)
        3. Merge groups using trust hierarchy
        4. Generate slugs for URLs
        5. Upsert to Entity table

        Returns:
            {"entities_created": N, "entities_updated": M, "conflicts": K}
        """

        # 1. Load extracted entities for this run
        extracted_entities = await self.db.extractedentity.find_many(
            where={
                "raw_ingestion": {
                    "orchestration_run_id": orchestration_run_id
                }
            },
            include={"raw_ingestion": True}
        )

        # 2. Group by deduplication key
        entity_groups = self._group_by_identity(extracted_entities)

        # 3. Merge and finalize each group
        stats = {"entities_created": 0, "entities_updated": 0, "conflicts": 0}

        for identity_key, group in entity_groups.items():
            merged_entity = await self._merge_and_finalize(group)

            # 4. Upsert to Entity table
            existing = await self.db.entity.find_unique(where={"slug": merged_entity["slug"]})

            if existing:
                await self.db.entity.update(
                    where={"id": existing.id},
                    data=merged_entity
                )
                stats["entities_updated"] += 1
            else:
                await self.db.entity.create(data=merged_entity)
                stats["entities_created"] += 1

        return stats

    def _group_by_identity(self, extracted_entities: List[ExtractedEntity]) -> Dict[str, List[ExtractedEntity]]:
        """Group extracted entities by identity (external_id or slug)."""
        groups = {}

        for entity in extracted_entities:
            # Priority: external_id > slug
            external_ids = json.loads(entity.external_ids or "{}")

            # Use strongest external ID as key
            if "google" in external_ids:
                key = f"google:{external_ids['google']}"
            elif "osm" in external_ids:
                key = f"osm:{external_ids['osm']}"
            else:
                # Generate slug from name
                attributes = json.loads(entity.attributes)
                key = f"slug:{self.slug_generator.generate(attributes['name'])}"

            if key not in groups:
                groups[key] = []
            groups[key].append(entity)

        return groups

    async def _merge_and_finalize(self, entity_group: List[ExtractedEntity]) -> Dict:
        """Merge multiple ExtractedEntity records into final Entity data."""

        if len(entity_group) == 1:
            # Single source - no merging needed
            return self._finalize_single(entity_group[0])

        # Multi-source merging
        merged = self.merger.merge_entities([
            self._to_merge_input(e) for e in entity_group
        ])

        return merged

    def _finalize_single(self, extracted: ExtractedEntity) -> Dict:
        """Convert single ExtractedEntity to Entity format."""
        attributes = json.loads(extracted.attributes)

        # Generate slug
        slug = self.slug_generator.generate(attributes["name"])

        return {
            "slug": slug,
            "entity_class": extracted.entity_class,
            "entity_name": attributes["name"],
            "summary": attributes.get("summary"),
            "canonical_activities": attributes.get("canonical_activities", []),
            "canonical_roles": attributes.get("canonical_roles", []),
            "canonical_place_types": attributes.get("canonical_place_types", []),
            "canonical_access": attributes.get("canonical_access", []),
            "location_lat": attributes.get("location_lat"),
            "location_lng": attributes.get("location_lng"),
            "address_full": attributes.get("address_full"),
            "contact_phone": attributes.get("contact_phone"),
            "contact_email": attributes.get("contact_email"),
            "contact_website": attributes.get("contact_website"),
            "modules": attributes.get("modules", {}),
            "source_info": {
                "sources": [extracted.source],
                "primary_source": extracted.source,
                "extraction_date": extracted.created_at.isoformat()
            }
        }

    def _to_merge_input(self, extracted: ExtractedEntity) -> Dict:
        """Convert ExtractedEntity to merger input format."""
        attributes = json.loads(extracted.attributes)
        return {
            "source": extracted.source,
            "attributes": attributes,
            "confidence": json.loads(extracted.field_confidence or "{}"),
        }
```

**Slug Generator Implementation:**

```python
# engine/extraction/deduplication.py (enhanced)

import re
from unidecode import unidecode

class SlugGenerator:
    """Generate URL-safe slugs from entity names."""

    def generate(self, name: str, location: Optional[str] = None) -> str:
        """
        Generate slug from entity name.

        Examples:
            "Edinburgh Padel Club" → "edinburgh-padel-club"
            "The Game4Padel - Portobello" → "game4padel-portobello"
        """
        # Remove articles
        slug = re.sub(r'^(the|a|an)\s+', '', name.lower())

        # Remove special characters
        slug = unidecode(slug)  # Convert accents: "Café" → "Cafe"
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)

        # Replace spaces with hyphens
        slug = re.sub(r'\s+', '-', slug.strip())

        # Add location if provided
        if location:
            location_slug = re.sub(r'[^a-z0-9\s-]', '', location.lower())
            location_slug = re.sub(r'\s+', '-', location_slug.strip())
            slug = f"{slug}-{location_slug}"

        # Remove duplicate hyphens
        slug = re.sub(r'-+', '-', slug)

        return slug.strip('-')
```

### 3.3 Integration with Orchestration

**Update:** `engine/orchestration/planner.py`

```python
async def orchestrate(request: IngestRequest) -> OrchestrationReport:
    """Main orchestration flow."""

    # ... existing orchestration logic ...

    # 6. Persist accepted entities
    if request.persist:
        async with PersistenceManager(db=db) as persistence:
            persistence_result = await persistence.persist_entities(
                context.accepted_entities,
                context.errors,
                orchestration_run_id=orchestration_run_id
            )

        # ✅ NEW: Finalize entities to Entity table
        from engine.orchestration.entity_finalizer import EntityFinalizer
        finalizer = EntityFinalizer(db=db)
        finalization_result = await finalizer.finalize_entities(orchestration_run_id)

        # Update report
        report.entities_created = finalization_result["entities_created"]
        report.entities_updated = finalization_result["entities_updated"]
        report.merge_conflicts = finalization_result["conflicts"]

    return report
```

**Benefits:**
- Complete pipeline: Orchestration → Extraction → Merging → Entity table
- Idempotent: Re-running same query updates existing entities (slug-based upsert)
- Data lineage: Entity tracks which sources contributed via source_info
- Frontend ready: Entity table populated with slug URLs

---

## Phase 4: Test Suite Overhaul

### 4.1 Current State (Problem)

**Claimed:** "192 orchestration tests passing"

**Reality:**
- Only 2 tests marked `@pytest.mark.slow` (real integration tests)
- Most tests heavily mock database operations
- Tests verify mock call counts, not actual behavior
- Example: `test_persistence.py` has 47 instances of "mock" - tests nothing real

### 4.2 Testing Strategy

**Principle:** Integration tests are PRIMARY, unit tests are SECONDARY

**Why:**
- Orchestration is inherently an integration system (multi-connector coordination)
- Mocking database operations creates false confidence
- Real tests catch real bugs

**Test Pyramid (Inverted for orchestration):**

```
       ┌─────────────────────────┐
       │  Unit Tests (Minimal)   │  Fast, test pure logic (e.g., slug generation)
       └─────────────────────────┘
              ▲
              │
       ┌──────────────────────────────┐
       │  Integration Tests (Primary) │  Test real DB, real connectors (mocked APIs)
       └──────────────────────────────┘
              ▲
              │
       ┌───────────────────────────────────┐
       │  Smoke Tests (Confidence Check)   │  Test with real APIs (optional, manual)
       └───────────────────────────────────┘
```

### 4.3 Test Refactor Plan

#### 4.3.1 Delete Zombie Tests

**Delete:**
- `tests/engine/orchestration/test_persistence.py` (47 mocks - tests nothing)

**Replace with:**
- `tests/engine/orchestration/test_persistence_integration.py` (real DB tests)

#### 4.3.2 New Integration Test: End-to-End Persistence

File: `tests/engine/orchestration/test_persistence_integration.py` (NEW)

```python
"""Integration tests for orchestration persistence (REAL DATABASE)."""

import pytest
from prisma import Prisma
from engine.orchestration.planner import orchestrate
from engine.orchestration.types import IngestRequest, IngestionMode

@pytest.mark.slow
@pytest.mark.asyncio
async def test_persist_creates_entity_records():
    """
    Test end-to-end persistence: orchestration → Entity table.

    Validates:
    - OrchestrationRun created
    - RawIngestion created
    - ExtractedEntity created
    - Entity created (final table)
    - Slug generated correctly
    """

    # Arrange
    db = Prisma()
    await db.connect()

    # Clean test data
    await db.entity.delete_many(where={"entity_name": {"contains": "Test Padel Club"}})

    request = IngestRequest(
        query="Test Padel Club Edinburgh",
        mode=IngestionMode.DISCOVER_MANY,
        persist=True,
        lens="padel"
    )

    # Act
    report = await orchestrate(request)

    # Assert: OrchestrationRun created
    assert report.orchestration_run_id is not None
    orchestration_run = await db.orchestrationrun.find_unique(
        where={"id": report.orchestration_run_id}
    )
    assert orchestration_run is not None
    assert orchestration_run.query == "Test Padel Club Edinburgh"
    assert orchestration_run.status == "completed"

    # Assert: RawIngestion created
    raw_ingestions = await db.rawingestion.find_many(
        where={"orchestration_run_id": report.orchestration_run_id}
    )
    assert len(raw_ingestions) > 0

    # Assert: ExtractedEntity created
    extracted_entities = await db.extractedentity.find_many(
        where={"raw_ingestion_id": {"in": [r.id for r in raw_ingestions]}}
    )
    assert len(extracted_entities) > 0

    # Assert: Entity created (FINAL TABLE)
    entities = await db.entity.find_many(
        where={"entity_name": {"contains": "Test Padel Club"}}
    )
    assert len(entities) > 0

    entity = entities[0]
    assert entity.slug is not None
    assert entity.entity_class == "place"
    assert entity.slug.startswith("test-padel-club")

    # Assert: Source info populated
    assert entity.source_info is not None
    assert "sources" in entity.source_info

    # Cleanup
    await db.entity.delete(where={"id": entity.id})
    await db.disconnect()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_persist_is_idempotent():
    """
    Test that re-running same query UPDATES existing entity, doesn't duplicate.

    Validates:
    - First run creates Entity
    - Second run updates same Entity (slug-based upsert)
    - No duplicates created
    """

    db = Prisma()
    await db.connect()

    # Clean test data
    await db.entity.delete_many(where={"entity_name": {"contains": "Idempotency Test Club"}})

    request = IngestRequest(
        query="Idempotency Test Club",
        mode=IngestionMode.DISCOVER_MANY,
        persist=True
    )

    # Act: First run
    report1 = await orchestrate(request)
    entities_after_first = await db.entity.find_many(
        where={"entity_name": {"contains": "Idempotency Test Club"}}
    )
    assert len(entities_after_first) == 1
    first_entity_id = entities_after_first[0].id

    # Act: Second run (same query)
    report2 = await orchestrate(request)
    entities_after_second = await db.entity.find_many(
        where={"entity_name": {"contains": "Idempotency Test Club"}}
    )

    # Assert: Still only 1 entity (updated, not duplicated)
    assert len(entities_after_second) == 1
    assert entities_after_second[0].id == first_entity_id  # Same entity

    # Cleanup
    await db.entity.delete(where={"id": first_entity_id})
    await db.disconnect()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_multi_source_merging():
    """
    Test that multi-source data (Serper + Google + OSM) merges correctly.

    Validates:
    - Multiple ExtractedEntity records for same place
    - Merged into single Entity record
    - Trust hierarchy applied (Google coords win over Serper)
    - source_info tracks all contributors
    """

    db = Prisma()
    await db.connect()

    # Clean test data
    await db.entity.delete_many(where={"entity_name": {"contains": "Multi Source Test"}})

    request = IngestRequest(
        query="Multi Source Test Venue Edinburgh",
        mode=IngestionMode.DISCOVER_MANY,
        persist=True
    )

    # Act
    report = await orchestrate(request)

    # Assert: Multiple ExtractedEntity records
    extracted_entities = await db.extractedentity.find_many(
        where={
            "raw_ingestion": {
                "orchestration_run_id": report.orchestration_run_id
            }
        }
    )
    # Expect: Serper + Google Places + OSM = 3 sources
    assert len(extracted_entities) >= 2  # At least 2 sources

    # Assert: Single merged Entity
    entities = await db.entity.find_many(
        where={"entity_name": {"contains": "Multi Source Test"}}
    )
    assert len(entities) == 1

    entity = entities[0]

    # Assert: source_info tracks all contributors
    assert len(entity.source_info["sources"]) >= 2
    assert "serper" in entity.source_info["sources"] or "google_places" in entity.source_info["sources"]

    # Cleanup
    await db.entity.delete(where={"id": entity.id})
    await db.disconnect()
```

**Key Differences from Current Tests:**
- ✅ Uses REAL database (not mocked)
- ✅ Validates actual Entity table records (not mock call counts)
- ✅ Tests end-to-end flow (orchestration → persistence → Entity)
- ✅ Marked `@pytest.mark.slow` (opt-in for CI)

#### 4.3.3 Keep Existing Unit Tests (Selectively)

**Keep tests that validate pure logic:**
- `test_query_features.py` - Query pattern detection
- `test_registry.py` - Connector metadata
- `test_execution_context.py` - Deduplication logic
- `test_types.py` - Type validation

**Refactor tests that mock too much:**
- `test_planner.py` - Reduce mocking, test actual connector selection
- `test_adapters.py` - Test real adapter behavior with mocked API responses

---

## Phase 5: Documentation & Validation

### 5.1 Update Documentation

**Files to Update:**

1. **CLAUDE.md** - Remove references to deleted scripts
2. **conductor/tech-stack.md** - Document Lens configuration system
3. **engine/lenses/README.md** (NEW) - Explain Lens architecture
4. **tests/README.md** - Document testing strategy (integration-first)

### 5.2 Validation Checklist

**Before Merge:**

- [ ] All 13 dead files deleted
- [ ] No import errors: `pytest --collect-only`
- [ ] No references to deleted files: `grep -r "run_seed\|ingest.py" engine/`
- [ ] Lens loader tests pass: `pytest tests/engine/lenses/`
- [ ] Integration tests pass: `pytest -m slow tests/engine/orchestration/`
- [ ] Manual smoke test: `python -m engine.orchestration.cli run "padel Edinburgh" --persist`
- [ ] Entity table populated: `SELECT COUNT(*) FROM "Entity";` returns > 0
- [ ] No hardcoded domain terms in engine: `grep -r "padel\|tennis" engine/orchestration/ engine/extraction/`
- [ ] Commit message follows convention: `refactor(engine): remove vertical-specific hardcoding`

---

## Implementation Plan

### Week 1: Dead Code Cleanup
- **Day 1-2:** Delete 13 dead files, update documentation
- **Day 3:** Validate no import errors, update CLAUDE.md
- **Day 4-5:** Buffer for issues

### Week 2: Hardcoding Refactor (Critical Path)
- **Day 1-3:** Refactor query features + planner (Lens-driven)
- **Day 4:** Refactor entity classifier (generic fields)
- **Day 5:** Refactor persistence (derive entity_class)

### Week 3: Lens Configuration System
- **Day 1-2:** Implement Lens loader
- **Day 3:** Create Padel lens configs (query_vocabulary, connector_rules)
- **Day 4:** Create Wine lens (validation of extensibility)
- **Day 5:** Test lens switching

### Week 4: Complete Persistence Pipeline
- **Day 1-2:** Implement EntityFinalizer
- **Day 3:** Integrate with orchestration
- **Day 4-5:** Test end-to-end persistence

### Week 5: Test Suite Overhaul
- **Day 1-2:** Write integration tests (persistence, merging)
- **Day 3:** Delete zombie tests
- **Day 4-5:** Validate coverage, update docs

---

## Success Metrics

**Vertical-Agnostic Validation:**
- [ ] Wine lens created with ZERO engine code changes
- [ ] Orchestration run with `--lens wine` succeeds
- [ ] No domain terms in `engine/orchestration/` or `engine/extraction/` (except comments)

**Persistence Pipeline:**
- [ ] CLI command `--persist` creates Entity records
- [ ] Entity table populated after orchestration
- [ ] Idempotent: Re-running same query updates, doesn't duplicate

**Test Confidence:**
- [ ] Integration tests pass against real database
- [ ] Smoke test validates multi-source merging
- [ ] Test count drops (delete zombie tests) but confidence increases

**Code Quality:**
- [ ] 13 dead files deleted (~2,500 LOC removed)
- [ ] No TODO comments for core persistence logic
- [ ] All hardcoded violations fixed

---

## Risks & Mitigations

### Risk 1: Lens System Too Complex

**Mitigation:**
- Start with minimal Lens (just query_vocabulary + connector_rules)
- Add features incrementally (don't over-engineer)
- Keep Lens YAML simple (no custom DSL)

### Risk 2: Breaking Existing Tests

**Mitigation:**
- Refactor tests incrementally (one module at a time)
- Keep existing tests passing until new tests validate behavior
- Delete zombie tests AFTER integration tests prove pipeline works

### Risk 3: Performance Regression

**Mitigation:**
- Lens configs cached in memory (loaded once per orchestration)
- No runtime overhead (Lens queries are simple dict lookups)
- Benchmark before/after: orchestration time should be identical

---

## Next Steps

1. **Review this design** - Approve overall approach
2. **Start with Phase 1** - Low-risk dead code cleanup (immediate win)
3. **Prototype Lens loader** - Validate Lens YAML approach works
4. **Implement critical refactors** - Query features + planner
5. **Complete persistence pipeline** - EntityFinalizer integration
6. **Test suite overhaul** - Delete zombie tests, add real tests

---

## Questions for Review

1. **Lens YAML format** - Does the proposed structure make sense? Too complex?
2. **Entity classifier refactor** - Generic field names (`provides_equipment`) vs vertical-specific (`has_courts`) - agree?
3. **Test strategy** - Integration-first approach - acceptable tradeoff (slower tests but higher confidence)?
4. **Implementation timeline** - 5 weeks realistic? Need faster?

---

**End of Design Document**
