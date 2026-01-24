Audience: Developers

# Edinburgh Finds Documentation

Welcome to the technical documentation for Edinburgh Finds. This project is a multi-vertical data ingestion and discovery engine designed to crawl, extract, and unify entity data (places, people, organizations) from various sources, presenting them through a "Lens" aware interface.

## 🏗️ Architecture

- [**System Overview**](architecture/overview.md) — High-level architecture and engine-purity principles.
- [**C4 Context**](architecture/c4-context.md) — System boundaries and external dependencies.
- [**C4 Container**](architecture/c4-container.md) — Subsystems, data stores, and communication paths.

### Subsystems
- [**Orchestration**](architecture/subsystems/orchestration.md) — The brain of the engine: query planning and execution.
- [**Schema & Generators**](architecture/subsystems/schema-core.md) — Universal entity model and automated code generation.
- [**Ingestion**](architecture/subsystems/ingestion-core.md) — Raw data fetching and connector management.
- [**Extraction & LLM Services**](architecture/subsystems/extraction-core.md) — AI-powered structured data extraction.
- [**Lens Layer**](architecture/subsystems/lenses.md) — Vertical-specific configuration and filtering.
- [**Web Frontend**](architecture/subsystems/web-frontend.md) — Next.js discovery interface.

## 📖 Reference

- [**CLI Reference**](reference/cli.md) — Command-line tools for engine operations.
- [**Configuration**](reference/configuration.md) — Guide to YAML configuration files.
- [**Module Index**](reference/module-index.md) — Detailed breakdown of internal Python modules.
- [**Data Model**](reference/data-model.md) — Database schema and JSONB structures.
- [**API Documentation**](reference/api.md) — (Planned) Backend API endpoints.

## 🛠️ Guides

- [**Operations**](operations/index.md) — Deployment, monitoring, and maintenance.
- [**How-to Guides**](howto/index.md) — Common tasks and extensions.
