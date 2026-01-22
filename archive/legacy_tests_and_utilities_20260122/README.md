# Archived Legacy Tests and Utilities
**Date:** 2026-01-22
**Reason:** Pre-purity remediation files with legacy architecture assumptions

## What's Here
- `engine_tests/` - All engine tests (entity_type, VENUE, Listing references)
- `extraction_tests/` - All extraction tests
- `validate_extraction.py` - Legacy validation script
- `check_entity_data.py` - Legacy data checker
- `check_raw_data.py` - Legacy raw data checker
- `id_strategy.md` - Legacy documentation
- `CONNECTOR_GUIDE.md` - Legacy documentation
- `SUMMARY_SYNTHESIS_EXTENSIBILITY.md` - Legacy documentation

## Why Archive?
These files encoded the OLD architecture:
- entity_type field (removed)
- VENUE enum (removed)
- Listing terminology (now Entity)
- entityType camelCase (removed)

Rather than translate 60+ files with high error risk, we archived them.
New tests will be written fresh against the NEW pure design as needed.

## Recovery
If you need to reference old test logic:
1. Look here for the pattern
2. Rewrite it against the new Entity/entity_class model
3. Don't copy-paste - rethink it fresh
