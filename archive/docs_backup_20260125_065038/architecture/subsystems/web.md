# Subsystem: web

## Purpose
The `web` subsystem is the frontend application for Edinburgh Finds, providing a user interface for exploring and querying the system's data. It is built as a modern web application using the Next.js framework.

## Key Components
- **Framework Configuration**: `next.config.ts` and `tsconfig.json` define the Next.js and TypeScript environment.
- **Dependency Management**: `package.json` tracks core dependencies including Next.js (16.1.1), React (19.2.3), and Prisma (7.3.0).
- **UI System**: `components.json` configures the Shadcn/UI component library, using Tailwind CSS for styling and Lucide for icons.
- **Environment**: `.env.example` (and the actual `.env`) manages local environment variables like `DATABASE_URL`.
- **Styling**: `postcss.config.mjs` and Tailwind CSS 4 provide the styling engine.

## Architecture
The subsystem follows the Next.js App Router architecture. It utilizes:
- **Server Components (RSC)**: Enabled by default in the Next.js App Router, as indicated by `components.json`.
- **Prisma ORM**: Used for direct database access from the web application.
- **Path Aliases**: Configured in `tsconfig.json` to allow clean imports using the `@/*` prefix.

## Dependencies
### Internal
- **Database**: The web application depends on the database schema defined in the project, accessed via the Prisma client.
- **Frontend Core**: Depends on `web/lib` for utilities and queries (documented in the `frontend` subsystem).

### External
- **Next.js**: The core application framework.
- **React**: The UI library.
- **Prisma**: ORM for database communication.
- **Tailwind CSS**: Utility-first CSS framework.
- **Shadcn/UI**: Component library for UI elements.
- **Lucide React**: Icon library.

## Data Models
The subsystem interacts with the data models defined in the Prisma schema (e.g., `web/prisma/schema.prisma`). It expects a PostgreSQL database connection string.

## Configuration
- `DATABASE_URL`: Connection string for the PostgreSQL database.
- `next.config.ts`: Next.js specific configuration options.
- `tsconfig.json`: TypeScript compiler options and path mapping.

## Evidence
- Purpose: `web/README.md:1-5`
- Dependencies: `web/package.json:11-30`
- UI Config: `web/components.json:1-20`
- TS Config: `web/tsconfig.json:1-35`
- Next Config: `web/next.config.ts:1-7`
