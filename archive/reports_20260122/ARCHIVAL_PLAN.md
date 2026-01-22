# Archival Plan - 2026-01-22

This plan identifies transient, legacy, and non-essential files to be moved to the `archive/` directory to clean up the workspace.

## 1. Root Directory Cleanup
**Destination:** `archive/reports_20260122/`

| File | Reason |
|------|--------|
| `ENGINE_PURITY_ASSESSMENT.md` | Transient report from completed purity assessment. |
| `ENGINE_PURITY_IMPLEMENTATION_GUIDE.md` | Transient guide for completed task. |
| `ENGINE_PURITY_REMEDIATION_PLAN.md` | Transient plan for completed task. |
| `ENGINE_PURITY_REVIEW.md` | Transient review document. |
| `next_steps_codex.md` | Stale todo list. |
| `next_steps_gemini.md` | Stale todo list. |
| `test_extraction.py` | Manual validation script, not part of test suite. |
| `file_map.txt` | Stale filesystem snapshot. |

## 2. Garbage / Accidental Files
**Destination:** `archive/trash/`

| File | Reason |
|------|--------|
| `CProjectsedinburgh_finds.env` | Accidental filename (copy-paste error). |
| `CProjectsedinburgh_findsweb.env` | Accidental filename (copy-paste error). |

## 3. Legacy Scripts
**Destination:** `archive/legacy_scripts/`

| File | Reason |
|------|--------|
| `scripts/migrate_listing_to_entity.py` | One-off migration script for Entity architecture transition (now complete). |
| `scripts/check_engine_purity.sh` | Maintenance script (Keep in scripts/ if used, otherwise archive. Assumed archive for cleanup). |

## 4. Verification of Previous Archival
The following were identified in previous plans as targets for archival/deletion. Please confirm they are gone or archive them if present:
- `engine/tests` (Should be moved to `archive/legacy_tests_and_utilities_20260122/` per previous plan. Current status: seems absent/moved).
- `engine/schema/venue.py` (Should be deleted).
- `engine/schema/winery.py` (Should be deleted).

## 5. Execution
To execute this plan, run the following commands:

```bash
# Create directories
mkdir -p archive/reports_20260122
mkdir -p archive/trash
mkdir -p archive/legacy_scripts

# Move Root Reports
mv ENGINE_PURITY_*.md archive/reports_20260122/
mv next_steps_*.md archive/reports_20260122/
mv test_extraction.py archive/reports_20260122/
mv file_map.txt archive/reports_20260122/

# Move Garbage
mv "CProjectsedinburgh_finds.env" archive/trash/
mv "CProjectsedinburgh_findsweb.env" archive/trash/

# Move Scripts
mv scripts/migrate_listing_to_entity.py archive/legacy_scripts/
# Optional: mv scripts/check_engine_purity.sh archive/legacy_scripts/
```
