# Implementation Plan - Architecture Alignment & Ecosystem Graph

## Phase 1: Schema Extension (Ecosystem Graph) [checkpoint: 3880cbf]
- [x] Task: Update `engine/schema.prisma` to include `ListingRelationship` model.
    - [x] Sub-task: Define fields: `id`, `sourceListingId`, `targetListingId`, `type`, `confidence`, `source`.
    - [x] Sub-task: Add relation fields to `Listing` model.
- [x] Task: Replicate changes to `web/prisma/schema.prisma` to ensure parity.
- [x] Task: Generate and apply SQLite migration.
    - [x] Sub-task: Run `npx prisma migrate dev --name add_listing_relationship`.
- [x] Task: Regenerate Prisma Clients. [85596d7]
    - [x] Sub-task: `npx prisma generate` (for Web/JS).
    - [x] Sub-task: `prisma generate` (for Engine/Python).
- [~] Task: Conductor - User Manual Verification 'Schema Extension' (Protocol in workflow.md)

## Phase 2: Engine Alignment (Attribute Parsing)
- [x] Task: Analyze current "Upsert" logic in `engine` to identify where `attributes` should be populated.
- [x] Task: Implement/Update the `transform` step in the pipeline. [987e2c1]
    - [x] Sub-task: Create a utility function to map raw connector data to the `attributes` JSON schema.
    - [x] Sub-task: Ensure `attributes` field is included in the database write operation.
- [ ] Task: Verify with `EdinburghCouncilConnector` (or similar).
    - [ ] Sub-task: Run a test ingestion.
    - [ ] Sub-task: Check database to confirm `attributes` column contains valid JSON data.
- [ ] Task: Conductor - User Manual Verification 'Engine Alignment' (Protocol in workflow.md)

## Phase 3: Frontend Alignment (Attribute Display)
- [ ] Task: Create/Update a helper function in `web/lib/utils.ts` (or similar) to parse the `attributes` JSON safely.
- [ ] Task: Update the Listing Detail component (or `page.tsx`).
    - [ ] Sub-task: Fetch the `attributes` field.
    - [ ] Sub-task: Render key attributes (e.g., specific amenities) in the UI.
- [ ] Task: Conductor - User Manual Verification 'Frontend Alignment' (Protocol in workflow.md)
