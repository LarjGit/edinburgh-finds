# Engine Analysis Findings

## 1. High-Level Assessment
The `seed_data.py` script is a brittle, "Happy Path" prototype script. It is tightly coupled to the current schema's specific column structure and uses raw SQL in a way that will make refactoring extremely painful. It is not suitable for a production-grade ETL pipeline.

## 2. Specific Risks

### A. Tightly Coupled SQL Inserts
- **Issue:** The `INSERT INTO Venue` statement relies on a hardcoded list of ~50 positional arguments.
- **Risk:** Changing a single column in the `Venue` table (adding, removing, or reordering) will break this script instantly. It requires "Lock-step" updates with `schema.prisma`.

### B. Unsafe Internal Table Access
- **Issue:** The script manually inserts into `_CategoryToListing` and `_CategoryToEntityType`.
- **Risk:** These are Prisma's *internal* implicit link tables. Prisma does not guarantee these names stay stable. Writing to them directly is brittle and bypasses any application-level logic.

### C. Hardcoded Taxonomy
- **Issue:** Categories like "Padel" and "Football" are hardcoded in the script.
- **Conflict:** The Product Vision is "Niche-Agnostic". We should not be hardcoding specific niches in the code.

### D. Lack of Type Safety
- **Issue:** Raw dictionaries are passed around. There is no validation that the `raw_data` actually matches what the `INSERT` statement expects before the SQL query executes and fails.

## 3. Recommendations for Refactor

1.  **Adopt a Python ORM (or Prisma Python):**
    -   Use `prisma-client-python` or `SQLAlchemy`. This allows us to interact with the DB using objects (`Venue.create(...)`), which is far more robust to schema changes than raw `INSERT` strings.

2.  **Generic Ingestion Pipeline:**
    -   Create a function `ingest_entity(payload)` that:
        1.  Validates the payload against a schema (e.g., Pydantic).
        2.  Upserts the `Listing` (core data).
        3.  Upserts the specific Type data (e.g., `Venue`, `Retailer`) based on `entity_type`.

3.  **Dynamic Category Creation:**
    -   Categories should be created dynamically based on the incoming data tags, not a hardcoded list.
