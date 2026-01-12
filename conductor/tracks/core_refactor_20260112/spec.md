# Track Specification: Core Architecture Refactor

## 1. Goal
To implement the "Generic Entity" architecture defined in the Architecture Review. The database schema will be simplified to a single `Listing` table with two JSON buckets:
1. `attributes`: Validated data driven by `FieldSpec` (Official Schema).
2. `discovered_attributes`: Catch-all for AI-extracted data not yet in the official schema.

The application logic (validation, types) will be driven by Python `FieldSpec` definitions ("Schema-Driven Development").

## 2. Scope
- **Schema Definitions:** Create/Port the `FieldSpec` python files (`common.py`, `venue.py`) to the `engine/schema` directory.
- **Database (Prisma):** Refactor `schema.prisma` to remove `Venue`/`Coach` tables and consolidate into `Listing`.
- **Generators:** Implement basic generators (or simple adapters) to derive Pydantic models from `FieldSpec`s.
- **Data Engine:** Rewrite `seed_data.py` to use the new "Generic Ingestion" pattern, validating against the generated models before inserting into the generic DB structure.

## 3. Deliverables
- **New Folder:** `engine/schema/` containing the Source of Truth `FieldSpecs`.
- **Refactored DB:** `schema.prisma` with generic `Listing` model.
- **Refactored Seed:** `engine/ingest.py` (replacing `seed_data.py`) that handles generic data.
- **Verification:** Successful seeding of Padel venues into the new structure.
