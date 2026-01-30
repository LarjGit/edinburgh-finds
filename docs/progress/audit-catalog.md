# Architectural Audit Catalog

**Current Phase:** Foundation (Phase 1)
**Validation Entity:** Powerleague Portobello Edinburgh (when in Phase 2+)
**Last Updated:** 2026-01-30 (EP-001 completed)

---

## Phase 1: Foundation Violations

### Critical (Level 1) - Architectural Boundaries

- [x] **EP-001: Engine Purity - sport_scotland_extractor.py:131-153**
  - **Principle:** Engine Purity (system-vision.md Invariant 1) + Extraction Boundary (architecture.md 4.2)
  - **Location:** `engine/extraction/extractors/sport_scotland_extractor.py:131-153`
  - **Description:** Hardcoded domain term "tennis" in conditional logic. Lines 131-153 contain `if "tennis" in facility_type.lower():` with tennis-specific field extraction logic. Engine code must not contain domain-specific terms or logic.
  - **Completed:** 2026-01-30
  - **Commit:** d1aadc2
  - **Executable Proof:**
    - `pytest tests/engine/extraction/extractors/test_sport_scotland_extractor.py::TestEnginePurity::test_extractor_contains_no_domain_literals -v` ✅ PASSED
    - `pytest tests/engine/extraction/extractors/test_sport_scotland_extractor.py::TestExtractionBoundary::test_extractor_outputs_only_primitives_and_raw_observations -v` ✅ PASSED
    - All 55 extraction tests pass (no regressions)
  - **Fix Applied:** Removed domain-specific tennis logic (lines 131-153), replaced with raw observation capture. Extractor now outputs ONLY schema primitives + raw observations per architecture.md 4.2 Phase 1 contract.

- [ ] **CP-001: Context Propagation - All extractors missing ctx parameter**
  - **Principle:** Extractor Interface Contract (architecture.md 3.8)
  - **Location:** All 6 extractors in `engine/extraction/extractors/*.py`
  - **Description:** Extractors use signature `def extract(self, raw_data: Dict) -> Dict` but architecture.md 3.8 requires `def extract(self, raw_data: dict, *, ctx: ExecutionContext) -> dict`. ExecutionContext must be threaded through all extractors to provide lens contract access and maintain boundary purity.
  - **Evidence:** `grep "def extract(self, raw_data" engine/extraction/extractors/*.py`
  - **Estimated Scope:** 6 files, signature changes + BaseExtractor abstract method
  - **Fix Strategy:**
    1. Update BaseExtractor.extract() signature to require ctx parameter
    2. Update all 6 extractor implementations to accept and use ctx
    3. Update all callsites to pass ctx

- [ ] **LB-001: Lens Loading Boundary - planner.py:233-246**
  - **Principle:** Lens Loading Lifecycle (architecture.md 3.2, 3.7)
  - **Location:** `engine/orchestration/planner.py:233-246`
  - **Description:** Lens is loaded from disk during orchestration execution (`lens_path = Path(...) / "lenses" / lens_id / "lens.yaml"` then `VerticalLens(lens_path)`). Architecture requires lens loading to occur only during bootstrap, then be injected via ExecutionContext. "Direct imports of lens loaders or registries outside bootstrap are forbidden."
  - **Evidence:** Read planner.py lines 233-246
  - **Estimated Scope:** 1 file (planner.py), refactor bootstrap/orchestration boundary
  - **Fix Strategy:**
    1. Create proper bootstrap entry point (CLI or orchestrator bootstrap)
    2. Load and validate lens once at bootstrap
    3. Create ExecutionContext with validated lens contract
    4. Pass context to planner instead of loading lens inside planner

### Important (Level 2) - Missing Contracts

- [ ] **EC-001: ExecutionContext Structure Mismatch**
  - **Principle:** ExecutionContext Contract (architecture.md 3.6)
  - **Location:** `engine/orchestration/execution_context.py:25-76`
  - **Description:** Current ExecutionContext doesn't match architecture.md 3.6 specification. Architecture requires frozen dataclass with `lens_id: str`, `lens_contract: dict`, `lens_hash: Optional[str]`. Current implementation is mutable class with different structure. Missing lens_id and lens_hash fields for reproducibility.
  - **Evidence:** Compare execution_context.py:25-76 with architecture.md 3.6
  - **Estimated Scope:** 1 file, class restructure
  - **Fix Strategy:**
    1. Change ExecutionContext to frozen dataclass per architecture spec
    2. Add lens_id and lens_hash fields
    3. Remove mutable collections (candidates, accepted_entities, etc.) - these belong in orchestrator state, not context
    4. Context should only carry lens contract and metadata, not execution state

- [ ] **MC-001: Missing Lens Validation Gates**
  - **Principle:** Lens Validation Gates (architecture.md 6.7)
  - **Location:** `engine/lenses/loader.py` and bootstrap entry points
  - **Description:** Architecture.md 6.7 requires 7 validation gates at lens load time: (1) Schema validation, (2) Canonical reference integrity, (3) Connector reference validation, (4) Identifier uniqueness, (5) Regex compilation validation, (6) Smoke coverage validation, (7) Fail-fast enforcement. Need to verify all gates are implemented and enforced.
  - **Evidence:** Review lenses/loader.py and lenses/validator.py for gate coverage
  - **Estimated Scope:** 2 files, add missing validation gates
  - **Fix Strategy:** Audit existing validation in lenses/validator.py, add missing gates, ensure fail-fast behavior

---

## Phase 2: Pipeline Implementation

(Populated when Phase 1 complete - After all Level-1 violations resolved and bootstrap gates enforced)

Placeholder items based on architecture.md 4.1 (11 pipeline stages):
- Lens Resolution validation (Stage 2)
- Planning stage completeness (Stage 3)
- Source Extraction boundary enforcement (Stage 6)
- Lens Application wiring (Stage 7)
- Classification correctness (Stage 8)
- Cross-Source Deduplication (Stage 9)
- Deterministic Merge implementation (Stage 10)
- Finalization validation (Stage 11)

---

## Notes

### Audit Methodology
This catalog was created by systematically auditing system-vision.md Invariants 1-10 and architecture.md contracts against the codebase:
- Searched engine code for domain terms using: `grep -ri "padel|tennis|wine|restaurant" engine/`
- Read all extractor implementations to check extraction boundary compliance
- Verified ExecutionContext propagation through pipeline
- Checked lens loading locations for bootstrap boundary violations
- Compared ExecutionContext implementation against architecture.md 3.6 specification

### Progress Rules
- Items worked in order (top to bottom within each level)
- Discovered violations added to appropriate section immediately
- Completed items marked `[x]` with completion date + commit hash + executable proof
- **Catalog is the ONLY source of truth for progress**

### Phase Transition Criteria
- **Phase 1 → Phase 2:** All Level-1 violations resolved + bootstrap validation gates enforced + architectural boundary tests pass
- **Phase 2 → Phase 3:** Complete 11-stage pipeline operational + validation entity flows end-to-end with correct data in database

### Executable Proof Required (per system-vision.md 6.3)
Every completed item MUST document executable proof:
- Code-level changes: Test name that passed
- Pipeline-level changes: Integration test that passed
- End-to-end validation: Database query showing correct entity data
- No item marked complete without concrete proof

---

**Next Action:** Select CP-001 (next Level-1 item) and begin micro-iteration process per development-methodology.md Section 5.
