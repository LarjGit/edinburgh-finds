# Architecture Documentation

This directory contains C4 model architecture diagrams for the Edinburgh Finds platform, a hyper-local discovery system for enthusiasts in Edinburgh.

## C4 Model Diagrams

The C4 model provides a hierarchical view of software architecture at different levels of abstraction:

- **[Level 1: System Context](./c4-level1-context.md)** - Shows how users and external systems interact with Edinburgh Finds
- **[Level 2: Container](./c4-level2-container.md)** - Shows high-level technical building blocks (web app, data engine, database)

## System Overview

**Edinburgh Finds** is a hyper-local directory platform connecting enthusiasts with venues, coaches, retailers, clubs, and events. The MVP focuses on Padel in Edinburgh, with architecture designed for horizontal scaling to other niches.

### Key Components

1. **Web Application** (Next.js 16, React 19, TypeScript)
   - Server-rendered discovery UI
   - Mobile-first responsive design
   - Direct Prisma database queries from server components

2. **Data Ingestion Engine** (Python, Pydantic)
   - Autonomous ETL pipeline
   - Connector-based architecture for multiple data sources
   - Hash-based deduplication
   - Raw data archiving for audit trail

3. **Database** (SQLite dev / PostgreSQL prod)
   - Universal Entity Framework schema
   - Flexible attributes system (core columns + JSON buckets)
   - Prisma ORM v5 for type-safe access

### Architecture Principles

- **"AI-Scale, Local Soul"** - LLM-powered data ingestion with locally curated UX
- **Niche-Agnostic** - Generic entity model supports any hobby/niche
- **Trust Architecture** - Tiered confidence system; business-claimed data is gold standard
- **Progressive Disclosure** - Clean, premium aesthetic with mobile-first design

## Viewing Diagrams

These diagrams use **Mermaid syntax** and render automatically in:

- **GitHub/GitLab** - View this repository on GitHub
- **Obsidian** - With [Mermaid plugin](https://github.com/obsidianmd/obsidian-mermaid)
- **VS Code** - With [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid)
- **Online** - Paste code into [Mermaid Live Editor](https://mermaid.live/)

### Rendering Example

In VS Code:
1. Open any `.md` file in this directory
2. Press `Ctrl+K V` (or `Cmd+K V` on Mac) to open Markdown preview
3. Diagrams render inline automatically

## Maintenance

Update these diagrams when:

- ✅ Adding new containers (services, databases, background workers)
- ✅ Changing technology stack (update both diagram and tech labels)
- ✅ Adding external integrations (APIs, third-party services)
- ✅ Modifying system boundaries (new user types, external systems)
- ✅ Architectural refactoring (component restructuring)

### Update Process

1. Edit the relevant `.md` file in `docs/architecture/`
2. Update technology labels in `<b>` tags to match actual code
3. Validate syntax at [Mermaid Live](https://mermaid.live/)
4. Commit with message: `docs(architecture): [describe change]`

## Related Documentation

- **[Product Vision](../../conductor/product.md)** - PRD and mission statement
- **[Tech Stack](../../conductor/tech-stack.md)** - Current technology choices (source of truth)
- **[Workflow](../../conductor/workflow.md)** - TDD development process
- **[Active Tracks](../../conductor/tracks.md)** - Current work in progress

## Technology Stack Reference

### Frontend
- Next.js 16 (React 19, TypeScript)
- Tailwind CSS v4
- shadcn/ui components

### Backend
- Next.js API Routes (TypeScript)
- Prisma ORM v5

### Data Engine
- Python
- Pydantic validation
- Prisma Client Python

### Database
- SQLite (development)
- PostgreSQL via Supabase (production)

### Infrastructure
- Vercel (web hosting - planned)
- Supabase (database - planned)

---

**Last Updated:** 2026-01-13
**Diagram Format:** Mermaid (TB orientation)
**Scope:** `engine/` and `web/` runtime architecture only
