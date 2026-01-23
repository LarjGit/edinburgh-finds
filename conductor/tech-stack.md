# Technology Stack

## System Architecture
See /ARCHITECTURE.md for complete system design, component interactions, data flows, entity relationships, and scaling strategies.

## Frontend
- **Framework:** Next.js 16 (React 19)
- **Styling:** Tailwind CSS v4
- **Component Library:** shadcn/ui
- **Language:** TypeScript

## Backend
- **Framework:** Next.js API Routes (Server Actions/API)
- **ORM:** Prisma 7.3+ (PostgreSQL)
- **Language:** TypeScript

## Database
- **Primary Database:** Supabase (PostgreSQL)

## Data Engine / Scripts
- **Language:** Python
- **Purpose:** Data extraction, processing, and seeding (ETL).
- **Schema Management:** YAML-based single source of truth
  - *YAML schemas auto-generate Python FieldSpecs and Prisma schemas*
  - *Eliminates schema drift, enables horizontal scaling*
  - *Location: `engine/config/schemas/*.yaml`*
- **Validation:** Pydantic (Schema-Driven)
- **LLM Integration:** Instructor + Anthropic (Claude)
- **Data Processing:** phonenumbers, fuzzywuzzy
- **ORM:** Prisma Client Python