# Orchestration Persistence System: Specification Document

**Date:** 2026-01-27
**Author:** Claude Sonnet 4.5
**Status:** Draft
**Priority:** Critical

---

## Executive Summary

The orchestration persistence feature (`--persist` flag) is currently incomplete and dysfunctional. It creates intermediate extraction records but fails to produce final merged entities in the `Entity` table, making the feature unusable for production. This document specifies the required fixes to deliver a working end-to-end persistence pipeline.

### Critical Issues Found

1. **Data Never Reaches Final Destination**: Persistence stops at `ExtractedEntity` table; `Entity` table remains empty
2. **Google Places Data Lost**: Google Places API calls succeed but data not persisted to database
3. **Insufficient Connector Selection**: Only 2 of 6 available connectors used for queries that warrant more
4. **Sports Detection Broken**: Major sports brands like "Powerleague" not recognized as sports queries
5. **Silent Async Failures**: Event loop detection causes persistence to fail silently in async contexts

### Impact

- **User Expectation:** `--persist` flag should deliver deduplicated, merged entities ready for display
- **Current Reality:** Creates orphaned extraction records with no path to final entities
- **Business Impact:** Orchestration feature cannot be used for production data ingestion

---

## Problem Statement

### Current Incomplete Flow

```
┌─────────────┐
│ Orchestrate │ ← User runs CLI with --persist flag
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Persist Entities │ ← Creates RawIngestion + ExtractedEntity
└──────┬───────────┘
       │
       ▼
    [STOPS HERE] ❌
```

**Result:**
- 17 `ExtractedEntity` records created (all serper)
- 0 `Entity` records created
- User gets no usable data

### Expected Complete Flow

```
┌─────────────┐
│ Orchestrate │ ← User runs CLI with --persist flag
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Persist Entities │ ← Creates RawIngestion + ExtractedEntity
└──────┬───────────┘
       │
       ▼
┌────────────────┐
│ Extract Phase  │ ← Structured data extraction (hybrid rules + LLM)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ Dedup Phase    │ ← Cross-source deduplication (already in ExecutionContext)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│ Merge Phase    │ ← Field-level trust hierarchy → Entity table
└────────┬───────┘
         │
         ▼
      ┌──────┐
      │Entity│ ✓ Final deduplicated entities ready for display
      └──────┘
```

---

## Detailed Issues

### Issue 1: Incomplete Persistence Pipeline (CRITICAL)

**Current Code:** `engine/orchestration/persistence.py`

**Problem:**
```python
async def persist_entities(self, accepted_entities, errors):
    # Creates RawIngestion
    raw_ingestion = await self.db.rawingestion.create(...)

    # Creates ExtractedEntity
    await self.db.extractedentity.create(...)

    # MISSING: No extraction, deduplication, or merging to Entity table
```

**Why This Happens:**
- Persistence module was implemented as a standalone component
- Does not integrate with existing extraction/merging pipeline
- Extraction system (`engine/extraction/`) exists but is decoupled from orchestration

**Required Integration Points:**

1. **Extraction Layer** (`engine/extraction/extractors/`)
   - Already has source-specific extractors (serper, google_places, etc.)
   - Need to invoke after persistence creates `ExtractedEntity`

2. **Merging Layer** (`engine/extraction/merging.py`)
   - Handles field-level trust hierarchy
   - Creates final `Entity` records
   - Need to invoke after extraction completes

**Expected Behavior:**

```python
# After persistence creates ExtractedEntity records:
for extracted_entity in created_entities:
    # Phase 1: Run extraction (if needed - some sources are already structured)
    if needs_llm_extraction(extracted_entity.source):
        enriched_entity = await run_extraction(extracted_entity)
    else:
        enriched_entity = extracted_entity

    # Phase 2: Deduplicate across all sources (already happening in ExecutionContext)
    # (This is done BEFORE persistence via context.accept_entity)

    # Phase 3: Merge to Entity table
    final_entity = await merge_to_entity(enriched_entity)
```

---

### Issue 2: Google Places Data Not Persisted

**Evidence:**
- Raw files created: `engine/data/raw/google_places/20260127_085731_*.json` ✓
- RawIngestion records: 0 google_places records in database ❌
- Database shows: 17/17 records from serper only

**Root Cause:** `engine/orchestration/persistence.py:329-359`

```python
def persist_entities_sync(accepted_entities, errors):
    try:
        loop = asyncio.get_running_loop()
        # Already in event loop - cannot use asyncio.run()
        return {
            "persisted_count": 0,  # ← SILENT FAILURE
            "persistence_errors": [{...}],
        }
    except RuntimeError:
        return asyncio.run(_persist_async(...))  # Only reaches here if NO event loop
```

**Problem:**
- If orchestrator runs in an async context (which it does via `asyncio.run()`), persistence silently fails
- Returns `persisted_count: 0` without raising an exception
- CLI shows success even though no data was saved

**Why Google Places Specifically?**
- Timing issue: By the time Google Places results arrive, event loop state has changed
- Serper executes first and might succeed before event loop detection kicks in
- Google Places executes second and hits the async context issue

**Required Fix:**
- Remove the event loop detection logic
- Make persistence fully async-native
- Handle event loop properly instead of trying to detect it

---

### Issue 3: Conservative Connector Selection

**Test Case:** Query: `"powerleague portobello"`

**Connectors Selected:** 2 (serper, google_places)
**Connectors Available:** 6 total

| Connector | Selected? | Why Not? |
|-----------|-----------|----------|
| serper | ✓ | Discovery phase (always selected) |
| google_places | ✓ | Enrichment phase (always selected) |
| openstreetmap | ✗ | Only added for "category search" detection |
| sport_scotland | ✗ | Sports keyword detection failed |
| edinburgh_council | ✗ | No trigger logic implemented |
| open_charge_map | ✗ | No trigger logic implemented |

**Selection Logic:** `engine/orchestration/planner.py:28-93`

```python
def select_connectors(request: IngestRequest) -> List[str]:
    if request.ingestion_mode == IngestionMode.DISCOVER_MANY:
        discovery_connectors.append("serper")

        if query_features.looks_like_category_search:  # ← "powerleague" = specific, not category
            discovery_connectors.append("openstreetmap")  # NEVER TRIGGERED

        enrichment_connectors.append("google_places")

        if is_sports_query:  # ← Sports detection failed
            enrichment_connectors.append("sport_scotland")  # NEVER TRIGGERED
```

**Problems:**

1. **Category vs. Specific Detection Too Strict**
   - "powerleague portobello" detected as specific search (not category)
   - But it's a brand search that benefits from multiple sources
   - OSM has location data for Powerleague venues

2. **Free Connectors Underutilized**
   - OSM ($0.00) not used even when it would add value
   - Conservative strategy wastes free resources

3. **Domain-Specific Triggers Missing**
   - Edinburgh Council: No trigger (should activate for Edinburgh locations)
   - Open Charge Map: No trigger (should activate for EV/charging queries)

**Expected Behavior:**

For "powerleague portobello":
- ✓ serper (discovery)
- ✓ google_places (enrichment, paid)
- ✓ openstreetmap (discovery, free, has venue data)
- ✓ sport_scotland (enrichment, free, sports domain)
- ✗ edinburgh_council (not relevant to sports venues)
- ✗ open_charge_map (not relevant to sports venues)

**Should select 4 connectors, not 2.**

---

### Issue 4: Sports Keyword Detection Broken

**Test Case:** Query: `"powerleague portobello"`
**Expected:** Detect as sports-related
**Actual:** Not detected

**Code:** `engine/orchestration/planner.py:138-173`

```python
def _is_sports_related(query: str) -> bool:
    normalized = query.lower()

    sports_keywords = [
        "padel", "tennis", "football", "rugby", "swimming", "pool", "pools",
        "sport", "sports", "gym", "fitness", "court", "courts", "pitch", "club", "clubs"
    ]

    return any(keyword in normalized for keyword in sports_keywords)
```

**Missing Keywords:**

| Brand/Term | Why Important |
|------------|---------------|
| powerleague | Major UK 5-a-side football chain, 50+ locations |
| league | Common in sports facility names |
| nuffield | Nuffield Health (gyms/pools) |
| david lloyd | David Lloyd Clubs (tennis/fitness) |
| goals | Goals Soccer Centres (5-a-side) |
| arena | Common sports venue suffix |
| leisure | Leisure centres (swimming/sports) |

**Impact:**
- Sport Scotland connector (free, authoritative) not triggered
- Missing official government sports facility data
- Poorer quality results for sports queries

---

### Issue 5: Connector Budget Logic Issues

**Current Code:** `engine/orchestration/planner.py:96-135`

**Problems:**

1. **Budget Gating Happens After Selection**
   ```python
   selected_connectors = discovery_connectors + enrichment_connectors
   if request.budget_usd is not None:
       selected_connectors = _apply_budget_gating(selected_connectors, request.budget_usd)
   ```

   This means:
   - Intelligence selects connectors first
   - Budget filters them out second
   - Results in suboptimal selection (high-cost filtered, low-value kept)

2. **No Cost-Benefit Analysis**
   - Doesn't consider trust level vs. cost
   - Doesn't prefer free high-trust sources (Sport Scotland, OSM) over paid low-trust sources

3. **No Default Budget**
   - If user doesn't specify `--budget`, no filtering happens
   - Could rack up unexpected API costs

**Expected Behavior:**

1. Budget-aware selection from the start
2. Prioritize free high-trust sources
3. Default budget cap (e.g., $0.10 per query)
4. Cost-benefit scoring: `value = trust_level / (cost + 0.01)`

---

## Architecture Requirements

### Persistence Pipeline Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                              │
│  (engine/orchestration/planner.py)                                  │
│                                                                      │
│  1. Select Connectors (intelligent multi-source selection)          │
│  2. Execute Connectors (via adapters)                               │
│  3. Deduplicate Candidates (ExecutionContext.accept_entity)         │
│  4. Persist Accepted Entities (if --persist flag)                   │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER                                │
│  (engine/orchestration/persistence.py)                              │
│                                                                      │
│  For each accepted entity:                                          │
│    1. Save raw payload to disk (data lineage)                       │
│    2. Create RawIngestion record (DB)                               │
│    3. Create ExtractedEntity record (DB)                            │
│    4. [NEW] Invoke extraction pipeline                              │
│    5. [NEW] Invoke merging pipeline                                 │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION LAYER                                 │
│  (engine/extraction/cli.py, engine/extraction/extractors/)          │
│                                                                      │
│  1. Load ExtractedEntity.attributes (JSON)                          │
│  2. Determine if LLM extraction needed                              │
│  3. If needed: Run hybrid extraction (rules + LLM)                  │
│  4. Enrich ExtractedEntity with structured data                     │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                    MERGING LAYER                                    │
│  (engine/extraction/merging.py)                                     │
│                                                                      │
│  1. Load all ExtractedEntity records for this entity (by slug)      │
│  2. Apply field-level trust hierarchy (Admin > Official > Crowdsrc) │
│  3. Merge into single canonical Entity record                       │
│  4. Upsert to Entity table (idempotent)                            │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
                           ▼
                        ┌──────┐
                        │Entity│ ← Final destination (user-facing)
                        └──────┘
```

### Data Flow Diagram

```
Input Query: "powerleague portobello --persist"
│
├─ Orchestration Phase
│  ├─ Select: [serper, google_places, sport_scotland, openstreetmap]
│  ├─ Execute: Parallel API calls
│  ├─ Dedupe: ExecutionContext → 8 accepted entities
│  └─ Result: {candidates: 11, accepted: 8}
│
├─ Persistence Phase [NEW INTEGRATION]
│  ├─ For each accepted entity:
│  │  ├─ Write raw JSON to disk
│  │  ├─ Create RawIngestion (with file_path)
│  │  ├─ Create ExtractedEntity (linked to RawIngestion)
│  │  └─ Track: raw_ingestion_ids[]
│  └─ Result: 8 ExtractedEntity records created
│
├─ Extraction Phase [NEW]
│  ├─ For each ExtractedEntity:
│  │  ├─ Load attributes (already structured for most sources)
│  │  ├─ Skip LLM if structured (serper, google_places, osm)
│  │  ├─ Enrich with canonical dimensions
│  │  └─ Update ExtractedEntity.discovered_attributes
│  └─ Result: 8 enriched ExtractedEntity records
│
└─ Merging Phase [NEW]
   ├─ Group ExtractedEntities by slug/external_id
   ├─ Apply trust hierarchy per field
   │  ├─ Name: google_places (0.95) > serper (0.75)
   │  ├─ Coords: google_places > sport_scotland > openstreetmap
   │  └─ Phone/Website: google_places > openstreetmap
   ├─ Create/Update Entity record (upsert by slug)
   └─ Result: 3-5 final Entity records (post-merge deduplication)

Final Output: Entity table populated with deduplicated entities
```

---

## Functional Requirements

### FR-1: Complete Persistence Pipeline

**Requirement:** When `--persist` flag is used, orchestration must produce final merged entities in the `Entity` table.

**Acceptance Criteria:**
- [ ] `Entity` table contains records after `--persist` run
- [ ] Entity count ≤ ExtractedEntity count (due to merging)
- [ ] All fields populated according to trust hierarchy
- [ ] `source_info` JSON tracks which connectors contributed which fields
- [ ] Idempotent: Re-running same query updates existing entities, doesn't duplicate

**Test Case:**
```bash
# Before
python -c "from prisma import Prisma; import asyncio; asyncio.run(Prisma().connect().entity.count())"
# Output: 0

# Run orchestration
python -m engine.orchestration.cli run "powerleague portobello" --persist

# After
python -c "from prisma import Prisma; import asyncio; asyncio.run(Prisma().connect().entity.count())"
# Output: 3-5 (merged entities)
```

---

### FR-2: All Connector Data Persisted

**Requirement:** Data from all executed connectors must be persisted to the database.

**Acceptance Criteria:**
- [ ] RawIngestion records created for each connector's results
- [ ] ExtractedEntity records created for each raw ingestion
- [ ] Database counts match connector metrics report
- [ ] No silent failures due to async context issues

**Test Case:**
```bash
# Run with multiple connectors
python -m engine.orchestration.cli run "powerleague portobello" --persist

# Verify counts match report
# Report shows: serper (10), google_places (1), sport_scotland (2)
# Database should show: 13 RawIngestion records, 13 ExtractedEntity records
```

---

### FR-3: Intelligent Connector Selection

**Requirement:** Planner must select appropriate connectors based on query features and domain.

**Selection Rules:**

| Query Type | Discovery | Enrichment | Notes |
|------------|-----------|------------|-------|
| Brand search (e.g., "powerleague portobello") | serper, openstreetmap | google_places, sport_scotland (if sports) | Multiple sources for validation |
| Category search (e.g., "tennis courts Edinburgh") | serper, openstreetmap | google_places, sport_scotland (if sports) | Broad discovery needed |
| Specific venue (e.g., "Royal Commonwealth Pool") | serper | google_places | Targeted enrichment |
| Edinburgh location | serper, openstreetmap | google_places, edinburgh_council | Add Council data |
| EV/charging query | serper, openstreetmap | google_places, open_charge_map | Domain-specific |

**Acceptance Criteria:**
- [ ] Sports queries trigger sport_scotland connector
- [ ] Free connectors (OSM) used for category/brand searches
- [ ] Edinburgh queries trigger edinburgh_council connector
- [ ] EV queries trigger open_charge_map connector
- [ ] Minimum 3 connectors for DISCOVER_MANY mode (except budget-constrained)

---

### FR-4: Sports Detection

**Requirement:** Detect sports-related queries to trigger domain-specific connectors.

**Keyword Coverage:**
- [ ] Major chains: powerleague, goals, nuffield, david lloyd
- [ ] Venues: arena, leisure centre, sports centre
- [ ] Generic: league, leagues, tournament

**Acceptance Criteria:**
- [ ] "powerleague portobello" → sport_scotland triggered
- [ ] "nuffield health edinburgh" → sport_scotland triggered
- [ ] "goals soccer centre" → sport_scotland triggered
- [ ] "royal commonwealth pool" → sport_scotland triggered
- [ ] False positive rate < 5% (don't trigger on non-sports queries)

**Test Case:**
```python
from engine.orchestration.planner import _is_sports_related

assert _is_sports_related("powerleague portobello") == True
assert _is_sports_related("nuffield edinburgh") == True
assert _is_sports_related("goals soccer") == True
assert _is_sports_related("david lloyd tennis") == True
assert _is_sports_related("pizza restaurant edinburgh") == False
```

---

### FR-5: Robust Async Handling

**Requirement:** Persistence must work correctly in all event loop contexts.

**Acceptance Criteria:**
- [ ] Works when called from asyncio.run() (CLI context)
- [ ] Works when called from async function (test context)
- [ ] Works when called from existing event loop (web server context)
- [ ] No silent failures - errors are logged and reported
- [ ] Transaction rollback on failure (no partial persistence)

**Test Case:**
```python
# Sync context (CLI)
report = orchestrate(request)
assert report["persisted_count"] > 0

# Async context (test)
async def test():
    report = orchestrate(request)  # Should work
    assert report["persisted_count"] > 0

asyncio.run(test())
```

---

## Non-Functional Requirements

### NFR-1: Performance

- **Extraction Phase:** < 2 seconds per entity (structured sources skip LLM)
- **Merging Phase:** < 500ms per entity (database operations)
- **Total Persistence:** < 5 seconds for 10 entities
- **Parallel Execution:** Where possible (extraction can be parallelized)

### NFR-2: Data Lineage

- **Raw Data:** All raw API responses saved to disk (audit trail)
- **RawIngestion:** Links to file_path for payload retrieval
- **ExtractedEntity:** Links to RawIngestion (provenance)
- **Entity:** source_info JSON tracks which sources contributed which fields

### NFR-3: Idempotency

- **Same Query Twice:** Updates existing entities, doesn't create duplicates
- **Slug-Based Dedup:** Entities merged by slug (generated from name + location)
- **External ID Tracking:** `external_ids` JSON preserves connector IDs

### NFR-4: Error Handling

- **Connector Failures:** Don't block persistence of other sources
- **Extraction Failures:** Log and continue (don't block merging)
- **Merge Conflicts:** Use trust hierarchy to resolve
- **Transaction Safety:** Rollback on critical failures

---

## Database Schema Implications

### Current Schema (Prisma)

```prisma
model RawIngestion {
  id            String   @id @default(cuid())
  source        String
  source_url    String
  file_path     String
  status        String
  hash          String
  metadata_json String?
  created_at    DateTime @default(now())
}

model ExtractedEntity {
  id                    String   @id @default(cuid())
  raw_ingestion_id      String
  source                String
  entity_class          String
  attributes            String?   // JSON
  discovered_attributes String?   // JSON
  external_ids          String?   // JSON
  // ... more fields
}

model Entity {
  id                String     @id @default(cuid())
  entity_name       String
  entity_class      String
  slug              String     @unique
  attributes        String?    // JSON
  modules           Json
  // ... 50+ fields (address, coords, socials, etc.)
  source_info       Json?      // NEW: Track which sources contributed which fields
}
```

### Required Changes

1. **Add OrchestrationRun Tracking** (optional but recommended):
   ```prisma
   model OrchestrationRun {
     id              String   @id @default(cuid())
     query           String
     mode            String   // "discover_many" or "resolve_one"
     status          String   // "success" or "failed"
     candidates_found Int
     accepted_count  Int
     persisted_count Int?
     sources_used    String[] // Array of connector names
     budget_spent_usd Float?
     created_at      DateTime @default(now())

     raw_ingestions  RawIngestion[] // Link to data created
   }
   ```

2. **Link RawIngestion to OrchestrationRun** (optional):
   ```prisma
   model RawIngestion {
     // ... existing fields
     orchestration_run_id String?
     orchestration_run OrchestrationRun? @relation(fields: [orchestration_run_id], references: [id])
   }
   ```

---

## Success Metrics

### Quantitative

- **Entity Table Population:** > 0 records after `--persist` (currently 0)
- **Data Loss:** 0% (all connector results persisted)
- **Connector Coverage:** ≥ 3 connectors per query (currently 2)
- **Sports Query Detection:** > 95% accuracy on test set
- **Performance:** < 10 seconds end-to-end for 10-entity query

### Qualitative

- **User Expectation:** `--persist` delivers final entities, not intermediate records
- **Data Quality:** Merged entities have higher completeness than single-source entities
- **Developer Experience:** Clear error messages, no silent failures
- **Maintainability:** Extraction/merging logic reused from existing pipeline

---

## Out of Scope

### Explicitly Not Included

1. **LLM Extraction Improvements:** Use existing extraction prompts as-is
2. **New Connectors:** Work with existing 6 connectors only
3. **Web UI:** CLI-only feature for now
4. **Real-time Updates:** Batch processing only
5. **Advanced Deduplication:** Use existing slug-based logic
6. **Field Conflict Resolution UI:** Automated trust hierarchy only

### Future Enhancements

1. **Incremental Updates:** Detect changed fields, update only deltas
2. **Entity Relationships:** Extract "plays_at", "coaches_at" relationships
3. **Confidence Scores:** Per-field confidence based on source agreement
4. **Audit Log:** Track entity evolution over time
5. **Smart Budget Allocation:** ML-based connector selection

---

## Appendices

### Appendix A: Trust Hierarchy by Source

| Source | Trust Level | Use For | Avoid For |
|--------|-------------|---------|-----------|
| google_places | 0.95 | Name, address, coords, phone, website, hours | Categories (too generic) |
| sport_scotland | 0.90 | Facility types, sports offered, official names | Commercial details |
| edinburgh_council | 0.90 | Public facility info, council services | Private businesses |
| serper | 0.75 | Discovery, names, basic info | Structured data (unreliable) |
| openstreetmap | 0.70 | Coords, address, basic POI data | Phone, website (often outdated) |
| open_charge_map | 0.80 | EV charging specifics | General venue info |

### Appendix B: Connector Cost & Latency

| Connector | Cost/Call | Avg Latency | Results/Call | Cost/Result |
|-----------|-----------|-------------|--------------|-------------|
| serper | $0.010 | 1,200ms | 10 | $0.001 |
| google_places | $0.017 | 600ms | 1-3 | $0.009 |
| openstreetmap | $0.000 | 2,000ms | 5-20 | $0.000 |
| sport_scotland | $0.000 | 1,500ms | 3-10 | $0.000 |
| edinburgh_council | $0.000 | 1,800ms | 2-8 | $0.000 |
| open_charge_map | $0.000 | 1,200ms | 1-5 | $0.000 |

**Insight:** Free sources take longer but provide good value. Paid sources (Google) offer best reliability but highest cost.

### Appendix C: Example Persistence Report

```
================================================================================
INTELLIGENT INGESTION ORCHESTRATION REPORT
================================================================================

Query: powerleague portobello

Summary:
  Candidates Found:    15
  Accepted Entities:   8
  Duplicates Removed:  7
  Persisted to DB:     8
  Extracted Entities:  8
  Merged Entities:     3

Connector Metrics:
--------------------------------------------------------------------------------
Connector            Status          Time (ms)    Candidates   Cost (USD)
--------------------------------------------------------------------------------
serper               ✓ SUCCESS       1472         10           0.0100
google_places        ✓ SUCCESS       617          3            0.0170
sport_scotland       ✓ SUCCESS       1834         2            0.0000
openstreetmap        ✗ TIMEOUT       3000         0            0.0000

Pipeline Stages:
--------------------------------------------------------------------------------
Persistence:         ✓ 8 RawIngestion + 8 ExtractedEntity created
Extraction:          ✓ 8 entities enriched (0 LLM calls, 8 structured)
Merging:             ✓ 3 Entity records created/updated

Final Entities:
  1. Powerleague Portobello (ChIJ...)
     Sources: serper, google_places, sport_scotland
     Completeness: 95% (19/20 fields)

  2. Powerleague Edinburgh - Meggetland (ChIJ...)
     Sources: serper, google_places
     Completeness: 85% (17/20 fields)

  3. Portobello Community Centre (osm:...)
     Sources: serper, openstreetmap
     Completeness: 60% (12/20 fields)

================================================================================
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-27 | Claude Sonnet 4.5 | Initial draft based on comprehensive review |

---

**Next Steps:**
1. Review and approve specification
2. Create detailed implementation plan (ORCHESTRATION_PERSISTENCE_PLAN.md)
3. Implement fixes in priority order
4. Write comprehensive tests (TDD workflow)
5. Update documentation
