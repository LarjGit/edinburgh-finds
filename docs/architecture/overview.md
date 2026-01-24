Audience: Developers

# Architecture Overview

Edinburgh Finds is built as a **Universal Discovery Engine**. Its primary design goal is to separate the *mechanics* of data discovery from the *domain-specific logic* of any particular vertical.

## Core Design Principles

### 1. Engine Purity
The engine core is vertical-agnostic. It does not know about "Padel", "Wine", or "Tennis". Instead, it works with:
- **Entities:** Universal objects (Place, Person, Organization).
- **Dimensions:** Multi-valued tags (Activities, Roles, Access).
- **Modules:** Structured namespaces (Contact, Location, Hours).

### 2. Lens-Driven Logic
Vertical-specific logic is encapsulated in **Lenses**. A Lens defines:
- **Seed Queries:** What to search for initially.
- **Classification Rules:** How to map raw data to dimensions.
- **Search Features:** How users interact with the data in the UI.

### 3. LLM-Centric Extraction
Instead of fragile regex or CSS selectors, the engine uses Large Language Models (LLMs) to extract structured data from semi-structured or unstructured raw sources. This allows the system to adapt to source changes with minimal code modifications.

### 4. Source Trust & Merging
The system implements a tiered trust model. When data for the same entity is found across multiple sources (e.g., Google Places and OpenStreetMap), the engine merges the fields based on configurable trust scores per source and per field.

## High-Level Data Flow

1. **Ingest:** Connectors fetch raw JSON/HTML from external APIs and websites.
2. **Classify:** The engine determines if a raw record matches the current Lens requirements.
3. **Extract:** LLMs transform raw data into the Universal Entity Model.
4. **Merge/Deduplicate:** Similar entities are linked; fields are updated based on trust.
5. **Serve:** The Lens-aware API filters and presents the unified data to the frontend.

## Key Subsystems

- **Orchestration:** Manages the lifecycle of a discovery run.
- **Ingestion:** Handles the "dirty work" of API integration, rate limiting, and retries.
- **Extraction:** Orchestrates LLM calls, caching, and cost monitoring.
- **Schema:** Ensures consistency across Python, TypeScript, and the Database.
- **Web:** A React-based interface that dynamically adjusts based on the active Lens.
