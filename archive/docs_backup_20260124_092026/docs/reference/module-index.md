# Module Index

This index provides a map of the key source files in the Edinburgh Finds codebase.

## Core Engine (`engine/`)

| File | Purpose |
|------|---------|
| `engine/ingest.py` | Orchestrator for data ingestion from all sources. |
| `engine/schema.prisma` | Database schema definition (Prisma). |
| `engine/extraction/base.py` | Abstract base class and core logic for extractors. |
| `engine/extraction/entity_classifier.py` | Logic for determining entity classes (place, person, etc). |
| `engine/extraction/llm_client.py` | Wrapper for LLM (Anthropic) and Instructor for structured data. |
| `engine/extraction/merging.py` | Logic for merging extracted data into "Golden Records". |
| `engine/extraction/deduplication.py` | Detects duplicate entities across different sources. |

## Operational Scripts (`scripts/`)

| File | Purpose |
|------|---------|
| `scripts/run_lens_aware_extraction.py` | Main CLI tool for running extraction for a specific lens. |
| `scripts/validate_wine_lens.py` | Utility to validate the configuration of the wine lens. |

## Web Application (`web/`)

| Path | Purpose |
|------|---------|
| `web/app/` | Next.js App Router directory (Pages and API routes). |
| `web/lib/prisma.ts` | Prisma client initialization for the frontend. |
| `web/components/` | Reusable React components for the dashboard. |

## Lenses (`lenses/`)

| Path | Purpose |
|------|---------|
| `lenses/edinburgh_finds/` | Configuration and mapping rules for local discovery. |
| `lenses/wine_discovery/` | Configuration and mapping rules for wine-specific data. |
