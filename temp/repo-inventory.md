# Repository Inventory

**Project:** Edinburgh Finds
**Date:** 2026-01-24

## 1. Structure & Stats
- **Root Directory:** `C:\Projects\edinburgh_finds`
- **Languages:**
  - Python (Backend/Engine)
  - TypeScript (Frontend/Web)
- **Frameworks:**
  - Backend: Pydantic, Prisma Client Python, Instructor, Pytest
  - Frontend: Next.js (App Router), React, Tailwind CSS, Prisma Client JS

### File Counts (Approximate Source)
- **Engine (Python):** 96 files
- **Web (TypeScript/React):** 19 files (excluding node_modules)
- **Lenses:** 4 files
- **Configuration:** ~10 files (YAML, JSON, Prisma)

## 2. Top-Level Directory Map
- `engine/`: Core logic for data ingestion, extraction, and processing.
  - `extraction/`: Logic for identifying entities from raw data using LLMs.
  - `ingestion/`: Connectors to external APIs (Google, OSM).
  - `config/`: Configuration files (YAML).
  - `schema.prisma`: Database schema.
- `web/`: Next.js web application.
  - `app/`: Routes and pages.
  - `lib/`: Shared utilities.
- `lenses/`: Domain-specific configuration bundles.
- `scripts/`: Operational scripts and entry points.
- `conductor/`: Project management and track definitions.

## 3. Subsystems & Capabilities
1.  **Extraction Engine**:
    - **Purpose**: Transform unstructured/semi-structured data into structured Entities.
    - **Components**: Entity Classifier, Deduplication, Merging, LLM Client.
    - **Key Files**: `engine/extraction/base.py`, `engine/extraction/run_all.py`.

2.  **Ingestion Pipeline**:
    - **Purpose**: Fetch raw data from external sources.
    - **Components**: Connectors (Google Places, OSM, Serper).
    - **Key Files**: `engine/ingest.py`, `engine/ingestion/modules/`.

3.  **Lens System**:
    - **Purpose**: Adapt the engine for different domains (e.g., "Edinburgh Finds" vs "Wine Discovery").
    - **Components**: Lens configuration files.
    - **Key Files**: `lenses/`.

4.  **Web Dashboard**:
    - **Purpose**: Visualize extracted data and manage the system.
    - **Components**: Next.js App, Prisma Data Access.

5.  **Data Persistence**:
    - **Purpose**: Store raw and structured data.
    - **Components**: PostgreSQL (implied by Prisma), Prisma Schema.

## 4. Configuration Surfaces
- **Environment**: `.env`, `.env.example` (API Keys, DB URL).
- **Application Config**: `engine/config/entity_model.yaml`, `engine/config/extraction.yaml`.
- **Database**: `engine/schema.prisma`.
- **Project**: `pyproject.toml` (if exists), `web/package.json`.

## 5. Documentation Gaps
- **Prior Status**: All previous docs moved to `archive/`.
- **Needs**:
    - Detailed setup guide (installing Python + Node deps).
    - Configuration reference (what do the YAMLs control?).
    - "How it works" for the Extraction Engine (complex logic).
    - CLI Command reference for `scripts/` and `engine/` entry points.
