# Architecture Documentation

This directory contains the C4 model architecture diagrams for Edinburgh Finds, a hyper-local directory platform.

## C4 Model Diagrams

The C4 model provides a hierarchical view of the system architecture at different levels of detail:

- **[Level 1: System Context](./c4-level1-context.md)** - How users and external systems interact with Edinburgh Finds
- **[Level 2: Container](./c4-level2-container.md)** - High-level technical building blocks (Web App, Data Engine, Database, Storage)

## System Overview

Edinburgh Finds is built with:
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4
- **Data Engine:** Python with Pydantic validation and async HTTP
- **Database:** SQLite (via Prisma ORM)
- **External Data Sources:** Serper API, Google Places API, OpenStreetMap

The architecture follows a clear separation:
- **Web Application** - User-facing Next.js app with Server Components
- **Data Engine** - Python-based CLI connectors for data ingestion
- **Database** - SQLite for structured data storage
- **Raw Storage** - File system for data lineage and archival

## Viewing Diagrams

These diagrams use Mermaid syntax and render automatically in:
- **GitHub/GitLab** - Built-in Mermaid rendering
- **Obsidian** - With Mermaid plugin enabled
- **VS Code** - With Mermaid preview extension
- **IDEs** - Most modern IDEs support Mermaid

For online viewing/editing, use [Mermaid Live](https://mermaid.live/).

## Maintenance

Update these diagrams when:
- Adding new containers (services, databases, workers, etc.)
- Changing technology stack (framework versions, databases, libraries)
- Adding external integrations (APIs, third-party services)
- Modifying system boundaries (new subsystems, microservices)
- Changing deployment architecture

All diagrams are derived from actual code inspection - ensure changes reflect real code changes, not planned features.

## Related Documentation

- `../../conductor/tech-stack.md` - Detailed technology stack and architectural decisions
- `../../conductor/product.md` - Product vision and strategy
- Schema definitions in `web/prisma/schema.prisma`
