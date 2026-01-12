# Frontend Analysis Findings

## 1. High-Level Assessment
The frontend (`web/`) is currently a raw `create-next-app` scaffold. While this means there is no technical debt, it also means there is **no architecture** yet. Starting development immediately without defining a folder structure and component hierarchy will lead to a "Big Ball of Mud" very quickly.

## 2. Specific Gaps

### A. Missing Component Architecture
- **Status:** `components.json` exists (shadcn), but no component directories are visible in the root scan.
- **Risk:** Without a clear separation between "Generic UI" (Buttons, Inputs) and "Domain Features" (ListingCard, SearchBar), the `components/` folder will become unmanageable.

### B. Undefined Routing Strategy
- **Status:** Only `app/page.tsx` exists.
- **Requirement:** The Product Vision implies a hierarchical URL structure (e.g., `/padel`, `/padel/powerleague-portobello`).
- **Gap:** We need to explicitly define if we are using Dynamic Routes (`[slug]`) or a flat structure.

### C. Missing Core Layouts
- **Status:** Default `layout.tsx` only.
- **Requirement:** A directory app needs complex layouts: "Search Layout" (Sidebar + Grid), "Detail Layout" (Hero + Content), "Marketing Layout" (Home).

## 3. Recommendations for Refactor

1.  **Adopt a Feature-Based Architecture:**
    -   Instead of dumping everything in `components/`, use a feature-based approach:
        -   `features/search/` (Components, Hooks, State for Search)
        -   `features/listing/` (Components, Hooks for Entity Display)
        -   `components/ui/` (Strictly for dumb shadcn primitives)

2.  **Define Route Groups:**
    -   Use Next.js Route Groups to separate concerns:
        -   `(public)`: Home, Marketing pages.
        -   `(app)`: The actual directory app (Search, Details).
        -   `(admin)`: Business owner portal.

3.  **Strict Server/Client Separation:**
    -   Enforce a pattern where Page files (`page.tsx`) are Server Components that fetch data, and they pass data to Client Components for interactivity.
