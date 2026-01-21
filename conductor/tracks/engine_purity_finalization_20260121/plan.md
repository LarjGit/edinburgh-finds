# Track Plan: Engine Purity Finalization

**Track ID:** `engine_purity_finalization_20260121`
**Status:** Active
**Priority:** Critical
**Objective:** Finalize engine purity and schema naming cleanup for a vertical-agnostic Entity Engine using a "Clean Slate" approach.

## 🧭 Implementation Phases

### Phase 1 — Schema & DB Migration (Clean Slate) ✅ COMPLETE
**Goal:** Establish the correct database schema (Entity, Lens, LensEntity) and remove legacy artifacts (Category, EntityType) by resetting the database.

**Clean Slate Rule:**
*We accept destructive changes. We will reset the DB and run fresh migrations.*

**Checkpoint:** `6b6eb2e` - Phase 1 Complete - Schema & DB Migration

- [x] **Task 1.1:** Update Prisma Schemas (Rename Listing -> Entity).
    -   **Files:** `engine/schema.prisma`, `web/prisma/schema.prisma`
    -   **Action:**
        -   Rename `model Listing` -> `model Entity`.
        -   Rename `model ListingRelationship` -> `model EntityRelationship`.
        -   Rename `model ExtractedListing` -> `model ExtractedEntity`.
        -   Update fields: `listingId` -> `entityId`, `targetListingId` -> `targetEntityId`.
    -   **Verification:** Run `npx prisma format --schema=engine/schema.prisma` to confirm syntax.

- [x] **Task 1.2:** Update Prisma Schemas (Remove Legacy & Add Discovery Signals).
    -   **Files:** `engine/schema.prisma`, `web/prisma/schema.prisma`
    -   **Deletions:**
        -   Remove `entityType` field from `Entity` model.
        -   Remove `model Category`.
        -   Remove relations: `Category` <-> `Entity`.
    -   **Additions:**
        -   Add `raw_categories String[] @default([])` to `Entity` model.
    -   **Guardrail Verification:** Ensure NO index is defined on `raw_categories`.

- [x] **Task 1.3:** Update Prisma Schemas (Add Lens Membership).
    -   **Files:** `engine/schema.prisma`, `web/prisma/schema.prisma`
    -   **Additions:**
        -   Define `model LensEntity`:
            ```prisma
            model LensEntity {
              lensId    String
              entityId  String
              entity    Entity   @relation(fields: [entityId], references: [id], onDelete: Cascade)
              createdAt DateTime @default(now())
              @@id([lensId, entityId])
              @@index([lensId])
              @@index([entityId])
            }
            ```
        -   Add relation field to `Entity`: `lensMemberships LensEntity[]`.
    -   **Verification:** Run `npx prisma format` on both schemas.

- [x] **Task 1.4:** Database Reset & Clean Migration.
    -   **Commands:**
        1.  `export DATABASE_URL=<YOUR_DEV_DB_URL>` (User to verify).
        2.  `npx prisma migrate reset --force --schema=engine/schema.prisma` (Drops all data).
        3.  `npx prisma migrate dev --name engine_purity_v1 --schema=engine/schema.prisma` (Creates fresh migration).
    -   **Verification:** Connect to DB (e.g., `psql`) and run `\dt`. Expect `Entity` table, NO `Listing`, NO `Category`.

### Phase 2 — Code Refactors
**Goal:** Update the codebase to match the new schema and remove vertical logic.

- [x] **Task 2.1:** Update Imports & Type Definitions (Cross-Repo).
    -   **Files:** `engine/**/*.py`, `web/src/**/*.ts`, `web/src/**/*.tsx`, `tests/**/*.py`.
    -   **Action:**
        -   Search `Listing` -> Replace `Entity`.
        -   Search `ExtractedListing` -> Replace `ExtractedEntity`.
        -   Search `listing_id` -> Replace `entity_id`.
    -   **Verification:** `grep -r "Listing" engine/ | grep -v "migration"` should be clean.

- [x] **Task 2.2:** Regenerate Schemas & Clients.
    -   **Commands:**
        1.  `python -m engine.schema.generate` (Updates Python Pydantic models).
        2.  `npx prisma generate --schema=engine/schema.prisma` (Updates Python Prisma client).
        3.  `cd web && npx prisma generate` (Updates JS Prisma client).
    -   **Verification:** Check `engine/schema.py` defines `class Entity`.

- [ ] **Task 2.3:** Remove EntityType Usage.
    -   **Files:** `engine/extraction/models.py`, `engine/schema.prisma` (already done), `engine/config/entity_model.yaml`.
    -   **Action:**
        -   Delete `EntityType` enum definition in code.
        -   Remove usage in extractors.
    -   **Verification:** `grep -r "EntityType" engine/` should return nothing.

- [ ] **Task 2.4:** Update Extractors.
    -   **Files:** `engine/extraction/base.py`, `engine/extraction/extractors/*.py`.
    -   **Action:**
        -   Update return type hints to `Entity`.
        -   Remove `VENUE` default assignments.
        -   Populate `raw_categories` from source data (without processing).
    -   **Verification:** Run `pytest tests/engine/test_extraction_base.py` (or equivalent).

### Phase 3 — Lens + Category Cleanup
**Goal:** Completely excise Category logic and implement explicit Lens membership.

- [ ] **Task 3.1:** Remove Category Logic from Engine.
    -   **Files:**
        -   Delete `engine/config/canonical_categories.yaml`.
        -   Update `engine/classification_rules.md` (remove category rules).
    -   **Verification:** `ls engine/config/canonical_categories.yaml` should fail.

- [ ] **Task 3.2:** Implement Explicit Lens Membership API.
    -   **Files:** Create/Update `engine/lenses/ops.py` (or similar utility).
    -   **Action:** Implement:
        -   `def attach_entity_to_lens(entity_id: str, lens_id: str): ...`
        -   `def detach_entity_from_lens(entity_id: str, lens_id: str): ...`
    -   **Constraint:** Ensure these methods perform direct DB writes to `LensEntity`.

- [ ] **Task 3.3:** Update Lens Loader.
    -   **Files:** `engine/lenses/loader.py`.
    -   **Action:** Verify lens loading logic does not depend on `Category` model.

### Phase 4 — Tests + Validation + Docs
**Goal:** Verify the system is stable, pure, and documented.

- [ ] **Task 4.1:** Update Tests.
    -   **Files:** `tests/engine/`, `tests/web/`.
    -   **Action:**
        -   Fix import errors in existing tests.
        -   Remove `tests/engine/test_category.py` (if exists).
        -   Add `tests/engine/test_lens_membership.py`.
    -   **Verification:** Run `pytest tests/engine`.

- [ ] **Task 4.2:** Repopulation & Smoke Test (Fast Reset).
    -   **Command:** `python -m engine.extraction.run_all --source osm --limit 5`
    -   **Verification:**
        -   Check `Entity` table has rows.
        -   Check `raw_categories` column has data (e.g., `['bar', 'pub']`).
        -   Check `LensEntity` table has rows (if lens logic runs separately).

- [ ] **Task 4.3:** Update Documentation.
    -   **Files:** `ARCHITECTURE.md`, `engine/README.md`.
    -   **Action:** Replace "Listing" references with "Entity". Document `LensEntity`.

## 🧪 Acceptance Criteria

The track is complete only when:

- [ ] ✅ No `entityType` column exists in DB or Prisma schema.
- [ ] ✅ No `EntityType` enum exists or is referenced in engine code.
- [ ] ✅ Primary persisted model is named `Entity`, not `Listing`.
- [ ] ✅ No `Category` model or relations exist anywhere.
- [ ] ✅ **Entity has `raw_categories` String[] field for discovery signals.**
- [ ] ✅ **`raw_categories` is not indexed, queried for filtering, or used in UI paths.**
- [ ] ✅ **No category taxonomy or canonical category table exists.**
- [ ] ✅ Lens membership table (`LensEntity`) exists and works.
- [ ] ✅ `entity_class` is required and universal.
- [ ] ✅ Canonical dimension arrays remain unchanged.
- [ ] ✅ **modules JSON structure remains unchanged and continues to be treated as opaque engine data interpreted only by lenses.**
- [ ] ✅ Adding a new lens requires zero engine code changes.
- [ ] ✅ All tests pass.

## ⚡ Fast Reset Checklist

Before marking complete, perform this sequence:

1.  [ ] **Check Env:** `echo $DATABASE_URL` (Must be dev/local).
2.  [ ] **Reset:** `npx prisma migrate reset --force --schema=engine/schema.prisma`
3.  [ ] **Migrate:** `npx prisma migrate dev --schema=engine/schema.prisma`
4.  [ ] **Smoke Test:** `python -m engine.extraction.run_all --source osm --limit 1`

## 🔎 Validation Examples

```bash
# Verify no EntityType
grep -r "entityType" engine/ | grep -v "migration"

# Verify Listing is gone
grep -r "Listing" engine/schema.prisma

# Verify LensEntity exists & indexes are present
grep -A 10 "model LensEntity" engine/schema.prisma

# Verify raw_categories exists but is NOT indexed
grep "raw_categories" engine/schema.prisma
# Ensure NO @@index includes raw_categories
```
