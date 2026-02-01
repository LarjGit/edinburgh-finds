# EX-003-RELOCATE: Relocate extract_with_lens_contract to Test Utilities

**Catalog Item:** EX-003-RELOCATE
**Principle:** Code Organization, Separation of Concerns
**Priority:** Low (cosmetic improvement, no functional impact)
**Created:** 2026-02-01
**Status:** ✅ COMPLETE (2026-02-01) - All 5 iterations successful

---

## Overview

The `extract_with_lens_contract()` function is a legacy convenience wrapper that combines Phase 1 + Phase 2 extraction. It's useful for testing and scripts but currently lives in `engine/extraction/base.py` which suggests it's core infrastructure. This plan relocates it to test utilities with a clearer name to signal test-only usage.

---

## Code Reality Audit (2026-02-01)

### Current Location
- **File:** `engine/extraction/base.py`
- **Lines:** 207-437 (231 lines)
- **Function signature:** `def extract_with_lens_contract(raw_data: Dict[str, Any], lens_contract: Dict[str, Any]) -> Dict[str, Any]:`

### Current Usage (4 files total)

**Test Files (1 file):**
1. `tests/engine/lenses/test_lens_integration_validation.py`
   - Line 10: Import statement
   - Lines 36, 69, 95, 127: Function calls (4 uses in 4 test functions)

**Script Files (3 files):**
1. `scripts/run_lens_aware_extraction.py`
   - Line 32: Import statement
   - Usage: TBD (need to verify actual call sites)

2. `scripts/test_wine_extraction.py`
   - Line 22: Import statement
   - Usage: TBD (need to verify actual call sites)

3. `scripts/validate_wine_lens.py`
   - Import statement present (1 occurrence found via grep)
   - Usage: TBD (need to verify actual call sites)

### Dependencies (imports needed in new location)
```python
from typing import Dict, Any, List
from engine.lenses.mapping_engine import execute_mapping_rules
from engine.extraction.entity_classifier import resolve_entity_class
from engine.extraction.stabilization import stabilize_canonical_dimensions
from engine.extraction.module_extraction import extract_module_fields
```

---

## Execution Plan: 5 Micro-Iterations

### Micro-Iteration 1: Create Test Helper File ✅ READY TO EXECUTE

**Catalog Item:** EX-003-RELOCATE-1
**Files Touched:** 1 new file
- `tests/engine/extraction/test_helpers.py` (NEW)

**Current State:**
- File does not exist
- Function lives in `engine/extraction/base.py` lines 207-437

**Change:**
1. Create `tests/engine/extraction/test_helpers.py`
2. Add module docstring explaining this is for test-only convenience functions
3. Copy `extract_with_lens_contract()` function (231 lines)
4. Rename to `extract_with_lens_for_testing()`
5. Update docstring to reflect new location and test-only nature
6. Add all required imports (see Dependencies section above)

**Pass Criteria:**
- ✅ File exists at `tests/engine/extraction/test_helpers.py`
- ✅ Function named `extract_with_lens_for_testing()` exists
- ✅ Docstring clearly states "Test-only convenience function"
- ✅ All imports resolve correctly
- ✅ Can import successfully: `from tests.engine.extraction.test_helpers import extract_with_lens_for_testing`
- ✅ Function signature matches original: `def extract_with_lens_for_testing(raw_data: Dict[str, Any], lens_contract: Dict[str, Any]) -> Dict[str, Any]:`

**Estimated Scope:** ~270 lines (module docstring + imports + function)

**Test Command:**
```bash
python -c "from tests.engine.extraction.test_helpers import extract_with_lens_for_testing; print('Import successful')"
```

---

### Micro-Iteration 2: Update Test File Import ⏸️ BLOCKED (needs Iteration 1)

**Catalog Item:** EX-003-RELOCATE-2
**Files Touched:** 1 file
- `tests/engine/lenses/test_lens_integration_validation.py`

**Current State:**
```python
# Line 10
from engine.extraction.base import extract_with_lens_contract

# Lines 36, 69, 95, 127 - 4 function calls
result = extract_with_lens_contract(raw_data, lens_contract)
```

**Change:**
1. Line 10: Change import to:
   ```python
   from tests.engine.extraction.test_helpers import extract_with_lens_for_testing
   ```
2. Lines 36, 69, 95, 127: Replace all 4 calls:
   ```python
   # OLD
   result = extract_with_lens_contract(raw_data, lens_contract)
   # NEW
   result = extract_with_lens_for_testing(raw_data, lens_contract)
   ```

**Pass Criteria:**
- ✅ Import statement updated (line 10)
- ✅ All 4 function calls renamed
- ✅ All tests pass: `pytest tests/engine/lenses/test_lens_integration_validation.py -v`
- ✅ No references to old function name remain: `grep -c "extract_with_lens_contract" tests/engine/lenses/test_lens_integration_validation.py` returns 0

**Estimated Scope:** 5 lines changed (1 import + 4 calls)

**Test Command:**
```bash
pytest tests/engine/lenses/test_lens_integration_validation.py -v
```

---

### Micro-Iteration 3: Update Script Imports ⏸️ BLOCKED (needs Iteration 2)

**Catalog Item:** EX-003-RELOCATE-3
**Files Touched:** 3 files
- `scripts/run_lens_aware_extraction.py`
- `scripts/test_wine_extraction.py`
- `scripts/validate_wine_lens.py`

**Current State (all 3 files):**
```python
from engine.extraction.base import extract_with_lens_contract
# ... usage somewhere in file
```

**Change (same for all 3 files):**
1. Update import statement:
   ```python
   from tests.engine.extraction.test_helpers import extract_with_lens_for_testing
   ```
2. Find and replace all function calls in each file:
   ```python
   # OLD
   extract_with_lens_contract(...)
   # NEW
   extract_with_lens_for_testing(...)
   ```

**Pass Criteria:**
- ✅ All 3 import statements updated
- ✅ All function calls renamed in all 3 files
- ✅ No references to old function name:
   ```bash
   grep -r "extract_with_lens_contract" scripts/
   # Should return nothing
   ```
- ✅ Scripts can be imported without errors:
   ```bash
   python -c "import sys; sys.path.insert(0, 'scripts'); import run_lens_aware_extraction"
   python -c "import sys; sys.path.insert(0, 'scripts'); import test_wine_extraction"
   python -c "import sys; sys.path.insert(0, 'scripts'); import validate_wine_lens"
   ```

**Estimated Scope:** ~6-9 lines changed (3 imports + 3-6 function calls)

**Note:** Need to verify exact number of function calls per script before execution

---

### Micro-Iteration 4: Delete from base.py ⏸️ BLOCKED (needs Iteration 3)

**Catalog Item:** EX-003-RELOCATE-4
**Files Touched:** 1 file
- `engine/extraction/base.py`

**Current State:**
- Function exists at lines 207-437 (231 lines)
- No production code should be using it (only tests/scripts which are now updated)

**Change:**
1. Delete lines 207-437 (entire function)
2. Verify no orphaned imports (imports only used by deleted function)

**Pass Criteria:**
- ✅ Function deleted from base.py
- ✅ File still valid Python (no syntax errors)
- ✅ No references to function in engine code:
   ```bash
   grep -r "extract_with_lens_contract" engine/
   # Should return nothing
   ```
- ✅ All extraction tests still pass:
   ```bash
   pytest tests/engine/extraction/ -v
   ```

**Estimated Scope:** 231 lines deleted

**Test Command:**
```bash
pytest tests/engine/extraction/ -v
python -c "from engine.extraction import base; print('base.py still valid')"
```

---

### Micro-Iteration 5: Final Verification ⏸️ BLOCKED (needs Iteration 4)

**Catalog Item:** EX-003-RELOCATE-5
**Files Touched:** None (verification only)

**Current State:**
- Function relocated to test utilities
- All imports updated
- Original function deleted

**Verification Steps:**
1. Run full test suite:
   ```bash
   pytest tests/engine/ -v
   ```

2. Verify no references to old location:
   ```bash
   grep -r "from engine.extraction.base import extract_with_lens_contract" .
   # Should return nothing
   ```

3. Verify new location works:
   ```bash
   grep -r "from tests.engine.extraction.test_helpers import extract_with_lens_for_testing" .
   # Should show 4 files (1 test + 3 scripts)
   ```

4. Manual smoke test of one script:
   ```bash
   python scripts/validate_wine_lens.py
   # Should run without import errors
   ```

**Pass Criteria:**
- ✅ All tests pass (no regressions)
- ✅ No references to old import path
- ✅ All 4 files using new import path
- ✅ Scripts can execute without errors

**Success Metrics:**
- ✅ Function clearly marked as test-only (lives in `tests/` directory)
- ✅ Better name signals intended usage (`extract_with_lens_for_testing`)
- ✅ Core extraction code cleaner (no test-only functions)
- ✅ Still available for legitimate testing/scripting use cases

---

## Commit Strategy

After each micro-iteration:
```bash
git add <changed files>
git commit -m "<type>(extraction): <description> (EX-003-RELOCATE-<N>)

<detailed description of what changed>

Part <N> of 5 for relocating extract_with_lens_contract to test utilities.

Validates: Code organization best practices
Catalog Item: EX-003-RELOCATE-<N>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

Example for Iteration 1:
```bash
git commit -m "refactor(extraction): create test_helpers with extract_with_lens_for_testing (EX-003-RELOCATE-1)

Created tests/engine/extraction/test_helpers.py with renamed convenience function
for lens-aware extraction. This function is test-only and now lives in test utilities
rather than production code.

Part 1 of 5 for relocating extract_with_lens_contract to test utilities.

Validates: Code organization best practices
Catalog Item: EX-003-RELOCATE-1

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Recovery Protocol

### If Iteration 1 fails:
- Delete `tests/engine/extraction/test_helpers.py`
- No other changes needed (nothing else touched)

### If Iteration 2-3 fails:
- Revert import changes: `git checkout -- <file>`
- Function still exists in both locations (safe)
- Can retry with corrected approach

### If Iteration 4 fails:
- Revert deletion: `git checkout -- engine/extraction/base.py`
- Tests/scripts already updated to use new location
- Can complete Iteration 4 when blocker resolved

### If Iteration 5 verification fails:
- All previous iterations complete
- Function still available in new location
- Can restore old location temporarily if critical blocker found

---

## Progress Tracking

- [x] Iteration 1: Create test_helpers.py - ✅ COMPLETE (2026-02-01, commit cf010e4)
- [x] Iteration 2: Update test file - ✅ COMPLETE (2026-02-01, commit 25abdf6)
- [x] Iteration 3: Update scripts - ✅ COMPLETE (2026-02-01, commit 99edfe3)
- [x] Iteration 4: Delete from base.py - ✅ COMPLETE (2026-02-01, commit 8896c35)
- [x] Iteration 5: Final verification - ✅ COMPLETE (2026-02-01)

**Status:** ALL ITERATIONS COMPLETE ✅

---

## Notes

- This is a low-priority cosmetic improvement
- Can be paused/resumed at any iteration boundary
- Each iteration is independently valuable (better test organization)
- No production code affected (test/script-only changes)
- Safe to execute in small time windows

**Estimated Total Time:** 1 hour spread across 5 micro-iterations
