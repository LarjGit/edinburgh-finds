# C4 Level 2: Container Diagram

**Generated:** 2026-01-15
**System:** Edinburgh Finds

## Purpose

This diagram shows the high-level technical building blocks of Edinburgh Finds.

## Diagram

```mermaid
graph TB
    User["User"]
    Operator["Data Operator"]

    subgraph System["Edinburgh Finds"]
        Web["Web Application<br/><b>Tech: Next.js 16, React 19, TypeScript, Prisma Client</b><br/>Renders UI and queries listings"]
        DataEngine["Data Engine<br/><b>Tech: Python, Pydantic, Prisma Client (py), aiohttp</b><br/>Fetches and stores raw data"]
        DB["Database<br/><b>Tech: SQLite (Prisma)</b><br/>Stores listings and ingestion records"]
        RawStorage["Raw Data Storage<br/><b>Tech: Local filesystem (JSON)</b><br/>Stores raw ingestion payloads"]
    end

    Serper["Serper API"]
    GooglePlaces["Google Places API"]
    OSM["OpenStreetMap Overpass API"]
    OpenChargeMap["OpenChargeMap API"]
    EdinburghCouncil["Edinburgh Council ArcGIS Hub"]
    SportScotland["SportScotland WFS"]

    User -->|"HTTPS"| Web
    Operator -->|"CLI"| DataEngine

    Web -->|"Prisma / SQL"| DB
    DataEngine -->|"Prisma / SQL"| DB
    DataEngine -->|"Write JSON"| RawStorage

    DataEngine -->|"HTTPS"| Serper
    DataEngine -->|"HTTPS"| GooglePlaces
    DataEngine -->|"HTTPS"| OSM
    DataEngine -->|"HTTPS"| OpenChargeMap
    DataEngine -->|"HTTPS"| EdinburghCouncil
    DataEngine -->|"HTTPS"| SportScotland
```

## Containers

| Container | Technology | Responsibility |
|-----------|------------|----------------|
| Web Application | Next.js, React, TypeScript, Prisma Client | Render UI and query listings |
| Data Engine | Python, Pydantic, Prisma Client (py), aiohttp | Fetch, deduplicate, and store raw data |
| Database | SQLite (via Prisma) | Persist listings and ingestion records |
| Raw Data Storage | Local filesystem (JSON) | Store raw ingestion payloads |

## Technology Stack Summary

- **Frontend:** Next.js 16, React 19, TypeScript
- **Backend:** Python, aiohttp, Prisma Client (py)
- **Database:** SQLite
- **Storage:** Local filesystem (JSON)
