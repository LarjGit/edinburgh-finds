# API Reference

**Generated:** 2026-02-06
**Status:** Auto-generated documentation

---

## Overview

Edinburgh Finds does **not** currently expose a REST or GraphQL API. The frontend communicates with the database directly via Prisma Client in Next.js Server Components, and the engine operates via CLI commands.

This document covers:
1. **CLI Commands** — The primary interface for the data pipeline
2. **Prisma Query Patterns** — How the frontend queries entities
3. **Internal Python APIs** — Key module interfaces

---

## 1. CLI Commands

### Orchestration (Full Pipeline)

```bash
python -m engine.orchestration.cli run --lens <lens_id> "<query>"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--lens` | Yes | Lens identifier (e.g., `edinburgh_finds`) |
| `<query>` | Yes | Natural language search query |

**Example:**
```bash
python -m engine.orchestration.cli run --lens edinburgh_finds "padel courts in Edinburgh"
```

**What it does:**
1. Bootstraps lens contract (load + validate + hash)
2. Analyzes query features
3. Selects and executes connectors
4. Persists raw ingestion data
5. Runs source extraction
6. Applies lens mapping rules
7. Classifies entities
8. Deduplicates across sources
9. Merges into canonical entities
10. Persists final entities to database

### Ingestion Only

```bash
python -m engine.ingestion.cli run --query "<query>"
```

Fetches raw data from connectors without extraction or processing.

### Extraction Only

```bash
# Extract single raw ingestion record
python -m engine.extraction.cli single <raw_ingestion_id>

# Extract all records from a source
python -m engine.extraction.cli source <source_name> --limit <n>
```

### Schema Management

```bash
# Validate YAML schemas
python -m engine.schema.generate --validate

# Regenerate all derived schemas (Python, Prisma, TypeScript)
python -m engine.schema.generate --all
```

---

## 2. Prisma Query Patterns

The frontend uses Prisma's native array filters for faceted queries against PostgreSQL `TEXT[]` columns.

### Basic Entity Listing

```typescript
import prisma from "@/lib/prisma";

const entities = await prisma.entity.findMany({
  take: 10,
  select: {
    id: true,
    entity_name: true,
    entity_class: true,
    canonical_activities: true,
    canonical_place_types: true,
    modules: true,
  },
});
```

### Faceted Filtering

```typescript
import { buildFacetedWhere, FacetFilters } from "@/lib/entity-queries";

const filters: FacetFilters = {
  activities: ["padel", "tennis"],   // OR: padel OR tennis
  place_types: ["sports_facility"],  // AND: must be sports facility
  entity_class: "place",             // AND: must be a place
};

const entities = await prisma.entity.findMany({
  where: buildFacetedWhere(filters),
});
```

### Available Prisma Array Operators

| Operator | Semantics | Example |
|----------|-----------|---------|
| `has` | Array contains exact value | `{canonical_activities: {has: "padel"}}` |
| `hasSome` | Array contains at least one | `{canonical_activities: {hasSome: ["padel", "tennis"]}}` |
| `hasEvery` | Array contains all values | `{canonical_activities: {hasEvery: ["padel", "tennis"]}}` |
| `isEmpty` | Array is empty | `{canonical_activities: {isEmpty: true}}` |

### Pre-Built Query Examples

The `entity-queries.ts` module provides common query patterns:

```typescript
import { EXAMPLE_QUERIES } from "@/lib/entity-queries";

// Find padel venues
const padelWhere = EXAMPLE_QUERIES.padelVenues();

// Find sports centres
const centresWhere = EXAMPLE_QUERIES.sportsCentres();

// Find coaches
const coachesWhere = EXAMPLE_QUERIES.coaches();

// Find pay-and-play padel at sports centres
const complexWhere = EXAMPLE_QUERIES.payAndPlayPadelSportsCentres();
```

---

## 3. Internal Python APIs

### Connector Interface

```python
class BaseConnector(ABC):
    @property
    def source_name(self) -> str: ...

    async def fetch(self, query: str) -> dict: ...
    async def save(self, data: dict, source_url: str) -> str: ...
    async def is_duplicate(self, content_hash: str) -> bool: ...
```

### Extractor Interface

```python
class BaseExtractor(ABC):
    @property
    def source_name(self) -> str: ...

    def extract(self, raw_data: dict, *, ctx: ExecutionContext) -> dict: ...
    def validate(self, extracted: Dict) -> Dict: ...
    def split_attributes(self, extracted: Dict) -> Tuple[Dict, Dict]: ...
```

### Connector Registry

```python
from engine.orchestration.registry import CONNECTOR_REGISTRY, get_connector_instance

# Access metadata
spec = CONNECTOR_REGISTRY["serper"]
print(spec.trust_level)  # 0.75
print(spec.cost_per_call_usd)  # 0.01

# Create connector instance
connector = get_connector_instance("google_places")
await connector.db.connect()
results = await connector.fetch("padel Edinburgh")
await connector.db.disconnect()
```

### ExecutionContext

```python
from engine.orchestration.execution_context import ExecutionContext

ctx = ExecutionContext(
    lens_id="edinburgh_finds",
    lens_contract={...},  # Validated lens data
    lens_hash="abc123",
)
```

---

## Error Responses

### CLI Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Unknown connector: X` | Connector not in registry | Check `CONNECTOR_REGISTRY` keys |
| `Lens validation failed` | Invalid lens.yaml | Fix lens config and re-run |
| `ANTHROPIC_API_KEY not set` | Missing env var | Set API key |
| `Database connection failed` | Bad DATABASE_URL | Check connection string |

### Prisma Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `P2002: Unique constraint` | Duplicate slug | Expected during idempotent upsert |
| `P2025: Record not found` | Missing foreign key | Check referential integrity |

---

## Related Documentation

- **Backend:** [BACKEND.md](BACKEND.md) — Detailed module descriptions
- **Database:** [DATABASE.md](DATABASE.md) — Schema and model details
- **Configuration:** [CONFIGURATION.md](CONFIGURATION.md) — Environment variables
