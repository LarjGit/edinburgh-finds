# Lessons Learned (Compounding Log)

This file captures institutional learning from Step 8 of the Development Methodology (reality-based incremental alignment).

**Usage Rules:**
- **WRITTEN** after each micro-iteration (Step 8: Compounding)
- **READ** before creating any new micro-plan (Step 3)
- Entries are **APPEND-ONLY** — never modify or delete previous entries
- Purpose: surface pitfalls, patterns, and documentation gaps to prevent repeated mistakes

Agents must consult this file during Step 2 (Code Reality Audit) to incorporate lessons into planning.

---

## 2026-02-10 — LA-013 — raw_categories Schema Classification Fix

**Context**
- Fixed `raw_categories` field misclassified as `exclude: true` when it should be `exclude: false` (Phase 1 primitive from source APIs, not computed/generated)

**Pattern Candidate**
- Yes
- Schema field classification determines data flow through split_attributes(). Phase 1 primitives (extracted from APIs) need `exclude: false` to be included in EntityExtraction schema. Phase 2/generated fields (canonical dimensions, computed values) use `exclude: true`.
- Reference: `engine/config/schemas/entity.yaml`, `engine/extraction/helpers/attribute_splitter.py:28-31`, commit 8c44c3f

**Documentation Clarity**
- Yes
- The `exclude` flag comment in entity.yaml is ambiguous ("Populated by extraction engine" could mean extracted OR generated). Propose adding header clarification: `exclude: false = Phase 1 primitive (extracted from sources), exclude: true = Phase 2/generated (computed by engine/lens)`.

**Pitfall**
- Yes
- When adding new schema fields, developers may incorrectly assume `exclude: true` for "engine-populated" fields, when the flag actually means "NOT a Phase 1 primitive extraction output."

**Suggested Guardrail (optional)**
- Add validation test that verifies EntityExtraction schema includes all fields that extractors output (Phase 1 primitives). This would catch misclassification bugs during schema changes.

---

## 2026-02-10 — LA-017 — Add Universal Amenity Fields to EntityExtraction Model

**Context**
- Added 4 universal amenity fields (locality, wifi, parking_available, disabled_access) to entity.yaml `fields:` section with `exclude: false`. Initial micro-plan incorrectly proposed adding them to `extraction_fields:` section before user intervention corrected placement per architectural guardrails established in LA-015.

**Pattern Candidate**
- Yes
- Universal persisted fields belong in `fields:` section with `exclude: false`, NOT in `extraction_fields:`. The `extraction_fields:` section is ONLY for volatile/extraction-only attributes (rating, currently_open, external_id). Universal fields that should persist as DB columns must go in `fields:` with `exclude: false` to be Phase 1 primitives included in EntityExtraction.
- Reference: `engine/config/schemas/entity.yaml` lines 292-327, commit af2ab86

**Documentation Clarity**
- Yes
- The entity.yaml header (lines 11-23) explains `exclude` flag semantics but doesn't clarify field placement rules. Propose adding explicit placement guide after exclude semantics: "Universal persisted fields → fields: section (with exclude: false). Extraction-only/volatile → extraction_fields: section. Examples: street_address, locality, wifi → fields:; rating, currently_open → extraction_fields:."

**Pitfall**
- Yes
- When adding "fields for extraction," it's easy to incorrectly assume they belong in `extraction_fields:` section. However, universal persisted fields (amenities, contact info, location details) must go in `fields:` with `exclude: false`, even though extractors populate them. Red flag: If field should be a database column, it belongs in `fields:`, NOT `extraction_fields:`.

**Suggested Guardrail (optional)**
- Add schema validation test that verifies no universal persisted fields exist in `extraction_fields:` section (negative validation). Current test suite includes this for LA-017 fields specifically (`test_amenity_fields_not_in_extraction_fields_section`), but a general guardrail could prevent future misplacements by validating extraction_fields contains ONLY expected volatile attributes.

---

## 2026-02-10 — LA-018a — Update OSM Extraction Prompt for Amenity Fields

**Context**
- Updated OSM LLM extraction prompt to capture 4 universal amenity fields (locality, wifi, parking_available, disabled_access) by adding explicit OSM tag mapping rules. Original LA-018 catalog item assumed "3 prompt files modified" but reality audit revealed only OSM uses LLM prompts - Google Places and Council use deterministic extraction requiring code changes, not prompt changes. Split LA-018 into LA-018a (OSM prompt), LA-018b (Google Places code), LA-018c (Council code) per Constraint C3 (max 2 files).

**Pattern Candidate**
- Yes
- Pattern: "Verify Extraction Strategy Before Planning Prompt Changes" - When planning updates to extractors, always verify the extraction strategy (LLM-based vs deterministic) before assuming prompt changes are needed. Not all extractors use LLM prompts - many use deterministic field mapping in extract() methods.
- Reference: LA-018 split rationale in audit-catalog.md, commit 3470da6 (OSM prompt update). Reality audit showed: osm_extractor.py uses LLM + prompt file (engine/extraction/prompts/osm_extraction.txt), but google_places_extractor.py and edinburgh_council_extractor.py use deterministic extract() methods with NO prompt files.

**Documentation Clarity**
- Yes
- Extractor docstrings don't explicitly state extraction strategy (LLM-based vs deterministic), making it unclear which extractors need prompt updates vs code changes. Propose adding "Extraction Strategy" metadata to each extractor's docstring header. Example: "Extraction Strategy: LLM-based (uses Instructor with prompt file: engine/extraction/prompts/osm_extraction.txt)" vs "Extraction Strategy: Deterministic (structured API response mapping, no prompt file)". This would make strategy immediately visible during code audits.

**Pitfall**
- Yes
- When creating catalog items for "update extractors to extract field X," don't assume prompt changes are universal. First audit: Which extractors use LLM? Which use deterministic extraction? Split catalog items by extraction strategy: LLM-based (prompt changes) vs deterministic (code changes). Concrete consequence: LA-018 violated Constraint C3 (max 2 files) until split into 3 sub-items, delaying work.

**Suggested Guardrail (optional)**
- Add "Extraction Strategy: [LLM-based|Deterministic]" field to extractor metadata in connector registry (engine/orchestration/connectors/registry.py) or extractor base class. This would make strategy queryable at runtime and prevent planning assumptions about prompt files existing. Alternative: Add extraction_strategy.md reference document listing all extractors with their strategies.

---

## 2026-02-11 — LA-018b — Update Google Places Extractor for Amenity/Accessibility Data

**Context**
- Updated Google Places deterministic extractor to extract 4 universal amenity fields (locality, wifi, parking_available, disabled_access) from Google Places API v1 response. Added extraction logic in google_places_extractor.py extract() method and updated field_mask in sources.yaml to request addressComponents and accessibilityOptions from API. Critical correction: parking_available maps wheelchairAccessibleParking=false → None (not False) to avoid false negatives where general parking exists but wheelchair parking is not accessible.

**Pattern Candidate**
- Yes
- Pattern: "API Field Masking for Deterministic Extractors" - When updating deterministic extractors to extract new fields, check if API requires explicit field masking (like Google Places API v1 X-Goog-FieldMask header). New fields must be added to field_mask configuration BEFORE extraction code will receive data. Two-file scope: (1) config/sources.yaml field_mask, (2) extractor extract() method.
- Reference: LA-018b added `places.addressComponents,places.accessibilityOptions` to google_places field_mask (sources.yaml:49), then implemented extraction logic (google_places_extractor.py:191-224), commit bc8b323. Without field_mask update, API would not return the data even with correct extraction code.

**Documentation Clarity**
- Yes
- Google Places API documentation doesn't prominently warn that wheelchair-accessible parking (wheelchairAccessibleParking) does NOT indicate general parking availability. Returning False when wheelchairAccessibleParking=false creates false negatives (implies parking doesn't exist when it may exist but isn't accessible). Propose adding inline comment in extractor explaining this semantic distinction: "wheelchairAccessibleParking=false means wheelchair parking NOT accessible, not that parking doesn't exist."

**Pitfall**
- Yes
- When mapping boolean accessibility fields to availability fields, don't assume accessible=false means unavailable=true. Example: wheelchairAccessibleParking=false could mean (1) no parking at all, or (2) parking exists but isn't wheelchair-accessible. Returning False creates false negatives. Safe pattern: Return True only when explicitly true, else None (inconclusive). Avoid treating false as definitive negative for availability fields.

**Suggested Guardrail (optional)**
- Add validation test that verifies extractors return None (not False) for inconclusive boolean fields. Example test case: Given wheelchairAccessibleParking=false, assert extracted['parking_available'] is None (not False). This prevents false negatives in availability fields derived from accessibility booleans.

---

## 2026-02-11 — LA-018c — Update Edinburgh Council Extractor for Amenity/Accessibility Data

**Context**
- Updated Edinburgh Council deterministic extractor to extract 4 universal amenity fields (locality, wifi, parking_available, disabled_access) from council GeoJSON response. Fixed schema mismatch bug: extractor emitted wheelchair_accessible (non-schema field) instead of disabled_access (schema field), causing field to leak into discovered_attributes. Evidence-based approach: inspected test fixtures, found only ACCESSIBLE field exists in Council data, mapped only that field. Set locality/wifi/parking_available to None rather than speculating on field names like NEIGHBOURHOOD/WIFI/PARKING.

**Pattern Candidate**
- Yes
- Pattern: "Evidence-Based Field Extraction (No Speculative Mappings)" - When adding universal field extraction to deterministic extractors, only map from field names that exist in test fixtures or observed API responses. Never introduce speculative property names without evidence. Benefit: Prevents maintenance burden of incorrect field mappings and ensures extractor code accurately reflects source API capabilities.
- Reference: LA-018c examined Council test fixtures (sample_council_response), found only ACCESSIBLE field, mapped only that field. Set locality/wifi/parking_available to None rather than guessing at NEIGHBOURHOOD/DISTRICT/WIFI/PARKING field names, commit b6669bb. This evidence-first approach was reinforced by user feedback during checkpoint 1.

**Documentation Clarity**
- Yes
- Section: target-architecture.md Section 4.2 (Extraction Boundary Phase 1) focuses on what extractors must NOT emit (canonical_*, modules, domain-specific fields) but could be clearer about what they MUST emit. Propose adding: "Phase 1 extractors must emit ALL universal schema primitives (entity_name, latitude, longitude, locality, wifi, parking_available, disabled_access, etc.), setting fields to None when source data does not provide them. This ensures consistent field presence across all extractors and prevents schema drift." Rationale: LA-018 series (a/b/c) required updating 3 extractors to add 4 universal fields. Clearer guidance on "must emit all primitives" would make this requirement explicit.

**Pitfall**
- Yes
- Schema field name mismatches cause fields to leak into discovered_attributes instead of being properly typed schema fields. When adding new universal fields to entity.yaml, verify ALL extractor output field names exactly match the schema field names. Example: Extractor outputs wheelchair_accessible but schema defines disabled_access → field goes to discovered_attributes (untyped bucket) instead of proper schema field. Detection method: Check split_attributes() output in tests - schema fields should appear in attributes dict, not discovered dict. LA-018c caught this bug where Edinburgh Council extractor emitted wheelchair_accessible (lines 169-171) but schema field is disabled_access (entity.yaml:319), causing data quality issues downstream.

**Suggested Guardrail (optional)**
- Add schema validation test that verifies extractor output field names exactly match schema field names for all universal primitives. Test would iterate through EntityExtraction model fields and verify each extractor's test fixtures use identical field names. This would catch schema mismatches during development before they leak fields into discovered_attributes in production.


---

## 2026-02-14 - R-02.1 - Local Overture Adapter->RawIngestion Slice

**Context**
- Added local-file Overture connector and validated adapter->RawIngestion persistence behavior with deterministic metadata proof.

**Pattern Candidate**
- Yes
- For local connector onboarding slices, validate the adapter contract first (`results` envelope + candidate mapping) before planner routing or live network integration.
- Reference: `engine/ingestion/connectors/overture_local.py`, `tests/engine/orchestration/test_overture_adapter_persistence.py`

**Documentation Clarity**
- No

**Pitfall**
- Yes
- Sandbox temp-path constraints can break `tmp_path` tests; prefer deterministic mocking of file reads when the test goal is payload-shape validation.

---

## 2026-02-15 - R-02.2a - Overture Official Input Contract Baseline

**Context**
- Established a fixture-backed Overture Places contract baseline from official docs/schema/release sources and added fail-fast tests that reject unsupported GeoJSON `FeatureCollection` assumptions.

**Pattern Candidate**
- Yes
- For upstream-source onboarding, define a contract fixture + boundary test + source-cited doc before implementing extractor behavior; this prevents extraction logic from being built on local shape assumptions.
- Reference: `tests/engine/ingestion/connectors/test_overture_input_contract.py`, `tests/fixtures/overture/overture_places_contract_samples.json`, `docs/progress/overture_input_contract.md`, commit `b5d231b`

**Documentation Clarity**
- Yes
- `docs/target-architecture.md` Section 4.2 (Extraction Boundary) could add a one-line note: "For new connectors, establish and cite an upstream payload contract baseline before Phase-1 extractor implementation."

**Pitfall**
- Yes
- Local synthetic fixtures can drift from official upstream format and silently force incorrect extractor contracts unless an explicit source-cited contract test is added first.

## 2026-02-15 - R-02.2 - Overture Phase-1 Extraction Contract Compliance

**Context**
- Added a deterministic Overture Phase-1 extractor and source dispatch wiring so `overture_local` emits schema primitives plus raw observations from row-style Overture records.

**Pattern Candidate**
- Yes
- Implement new connector extractors with an explicit boundary guard in `validate()` that rejects `canonical_*` and `modules` keys, then prove the contract with a fixture-based extraction test.
- Reference: `engine/extraction/extractors/overture_local_extractor.py`, `tests/engine/extraction/extractors/test_overture_local_extractor.py`, commit `dfdcf68`

**Documentation Clarity**
- Yes
- `docs/target-architecture.md` Section 4.2 could add one line under Phase 1: "New extractors should include explicit forbidden-field validation for canonical dimensions and modules at extractor validation time."

**Pitfall**
- Yes
- If tests assert `external_id` inside split `attributes`, they will fail because `external_id` is extraction-only and intentionally not part of persisted schema attributes.

---

## 2026-02-15 - R-02.3 - Overture Lens Mapping to Canonical + Module Trigger

**Context**
- Added lens-only mapping/trigger/rule updates so Overture `raw_categories=["sports_centre"]` produces non-empty `canonical_place_types` and at least one populated `modules.sports_facility.*` field.

**Pattern Candidate**
- Yes
- For new connector evidence tokens, first add a lens-integration RED test that uses connector-native raw evidence (not entity name), then add minimal lens rules to satisfy mapping + trigger + deterministic module population.
- Reference: `tests/engine/extraction/test_lens_integration_modules.py::test_module_extraction_for_overture_entity`, `engine/lenses/edinburgh_finds/lens.yaml`, commit `0257381`

**Documentation Clarity**
- Yes
- `docs/target-architecture.md` Section 7.2 (Module Triggers) could include one explicit example that triggers from `place_type` facet, not only `activity`, to make multi-facet module triggering expectations concrete.

**Pitfall**
- Yes
- If module triggers depend only on activity facet, place-type-only evidence from sources like Overture can map canonical values but still produce empty modules.
