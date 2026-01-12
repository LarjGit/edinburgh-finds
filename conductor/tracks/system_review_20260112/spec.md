# Specification: Comprehensive Architecture & Documentation Review

## Overview
A comprehensive audit of the current codebase following recent refactoring efforts. The goal is to ensure architectural integrity, design consistency, and a strict bidirectional match between the actual file structure/code and the project documentation.

## Scope
-   **Core Engine (Python):** `engine/` directory (ingestion, schema, scripts).
-   **Database Schema:** Prisma schemas in both `engine/` and `web/` directories.
-   **Documentation:** `conductor/` directory (product, tech-stack, workflow).
-   **Project Structure:** Root level organization and file locations.

## Objectives
1.  **Schema Validation:**
    -   Verify the transition to generic entities (`Listing`).
    -   Check synchronization between `engine/schema.prisma` and `web/prisma/schema.prisma`.
    -   Ensure the schema supports the product vision defined in `product.md`.
2.  **Architectural Integrity:**
    -   Identify logical inconsistencies or circular dependencies.
    -   Validate the separation of concerns between Engine (ETL) and Web (App).
3.  **Documentation Synchronization:**
    -   **Code-to-Docs:** Ensure all major modules and files are documented.
    -   **Docs-to-Code:** Ensure all documented files and paths actually exist.
    -   Update `tech-stack.md` and `product.md` if discrepancies are found (flagging them first).

## Approach
-   **Analysis:** Use automated scripts and manual inspection to map the current codebase.
-   **Comparison:** Compare the map against the expectations set in `conductor/` files.
-   **Reporting:** Generate a report classifying findings by severity (Critical, Major, Minor).
-   **Planning:** Create a remediation plan for identified issues.

## Deliverables
1.  **Architecture Report:** A document detailing the current state, schema analysis, and architectural health.
2.  **Discrepancy Log:** A list of mismatches between code and docs.
3.  **Remediation Plan:** A set of actionable tasks to fix the findings.

## Acceptance Criteria
-   All "Critical" and "Major" architectural issues are identified.
-   A complete list of missing or outdated documentation is compiled.
-   The Prisma schema strategy is clearly evaluated and confirmed (or flagged for fix).
