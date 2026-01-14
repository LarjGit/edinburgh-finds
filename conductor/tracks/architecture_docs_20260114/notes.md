# Architectural Principles Extraction

## Core Mission
- **USP:** "AI-Scale, Local Soul".
- **Goal:** Hyper-local, niche discovery (starting with Padel in Edinburgh).

## Universal Entity Framework (UEF)
- **5 Pillars:**
  1. Infrastructure (Venues)
  2. Commerce (Retail)
  3. Guidance (Coaches)
  4. Organization (Clubs)
  5. Momentum (Events)
- **Scalability:** Uses "Generic Attributes" to scale horizontally (new niches) without schema migrations.

## Data Engine
- **Language:** Python.
- **Flow:** Autonomous Ingestion -> Processing -> Database.
- **Pattern:** ETL with validation (Pydantic).

## Trust & Quality
- **Confidence:** Credibility > Completeness.
- **Hierarchy:** Business Claimed > AI/Scraped.
- **Voice:** "Knowledgeable Local Friend" (Contextual, no fluff).

## Technical Architecture
- **Frontend:** Next.js (React), Tailwind, shadcn/ui.
- **Backend:** Next.js API Routes.
- **Database:** Supabase (PostgreSQL) - currently SQLite for dev.
- **ORM:** Prisma (v5).

## Design Philosophy
- "The Sophisticated Canvas".
- Agnostic elegance.

## Codebase Analysis
- **Schema Consistency:** `engine/schema.prisma` and `web/prisma/schema.prisma` match.
  - `Listing` model supports "Flexible Attribute Buckets" (`attributes`, `discovered_attributes`) implementing the UEF.
  - `EntityType` model supports the 5 Pillars concept.
- **Ingestion:**
  - `BaseConnector` (`engine/ingestion/base.py`) enforces the standard interface (`fetch`, `save`, `is_duplicate`).
  - `RawIngestion` model tracks source provenance.
- **Trust:** `field_confidence` and `source_info` fields exist in `Listing` model.