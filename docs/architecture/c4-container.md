# C4 Container Diagram

The C4 Container diagram shows the high-level technical building blocks of the Edinburgh Finds system.

```mermaid
C4Container
    title Container diagram for Edinburgh Finds

    Person(User, "End User")
    Person(Admin, "System Administrator")

    Container_Boundary(EF_System, "Edinburgh Finds System") {
        Container(WebUI, "Discovery Frontend", "Next.js, React, Tailwind", "Provides domain-specific search and entity views.")
        Container(EngineCLI, "Engine CLI", "Python, Typer", "Allows administrators to trigger ingestion and extraction.")
        Container(Orchestrator, "Ingestion Orchestrator", "Python, asyncio", "Manages complex multi-phase data acquisition.")
        Container(Extractor, "Extraction Pipeline", "Python, Pydantic, Instructor", "Transforms raw data into universal entities using LLMs.")
        ContainerDb(Database, "Primary Database", "PostgreSQL", "Stores raw ingestion, universal entities, and lens memberships.")
        Container(SchemaGen, "Schema Generator", "Python", "Maintains cross-language type safety (YAML -> Prisma/Pydantic/TS).")
    }

    System_Ext(DataProviders, "External APIs", "Google, OSM, Serper, etc.")
    System_Ext(LLM, "LLM Service", "Anthropic Claude")

    Rel(User, WebUI, "Uses", "HTTPS")
    Rel(Admin, EngineCLI, "Uses", "CLI")
    
    Rel(WebUI, Database, "Reads from", "Prisma JS")
    Rel(EngineCLI, Orchestrator, "Commands")
    Rel(EngineCLI, SchemaGen, "Commands")
    
    Rel(Orchestrator, DataProviders, "Fetches raw data", "HTTPS")
    Rel(Orchestrator, Database, "Saves raw ingestion", "Prisma PY")
    
    Rel(Extractor, Database, "Reads raw data / Saves entities", "Prisma PY")
    Rel(Extractor, LLM, "Sends extraction prompts", "HTTPS")
    
    Rel(SchemaGen, Database, "Updates schema", "Prisma Migrate")
```

## Containers
- **Discovery Frontend**: A modern web application that applies "Lenses" to the data. It is read-heavy and uses Prisma for type-safe queries.
- **Ingestion Orchestrator**: The "brain" of data acquisition. It manages dependencies between connectors and ensures efficient data gathering.
- **Extraction Pipeline**: The core value-add component that turns messy JSON into a structured, queryable database.
- **Schema Generator**: An internal tool that ensures that a change in the data model is reflected across the entire stack.
- **Primary Database**: The central repository for all structured and semi-structured data.

---
*Evidence: docs/architecture/subsystems/engine.md, docs/architecture/subsystems/database.md, docs/architecture/subsystems/web.md*
