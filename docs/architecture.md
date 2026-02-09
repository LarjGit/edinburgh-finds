# Edinburgh Finds - System Architecture

## Overview

Edinburgh Finds is an intelligent data ingestion and extraction system that transforms raw data from multiple sources into structured, searchable entities. The system uses a three-stage pipeline with AI-powered extraction and configurable domain-specific lenses.

## Core Architecture

### 1. Three-Stage Pipeline

The system follows a sequential three-stage architecture:

```
Raw Data Sources → Ingestion → Extraction → Structured Entities
     ↓               ↓           ↓              ↓
  Google Places   Raw Records  AI Analysis   Canonical
  OpenStreetMap   in Database  with Claude   Entities
  Serper API                                 in Database
  Council APIs
```

**Stage 1: Ingestion**
- Fetch raw data from multiple sources
- Store unprocessed payloads in `RawIngestion` table
- Support for 6+ connector types (Google Places, OSM, Serper, etc.)

**Stage 2: Extraction** 
- AI-powered entity extraction using Anthropic Claude
- Transform raw payloads into structured entity fields
- Apply lens-specific mapping rules and validation

**Stage 3: Orchestration**
- Intelligent coordination of ingestion and extraction
- Phase-based execution with dependency management
- Deduplication and conflict resolution

### 2. Lens System

Lenses are YAML configuration files that define domain-specific extraction rules and entity schemas. They provide vertical-specific knowledge without hardcoding business logic.

#### Lens Components

**Facets** - Define how dimensions are displayed and categorised:
```yaml
facets:
  activity:
    dimension_source: canonical_activities
    ui_label: "Activities"
    display_mode: tags
    show_in_filters: true
```

**Canonical Values** - Registry of standardised values with metadata:
```yaml
values:
  - key: padel
    facet: activity
    display_name: "Padel"
    description: "Racquet sport combining elements of tennis and squash"
    search_keywords: ["padel", "racket sport"]
```

**Mapping Rules** - Transform raw data into canonical values:
```yaml
mapping_rules:
  - id: map_padel_from_name
    pattern: "(?i)padel"
    canonical: "padel"
    confidence: 0.95
```

**Domain Modules** - Vertical-specific data structures:
```yaml
modules:
  sports_facility:
    field_rules:
      - rule_id: extract_court_count
        target_path: padel_courts.total
        extractor: regex_capture
        pattern: "(?i)(\\d+)\\s+courts?"
```

#### Lens Loading and Validation

The `LensRegistry` provides global access to loaded lenses with fail-fast validation:

```python
# Load all lenses from directory
LensRegistry.load_all(Path("engine/lenses"))

# Get specific lens
lens = LensRegistry.get_lens("edinburgh_finds")
```

Lenses are validated at load time using `validate_lens_config()` to ensure:
- Required fields are present
- Facet references are valid
- Mapping rules have proper structure
- Module definitions are well-formed

### 3. Orchestration Engine

The orchestration engine provides intelligent coordination of data ingestion with phase-based execution and dependency management.

#### Execution Phases

Connectors are organised into three sequential phases:

1. **DISCOVERY** - Initial data gathering (lowest specificity, highest coverage)
2. **STRUCTURED** - High-quality structured data sources  
3. **ENRICHMENT** - Additional details and refinement

Phase barriers enforce sequential execution whilst allowing parallelism within each phase.

#### Execution Plan

The `ExecutionPlan` class builds a DAG-lite structure with automatic dependency inference:

```python
plan = ExecutionPlan()
plan.add_connector(ConnectorSpec(
    name="google_places",
    phase=ExecutionPhase.STRUCTURED,
    trust_level=8,
    requires=["request.query"],
    provides=["context.structured_data"]
))
```

**Dependency Inference Rules:**
- Only `context.*` keys in `requires` create dependencies
- `request.*` and `query_features.*` keys do NOT create dependencies
- Dependencies are matched against `provides` lists of existing connectors
- Duplicate dependencies are automatically eliminated

#### Orchestrator

The `Orchestrator` class manages the execution control loop:

```python
orchestrator = Orchestrator(plan)
context = orchestrator.execute(request, query_features)
```

**Key Features:**
- Enforces strict phase ordering
- Manages shared `ExecutionContext` across all connectors
- Handles early stopping based on budget and confidence thresholds
- Provides deterministic conflict resolution for scalar fields

**Conflict Resolution:**
- **List fields**: Append (preserve all values)
- **Dict fields**: Merge by key
- **Scalar fields**: Higher trust wins; on tie, alphabetically last writer wins

#### Early Stopping Conditions

The orchestrator supports intelligent early stopping:

**RESOLVE_ONE Mode:**
- Stop when `confidence >= min_confidence` AND at least one entity accepted

**DISCOVER_MANY Mode:**
- Stop when `len(accepted_entities) >= target_entity_count`

**Budget Control:**
- Pre-phase check: Skip phase if estimated cost would exceed budget
- Post-phase check: Stop if budget already exhausted

### 4. Extraction Pipeline

The extraction system transforms raw ingestion payloads into structured entity fields using AI and lens-specific rules.

#### BaseExtractor Interface

All extractors implement the `BaseExtractor` abstract base class:

```python
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, raw_data: dict, *, ctx: ExecutionContext) -> dict:
        """Transform raw data into extracted entity fields."""
        pass
    
    @abstractmethod
    def validate(self, extracted: Dict) -> Dict:
        """Validate extracted fields against schema rules."""
        pass
    
    @abstractmethod
    def split_attributes(self, extracted: Dict) -> Tuple[Dict, Dict]:
        """Split into schema-defined and discovered attributes."""
        pass
```

#### Two-Phase Extraction

**Phase 1: Source Extractors**
- Return primitive fields only (entity_name, description, etc.)
- No lens-specific interpretation
- Source-agnostic field mapping

**Phase 2: Lens Mapping**
- Apply lens mapping rules to populate canonical dimensions
- Transform raw categories into standardised values
- Execute domain module field extraction rules

```python
# Phase 1: Source extractor
extracted = extractor.extract(raw_data, ctx=ctx)
# Result: {"entity_name": "Padel Club", "description": "..."}

# Phase 2: Lens mapping  
result = apply_lens_mapping(extracted, ctx)
# Result: {"entity_name": "Padel Club", "canonical_activities": ["padel"]}
```

#### Mapping Engine

The `mapping_engine.py` module applies lens mapping rules:

```python
def apply_lens_mapping(entity: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
    """Apply lens mapping rules to populate canonical dimensions."""
    
    # Get mapping rules from lens
    mapping_rules = ctx.lens.mapping_rules
    
    # Execute rules against entity fields
    dimensions = execute_mapping_rules(mapping_rules, entity)
    
    # Stabilise dimensions (dedupe + sort for determinism)
    dimensions = stabilize_canonical_dimensions(dimensions)
    
    # Merge into entity
    return {**entity, **dimensions}
```

**Default Source Fields:**
When `source_fields` is omitted from mapping rules, the engine searches these default fields:
- `entity_name`
- `description` 
- `raw_categories`
- `summary`
- `street_address`

#### Rich Text Extraction

Extractors can provide rich text descriptions for summary synthesis:

```python
def extract_rich_text(self, raw_data: Dict) -> List[str]:
    """Extract unstructured text for summary synthesis."""
    return ["Editorial summary...", "Review 1 text...", "Review 2 text..."]
```

#### Structured Logging

All extraction operations include structured logging with timing and metadata:

```python
extracted = extractor.extract_with_logging(
    raw_data=payload,
    record_id=record.id,
    confidence_score=0.85,
    ctx=execution_context
)
```

### 5. Execution Context

The `ExecutionContext` is an immutable carrier object that holds lens contract and metadata throughout the pipeline.

```python
@dataclass(frozen=True)
class ExecutionContext:
    """Immutable carrier for lens contract and metadata."""
    lens_id: str
    lens_contract: Dict[str, Any]  
    lens_hash: Optional[str] = None
```

**Key Properties:**
- Created exactly once during bootstrap
- Never mutated (frozen dataclass)
- Contains only plain serializable data
- Safe for logging, persistence, and replay
- No live loaders, registries, or mutable references

### 6. Type System

The system uses frozen dataclasses for thread-safe orchestration:

#### Core Types

```python
@dataclass(frozen=True)
class IngestRequest:
    """Immutable request object for ingestion operations."""
    ingestion_mode: IngestionMode
    query: str
    target_entity_count: Optional[int] = None
    min_confidence: Optional[float] = None
    budget_usd: Optional[float] = None
    persist: bool = False
    lens: Optional[str] = None

@dataclass(frozen=True) 
class GeoPoint:
    """Immutable geographic coordinate."""
    lat: float
    lng: float

@dataclass(frozen=True)
class BoundingBox:
    """Immutable geographic bounding box."""
    southwest: GeoPoint
    northeast: GeoPoint
```

#### Ingestion Modes

```python
class IngestionMode(Enum):
    RESOLVE_ONE = "resolve_one"    # Focus on single entity with high confidence
    DISCOVER_MANY = "discover_many" # Discover multiple matching entities
```

### 7. Data Flow

#### Complete Pipeline Flow

```
1. CLI Request
   ↓
2. Query Features Extraction
   ↓  
3. Execution Plan Generation
   ↓
4. Phase-Based Connector Execution
   ├── DISCOVERY Phase
   ├── STRUCTURED Phase  
   └── ENRICHMENT Phase
   ↓
5. Raw Data Ingestion
   ↓
6. AI-Powered Extraction
   ├── Phase 1: Source Extraction
   └── Phase 2: Lens Mapping
   ↓
7. Entity Validation & Storage
   ↓
8. Results Return
```

#### Context Flow

The `ExecutionContext` flows through the entire pipeline:

```
Bootstrap → Lens Loading → Context Creation → Orchestration → Extraction → Results
    ↓           ↓              ↓               ↓              ↓           ↓
  Config    Lens Registry  ExecutionContext  Shared State   AI Analysis  Entities
```

### 8. Configuration Management

#### Lens Resolution Order

1. CLI argument (`--lens`)
2. Environment variable (`LENS_ID`)
3. Application config (`engine/config/app.yaml`)
4. Dev fallback (`--allow-default-lens`)

#### Environment Variables

```bash
# Required
DATABASE_URL="postgresql://user:pass@localhost:5432/edinburgh_finds"
ANTHROPIC_API_KEY="sk-ant-api03-..."

# Optional
LENS_ID="edinburgh_finds"
GOOGLE_PLACES_API_KEY="your-key"
SERPER_API_KEY="your-key"
LOG_LEVEL="INFO"
```

### 9. Error Handling and Validation

#### Fail-Fast Validation

The system employs fail-fast validation at multiple levels:

**Lens Loading:**
- YAML syntax validation
- Schema structure validation  
- Reference integrity checking
- Duplicate key detection

**Extraction:**
- Field validation against schema rules
- Confidence threshold enforcement
- Required field checking

**Orchestration:**
- Budget validation
- Dependency resolution
- Phase ordering enforcement

#### Structured Error Types

```python
class LensConfigError(Exception):
    """Raised when lens configuration is invalid."""
    pass

class ValidationError(Exception):
    """Raised when validation fails."""
    pass

class ModuleValidationError(Exception):
    """Raised when module structure is invalid."""
    pass
```

### 10. Performance and Scalability

#### Deterministic Behaviour

The system ensures deterministic behaviour through:
- Lexicographic ordering of canonical dimensions
- Alphabetical connector execution within phases
- Trust-based conflict resolution with tie-breaking
- Reproducible lens contract hashing

#### Budget Control

- Pre-phase budget estimation
- Real-time budget tracking
- Early stopping when budget exhausted
- Per-connector cost estimation

#### Parallel Execution

The architecture supports future parallel execution:
- Within-phase parallelism (connectors can run concurrently)
- Phase barriers prevent cross-phase dependencies
- Immutable context prevents race conditions

### 11. Extensibility

#### Adding New Connectors

1. Implement connector interface
2. Define `ConnectorSpec` with phase, trust level, dependencies
3. Add to execution plan
4. Register in connector registry

#### Adding New Extractors

1. Extend `BaseExtractor` abstract class
2. Implement `extract()`, `validate()`, `split_attributes()` methods
3. Add source-specific field mapping logic
4. Register with extraction system

#### Adding New Lenses

1. Create `lens.yaml` configuration file
2. Define facets, values, mapping rules, modules
3. Place in `engine/lenses/<lens_id>/` directory
4. System auto-loads on startup

### 12. Testing Strategy

#### Test Doubles

The system provides `FakeConnector` for deterministic testing:

```python
fake_connector = FakeConnector(
    name="test_connector",
    spec=ConnectorSpec(...),
    on_execute=lambda ctx: ctx.candidates.append("test_entity")
)
```

#### Integration Testing

- End-to-end pipeline testing with real lenses
- Orchestration flow validation
- Extraction accuracy testing
- Performance benchmarking

#### Unit Testing

- Individual component testing
- Lens validation testing
- Mapping rule testing
- Conflict resolution testing

## Summary

Edinburgh Finds implements a sophisticated three-stage pipeline with intelligent orchestration, AI-powered extraction, and configurable domain-specific lenses. The architecture emphasises:

- **Modularity**: Clear separation between ingestion, extraction, and orchestration
- **Configurability**: YAML-driven lenses for domain-specific customisation
- **Determinism**: Reproducible behaviour through careful ordering and conflict resolution
- **Extensibility**: Plugin architecture for connectors, extractors, and lenses
- **Reliability**: Fail-fast validation and structured error handling
- **Performance**: Budget control, early stopping, and parallel execution support

The system successfully balances flexibility with reliability, enabling rapid deployment across different verticals whilst maintaining consistent behaviour and high-quality entity extraction.
