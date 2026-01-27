# Coding Conventions

**Analysis Date:** 2026-01-27

## Naming Patterns

**Files (TypeScript/JavaScript):**
- kebab-case: `lens-query.ts`, `entity-queries.ts`, `entity-helpers.ts`
- Pattern: Lowercase with hyphens for multi-word names
- Test files: `{name}.test.ts` (e.g., `utils.test.ts`, `lens-query.test.ts`)

**Files (Python):**
- snake_case: `entity_classifier.py`, `deduplication.py`, `logging_config.py`
- Pattern: Lowercase with underscores for multi-word names
- Test files: `test_{module_name}.py` (e.g., `test_adapters.py`, `test_entity_model_purity.py`)

**Functions (TypeScript):**
- camelCase: `parseAttributesJSON()`, `formatAttributeKey()`, `queryByFacet()`
- Prefix conventions:
  - Query builders: `query*()` (e.g., `queryByFacet()`, `queryByValue()`, `queryByGrouping()`)
  - Formatters: `format*()` (e.g., `formatAttributeKey()`, `formatAttributeValue()`)
  - Parsers: `parse*()` (e.g., `parseAttributesJSON()`)

**Functions (Python):**
- snake_case: `normalize_for_json()`, `extract_rich_text()`, `split_attributes()`
- Private functions: `_prefix_` (e.g., `_normalize_id()`, `_calculate_name_similarity()`, `_distance_to_score()`)
- Abstract methods: `@abstractmethod` decorator with underscore prefix not used (e.g., `source_name`, `extract()`, `validate()`)

**Variables (TypeScript):**
- camelCase: `selectedValues`, `dimensionSource`, `extracted`, `raw_data`
- Constants: UPPER_SNAKE_CASE: `REQUIRED_DIMENSIONS`, `FORBIDDEN_VERTICAL_KEYWORDS`
- Interface properties: camelCase

**Variables (Python):**
- snake_case: `selected_values`, `dimension_source`, `extracted`, `raw_data`
- Constants: UPPER_SNAKE_CASE: `REQUIRED_DIMENSIONS`, `FORBIDDEN_VERTICAL_KEYWORDS`, `CONNECTOR_REGISTRY`
- Dataclass attributes: snake_case

**Types (TypeScript):**
- PascalCase: `FacetFilter`, `ConnectorAdapter`, `ExecutionContext`
- Interface naming: Descriptive, no `I` prefix: `FacetFilter`, `QueryFeatures` not `IFacetFilter`
- Type exports with `type` keyword: `export type FacetFilter = {}`

**Types (Python):**
- PascalCase for classes: `BaseExtractor`, `ConnectorSpec`, `Deduplicator`, `MatchResult`
- Dataclass naming: `@dataclass` for immutable specs: `ConnectorSpec` marked `frozen=True`
- Enum-like classes: Use dataclass with frozen=True for immutable metadata

**Schema/Model Names:**
- Universal (engine-agnostic): `entity_class`, `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`
- Never domain-specific: No "venue", "padel", "wine", "restaurant" in engine code
- Module types: Lowercase with underscore: `core`, `location`, `contact`, `hours`, `amenities`, `time_range`

## Code Style

**Formatting:**
- Language: TypeScript uses ESLint (Next.js default config) + eslint-config-next
- Language: Python uses standard formatting (no explicit formatter configured)
- EditorConfig: Next.js projects follow ESLint defaults
- Line length: Not explicitly restricted (ESLint defaults)

**Linting:**
- TypeScript/JavaScript: ESLint with `eslint-config-next` and `eslint-config-next/core-web-vitals`
- Python: No linter configured in codebase (pytest used for testing only)
- Run command (web): `npm run lint` (via ESLint)

**Import Organization:**

Order (TypeScript):
1. External packages: `import { ... } from '@prisma/client'`
2. Internal utilities: `import { cn } from '@/lib/utils'`
3. Local imports: `import { queryByFacet } from './lens-query'`

Order (Python):
1. Standard library: `import asyncio`, `import time`, `from abc import ABC`
2. Third-party: `from pydantic import ...`, `from prisma import Prisma`
3. Local: `from engine.extraction.base import BaseExtractor`
4. Relative: Avoid; use absolute imports from package root

**Path Aliases:**
- TypeScript: `@/*` maps to `./` (web root)
- Usage: `import { EntityView } from '@/lib/types'`
- Python: Absolute imports from package root `engine.` or `web.` (no relative imports)

## Error Handling

**TypeScript Patterns:**
- Try-catch for async operations: Standard try-catch blocks
- Return empty objects on parse failure: `parseAttributesJSON()` returns `{}` on invalid JSON
- Null coalescing for optional values: Check `if (!value)` before processing
- Logging: `console.warn()` for recoverable errors

**Python Patterns:**
- Exception re-raising with logging: `extract_with_logging()` logs then re-raises
  ```python
  try:
      extracted = self.extract(raw_data)
  except Exception as e:
      log_extraction_failure(...)
      raise  # Re-raise after logging
  ```
- Dataclass validation: Pydantic models or manual validation in extractors
- Deduplication errors: Captured in MatchResult dataclass with confidence scores
- JSON normalization fallback: Non-serializable objects → `str(data)` fallback

## Logging

**Framework:** Python uses structured logging module (JSON formatter)

**Location:** `engine/extraction/logging_config.py` provides:
- `ExtractionLogFormatter`: JSON-formatted logs with structured fields
- `get_extraction_logger()`: Global logger access
- `setup_extraction_logger()`: Initial setup

**Patterns:**
- Extraction events logged with: source, record_id, extractor name, duration, fields_extracted
- Example: `log_extraction_start()`, `log_extraction_success()`, `log_extraction_failure()`
- Fields: `timestamp`, `level`, `message`, `logger`, `source`, `record_id`, `extractor`, `duration_seconds`, `fields_extracted`, `confidence_score`

**TypeScript:** Uses `console.warn()` for warnings (e.g., JSON parse failures)

## Comments

**When to Comment:**

TypeScript:
- JSDoc for public functions and interfaces (required)
- Explain "why", not "what" - code shows what, comment shows why
- Document complex query semantics in lens-query.ts
- Semantic examples: Show what queries match and don't match

Python:
- Docstrings for all classes and public methods (Google/NumPy style)
- Module-level docstrings explaining purpose
- Inline comments for complex matching logic (Deduplicator)
- No comments for obvious code

**JSDoc/TSDoc (TypeScript):**
```typescript
/**
 * Query by facet using Prisma array filters.
 *
 * @param filter - Facet filter configuration
 * @returns Prisma where clause for array filtering
 *
 * @example
 * queryByFacet({
 *   facet: "activity",
 *   dimensionSource: "canonical_activities",
 *   selectedValues: ["padel", "tennis"],
 *   mode: "OR"
 * })
 */
```

**Docstrings (Python):**
```python
def find_match(self, entity1: Dict[str, Any], entity2: Dict[str, Any]) -> MatchResult:
    """
    Find if two entities are duplicates using hierarchical matching.

    Args:
        entity1: First entity dict with optional external_id, slug, name, lat, lng
        entity2: Second entity dict

    Returns:
        MatchResult with is_match, confidence, and reason fields
    """
```

## Function Design

**Size Guidelines:**
- Keep functions focused (single responsibility)
- Extractors: ~100-150 lines (extract, validate, split_attributes)
- Query builders: ~10-30 lines
- Utility functions: <50 lines

**Parameters:**
- Prefer positional for required params
- Keyword-only for optional params (Python: use `*,` separator)
- TypeScript: Use interfaces for complex parameter objects

**Return Values:**
- Return dict/interface for structured data (e.g., MatchResult dataclass)
- Return empty dict `{}` on error (TypeScript parsing)
- Return tuple for multiple outputs (e.g., `split_attributes()` returns `(attributes, discovered)`)
- Use dataclass for multi-value returns with named fields

## Module Design

**Exports (TypeScript):**
```typescript
// Query functions
export function queryByFacet(filter: FacetFilter): Record<string, any> { }
export function queryByValue(dimension: string, value: string): Record<string, any> { }

// Types
export interface FacetFilter { }
```

**Exports (Python):**
```python
# Classes
class BaseExtractor(ABC):
    pass

# Functions
def normalize_for_json(data: Any) -> Any:
    pass

# No wildcard imports in engine code
```

**Barrel Files:**
- TypeScript: `web/lib/__init__.ts` not used; import directly from modules
- Python: `engine/extraction/__init__.py` minimal (used for public API only)

**Visibility:**
- TypeScript: No explicit private modifiers; use `_` prefix for private helpers in module scope
- Python: Use `_` prefix for private methods/functions; classes are public unless prefixed

## Vertical Purity

**Engine Code (Python):**
- NEVER hardcode vertical-specific terms: "Padel", "Wine", "Tennis", "Court"
- NEVER use domain-specific types: "Venue", "Club", "Facility"
- NEVER add domain modules to engine code
- Use universal `entity_class` (place, person, organization, event, thing)
- Use universal dimensions: `canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`
- Domain logic belongs in Lens YAML configs, NOT in engine code

**Web Code (TypeScript):**
- Can reference vertical specifics in UI context
- But query layer uses universal dimensions only
- Example: Display "Padel Courts" (UI), but query uses `canonical_place_types: ["sports_centre"]` (data layer)

## Type Safety

**TypeScript:**
- Strict mode enabled in tsconfig.json
- Use type interfaces for all complex objects
- Avoid `any` type; use specific types or generics
- Use `Record<string, any>` only when structure unknown

**Python:**
- Type hints required for all function signatures
- Use `Dict[str, Any]` for untyped dicts
- Use `Optional[T]` for nullable values
- Dataclasses preferred for structured return values

---

*Convention analysis: 2026-01-27*
