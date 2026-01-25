# Subsystem: frontend

## Purpose
The frontend subsystem is a Next.js application that provides a user interface for browsing and filtering entities within the Edinburgh Finds ecosystem. It implements the "Lens" part of the Engine-Lens architecture, taking opaque canonical data from the database and interpreting it through lens-specific metadata to provide a rich, user-friendly experience.

## Key Components

### Core Application
- **`web/app/layout.tsx`**: The root layout for the Next.js application, managing global styles and font configurations.
- **`web/app/page.tsx`**: The main entry point that demonstrates entity display and faceted filtering. It shows how to use Prisma array filters for querying dimensions like activities and roles.

### Query & Data Layer
- **`web/lib/entity-queries.ts`**: Implements faceted search logic. It provides utilities for building Prisma `where` clauses using native PostgreSQL array operators (`hasSome`, `hasEvery`). It follows the "OR within facet, AND across facets" search semantics.
- **`web/lib/lens-query.ts`**: The primary lens-aware query layer. It handles the transformation of raw entities into `EntityView` objects, enriching them with labels, icons, and colors from lens definitions. It also computes derived groupings (e.g., "people" vs "places") at runtime based on entity properties.
- **`web/lib/prisma.ts`**: Ensures a singleton instance of the Prisma client is used across the application.
- **`web/lib/entity-helpers.ts`**: Provides defensive utilities for ensuring dimension fields (arrays) and module fields (JSONB) are correctly handled.

### Utilities & Types
- **`web/lib/utils.ts`**: contains UI utilities like `cn` for Tailwind class merging and formatters for entity attributes.
- **`web/types/index.ts`**: Exports shared TypeScript interfaces and types.

## Architecture

- **Next.js App Router**: Utilizes React Server Components for efficient data fetching and rendering.
- **Engine-Lens Pattern**: The frontend is "Lens-aware," meaning it knows how to map canonical keys (e.g., `padel`) to display metadata (e.g., "Padel" with a racket icon) using lens configuration.
- **Prisma Array Filters**: Leverages Prisma's native support for PostgreSQL `String[]` arrays to perform efficient faceted filtering directly in the database.
- **Derived Groupings**: Groupings are computed at query/view time from `entity_class` and `roles`, rather than being stored statically in the database, allowing for flexible categorization.
- **Styling**: Tailwind CSS for a modern, responsive, and maintainable UI.

## Dependencies

### Internal
- **Database Subsystem**: Depends on the Prisma schema and generated client for data access.
- **Engine Subsystem**: Consumes the data ingested and processed by the engine components.

### External
- **Next.js**: React framework for the web application.
- **Prisma**: Object-Relational Mapping (ORM) for PostgreSQL.
- **Tailwind CSS**: Utility-first CSS framework.
- **PostgreSQL**: Native array and JSONB features are critical for the data model.

## Data Models

### EntityView
A rich representation of an entity after lens transformation.
- `activities`, `roles`, `place_types`, `access`: Arrays of objects containing `key`, `label`, `icon`, and `color`.
- `grouping`: A derived string identifier (e.g., "places") computed from entity properties.

### FacetFilter
Configuration for faceted search.
- `dimensionSource`: The actual DB column name (e.g., `canonical_activities`).
- `selectedValues`: List of canonical keys to filter by.
- `mode`: Either `OR` (default, `hasSome`) or `AND` (`hasEvery`).

## Evidence
- **Prisma Array Filters**: `web/lib/entity-queries.ts:80-125`
- **Lens Transformation**: `web/lib/lens-query.ts:190-260`
- **Faceted Search Semantics**: `web/lib/entity-queries.ts:40-75`
- **Native Postgres Support**: `web/lib/entity-helpers.ts:1-40`
- **Next.js Integration**: `web/app/page.tsx:5-50`
