# Architecture & Review Report - 2026-01-12

## 1. Executive Summary
The system has successfully transitioned to a Generic Entity Architecture, with the `Listing` model correctly serving as the foundation for all entity types. The Engine (Python) and Web (Next.js) components are structurally aligned. However, a critical configuration issue was identified in the Web Prisma schema that requires immediate remediation.

## 2. Schema Analysis

### 2.1 Sync Status
-   **Engine Schema (`engine/schema.prisma`):** Correctly defines the `Listing` model and points to the `web/dev.db` SQLite file.
-   **Web Schema (`web/prisma/schema.prisma`):** Identical model structure to Engine. **CRITICAL ISSUE:** The `datasource db` block is missing the `url` property (e.g., `url = env("DATABASE_URL")`). This will cause database connection failures in the web application.

### 2.2 Generic Model Adoption
-   The `Listing` model is robust and implemented consistently across both schemas.
-   The `attributes` and `discovered_attributes` JSON columns are present to handle entity-specific data (e.g., Court numbers for Venues), implementing the "Flexible Attribute Bucket" pattern effectively.
-   Python specifications in `engine/schema/venue.py` correctly extend the base `Listing` fields, ensuring that the ETL process can validate specific attributes before storing them in the generic JSON column.

## 3. Documentation Alignment

### 3.1 Code-to-Docs Matches
-   **Tech Stack:** The actual codebase matches `conductor/tech-stack.md` (Next.js, Tailwind, Prisma, Python Engine).
-   **Product Vision:** The generic architecture directly supports the "Multi-Faceted Search & Discovery" feature described in `product.md`.
-   **Workflow:** The project structure respects the `conductor` workflow and track organization.

### 3.2 Gaps Identified
-   **Missing URL in Web Schema:** As noted in 2.1.

## 4. Architectural Health
-   **Separation of Concerns:** Excellent separation between the Data Engine (ETL/Ingestion) and the Web Application. They share data via the Database but have distinct responsibilities.
-   **Dependencies:** No circular dependencies or major structural issues found.
-   **File Organization:** Clean and logical structure.

## 5. Recommendations
1.  **Immediate Fix:** Add `url = env("DATABASE_URL")` to `web/prisma/schema.prisma`.
2.  **Verify Env:** Ensure `.env` in `web/` contains the correct `DATABASE_URL`.
