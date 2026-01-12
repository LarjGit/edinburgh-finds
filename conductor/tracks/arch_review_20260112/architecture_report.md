# Architecture & Foundation Report

## Executive Summary
The current project state (as inherited) is a "Sports-Specific Prototype" that is **incompatible** with the new "Niche-Agnostic Directory" vision defined in `product.md`. Proceeding with UI development on top of the current schema and data engine would be a mistake, leading to significant technical debt and inevitable rewrites.

## Key Findings

### 1. Database Schema (Prisma)
- **Status:** **Critical Misalignment.**
- **Issue:** The `Venue` table is a "God Object" for sports attributes (tennis courts, pool length, etc.). This makes it impossible to store non-sports entities (e.g., Pottery Classes, Retailers) without constant schema migrations.
- **Risk:** High. Scaling to new niches will be painful.

### 2. Data Engine (Python)
- **Status:** **Fragile Prototype.**
- **Issue:** The `seed_data.py` script uses raw SQL with hardcoded positional arguments tightly coupled to the flawed schema. It is brittle and unsafe.
- **Risk:** High. Any schema change breaks the ingestion pipeline.

### 3. Frontend (Next.js)
- **Status:** **Greenfield / Blank Slate.**
- **Issue:** No architecture exists yet.
- **Risk:** Low (Opportunity). We have the chance to set up a correct Feature-Based Architecture and Route Groups from Day 1.

## Strategic Recommendations

### Recommendation 1: Refactor Schema FIRST
We must pivot the database design from "Sports Venue DB" to "Generic Entity Directory".
- **Action:** Flatten the `Venue` table into the `Listing` table using a `JSONB` column for `attributes`.
- **Action:** Remove the hardcoded `Venue` / `Coach` models in favor of a unified `Listing` model that relies on application-level validation (Zod) for type-specific data.

### Recommendation 2: Rewrite Data Engine
The ingestion logic needs to support the new generic schema.
- **Action:** Replace `seed_data.py` with a robust `ingestor` module using a Python ORM (Prisma Python) or safer SQL construction.
- **Action:** Implement dynamic category creation.

### Recommendation 3: Feature-Based Frontend
- **Action:** Initialize the Next.js project with a `features/` directory structure.
- **Action:** Define Route Groups (`(public)`, `(app)`, `(admin)`).

## Proposed Next Steps (The "Real" Track)

I recommend the next immediate track be:

**Track: Core Architecture Refactor**
1.  **Refactor Prisma Schema:** Implement the "Generic Listing" model (remove `Venue` table).
2.  **Refactor Seed Script:** Rewrite `seed_data.py` to populate the new generic schema using the existing JSON data.
3.  **Scaffold Frontend:** Create the folder structure (`features/`, `(routes)`) to match the new vision.

*Only after this refactor should we begin building the UI.*
