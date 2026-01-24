# Architecture Overview

Audience: System Architects and Developers.

## High-Level Architecture

The system is composed of two main subsystems: the **Extraction Engine** (Offline/Background) and the **Discovery Application** (Online/User-Facing).

### 1. Extraction Engine (Python)

An autonomous ETL pipeline responsible for:
- **Ingestion**: Fetching raw data from external APIs (Google, OSM, Serper).
- **Extraction**: Using LLMs (Claude via Instructor) to structure unstructured text into typed objects.
- **Resolution**: Deduplicating entities and resolving conflicts using a "Golden Data" trust model.
- **Seeding**: Populating the Postgres database.

Key Components:
- `engine/ingest.py`: Entry point for fetching data.
- `engine/extraction/`: Core logic for LLM processing and entity classification.
- `engine/config/schemas/`: YAML definitions of the entity models.

Evidence: `engine/README.md` (inferred), `engine/extraction/__init__.py`

### 2. Discovery Application (Next.js)

A modern web application responsible for:
- **Presentation**: Displaying entities with high performance.
- **Filtering**: Using the "Lenses" configuration to provide vertical-specific facets.
- **Routing**: URL structures optimized for SEO and discovery.

Key Components:
- `web/app/`: Next.js App Router pages.
- `web/lib/prisma.ts`: Database client.

Evidence: `web/README.md`

### 3. Universal Entity Framework

The bridge between the Engine and the Web App.
- **Data**: Stored in a generic schema (`Entity` table) with opaque arrays for dimensions.
- **Interpretation**: The "Lenses" layer (`lenses/*.yaml`) tells the Web App how to interpret the opaque data for a specific vertical (e.g., "Padel").

Evidence: `conductor/product.md`
