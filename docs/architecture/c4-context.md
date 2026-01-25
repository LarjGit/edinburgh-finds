# C4 Context Diagram

The C4 Context diagram shows the Edinburgh Finds system and its relationship with users and external systems.

```mermaid
C4Context
    title System Context diagram for Edinburgh Finds

    Person(User, "End User", "Discovers entities (places, people) through domain-specific lenses.")
    Person(Admin, "System Administrator", "Configures lenses, manages data ingestion, and monitors system health.")

    System(EdinburghFinds, "Edinburgh Finds", "Harmonizes raw data into structured entities and provides discovery interfaces.")

    System_Ext(GooglePlaces, "Google Places API", "Provides structured place data and reviews.")
    System_Ext(OSM, "OpenStreetMap", "Provides geographic and facility data via Overpass API.")
    System_Ext(Serper, "Serper (Google Search)", "Provides general search results and web discovery.")
    System_Ext(CouncilAPIs, "Government APIs", "Specialized data sources (ArcGIS, WFS) for council and sports data.")
    System_Ext(LLM, "LLM Provider (Anthropic)", "Performs structured data extraction from raw ingestion.")

    Rel(User, EdinburghFinds, "Uses", "HTTPS")
    Rel(Admin, EdinburghFinds, "Manages & Monitors", "CLI/HTTPS")

    Rel(EdinburghFinds, GooglePlaces, "Fetches data from")
    Rel(EdinburghFinds, OSM, "Fetches data from")
    Rel(EdinburghFinds, Serper, "Fetches data from")
    Rel(EdinburghFinds, CouncilAPIs, "Fetches data from")
    Rel(EdinburghFinds, LLM, "Sends raw data for extraction")
```

## External Actors
- **End User**: Primarily interacts with the Next.js web application to find specific types of entities (e.g., "padel courts" or "wine shops").
- **System Administrator**: Uses the Engine CLI to trigger ingestion jobs, check purity, and update schemas.

## External Systems
- **Data Providers**: Various APIs that provide the raw material for the engine.
- **LLM Provider**: The intelligence layer used for high-fidelity extraction of attributes from messy raw data.

---
*Evidence: docs/architecture/subsystems/engine.md, docs/architecture/subsystems/infrastructure.md*
