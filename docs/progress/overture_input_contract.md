# Overture Places Input Contract Baseline (`R-02.2a`)

Accessed: 2026-02-15

## Accepted Contract (for `R-02.2`+ extraction work)

- Baseline payload shape is **row-style place records** (one place per record).
- Records are expected to align to Overture Places schema fields, not wrapped in
  GeoJSON `FeatureCollection`.
- Required fields for this repo baseline:
  - `id`
  - `version`
  - `sources` (non-empty list)
  - `names.primary`
  - `categories.primary`
  - `geometry`
- Optional fields validated by sample coverage:
  - `bbox`
  - `theme`
  - `type`

## Rejected Local Assumption

- Unsupported shape: top-level GeoJSON `FeatureCollection` with `features`.
- Reason: this baseline is intentionally aligned to official Overture Places
  release/schema references for row-style data ingestion.

## Fixture and Test

- Fixture: `tests/fixtures/overture/overture_places_contract_samples.json`
- Contract test: `tests/engine/ingestion/connectors/test_overture_input_contract.py`

## Official Sources

- Getting data (release artifacts, theme/type download pattern):  
  https://docs.overturemaps.org/getting-data/
- Places schema overview:  
  https://docs.overturemaps.org/schema/reference/places/
- Place schema reference:  
  https://docs.overturemaps.org/schema/reference/places/place/
- Official release index:  
  https://github.com/OvertureMaps/data/releases
