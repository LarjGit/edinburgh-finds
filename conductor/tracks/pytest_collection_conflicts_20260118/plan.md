# Plan: Pytest Collection Conflicts

## Phase 1: Discovery
- [x] **Reproduce & Catalog**: Run `pytest` and capture all collection errors with file pairs that conflict.
- [x] **Inventory Test Files**: List all `test_*.py` files and classify as real tests vs scripts/examples.
- [x] **Check Pytest Config**: Review existing pytest config (`pyproject.toml`, `pytest.ini`, `conftest.py`) to understand current collection rules.

**Findings:**
- 15 collection errors identified
- 5 import file mismatches: `scripts/test_*_connector.py` vs `tests/test_*_connector.py`
- 2 logging test conflicts: `extraction/tests/test_logging.py` vs `tests/test_logging.py`
- 10 ImportErrors in extraction/tests (resolved by running from root)
- No pytest configuration exists

## Phase 2: Solution Design
- [x] **Choose Strategy**: Decide on the safest approach:
  - Rename scripts to avoid pytest collection, OR
  - Move scripts outside test discovery paths, OR
  - Add pytest collection filters (e.g., `norecursedirs`, `python_files`) that explicitly exclude script directories.
- [x] **Assess Impact**: Ensure legitimate tests remain collected; avoid unintentionally skipping real tests.

**Decision:**
- Rename manual scripts from `test_*.py` to `run_*.py` (5 files)
- Rename logging tests to be more specific: `test_extraction_logging.py` and `test_ingestion_logging.py` (2 files)
- Minimal disruption, no pytest config needed

## Phase 3: Implementation
- [x] **Apply Fix**: Implement the chosen strategy (renames, moves, or config updates).
- [x] **Update Docs**: Document the decision and how to run scripts/tests if paths changed.

**Changes:**
- Renamed 5 scripts in `engine/scripts/` from `test_*.py` to `run_*.py`
- Renamed 2 logging test files to be more specific
- Updated script docstrings with new module paths
- Updated `engine/scripts/README.md` with new script names
- Updated `engine/ingestion/README.md` with new script names

## Phase 4: Verification
- [x] **Run Pytest**: Confirm collection passes and suite executes.
- [x] **Spot-Check**: Verify expected key test groups still run (e.g., `engine/tests`, `engine/extraction/tests`).

**Results:**
- Pytest collection: 1032 tests collected, 0 errors (was 834 tests, 15 errors)
- All key test groups verified:
  - `engine/tests/test_serper_connector.py`: 18 tests
  - `engine/extraction/tests/`: 117 tests
  - `engine/extraction/tests/test_extraction_logging.py`: 16 tests
  - `engine/tests/test_ingestion_logging.py`: 22 tests
