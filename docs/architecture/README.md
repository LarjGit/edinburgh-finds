# Architecture Documentation

This directory contains C4 model architecture diagrams for the Edinburgh Finds platform.

## C4 Model Diagrams

- **[Level 1: System Context](./c4-level1-context.md)** - Shows how users and external systems interact with Edinburgh Finds
- **[Level 2: Container Diagram](./c4-level2-container.md)** - Shows the high-level technical building blocks (web app, data engine, database, storage)

## What is the C4 Model?

The C4 model is a hierarchical approach to visualizing software architecture:

1. **Level 1: System Context** - The big picture: users, systems, and their relationships
2. **Level 2: Container** - High-level technology choices: applications, databases, file systems
3. **Level 3: Component** - Internal structure of each container (not included in this documentation)
4. **Level 4: Code** - Classes, functions, and implementation details (not included in this documentation)

This documentation covers Levels 1 and 2, providing a clear overview of the Edinburgh Finds platform architecture.

## Viewing Diagrams

These diagrams use **Mermaid syntax** and render automatically in:

- **GitHub/GitLab** - Diagrams render inline when viewing markdown files
- **Obsidian** - With Mermaid plugin enabled
- **VS Code** - With Mermaid preview extension installed
- **JetBrains IDEs** - Built-in markdown preview supports Mermaid

### Online Viewer

If you need to view or edit diagrams outside of these tools, use:

**[Mermaid Live Editor](https://mermaid.live/)** - Copy the Mermaid code block and paste it into the editor

## Architecture Overview

### System Components

Edinburgh Finds consists of four main containers:

1. **Web Application** (Next.js 16, React 19, TypeScript)
   - Server-side rendered UI
   - Displays venue listings to end users
   - Read-only access to database

2. **Data Engine** (Python, Pydantic, aiohttp)
   - CLI-based data ingestion pipeline
   - Fetches data from 6 external APIs
   - Validates and transforms data

3. **Database** (SQLite via Prisma)
   - Stores validated listings and raw ingestions
   - Accessed by both web app and data engine

4. **Raw Data Storage** (File System)
   - Stores raw JSON from external APIs
   - Enables reprocessing and debugging

### External Data Sources

The platform aggregates data from:
- Serper API (Google search results)
- Google Places API (venue details)
- OpenStreetMap API (geographic data)
- Open Charge Map API (EV charging stations)
- Sport Scotland API (sports facilities)
- Edinburgh Council API (council facilities)

## Maintenance

Update these diagrams when:

- Adding new containers (services, databases, workers, etc.)
- Changing technology stack (e.g., migrating from SQLite to PostgreSQL)
- Adding external integrations (new APIs, third-party services)
- Modifying system boundaries (e.g., adding authentication service)
- Refactoring major architectural components

## Guidelines for Updates

1. **Code-Only Inspection**: Always derive diagrams from actual code, not documentation
2. **Technology Labels**: Every container MUST show its technology stack
3. **Top-Down Orientation**: Use `graph TB` for consistent vertical layout
4. **Separate Files**: Keep one diagram per file for easier navigation
5. **Validate Syntax**: Test complex diagrams at [Mermaid Live](https://mermaid.live/) before committing

## Related Documentation

- [Tech Stack](../../conductor/tech-stack.md) - Detailed technology choices and rationale
- [Database Schema](../../web/prisma/schema.prisma) - Prisma schema definition
- [Data Pipeline](../../engine/) - Data engine source code

---

**Last Updated:** 2026-01-15
**Diagrams:** 2 (Context, Container)
**Format:** Mermaid (TB orientation)
**Scope:** `engine/` and `web/` runtime architecture
