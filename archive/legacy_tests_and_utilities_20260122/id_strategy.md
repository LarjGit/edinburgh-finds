# ID Strategy Documentation

## Overview

This document defines the **standardized ID strategy** for all database models in Edinburgh Finds. Following a consistent ID strategy is critical for:
- Type safety in foreign key relationships
- Migration compatibility when moving to Supabase/PostgreSQL
- Debugging and troubleshooting (consistent ID formats)
- Distributed system compatibility

## Chosen Strategy: CUID

**All models in Edinburgh Finds use `@default(cuid())` for their ID fields.**

### Rationale

We chose **CUID (Collision-resistant Unique IDentifier)** over UUID for the following reasons:

1. **Prisma Default**: CUID is Prisma's recommended default strategy
2. **Better Sorting**: CUIDs are sortable by creation time (unlike UUIDs which are random)
3. **Collision Resistance**: Designed to be globally unique across distributed systems
4. **Shorter Length**: CUIDs are more compact than UUIDs (25 chars vs 36 chars)
5. **SQLite → PostgreSQL Migration**: CUIDs work seamlessly in both databases
6. **Framework Agnostic**: Compatible with Supabase, PostgreSQL, and SQLite

### Implementation

All models follow this pattern:

```prisma
model Example {
  id String @id @default(cuid())
  // ... other fields
}
```

### Foreign Keys

All foreign key fields use `String` type to match CUID IDs:

```prisma
model ChildModel {
  id        String @id @default(cuid())
  parentId  String  // Foreign key matching parent's cuid() ID
  parent    ParentModel @relation(fields: [parentId], references: [id])
}
```

## Rules (MUST NOT DEVIATE)

1. ✅ **All `@id` fields must use `String @default(cuid())`**
2. ✅ **All foreign key fields must use `String` type**
3. ❌ **NEVER mix cuid() and uuid() strategies**
4. ❌ **NEVER use autoincrement() for distributed systems**
5. ❌ **NEVER use `Int` IDs in new models**

## Validation

The ID strategy is enforced by automated tests in `engine/tests/test_schema_id_strategy.py`:

- `test_all_models_use_consistent_id_strategy()` - Ensures no mixing of cuid/uuid
- `test_no_autoincrement_ids()` - Prevents autoincrement usage
- `test_foreign_keys_match_id_type()` - Validates FK type consistency

These tests run in CI and will **fail the build** if the ID strategy is violated.

## Current Models Using CUID

As of 2026-01-18, all models use cuid() consistently:

- Category
- Listing
- ListingRelationship
- ExtractedListing
- FailedExtraction
- MergeConflict
- RawIngestion

## Future Considerations

### Moving to Supabase/PostgreSQL

CUIDs work natively in PostgreSQL. No migration needed.

If we later decide to switch to native PostgreSQL UUIDs:
1. Create a migration plan
2. Update this document with the decision
3. Update all models atomically (never mix strategies)
4. Run full test suite to validate

### UUID Alternative (Not Chosen)

If we had chosen UUID instead:
- **Pros**: Native PostgreSQL support, wider ecosystem adoption
- **Cons**: Random ordering (worse for DB performance), longer format, no creation timestamp info

We chose CUID for better sortability and Prisma ecosystem alignment.

## References

- Prisma ID Documentation: https://www.prisma.io/docs/reference/api-reference/prisma-schema-reference#id
- CUID Specification: https://github.com/paralleldrive/cuid
- Supabase Best Practices: Uses UUID by default, but supports any String ID strategy

## Maintenance Log

- **2026-01-18**: Initial standardization - documented cuid() strategy and created validation tests (Task 1.2a)
