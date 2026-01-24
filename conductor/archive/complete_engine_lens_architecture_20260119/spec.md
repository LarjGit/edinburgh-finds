# Specification: Complete Engine-Lens Architecture

## 1. Problem Definition
The "Engine-Lens" architecture is partially implemented but strictly blocked by:
1.  **Database Limitation:** The system runs on SQLite, forcing `canonical_*` dimensions to be stored as JSON strings instead of native Postgres arrays (`String[]`). This prevents the use of GIN indexes and efficient array filtering (`has`, `hasSome`).
2.  **Engine Impurity:** The `engine/` directory still contains:
    *   Legacy schema files (`engine/schema/venue.py`).
    *   Hardcoded vertical keywords ("coach", "instructor", "tennis") in `entity_classifier.py`.
    *   Ingestion pipelines defaulting to `VENUE_FIELDS`.
3.  **Logic Errors:**
    *   Classification priority checks `person` before `organization` (incorrect).
    *   Module trigger loader expects a `dict`, but the YAML spec uses a `list`.
    *   Confidence thresholds are hardcoded (0.7) rather than configurable.

## 2. Solution Architecture

### 2.1 Database (Supabase/Postgres)
The database MUST be PostgreSQL (Supabase).
*   **Provider:** `postgresql`
*   **Dimensions:** `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access` must be type `String[]` (native array).
*   **Indexes:** GIN indexes on all dimension arrays.
*   **Defaults:** `@default([])` (empty array, never null).

### 2.2 Engine Purity (The "Opaque" Rule)
The Engine (`engine/`) must treat all strings as opaque values.
*   **Forbidden:** `if "tennis" in categories:`
*   **Forbidden:** `if "coach" in name:`
*   **Allowed:** `if entity_class == "person":`
*   **Allowed:** `required_modules = lens_contract.get_required_modules(...)`

Any vertical-specific logic must be moved to:
1.  `lens.yaml` (Mappings, Triggers).
2.  `LensContract` (The injected configuration).

### 2.3 Correct Classification Priority
The deterministic classification algorithm must be:
1.  **Event** (Time-bounded? Start/End dates?) -> `event`
2.  **Place** (Physical location? Address/Coords?) -> `place`
3.  **Organization** (Membership? Group? No fixed location?) -> `organization`
4.  **Person** (Named individual?) -> `person`
5.  **Thing** (Fallback) -> `thing`

## 3. Scope of Work

### Must Have
*   Migration to Supabase (Postgres).
*   `schema.prisma` updated to `postgresql` and `String[]`.
*   Removal of `engine/schema/venue.py`.
*   Removal of vertical keywords from `entity_classifier.py`.
*   Fix for `ModuleTrigger` loader (list vs dict).
*   Configurable confidence threshold in `lens.yaml`.

### Out of Scope
*   New features or lenses (beyond fixing the existing ones).
*   Frontend UI overhaul (focus is on the backend/data layer).

## 4. Success Criteria
1.  **Supabase Connection:** `DATABASE_URL` points to a valid Postgres instance.
2.  **Native Arrays:** `prisma migrate dev` creates columns as `text[]`.
3.  **Clean Grep:** Searching for "tennis" or "coach" in `engine/` returns ZERO results (excluding tests).
4.  **Test Pass:** `tests/query/test_prisma_array_filters.py` passes (verifying GIN indexes).
