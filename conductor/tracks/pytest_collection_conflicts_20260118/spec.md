# Track: Pytest Collection Conflicts
**Status**: Proposed
**Created**: 2026-01-18
**Owner**: Conductor
**Goal**: Identify and resolve pytest collection conflicts caused by duplicate test module names so the full test suite can run reliably.

## Problem
Running `pytest` fails during collection due to import file mismatches. The errors indicate duplicate module basenames across directories (e.g., `engine/scripts/test_*.py` and `engine/tests/test_*.py`, plus `engine/extraction/tests/test_logging.py` vs `engine/tests/test_logging.py`). Pytest imports the wrong module first and then refuses to collect the second file with the same import name.

## Why It Matters
Collection failures block the entire test suite, which makes verification unreliable and breaks CI/local workflows.

## Success Criteria
1. `pytest` completes test collection without import mismatch errors.
2. The full suite runs (or at least progresses past collection) without excluding legitimate tests unintentionally.
3. The fix is documented and reproducible (config changes, renames, or explicit exclusions).

## Constraints & Considerations
- Avoid half-measures that hide tests without intent (e.g., excluding real tests unintentionally).
- Prefer explicit, auditable solutions (rename modules or configure pytest collection rules).
- Preserve existing behavior of legitimate tests in `engine/tests` and `engine/extraction/tests`.

## Verification
- Run `pytest` from repo root.
- Confirm zero collection errors due to import mismatch.
- Document any exclusions or renamed files in appropriate docs or config.
