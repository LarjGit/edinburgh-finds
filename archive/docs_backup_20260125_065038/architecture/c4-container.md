# C4 Container Diagram

The Container diagram shows the high-level technical architecture and how the various subsystems are partitioned.

```mermaid
C4Container
    title Container diagram for Edinburgh Finds

    Person(user, "User", "Discovery and search")
    Person(dev, "Developer", "CLI operations and management")

    System_Boundary(c1, "Edinburgh Finds") {
        Container(web_app, "Web Application", "Next.js, TypeScript", "Provides the discovery UI and search interface.")
        Container(data_engine, "Data Engine (ETL)", "Python, Pydantic", "Orchestrates ingestion, extraction, and synthesis.")
        ContainerDb(db, "Database", "PostgreSQL", "Stores ingested entities, raw data, and system state.")
        Container(cli, "CLI Tool", "Python", "Interface for developers to trigger and monitor ingestion runs.")
    }

    System_Ext(external_apis, "External APIs", "OSM, Google, Serper, Council APIs")
    System_Ext(llm, "LLM Service", "Anthropic Claude")

    Rel(user, web_app, "Uses", "HTTPS")
    Rel(dev, cli, "Uses", "Shell")
    Rel(cli, data_engine, "Triggers", "Function calls")
    Rel(web_app, db, "Reads from", "Prisma/SQL")
    Rel(data_engine, db, "Reads/Writes", "Prisma/SQL")
    Rel(data_engine, external_apis, "Queries", "HTTPS/JSON")
    Rel(data_engine, llm, "Sends data for extraction", "HTTPS/JSON")
```

## Containers
- **Web Application**: A Next.js 16 application that serves the frontend and handles user queries. It interacts with the database via Prisma.
- **Data Engine (ETL)**: The core Python logic responsible for the ingestion pipeline. It handles the complexity of multi-source merging and trust rules.
- **Database**: A PostgreSQL instance (managed via Supabase) that serves as the central storage for all discovery data and system configuration.
- **CLI Tool**: A set of scripts and entry points that allow developers to run ingestion tasks, validate schemas, and manage the system.

---
*Evidence: tech-stack.md and subsystem documentation.*
