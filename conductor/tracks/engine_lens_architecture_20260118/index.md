# Engine-Lens Architecture Refactor (v2.2)

**Track ID:** engine_lens_architecture_20260118
**Status:** Ready for Implementation
**Priority:** Critical
**Version:** v2.2 (with Tightening Addendum)
**Estimated Effort:** 30-40 hours (6 phases)

---

## v2.2 Tightening Addendum

This version adds explicit enforcement tasks and acceptance criteria for:

1. **Supabase/Prisma Specifics** - Postgres array defaults verified, GIN indexes required, standardized ID strategy (uuid OR cuid, no mixing)
2. **Engine Purity Enforcement** - No lens imports, CI/grep tests prevent violations, no value-string branching (e.g., `if value == "padel"`)
3. **Lens Contract Validation** - dimension_source must be one of 4 canonical_* columns, facet references validated, fail-fast validation
4. **Module Composition Hardening** - No duplicate module keys; JSONB namespacing enforced; duplicate field names across modules allowed.
5. **Classification Rule Locked** - Single entity_class + multi roles pattern documented with concrete examples ("club with courts" → place + multiple roles)
6. **Query Semantics** - OR within facet (default), AND across facets, grouping derived/view-only (not stored)
7. **Comprehensive Test Suite** - Engine purity, lens validation, deduplication determinism, Prisma array filters, module composition

---

## Quick Summary

Refactor Edinburgh Finds to separate a universal, vertical-agnostic **Entity Engine** from vertical-specific **Lens Layer**. This architectural separation enables horizontal scaling to new verticals (wine, restaurants, gyms) by adding YAML configuration only - **zero engine code changes required**.

## Key Architectural Shift

### Before (Current State)
```
Engine Layer
├── Vertical-specific concepts (padel, tennis, gym, coach, venue)
├── Domain modules (sports_facility) in engine
├── Dimensions stored as JSONB
├── Activity-specific triggers ("padel" → sports_facility)
└── Entity classification tied to vertical vocabulary
```

### After (Target State)
```
┌─────────────────────────────────────────────────────────────────┐
│ LENS LAYER (Vertical-Specific)                                 │
│ - Facets, canonical values, mapping rules                      │
│ - Domain modules (sports_facility, wine_production)            │
│ - Module triggers (value-based, explicit format)               │
│ - Derived groupings, SEO templates                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ ENGINE LAYER (100% Vertical-Agnostic)                          │
│ - entity_class (place, person, organization, event, thing)     │
│ - Dimensions as Postgres text[] arrays (GIN indexed)           │
│ - Opaque values (zero interpretation)                          │
│ - Universal modules only (core, location, contact, hours)      │
└─────────────────────────────────────────────────────────────────┘
```

## Critical Requirements (Must Not Deviate)

1. ✅ **Engine remains 100% vertical-agnostic**
   - No domain concepts (sports, wine, padel, coach, venue)
   - No value-based triggers
   - No domain modules

2. ✅ **Dimensions are Postgres text[] arrays with GIN indexes**
   - NOT JSONB
   - Fast faceted filtering
   - Prisma array filters (has, hasSome, hasEvery)

3. ✅ **Lens owns ALL interpretation**
   - Canonical values with metadata (labels, icons, colors)
   - Mapping rules (raw → canonical)
   - Role facet (internal-only)
   - Derived groupings (entity_class + roles logic)
   - Domain modules (sports_facility, wine_production)
   - Module triggers (explicit `when: {facet, value}` format)

4. ✅ **Extraction pipeline integration**
   - Build facet_to_dimension lookup from lens.facets
   - Initialize canonical_values_by_facet with empty lists for all facets
   - Distribute values by facet to dimension arrays
   - Deduplicate deterministically (dedupe_preserve_order)
   - Apply lens module triggers

## Six Phases (v2.2)

### Phase 1: Engine Core Design
- Create `engine/config/entity_model.yaml` (universal entity classes, dimensions, universal modules)
- Update Prisma schema (String[] for dimensions, Json for modules, GIN indexes)
- **v2.2**: Standardize ID strategy (uuid OR cuid, no mixing)
- **v2.2**: Lock classification rules with examples ("club with courts" → place + multiple roles)

### Phase 2: Lens Layer Design
- Create `lenses/edinburgh_finds/lens.yaml` (Sports & Fitness lens)
- Implement `lenses/loader.py` (lens configuration loader)
- **v2.2**: Implement fail-fast lens contract validation
- **v2.2**: Enforce module composition (no duplicates, JSONB namespacing)

### Phase 3: Data Flow Integration
- Update extraction pipeline to use lens mapping
- Implement facet routing and deduplication
- Create query layer with Prisma array filters
- **v2.2**: Document query semantics (OR within facet, AND across facets)

### Phase 4: Migration Strategy
- Schema migration (text[] arrays, GIN indexes)
- Data transformation (entityType → entity_class + canonical_roles)
- Re-extraction with lens-aware pipeline
- Validation

### Phase 5: Second Vertical Validation
- Create `lenses/wine_discovery/lens.yaml` (Wine lens)
- Validate zero engine changes needed
- Test extraction with wine lens
- Validate different interpretation of same dimensions

### Phase 6: Hardening & Test Suite (v2.2 NEW)
- **Engine purity enforcement**: CI/grep tests, no lens imports, no value-string branching
- **Lens validation tests**: All 5 contract validations (dimension_source, facet refs, mapping refs, no duplicates)
- **Deduplication tests**: Deterministic, preserves order
- **Prisma array filter tests**: has/hasSome/hasEvery correctness
- **Module composition tests**: No duplicates, JSONB namespacing
- **CI/CD integration**: All contracts enforced on every commit

## Success Criteria

**Track is complete when:**

1. ✅ Engine is 100% vertical-agnostic (zero references to sports, wine, etc.)
2. ✅ Dimensions use Postgres text[] arrays with GIN indexes (not JSONB)
3. ✅ Modules remain JSONB (flexible attribute storage)
4. ✅ Lens configuration owns all interpretation
5. ✅ Role facet implemented (internal-only, universal function-style keys)
6. ✅ Extraction pipeline uses lens mapping with facet routing
7. ✅ Query layer uses Prisma array filters (has, hasSome, hasEvery)
8. ✅ Deduplication applied deterministically (dedupe_preserve_order)
9. ✅ Second vertical (Wine Discovery) works with zero engine changes
10. ✅ All existing tests pass

## Key Files

**Engine Layer:**
- `engine/config/entity_model.yaml` - NEW
- `web/prisma/schema.prisma` - UPDATE
- `engine/extraction/base.py` - UPDATE
- `engine/extraction/entity_classifier.py` - NEW

**Lens Layer:**
- `lenses/loader.py` - NEW
- `lenses/edinburgh_finds/lens.yaml` - NEW
- `lenses/wine_discovery/lens.yaml` - NEW
- `web/lib/lens-query.ts` - NEW

**Migration:**
- `scripts/migrate_listing_to_entity.py` - NEW
- `migrations/xxx_add_dimension_gin_indexes.sql` - NEW

## Horizontal Scaling Example

**Adding French Vineyards (Wine Discovery vertical):**

**Before (Current Architecture):**
1. Edit engine code (add wine-specific concepts)
2. Create domain modules in engine
3. Update extraction logic
4. Update database schema
5. Deploy code changes

**After (Engine-Lens Architecture):**
1. Create `lenses/wine_discovery/lens.yaml` (configuration only)
2. Deploy (zero engine code changes!)

Same engine, different lens interpretation. ✨

---

## Documentation

- **Full Spec:** [spec.md](./spec.md)
- **Implementation Plan:** [plan.md](./plan.md)
- **Metadata:** [metadata.json](./metadata.json)

---

**Created:** 2026-01-18
**Last Updated:** 2026-01-18
