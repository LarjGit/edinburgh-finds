# C4 Level 1: System Context

**Generated:** 2026-01-15
**System:** Edinburgh Finds

## Purpose

This diagram shows how users and external systems interact with Edinburgh Finds.

## Diagram

```mermaid
graph TB
    User["User<br/>(End User)<br/>Browses listings"]
    Operator["Data Operator<br/>(Ingestion CLI user)<br/>Runs data fetches"]

    System["Edinburgh Finds<br/>Local venue discovery platform<br/>Indexes and displays listings"]

    Serper["Serper API<br/>(Search results API)<br/>Provides web search data"]
    GooglePlaces["Google Places API<br/>(Places search)<br/>Provides place details"]
    OSM["OpenStreetMap Overpass API<br/>(OSM data query)<br/>Provides map features"]
    OpenChargeMap["OpenChargeMap API<br/>(EV charging data)<br/>Provides station data"]
    EdinburghCouncil["Edinburgh Council ArcGIS Hub<br/>(Civic datasets)<br/>Provides facility data"]
    SportScotland["SportScotland WFS<br/>(Sports facilities data)<br/>Provides facility layers"]

    User -->|"HTTPS"| System
    Operator -->|"Runs CLI"| System

    System -->|"HTTPS"| Serper
    System -->|"HTTPS"| GooglePlaces
    System -->|"HTTPS"| OSM
    System -->|"HTTPS"| OpenChargeMap
    System -->|"HTTPS"| EdinburghCouncil
    System -->|"HTTPS"| SportScotland
```

## Key Actors

- **User:** Uses the web app to browse venue listings.
- **Data Operator:** Runs ingestion CLI to fetch external data sources.

## External Dependencies

| System | Purpose | Protocol |
|--------|---------|----------|
| Serper API | Search results ingestion | HTTPS |
| Google Places API | Places search ingestion | HTTPS |
| OpenStreetMap Overpass API | Map feature ingestion | HTTPS |
| OpenChargeMap API | EV charging data ingestion | HTTPS |
| Edinburgh Council ArcGIS Hub | Civic dataset ingestion | HTTPS |
| SportScotland WFS | Sports facility ingestion | HTTPS |
