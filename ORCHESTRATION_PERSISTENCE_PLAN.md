# Orchestration Persistence: Implementation Plan

**Date:** 2026-01-27
**Status:** Ready for Implementation
**Est. Effort:** 2-3 days (following TDD workflow)
**Priority:** Critical

---

## Overview

This plan fixes 5 critical issues in the orchestration persistence system, transforming it from a non-functional prototype into a production-ready feature that delivers deduplicated, merged entities to the `Entity` table.

**Reference:** See `ORCHESTRATION_PERSISTENCE_SPEC.md` for detailed specifications and requirements.

---

## Implementation Strategy

### Phased Approach

```
Phase 1: Fix Async/Persistence (High Priority, Low Risk)
  └─ Fixes Issue #2 (Google Places data loss)
  └─ Enables reliable testing of remaining phases

Phase 2: Complete Persistence Pipeline (Critical, Medium Risk)
  └─ Fixes Issue #1 (no data in Entity table)
  └─ Integrates extraction and merging

Phase 3: Enhance Connector Selection (Important, Low Risk)
  └─ Fixes Issue #3 (only 2 connectors used)
  └─ Fixes Issue #4 (sports detection)

Phase 4: Add Observability (Nice-to-Have, Low Risk)
  └─ Better error reporting and debugging
```

**Rationale:** Fix data loss first (Phase 1), then complete the pipeline (Phase 2), then optimize selection (Phase 3).

---

## Phase 1: Fix Async Handling & Persistence

**Goal:** Eliminate silent failures in persistence layer, ensure all connector data is saved.

**Issues Fixed:** Issue #2 (Google Places data not persisted)

### Task 1.1: Remove Event Loop Detection

**File:** `engine/orchestration/persistence.py`

**Current Problem:**
```python
def persist_entities_sync(accepted_entities, errors):
    try:
        loop = asyncio.get_running_loop()
        # Already in event loop - cannot use asyncio.run()
        return {
            "persisted_count": 0,  # ← SILENT FAILURE
            "persistence_errors": [{"error": "Cannot persist from within async context"}],
        }
    except RuntimeError:
        return asyncio.run(_persist_async(...))  # Only works if NO event loop
```

**Solution:** Make persistence fully async, remove sync wrapper.

**Changes:**

1. **Rename `persist_entities_sync` → `persist_entities_async`**
   ```python
   async def persist_entities_async(
       accepted_entities: List[Dict[str, Any]],
       errors: List[Dict[str, Any]]
   ) -> Dict[str, Any]:
       """
       Async persistence (no event loop detection).

       Direct async implementation - caller handles event loop management.
       """
       async with PersistenceManager() as persistence:
           return await persistence.persist_entities(accepted_entities, errors)
   ```

2. **Update planner to use async persistence**

   **File:** `engine/orchestration/planner.py:259-263`

   **Current:**
   ```python
   if request.persist:
       persistence_result = persist_entities_sync(context.accepted_entities, context.errors)
   ```

   **New:**
   ```python
   if request.persist:
       persistence_result = await persist_entities_async(context.accepted_entities, context.errors)
   ```

3. **Make `orchestrate()` async**

   **File:** `engine/orchestration/planner.py:175`

   **Current:**
   ```python
   def orchestrate(request: IngestRequest) -> Dict[str, Any]:
   ```

   **New:**
   ```python
   async def orchestrate(request: IngestRequest) -> Dict[str, Any]:
   ```

4. **Update CLI to call async orchestrate**

   **File:** `engine/orchestration/cli.py:207`

   **Current:**
   ```python
   report = orchestrate(request)
   ```

   **New:**
   ```python
   report = asyncio.run(orchestrate(request))
   ```

**Testing:**

```python
# tests/engine/orchestration/test_persistence_async.py

@pytest.mark.asyncio
async def test_persistence_works_in_async_context():
    """Verify persistence works when called from async context."""
    request = IngestRequest(query="test", persist=True)

    # This should NOT fail with "cannot persist from async context"
    report = await orchestrate(request)

    assert report["persisted_count"] > 0
    assert "Cannot persist from within async context" not in str(report.get("persistence_errors", []))


def test_persistence_works_from_cli():
    """Verify CLI can call async orchestrate."""
    # This simulates the CLI context (no existing event loop)
    request = IngestRequest(query="test", persist=True)

    # CLI uses asyncio.run()
    report = asyncio.run(orchestrate(request))

    assert report["persisted_count"] > 0
```

**Verification:**

```bash
# Test that google_places data is now persisted
python -m engine.orchestration.cli run "powerleague portobello" --persist

# Check database
python -c "
from prisma import Prisma
import asyncio

async def check():
    db = Prisma()
    await db.connect()

    # Should now see google_places records
    sources = await db.rawingestion.group_by(by=['source'], count={'_all': True})
    for s in sources:
        print(f'{s[\"source\"]}: {s[\"_count\"][\"_all\"]}')

    await db.disconnect()

asyncio.run(check())
"
# Expected output: serper: 10, google_places: 1-3, sport_scotland: 2
```

---

## Phase 2: Complete Persistence Pipeline

**Goal:** Integrate extraction and merging to deliver final entities in the `Entity` table.

**Issues Fixed:** Issue #1 (no data in Entity table)

### Task 2.1: Create Extraction Integration

**New File:** `engine/orchestration/extraction_integration.py`

**Purpose:** Bridge between orchestration persistence and existing extraction system.

```python
"""
Extraction integration for orchestration persistence.

Handles the extraction phase after RawIngestion/ExtractedEntity creation:
1. Determine if LLM extraction needed (based on source)
2. Run hybrid extraction for unstructured sources (serper)
3. Skip extraction for structured sources (google_places, osm, sport_scotland)
4. Return enriched ExtractedEntity data
"""

from typing import Dict, Any, List
from prisma import Prisma

# Sources that are already structured (skip LLM extraction)
STRUCTURED_SOURCES = {
    "google_places",
    "openstreetmap",
    "sport_scotland",
    "edinburgh_council",
    "open_charge_map"
}

async def needs_extraction(source: str) -> bool:
    """
    Determine if a source needs LLM extraction.

    Structured sources (Google Places, OSM, etc.) have structured APIs
    and don't need LLM extraction. Unstructured sources (Serper) need it.

    Args:
        source: The source name (e.g., "serper", "google_places")

    Returns:
        True if LLM extraction needed, False if already structured
    """
    return source not in STRUCTURED_SOURCES


async def extract_entity(extracted_entity_id: str, db: Prisma) -> Dict[str, Any]:
    """
    Run extraction on an ExtractedEntity if needed.

    For structured sources: Return entity as-is (already has structured data)
    For unstructured sources: Run hybrid extraction (rules + LLM)

    Args:
        extracted_entity_id: ID of the ExtractedEntity record
        db: Connected Prisma database client

    Returns:
        Dict with extraction results:
        - extracted: bool (whether extraction ran)
        - llm_calls: int (number of LLM calls made)
        - entity_data: dict (enriched entity data)
    """
    # Load ExtractedEntity from database
    entity = await db.extractedentity.find_unique(where={"id": extracted_entity_id})

    if not entity:
        raise ValueError(f"ExtractedEntity not found: {extracted_entity_id}")

    # Check if extraction needed
    if not await needs_extraction(entity.source):
        # Structured source - return as-is
        return {
            "extracted": False,
            "llm_calls": 0,
            "entity_data": entity,
            "reason": f"{entity.source} is structured, no extraction needed"
        }

    # Unstructured source - run extraction
    # Import extraction system components
    from engine.extraction.extractors import get_extractor_for_source
    from engine.extraction.hybrid_engine import HybridExtractionEngine

    # Get source-specific extractor
    extractor = get_extractor_for_source(entity.source)

    if not extractor:
        # No extractor available - return as-is with warning
        return {
            "extracted": False,
            "llm_calls": 0,
            "entity_data": entity,
            "reason": f"No extractor found for {entity.source}"
        }

    # Load raw ingestion data
    raw_ingestion = await db.rawingestion.find_unique(
        where={"id": entity.raw_ingestion_id}
    )

    if not raw_ingestion:
        raise ValueError(f"RawIngestion not found: {entity.raw_ingestion_id}")

    # Load raw payload from disk
    import json
    from pathlib import Path

    raw_file = Path(raw_ingestion.file_path)
    if not raw_file.exists():
        raise FileNotFoundError(f"Raw file not found: {raw_file}")

    raw_data = json.loads(raw_file.read_text(encoding="utf-8"))

    # Run hybrid extraction
    engine = HybridExtractionEngine()
    extracted_data = await engine.extract(raw_data, extractor)

    # Update ExtractedEntity.discovered_attributes
    await db.extractedentity.update(
        where={"id": extracted_entity_id},
        data={"discovered_attributes": json.dumps(extracted_data)}
    )

    # Reload updated entity
    updated_entity = await db.extractedentity.find_unique(
        where={"id": extracted_entity_id}
    )

    return {
        "extracted": True,
        "llm_calls": 1 if extracted_data else 0,
        "entity_data": updated_entity,
        "reason": "Hybrid extraction completed"
    }
```

**Testing:**

```python
# tests/engine/orchestration/test_extraction_integration.py

@pytest.mark.asyncio
async def test_structured_source_skips_extraction():
    """Verify google_places skips LLM extraction."""
    assert await needs_extraction("google_places") == False
    assert await needs_extraction("openstreetmap") == False
    assert await needs_extraction("sport_scotland") == False


@pytest.mark.asyncio
async def test_unstructured_source_needs_extraction():
    """Verify serper requires LLM extraction."""
    assert await needs_extraction("serper") == True


@pytest.mark.asyncio
@pytest.mark.slow
async def test_extract_serper_entity(db_with_raw_ingestion):
    """Integration test: Extract a serper entity."""
    # Setup: Create RawIngestion + ExtractedEntity with serper data
    raw_id = await create_test_raw_ingestion(db_with_raw_ingestion, source="serper")
    entity_id = await create_test_extracted_entity(db_with_raw_ingestion, raw_id)

    # Execute extraction
    result = await extract_entity(entity_id, db_with_raw_ingestion)

    # Verify
    assert result["extracted"] == True
    assert result["llm_calls"] >= 0  # May be 0 if rules-only extraction worked
    assert result["entity_data"].discovered_attributes is not None
```

---

### Task 2.2: Create Merging Integration

**New File:** `engine/orchestration/merging_integration.py`

**Purpose:** Bridge between extraction and the existing merging system.

```python
"""
Merging integration for orchestration persistence.

Handles the merging phase after extraction:
1. Group ExtractedEntities by slug/external_id
2. Apply field-level trust hierarchy
3. Create or update Entity records
4. Track source_info provenance
"""

from typing import Dict, Any, List, Optional
from prisma import Prisma
import json
import hashlib
import re


def generate_slug(name: str, location: Optional[str] = None) -> str:
    """
    Generate a URL-safe slug for an entity.

    Slug format: normalized-name-location-hash
    Example: "powerleague-portobello-a3b5"

    Args:
        name: Entity name
        location: Optional location (city, area)

    Returns:
        URL-safe slug string
    """
    # Normalize name: lowercase, remove special chars, collapse spaces
    normalized = name.lower()
    normalized = re.sub(r'[^a-z0-9\s-]', '', normalized)
    normalized = re.sub(r'\s+', '-', normalized.strip())

    # Add location if provided
    if location:
        loc_normalized = location.lower()
        loc_normalized = re.sub(r'[^a-z0-9\s-]', '', loc_normalized)
        loc_normalized = re.sub(r'\s+', '-', loc_normalized.strip())
        normalized = f"{normalized}-{loc_normalized}"

    # Add short hash for uniqueness (first 4 chars of SHA1)
    hash_input = f"{name}{location or ''}"
    hash_short = hashlib.sha1(hash_input.encode()).hexdigest()[:4]

    slug = f"{normalized}-{hash_short}"

    # Truncate if too long (max 100 chars)
    if len(slug) > 100:
        slug = slug[:96] + hash_short

    return slug


def get_trust_score(source: str) -> float:
    """
    Get trust score for a source (used for field-level merging).

    Trust hierarchy:
    - Admin (manual): 1.00 (not used in orchestration)
    - Official (govt): 0.90-0.95
    - Authoritative (Google): 0.95
    - Crowdsourced (OSM): 0.70
    - Web search (Serper): 0.75

    Args:
        source: Source name (e.g., "google_places")

    Returns:
        Trust score from 0.0 to 1.0
    """
    trust_scores = {
        "google_places": 0.95,
        "sport_scotland": 0.90,
        "edinburgh_council": 0.90,
        "open_charge_map": 0.80,
        "serper": 0.75,
        "openstreetmap": 0.70,
    }
    return trust_scores.get(source, 0.50)  # Default to low trust


async def merge_extracted_entities(
    extracted_entity_ids: List[str],
    db: Prisma
) -> Dict[str, Any]:
    """
    Merge multiple ExtractedEntities into a single Entity record.

    Process:
    1. Load all ExtractedEntities
    2. Generate slug for deduplication
    3. Apply field-level trust hierarchy
    4. Create or update Entity record (upsert)
    5. Track source_info provenance

    Args:
        extracted_entity_ids: List of ExtractedEntity IDs to merge
        db: Connected Prisma database client

    Returns:
        Dict with merge results:
        - entity_id: ID of created/updated Entity
        - created: bool (True if new, False if updated)
        - sources_merged: int (number of sources merged)
        - slug: The generated slug
    """
    # Load all ExtractedEntities
    entities = await db.extractedentity.find_many(
        where={"id": {"in": extracted_entity_ids}}
    )

    if not entities:
        raise ValueError("No entities found to merge")

    # Parse attributes from JSON
    parsed_entities = []
    for entity in entities:
        attrs = json.loads(entity.attributes) if entity.attributes else {}
        discovered = json.loads(entity.discovered_attributes) if entity.discovered_attributes else {}
        external_ids = json.loads(entity.external_ids) if entity.external_ids else {}

        parsed_entities.append({
            "id": entity.id,
            "source": entity.source,
            "trust": get_trust_score(entity.source),
            "attributes": attrs,
            "discovered": discovered,
            "external_ids": external_ids,
        })

    # Sort by trust (highest first)
    parsed_entities.sort(key=lambda e: e["trust"], reverse=True)

    # Generate slug from highest-trust name
    primary_entity = parsed_entities[0]
    primary_name = primary_entity["attributes"].get("name") or primary_entity["discovered"].get("name") or "unknown"
    primary_location = primary_entity["attributes"].get("city") or primary_entity["attributes"].get("address", "").split(",")[-1].strip()

    slug = generate_slug(primary_name, primary_location)

    # Merge fields using trust hierarchy
    merged_fields = {}
    source_info = {}  # Track which source provided which field

    field_names = [
        "name", "address", "city", "postcode", "country",
        "latitude", "longitude", "phone", "email", "website",
        "opening_hours", "description"
    ]

    for field in field_names:
        best_value = None
        best_source = None
        best_trust = 0.0

        for entity in parsed_entities:
            # Check attributes first, then discovered
            value = entity["attributes"].get(field) or entity["discovered"].get(field)

            if value and entity["trust"] > best_trust:
                best_value = value
                best_source = entity["source"]
                best_trust = entity["trust"]

        if best_value:
            merged_fields[field] = best_value
            source_info[field] = {
                "source": best_source,
                "trust": best_trust
            }

    # Merge external IDs (keep all)
    merged_external_ids = {}
    for entity in parsed_entities:
        merged_external_ids.update(entity["external_ids"])

    # Build Entity data
    entity_data = {
        "entity_name": merged_fields.get("name", "Unknown"),
        "entity_class": "place",  # All orchestration entities are places for now
        "slug": slug,
        "summary": merged_fields.get("description"),
        "attributes": json.dumps(merged_fields),
        "modules": {},  # Empty modules for now (vertical-specific data)
        "street_address": merged_fields.get("address"),
        "city": merged_fields.get("city"),
        "postcode": merged_fields.get("postcode"),
        "country": merged_fields.get("country", "GB"),
        "latitude": merged_fields.get("latitude"),
        "longitude": merged_fields.get("longitude"),
        "phone": merged_fields.get("phone"),
        "email": merged_fields.get("email"),
        "website_url": merged_fields.get("website"),
        "opening_hours": merged_fields.get("opening_hours"),
        "source_info": source_info,
        "external_ids": merged_external_ids,
    }

    # Upsert Entity (create if not exists, update if exists)
    entity = await db.entity.upsert(
        where={"slug": slug},
        data={
            "create": entity_data,
            "update": {
                **entity_data,
                # Preserve existing fields if not in new data
                "updatedAt": None,  # Auto-updated by Prisma
            }
        }
    )

    created = entity.createdAt == entity.updatedAt  # If timestamps match, was just created

    return {
        "entity_id": entity.id,
        "created": created,
        "sources_merged": len(parsed_entities),
        "slug": slug,
        "entity": entity,
    }
```

**Testing:**

```python
# tests/engine/orchestration/test_merging_integration.py

def test_generate_slug():
    """Verify slug generation."""
    slug = generate_slug("Powerleague Portobello", "Edinburgh")
    assert "powerleague" in slug
    assert "portobello" in slug
    assert "edinburgh" in slug
    assert len(slug) <= 100


def test_trust_scores():
    """Verify trust hierarchy."""
    assert get_trust_score("google_places") == 0.95
    assert get_trust_score("sport_scotland") == 0.90
    assert get_trust_score("serper") == 0.75
    assert get_trust_score("openstreetmap") == 0.70

    # Google should win over Serper
    assert get_trust_score("google_places") > get_trust_score("serper")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_merge_multiple_sources(db_with_extracted_entities):
    """Integration test: Merge entities from multiple sources."""
    # Setup: Create ExtractedEntities from serper, google_places
    serper_id = await create_test_extracted_entity(
        db_with_extracted_entities,
        source="serper",
        attributes={"name": "Powerleague", "address": "123 Street"}
    )

    google_id = await create_test_extracted_entity(
        db_with_extracted_entities,
        source="google_places",
        attributes={"name": "Powerleague Portobello", "latitude": 55.95, "longitude": -3.11, "phone": "0131 123 4567"}
    )

    # Execute merge
    result = await merge_extracted_entities([serper_id, google_id], db_with_extracted_entities)

    # Verify
    assert result["created"] == True
    assert result["sources_merged"] == 2

    entity = result["entity"]
    assert entity.entity_name == "Powerleague Portobello"  # Google wins (higher trust)
    assert entity.phone == "0131 123 4567"  # Google data
    assert entity.latitude == 55.95

    # Check source_info tracks provenance
    source_info = entity.source_info
    assert source_info["name"]["source"] == "google_places"
    assert source_info["phone"]["source"] == "google_places"


@pytest.mark.asyncio
async def test_merge_idempotent(db_with_extracted_entities):
    """Verify re-merging same entities updates, doesn't duplicate."""
    # Setup
    entity_id = await create_test_extracted_entity(db_with_extracted_entities)

    # Merge once
    result1 = await merge_extracted_entities([entity_id], db_with_extracted_entities)
    slug1 = result1["slug"]

    # Merge again
    result2 = await merge_extracted_entities([entity_id], db_with_extracted_entities)
    slug2 = result2["slug"]

    # Verify same entity updated
    assert slug1 == slug2
    assert result1["entity_id"] == result2["entity_id"]

    # Check only 1 Entity record in DB
    count = await db_with_extracted_entities.entity.count()
    assert count == 1
```

---

### Task 2.3: Integrate Extraction and Merging into Persistence

**File:** `engine/orchestration/persistence.py`

**Changes:**

```python
# Add imports at top
from engine.orchestration.extraction_integration import extract_entity
from engine.orchestration.merging_integration import merge_extracted_entities

# Modify persist_entities method (line 51)
async def persist_entities(
    self, accepted_entities: List[Dict[str, Any]], errors: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Persist accepted entities to the database with full pipeline.

    Pipeline:
    1. Save raw payload to disk
    2. Create RawIngestion + ExtractedEntity
    3. Run extraction (if needed)
    4. Merge to Entity table

    Args:
        accepted_entities: List of accepted (deduplicated) candidate dicts
        errors: List to append persistence errors to

    Returns:
        Dict with persistence statistics:
        - persisted_count: Number of entities saved to ExtractedEntity
        - extracted_count: Number of entities that ran extraction
        - merged_count: Number of final Entity records created
        - persistence_errors: List of errors
    """
    persisted_count = 0
    extracted_count = 0
    merged_count = 0
    persistence_errors = []

    # Phase 1: Create RawIngestion + ExtractedEntity (existing code)
    extracted_entity_ids = []

    for candidate in accepted_entities:
        try:
            # ... existing code to create RawIngestion + ExtractedEntity ...
            # (Keep all existing code from lines 73-117)

            # Track extracted entity IDs for later phases
            extracted_entity_ids.append(extracted_entity.id)
            persisted_count += 1

        except Exception as e:
            # ... existing error handling ...

    # Phase 2: Run Extraction (NEW)
    for entity_id in extracted_entity_ids:
        try:
            extraction_result = await extract_entity(entity_id, self.db)
            if extraction_result["extracted"]:
                extracted_count += 1
        except Exception as e:
            persistence_errors.append({
                "phase": "extraction",
                "entity_id": entity_id,
                "error": str(e),
            })
            # Continue with other entities

    # Phase 3: Merge to Entity table (NEW)
    # Group entities by candidate (already deduplicated in ExecutionContext)
    # For orchestration, each accepted entity is unique, so merge individually
    for entity_id in extracted_entity_ids:
        try:
            merge_result = await merge_extracted_entities([entity_id], self.db)
            if merge_result["created"] or not merge_result["created"]:  # Count both creates and updates
                merged_count += 1
        except Exception as e:
            persistence_errors.append({
                "phase": "merging",
                "entity_id": entity_id,
                "error": str(e),
            })
            # Continue with other entities

    return {
        "persisted_count": persisted_count,
        "extracted_count": extracted_count,
        "merged_count": merged_count,
        "persistence_errors": persistence_errors,
    }
```

**Update Planner to Report All Phases:**

**File:** `engine/orchestration/planner.py:256-278`

```python
# After persistence (existing code at line 259)
if request.persist:
    persistence_result = await persist_entities_async(context.accepted_entities, context.errors)
    persisted_count = persistence_result["persisted_count"]
    extracted_count = persistence_result.get("extracted_count", 0)  # NEW
    merged_count = persistence_result.get("merged_count", 0)  # NEW
    persistence_errors = persistence_result["persistence_errors"]

# Build structured report (existing code at line 266)
report = {
    "query": request.query,
    "candidates_found": len(context.candidates),
    "accepted_entities": len(context.accepted_entities),
    "connectors": context.metrics,
    "errors": context.errors,
}

# Add persistence info if persist was enabled (existing)
if request.persist:
    report["persisted_count"] = persisted_count
    report["extracted_count"] = extracted_count  # NEW
    report["merged_count"] = merged_count  # NEW
    report["persistence_errors"] = persistence_errors
```

**Update CLI Report Formatting:**

**File:** `engine/orchestration/cli.py:90-94`

```python
# Add extraction and merging info to report (after line 92)
if "persisted_count" in report:
    lines.append(f"  Persisted to DB:     {colorize(str(report['persisted_count']), Colors.GREEN)}")

    # NEW: Show extraction and merging counts
    if "extracted_count" in report:
        lines.append(f"  Extracted Entities:  {colorize(str(report['extracted_count']), Colors.GREEN)}")
    if "merged_count" in report:
        lines.append(f"  Merged Entities:     {colorize(str(report['merged_count']), Colors.GREEN)}")
```

**Testing:**

```python
# tests/engine/orchestration/test_complete_pipeline.py

@pytest.mark.asyncio
@pytest.mark.slow
async def test_complete_persistence_pipeline():
    """
    End-to-end test: Orchestrate → Persist → Extract → Merge → Entity.

    This is the critical integration test that verifies the entire pipeline works.
    """
    # Setup
    request = IngestRequest(
        query="powerleague portobello",
        ingestion_mode=IngestionMode.DISCOVER_MANY,
        persist=True
    )

    # Execute full orchestration
    report = await orchestrate(request)

    # Verify report
    assert report["persisted_count"] > 0
    assert report["extracted_count"] >= 0  # Some sources skip extraction
    assert report["merged_count"] > 0  # CRITICAL: Final entities created

    # Verify database state
    async with Prisma() as db:
        # Check Entity table (final destination)
        entity_count = await db.entity.count()
        assert entity_count > 0, "Entity table should have records after --persist"

        # Check entities have proper data
        entities = await db.entity.find_many()
        for entity in entities:
            assert entity.entity_name  # Has name
            assert entity.slug  # Has slug
            assert entity.source_info  # Has provenance tracking

            # At least one of address or coordinates
            assert entity.street_address or (entity.latitude and entity.longitude)


@pytest.mark.asyncio
async def test_persistence_creates_more_entities_than_final():
    """Verify merging deduplicates across sources."""
    request = IngestRequest(query="powerleague portobello", persist=True)
    report = await orchestrate(request)

    # Multiple sources may find same entity
    # After merging, should have fewer final entities
    assert report["merged_count"] <= report["persisted_count"]
```

**Verification:**

```bash
# Run full pipeline
python -m engine.orchestration.cli run "powerleague portobello" --persist

# Expected output:
# Persisted to DB:     8
# Extracted Entities:  8
# Merged Entities:     3

# Verify Entity table populated
python -c "
from prisma import Prisma
import asyncio

async def check():
    db = Prisma()
    await db.connect()

    count = await db.entity.count()
    print(f'Entity count: {count}')
    assert count > 0, 'Entity table should have records!'

    entities = await db.entity.find_many(take=3)
    for e in entities:
        print(f'  - {e.entity_name} ({e.slug})')
        print(f'    Sources: {list(e.source_info.keys()) if e.source_info else \"none\"}')

    await db.disconnect()

asyncio.run(check())
"
```

---

## Phase 3: Enhance Connector Selection

**Goal:** Improve connector selection intelligence to use more sources appropriately.

**Issues Fixed:** Issue #3 (only 2 connectors), Issue #4 (sports detection)

### Task 3.1: Expand Sports Keyword Detection

**File:** `engine/orchestration/planner.py:153-171`

**Changes:**

```python
def _is_sports_related(query: str) -> bool:
    """
    Detect if query is sports-related.

    Checks for:
    - Sport types (padel, tennis, football, etc.)
    - Venue types (court, pitch, arena, etc.)
    - Major UK sports brands (Powerleague, Goals, Nuffield, David Lloyd)

    Args:
        query: The search query string

    Returns:
        True if query contains sports-related terms
    """
    normalized = query.lower()

    sports_keywords = [
        # Sport types
        "padel", "tennis", "football", "rugby", "swimming", "pool", "pools",
        "sport", "sports", "gym", "fitness", "badminton", "squash", "basketball",
        "volleyball", "hockey", "cricket",

        # Venue types
        "court", "courts", "pitch", "pitches", "arena", "arenas",
        "stadium", "leisure", "leisure centre", "sports centre",

        # Generic terms
        "club", "clubs", "league", "leagues", "tournament", "training",

        # UK Major Brands (Recommended)
        "powerleague", "goals", "nuffield", "david lloyd", "puregym",
        "everyone active", "better", "places for people",
    ]

    return any(keyword in normalized for keyword in sports_keywords)
```

**Testing:**

```python
# tests/engine/orchestration/test_sports_detection.py

def test_sports_brand_detection():
    """Verify major sports brands are detected."""
    assert _is_sports_related("powerleague portobello") == True
    assert _is_sports_related("goals soccer centre edinburgh") == True
    assert _is_sports_related("nuffield health gym") == True
    assert _is_sports_related("david lloyd tennis") == True


def test_sports_venue_types():
    """Verify venue types are detected."""
    assert _is_sports_related("leisure centre edinburgh") == True
    assert _is_sports_related("sports arena") == True
    assert _is_sports_related("tennis courts") == True


def test_non_sports_queries():
    """Verify false positives are avoided."""
    assert _is_sports_related("pizza restaurant edinburgh") == False
    assert _is_sports_related("coffee shop portobello") == False
    assert _is_sports_related("hotel near airport") == False
```

---

### Task 3.2: Improve Connector Selection Logic

**File:** `engine/orchestration/planner.py:28-93`

**Changes:**

```python
def select_connectors(request: IngestRequest) -> List[str]:
    """
    Select which connectors to run for the given request.

    Enhanced selection logic:
    - Brand searches use multiple sources (serper + osm + google + domain)
    - Category searches use broad discovery (serper + osm)
    - Sports queries always include sport_scotland
    - Edinburgh queries include edinburgh_council
    - Free sources (OSM) used more liberally

    Args:
        request: The ingestion request containing query and parameters

    Returns:
        List of connector names to execute, ordered by phase
    """
    query_features = QueryFeatures.extract(request.query, request)

    # Detect special query types
    is_sports_query = _is_sports_related(request.query)
    is_edinburgh_query = _is_edinburgh_related(request.query)  # NEW function
    is_category_search = query_features.looks_like_category_search

    # Initialize connector sets by phase
    discovery_connectors = []
    enrichment_connectors = []

    # Selection rules
    if request.ingestion_mode == IngestionMode.RESOLVE_ONE:
        # RESOLVE_ONE: Minimal discovery, focused enrichment
        if not is_category_search:
            enrichment_connectors.append("google_places")
        else:
            discovery_connectors.append("serper")
            enrichment_connectors.append("google_places")

    else:  # DISCOVER_MANY (most common)
        # Always use serper for web discovery
        discovery_connectors.append("serper")

        # Add OSM for category searches OR brand searches (NEW: more liberal)
        # OSM is free and has good coverage, use it widely
        if is_category_search or _is_brand_search(request.query):  # NEW function
            discovery_connectors.append("openstreetmap")

        # Always use google_places for authoritative enrichment
        enrichment_connectors.append("google_places")

        # Domain-specific connectors (all free)
        if is_sports_query:
            enrichment_connectors.append("sport_scotland")

        if is_edinburgh_query:
            enrichment_connectors.append("edinburgh_council")

        # EV/charging queries (NEW)
        if _is_ev_related(request.query):  # NEW function
            enrichment_connectors.append("open_charge_map")

    # Apply budget-aware gating
    selected_connectors = discovery_connectors + enrichment_connectors

    if request.budget_usd is not None:
        selected_connectors = _apply_budget_gating(selected_connectors, request.budget_usd)

    return selected_connectors


def _is_edinburgh_related(query: str) -> bool:
    """Detect if query is Edinburgh-specific."""
    normalized = query.lower()
    return any(term in normalized for term in [
        "edinburgh", "leith", "portobello", "corstorphine",
        "morningside", "stockbridge", "bruntsfield"
    ])


def _is_brand_search(query: str) -> bool:
    """
    Detect if query is searching for a specific brand.

    Brand searches benefit from multiple sources for validation.
    """
    normalized = query.lower()

    # Common brand indicators
    brand_patterns = [
        # Sports brands
        "powerleague", "goals", "nuffield", "david lloyd", "virgin active",
        # Gym brands
        "puregym", "the gym", "anytime fitness", "fitness first",
        # Leisure operators
        "everyone active", "better", "places for people",
        # Other chains
        "starbucks", "costa", "wetherspoons", "tesco", "sainsburys"
    ]

    return any(brand in normalized for brand in brand_patterns)


def _is_ev_related(query: str) -> bool:
    """Detect if query is EV/charging-related."""
    normalized = query.lower()
    return any(term in normalized for term in [
        "ev", "electric vehicle", "charging", "charger", "charge point",
        "supercharger", "rapid charger", "tesla"
    ])
```

**Testing:**

```python
# tests/engine/orchestration/test_connector_selection.py

def test_powerleague_selects_multiple_connectors():
    """Brand search should use multiple sources."""
    request = IngestRequest(
        query="powerleague portobello",
        ingestion_mode=IngestionMode.DISCOVER_MANY
    )

    connectors = select_connectors(request)

    # Should include:
    # - serper (discovery)
    # - openstreetmap (discovery, free)
    # - google_places (enrichment)
    # - sport_scotland (sports domain)
    assert "serper" in connectors
    assert "openstreetmap" in connectors
    assert "google_places" in connectors
    assert "sport_scotland" in connectors
    assert len(connectors) >= 4


def test_category_search_uses_broad_discovery():
    """Category search should use multiple discovery sources."""
    request = IngestRequest(
        query="tennis courts edinburgh",
        ingestion_mode=IngestionMode.DISCOVER_MANY
    )

    connectors = select_connectors(request)

    assert "serper" in connectors
    assert "openstreetmap" in connectors
    assert "sport_scotland" in connectors


def test_edinburgh_council_triggered():
    """Edinburgh-specific queries should include council data."""
    request = IngestRequest(
        query="libraries in edinburgh",
        ingestion_mode=IngestionMode.DISCOVER_MANY
    )

    connectors = select_connectors(request)
    assert "edinburgh_council" in connectors
```

---

## Phase 4: Add Observability

**Goal:** Better error reporting and debugging capabilities.

### Task 4.1: Add Pipeline Stage Tracking

**File:** `engine/orchestration/cli.py`

**Changes:** Add pipeline stages section to report:

```python
# In format_report() function, after Connector Metrics section (around line 126)

# NEW: Pipeline Stages section
if "extracted_count" in report or "merged_count" in report:
    lines.append(colorize("Pipeline Stages:", Colors.BOLD))
    lines.append(colorize("-" * 80, Colors.GRAY))

    if "persisted_count" in report:
        status = colorize("✓", Colors.GREEN)
        lines.append(f"  {status} Persistence:  {report['persisted_count']} RawIngestion + ExtractedEntity created")

    if "extracted_count" in report:
        status = colorize("✓", Colors.GREEN)
        lines.append(f"  {status} Extraction:   {report['extracted_count']} entities enriched")

    if "merged_count" in report:
        status = colorize("✓", Colors.GREEN)
        lines.append(f"  {status} Merging:      {report['merged_count']} Entity records created/updated")

    lines.append("")
```

---

### Task 4.2: Add Entity Summary to Report

**File:** `engine/orchestration/cli.py`

**Changes:** Add final entities summary (optional, nice-to-have):

```python
# In format_report(), after Pipeline Stages (optional)

if "final_entities" in report and report["final_entities"]:
    lines.append(colorize("Final Entities:", Colors.BOLD))
    lines.append(colorize("-" * 80, Colors.GRAY))

    for i, entity in enumerate(report["final_entities"][:5], 1):  # Limit to 5
        name = entity.get("name", "Unknown")
        sources = entity.get("sources", [])
        completeness = entity.get("completeness", 0)

        lines.append(f"  {i}. {colorize(name, Colors.CYAN)}")
        lines.append(f"     Sources: {', '.join(sources)}")
        lines.append(f"     Completeness: {completeness}%")
        lines.append("")
```

**Update planner to include entity summary:**

```python
# In planner.py, after merge phase

if request.persist and merged_count > 0:
    # Load final entities for report
    async with Prisma() as db:
        final_entities = await db.entity.find_many(
            take=5,
            order={"updatedAt": "desc"}
        )

        entity_summaries = []
        for entity in final_entities:
            sources = list(entity.source_info.keys()) if entity.source_info else []
            total_fields = 20  # Approximate
            filled_fields = sum(1 for f in [
                entity.entity_name, entity.street_address, entity.latitude,
                entity.phone, entity.website_url, entity.email
            ] if f)
            completeness = int((filled_fields / total_fields) * 100)

            entity_summaries.append({
                "name": entity.entity_name,
                "sources": sources,
                "completeness": completeness,
            })

        report["final_entities"] = entity_summaries
```

---

## Testing Strategy

### Test Pyramid

```
                    /\
                   /  \
                  / E2E \ ← 5 tests (slow, critical paths)
                 /______\
                /        \
               / Integration \ ← 20 tests (medium, component combos)
              /______________\
             /                \
            /      Unit        \ ← 50 tests (fast, logic verification)
           /____________________\
```

### Critical Test Cases

1. **End-to-End Pipeline Test** (E2E, slow)
   ```python
   test_complete_persistence_pipeline()
   # Verifies: Orchestrate → Persist → Extract → Merge → Entity table populated
   ```

2. **Async Context Handling** (Integration)
   ```python
   test_persistence_works_in_async_context()
   test_persistence_works_from_cli()
   # Verifies: No silent failures in different event loop contexts
   ```

3. **Multi-Source Merging** (Integration)
   ```python
   test_merge_multiple_sources()
   # Verifies: Trust hierarchy, field-level merging, provenance tracking
   ```

4. **Connector Selection** (Unit)
   ```python
   test_powerleague_selects_multiple_connectors()
   test_sports_detection()
   # Verifies: Intelligent selection, domain triggers
   ```

5. **Idempotency** (Integration)
   ```python
   test_merge_idempotent()
   # Verifies: Re-running same query updates, doesn't duplicate
   ```

### Coverage Goals

- **Overall:** > 80% coverage
- **Critical Paths:** 100% coverage (persistence, extraction, merging)
- **New Code:** 100% coverage (all new functions must have tests)

---

## Rollout Plan

### Phase 1: Development (Day 1-2)

1. **Morning:** Implement async handling fixes (Task 1.1)
   - Test in isolation
   - Verify google_places data now persisted

2. **Afternoon:** Implement extraction integration (Task 2.1)
   - Create extraction_integration.py
   - Write unit tests
   - Test with mock data

3. **Evening:** Implement merging integration (Task 2.2)
   - Create merging_integration.py
   - Write unit tests
   - Test with mock data

### Phase 2: Integration (Day 2-3)

4. **Morning:** Integrate extraction + merging into persistence (Task 2.3)
   - Modify persistence.py
   - Write integration tests
   - Run E2E test

5. **Afternoon:** Enhance connector selection (Tasks 3.1, 3.2)
   - Update sports detection
   - Improve selection logic
   - Test with various queries

6. **Evening:** Add observability (Task 4.1, 4.2)
   - Update CLI reporting
   - Add pipeline stage tracking
   - Test final output

### Phase 3: Verification (Day 3)

7. **Testing:**
   - Run full test suite (pytest)
   - Run live tests with real queries
   - Verify database state

8. **Documentation:**
   - Update README with new --persist behavior
   - Document pipeline stages
   - Add troubleshooting guide

9. **Code Review:**
   - Self-review all changes
   - Check for edge cases
   - Verify error handling

---

## Risk Mitigation

### High-Risk Items

1. **Risk:** Extraction system integration breaks existing extraction CLI
   - **Mitigation:** Use separate integration layer, don't modify extraction core
   - **Testing:** Run existing extraction tests after changes

2. **Risk:** Async changes break tests
   - **Mitigation:** Update all tests to handle async properly
   - **Testing:** Run full test suite with pytest-asyncio

3. **Risk:** Performance degradation (LLM calls for every entity)
   - **Mitigation:** Skip LLM for structured sources (google_places, osm, sport_scotland)
   - **Testing:** Measure E2E time, ensure < 10 seconds for 10 entities

4. **Risk:** Database schema changes needed
   - **Mitigation:** Use existing schema, add optional OrchestrationRun table later
   - **Testing:** Verify schema compatibility

### Rollback Plan

If critical issues arise:

1. **Revert CLI changes:** `git revert <commit>` to restore working CLI
2. **Disable persistence:** Add `if False:` guard around persist logic
3. **Use existing extraction CLI:** Fall back to manual extraction workflow

---

## Success Criteria

### Must Have (Blocker)

- [ ] Entity table populated after `--persist` (Issue #1 fixed)
- [ ] All connector data persisted (Issue #2 fixed)
- [ ] No silent failures in any context
- [ ] All tests pass (>80% coverage)

### Should Have (Important)

- [ ] 3+ connectors used for brand searches (Issue #3 fixed)
- [ ] Sports detection works for major brands (Issue #4 fixed)
- [ ] Pipeline stages visible in CLI report
- [ ] Idempotent: re-running updates, doesn't duplicate

### Nice to Have (Enhancement)

- [ ] Entity summary in CLI report
- [ ] OrchestrationRun tracking table
- [ ] Performance < 10 seconds for 10 entities
- [ ] Confidence scores per field

---

## Post-Implementation

### Documentation Updates

1. **README.md:**
   - Update `--persist` flag description
   - Add pipeline stages diagram
   - Document final output format

2. **ARCHITECTURE.md:**
   - Add orchestration persistence section
   - Document data flow end-to-end
   - Explain trust hierarchy

3. **CLAUDE.md:**
   - Update orchestration commands
   - Add persistence examples
   - Document connector selection logic

### Future Enhancements

1. **Orchestration Tracking Table** (OrchestrationRun model)
   - Track query history
   - Link to created entities
   - Enable analytics

2. **Field Confidence Scores**
   - Per-field confidence based on source agreement
   - Display in Entity table
   - Use for UX indicators

3. **Incremental Updates**
   - Detect field changes
   - Update only deltas
   - Preserve manual edits

4. **Relationship Extraction**
   - Extract "plays_at", "coaches_at" relationships
   - Populate EntityRelationship table
   - Enable graph queries

---

## Appendix: File Checklist

### Files Modified

- [ ] `engine/orchestration/persistence.py` (async handling, pipeline integration)
- [ ] `engine/orchestration/planner.py` (async orchestrate, connector selection)
- [ ] `engine/orchestration/cli.py` (async call, enhanced reporting)
- [ ] `engine/orchestration/query_features.py` (sports detection keywords)

### Files Created

- [ ] `engine/orchestration/extraction_integration.py` (extraction bridge)
- [ ] `engine/orchestration/merging_integration.py` (merging bridge)
- [ ] `tests/engine/orchestration/test_persistence_async.py` (async tests)
- [ ] `tests/engine/orchestration/test_extraction_integration.py` (extraction tests)
- [ ] `tests/engine/orchestration/test_merging_integration.py` (merging tests)
- [ ] `tests/engine/orchestration/test_complete_pipeline.py` (E2E tests)
- [ ] `tests/engine/orchestration/test_sports_detection.py` (detection tests)
- [ ] `tests/engine/orchestration/test_connector_selection.py` (selection tests)

### Documentation Updated

- [ ] `README.md` (--persist behavior)
- [ ] `ARCHITECTURE.md` (persistence pipeline)
- [ ] `CLAUDE.md` (orchestration commands)

---

## End of Plan

**Estimated Completion:** 2-3 days (following TDD workflow)

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 1, Task 1.1 (async handling fixes)
3. Follow TDD workflow: Red → Green → Refactor
4. Update plan.md with commit SHAs as work progresses
