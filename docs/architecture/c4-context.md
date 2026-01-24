Audience: Developers

# C4 Context Diagram

The System Context diagram shows the Edinburgh Finds system and its relationship with users and external systems.

```mermaid
C4Context
    title System Context diagram for Edinburgh Finds

    Person(user, "End User", "A user looking for local facilities (e.g., Padel courts, Wine shops).")
    Person(admin, "System Admin", "Monitors engine health and updates Lenses.")

    System(engine, "Edinburgh Finds Engine", "Ingests, extracts, and unifies entity data.")

    System_Ext(osm, "OpenStreetMap", "Source for geographic and facility data.")
    System_Ext(google, "Google Places", "Source for business names, ratings, and contact info.")
    System_Ext(llm, "LLM Provider (Anthropic/OpenAI)", "Processes unstructured data into structured schemas.")
    System_Ext(external_web, "External Websites", "Direct scraping of venue/provider sites.")

    Rel(user, engine, "Searches and explores entities")
    Rel(admin, engine, "Configures Lenses and monitors runs")
    Rel(engine, osm, "Fetches geographic data")
    Rel(engine, google, "Fetches business details")
    Rel(engine, llm, "Sends raw text for structured extraction")
    Rel(engine, external_web, "Scrapes raw content")
```

## External Dependencies

- **OpenStreetMap:** Primary source for physical locations and basic attributes.
- **Google Places / Serper:** High-fidelity source for business names and ratings.
- **LLM Provider:** Critical for turning noisy raw data into the Universal Entity Model.
- **Local Authorities:** (e.g., Edinburgh Council) Trusted sources for specific facility types.
