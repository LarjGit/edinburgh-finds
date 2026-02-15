# Overture Live End-to-End Single-Run Proof (R-02.8)

This artifact defines the live validation flow for one Overture run that reaches
Entity persistence with explicit database assertions.

## Preconditions

- `DATABASE_URL` points to a non-production validation database.
- `RUN_LIVE_OVERTURE_E2E=1` is set.
- Network access is available for Overture release fetch.
- Optional:
  - `OVERTURE_LIVE_TIMEOUT_SECONDS` (default `90`)
  - `OVERTURE_LIVE_MAX_ARTIFACT_BYTES` (default `1073741824`)

## Commands

```bash
python -m engine.orchestration.cli run --lens edinburgh_finds --connector overture_release "overture live slice"
pytest tests/engine/orchestration/test_overture_live_end_to_end_validation.py -v -s
```

## Required Assertions

The live test must prove at least one persisted `Entity` includes:

- Primitive data: non-empty `entity_name`
- Geographic anchor: coordinates or address fields
- Canonical enrichment: at least one non-empty `canonical_*` array
- Module enrichment: at least one populated `modules.*` field

## Evidence Log Template

- Run date:
- Environment:
  - DATABASE_URL target:
  - RUN_LIVE_OVERTURE_E2E:
  - OVERTURE_LIVE_TIMEOUT_SECONDS:
  - OVERTURE_LIVE_MAX_ARTIFACT_BYTES:
- CLI command result:
- Pytest result:
- Persisted entity sample:
  - entity_name:
  - canonical_activities:
  - canonical_place_types:
  - modules (keys):
