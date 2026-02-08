# Frontend Architecture

> **Last Updated:** 2026-02-08
> **Generated from source analysis**
> **Target:** Next.js 16 App Router with React 19

---

## Overview

The frontend is built on Next.js 16 (App Router) with React 19, TypeScript, and Tailwind CSS v4. It follows a **lens-aware architecture** where the UI consumes universal entity data interpreted through vertical-specific lenses. The frontend is strictly vertical-agnostic at the framework level—all domain semantics are injected via lens contracts, enabling horizontal scaling to new verticals without code changes.

**Core Philosophy:**
- **Engine-Lens Separation:** UI operates on universal entity primitives (`entity_class`, `canonical_*` dimensions, `modules`)
- **Data-Driven Presentation:** Lens contracts provide display metadata (labels, icons, colors) for opaque canonical values
- **Agnostic Elegance:** Design system avoids vertical tropes (e.g., no "neon green for Padel"); uses sophisticated neutral aesthetics
- **Mobile-First:** Touch-optimized (44x44px minimum), progressive enhancement for desktop

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Framework** | Next.js | 16.1.1 | App Router, React Server Components, streaming SSR |
| **UI Library** | React | 19.2.3 | Concurrent features, automatic batching, transitions |
| **Language** | TypeScript | 5.x | Type safety, generated types from Prisma schema |
| **Styling** | Tailwind CSS | v4 | Utility-first, custom `@theme` variables, dark mode |
| **Components** | shadcn/ui | Latest | Accessible, customizable primitives (neutral base) |
| **ORM** | Prisma Client | 7.3.0 | Type-safe database queries, auto-generated types |
| **Utilities** | clsx + tailwind-merge | Latest | Conditional classNames, conflict resolution |
| **Icons** | Lucide React | 0.562.0 | Consistent iconography |

---

## Project Structure

```
web/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout (fonts, metadata)
│   ├── page.tsx                  # Homepage (entity listing)
│   └── globals.css               # Tailwind v4 config + theme variables
├── lib/                          # Shared utilities
│   ├── prisma.ts                 # Prisma client singleton
│   ├── utils.ts                  # cn(), parseAttributesJSON(), formatters
│   ├── entity-helpers.ts         # Array/module type guards
│   ├── entity-queries.ts         # Faceted query builder (Prisma array filters)
│   └── lens-query.ts             # Lens-aware transformation layer
├── components/                   # React components (currently none—scaffolding phase)
├── prisma/
│   └── schema.prisma             # Auto-generated from engine/config/schemas/*.yaml
├── package.json                  # Dependencies, scripts
└── tsconfig.json                 # TypeScript configuration
```

**Key Characteristics:**
- **Minimal component library:** Current implementation uses inline JSX in `page.tsx`; component extraction pending
- **Server-first rendering:** Leverages React Server Components for data fetching
- **Auto-generated schemas:** Prisma schema regenerated via `python -m engine.schema.generate`

---

## Architecture Patterns

### 1. Next.js App Router Structure

**File-Based Routing:**
```
app/
├── layout.tsx        → Root layout (applies to all routes)
├── page.tsx          → Route handler for /
├── [slug]/page.tsx   → Dynamic route for /[slug] (future)
└── api/              → API routes (future)
```

**Key Patterns:**
- **Server Components by Default:** All components are React Server Components unless marked with `"use client"`
- **Streaming SSR:** Use `<Suspense>` boundaries for progressive loading
- **Metadata API:** Dynamic metadata in `layout.tsx` or `page.tsx` exports

**Example (Root Layout):**
```typescript
// app/layout.tsx
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Edinburgh Finds",
  description: "Universal entity discovery platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

---

### 2. Data Fetching with Prisma

**Prisma Client Singleton:**
```typescript
// lib/prisma.ts
import { PrismaClient } from '@prisma/client';

const prismaClientSingleton = () => new PrismaClient();

declare global {
  var prisma: undefined | ReturnType<typeof prismaClientSingleton>;
}

const prisma = globalThis.prisma ?? prismaClientSingleton();

export default prisma;

if (process.env.NODE_ENV !== 'production') globalThis.prisma = prisma;
```

**Usage in Server Components:**
```typescript
// app/page.tsx
import prisma from "@/lib/prisma";

export default async function Home() {
  const entities = await prisma.entity.findMany({
    where: { entity_class: "place" },
    take: 10,
  });

  return <EntityList entities={entities} />;
}
```

**Key Points:**
- Server Components fetch data directly (no API route needed)
- Prisma client auto-reused in development via `globalThis`
- Type-safe queries with auto-generated types from `schema.prisma`

---

### 3. Lens-Aware Query Layer

**Universal Entity Model:**
```typescript
// Prisma schema (auto-generated)
model Entity {
  id                    String   @id @default(cuid())
  entity_name           String
  entity_class          String   // place, person, organization, event, thing
  canonical_activities  String[] @default([])  // Opaque arrays
  canonical_roles       String[] @default([])
  canonical_place_types String[] @default([])
  canonical_access      String[] @default([])
  modules               Json                   // Namespaced vertical data
  // ... location, contact primitives
}
```

**Faceted Query Builder (`lib/entity-queries.ts`):**
```typescript
import { buildFacetedWhere, FacetFilters } from "@/lib/entity-queries";

// Semantic: OR within facet, AND across facets
const where = buildFacetedWhere({
  activities: ["padel", "tennis"],       // Has padel OR tennis
  place_types: ["sports_centre"],        // AND is sports_centre
  entity_class: "place",
});

const results = await prisma.entity.findMany({ where });
```

**Prisma Array Filters (Postgres-native):**
| Prisma Filter | SQL Operator | Semantics |
|--------------|--------------|-----------|
| `hasSome: [...]` | `&&` | Array contains ANY of these values (OR) |
| `has: "value"` | `?` | Array contains this exact value |
| `hasEvery: [...]` | `@>` | Array contains ALL of these values (AND) |

**Lens Transformation (`lib/lens-query.ts`):**
```typescript
// Transform opaque values to rich metadata
const entityView = transformEntityToView(entity, lens);

// Input:  { canonical_activities: ["padel"] }
// Output: {
//   activities: [
//     { key: "padel", label: "Padel", icon: "racket", color: "blue" }
//   ],
//   grouping: "places"  // Computed at query time, not stored
// }
```

---

### 4. State Management

**Current Approach (Server-First):**
- **No client-side state library:** Server Components eliminate most state needs
- **URL as state:** Use search params for filters (`?activity=padel&access=pay_and_play`)
- **Progressive Enhancement:** Client interactions via `"use client"` components where needed

**Future Patterns:**
```typescript
// URL-driven filtering (Next.js 16)
import { useSearchParams } from "next/navigation";

function Filters() {
  "use client";
  const searchParams = useSearchParams();
  const activity = searchParams.get("activity");

  // Update URL to trigger server refetch
  const handleFilter = (value: string) => {
    const params = new URLSearchParams(searchParams);
    params.set("activity", value);
    router.push(`?${params.toString()}`);
  };
}
```

**State Boundaries:**
- **Server State:** Entity data, lens configs (fetched in Server Components)
- **Client State:** UI interactions (filters, modals, animations)
- **Shared State:** Search params (URL is single source of truth)

---

### 5. TypeScript Conventions

**Generated Types (Prisma):**
```typescript
// Auto-generated from prisma/schema.prisma
import { Entity, Prisma } from "@prisma/client";

type EntityWithRelations = Prisma.EntityGetPayload<{
  include: { lensMemberships: true };
}>;
```

**Custom Types:**
```typescript
// lib/entity-queries.ts
export interface FacetFilters {
  activities?: string[];
  roles?: string[];
  place_types?: string[];
  access?: string[];
  entity_class?: string;
}

// lib/lens-query.ts
export interface EntityView {
  id: string;
  entity_name: string;
  entity_class: string;
  activities: Array<{ key: string; label: string; icon?: string }>;
  grouping?: string;  // Computed, not stored
}
```

**Type Safety Guarantees:**
- ✅ Prisma queries return strongly-typed results
- ✅ Generated types auto-update on schema regeneration
- ✅ TypeScript strict mode enabled (`tsconfig.json`)

---

## Styling & Design System

### Tailwind CSS v4

**Configuration (`app/globals.css`):**
```css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-primary: oklch(0.6 0.118 184.704);
  --color-muted: oklch(0.97 0 0);
  --radius-lg: var(--radius);
}

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --radius: 0.5rem;
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
}
```

**Key Features:**
- **v4 Inline Theming:** CSS variables defined in `@theme inline` (no `tailwind.config.js`)
- **OKLCH Color Space:** Perceptually uniform colors, better dark mode
- **Custom Variants:** Dark mode via `@custom-variant`

---

### Design Principles (Agnostic Elegance)

**❌ Prohibited (Vertical Tropes):**
- Neon green for Padel, wine red for Wine Discovery
- Sport-specific iconography in base theme
- Domain-specific color palettes

**✅ Required (Sophisticated Neutrals):**
- Base palette: Zinc/Neutral (shadcn/ui default)
- Accent colors derived from lens metadata (e.g., `canonical_values[key].color`)
- Iconography from lens contracts, not hardcoded

**Example (Lens-Driven Styling):**
```typescript
// Lens contract provides color metadata
const activityBadge = (
  <span
    className="px-2 py-1 rounded-full text-xs"
    style={{ backgroundColor: activity.color }}  // From lens
  >
    {activity.label}
  </span>
);
```

---

### Component Patterns (shadcn/ui)

**Installation:**
```bash
npx shadcn@latest add button card badge
```

**Usage:**
```typescript
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

<Card>
  <CardContent>
    <h3>{entity.entity_name}</h3>
    <Button variant="outline">View Details</Button>
  </CardContent>
</Card>
```

**Customization:**
- Components live in `components/ui/` (not checked in)
- Tailwind classes applied directly to primitives
- Variants configured via `cva` (class-variance-authority)

---

## Mobile-First Approach

### Responsive Breakpoints

```typescript
// Tailwind default breakpoints
sm: '640px'   // Small devices
md: '768px'   // Tablets
lg: '1024px'  // Desktops
xl: '1280px'  // Large desktops
```

**Design Strategy:**
- **Mobile = Tool:** Prioritize CTAs (Directions, Call, Book)
- **Desktop = Resource:** Show comparison tables, detailed specs

**Example:**
```typescript
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Mobile: 1 column, Desktop: 3 columns */}
</div>

<button className="h-11 w-11 md:h-auto md:w-auto md:px-4">
  {/* Mobile: 44x44px touch target */}
</button>
```

---

### Accessibility (WCAG 2.1 AA)

**Requirements:**
- ✅ Minimum touch targets: 44x44px
- ✅ Color contrast: 4.5:1 for text, 3:1 for UI components
- ✅ Keyboard navigation: All interactive elements tabbable
- ✅ ARIA labels: Screen reader support

**Implementation:**
```typescript
<button
  aria-label="Call venue"
  className="h-11 w-11"  // 44px minimum
>
  <Phone className="h-5 w-5" />
</button>
```

---

## API Integration

### Prisma Query Patterns

**Faceted Filtering (Server Component):**
```typescript
import prisma from "@/lib/prisma";
import { buildFacetedWhere } from "@/lib/entity-queries";

export default async function SearchPage({ searchParams }) {
  const filters = {
    activities: searchParams.activity?.split(",") || [],
    entity_class: "place",
  };

  const entities = await prisma.entity.findMany({
    where: buildFacetedWhere(filters),
    take: 20,
  });

  return <EntityGrid entities={entities} />;
}
```

**Pagination:**
```typescript
const entities = await prisma.entity.findMany({
  where,
  skip: (page - 1) * 20,
  take: 20,
  orderBy: { createdAt: "desc" },
});

const totalCount = await prisma.entity.count({ where });
```

**Relationship Loading:**
```typescript
const entity = await prisma.entity.findUnique({
  where: { id },
  include: {
    outgoingRelationships: {
      include: { targetEntity: true },
    },
  },
});
```

---

### Lens-Aware Data Flow

```mermaid
graph LR
    A[User Query] --> B[Server Component]
    B --> C[buildFacetedWhere]
    C --> D[Prisma Query]
    D --> E[Raw Entities]
    E --> F[transformEntityToView]
    F --> G[EntityView with Metadata]
    G --> H[React Render]
```

**Key Points:**
1. **Input:** User-facing filters (UI-friendly labels)
2. **Translation:** Convert to `canonical_*` values via lens vocabulary
3. **Query:** Prisma array filters on universal dimensions
4. **Transform:** Enrich opaque values with display metadata
5. **Render:** Present rich data in UI

---

## Component Architecture

### Current State (Scaffolding Phase)

**No Component Library Yet:**
- Inline JSX in `app/page.tsx` demonstrates patterns
- Component extraction pending (future refactor)

**Example (Current Homepage):**
```typescript
// app/page.tsx (inline rendering)
export default async function Home() {
  const listings = await prisma.entity.findMany({ take: 5 });

  return (
    <main className="flex min-h-screen flex-col items-center p-24">
      <h1 className="text-4xl font-bold mb-8">Edinburgh Finds</h1>
      <ul className="space-y-4">
        {listings.map((listing) => (
          <li key={listing.id} className="p-6 border rounded-lg">
            <h3>{listing.entity_name}</h3>
            <p>{listing.summary}</p>
            {/* Dimensions, modules rendering */}
          </li>
        ))}
      </ul>
    </main>
  );
}
```

---

### Future Component Structure

**Proposed Hierarchy:**
```
components/
├── ui/                    # shadcn/ui primitives
│   ├── button.tsx
│   ├── card.tsx
│   └── badge.tsx
├── entity/
│   ├── EntityCard.tsx     # Universal entity display
│   ├── EntityGrid.tsx     # Grid layout
│   └── EntityDetails.tsx  # Detail view
├── filters/
│   ├── FacetFilter.tsx    # Faceted search UI
│   └── SearchBar.tsx
└── layout/
    ├── Header.tsx
    └── Footer.tsx
```

**Design Principles:**
- **Universal Components:** `EntityCard` accepts any `entity_class`
- **Lens-Driven Rendering:** Components consume `EntityView` (transformed data)
- **No Vertical Hardcoding:** Avoid `if (activity === "padel")` logic

---

## Routing Structure

### Current Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/` | `app/page.tsx` | Homepage (entity listing) |

### Future Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/[slug]` | `app/[slug]/page.tsx` | Entity detail page |
| `/search` | `app/search/page.tsx` | Faceted search interface |
| `/api/entities` | `app/api/entities/route.ts` | REST API (if needed for client components) |

**Dynamic Metadata (SEO):**
```typescript
// app/[slug]/page.tsx
export async function generateMetadata({ params }): Promise<Metadata> {
  const entity = await prisma.entity.findUnique({
    where: { slug: params.slug },
  });

  return {
    title: entity.entity_name,
    description: entity.summary,
  };
}
```

---

## Performance Optimization

### Core Web Vitals Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| **LCP** | < 2.5s | Image optimization, streaming SSR |
| **FID** | < 100ms | Minimal JavaScript, React 19 concurrent features |
| **CLS** | < 0.1 | Reserved space for images, font loading optimization |

**Next.js 16 Features:**
- **Automatic Image Optimization:** `<Image>` component with WebP
- **Incremental Static Regeneration (ISR):** Cache entity pages, revalidate on-demand
- **React Server Components:** Zero JavaScript for static content

---

### Data Fetching Strategy

**Current (Server Components):**
```typescript
// No loading state needed—streaming SSR
export default async function Page() {
  const data = await fetchData();  // Automatically streamed
  return <Content data={data} />;
}
```

**Future (Suspense Boundaries):**
```typescript
import { Suspense } from "react";

export default function Page() {
  return (
    <Suspense fallback={<Skeleton />}>
      <EntityList />  {/* Async Server Component */}
    </Suspense>
  );
}
```

---

## Testing Strategy

### Unit Testing (Future)

**Recommended Stack:**
- Vitest (faster than Jest, ESM-native)
- React Testing Library
- MSW (Mock Service Worker) for Prisma mocks

**Example:**
```typescript
import { render, screen } from "@testing-library/react";
import { EntityCard } from "@/components/entity/EntityCard";

test("renders entity name", () => {
  const entity = { id: "1", entity_name: "Test Venue" };
  render(<EntityCard entity={entity} />);
  expect(screen.getByText("Test Venue")).toBeInTheDocument();
});
```

---

### Integration Testing

**Playwright (E2E):**
```typescript
test("faceted search filters entities", async ({ page }) => {
  await page.goto("/search");
  await page.click('[data-filter="activity"][data-value="padel"]');
  await expect(page.locator('[data-entity-card]')).toHaveCount(5);
});
```

---

## Environment Setup

### Required Environment Variables

```bash
# web/.env
DATABASE_URL="postgresql://user:pass@host:5432/db?schema=public"
NEXT_PUBLIC_SITE_URL="https://edinburgh.finds"  # For metadata
```

### Development Commands

```bash
cd web

# Development
npm run dev          # Start dev server (localhost:3000)

# Production
npm run build        # Build for production
npm run start        # Start production server

# Linting
npm run lint         # ESLint (Next.js config)

# Database
npx prisma generate  # Generate Prisma client
npx prisma db push   # Sync schema to DB (dev)
npx prisma migrate dev  # Create migration (production)
```

---

## Diagrams

### Component Dependency Graph

```mermaid
graph TD
    %% Orchestration Layer
    subgraph Orchestration["Orchestration Layer"]
        ExecutionContext["ExecutionContext<br/>(Immutable context carrier)"]
        QueryFeatures["QueryFeatureExtractor<br/>(Vocabulary-based analysis)"]
        ExecutionPlanner["ExecutionPlanner<br/>(Connector selection)"]
        Orchestrator["Orchestrator<br/>(Pipeline coordinator)"]
        EntityFinalizer["EntityFinalizer<br/>(Slug generation & persistence)"]
    end

    %% Lens Layer
    subgraph LensLayer["Lens Layer"]
        LensLoader["LensLoader<br/>(YAML → runtime contract)"]
        LensValidator["LensValidator<br/>(Bootstrap validation)"]
        MappingEngine["MappingEngine<br/>(Pattern → canonical values)"]
        ModuleTriggerEngine["ModuleTriggerEngine<br/>(Conditional module attachment)"]
    end

    %% Ingestion Layer
    subgraph IngestionLayer["Ingestion Layer"]
        ConnectorRegistry["ConnectorRegistry<br/>(Metadata: trust, cost, phase)"]
        ConnectorAdapters["ConnectorAdapters<br/>(Async bridge & normalization)"]
        RawIngestionStorage["RawIngestionStorage<br/>(Immutable artifact persistence)"]

        subgraph Connectors["Connectors"]
            Serper["Serper"]
            GooglePlaces["GooglePlaces"]
            OSM["OpenStreetMap"]
            SportScotland["SportScotland"]
            EdinburghCouncil["EdinburghCouncil"]
            OpenChargeMap["OpenChargeMap"]
        end
    end

    %% Extraction Layer
    subgraph ExtractionLayer["Extraction Layer"]
        ValidationEngine["ValidationEngine<br/>(Pydantic schemas)"]
        LLMExtractionEngine["LLMExtractionEngine<br/>(Instructor + Claude)"]

        subgraph SourceExtractors["Source Extractors"]
            SerperExtractor["SerperExtractor<br/>(Primitives only)"]
            GooglePlacesExtractor["GooglePlacesExtractor<br/>(Primitives only)"]
            OSMExtractor["OSMExtractor<br/>(Primitives only)"]
            SportScotlandExtractor["SportScotlandExtractor<br/>(Primitives only)"]
            EdinburghCouncilExtractor["EdinburghCouncilExtractor<br/>(Primitives only)"]
            OpenChargeMapExtractor["OpenChargeMapExtractor<br/>(Primitives only)"]
        end

        EntityClassifier["EntityClassifier<br/>(Geographic anchoring rules)"]
        ModuleExtractor["ModuleExtractor<br/>(Generic field rule executor)"]
    end

    %% Deduplication & Merge Layer
    subgraph MergeLayer["Deduplication & Merge"]
        DeduplicationEngine["DeduplicationEngine<br/>(Cross-source grouping)"]
        MergeEngine["MergeEngine<br/>(Metadata-driven conflict resolution)"]
    end

    %% Persistence Layer
    subgraph PersistenceLayer["Persistence Layer"]
        EntityRepository["EntityRepository<br/>(Idempotent upsert)"]
        ProvenanceTracker["ProvenanceTracker<br/>(Source metadata)"]
    end

    %% Schema Generation System
    subgraph SchemaGeneration["Schema Generation"]
        SchemaParser["SchemaParser<br/>(YAML reader)"]
        PythonGenerator["PythonGenerator<br/>(FieldSpecs)"]
        PrismaGenerator["PrismaGenerator<br/>(Database schema)"]
        TypeScriptGenerator["TypeScriptGenerator<br/>(Frontend types)"]
    end

    %% Dependencies - Orchestration
    LensLoader --> ExecutionContext
    LensValidator --> LensLoader
    ExecutionContext --> QueryFeatures
    ExecutionContext --> ExecutionPlanner
    QueryFeatures --> ExecutionPlanner
    ConnectorRegistry --> ExecutionPlanner
    ExecutionPlanner --> Orchestrator
    Orchestrator --> ConnectorAdapters
    Orchestrator --> EntityFinalizer

    %% Dependencies - Lens Layer
    LensLoader --> LensValidator
    LensLoader --> MappingEngine
    LensLoader --> ModuleTriggerEngine

    %% Dependencies - Ingestion
    ConnectorAdapters --> Serper
    ConnectorAdapters --> GooglePlaces
    ConnectorAdapters --> OSM
    ConnectorAdapters --> SportScotland
    ConnectorAdapters --> EdinburghCouncil
    ConnectorAdapters --> OpenChargeMap
    ConnectorAdapters --> RawIngestionStorage
    ConnectorRegistry --> ConnectorAdapters

    %% Dependencies - Extraction
    RawIngestionStorage --> SerperExtractor
    RawIngestionStorage --> GooglePlacesExtractor
    RawIngestionStorage --> OSMExtractor
    RawIngestionStorage --> SportScotlandExtractor
    RawIngestionStorage --> EdinburghCouncilExtractor
    RawIngestionStorage --> OpenChargeMapExtractor

    SerperExtractor --> ValidationEngine
    GooglePlacesExtractor --> ValidationEngine
    OSMExtractor --> ValidationEngine
    SportScotlandExtractor --> ValidationEngine
    EdinburghCouncilExtractor --> ValidationEngine
    OpenChargeMapExtractor --> ValidationEngine

    SerperExtractor --> LLMExtractionEngine
    GooglePlacesExtractor --> LLMExtractionEngine
    OSMExtractor --> LLMExtractionEngine
    SportScotlandExtractor --> LLMExtractionEngine
    EdinburghCouncilExtractor --> LLMExtractionEngine
    OpenChargeMapExtractor --> LLMExtractionEngine

    %% Dependencies - Phase 2: Lens Application (Post-Extraction)
    Orchestrator --> MappingEngine
    Orchestrator --> ModuleTriggerEngine
    MappingEngine --> EntityClassifier
    ModuleTriggerEngine --> EntityClassifier

    %% Dependencies - Merge & Persistence
    EntityClassifier --> DeduplicationEngine
    DeduplicationEngine --> MergeEngine
    ConnectorRegistry --> MergeEngine
    MergeEngine --> EntityFinalizer
    EntityFinalizer --> EntityRepository
    EntityFinalizer --> ProvenanceTracker

    %% Dependencies - Schema Generation
    SchemaParser --> PythonGenerator
    SchemaParser --> PrismaGenerator
    SchemaParser --> TypeScriptGenerator
    PythonGenerator --> ValidationEngine
    PrismaGenerator --> EntityRepository

    %% Styling
    classDef orchestration fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef lens fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef ingestion fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef extraction fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef merge fill:#fff8e1,stroke:#f57f17,stroke-width:2px
    classDef persistence fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef schema fill:#e0f2f1,stroke:#004d40,stroke-width:2px

    class ExecutionContext,QueryFeatures,ExecutionPlanner,Orchestrator,EntityFinalizer orchestration
    class LensLoader,LensValidator,MappingEngine,ModuleTriggerEngine lens
    class ConnectorRegistry,ConnectorAdapters,RawIngestionStorage,Serper,GooglePlaces,OSM,SportScotland,EdinburghCouncil,OpenChargeMap ingestion
    class ValidationEngine,LLMExtractionEngine,SerperExtractor,GooglePlacesExtractor,OSMExtractor,SportScotlandExtractor,EdinburghCouncilExtractor,OpenChargeMapExtractor,EntityClassifier,ModuleExtractor extraction
    class DeduplicationEngine,MergeEngine merge
    class EntityRepository,ProvenanceTracker persistence
    class SchemaParser,PythonGenerator,PrismaGenerator,TypeScriptGenerator schema
```

### State Transition Flow

```mermaid
stateDiagram-v2
    %% Universal Entity Extraction Engine - State Transitions & Execution Flow

    %% Entity Lifecycle States
    [*] --> QuerySubmitted: User submits query

    QuerySubmitted --> LensResolved: Lens resolution & validation
    LensResolved --> PlanCreated: Orchestrator creates execution plan
    PlanCreated --> ConnectorExec: Dispatch connectors by phase

    ConnectorExec --> RawDataIngested: All connectors complete
    RawDataIngested --> Extracted: Per-source extraction

    Extracted --> LensMapped: Apply mapping rules
    LensMapped --> Classified: Determine entity_class

    Classified --> Deduplicated: Cross-source grouping
    Deduplicated --> Merged: Deterministic merge

    Merged --> Finalized: Generate slugs, upsert
    Finalized --> [*]: Entity persisted

    %% Failure paths
    LensResolved --> [*]: Lens validation fails
    ConnectorExec --> PartialIngestion: Some connectors fail
    PartialIngestion --> RawDataIngested: Continue with available data
    Extracted --> [*]: Critical extraction failure
    Merged --> [*]: Persistence failure

    %% Connector Execution States (nested within dispatch phase)
    state "Connector Execution" as ConnectorExec {
        [*] --> Planned
        Planned --> Queued: Added to phase queue
        Queued --> Executing: Connector invoked

        Executing --> RateLimited: Rate limit hit
        RateLimited --> Executing: Retry after backoff

        Executing --> Success: Data returned
        Executing --> Timeout: Execution timeout
        Executing --> Failed: Network/API error

        Success --> Persisting: Save raw artifact
        Persisting --> Completed: Artifact persisted

        Completed --> [*]
        Timeout --> [*]
        Failed --> [*]
    }

    %% Annotations
    note right of LensResolved
        Bootstrap validation gates:
        - Schema validation
        - Canonical registry integrity
        - Connector references
        - Regex compilation
    end note

    note right of Extracted
        Phase 1 (Extractors):
        Schema primitives + raw observations only
        NO canonical_* or modules
    end note

    note right of LensMapped
        Phase 2 (Lens Application):
        Populate canonical dimensions
        Execute module triggers
        Deterministic rules first
    end note

    note right of Merged
        Deterministic merge cascade:
        trust_tier → quality → confidence
        → completeness → priority → connector_id
    end note
```

---

## Voice & Tone Guidelines

**Prohibited Phrases (Generic AI-Sounding):**
- ❌ "Located at"
- ❌ "Features include"
- ❌ "A great place for"
- ❌ "Welcome to"

**Required Style (Contextual Bridges):**
- ✅ "Just a short walk from Waverley Station"
- ✅ "Perfect for those who prefer outdoor courts"
- ✅ "Premium-priced but widely regarded as..."

**Implementation:**
- AI-generated summaries stored in `Entity.summary` (LLM-generated during extraction)
- Frontend displays without modification (pre-validated for tone)

---

## Common Gotchas

### 1. Schema Regeneration

**Problem:** Manually editing `prisma/schema.prisma` gets overwritten.

**Solution:**
```bash
# Edit YAML schemas in engine/config/schemas/
python -m engine.schema.generate --all  # Regenerate Prisma schema
npx prisma generate                      # Regenerate Prisma client
```

---

### 2. Array Filters with Empty Arrays

**Problem:** Empty facet arrays break queries.

**Solution:**
```typescript
// buildFacetedWhere handles this internally
if (filters.activities && filters.activities.length > 0) {
  conditions.push({ canonical_activities: { hasSome: filters.activities } });
}
```

---

### 3. Module Type Safety

**Problem:** `modules` field is `Json` type (untyped).

**Workaround:**
```typescript
// Type guard for specific module
function hasSportsFacilityModule(entity: Entity): entity is Entity & {
  modules: { sports_facility: { court_type: string } }
} {
  return typeof entity.modules === "object" && "sports_facility" in entity.modules;
}

if (hasSportsFacilityModule(entity)) {
  console.log(entity.modules.sports_facility.court_type);  // Type-safe
}
```

---

### 4. Dark Mode Flicker

**Problem:** Flash of light mode on initial load.

**Solution:**
```typescript
// app/layout.tsx
<html lang="en" className="dark" suppressHydrationWarning>
  {/* Add dark class at HTML level */}
</html>
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `app/layout.tsx` | Root layout, metadata, fonts |
| `app/page.tsx` | Homepage (entity listing) |
| `lib/prisma.ts` | Prisma client singleton |
| `lib/entity-queries.ts` | Faceted query builder (Prisma array filters) |
| `lib/lens-query.ts` | Lens-aware transformation layer |
| `lib/utils.ts` | Utility functions (cn, formatters) |
| `prisma/schema.prisma` | Auto-generated database schema (DO NOT EDIT) |

---

## Next Steps

**Immediate Priorities:**
1. ✅ Extract reusable components (`EntityCard`, `FacetFilter`)
2. ⬜ Implement faceted search UI (`/search` route)
3. ⬜ Add entity detail pages (`/[slug]`)
4. ⬜ Integrate lens metadata for dynamic styling

**Future Enhancements:**
- Map integration (Leaflet/Mapbox for location-based entities)
- Image optimization pipeline (auto-resize, WebP conversion)
- Analytics (Vercel Analytics, privacy-first)
- PWA support (offline mode for saved entities)

---

**End of Document**
