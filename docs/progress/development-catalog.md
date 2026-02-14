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
