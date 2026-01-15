# Track: Refactor EntityType to Enum & Update Architecture

## 1. Overview
The current system models `EntityType` as a separate database table with a many-to-many relationship to `Category`. To simplify the architecture and align with the conceptual design, this track will refactor `EntityType` to be a native PostgreSQL/Prisma Enum on the `Listing` model. The separate `EntityType` table and its relationship to `Category` will be removed.

Additionally, this track will update the project documentation (`ARCHITECTURE.md`) to clarify the distinction between the 5 conceptual "Entity Pillars" (Infrastructure, Commerce, Guidance, Organization, Momentum) and the concrete `EntityType` enum values.

## 2. Functional Requirements

### 2.1 Schema Changes
-   **Remove Model:** Delete the `EntityType` model from `schema.prisma`.
-   **Update Listing:** Replace the `entityTypeId` relation with a direct `entityType` field using a new Enum.
-   **Update Category:** Remove the relation to `EntityType`.
-   **Define Enum:** Create a new Enum `EntityType` with the following initial values (grouped by their conceptual pillar):
    -   **Infrastructure:** `VENUE`
    -   **Guidance:** `COACH`, `INSTRUCTOR`
    -   **Commerce:** `RETAILER`
    -   **Organization:** `CLUB`, `LEAGUE`
    -   **Momentum:** `EVENT`, `TOURNAMENT`

### 2.2 Documentation Updates
-   **Update ARCHITECTURE.md:**
    -   Clarify that the 5 Pillars are conceptual, not schema entities.
    -   Update the ERD/Schema diagrams to show `entityType` as an Enum on `Listing`.
    -   Remove the `EntityType` table entity from diagrams.
    -   Add a note on scaling: New types are added to the Enum and mapped to a pillar conceptually.

### 2.3 Codebase Refactoring
-   **Engine/Ingestion:** Update Python Pydantic models (e.g., `engine/schema/*.py`) to use the new Enum instead of expecting a relation ID or table lookup.
-   **Seeding/Scripts:** Update `seed_data.py` or any ingestion scripts that populate `Listing` to use the Enum values.
-   **Frontend:** Ensure any UI components relying on fetching the list of EntityTypes are updated (if applicable) or hardcoded/mapped from the Enum definition.

## 3. Non-Functional Requirements
-   **Data Migration Strategy:** Reset Strategy. The database will be dropped/reset as this is a dev environment change. No complex migration script is needed to preserve existing IDs.
-   **Type Safety:** Ensure strict typing is maintained in both TypeScript (Prisma generated types) and Python (Pydantic/Prisma Client).

## 4. Acceptance Criteria
-   `schema.prisma` no longer contains `model EntityType`.
-   `Listing` model has a required `entityType` field of type `EntityType` (Enum).
-   `Category` model has no relation to `EntityType`.
-   `ARCHITECTURE.md` accurately reflects the new "Conceptual Pillars vs. Concrete Enum" design.
-   The application builds and runs successfully after a database reset (`prisma db push` / `prisma migrate reset`).
-   Ingestion/Seed scripts run without errors using the new Enum values.

## 5. Out of Scope
-   Preserving existing database data (we are resetting).
-   Complex UI features for managing dynamic EntityTypes (since it's now a code-defined Enum).
