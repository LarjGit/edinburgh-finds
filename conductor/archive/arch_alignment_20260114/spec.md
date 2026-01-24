# Specification: Architecture Alignment & Ecosystem Graph

## 1. Overview
This track focuses on bringing the codebase into full alignment with the `ARCHITECTURE.md` vision. It addresses two key areas:
1.  **Alignment Discrepancies:** Fixing the implementation of the "Flexible Attribute Bucket" strategy in both the Frontend (display) and Engine (parsing).
2.  **Ecosystem Graph:** Implementing the foundational schema for "Listing Relationships" (e.g., Coaches connected to Venues).

## 2. Functional Requirements

### 2.1. Alignment: Flexible Attribute Bucket
-   **Frontend (`web`):**
    -   The Listing Detail view must extract and display data from the `attributes` JSON column.
    -   It should gracefully handle missing or unstructured data in `discovered_attributes`.
-   **Engine (`engine`):**
    -   The ingestion pipeline must have a clear "Transform" step that parses raw data into the `Listing` model's `attributes` JSON column (validating against the schema).
    -   Currently, connectors save raw data; the `Upsert` logic needs to ensure `attributes` are populated.

### 2.2. Feature: Ecosystem Graph (Schema Only)
-   **Schema Extension:**
    -   Add `ListingRelationship` model to `prisma.schema` (in both `engine` and `web`).
    -   Fields: `id`, `sourceListingId`, `targetListingId`, `type` (e.g., `teaches_at`, `plays_at`), `confidence`, `source`.
-   **Database Migration:**
    -   Generate and apply the migration to the SQLite development database.
    -   Regenerate Prisma Clients for both Python and TypeScript.

## 3. Non-Functional Requirements
-   **Single Source of Truth:** `engine/schema.prisma` and `web/prisma/schema.prisma` must remain identical (or effectively synced).
-   **Data Integrity:** Existing data in `Listing` table must be preserved during migration.

## 4. Out of Scope
-   **Relationship UI:** No user-facing UI to create or display relationships yet.
-   **Relationship Logic:** No automatic inference of relationships.
-   **Business Claiming:** Owner override logic is deferred.
-   **Programmatic SEO:** deferred.

## 5. Acceptance Criteria
-   [ ] `ListingRelationship` table exists in the SQLite database.
-   [ ] Prisma Clients (JS and Python) are regenerated and typed correctly.
-   [ ] Frontend correctly renders at least one field from the `attributes` JSON bucket (e.g., "Number of Courts").
-   [ ] Engine ingestion flow successfully populates the `attributes` column for a sample listing.
