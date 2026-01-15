# Implementation Plan - Refactor EntityType to Enum

## Phase 1: Documentation & Preparation [checkpoint: 5c7ba4f]
- [x] Task: Update `ARCHITECTURE.md` with new Entity Pillar concepts and Enum definition. [4c54205]
- [x] Task: Create specific tests for schema validation (to fail first) - verifying the new Enum structure. [25e41d2]
- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Schema & Engine Refactoring [checkpoint: ae4efe2]
- [x] Task: Update `schema.prisma`: remove `EntityType` model, add Enum, update `Listing` and `Category`. [ae9d3bc]
- [x] Task: Update Python Pydantic models in `engine/schema/` to use the new Enum. [328ff24]
- [x] Task: Refactor `engine/transform.py` and `engine/ingest.py` to handle the Enum mapping. [9df74e8]
- [x] Task: Update `seed_data.py` to use new Enum values. [373dd81]
- [x] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: Database Reset & Verification
- [x] Task: Drop local database and generate new migrations/client (`prisma migrate reset`). [07efac3]
- [x] Task: Run updated seed script to verify end-to-end data flow. [07efac3]
- [x] Task: Run full test suite (Python & TypeScript) to ensure no regressions. [07efac3]
- [~] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)
