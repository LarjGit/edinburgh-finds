# Edinburgh Finds

A vertical-agnostic data harmonization engine and discovery platform designed to surface structured entities (places, people, organizations) through a "Lens" based architecture.

## Overview
Edinburgh Finds is a high-purity data processing system that ingests raw data from multiple sources (Google Places, OpenStreetMap, specialized government APIs), extracts structured information using LLMs (Anthropic, Instructor), and harmonizes it into a Universal Entity Model. 

The system is strictly divided into an **Engine** (vertical-agnostic) and **Lenses** (vertical-specific), allowing the same core infrastructure to power diverse discovery experiences (e.g., Wine Discovery, Sports Facility Finder, Local Services).

## Technology Stack

### Backend (Engine)
- **Language**: Python 3.12
- **ORM**: Prisma (prisma-client-py)
- **Validation**: Pydantic
- **LLM Integration**: Anthropic (Claude), Instructor
- **Data Ingestion**: Aiohttp (Async HTTP), Overpass QL (OSM), ArcGIS/WFS
- **Database**: PostgreSQL (Production), SQLite (Development)

### Frontend (Web)
- **Framework**: Next.js 15+ (React 19)
- **Styling**: Tailwind CSS, Tailwind Merge
- **Icons**: Lucide React
- **Language**: TypeScript
- **State/Query**: Prisma (prisma-client-js)

### Infrastructure & Tooling
- **CI/CD**: GitHub Actions
- **Testing**: Pytest
- **Linting**: ESLint
- **Workflow Management**: Conductor

## Getting Started
- [Architecture Overview](architecture/overview.md)
- [Development Setup](howto/development-setup.md)
- [Testing Guide](howto/testing.md)
- [Subsystem Documentation](architecture/subsystems/)

## Documentation Map
- **Architecture**: System design, C4 diagrams, and subsystem details.
- **Reference**: API endpoints and data models.
- **How-To**: Setup, deployment, and development guides.
- **Operations**: Monitoring, troubleshooting, and maintenance.

---
*Evidence: web/package.json, engine/requirements.txt, docs/architecture/subsystems/engine.md*
