# Documentation Coverage Report

## 📊 Summary

- **Total Source Files:** 85
- **Covered Files:** 56
- **Coverage:** 65.9%
- **Workflows Discovered:** 5
- **Subsystem Docs:** 10
- **Reference Docs:** 5
- **How-to Guides:** 6
- **Operations Docs:** 2

## 🧩 Subsystem Coverage

| Subsystem | Files | Status |
| :--- | :--- | :--- |
| Orchestration | 6/13 | Partial (Core covered) |
| Schema | 9/15 | Partial (Core + Generators covered) |
| Extraction | 17/30 | Partial (Core, Services, Extractors covered) |
| Ingestion | 12/25 | Partial (Core, Connectors covered) |
| Lenses | 5/10 | Partial (Core covered) |
| Web | 7/15 | Partial (Core covered) |

## 🚀 Workflows

1. **Local Development Setup** (howto/local-development.md)
2. **Adding a New Lens** (howto/add-new-lens.md)
3. **Running a Discovery Cycle** (howto/discovery-cycle.md)
4. **Modifying the Entity Model** (howto/modify-entity-model.md)
5. **Managing the Quarantine** (howto/manage-quarantine.md)

## ⚠️ Gaps & Missing Documentation

### 1. Script Documentation
The following scripts in the root and `scripts/` directory are not fully documented in subsystem guides:
- `engine/check_data.py`
- `engine/inspect_db.py`
- `scripts/run_lens_aware_extraction.py`
- `scripts/test_wine_extraction.py`

### 2. Testing Guide
While CI is documented, a dedicated `howto/testing.md` for developers on how to write and run unit/integration tests locally is missing.

### 3. Module Deep-dives
Several utility modules in `engine/modules/` (not shown in manifest) lack dedicated documentation.

## ✅ Validation

- **Manifest Integrity:** OK
- **Output Existence:** OK (All 26 files exist)
- **Broken Links:** None detected (Internal cross-references verified)
- **Engine Purity:** Maintained in all documentation descriptions.
