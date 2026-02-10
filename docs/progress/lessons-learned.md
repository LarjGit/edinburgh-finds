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

