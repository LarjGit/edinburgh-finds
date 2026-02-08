# Frontend Architecture

**Generated:** 2026-02-08
**Project:** Edinburgh Finds — Universal Entity Extraction Engine
**Framework:** Next.js 16 (App Router) + React 19

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Data Fetching](#data-fetching)
6. [Styling](#styling)
7. [Type Safety](#type-safety)
8. [Performance](#performance)
9. [Development](#development)
10. [Deployment](#deployment)
11. [Best Practices](#best-practices)
12. [Common Patterns](#common-patterns)

---

## Overview

The frontend is built with **Next.js 16** using the **App Router** architecture and **React 19**, providing a modern, high-performance web application for displaying entities extracted by the Universal Entity Extraction Engine.

### Key Characteristics

- **Server-First Architecture**: Leverages React Server Components for optimal performance
- **Type-Safe Data Access**: Direct Prisma integration with full TypeScript support
- **Lens-Aware Queries**: Native support for canonical dimension arrays and modules
- **Mobile-First Design**: Responsive layouts optimized for all screen sizes
- **Zero-Config Styling**: Tailwind CSS v4 with shadcn/ui components

### Technology Highlights

- **Next.js 16**: Latest App Router with enhanced performance and developer experience
- **React 19**: Server Components, improved Suspense, and better hydration
- **Prisma Client**: Type-safe database queries with auto-generated types
- **Tailwind CSS v4**: CSS-first configuration with inline theme system
- **TypeScript**: Strict mode enabled for maximum type safety

---

## Architecture

### App Router Structure

The frontend uses Next.js 16's **App Router** architecture, which provides:

1. **File-based routing** in the `app/` directory
2. **Automatic code splitting** at the route level
3. **Server Components by default** for optimal performance
4. **Built-in data fetching** with React Server Components
5. **Layout nesting** for shared UI components

```
web/app/
├── layout.tsx          # Root layout (fonts, global styles)
├── page.tsx            # Home page (Server Component)
└── globals.css         # Tailwind v4 configuration
```

### Server vs Client Components

The application follows a **Server-First** approach:

- **Server Components** (default): Data fetching, database queries, static content
- **Client Components** (marked with `"use client"`): Interactive UI, event handlers, client-side state

**Current Implementation:**
```typescript
// app/page.tsx - Server Component (default)
export default async function Home() {
  // Direct database access in Server Component
  const listings = await prisma.entity.findMany({
    take: 5,
    select: {
      id: true,
      entity_name: true,
      canonical_activities: true,
      // ... other fields
    },
  });

  return (
    <main>
      {/* Render listings */}
    </main>
  );
}
```

**Separation of Concerns:**

| Component Type | Use Cases | Examples |
|----------------|-----------|----------|
| **Server Components** | Database queries, data fetching, static rendering | Entity listings, detail pages, search results |
| **Client Components** | Interactive forms, dropdowns, modals, animations | Filters, search inputs, collapsible sections |

### Prisma Integration

The frontend uses **Prisma Client** for type-safe database access:

**Singleton Pattern (`lib/prisma.ts`):**
```typescript
import { PrismaClient } from '@prisma/client'

const prismaClientSingleton = () => {
  return new PrismaClient()
}

declare global {
  var prisma: undefined | ReturnType<typeof prismaClientSingleton>
}

const prisma = globalThis.prisma ?? prismaClientSingleton()

export default prisma

if (process.env.NODE_ENV !== 'production') globalThis.prisma = prisma
```

**Why this pattern?**
- Prevents multiple Prisma Client instances in development (hot reload issue)
- Ensures single connection pool in production
- Type-safe access to database models

---

## Tech Stack

### Core Framework

```json
{
  "next": "16.1.1",
  "react": "19.2.3",
  "react-dom": "19.2.3"
}
```

**Next.js 16 Features:**
- **Turbopack**: Faster local development with improved HMR
- **Enhanced App Router**: Better caching and revalidation
- **Partial Prerendering (PPR)**: Mix static and dynamic content seamlessly
- **Server Actions**: Type-safe server mutations

**React 19 Features:**
- **React Server Components**: Zero-bundle server-side rendering
- **Improved Suspense**: Better streaming and error boundaries
- **Actions**: Built-in form handling and mutations
- **use() Hook**: Async data reading in components

### Database & ORM

```json
{
  "@prisma/client": "^7.3.0",
  "prisma": "^7.3.0"
}
```

**Prisma 7.3 Capabilities:**
- Type-safe queries with auto-generated types
- Native support for PostgreSQL arrays (`TEXT[]`)
- JSONB support for `modules` and `discovered_attributes`
- Array filters: `has`, `hasSome`, `hasEvery`
- Transaction support and connection pooling

**Database Provider:** Supabase (PostgreSQL)

### Styling

```json
{
  "tailwindcss": "^4",
  "@tailwindcss/postcss": "^4",
  "tw-animate-css": "^1.4.0"
}
```

**Tailwind CSS v4 Changes:**
- **CSS-first configuration**: Theme defined in `globals.css` using `@theme`
- **Zero JavaScript config**: No `tailwind.config.js` needed
- **Better performance**: Faster builds and smaller CSS output
- **Native CSS features**: Uses modern CSS variables and `@import`

**shadcn/ui Components:**
```json
{
  "class-variance-authority": "^0.7.1",
  "clsx": "^2.1.1",
  "tailwind-merge": "^3.4.0",
  "lucide-react": "^0.562.0"
}
```

- **CVA**: Type-safe variant styling
- **clsx/tailwind-merge**: Conditional class merging
- **lucide-react**: Icon library (1000+ icons)

### TypeScript

```json
{
  "typescript": "^5"
}
```

**Configuration (`tsconfig.json`):**
```json
{
  "compilerOptions": {
    "target": "ES2017",
    "strict": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

- **Strict mode enabled**: Maximum type safety
- **Path aliases**: `@/` maps to project root
- **Next.js plugin**: Auto-types for App Router

---

## Project Structure

### Directory Layout

```mermaid
graph LR
    %% Frontend (Web) Module Dependencies
    subgraph Frontend["Frontend (Next.js)"]
        direction TB

        %% Core Directories
        App["app/<br/>(App Router)"]
        Lib["lib/<br/>(utilities)"]
        Components["components/<br/>(UI)"]
        LibTypes["lib/types/generated/"]

        %% Dependencies
        App --> Lib
        App --> Components
        Components --> Lib
        Lib --> LibTypes
    end

    %% External Dependencies
    subgraph External["External Packages"]
        direction TB

        %% Frontend External
        NextJS["Next.js 16<br/>(React 19)"]
        PrismaTS["Prisma Client<br/>TypeScript"]
        Tailwind["Tailwind CSS v4"]
        ShadcnUI["shadcn/ui<br/>(components)"]
    end

    %% Cross-Layer Dependencies
    subgraph Database["Database Layer"]
        PostgreSQL["PostgreSQL<br/>(Supabase)"]
        PrismaSchema["Prisma Schema<br/>(auto-generated)"]
    end

    %% Frontend to External
    App --> NextJS
    Components --> Tailwind
    Components --> ShadcnUI
    Lib --> PrismaTS

    %% Database Connections
    PrismaTS --> PostgreSQL
    PrismaSchema --> PostgreSQL

    %% Styling
    classDef frontendModule fill:#fff4e1,stroke:#ff8800,stroke-width:2px
    classDef externalPkg fill:#f0f0f0,stroke:#666,stroke-width:1px
    classDef dbLayer fill:#e8f5e9,stroke:#4caf50,stroke-width:2px

    class App,Lib,Components,LibTypes frontendModule
    class NextJS,PrismaTS,Tailwind,ShadcnUI externalPkg
    class PostgreSQL,PrismaSchema dbLayer
```

### File Organization

```
web/
├── app/                       # Next.js App Router
│   ├── layout.tsx            # Root layout (fonts, metadata)
│   ├── page.tsx              # Home page (entity listings)
│   └── globals.css           # Tailwind v4 config + theme
│
├── lib/                      # Shared utilities
│   ├── prisma.ts             # Prisma Client singleton
│   ├── entity-queries.ts     # Lens-aware query builders
│   ├── entity-helpers.ts     # Type coercion utilities
│   ├── utils.ts              # General utilities (cn, formatters)
│   ├── lens-query.ts         # Lens query resolution
│   └── types/                # Type definitions (future)
│       └── generated/        # Auto-generated from schema
│
├── components/               # React components (future)
│   └── ui/                   # shadcn/ui components
│
├── prisma/                   # Prisma schema
│   └── schema.prisma         # Auto-generated from YAML
│
├── public/                   # Static assets
│
├── package.json              # Dependencies
├── tsconfig.json             # TypeScript config
├── next.config.ts            # Next.js config
├── postcss.config.mjs        # PostCSS config (Tailwind)
└── eslint.config.mjs         # ESLint config
```

### Key Files

#### `app/layout.tsx` - Root Layout

```typescript
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Edinburgh Finds",
  description: "Discover places, people, and activities",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

**Purpose:**
- Defines HTML structure and metadata
- Loads font families (Geist Sans, Geist Mono)
- Wraps all pages with shared layout

#### `app/page.tsx` - Home Page

```typescript
import prisma from "@/lib/prisma";

export default async function Home() {
  // Server Component - direct database access
  const listings = await prisma.entity.findMany({
    take: 5,
    select: {
      id: true,
      entity_name: true,
      entity_class: true,
      canonical_activities: true,
      canonical_roles: true,
      modules: true,
    },
  });

  return (
    <main className="flex min-h-screen flex-col items-center p-24">
      <h1 className="text-4xl font-bold mb-8">Edinburgh Finds</h1>
      {/* Render listings */}
    </main>
  );
}
```

**Purpose:**
- Demonstrates Server Component data fetching
- Shows lens-aware entity rendering
- Example of Prisma Client usage

#### `lib/prisma.ts` - Database Client

See [Prisma Integration](#prisma-integration) section above.

#### `lib/entity-queries.ts` - Lens-Aware Queries

See [Data Fetching](#data-fetching) section below.

---

## Data Fetching

### Lens-Aware Prisma Queries

The frontend provides **lens-aware query utilities** that understand the Engine's canonical dimension system.

#### Faceted Filtering

**File:** `lib/entity-queries.ts`

```typescript
import { Prisma } from "@prisma/client";

export interface FacetFilters {
  activities?: string[];      // Canonical activities
  roles?: string[];           // Canonical roles
  place_types?: string[];     // Canonical place types
  access?: string[];          // Canonical access types
  entity_class?: string;      // Entity class (place/person/org/event/thing)
}

export function buildFacetedWhere(filters: FacetFilters): Prisma.EntityWhereInput {
  const where: Prisma.EntityWhereInput = {};
  const conditions: Prisma.EntityWhereInput[] = [];

  // Activity facet - OR within facet (hasSome)
  if (filters.activities && filters.activities.length > 0) {
    conditions.push({
      canonical_activities: {
        hasSome: filters.activities, // Entity has at least one of these activities
      },
    });
  }

  // Role facet - OR within facet (hasSome)
  if (filters.roles && filters.roles.length > 0) {
    conditions.push({
      canonical_roles: {
        hasSome: filters.roles,
      },
    });
  }

  // Place type facet - OR within facet (hasSome)
  if (filters.place_types && filters.place_types.length > 0) {
    conditions.push({
      canonical_place_types: {
        hasSome: filters.place_types,
      },
    });
  }

  // Access facet - OR within facet (hasSome)
  if (filters.access && filters.access.length > 0) {
    conditions.push({
      canonical_access: {
        hasSome: filters.access,
      },
    });
  }

  // Entity class - exact match
  if (filters.entity_class) {
    conditions.push({
      entity_class: filters.entity_class,
    });
  }

  // Combine all conditions with AND
  if (conditions.length > 0) {
    where.AND = conditions;
  }

  return where;
}
```

**Query Semantics:**
- **OR within facet**: Entity matches if it has ANY of the specified values
- **AND across facets**: Entity must match ALL specified facets

**Example:**
```typescript
buildFacetedWhere({
  activities: ["padel", "tennis"],  // Must have padel OR tennis
  place_types: ["sports_centre"]    // AND must be sports_centre
})
// Returns entities that are sports centres offering padel or tennis
```

#### Prisma Array Filters

Prisma 7.3 provides native PostgreSQL array filters:

| Filter | SQL Equivalent | Usage |
|--------|----------------|-------|
| `has` | `@>` | Array contains exact value |
| `hasSome` | `&&` | Array contains at least one value (OR) |
| `hasEvery` | `@>` | Array contains all values (AND) |

**Example Queries:**
```typescript
// Find all padel venues
const padelVenues = await prisma.entity.findMany({
  where: {
    canonical_activities: {
      has: "padel"
    },
    entity_class: "place"
  }
});

// Find venues offering padel OR tennis
const racquetVenues = await prisma.entity.findMany({
  where: {
    canonical_activities: {
      hasSome: ["padel", "tennis"]
    }
  }
});

// Find sports centres offering both padel AND tennis
const dualSportCentres = await prisma.entity.findMany({
  where: {
    canonical_activities: {
      hasEvery: ["padel", "tennis"]
    },
    canonical_place_types: {
      has: "sports_centre"
    }
  }
});
```

#### Query Helper Functions

**File:** `lib/entity-queries.ts`

```typescript
// Query entities by facets
export async function queryEntitiesByFacets(
  prisma: any,
  filters: FacetFilters,
  options?: {
    take?: number;
    skip?: number;
    orderBy?: Prisma.EntityOrderByWithRelationInput;
    select?: Prisma.EntitySelect;
  }
) {
  const where = buildFacetedWhere(filters);

  return prisma.entity.findMany({
    where,
    ...options,
  });
}

// Count entities by facets (for pagination)
export async function countEntitiesByFacets(
  prisma: any,
  filters: FacetFilters
): Promise<number> {
  const where = buildFacetedWhere(filters);

  return prisma.entity.count({
    where,
  });
}
```

**Usage:**
```typescript
import prisma from "@/lib/prisma";
import { queryEntitiesByFacets } from "@/lib/entity-queries";

const padelVenues = await queryEntitiesByFacets(prisma, {
  activities: ["padel"],
  entity_class: "place"
}, {
  take: 10,
  orderBy: { entity_name: 'asc' }
});
```

### Server Component Data Fetching

**Pattern:**
```typescript
export default async function EntityListingPage() {
  // Direct Prisma query in Server Component
  const entities = await prisma.entity.findMany({
    where: buildFacetedWhere({
      activities: ["padel"],
      entity_class: "place"
    }),
    select: {
      id: true,
      entity_name: true,
      summary: true,
      canonical_activities: true,
      modules: true,
      street_address: true,
      city: true,
    },
  });

  return (
    <div>
      {entities.map((entity) => (
        <EntityCard key={entity.id} entity={entity} />
      ))}
    </div>
  );
}
```

**Benefits:**
- Zero client-side JavaScript for data fetching
- No loading states needed (use Suspense for streaming)
- Type-safe queries with Prisma types
- Automatic request deduplication

### Dynamic Metadata

**Pattern:**
```typescript
import { Metadata } from 'next';

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const entity = await prisma.entity.findUnique({
    where: { slug: params.slug },
  });

  return {
    title: entity?.entity_name || 'Entity Not Found',
    description: entity?.summary || 'Entity details',
    openGraph: {
      title: entity?.entity_name,
      description: entity?.summary,
      images: entity?.mainImage ? [entity.mainImage] : [],
    },
  };
}

export default async function EntityDetailPage({
  params,
}: {
  params: { slug: string };
}) {
  const entity = await prisma.entity.findUnique({
    where: { slug: params.slug },
  });

  if (!entity) {
    return <div>Entity not found</div>;
  }

  return <EntityDetail entity={entity} />;
}
```

**Features:**
- SEO-optimized metadata per page
- Dynamic Open Graph tags
- Automatic meta tag generation

### Incremental Static Regeneration (ISR)

**Pattern:**
```typescript
export const revalidate = 3600; // Revalidate every hour

export default async function EntityListingPage() {
  const entities = await prisma.entity.findMany();

  return <div>{/* Render entities */}</div>;
}
```

**Benefits:**
- Static generation with periodic updates
- Best of static and dynamic: speed + freshness
- Configurable revalidation intervals

---

## Styling

### Tailwind CSS v4

The application uses **Tailwind CSS v4** with a CSS-first configuration approach.

#### Configuration

**File:** `app/globals.css`

```css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
  /* ... more theme tokens */
}

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.6 0.118 184.704);
  /* ... more color definitions */
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  /* ... dark mode colors */
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

**Key Features:**
- **No JavaScript config**: Everything in CSS
- **OKLCH color space**: Better color interpolation and accessibility
- **CSS custom properties**: Native browser support
- **Dark mode**: Automatic via `.dark` class

#### Theme System

**Design Tokens:**
```css
/* Light mode */
:root {
  --background: oklch(1 0 0);           /* White */
  --foreground: oklch(0.145 0 0);       /* Near-black */
  --primary: oklch(0.6 0.118 184.704);  /* Blue */
  --secondary: oklch(0.97 0 0);         /* Light gray */
  --muted: oklch(0.97 0 0);             /* Light gray */
  --accent: oklch(0.97 0 0);            /* Light gray */
  --destructive: oklch(0.577 0.245 27.325); /* Red */
  --border: oklch(0.922 0 0);           /* Gray */
}

/* Dark mode */
.dark {
  --background: oklch(0.145 0 0);       /* Near-black */
  --foreground: oklch(0.985 0 0);       /* Near-white */
  --primary: oklch(0.704 0.14 182.503); /* Brighter blue */
  /* ... inverted colors */
}
```

**Usage:**
```typescript
<div className="bg-background text-foreground">
  <h1 className="text-primary">Heading</h1>
  <p className="text-muted-foreground">Description</p>
  <button className="bg-primary text-primary-foreground">
    Click me
  </button>
</div>
```

#### shadcn/ui Integration

**Utility Function (`lib/utils.ts`):**
```typescript
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

**Purpose:**
- Merge Tailwind classes intelligently
- Handle conditional classes
- Prevent class conflicts

**Example:**
```typescript
<div className={cn(
  "px-4 py-2 rounded-lg",
  isActive && "bg-primary text-primary-foreground",
  isDisabled && "opacity-50 cursor-not-allowed"
)}>
  Content
</div>
```

#### Responsive Design

**Mobile-First Approach:**
```typescript
<div className="
  w-full              /* Mobile: Full width */
  md:w-1/2            /* Tablet: Half width */
  lg:w-1/3            /* Desktop: Third width */
  px-4                /* Mobile: 1rem padding */
  md:px-6             /* Tablet: 1.5rem padding */
  lg:px-8             /* Desktop: 2rem padding */
">
  Content
</div>
```

**Breakpoints:**
| Breakpoint | Min Width | Device |
|------------|-----------|--------|
| `sm` | 640px | Small tablets |
| `md` | 768px | Tablets |
| `lg` | 1024px | Laptops |
| `xl` | 1280px | Desktops |
| `2xl` | 1536px | Large desktops |

#### Content & Voice Guidelines

**From CLAUDE.md:**

> **Tone:** "The Knowledgeable Local Friend"
> - Warm, helpful, authoritative - never generic AI-sounding
> - **Prohibited phrases:** "Located at," "Features include," "A great place for," "Welcome to"
> - **Required style:** Contextual bridges like "Just a short walk from [Landmark]" or "Perfect for those who prefer [Specific Need]"
> - Utility over hype: If expensive, say "Premium-priced". If basic, say "Functional and focused"

**Design Philosophy:** "The Sophisticated Canvas"
- **Agnostic elegance**: No vertical tropes (no "neon green for Padel")
- **Premium neutral aesthetic**: shadcn/ui "neutral" base
- **Transform raw data**: Convert opening hours, specs into visual components (tags, icons) not text blocks

**Example:**
```typescript
// ❌ Generic AI writing
<p>Located at 123 Main Street. Features include parking and WiFi. A great place for families.</p>

// ✅ Contextual, utility-focused
<p>Just a two-minute walk from Waverley Station. Parking available on-site. Premium-priced with reliable WiFi throughout.</p>
```

---

## Type Safety

### Prisma-Generated Types

Prisma automatically generates TypeScript types from the database schema.

**Auto-Generated Types:**
```typescript
// From @prisma/client
import { Entity, Prisma } from '@prisma/client';

// Entity type (full model)
type EntityType = Entity;

// Partial selection types
type EntityWithName = Prisma.EntityGetPayload<{
  select: { id: true; entity_name: true }
}>;

// Where clause types
type EntityWhereInput = Prisma.EntityWhereInput;

// OrderBy types
type EntityOrderByInput = Prisma.EntityOrderByWithRelationInput;
```

**Usage:**
```typescript
import { Entity, Prisma } from '@prisma/client';

async function getEntities(
  where: Prisma.EntityWhereInput,
  orderBy?: Prisma.EntityOrderByWithRelationInput
): Promise<Entity[]> {
  return prisma.entity.findMany({
    where,
    orderBy,
  });
}
```

### TypeScript Strict Mode

**Configuration (`tsconfig.json`):**
```json
{
  "compilerOptions": {
    "strict": true,
    "noEmit": true,
    "target": "ES2017",
    "jsx": "react-jsx"
  }
}
```

**Enabled Checks:**
- `noImplicitAny`: All types must be explicit
- `strictNullChecks`: Null/undefined must be handled
- `strictFunctionTypes`: Function types checked strictly
- `strictBindCallApply`: Bind/call/apply checked
- `strictPropertyInitialization`: Class properties initialized

### Type Helpers

**File:** `lib/entity-helpers.ts`

```typescript
/**
 * Helper to ensure we have an array for dimension fields.
 * Defensive coding for canonical dimensions.
 */
export function ensureArray(val: string[] | null | undefined): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  return [];
}

/**
 * Helper to ensure we have an object for module fields.
 * Defensive coding for JSONB modules.
 */
export function ensureModules(val: Record<string, any> | null | undefined): Record<string, any> {
  if (!val) return {};
  if (typeof val === "object") return val;
  return {};
}

export function parseDimensionArray(val: string[] | null | undefined): string[] {
  return ensureArray(val);
}

export function parseModules(val: Record<string, any> | null | undefined): Record<string, any> {
  return ensureModules(val);
}
```

**Purpose:**
- Defensive type coercion for database fields
- Handle null/undefined gracefully
- Ensure correct types for rendering

**Usage:**
```typescript
import { parseDimensionArray, parseModules } from '@/lib/entity-helpers';

export default async function EntityCard({ entity }: { entity: Entity }) {
  const activities = parseDimensionArray(entity.canonical_activities);
  const modules = parseModules(entity.modules);

  return (
    <div>
      {activities.length > 0 && (
        <div>Activities: {activities.join(', ')}</div>
      )}
    </div>
  );
}
```

### Zod Validation (Future)

**Planned Integration:**
```typescript
import { z } from 'zod';

const EntityFilterSchema = z.object({
  activities: z.array(z.string()).optional(),
  roles: z.array(z.string()).optional(),
  entity_class: z.string().optional(),
});

type EntityFilter = z.infer<typeof EntityFilterSchema>;

export async function searchEntities(filter: EntityFilter) {
  // Runtime validation
  const validated = EntityFilterSchema.parse(filter);

  // Type-safe query
  return queryEntitiesByFacets(prisma, validated);
}
```

---

## Performance

### Core Web Vitals Targets

| Metric | Target | Current | Strategy |
|--------|--------|---------|----------|
| **LCP** (Largest Contentful Paint) | < 2.5s | TBD | Server Components, Image optimization |
| **FID** (First Input Delay) | < 100ms | TBD | Minimal client JS, Server Actions |
| **CLS** (Cumulative Layout Shift) | < 0.1 | TBD | Fixed dimensions, font preloading |
| **TTFB** (Time to First Byte) | < 600ms | TBD | Edge functions, database connection pooling |

### Optimization Strategies

#### 1. Server Components

**Default to Server Components:**
```typescript
// ✅ Server Component (default)
export default async function EntityList() {
  const entities = await prisma.entity.findMany();
  return <div>{/* Render */}</div>;
}

// ❌ Client Component (only when needed)
"use client"
export default function InteractiveFilter() {
  const [filter, setFilter] = useState({});
  return <div>{/* Interactive UI */}</div>;
}
```

**Benefits:**
- Zero JavaScript for static content
- Faster initial page load
- Better SEO (content in HTML)
- Reduced bundle size

#### 2. Image Optimization

**Next.js Image Component:**
```typescript
import Image from 'next/image';

export function EntityImage({ entity }: { entity: Entity }) {
  if (!entity.mainImage) return null;

  return (
    <Image
      src={entity.mainImage}
      alt={entity.entity_name}
      width={800}
      height={600}
      loading="lazy"
      placeholder="blur"
      blurDataURL="/placeholder.jpg"
    />
  );
}
```

**Automatic Optimizations:**
- WebP/AVIF format conversion
- Responsive images (srcset)
- Lazy loading
- Blur placeholder

#### 3. Code Splitting

**Automatic Route-Level Splitting:**
```
app/
├── page.tsx          → /          (chunk-home.js)
├── about/
│   └── page.tsx      → /about     (chunk-about.js)
└── entities/
    └── [slug]/
        └── page.tsx  → /entities/:slug (chunk-entity.js)
```

**Dynamic Imports:**
```typescript
import dynamic from 'next/dynamic';

const InteractiveMap = dynamic(() => import('@/components/InteractiveMap'), {
  loading: () => <p>Loading map...</p>,
  ssr: false, // Disable server-side rendering for this component
});

export default function EntityDetail({ entity }: { entity: Entity }) {
  return (
    <div>
      <h1>{entity.entity_name}</h1>
      <InteractiveMap coordinates={[entity.latitude, entity.longitude]} />
    </div>
  );
}
```

#### 4. Database Query Optimization

**Select Only Needed Fields:**
```typescript
// ❌ Fetching all fields
const entities = await prisma.entity.findMany();

// ✅ Select only needed fields
const entities = await prisma.entity.findMany({
  select: {
    id: true,
    entity_name: true,
    summary: true,
    canonical_activities: true,
  },
});
```

**Use Indexes:**
```prisma
model Entity {
  id           String   @id @default(cuid())
  entity_name  String
  entity_class String
  canonical_activities String[] @default([])

  @@index([entity_name])        // Text search
  @@index([entity_class])        // Filtering
  @@index([canonical_activities]) // Array filtering (GIN index)
}
```

**Pagination:**
```typescript
const ENTITIES_PER_PAGE = 20;

export async function getEntitiesPaginated(page: number = 1) {
  const [entities, total] = await Promise.all([
    prisma.entity.findMany({
      skip: (page - 1) * ENTITIES_PER_PAGE,
      take: ENTITIES_PER_PAGE,
      orderBy: { entity_name: 'asc' },
    }),
    prisma.entity.count(),
  ]);

  return {
    entities,
    total,
    pages: Math.ceil(total / ENTITIES_PER_PAGE),
    currentPage: page,
  };
}
```

#### 5. Caching Strategies

**Static Generation:**
```typescript
export default async function StaticEntityList() {
  const entities = await prisma.entity.findMany();
  return <div>{/* Render */}</div>;
}

// Regenerate at build time (static)
```

**Incremental Static Regeneration:**
```typescript
export const revalidate = 3600; // 1 hour

export default async function ISREntityList() {
  const entities = await prisma.entity.findMany();
  return <div>{/* Render */}</div>;
}

// Regenerate every hour (ISR)
```

**Dynamic Rendering:**
```typescript
export const dynamic = 'force-dynamic';

export default async function DynamicEntityList() {
  const entities = await prisma.entity.findMany();
  return <div>{/* Render */}</div>;
}

// Regenerate on every request (SSR)
```

#### 6. Font Optimization

**Font Preloading (`app/layout.tsx`):**
```typescript
import { Geist, Geist_Mono } from "next/font/google";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap", // Prevent invisible text during font load
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});
```

**Benefits:**
- Automatic font subsetting
- Self-hosted fonts (no Google Fonts request)
- CSS variable injection
- Zero layout shift

---

## Development

### Setup

**Prerequisites:**
- Node.js 20+ (for React 19 compatibility)
- npm or pnpm
- PostgreSQL database (Supabase)

**Installation:**
```bash
cd web
npm install
```

**Environment Variables:**
```bash
# web/.env
DATABASE_URL="postgresql://user:password@host:5432/database?schema=public"
```

### Development Server

**Start development server:**
```bash
npm run dev
```

**Output:**
```
  ▲ Next.js 16.1.1
  - Local:        http://localhost:3000
  - Network:      http://192.168.1.X:3000

 ✓ Ready in 1.2s
```

**Features:**
- **Hot Module Replacement (HMR)**: Instant updates without full reload
- **Fast Refresh**: Preserves component state during edits
- **Error overlay**: Detailed error messages in browser
- **Turbopack**: Faster builds than Webpack

### Database Workflow

**Generate Prisma Client:**
```bash
npx prisma generate
```

**Sync schema to database (development):**
```bash
npx prisma db push
```

**Create migration (production):**
```bash
npx prisma migrate dev --name add_new_field
```

**Open Prisma Studio (database GUI):**
```bash
npx prisma studio
```

### Linting

**Run ESLint:**
```bash
npm run lint
```

**Auto-fix issues:**
```bash
npm run lint -- --fix
```

**Configuration (`eslint.config.mjs`):**
```javascript
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
```

**Rules:**
- Next.js Core Web Vitals rules
- TypeScript strict checks
- React 19 rules (hooks, components)

### Testing

**Current Status:** No test framework configured yet.

**Recommended Setup:**
```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom jest jest-environment-jsdom
```

**Future Test Structure:**
```
web/
├── __tests__/
│   ├── components/
│   │   └── EntityCard.test.tsx
│   ├── lib/
│   │   └── entity-queries.test.ts
│   └── app/
│       └── page.test.tsx
```

**Example Test:**
```typescript
import { render, screen } from '@testing-library/react';
import { buildFacetedWhere } from '@/lib/entity-queries';

describe('buildFacetedWhere', () => {
  it('builds correct where clause for activities', () => {
    const where = buildFacetedWhere({
      activities: ['padel', 'tennis'],
    });

    expect(where.AND).toContainEqual({
      canonical_activities: {
        hasSome: ['padel', 'tennis'],
      },
    });
  });
});
```

---

## Deployment

### Vercel (Recommended)

**Why Vercel:**
- Built by Next.js creators
- Zero-config deployment
- Edge Network (global CDN)
- Automatic HTTPS
- Preview deployments for PRs

**Deployment Steps:**

1. **Connect GitHub repository:**
   ```bash
   # Install Vercel CLI
   npm install -g vercel

   # Login
   vercel login

   # Deploy
   vercel
   ```

2. **Configure environment variables:**
   - Go to Vercel dashboard > Project > Settings > Environment Variables
   - Add `DATABASE_URL` with Supabase connection string

3. **Auto-deploy on push:**
   - Main branch → Production
   - Feature branches → Preview deployments

**Automatic Optimizations:**
- Image optimization (automatic WebP/AVIF)
- Edge caching
- Compression (Brotli)
- Analytics (optional)

### Self-Hosted

**Build for production:**
```bash
npm run build
```

**Start production server:**
```bash
npm start
```

**Docker deployment:**
```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["npm", "start"]
```

**Build and run:**
```bash
docker build -t edinburgh-finds-web .
docker run -p 3000:3000 -e DATABASE_URL="..." edinburgh-finds-web
```

### Environment Variables

**Required:**
```bash
DATABASE_URL="postgresql://..."
```

**Optional:**
```bash
# Analytics
NEXT_PUBLIC_ANALYTICS_ID="..."

# Error tracking
SENTRY_DSN="..."

# Feature flags
NEXT_PUBLIC_ENABLE_SEARCH="true"
```

**Security:**
- Never commit `.env` files
- Use Vercel's environment variable system
- Separate dev/staging/production environments

---

## Best Practices

### 1. Server Components First

**Default to Server Components:**
```typescript
// ✅ Server Component (default)
export default async function EntityPage() {
  const entities = await prisma.entity.findMany();
  return <div>{/* Render */}</div>;
}
```

**Use Client Components only when:**
- Need interactivity (onClick, onChange)
- Need browser APIs (localStorage, geolocation)
- Need React hooks (useState, useEffect)

### 2. Type Safety

**Always type component props:**
```typescript
// ✅ Typed props
interface EntityCardProps {
  entity: Entity;
  onSelect?: (id: string) => void;
}

export function EntityCard({ entity, onSelect }: EntityCardProps) {
  return <div>{/* Render */}</div>;
}

// ❌ Untyped props
export function EntityCard({ entity, onSelect }: any) {
  return <div>{/* Render */}</div>;
}
```

### 3. Error Handling

**Use Error Boundaries:**
```typescript
// app/error.tsx
'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={() => reset()}>Try again</button>
    </div>
  )
}
```

**Handle not found:**
```typescript
// app/entities/[slug]/not-found.tsx
export default function NotFound() {
  return (
    <div>
      <h2>Entity Not Found</h2>
      <p>The entity you're looking for doesn't exist.</p>
    </div>
  )
}

// app/entities/[slug]/page.tsx
import { notFound } from 'next/navigation';

export default async function EntityDetailPage({ params }: { params: { slug: string } }) {
  const entity = await prisma.entity.findUnique({
    where: { slug: params.slug },
  });

  if (!entity) {
    notFound();
  }

  return <EntityDetail entity={entity} />;
}
```

### 4. Accessibility

**Semantic HTML:**
```typescript
// ✅ Semantic
<main>
  <h1>Entities</h1>
  <nav aria-label="Entity filters">
    <button>Filter</button>
  </nav>
  <ul>
    {entities.map(e => <li key={e.id}>{e.entity_name}</li>)}
  </ul>
</main>

// ❌ Non-semantic
<div>
  <div className="title">Entities</div>
  <div>
    <div onClick={filter}>Filter</div>
  </div>
  <div>
    {entities.map(e => <div key={e.id}>{e.entity_name}</div>)}
  </div>
</div>
```

**ARIA attributes:**
```typescript
<button
  aria-label="Close modal"
  aria-expanded={isOpen}
  aria-controls="modal-content"
>
  X
</button>
```

**Keyboard navigation:**
```typescript
<div
  tabIndex={0}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleSelect();
    }
  }}
>
  Clickable content
</div>
```

### 5. Performance

**Optimize images:**
```typescript
import Image from 'next/image';

<Image
  src={entity.mainImage}
  alt={entity.entity_name}
  width={800}
  height={600}
  loading="lazy"
  placeholder="blur"
/>
```

**Minimize client JS:**
```typescript
// ✅ Server Component (no JS)
export default async function EntityList() {
  const entities = await prisma.entity.findMany();
  return <div>{/* Static list */}</div>;
}

// ❌ Client Component (sends JS to browser)
"use client"
export default function EntityList() {
  const [entities, setEntities] = useState([]);
  useEffect(() => { fetch('/api/entities').then(setEntities) }, []);
  return <div>{/* Interactive list */}</div>;
}
```

**Use Suspense for streaming:**
```typescript
import { Suspense } from 'react';

export default function EntityPage() {
  return (
    <div>
      <h1>Entities</h1>
      <Suspense fallback={<div>Loading...</div>}>
        <EntityList />
      </Suspense>
    </div>
  );
}

async function EntityList() {
  const entities = await prisma.entity.findMany();
  return <ul>{/* Render */}</ul>;
}
```

### 6. SEO

**Dynamic metadata:**
```typescript
export async function generateMetadata({ params }: { params: { slug: string } }) {
  const entity = await prisma.entity.findUnique({ where: { slug: params.slug } });

  return {
    title: entity?.entity_name,
    description: entity?.summary,
    openGraph: {
      title: entity?.entity_name,
      description: entity?.summary,
      images: [entity?.mainImage],
    },
  };
}
```

**Structured data:**
```typescript
export default async function EntityDetailPage({ params }: { params: { slug: string } }) {
  const entity = await prisma.entity.findUnique({ where: { slug: params.slug } });

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Place",
    "name": entity.entity_name,
    "description": entity.summary,
    "address": {
      "@type": "PostalAddress",
      "streetAddress": entity.street_address,
      "addressLocality": entity.city,
      "postalCode": entity.postcode,
    },
  };

  return (
    <div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      {/* Entity detail */}
    </div>
  );
}
```

---

## Common Patterns

### Entity Rendering

**Entity Card Component:**
```typescript
import { Entity } from '@prisma/client';
import { parseDimensionArray, parseModules } from '@/lib/entity-helpers';

interface EntityCardProps {
  entity: Entity;
}

export function EntityCard({ entity }: EntityCardProps) {
  const activities = parseDimensionArray(entity.canonical_activities);
  const roles = parseDimensionArray(entity.canonical_roles);
  const modules = parseModules(entity.modules);

  return (
    <div className="p-6 border border-zinc-200 rounded-lg shadow-sm bg-white">
      <div className="flex justify-between items-start">
        <h3 className="text-xl font-bold">{entity.entity_name}</h3>
        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full">
          {entity.entity_class}
        </span>
      </div>

      {entity.summary && (
        <p className="mt-2 text-zinc-600">{entity.summary}</p>
      )}

      {/* Canonical Dimensions */}
      {activities.length > 0 && (
        <div className="mt-4">
          <span className="text-sm text-zinc-500">Activities:</span>{' '}
          <span className="text-sm text-zinc-700">{activities.join(', ')}</span>
        </div>
      )}

      {roles.length > 0 && (
        <div className="mt-2">
          <span className="text-sm text-zinc-500">Roles:</span>{' '}
          <span className="text-sm text-zinc-700">{roles.join(', ')}</span>
        </div>
      )}

      {/* Modules */}
      {Object.keys(modules).length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-semibold">Modules</h4>
          {Object.entries(modules).map(([name, data]) => (
            <div key={name} className="text-sm">
              <span className="text-zinc-500">{name}:</span>{' '}
              <span className="text-zinc-700">{JSON.stringify(data)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Location */}
      {entity.street_address && (
        <div className="mt-4 text-sm text-zinc-500">
          {entity.street_address}, {entity.city} {entity.postcode}
        </div>
      )}
    </div>
  );
}
```

### Faceted Search UI

**Filter Component (Client):**
```typescript
"use client"

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function EntityFilters() {
  const router = useRouter();
  const [filters, setFilters] = useState({
    activities: [] as string[],
    entity_class: '',
  });

  const handleFilterChange = (facet: string, value: string) => {
    if (facet === 'activities') {
      setFilters(prev => ({
        ...prev,
        activities: prev.activities.includes(value)
          ? prev.activities.filter(a => a !== value)
          : [...prev.activities, value]
      }));
    } else {
      setFilters(prev => ({ ...prev, [facet]: value }));
    }
  };

  const applyFilters = () => {
    const params = new URLSearchParams();
    if (filters.activities.length > 0) {
      params.set('activities', filters.activities.join(','));
    }
    if (filters.entity_class) {
      params.set('entity_class', filters.entity_class);
    }

    router.push(`/entities?${params.toString()}`);
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold mb-2">Activities</h3>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.activities.includes('padel')}
            onChange={() => handleFilterChange('activities', 'padel')}
          />
          Padel
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.activities.includes('tennis')}
            onChange={() => handleFilterChange('activities', 'tennis')}
          />
          Tennis
        </label>
      </div>

      <div>
        <h3 className="font-semibold mb-2">Entity Class</h3>
        <select
          value={filters.entity_class}
          onChange={(e) => handleFilterChange('entity_class', e.target.value)}
          className="border rounded px-2 py-1"
        >
          <option value="">All</option>
          <option value="place">Places</option>
          <option value="person">People</option>
          <option value="organization">Organizations</option>
        </select>
      </div>

      <button
        onClick={applyFilters}
        className="px-4 py-2 bg-primary text-primary-foreground rounded"
      >
        Apply Filters
      </button>
    </div>
  );
}
```

**Search Results Page (Server):**
```typescript
import { queryEntitiesByFacets } from '@/lib/entity-queries';
import { EntityCard } from '@/components/EntityCard';
import { EntityFilters } from '@/components/EntityFilters';

export default async function EntitySearchPage({
  searchParams,
}: {
  searchParams: { activities?: string; entity_class?: string };
}) {
  const filters = {
    activities: searchParams.activities?.split(','),
    entity_class: searchParams.entity_class,
  };

  const entities = await queryEntitiesByFacets(prisma, filters, {
    take: 20,
    orderBy: { entity_name: 'asc' },
  });

  return (
    <div className="flex gap-8">
      <aside className="w-64">
        <EntityFilters />
      </aside>

      <main className="flex-1">
        <h1 className="text-3xl font-bold mb-6">Search Results</h1>
        {entities.length === 0 ? (
          <p>No entities found.</p>
        ) : (
          <div className="space-y-4">
            {entities.map(entity => (
              <EntityCard key={entity.id} entity={entity} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
```

### Loading States

**Suspense Boundaries:**
```typescript
import { Suspense } from 'react';

export default function EntityPage() {
  return (
    <div>
      <h1>Entities</h1>
      <Suspense fallback={<EntityListSkeleton />}>
        <EntityList />
      </Suspense>
    </div>
  );
}

function EntityListSkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="h-6 bg-zinc-200 rounded w-1/3 mb-2"></div>
          <div className="h-4 bg-zinc-100 rounded w-full"></div>
        </div>
      ))}
    </div>
  );
}

async function EntityList() {
  const entities = await prisma.entity.findMany();
  return (
    <div className="space-y-4">
      {entities.map(entity => (
        <EntityCard key={entity.id} entity={entity} />
      ))}
    </div>
  );
}
```

### Pagination

**Server-Side Pagination:**
```typescript
import { queryEntitiesByFacets, countEntitiesByFacets } from '@/lib/entity-queries';

const ENTITIES_PER_PAGE = 20;

export default async function PaginatedEntityList({
  searchParams,
}: {
  searchParams: { page?: string };
}) {
  const page = parseInt(searchParams.page || '1');

  const filters = { entity_class: 'place' };

  const [entities, total] = await Promise.all([
    queryEntitiesByFacets(prisma, filters, {
      skip: (page - 1) * ENTITIES_PER_PAGE,
      take: ENTITIES_PER_PAGE,
    }),
    countEntitiesByFacets(prisma, filters),
  ]);

  const totalPages = Math.ceil(total / ENTITIES_PER_PAGE);

  return (
    <div>
      <div className="space-y-4">
        {entities.map(entity => (
          <EntityCard key={entity.id} entity={entity} />
        ))}
      </div>

      <div className="flex gap-2 mt-6">
        {page > 1 && (
          <a href={`?page=${page - 1}`} className="px-4 py-2 border rounded">
            Previous
          </a>
        )}
        <span className="px-4 py-2">
          Page {page} of {totalPages}
        </span>
        {page < totalPages && (
          <a href={`?page=${page + 1}`} className="px-4 py-2 border rounded">
            Next
          </a>
        )}
      </div>
    </div>
  );
}
```

---

## Summary

The Universal Entity Extraction Engine frontend is built with **Next.js 16** and **React 19**, leveraging the latest Server Components architecture for optimal performance and developer experience.

### Key Takeaways

1. **Server-First Architecture**: Default to Server Components, use Client Components only when needed
2. **Type-Safe Data Access**: Prisma Client provides full TypeScript support with auto-generated types
3. **Lens-Aware Queries**: Native support for canonical dimensions and modules via Prisma array filters
4. **Modern Styling**: Tailwind CSS v4 with CSS-first configuration and shadcn/ui components
5. **Performance Optimized**: Code splitting, image optimization, ISR, and minimal client JavaScript
6. **Production Ready**: Vercel deployment with automatic optimizations and edge caching

### Architecture Principles

- **Engine Purity**: Frontend respects the Engine vs Lens boundary
- **Vertical Agnostic**: Works with any vertical via canonical dimensions
- **Type Safety**: Strict TypeScript mode with Prisma-generated types
- **Performance First**: Server Components, code splitting, image optimization
- **Mobile First**: Responsive design with Tailwind breakpoints

### Next Steps

1. Add dynamic routes: `/entities/[slug]` for entity detail pages
2. Implement search functionality with full-text search
3. Add interactive components: filters, dropdowns, modals
4. Integrate shadcn/ui components for consistent design
5. Set up testing framework (React Testing Library + Jest)
6. Add analytics and error tracking (Vercel Analytics, Sentry)
7. Optimize for Core Web Vitals (LCP < 2.5s, FID < 100ms, CLS < 0.1)

---

**Generated:** 2026-02-08
**Target:** `docs/generated/FRONTEND.md`
**Lines:** 1,366
