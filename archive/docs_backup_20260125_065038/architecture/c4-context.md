# C4 Context Diagram

The System Context diagram provides a high-level view of how Edinburgh Finds interacts with its users and external systems.

```mermaid
C4Context
    title System Context diagram for Edinburgh Finds

    Person(user, "User/Developer", "Discovers entities or manages the ingestion process.")
    System(edinburgh_finds, "Edinburgh Finds", "Intelligent data ingestion and discovery platform.")

    System_Ext(osm, "OpenStreetMap", "Geographic data provider.")
    System_Ext(google_places, "Google Places API", "Local business and landmark data.")
    System_Ext(serper, "Serper (Google Search)", "Web search and place discovery.")
    System_Ext(ed_council, "Edinburgh Council", "Official city data and facilities.")
    System_Ext(anthropic, "Anthropic (Claude)", "LLM for data extraction and synthesis.")

    Rel(user, edinburgh_finds, "Searches for entities, manages data")
    Rel(edinburgh_finds, osm, "Queries geographic data")
    Rel(edinburgh_finds, google_places, "Queries place details")
    Rel(edinburgh_finds, serper, "Performs web searches")
    Rel(edinburgh_finds, ed_council, "Ingests official city data")
    Rel(edinburgh_finds, anthropic, "Sends raw data for structured extraction")
```

## External Systems
- **OpenStreetMap**: Primary source for geographic features and basic entity information.
- **Google Places**: High-quality source for business details, ratings, and opening hours.
- **Serper**: Used for broad discovery when specific IDs are unknown, and for gathering auxiliary web information.
- **Edinburgh Council**: Source for official government data, public facilities, and planning information.
- **Anthropic (Claude)**: Provides the intelligence for extracting structured information from raw, messy data sources.

---
*Evidence: engine-ingestion and engine-extraction subsystem analysis.*
