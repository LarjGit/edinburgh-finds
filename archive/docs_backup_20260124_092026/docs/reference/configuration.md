# Configuration Reference

This document details the configuration surfaces of the Edinburgh Finds platform.

## Environment Variables (`.env`)

The system relies on environment variables for credentials and infrastructure settings.

### Database
| Variable | Description | Default / Example |
|----------|-------------|-------------------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/db` |

### External APIs
| Variable | Description | Required? |
|----------|-------------|-----------|
| `ANTHROPIC_API_KEY` | Key for Anthropic Claude (LLM Extraction) | **Yes** |
| `GOOGLE_PLACES_API_KEY` | Key for Google Places API (Ingestion) | No (if not using Google) |
| `SERPER_API_KEY` | Key for Serper.dev API (Search Ingestion) | No (if not using Serper) |

### Runtime
| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Python logging level (DEBUG, INFO, WARN) | `INFO` |
| `NODE_ENV` | Node.js environment | `development` |

## Engine Configuration (`engine/config/`)

The behavior of the extraction engine and the domain model is controlled by YAML files in `engine/config/`.

### `entity_model.yaml`
**Purpose**: Defines the UNIVERSAL, VERTICAL-AGNOSTIC entity model.
**Location**: `engine/config/entity_model.yaml`

This file enforces "Engine Purity" by defining:
1.  **Entity Classes**: The fundamental types (Place, Person, Organization, Event).
2.  **Dimensions**: Opaque arrays used for faceted filtering (e.g., `canonical_activities`, `canonical_place_types`). These are stored as `text[]` in Postgres and interpreted by the Lens layer.
3.  **Modules**: Reusable data schemas (e.g., `location`, `contact`, `hours`).

**Evidence**: `engine/config/entity_model.yaml`

### `extraction.yaml`
**Purpose**: Configures the extraction pipeline behavior.
**Location**: `engine/config/extraction.yaml`

Controls:
- LLM model selection (e.g., `claude-3-opus-20240229`).
- Retry policies and confidence thresholds.
- Batch sizes and concurrency limits.

## Database Schema (`engine/schema.prisma`)

The database schema is the source of truth for persistence. It is managed via Prisma.
See [Data Model](data-model.md) for details.
