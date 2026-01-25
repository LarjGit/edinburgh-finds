Audience: Developers

# Module Index

This index provides a comprehensive list of the core Python modules and their primary responsibilities within the engine.

## 🧠 Orchestration (`engine/orchestration/`)

| Module | Responsibility |
| :--- | :--- |
| `orchestrator.py` | Top-level execution manager for discovery runs. |
| `execution_plan.py` | Logic for determining the sequence of ingestion and extraction tasks. |
| `query_features.py` | Lens-aware query expansion and filtering. |

## 🛠️ Schema & Model (`engine/schema/`)

| Module | Responsibility |
| :--- | :--- |
| `core.py` | Universal Entity Model definitions. |
| `entity.py` | Pydantic models for entity validation. |
| `generator.py` | Orchestrates the generation of Prisma and TypeScript schemas. |
| `generators/` | specific targets: `prisma.py`, `typescript.py`, `pydantic_extraction.py`. |

## 📥 Ingestion (`engine/ingestion/`)

| Module | Responsibility |
| :--- | :--- |
| `base.py` | Abstract base classes for data connectors. |
| `storage.py` | Management of the `RawIngestion` database table. |
| `rate_limiting.py`| Token-bucket implementation for external API respect. |
| `connectors/` | External integrations: `open_street_map.py`, `google_places.py`, `serper.py`, etc. |

## 🧬 Extraction (`engine/extraction/`)

| Module | Responsibility |
| :--- | :--- |
| `base.py` | Core extraction logic and LLM prompt templates. |
| `llm_client.py` | Wrapper for Anthropic/OpenAI API calls with retry logic. |
| `llm_cache.py` | Database-backed caching of LLM responses to reduce costs. |
| `entity_classifier.py`| Pre-extraction check to ensure raw data matches the Lens. |
| `deduplication.py` | Logic for linking records from different sources to the same entity. |

## 🔍 Lens Layer (`engine/lenses/`)

| Module | Responsibility |
| :--- | :--- |
| `loader.py` | Logic for parsing and validating `lens.yaml` files. |
| `ops.py` | Lens-specific filtering and data transformation. |
| `validator.py` | Ensures a Lens adheres to the "Engine Purity" constraints. |

## 🌐 Web Backend/API (`web/lib/`)

| Module | Responsibility |
| :--- | :--- |
| `prisma.ts` | Shared Prisma client instance. |
| `lens-query.ts` | Server-side logic for executing Lens-aware searches. |
| `entity-queries.ts`| Optimized database queries for entity retrieval. |
