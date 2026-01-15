# Implementation Plan - Refactor EntityType to Enum

## Phase 1: Documentation & Preparation [checkpoint: 5c7ba4f]
- [x] Task: Update `ARCHITECTURE.md` with new Entity Pillar concepts and Enum definition. [4c54205]
- [x] Task: Create specific tests for schema validation (to fail first) - verifying the new Enum structure. [25e41d2]
- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Schema & Engine Refactoring
- [ ] Task: Update `schema.prisma`: remove `EntityType` model, add Enum, update `Listing` and `Category`.
- [ ] Task: Update Python Pydantic models in `engine/schema/` to use the new Enum.
- [ ] Task: Refactor `engine/transform.py` and `engine/ingest.py` to handle the Enum mapping.
- [ ] Task: Update `seed_data.py` to use new Enum values.
- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: Database Reset & Verification
- [ ] Task: Drop local database and generate new migrations/client (`prisma migrate reset`).
- [ ] Task: Run updated seed script to verify end-to-end data flow.
- [ ] Task: Run full test suite (Python & TypeScript) to ensure no regressions.
- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)
