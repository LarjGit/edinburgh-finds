# Development Catalog

---

## R-02: Connector Tier System

Scoped items for roadmap `R-02` ("Implement Data Connector Tier System"),
executed under methodology constraints (C1-C9, G1-G6).

### **R-02.1: Overture Tier 1 Local File Ingestion (Slice 1)**
- **Type:** Infrastructure
- **Goal:** Add a zero-cost Overture onboarding slice that ingests local
  Overture baseline files into `RawIngestion` through the orchestration adapter
  path.
- **Boundaries:**
  - Implement local-file Overture connector with FeatureCollection validation and
    adapter-aligned output envelope (`{"results": [...]}`).
  - Validate adapter->persistence seam writes `RawIngestion` even when extraction
    fails for unknown source.
  - Validate deterministic `hash` and required `metadata_json` fields.
- **Exclusions:**
  - No planner routing changes.
  - No extraction/canonical/module logic changes.
  - No live Overture API integration.
  - No schema changes.
- **Files (Actual):**
  - `engine/ingestion/connectors/overture_local.py`
  - `tests/fixtures/overture/overture_feature_collection.json`
  - `tests/engine/ingestion/connectors/test_overture_local_connector.py`
  - `tests/engine/orchestration/test_overture_adapter_persistence.py`
- **Status:** Complete
- **Completed:** 2026-02-14
- **Commit:** `bf9698c`
- **Executable Proof:**
  - `pytest tests/engine/ingestion/connectors/test_overture_local_connector.py -v` ✅ PASSED
  - `pytest tests/engine/orchestration/test_overture_adapter_persistence.py::test_overture_adapter_path_persists_raw_ingestion_even_when_extraction_fails -v` ✅ PASSED

### R-02.2: Overture Phase-1 Extraction Contract Compliance
- **Type:** Infrastructure
- **Goal:** Ensure Overture extraction emits only schema primitives and raw observations (no `canonical_*`, no `modules`) from fixture-driven input.
- **Boundaries:** Implement/adjust Overture extractor output mapping to schema primitives + raw evidence surfaces; enforce Phase-1 contract at extraction boundary.
- **Exclusions:** No lens mapping changes, no module population logic, no planner/routing changes, no merge/finalization changes.
- **Files (Actual):**
  - `engine/extraction/extractors/overture_local_extractor.py`
  - `engine/extraction/run.py`
  - `tests/engine/extraction/extractors/test_overture_local_extractor.py`
- **Proof Approach:** Fixture-based integration test asserting extraction output includes required primitives and excludes all `canonical_*`/`modules`.
- **Estimated Scope:** 2 files, ~90 lines
- **Prerequisite:** `R-02.2a` complete (real input contract established).
- **Status:** Complete
- **Completed:** 2026-02-15
- **Commit:** `dfdcf68`
- **Executable Proof:**
  - `pytest tests/engine/extraction/extractors/test_overture_local_extractor.py -v` PASSED
  - `pytest tests/engine/orchestration/test_overture_adapter_persistence.py::test_overture_adapter_path_persists_raw_ingestion_even_when_extraction_fails -v` PASSED

### R-02.2a: Overture Official-Format Discovery + Contract Baseline (Prerequisite)
- **Type:** Infrastructure
- **Goal:** Establish the actual Overture Places payload contract from official internet sources before extractor implementation, so downstream work is grounded in real upstream format (not local assumptions).
- **Boundaries:**
  - Confirm Overture Places structure from official sources (docs + schema references) with dated citations.
  - Capture a versioned contract fixture representing the discovered real record shape (expected to be row-style Places records, not GeoJSON `FeatureCollection`).
  - Add contract tests that validate required/optional fields from official schema-aligned samples and explicitly reject unsupported local assumptions.
  - Document the accepted contract and source links used for subsequent Overture extraction work.
- **Exclusions:**
  - No extractor implementation changes.
  - No lens mapping or module logic changes.
  - No planner/routing/merge/finalization changes.
- **Files (Estimated):**
  - `tests/fixtures/overture/overture_places_contract_samples.json`
  - `tests/engine/ingestion/connectors/test_overture_input_contract.py`
  - `docs/progress/overture_input_contract.md`
- **Proof Approach:** Contract tests pass for official-schema-aligned samples and fail for invalid/unsupported shapes with explicit error messages; contract doc includes clickable source links and access date.
- **Estimated Scope:** 1 code-adjacent fixture + 1 test + 1 doc, ~100 lines
- **Status:** Complete
- **Completed:** 2026-02-15
- **Commit:** `b5d231b`
- **Executable Proof:**
  - `pytest tests/engine/ingestion/connectors/test_overture_input_contract.py -v` ✅ PASSED

### R-02.3: Overture Lens Mapping to Canonical + Module Trigger
- **Type:** Infrastructure
- **Goal:** Map Overture evidence to non-empty `canonical_*` targets and trigger at least one module path via lens rules.
- **Boundaries:** Lens-only rule updates for canonical mappings and at least one module trigger compatible with existing engine contracts.
- **Exclusions:** No engine code changes, no planner/routing changes, no merge/finalization changes, no schema changes.
- **Files (Actual):**
  - `engine/lenses/edinburgh_finds/lens.yaml`
  - `tests/engine/extraction/test_lens_integration_modules.py`
- **Proof Approach:** Fixture-based integration test at lens-application boundary asserting non-empty mapped `canonical_*` fields and at least one populated `modules.*` field.
- **Estimated Scope:** 1 file, ~80 lines
- **Status:** Complete
- **Completed:** 2026-02-15
- **Commit:** `0257381`
- **Executable Proof:**
  - `pytest tests/engine/extraction/test_lens_integration_modules.py::test_module_extraction_for_overture_entity -v` PASSED
  - `pytest tests/engine/extraction/test_lens_integration_modules.py::test_module_extraction_for_padel_entity -v` PASSED

### R-02.4: Overture Deterministic End-to-End Proof (Fixture-Based)
- **Type:** Infrastructure
- **Goal:** Prove Overture works end-to-end (orchestration -> lens application -> persistence) with deterministic fixture input.
- **Boundaries:** Add one deterministic E2E integration test using local fixtures and existing pipeline entrypoints; assert persisted entity shape.
- **Exclusions:** No live API calls, no new connector hardening items, no production logic changes beyond test scaffolding.
- **Files (Estimated):** `tests/engine/orchestration/test_overture_end_to_end_validation.py`
- **Proof Approach:** Fixture-based E2E test asserting non-empty `canonical_*` and at least one populated `modules.*` field in persisted output.
- **Estimated Scope:** 1 file, ~70 lines
- **Status:** [ ] Pending

### R-02.5: Overture Release Download Connector (Live Source)
- **Type:** Infrastructure
- **Goal:** Add a live Overture acquisition path that downloads the latest Overture Places release artifact over HTTP and caches it locally for ingestion.
- **Boundaries:** Implement release URL resolution, download, cache path, and deterministic file hash metadata.
- **Exclusions:** No extraction changes, no lens changes, no merge/finalization changes.
- **Files (Estimated):** `engine/ingestion/connectors/overture_release.py`, `tests/engine/ingestion/connectors/test_overture_release_connector.py`
- **Proof Approach:** Connector test validates successful download/caching contract and deterministic metadata fields.
- **Estimated Scope:** 2 files, ~90 lines
- **Prerequisite:** `R-02.4` complete (fixture E2E baseline in place).
- **Status:** [ ] Pending

### R-02.6: Overture Row-Record Ingestion to RawIngestion (Live Path)
- **Type:** Infrastructure
- **Goal:** Ingest live Overture row-style records from the downloaded release into `RawIngestion` through the orchestration adapter path.
- **Boundaries:** Adapter mapping for row records, one raw payload per persisted ingestion record, deterministic hash/metadata.
- **Exclusions:** No extraction/lens/module logic changes.
- **Files (Estimated):** `engine/orchestration/adapters.py`, `tests/engine/orchestration/test_overture_release_adapter_persistence.py`
- **Proof Approach:** Integration test proving adapter->`RawIngestion` persistence for live-format row records.
- **Estimated Scope:** 2 files, ~100 lines
- **Prerequisite:** `R-02.5` complete (live artifact acquisition available).
- **Status:** [ ] Pending

### R-02.7: Overture Live Connector Registration + Runnable Execution Slice
- **Type:** Infrastructure
- **Goal:** Make the live Overture connector runnable from orchestration so a single live execution can be triggered intentionally.
- **Boundaries:** Register connector spec and minimal execution wiring needed for one manual live run.
- **Exclusions:** No planner heuristics expansion, no UI, no schema changes.
- **Files (Estimated):** `engine/orchestration/connectors/registry.py`, `engine/orchestration/cli.py`
- **Proof Approach:** CLI proof command executes the live Overture connector and produces accepted candidates.
- **Estimated Scope:** 2 files, ~80 lines
- **Prerequisite:** `R-02.6` complete (live row ingestion seam validated).
- **Status:** [ ] Pending

### R-02.8: Overture Live End-to-End Single-Run Proof (DB Validation)
- **Type:** Infrastructure
- **Goal:** Prove one real live Overture run persists at least one entity with primitives plus non-empty canonical dimensions and at least one populated module field.
- **Boundaries:** Add a live E2E validation artifact (test/script) and explicit DB assertions.
- **Exclusions:** No new connector capabilities, no lens refactor beyond what `R-02.3` already covers.
- **Files (Estimated):** `tests/engine/orchestration/test_overture_live_end_to_end_validation.py`, `docs/progress/overture_live_e2e_proof.md`
- **Proof Approach:** Run command + DB assertions for required persisted fields (`entity_name`, coordinates/address if available, non-empty `canonical_*`, non-empty `modules.*` field).
- **Estimated Scope:** 2 files, ~100 lines
- **Prerequisite:** `R-02.3` and `R-02.7` complete (lens mapping and live run path both available).
- **Status:** [ ] Pending

### R-02.9: Overture Live Runbook + Safety Controls
- **Type:** Infrastructure
- **Goal:** Document and enforce the operational run steps for the live Overture E2E slice (inputs, limits, retry/failure behavior).
- **Boundaries:** Add operator runbook and guardrails for controlled single-run execution.
- **Exclusions:** No runtime behavior changes beyond guardrail flags already introduced.
- **Files (Estimated):** `COMMANDS.md`, `docs/progress/overture_live_e2e_proof.md`
- **Proof Approach:** Runbook commands are executable and reproduce the live single-run proof flow.
- **Estimated Scope:** 2 files, ~70 lines
- **Prerequisite:** `R-02.8` complete (live E2E proof implemented).
- **Status:** [ ] Pending
