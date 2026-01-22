# Edinburgh Finds

> **Status:** Active Development
> **Architecture:** Vertical-Agnostic Extraction Engine + Lens-Based Frontend

Edinburgh Finds is a local discovery platform built on a dual-stack architecture: a Python-based data ingestion and extraction engine (ETL) and a Next.js frontend. It features a "Universal Entity" model where vertical-specific logic (e.g., "Sports", "Wine", "Pottery") is defined via configuration "Lenses" rather than hardcoded schemas.

---

## ⚡ Tech Stack Snapshot

| Layer | Technology | Key Libraries/Notes |
| :--- | :--- | :--- |
| **Frontend** | **Next.js 16.1** (App Router) | React 19, Tailwind CSS v4, Lucide React |
| **Backend / ETL** | **Python 3.12+** | `asyncio`, `aiohttp`, `pydantic`, `instructor` |
| **Database** | **PostgreSQL** (Dev & Prod) | **Prisma ORM** (v5/v7) used by *both* Python & JS |
| **AI / LLM** | **Anthropic Claude** | Via `instructor` for structured extraction |
| **Schema** | **YAML-First** | Custom generator (`engine.schema`) creates Prisma/Pydantic/TS artifacts |

---

## 🛠 Environment Variables

Copy `.env.example` to `.env` in the root directory.

| Variable | Required? | Description | Default / Example |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Yes** | Connection string for Prisma (PostgreSQL). | `postgresql://user:password@localhost:5432/edinburgh_finds?schema=public` |
| `ANTHROPIC_API_KEY` | **Yes** | For LLM-based extraction. | `sk-ant-...` |
| `GOOGLE_PLACES_API_KEY` | No | For Google Places connector. | |
| `SERPER_API_KEY` | No | For Serper (Google Search) connector. | |
| `LOG_LEVEL` | No | Logging verbosity. | `INFO` |
| `NODE_ENV` | No | Environment mode. | `development` |

---

## 🚀 Quick Start (AI Agent & User Guide)

### 1. Install Dependencies

**Frontend (Node.js):**
```bash
cd web
npm install
```

**Engine (Python):**
```bash
# Recommended: Create a virtual environment first
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install -r engine/requirements.txt
```

### 2. Database Initialization (CRITICAL)

The project uses a unified schema. You must generate clients for both languages.

```bash
# 1. Generate Prisma Client for Python and JavaScript
npx prisma generate --schema=web/prisma/schema.prisma

# 2. Apply migrations to PostgreSQL database
npx prisma migrate dev --schema=web/prisma/schema.prisma
```

### 3. Run the Application

**Start the Web UI:**
```bash
cd web
npm run dev
# Access at http://localhost:3000
```

---

## 🧠 User Journeys & Workflows

### A. Schema Management (The "Source of Truth")
**⚠️ DO NOT EDIT `schema.prisma` MANUALLY.**
The project uses a **YAML-first** approach.

1.  **Edit** YAML definitions in `engine/config/schemas/*.yaml`.
2.  **Generate** artifacts (Prisma, Pydantic, TS):
    ```bash
    python -m engine.schema.generate
    ```
3.  **Migrate** the database:
    ```bash
    npx prisma migrate dev --name <migration_name> --schema=web/prisma/schema.prisma
    ```

### B. Data Ingestion (ETL Stage 1)
Run individual connectors to fetch raw data.
```bash
# Example: Run Manual OSM Ingestion
python engine/run_osm_manual.py

# Example: Run Serper Connector
python engine/scripts/run_serper_connector.py
```

### C. Extraction (ETL Stage 2)
Process raw data into structured Entities using Lenses.
```bash
# Run the lens-aware extraction pipeline
python engine/scripts/run_lens_aware_extraction.py
```

### D. Extraction Maintenance
Manage the extraction queue and retry failed jobs.
```bash
# Retry failed extractions
python -m engine.extraction.cli --retry-failed --max-retries 3
```

---

## 📂 Project Structure Map

*   **`engine/`**: Python backend.
    *   `config/schemas/`: **SSOT** YAML definitions for entities.
    *   `extraction/`: Core logic for LLM processing and entity cleaning.
    *   `ingestion/`: Connectors for external APIs (Google, OSM, etc.).
    *   `scripts/`: Entry points for running ETL jobs.
*   **`web/`**: Next.js frontend.
    *   `app/`: App Router pages.
    *   `prisma/`: Contains `schema.prisma` and SQLite DB file.
    *   `lib/`: Shared utilities (Prisma client instance).
*   **`lenses/`**: Configuration for different verticals (e.g., `edinburgh_finds`, `wine_discovery`).
    *   Defines facets, categories, and UI mapping rules.

---

## ⚠️ Key Architectural Constraints

1.  **Prisma Client Parity**: Both `web` (JS) and `engine` (Python) must use compatible Prisma Client versions. Always run `prisma generate` after schema changes.
2.  **Engine Purity**: The `engine/` code does not know about "Sports" or "Wine". It only knows "Entities" and "Dimensions". Domain logic lives in `lenses/`.
3.  **Postgres Native**: The app relies on native PostgreSQL features (arrays, GIN indexes, JSONB). Ensure your development database is PostgreSQL 14+.
