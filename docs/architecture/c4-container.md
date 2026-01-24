Audience: Developers

# C4 Container Diagram

The Container diagram shows the high-level software building blocks of the Edinburgh Finds system.

```mermaid
C4Container
    title Container diagram for Edinburgh Finds

    Person(user, "End User")
    
    Container_Boundary(c1, "Edinburgh Finds System") {
        Container(web, "Next.js Frontend", "React, TypeScript", "Dynamic UI for entity discovery and filtering.")
        Container(api, "Next.js API Routes", "TypeScript, Prisma", "Lens-aware data retrieval and search.")
        Container(orchestrator, "Orchestration Engine", "Python", "Plans and executes ingestion/extraction runs.")
        Container(ingestor, "Ingestion Pipeline", "Python", "Fetches raw data via multi-connector framework.")
        Container(extractor, "Extraction Engine", "Python, Pydantic", "LLM-driven structured data extraction.")
        
        ContainerDb(db, "PostgreSQL", "PostGIS, JSONB", "Stores raw ingestion records, unified entities, and LLM cache.")
    }

    Rel(user, web, "Uses")
    Rel(web, api, "Queries", "JSON/HTTPS")
    Rel(api, db, "Reads/Writes", "Prisma")
    
    Rel(orchestrator, ingestor, "Commands")
    Rel(orchestrator, extractor, "Commands")
    
    Rel(ingestor, db, "Stores Raw Data")
    Rel(extractor, db, "Reads Raw / Stores Entities")
    
    System_Ext(external_apis, "External APIs", "OSM, Google, Serper")
    System_Ext(llm_service, "LLM Service", "Claude / OpenAI")

    Rel(ingestor, external_apis, "Fetch", "HTTPS")
    Rel(extractor, llm_service, "Extract", "JSON/HTTPS")
```

## Internal Components

- **PostgreSQL:** The central source of truth, utilizing `JSONB` for extensible module data and `PostGIS` for spatial queries.
- **Python Engine:** Handles the heavy lifting of data processing, LLM orchestration, and schema enforcement.
- **Next.js Frontend:** A modern, type-safe interface that leverages the shared schema for consistent data rendering.
