Audience: Developers

# Web Frontend Subsystem

The Web Frontend subsystem is a Next.js application that provides the user interface for discovering and exploring entities. It leverages the **Engine-Lens Architecture** to provide lens-aware filtering, searching, and rich entity visualization.

## Overview

The frontend is built with **Next.js 15 (App Router)** and **TypeScript**, using **Prisma** as the ORM to interact with the PostgreSQL database. It is designed to be "lens-aware," meaning it uses lens definitions to interpret raw database data and provide a rich, domain-specific user experience.

### Key Principles
- **Server-Side Rendering (SSR):** Most data fetching is performed in Server Components for performance and SEO.
- **Native Postgres Integration:** Directly uses Postgres features like `text[]` arrays and `jsonb` modules via Prisma.
- **Lens Interpretation:** Opaque canonical values (e.g., `padel`) are transformed into rich metadata (labels, icons, colors) using Lens configurations.
- **Query-Time Grouping:** Entity groupings (e.g., "Venues" vs "Coaches") are computed at query time or in the view layer, not stored in the database.

## Components

### Core Query Layer (`web/lib/lens-query.ts`)
The primary interface for lens-aware operations.
- **Facet Filtering:** Implements "OR within facet, AND across facets" logic.
- **Entity Transformation:** Maps raw entity data to `EntityView` objects with rich metadata.
- **Grouping Logic:** Computes derived groupings based on `entity_class` and `canonical_roles`.

### Prisma Query Utilities (`web/lib/entity-queries.ts`)
Encapsulates Prisma-specific query building using Postgres array filters.
- **`buildFacetedWhere`:** Translates high-level facet filters into Prisma `where` clauses using `hasSome`.
- **Predefined Queries:** Common query patterns like `padelVenues`, `sportsCentres`, and `coaches`.

### Helper Utilities
- **`web/lib/entity-helpers.ts`:** Provides type-safe wrappers (`ensureArray`, `ensureModules`) for handling Postgres-native types.
- **`web/lib/prisma.ts`:** Implements a singleton pattern for the Prisma Client.
- **`web/lib/utils.ts`:** Contains UI helpers for formatting attribute keys and values for display.

## Data Flow

1.  **Request:** A user interacts with the UI (e.g., selects a facet).
2.  **Query Building:** The application uses `buildFacetedWhere` (`web/lib/entity-queries.ts`) to create a Prisma query.
3.  **Database Execution:** Prisma executes a Postgres query using array operators (`&&` for `hasSome`).
4.  **Transformation:** Raw entities are passed through `transformEntityToView` (`web/lib/lens-query.ts`).
5.  **Lens Mapping:** The transformer looks up canonical values in the active Lens to add display labels, icons, and colors.
6.  **Rendering:** The rich `EntityView` is rendered by React components.

## Configuration Surface

The web subsystem is configured primarily through:
- **Environment Variables:** `.env` file for `DATABASE_URL`.
- **Lens Definitions:** YAML files (e.g., `lenses/edinburgh_finds/lens.yaml`) which control how data is interpreted and displayed.
- **Tailwind Config:** `tailwind.config.ts` for styling.

## Public Interfaces

### `EntityView`
The standard interface for entities in the UI layer.
```typescript
interface EntityView {
  id: string;
  entity_name: string;
  entity_class: string;
  activities: Array<{ key: string; label: string; icon?: string; color?: string }>;
  roles: Array<{ key: string; label: string }>;
  place_types: Array<{ key: string; label: string }>;
  access: Array<{ key: string; label: string }>;
  grouping?: string;
  [key: string]: any;
}
```

### `buildFacetedWhere`
Builds a Prisma `where` clause from facet selections.
```typescript
function buildFacetedWhere(filters: FacetFilters): Prisma.EntityWhereInput
```

## Examples

### Querying with Array Filters
Evidence: `web/lib/entity-queries.ts:74-95`
```typescript
// Example: Find sports centres offering padel or tennis
const where = buildFacetedWhere({
  activities: ["padel", "tennis"],
  place_types: ["sports_centre"],
  entity_class: "place"
});

const listings = await prisma.entity.findMany({ where });
```

### Transforming Raw Data to View
Evidence: `web/lib/lens-query.ts:251-344`
```typescript
// transformEntityToView maps "padel" -> { label: "Padel", icon: "racket-icon", ... }
const view = transformEntityToView(rawEntity, lens);
console.log(view.activities[0].label); // "Padel"
```

## Edge Cases / Notes
- **JSONB vs Arrays:** General attributes are stored in `attributes` (JSONB) and `discovered_attributes` (JSONB), while core dimensions are in `canonical_*` (text[]). The UI handles both types.
- **Missing Lens Data:** If a canonical value is not defined in the Lens, the UI falls back to displaying the raw key as the label.
- **Performance:** For large result sets, the transformation step (`transformEntityToView`) should be benchmarked as it performs lookups for every dimension value.
