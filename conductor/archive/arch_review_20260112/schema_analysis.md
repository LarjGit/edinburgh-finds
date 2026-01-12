# Schema Analysis Findings

## 1. High-Level Assessment
The current `prisma/schema.prisma` is **heavily over-specialized** for the initial use case (Sports/Padel) and fundamentally conflicts with the "Niche-Agnostic" Product Vision. It uses a "Table-Per-Type" approach with wide, hardcoded columns for specific attributes, which will make adding new non-sports categories (e.g., Pottery, Chess) difficult and messy.

## 2. Specific Gaps

### A. The `Venue` Model Anti-Pattern
- **Issue:** The `Venue` model contains ~50 hardcoded columns specific to sports (e.g., `tennis_total_courts`, `hydro_pool`, `football_5_a_side`).
- **Conflict:** This violates the requirement to support *any* niche. If we add a "Pottery Studio", we would need to add columns like `kiln_count` or `wheel_available` to this table, or create a new `Studio` table.
- **Risk:** Database "Swiss Army Knife" bloat. Most rows will have 90% null values. Migrations will be required for every new niche feature.

### B. Missing Entity Models
- **Issue:** The schema defines `Venue` and `Coach` but is missing `Retailer`, `Club`, and `Event`, which are explicitly listed in the Product Guide.
- **Conflict:** Incomplete representation of the domain.

### C. Inconsistent Attribute Storage
- **Issue:** `Listing` has `other_attributes` (JSON), but `Venue` breaks this data out into strict columns.
- **Conflict:** Two ways of doing the same thing. The JSON approach in `Listing` is actually *better* for the "Niche-Agnostic" vision, while the `Venue` table is a regression to rigid schema.

## 3. Recommendations for Refactor

1.  **Drop the `Venue` Model (or severely reduce it):**
    -   Move all specific attributes (court counts, pool lengths) into a structured JSONB column (e.g., `attributes` or `specifications`) on the `Listing` model or a simplified `ListingDetail` model.
    -   This allows a "Pottery Studio" to have `{ "kilns": 3 }` and a "Padel Court" to have `{ "courts": 4 }` without schema changes.

2.  **Unified Entity Type Handling:**
    -   Instead of separate tables for `Venue`, `Coach`, `Retailer`, use the `entity_type` field to drive validation logic in the application layer (Zod schemas), not the database layer.

3.  **Preserve `Listing` Core:**
    -   The `Listing` model is actually well-structured (Name, Location, Contact). This should remain the anchor.
