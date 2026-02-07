# Development Guide

**Generated:** 2026-02-06
**Status:** Auto-generated documentation

> **Important:** This project follows a strict development methodology defined in [`docs/development-methodology.md`](../development-methodology.md). Read that document before making changes.

---

## Development Philosophy

This project uses **Reality-Based Incremental Alignment** — a methodology designed to prevent architectural drift when working with AI agents. Key principles:

1. **Ultra-small work units** — 1-2 files max per change
2. **Reality-based planning** — Read actual code before planning
3. **Golden doc supremacy** — `system-vision.md` and `architecture.md` are authoritative
4. **Test-first development** — Red -> Green -> Refactor
5. **User-driven validation** — Human approval at start and end of each change

---

## Coding Standards

### Python (Engine)

- **Style:** Follow existing patterns in the codebase
- **Type hints:** Use throughout (enforced by Pydantic for models)
- **Docstrings:** Module-level and class-level docstrings required
- **Imports:** Standard library -> third-party -> local modules
- **Testing:** pytest with fixtures, marks for slow tests

### TypeScript (Frontend)

- **Style:** ESLint with Next.js config
- **Components:** React Server Components by default
- **Types:** Strict TypeScript (no `any` where avoidable)
- **Styling:** Tailwind CSS utility classes

### Naming Conventions

| Layer | Convention | Example |
|-------|-----------|---------|
| Python modules | `snake_case.py` | `entity_finalizer.py` |
| Python classes | `PascalCase` | `BaseExtractor` |
| Python functions | `snake_case` | `get_connector_instance()` |
| TypeScript files | `kebab-case.ts` | `entity-queries.ts` |
| React components | `PascalCase.tsx` | `EntityCard.tsx` |
| Database fields | `snake_case` | `entity_name` |
| YAML configs | `snake_case` | `lens.yaml` |

---

## Git Workflow

### Branch Strategy

- `main` — Production-ready code
- `develop` — Integration branch (if used)
- Feature branches from `main` for individual changes

### Commit Message Format

```
<type>(<scope>): <description>

<optional body>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Checklist

Every PR must pass the architectural validation checklist (see `.github/pull_request_template.md`):
- Engine purity checks
- Lens contract validation
- Module composition validation
- All tests pass
- New tests for new code

---

## Adding Features

### Adding a New Connector

1. Create `engine/ingestion/connectors/<name>.py` implementing `BaseConnector`
2. Register in `engine/orchestration/registry.py` with `ConnectorSpec`
3. Add adapter mapping in `engine/orchestration/adapters.py`
4. Create extractor in `engine/extraction/extractors/<name>_extractor.py`
5. Add connector config to `engine/config/sources.yaml`
6. Reference from lens routing rules in `lens.yaml`
7. Write tests in `tests/engine/`

### Adding a New Lens (Vertical)

1. Create `engine/lenses/<lens_id>/lens.yaml`
2. Define vocabulary, connector rules, mapping rules, canonical values, modules
3. Write lens validation tests in `tests/lenses/`
4. **No engine code changes required** (Invariant 3)

### Adding a New Entity Field

1. Edit `engine/config/schemas/entity.yaml`
2. Run `python -m engine.schema.generate --all`
3. Run `cd web && npx prisma migrate dev`
4. Update extractors to populate the new field
5. Update frontend to display it

### Adding a Module

1. Define module schema in `lens.yaml` under `modules:`
2. Add field_rules with extractors and source_fields
3. Add module_trigger to determine when the module is attached
4. Write tests against real fixture data

---

## Testing Strategy

### Test Organization

```
tests/
├── engine/
│   ├── test_purity.py              # Engine purity (Invariant 1)
│   ├── test_lens_membership.py     # Lens membership tests
│   ├── config/
│   │   └── test_entity_model_purity.py
│   ├── extraction/
│   │   ├── test_base.py            # BaseExtractor contract
│   │   ├── test_merging.py         # Multi-source merge
│   │   ├── test_lens_integration.py
│   │   ├── test_module_extractor.py
│   │   └── extractors/             # Per-extractor tests
│   ├── orchestration/
│   │   ├── test_planner.py         # Query planning
│   │   ├── test_registry.py        # Connector registry
│   │   ├── test_adapters.py        # Connector adapters
│   │   ├── test_persistence.py     # Entity persistence
│   │   ├── test_entity_finalizer.py
│   │   ├── test_deduplication.py
│   │   └── test_end_to_end_validation.py
│   └── lenses/
│       ├── test_mapping_engine.py   # Mapping rule execution
│       ├── test_validator_gates.py  # Lens validation
│       └── extractors/             # Generic extractor tests
├── lenses/
│   ├── test_loader.py              # Lens loading
│   ├── test_validator.py           # Lens validation
│   ├── test_edinburgh_finds_lens.py
│   └── test_wine_discovery_lens.py
├── modules/
│   └── test_composition.py         # Module composition
├── query/
│   └── test_prisma_array_filters.py
└── migration/
    └── test_migrate_listing_to_entity.py
```

### Test Categories

| Category | Command | Purpose |
|----------|---------|---------|
| All tests | `pytest` | Full suite |
| Fast tests | `pytest -m "not slow"` | Quick iteration |
| Purity | `pytest tests/engine/test_purity.py` | Engine purity |
| Extraction | `pytest tests/engine/extraction/` | All extraction |
| Orchestration | `pytest tests/engine/orchestration/` | Pipeline tests |
| Lens validation | `pytest tests/lenses/test_validator.py` | Lens config |
| Coverage | `pytest --cov=engine --cov-report=html` | HTML report |

### Test Patterns

```python
# Use @pytest.mark.slow for tests > 1 second
@pytest.mark.slow
def test_full_pipeline_integration():
    ...

# Use fixtures for common setup (see conftest.py files)
@pytest.fixture
def mock_ctx():
    return ExecutionContext(lens_id="test", lens_contract={}, lens_hash="test")

# Reference architectural principles in test names
def test_extractor_outputs_only_primitives_and_raw_observations():
    """Validates architecture.md 4.2 Phase 1 contract"""
    ...
```

---

## Debugging Tips

### Database Inspection

```bash
# Prisma Studio — visual database browser
cd web && npx prisma studio

# Python database inspection
python engine/inspect_db.py
python engine/check_data.py
```

### Extraction Debugging

```bash
# Extract a single raw ingestion record
python -m engine.extraction.cli single <raw_ingestion_id>

# Check extraction logs
# Extractors use structured logging (see extraction/logging_config.py)
```

### Common Gotchas

1. **Never edit generated files** — Files with "DO NOT EDIT" headers are auto-generated from YAML. Edit the YAML source instead.

2. **Entity class vs domain types** — Use `entity_class` (place/person/organization/event/thing), never domain terms like "Venue".

3. **Extraction boundary** — Extractors emit ONLY primitives. Canonical dimensions come from lens application.

4. **ExecutionContext threading** — All extractors must accept `ctx: ExecutionContext` parameter.

5. **Schema changes require regeneration** — After editing `entity.yaml`, run `python -m engine.schema.generate --all`.

6. **Lens validation is strict** — Invalid lens configs fail at bootstrap, not at runtime.

---

## Development Workflow Summary

```
1. Read docs/progress/audit-catalog.md
2. Select next catalog item (Decision Logic)
3. Read actual code (Code Reality Audit)
4. Write micro-plan (half page max)
5. USER CHECKPOINT 1: Approve plan
6. Write failing test (RED)
7. Implement minimum code (GREEN)
8. Refactor
9. Validate against golden docs
10. USER CHECKPOINT 2: Validate result
11. Commit with conventional message
12. Update catalog
```

---

## Related Documentation

- **Methodology:** [`docs/development-methodology.md`](../development-methodology.md) — Full methodology specification
- **Audit Catalog:** [`docs/progress/audit-catalog.md`](../progress/audit-catalog.md) — Current progress
- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Backend:** [BACKEND.md](BACKEND.md)
- **Frontend:** [FRONTEND.md](FRONTEND.md)
