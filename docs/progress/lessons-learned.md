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

