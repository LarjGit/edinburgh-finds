# Technology Stack

## System Architecture
See /ARCHITECTURE.md for complete system design, 
component interactions, data flows, entity relationships, and scaling strategies.
## Frontend
- **Framework:** Next.js (React)
- **Styling:** Tailwind CSS
- **Component Library:** shadcn/ui
- **Language:** TypeScript

## Backend
- **Framework:** Next.js API Routes (Server Actions/API)
- **ORM:** Prisma 5 (Stable) - *Pinned to v5 to ensure stability with SQLite and standard configuration.*
- **Language:** TypeScript

## Database
- **Primary Database:** Supabase (PostgreSQL)
    - *Note: Current development uses SQLite as a temporary placeholder.*

## Data Engine / Scripts
- **Language:** Python
- **Purpose:** Data extraction, processing, and seeding (ETL).
- **Validation:** Pydantic (Schema-Driven)
- **ORM:** Prisma Client Python
