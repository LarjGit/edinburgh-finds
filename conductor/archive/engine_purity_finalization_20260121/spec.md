# Track Specification: Engine Purity Finalization

## 🎯 Objective
Finish purifying the engine layer so it contains **zero** vertical or product semantics, uses correct neutral terminology, and cleanly separates:
- **Engine** → universal entity persistence + opaque tokens
- **Lens layer** → all vertical interpretation, navigation, mapping, SEO, UI semantics

## 📌 Current Context
- **Prisma** is used in both `engine/` (prisma-client-py) and `web/` (prisma-client-js).
- **Database** is PostgreSQL (Supabase).
- **Current primary model name** is `Listing`.
- **Legacy vertical artifacts** still exist:
  - `entityType` column
  - `EntityType` enum (VENUE, COACH, etc.)
- **Canonical dimensions** already exist:
  - `canonical_activities`
  - `canonical_roles`
  - `canonical_place_types`
  - `canonical_access`
- **Lenses** are loaded via `lenses/loader.py` and identified by `lens_id` (e.g., `edinburgh_finds`).
- **Category model** currently exists but is legacy navigation scaffolding and must be removed.

## 🛡️ Engine Purity Guardrails
To protect the architecture long-term, the following rules are immutable:

1.  **Engine must not interpret:**
    -   `raw_categories` (treated as opaque data).
    -   Canonical dimension meanings (engine stores them, lenses define what they mean).
    -   Module semantics (JSON blobs are opaque to engine).
    -   Lens semantics (what makes a "pub" a "pub" is a lens rule, not an engine type).

2.  **Engine may only:**
    -   Store opaque values.
    -   Index canonical dimensions for performance.
    -   Enforce universal structural constraints (IDs, timestamps, relations).

3.  **Future Logic Location:**
    -   Any future taxonomy, labeling, grouping, or navigation logic **must live in lenses**, not the engine.

## 🚨 Issues To Fix
### Issue 1 — Vertical leakage via EntityType / entityType
- Vertical-coded enum and DB field violate engine purity.
- Engine must only use universal `entity_class`: `place | person | organization | event | thing`.

### Issue 2 — Misleading naming: Listing
- The engine stores canonical entities, not “listings”.
- The primary persisted model must be renamed from `Listing` → `Entity`.
- Relationship and derived models must follow this rename consistently.

### Issue 3 — Legacy Category taxonomy
- Category was originally UI navigation scaffolding.
- Categories like “padel”, “chess”, “pickleball” are already modeled via canonical dimensions.
- Categories are lens-specific and do NOT belong in engine persistence.
- **Category must be deleted entirely** (no alternatives).

### Issue 4 — Lens membership not persisted
- Lenses exist at runtime (`lens_id`) but membership is not represented in DB.
- Add a minimal, engine-agnostic join table to persist membership.
- **Lens registry (Lens table) is optional.**
- **LensEntity join table is required.**

## ✅ Required Remedial Actions (NO OPTIONS)

### A) Remove vertical-coded type artifacts
- Remove `entityType` field from Prisma schemas and database.
- Remove `EntityType` enum and all imports/usages.
- Remove any normalization helpers that translate legacy types.
- Update extractors:
  - Must NOT default to VENUE or any vertical type.
  - Must populate `entity_class` using universal classifier logic.
  - Ensure `entity_class` is required (NOT NULL) everywhere.

### B) Rename Listing → Entity everywhere
- This is a semantic correction, not optional.
- Rename Prisma model: `model Listing` → `model Entity`
- Rename dependent models consistently:
  - `ListingRelationship` → `EntityRelationship`
  - `ExtractedListing` → `ExtractedEntity`
  - Any other generated or referenced types.
- **Rename Impact Scope:** This is a cross-repo rename operation.
  - Prisma schemas
  - Generated Python schema
  - Generated JS schema
  - Imports
  - Tests
  - Migrations
  - Any raw SQL

### C) Delete Category completely (FINAL DECISION — NO OPTIONS)
- Categories are not part of the engine model anymore.
- Delete `Category` model from all Prisma schemas.
- Remove all relations between `Entity` and `Category`.
- Do NOT replace Category with another taxonomy table.
- **Clarification:** The Category *model and taxonomy* are fully deleted. This does NOT conflict with keeping `raw_categories` (see Section F), which are observational signals only and not taxonomy.
- Remove seeders, tests, and utilities that depend on Category.
- Navigation and filtering must come exclusively from:
  - canonical dimension arrays
  - lens facet definitions
  - lens mapping rules
  - derived groupings (computed at query time)

### D) Add persisted lens membership (engine-agnostic)
- Add minimal membership persistence.
- **Lens Registry (`Lens` table) is OPTIONAL.** If implemented, it must remain purely generic and contain no business semantics.
- **LensEntity join table is REQUIRED.**
  - `lens_id`
  - `entity_id`
  - `timestamps`
  - optional metadata (source, confidence)
  - PK (`lens_id`, `entity_id`)
- Add appropriate indexes for lookup by lens and by entity.
- Keep this model strictly generic — no vertical meaning.
- **Membership Semantics:**
    - Lens membership represents **inclusion in a product surface / lens**.
    - It is **NOT** classification.
    - It is **NOT** taxonomy.
    - It is **NOT** inference.
    - Membership is explicitly managed by application workflows or tooling. The engine does not decide what belongs in a lens.

### E) Explicit Lens Membership API
- Do NOT auto-infer lens membership implicitly in extraction pipelines.
- Implement explicit functions/services:
  - `attach_entity_to_lens(entity_id, lens_id)`
  - `detach_entity_from_lens(entity_id, lens_id)`
- Lens membership should be:
  - Explicit
  - Auditable
  - Engine-generic
  - No vertical heuristics or business rules in engine code.
- This is a persistence concern, not inference logic.

### F) Raw Categories (Discovery Only — Engine-Pure)
The engine WILL persist raw category labels as uncontrolled discovery signals.
- **Schema:** Add field on Entity: `raw_categories String[] @default([])`
- **Purpose:** These values represent observed labels from sources, scrapers, or LLM output (uncontrolled, noisy, and non-canonical).
- **Naming Note:** Although the field is named `raw_categories`, it must be treated strictly as uncontrolled observational labels, not as taxonomy or canonical categories. If semantic confusion ever arises, this field may be renamed to `observed_labels` or similar in a future cleanup without behavioral impact.
- **Engine Purity Rules:** The engine MUST treat raw categories as:
  - Opaque strings
  - No validation
  - No normalization
  - No indexing (for search/filtering)
  - No joins
  - No interpretation
- **Validation Checklist:**
    - [ ] Verify `raw_categories` field exists in schema.
    - [ ] Verify it is **not** indexed.
    - [ ] Verify no queries filter on `raw_categories`.
    - [ ] Verify no UI uses `raw_categories` directly.
    - [ ] Verify no engine code maps or normalizes `raw_categories`.
- **Usage Restrictions:** Raw categories MUST NOT:
  - Drive UI navigation
  - Be used directly for filtering or querying
  - Be exposed as canonical values
  - Be mapped inside engine logic
- **Permitted Use:** Raw categories MAY:
  - Be inspected for debugging and discovery
  - Be used by lens mapping rules (outside engine)
  - Inform future canonical dimension design decisions

## 🧹 Clean Slate Rule (CLEAN SLATE MODE)

This project is early-stage. We do not need to retain data and we do not need backward compatibility.
1.  **Destructive Changes Allowed:** It is acceptable for Prisma migrations to drop and recreate tables.
2.  **Reset Procedure:** Before applying migrations, we will reset the dev database (using `prisma migrate reset`).
3.  **Repopulation:** We will re-run ingestion/extraction scripts to repopulate data after the schema change.
4.  **Simplicity First:** We prefer the simplest implementation path (clean slate) over complex `ALTER TABLE` rename logic.