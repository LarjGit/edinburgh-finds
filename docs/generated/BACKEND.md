# Backend Architecture (Python Engine)

**Generated:** 2026-02-06
**Status:** Auto-generated documentation

---

## Overview

The Python engine is the data processing backbone of Edinburgh Finds. It handles data ingestion from external sources, AI-powered extraction, multi-source deduplication and merge, and entity persistence. The engine is designed to be **completely vertical-agnostic** — all domain knowledge lives in lens YAML configurations.

---

## Project Structure

```
engine/
├── config/                    # Configuration files
│   ├── schemas/               # YAML schema definitions (single source of truth)
│   │   └── entity.yaml        # Entity model definition
│   ├── app.yaml               # Application config (lens defaults)
│   ├── extraction.yaml        # LLM model + trust levels
│   ├── sources.yaml           # API keys and connector configs (gitignored)
│   ├── sources.yaml.example   # Template for sources.yaml
│   ├── entity_model.yaml      # Entity model config
│   └── monitoring_alerts.yaml # Alerting configuration
│
├── ingestion/                 # Data fetching layer
│   ├── base.py                # BaseConnector abstract interface
│   ├── connectors/            # 6 source-specific connectors
│   │   ├── serper.py          # Serper web search API
│   │   ├── google_places.py   # Google Places API (v1)
│   │   ├── open_street_map.py # OSM Overpass API
│   │   ├── sport_scotland.py  # Sport Scotland WFS
│   │   ├── edinburgh_council.py # Edinburgh Council Open Data
│   │   └── open_charge_map.py # OpenChargeMap EV data
│   ├── cli.py                 # Ingestion CLI entry point
│   ├── deduplication.py       # Content-hash deduplication
│   ├── rate_limiting.py       # Per-connector rate limiting
│   ├── retry_logic.py         # Exponential backoff retry
│   ├── storage.py             # Raw data file persistence
│   ├── health_check.py        # Connector health monitoring
│   ├── summary_report.py      # Ingestion summary reports
│   └── logging_config.py      # Structured logging
│
├── extraction/                # Data transformation layer
│   ├── base.py                # BaseExtractor abstract interface
│   ├── extractors/            # 6 source-specific extractors
│   │   ├── serper_extractor.py
│   │   ├── google_places_extractor.py
│   │   ├── osm_extractor.py
│   │   ├── sport_scotland_extractor.py
│   │   ├── edinburgh_council_extractor.py
│   │   └── open_charge_map_extractor.py
│   ├── models/
│   │   └── entity_extraction.py # Pydantic extraction models
│   ├── llm_client.py          # Instructor + Anthropic Claude integration
│   ├── llm_cache.py           # LLM response caching
│   ├── llm_cost.py            # LLM cost tracking
│   ├── cost_report.py         # Extraction cost reporting
│   ├── deduplication.py       # Extraction-level deduplication
│   ├── merging.py             # Multi-source merge engine
│   ├── lens_integration.py    # Lens application integration
│   ├── module_extractor.py    # Module field extraction engine
│   ├── quarantine.py          # Quarantine management
│   ├── attribute_splitter.py  # Schema/discovered attribute splitting
│   ├── schema_utils.py        # Schema utility functions
│   ├── health.py              # Extraction health checks
│   ├── run.py                 # Batch extraction runner
│   ├── run_all.py             # Full extraction pipeline
│   ├── cli.py                 # Extraction CLI entry point
│   ├── config.py              # Extraction configuration
│   ├── logging_config.py      # Structured logging
│   └── utils/                 # Utility functions
│       ├── opening_hours.py   # Opening hours parsing
│       ├── category_mapper.py # Category mapping utilities
│       └── summary_synthesis.py # Rich text summary synthesis
│
├── orchestration/             # Pipeline coordination layer
│   ├── orchestrator.py        # Main orchestration loop
│   ├── planner.py             # Query analysis + connector selection
│   ├── query_features.py      # Query feature extraction
│   ├── registry.py            # Connector metadata registry
│   ├── adapters.py            # Connector-to-orchestrator bridge
│   ├── execution_context.py   # Immutable ExecutionContext (frozen dataclass)
│   ├── execution_plan.py      # Execution plan data structures
│   ├── orchestrator_state.py  # Mutable orchestrator state
│   ├── entity_finalizer.py    # Slug generation + entity assembly
│   ├── persistence.py         # Entity upsert to database
│   ├── extraction_integration.py # Extraction pipeline integration
│   ├── conditions.py          # Conditional execution logic
│   ├── types.py               # Shared type definitions
│   └── cli.py                 # Orchestration CLI entry point
│
├── lenses/                    # Lens system (vertical interpretation)
│   ├── loader.py              # Lens YAML loading and compilation
│   ├── validator.py           # 7 validation gates
│   ├── mapping_engine.py      # Generic mapping rule execution
│   ├── query_lens.py          # Query-time lens operations
│   ├── ops.py                 # Lens operations
│   ├── extractors/            # Generic field extractors
│   │   ├── numeric_parser.py  # Parse numeric values
│   │   ├── regex_capture.py   # Regex-based value extraction
│   │   └── normalizers.py     # Value normalization pipeline
│   ├── edinburgh_finds/
│   │   └── lens.yaml          # Edinburgh sports discovery lens
│   └── wine/
│       └── lens.yaml          # Wine discovery lens (skeleton)
│
├── modules/                   # Module system
│   └── validator.py           # Module structure validation
│
├── schema/                    # Schema generation system
│   ├── generate.py            # Generation orchestrator
│   ├── generator.py           # Core generator logic
│   ├── parser.py              # YAML schema parser
│   ├── core.py                # Core schema types
│   ├── types.py               # Schema type definitions
│   ├── entity.py              # Generated Python FieldSpecs
│   ├── cli.py                 # Schema CLI entry point
│   └── generators/            # Per-target generators
│       ├── pydantic_extraction.py
│       ├── prisma.py
│       ├── typescript.py
│       └── python_fieldspec.py
│
├── data/                      # Data storage
│   └── raw/                   # Raw ingestion payloads (per-source subdirectories)
│
├── inspect_db.py              # Database inspection utility
└── check_data.py              # Data validation utility
```

---

## Key Modules

### Ingestion (`engine/ingestion/`)

The ingestion layer fetches raw data from external sources.

**BaseConnector interface** (`base.py`):
```python
class BaseConnector(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    async def fetch(self, query: str) -> dict: ...

    @abstractmethod
    async def save(self, data: dict, source_url: str) -> str: ...

    @abstractmethod
    async def is_duplicate(self, content_hash: str) -> bool: ...
```

Each connector handles its own API authentication, pagination, and response parsing. Raw data is saved to `engine/data/raw/<source>/` and tracked in the `RawIngestion` table.

### Extraction (`engine/extraction/`)

The extraction layer transforms raw data into structured entities.

**BaseExtractor interface** (`base.py`):
```python
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, raw_data: dict, *, ctx: ExecutionContext) -> dict: ...

    @abstractmethod
    def validate(self, extracted: Dict) -> Dict: ...

    @abstractmethod
    def split_attributes(self, extracted: Dict) -> Tuple[Dict, Dict]: ...
```

**Critical contract:** Extractors emit ONLY schema primitives (entity_name, latitude, street_address, etc.) and raw observations (raw_categories, description). They must NEVER emit canonical dimensions or modules — that is the lens application's job.

### Orchestration (`engine/orchestration/`)

The orchestration layer coordinates the full pipeline.

**ConnectorSpec** (`registry.py`):
```python
@dataclass(frozen=True)
class ConnectorSpec:
    name: str
    connector_class: str
    phase: str              # "discovery" or "enrichment"
    cost_per_call_usd: float
    trust_level: float      # 0.0 to 1.0
    timeout_seconds: int
    rate_limit_per_day: int
```

The planner analyzes queries using lens vocabulary and selects connectors based on lens routing rules. The orchestrator enforces phase barriers (DISCOVERY -> STRUCTURED -> ENRICHMENT).

### Lens System (`engine/lenses/`)

The lens system provides all domain knowledge.

**Loader** (`loader.py`): Loads lens YAML, validates through 7 gates, computes content hash, and materializes a runtime contract.

**Mapping Engine** (`mapping_engine.py`): Executes mapping rules generically — applies regex patterns to raw observations and populates canonical dimensions.

**Validator** (`validator.py`): Enforces 7 validation gates:
1. Schema validation
2. Canonical reference integrity
3. Connector reference validation
4. Identifier uniqueness
5. Regex compilation
6. Smoke coverage validation
7. Fail-fast enforcement

### ExecutionContext (`orchestration/execution_context.py`)

Immutable carrier object threaded through the entire pipeline:

```python
@dataclass(frozen=True)
class ExecutionContext:
    lens_id: str
    lens_contract: dict
    lens_hash: Optional[str]
```

Created once at bootstrap, never mutated, carries the validated lens contract.

---

## CLI Entry Points

```bash
# Full orchestration pipeline
python -m engine.orchestration.cli run --lens edinburgh_finds "padel courts Edinburgh"

# Ingestion only (fetch raw data)
python -m engine.ingestion.cli run --query "padel courts Edinburgh"

# Extraction only (process raw data)
python -m engine.extraction.cli single <raw_ingestion_id>
python -m engine.extraction.cli source serper --limit 10

# Schema management
python -m engine.schema.generate --validate
python -m engine.schema.generate --all
```

---

## Error Handling Strategy

The engine uses a tiered error handling approach:

| Error Type | Behavior | Example |
|-----------|----------|---------|
| Lens validation failure | **Fail-fast at bootstrap** | Invalid regex pattern in lens.yaml |
| Connector failure | Isolated, partial results | Serper API timeout |
| Extraction rule failure | Log + skip field | Regex didn't match |
| LLM failure | Log + partial module | Claude API error |
| Merge/persistence failure | **Abort execution** | Database constraint violation |

Silent fallback behavior is explicitly forbidden.

---

## External Service Integrations

| Service | Library | Purpose |
|---------|---------|---------|
| Anthropic Claude | `instructor` + `anthropic` | Schema-bound LLM extraction |
| Serper API | `aiohttp` | Web search results |
| Google Places API v1 | `aiohttp` | Authoritative venue data |
| OSM Overpass | `aiohttp` | Geographic/facility data |
| Sport Scotland WFS | `aiohttp` | Official sports data |
| OpenChargeMap | `aiohttp` | EV charging data |
| Supabase PostgreSQL | `prisma` | Database operations |

---

## Related Documentation

- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Database:** [DATABASE.md](DATABASE.md)
- **Configuration:** [CONFIGURATION.md](CONFIGURATION.md)
- **Development:** [DEVELOPMENT.md](DEVELOPMENT.md)
