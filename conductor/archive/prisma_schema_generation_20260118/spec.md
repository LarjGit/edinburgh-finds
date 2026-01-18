# Track: Prisma Schema Generation
**Status**: Proposed
**Created**: 2026-01-18
**Owner**: Conductor
**Goal**: Automate the generation of `schema.prisma` files for both Engine and Web from the YAML "Single Source of Truth" to prevent schema divergence.

## Problem
The project relies on YAML files in `engine/config/schemas/` as the single source of truth for domain entities. However, the `prisma/schema.prisma` (Web) and `engine/schema.prisma` (Engine) files are currently maintained manually. This has led to critical divergence:
1.  Missing models (e.g., `MergeConflict` missing in Engine).
2.  Inconsistent configurations (e.g., hardcoded SQLite paths vs. environment variables).
3.  Risk of breaking the "Universal Entity Framework" if a field is added to YAML but forgotten in one of the Prisma files.

## Solution
Extend the existing schema generation system (`engine.schema.generate`) to programmatically generate the full content of `schema.prisma`.

### Key Requirements
1.  **Single Source of Truth**: The generator must read `engine/config/schemas/*.yaml` to generate domain models (`Listing`, `Venue`, etc.).
2.  **Infrastructure Support**: Infrastructure models (`RawIngestion`, `ExtractedListing`, `MergeConflict`) must be preserved. These should either be defined in a new `infrastructure.yaml` or maintained as a static template within the generator that is merged with the dynamic domain models.
3.  **Dual Output**: The generator must output two files:
    *   `engine/schema.prisma` (Engine context)
    *   `web/prisma/schema.prisma` (Web context)
4.  **Configuration Handling**:
    *   Both schemas should generally use `env("DATABASE_URL")`.
    *   The `generator client` blocks might differ (Python client for Engine, JS client for Web).
5.  **Strict Mode**: The generation process should overwrite the files entirely (with a warning/header "DO NOT EDIT") to enforce the automation.

## Architecture
*   **Generator**: `engine/schema/generators/prisma_generator.py`
    *   Input: Parsed YAML schemas.
    *   Template: Base definitions for `RawIngestion`, `MergeConflict`, etc.
    *   Logic: Map `FieldSpec` types (e.g., `string`, `list[string]`) to Prisma types (e.g., `String`, `String` (with validation) or JSON if needed, though SQLite has limitations).
*   **CLI**: Update `engine/schema/cli.py` to add a `--prisma` step.

## Verification
*   Running `python -m engine.schema.generate` should update both `.prisma` files.
*   Running `prisma generate` (JS) and `prisma generate` (Python) should succeed without errors.
*   The `MergeConflict` model and any other infrastructure models must be present in both.
