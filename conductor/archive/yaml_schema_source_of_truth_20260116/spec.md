# Track: YAML Schema - Single Source of Truth

## Status
**Ready for Implementation**

## Problem Statement

The current architecture suffers from **schema drift** between three separate schema definitions:

1. **Prisma Schema** (`engine/schema.prisma`) - Database structure
2. **Python Schema** (`engine/schema/listing.py`, `venue.py`) - Extraction field definitions
3. **TypeScript Types** (`web/` app) - Frontend types

These are maintained **manually and independently** with no synchronization mechanism. This creates:

- ❌ **High drift risk** - Fields can get out of sync silently
- ❌ **Manual maintenance burden** - Every schema change requires updating 3 places
- ❌ **No validation** - No automated checks that schemas match
- ❌ **Blocks horizontal scaling** - Adding new entity types (WINERY) requires code changes
- ❌ **No single source of truth** - Unclear which schema is "correct"

### Current State Example

Adding a new core field requires:
1. Edit `schema.prisma` → Run migration
2. Edit `listing.py` → Update Python FieldSpecs
3. Edit TypeScript types → Update frontend
4. Hope nothing was missed! 🤞

## Vision

**Single YAML source generates all schemas automatically.**

```yaml
# engine/config/schema.yaml (SINGLE SOURCE OF TRUTH)
entities:
  listing:
    description: "Base entity with universal fields"
    fields:
      - name: entity_name
        type: string
        nullable: false
        description: "Official name of the entity"
        search_keywords: [name, called, named]
```

From this YAML:
- ✅ Generate `schema.prisma` (database)
- ✅ Generate `listing.py` (Python FieldSpecs)
- ✅ Generate TypeScript types (frontend)
- ✅ Validate all schemas match source
- ✅ Add new entity types without code changes

## Goals

### Must-Have (Core Track)

1. **YAML Schema Format**: Design comprehensive YAML schema that captures all field metadata
2. **Prisma Generator**: YAML → Prisma schema generation
3. **Python Generator**: YAML → Python FieldSpec generation
4. **Validation**: Automated tests that generated schemas match YAML source
5. **Migration**: Convert existing `listing.py` fields → YAML
6. **Documentation**: Clear guide for adding new entity types

### Nice-to-Have (Future Extensions)

7. **TypeScript Generator**: YAML → TypeScript type generation
8. **CLI Tool**: `python -m engine.schema.generate --validate`
9. **Schema Versioning**: Track schema changes over time
10. **Domain-Specific Schemas**: Easy addition of `winery.yaml`, `restaurant.yaml`

## Success Criteria

1. ✅ Single YAML file defines all core fields (entity_name, address, location, contact)
2. ✅ Generate Prisma schema matches current `schema.prisma` exactly
3. ✅ Generate Python FieldSpecs matches current `listing.py` exactly
4. ✅ Validation tests fail if schemas drift from YAML
5. ✅ Can add new entity-specific schema (e.g., `winery.yaml`) without code changes
6. ✅ Documentation enables non-developers to add entity types
7. ✅ All existing tests pass with generated schemas

## Non-Goals (Explicitly Out of Scope)

- ❌ Relationship schema definition (ListingRelationship) - keep manual for now
- ❌ Migration of web app types (TypeScript generation is nice-to-have)
- ❌ Schema evolution/migration tooling (just generation)
- ❌ Runtime schema validation (application-level validation separate concern)

## Architecture

### YAML Schema Structure

```yaml
# engine/config/schemas/base.yaml
schema_version: "1.0"
description: "Core fields shared by all entity types"

fields:
  # Each field has rich metadata
  - name: entity_name
    type: string
    nullable: false
    required: true
    indexed: true
    unique: false
    description: "Official name of the entity"
    search_category: identity
    search_keywords: [name, called, named]

  - name: latitude
    type: float
    nullable: true
    description: "WGS84 Latitude coordinate (decimal degrees)"
    validation:
      min: -90
      max: 90

  - name: attributes
    type: json
    nullable: true
    description: "Validated domain-specific attributes (JSON blob)"
    exclude_from_extraction: false

  - name: discovered_attributes
    type: json
    nullable: true
    description: "Raw AI-extracted attributes awaiting validation"
```

```yaml
# engine/config/schemas/venue.yaml (domain-specific)
schema_version: "1.0"
extends: base
description: "Venue-specific fields for sports facilities"

fields:
  - name: tennis_summary
    type: string
    nullable: true
    description: "Short description of tennis facilities"
    search_category: racquet_sports
    search_keywords: [tennis, courts]
    storage: json  # Goes into 'attributes' JSON, not separate column
```

### Generation Pipeline

```
YAML Source
    ↓
┌───────────────┐
│ Schema Parser │ ← Parse & validate YAML
└───────────────┘
    ↓
┌───────────────────────────────────┐
│ Generator Registry                │
│  - PrismaGenerator               │
│  - PythonFieldSpecGenerator      │
│  - TypeScriptGenerator (future)  │
└───────────────────────────────────┘
    ↓
Generated Artifacts
  ├─ schema.prisma (database)
  ├─ listing.py (Python)
  └─ types.ts (TypeScript - future)
```

### File Organization

```
engine/
├── config/
│   └── schemas/
│       ├── base.yaml           ← Core universal fields
│       ├── venue.yaml          ← Sports venue fields
│       └── winery.yaml         ← Wine estate fields (future)
│
├── schema/
│   ├── parser.py               ← Parse YAML schemas
│   ├── generators/
│   │   ├── prisma.py           ← Generate .prisma
│   │   ├── python_fieldspec.py ← Generate listing.py
│   │   └── typescript.py       ← Generate .ts (future)
│   ├── validator.py            ← Validate generated vs source
│   └── cli.py                  ← python -m engine.schema.generate
│
├── schema.prisma               ← GENERATED (don't edit)
└── schema/
    ├── listing.py              ← GENERATED (don't edit)
    └── venue.py                ← GENERATED (don't edit)
```

## Benefits

### For Horizontal Scaling

**Before (Current):**
To add French vineyards:
1. Edit `types.py`: Add `WINERY = "WINERY"` (Python code change)
2. Create `winery.py` with FieldSpecs (Python code change)
3. Edit `schema.prisma`? (Maybe, if adding columns)
4. Update TypeScript types (Frontend code change)
5. Deploy code changes

**After (With YAML):**
To add French vineyards:
1. Create `engine/config/schemas/winery.yaml` (config file)
2. Run `python -m engine.schema.generate`
3. Commit generated files
4. Deploy (no code changes!)

### For Development Workflow

- ✅ **Single edit point**: Change field in one place (YAML)
- ✅ **Automated sync**: Run generator, all schemas update
- ✅ **CI validation**: Tests fail if schemas drift
- ✅ **Version control**: YAML changes show in git diffs
- ✅ **Non-dev friendly**: Product managers can add entity types

### For Multi-Vertical Deployment

- ✅ **Edinburgh**: Uses `base.yaml` + `venue.yaml`
- ✅ **French Vineyards**: Uses `base.yaml` + `winery.yaml`
- ✅ **NYC Restaurants**: Uses `base.yaml` + `restaurant.yaml`
- ✅ **Shared core**: All verticals share base fields
- ✅ **Independent domains**: Each vertical adds specific fields

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Generator bugs create invalid schemas | High | Comprehensive validation tests, schema snapshots |
| YAML format too complex to maintain | Medium | Keep simple, provide templates, good documentation |
| Generated files accidentally edited | Medium | Add "GENERATED - DO NOT EDIT" warnings, git hooks |
| Breaking changes to existing schemas | High | Start with exact replication, validate before replacing |
| Performance of parsing YAML on every import | Low | Cache parsed schemas, only parse on generation |

## Dependencies

- **Requires**: Current schema files (`listing.py`, `schema.prisma`) as reference
- **Blocks**: None (this is foundational infrastructure)
- **Enables**:
  - Easy addition of new entity types (wineries, restaurants)
  - Multi-vertical deployment without code changes
  - Automated schema validation in CI
  - Future: TypeScript type generation

## Out of Scope (Deferred)

These are valuable but not part of this track:

1. **Schema Registry Service**: API for dynamic schema retrieval (overkill for now)
2. **Schema Migration Tooling**: Automated migration generation (Prisma handles this)
3. **Runtime Schema Validation**: Runtime type checking (Pydantic handles this)
4. **Schema Versioning System**: Track breaking changes (manual versioning sufficient)

## Acceptance Criteria

**This track is complete when:**

1. ✅ `engine/config/schemas/base.yaml` exists with all current Listing fields
2. ✅ Running `python -m engine.schema.generate` produces:
   - `schema.prisma` (exact match to current)
   - `listing.py` (exact match to current)
3. ✅ Validation tests pass confirming schemas match YAML
4. ✅ All existing extraction tests pass (89 tests)
5. ✅ Documentation exists: "Adding a New Entity Type"
6. ✅ Example: Created `winery.yaml` and generated schemas successfully
7. ✅ Git commit history shows YAML as source, generated files as artifacts

## Timeline Estimate

- **Phase 1** (Parser & Validator): 2-3 hours
- **Phase 2** (Python Generator): 2-3 hours
- **Phase 3** (Prisma Generator): 3-4 hours
- **Phase 4** (Migration & Testing): 2-3 hours
- **Phase 5** (Documentation): 1-2 hours

**Total**: 10-15 hours of focused work

## Related Documentation

- Current Python schemas: `engine/schema/listing.py`, `engine/schema/venue.py`
- Current Prisma schema: `engine/schema.prisma`
- Architecture docs: `ARCHITECTURE.md` (Section 2: Entity Framework)
- Extraction utilities: `engine/extraction/schema_utils.py`
