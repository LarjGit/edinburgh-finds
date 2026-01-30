# Engineering Task: Wire Lens Contract into Orchestration Pipeline

**Status:** BLOCKED - Required for end-to-end validation
**Priority:** HIGH
**Estimate:** 1-2 hours
**Created:** 2026-01-30

## Context

The lens mapping and module extraction engines are **implemented and tested** (94% and 88% coverage respectively), but the orchestration pipeline is NOT wired up to use them.

**Current State:**
- `engine/orchestration/extraction_integration.py` uses old extraction path
- Calls `extractor.extract()` (Phase 1 primitives only)
- Does NOT call `extract_with_lens_contract()` (full pipeline)
- Result: Orchestration CLI does NOT populate canonical dimensions or modules

**Required State:**
- Orchestration must load lens contract at bootstrap
- Pass lens contract to extraction integration
- Call `extract_with_lens_contract()` instead of `extractor.extract()`
- Populate canonical dimensions and modules in database

## Implementation Plan

### Step 1: Lens Contract Loading in Orchestration

**File:** `engine/orchestration/planner.py`

Add lens loading at orchestration bootstrap:

```python
from engine.lenses.query_lens import load_lens

async def orchestrate(request: IngestRequest) -> Dict[str, Any]:
    # Load lens contract
    lens_name = request.lens or "edinburgh_finds"  # Default to Edinburgh Finds
    lens = load_lens(lens_name)
    lens_contract = lens.to_contract()  # Convert to plain dict

    # Pass lens_contract through OrchestrationContext
    # ... rest of orchestration
```

### Step 2: Update OrchestrationContext

**File:** `engine/orchestration/types.py`

Add lens_contract to context:

```python
@dataclass
class OrchestrationContext:
    """Runtime context for orchestration execution."""
    query: str
    mode: IngestionMode
    lens_contract: Dict[str, Any]  # ADD THIS
    # ... other fields
```

### Step 3: Update Extraction Integration

**File:** `engine/orchestration/extraction_integration.py`

Modify `extract_entity()` to use full pipeline:

```python
from engine.extraction.base import extract_with_lens_contract

async def extract_entity(
    raw_ingestion_id: str,
    db: Prisma,
    lens_contract: Dict[str, Any]  # ADD THIS PARAMETER
) -> Dict[str, Any]:
    # ... load raw data from file (unchanged)

    # REPLACE extractor-based extraction with lens contract extraction
    # OLD:
    # extracted = extractor.extract(raw_data)
    # validated = extractor.validate(extracted)
    # attributes, discovered = extractor.split_attributes(validated)

    # NEW:
    result = extract_with_lens_contract(raw_data, lens_contract)

    # Return result with schema structure
    return {
        "entity_class": result["entity_class"],
        "attributes": {
            "entity_name": raw_data.get("entity_name"),
            # ... map universal fields
            "canonical_activities": result["canonical_activities"],
            "canonical_place_types": result["canonical_place_types"],
            "canonical_roles": result["canonical_roles"],
            "canonical_access": result["canonical_access"],
            "modules": result["modules"]
        },
        "discovered_attributes": {}
    }
```

### Step 4: Update EntityFinalizer

**File:** `engine/orchestration/entity_finalizer.py`

Ensure finalizer preserves canonical dimensions and modules from extraction result.

Already reads from attributes, should work as-is, but verify.

### Step 5: Test End-to-End

```bash
# Run orchestration with persistence
python -m engine.orchestration.cli run "padel courts edinburgh" --persist

# Query database
python scripts/query_padel_entities.py

# Verify canonical_activities contains "padel"
```

## Acceptance Criteria

- [ ] Orchestration CLI loads lens contract at bootstrap
- [ ] `extract_entity()` calls `extract_with_lens_contract()`
- [ ] Orchestration run populates `canonical_activities` in database
- [ ] Orchestration run populates `canonical_place_types` in database
- [ ] Orchestration run populates `canonical_roles` in database
- [ ] Orchestration run populates `modules` field in database
- [ ] All existing orchestration tests still pass
- [ ] End-to-end validation (Phase 2) can complete

## References

- Lens mapping implementation: `engine/lenses/mapping_engine.py`
- Full pipeline function: `engine/extraction/base.py::extract_with_lens_contract()`
- Architecture spec: `docs/architecture.md` Section 4.2 (Extraction Boundary)
- System vision: `docs/system-vision.md` Section 6.3 (One Perfect Entity)

## Notes

This is a WIRING task, not an implementation task. The components exist and work correctly in isolation. We just need to connect them in the orchestration flow.
