# Architecture Overview

This document provides a high-level narrative of the Edinburgh Finds architecture, its core design principles, and a map of its various subsystems.

## Narrative
Edinburgh Finds operates as a tiered data platform. At its heart is the **Data Engine**, a Python-based system that manages the complexity of multi-source data ingestion. The engine is responsible for "discovering" entities (like businesses, landmarks, or events), "extracting" structured data from raw responses using LLMs and traditional parsers, and "merging" these into a unified state.

The system uses a **Lens-based Architecture**, where different "lenses" (e.g., Edinburgh Finds, Wine Discovery) define specific views or subsets of data and logic applicable to a particular domain.

The **Web layer** provides the user-facing discovery interface, built on a modern Next.js stack that shares the same database schema as the engine, ensuring that what is ingested is immediately and accurately representable to the user.

## Key Architectural Decisions
- **Schema-Driven Development**: Schemas are defined once in `engine/config/schemas/*.yaml` and used to generate code for both the engine and the web layers.
- **Trust-Based Conflict Resolution**: When multiple sources provide conflicting data for the same field, the system uses pre-defined trust levels to decide which value to preserve.
- **3-Phase Sequential Pipeline**: Ingestion is split into Discovery, Structured, and Enrichment phases to optimize cost and data quality.
- **LLM-Powered Extraction**: Uses LLMs (via the `instructor` library) to parse unstructured or semi-structured data into strictly typed Pydantic models.

## Subsystem Map

| Subsystem | Responsibility |
|-----------|----------------|
| **[engine-orchestration](./subsystems/engine-orchestration.md)** | Coordinates multi-phase ingestion and manages execution context. |
| **[engine-ingestion](./subsystems/engine-ingestion.md)** | Handles raw data collection from external APIs and connectors. |
| **[engine-extraction](./subsystems/engine-extraction.md)** | Transforms raw data into structured entities using LLMs and parsers. |
| **[engine-lenses](./subsystems/engine-lenses.md)** | Manages domain-specific configuration and logic. |
| **[database](./subsystems/database.md)** | Prisma schemas, migrations, and schema generation tools. |
| **[frontend](./subsystems/frontend.md)** | User interface and entity discovery web application. |
| **[lenses](./subsystems/lenses.md)** | Domain-specific lens definitions (YAML). |
| **[infrastructure](./subsystems/infrastructure.md)** | CI/CD workflows and deployment configurations. |
| **[scripts](./subsystems/scripts.md)** | Automation and management utilities. |
| **[config](./subsystems/config.md)** | Global environment and tool configuration. |

## Data Flow
1. **Request**: A discovery request is received (CLI or API).
2. **Orchestration**: The `engine-orchestration` determines the necessary connectors and phases.
3. **Ingestion**: `engine-ingestion` fetchers collect data from providers (OSM, Google, etc.).
4. **Extraction**: `engine-extraction` converts raw JSON/HTML into structured Pydantic models.
5. **Synthesis**: Entities are merged based on identity and trust rules.
6. **Storage**: The unified entities are persisted to the PostgreSQL database via Prisma.
7. **Delivery**: The `frontend` queries the database to display the discovery results.

---
*Evidence: Subsystem documentation and manifest inventory.*
