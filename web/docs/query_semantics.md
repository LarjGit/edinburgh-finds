# Query Semantics Documentation

## Overview

This document defines and enforces the default query semantics for entity filtering in the lens-aware query layer. All queries operate on Postgres text[] arrays (canonical_activities, canonical_roles, canonical_place_types, canonical_access), not JSON.

## Core Rule

**Default query semantics: OR within facet, AND across facets**

This means:
- When filtering by multiple values within the same facet (e.g., multiple activities), entities match if they have ANY of those values (OR logic)
- When filtering by multiple facets (e.g., activities AND place_type), entities must satisfy all facet conditions (AND logic)

## Examples

### Example 1: Activities Filter (Single Facet)

**User selects multiple activities: "Show me places with padel OR tennis"**

```typescript
// Query
{
  canonical_activities: { hasSome: ['padel', 'tennis'] }
}

// Semantic: Entity matches if it has ANY of these activities
// Prisma array filter: hasSome (Postgres && operator)

// Matching entities:
// ✅ Entity with activities: ["padel"]
// ✅ Entity with activities: ["tennis"]
// ✅ Entity with activities: ["padel", "tennis"]
// ✅ Entity with activities: ["padel", "tennis", "squash"]
// ❌ Entity with activities: ["squash", "badminton"]
```

### Example 2: Multi-Facet Filter

**User selects: activities=[padel, tennis] AND place_type=[sports_centre]**

**Semantic: "Show me sports centres with padel OR tennis"**

```typescript
// Query
{
  AND: [
    { canonical_activities: { hasSome: ['padel', 'tennis'] } },  // OR within facet
    { canonical_place_types: { hasSome: ['sports_centre'] } }    // AND across facets
  ]
}

// Entity matches if: (has padel OR tennis) AND (is sports_centre)

// Matching entities:
// ✅ Sports centre with padel
// ✅ Sports centre with tennis
// ✅ Sports centre with padel and tennis
// ❌ Sports centre with only squash (missing padel/tennis)
// ❌ Outdoor facility with padel (wrong place_type)
// ❌ Park with tennis (wrong place_type)
```

### Example 3: Derived Grouping (Computed, Not Stored)

**Grouping is computed at query time, never stored in database**

```typescript
// Derived grouping "people" = entity_class:person AND roles:provides_instruction
// This is computed at query time, never stored in database

// Query
{
  AND: [
    { entity_class: 'person' },
    { canonical_roles: { hasSome: ['provides_instruction'] } }
  ]
}

// Grouping is a VIEW-ONLY concept, derived from entity_class + roles
// It is NEVER stored as a column in the database

// Matching entities:
// ✅ Person with role "provides_instruction"
// ✅ Person with roles ["provides_instruction", "sells_goods"]
// ❌ Person with role "sells_goods" only (missing required role)
// ❌ Organization with role "provides_instruction" (wrong entity_class)
```

### Example 4: AND Mode (Special Case)

**User wants places with BOTH padel AND tennis (rare case)**

```typescript
// Query
{
  canonical_activities: { hasEvery: ['padel', 'tennis'] }
}

// Entity matches if it has ALL of these activities
// Prisma array filter: hasEvery (Postgres @> operator)

// Note: This is NOT the default, must be explicitly requested

// Matching entities:
// ✅ Entity with activities: ["padel", "tennis"]
// ✅ Entity with activities: ["padel", "tennis", "squash"]
// ❌ Entity with activities: ["padel"] (missing tennis)
// ❌ Entity with activities: ["tennis"] (missing padel)
// ❌ Entity with activities: ["squash"] (missing both)
```

## Prisma Array Filters Reference

### `has` - Single Value Match
```typescript
{ canonical_activities: { has: "padel" } }
// Postgres ? operator
// Matches: Entity has exactly "padel" in activities array
```

### `hasSome` - OR Logic (Default)
```typescript
{ canonical_activities: { hasSome: ["padel", "tennis"] } }
// Postgres && operator
// Matches: Entity has AT LEAST ONE of these values
// This is the DEFAULT for multi-value filters within a facet
```

### `hasEvery` - AND Logic (Special Case)
```typescript
{ canonical_activities: { hasEvery: ["padel", "tennis"] } }
// Postgres @> operator
// Matches: Entity has ALL of these values
// This is NOT the default, must be explicitly requested
```

## Anti-Patterns

### ❌ NEVER: Store grouping in database

```typescript
// WRONG: Adding grouping_id column
model Entity {
  grouping_id String?  // ❌ DO NOT DO THIS
}

// WRONG: Storing computed grouping value
await prisma.entity.update({
  where: { id: entityId },
  data: { grouping_id: "people" }  // ❌ DO NOT DO THIS
});
```

### ✅ ALWAYS: Compute grouping at query/view time

```typescript
// CORRECT: Compute grouping from entity_class + roles
function computeGrouping(entity: Entity, lens: VerticalLens): string | undefined {
  for (const grouping of lens.derived_groupings) {
    if (grouping.matches(entity)) {
      return grouping.id;
    }
  }
  return undefined;
}

// CORRECT: Apply grouping in view transformation
const entityView = transformEntityToView(entity, lens);
// entityView.grouping is computed, not retrieved from database
```

## Implementation Guidelines

### 1. Default Query Pattern

When building queries, always default to OR within facet:

```typescript
// CORRECT: Default OR within facet
const query = {
  canonical_activities: { hasSome: selectedActivities }
};

// WRONG: Using AND when OR is expected
const query = {
  canonical_activities: { hasEvery: selectedActivities }
};
```

### 2. Multi-Facet Queries

Combine facets with AND logic:

```typescript
// CORRECT: AND across facets
const query = {
  AND: [
    { canonical_activities: { hasSome: activities } },
    { canonical_place_types: { hasSome: placeTypes } },
    { canonical_access: { hasSome: accessTypes } }
  ]
};
```

### 3. Grouping Computation

Always compute grouping at query/view time:

```typescript
// CORRECT: Compute in application layer
const entities = await prisma.entity.findMany({ where: query });
const views = entities.map(entity => ({
  ...entity,
  grouping: lens.compute_grouping(entity) // Computed, not stored
}));

// WRONG: Query for grouping
const entities = await prisma.entity.findMany({
  where: { grouping_id: "people" } // ❌ grouping_id doesn't exist
});
```

## Query Performance

### Indexes

Ensure GIN indexes exist on all dimension columns:

```sql
CREATE INDEX idx_canonical_activities ON entities USING GIN (canonical_activities);
CREATE INDEX idx_canonical_roles ON entities USING GIN (canonical_roles);
CREATE INDEX idx_canonical_place_types ON entities USING GIN (canonical_place_types);
CREATE INDEX idx_canonical_access ON entities USING GIN (canonical_access);
```

### Query Optimization

- Use `hasSome` for OR logic (default) - optimized with GIN index
- Use `hasEvery` sparingly (only when truly needed) - requires full array scan
- Combine filters with AND at the top level for efficient index usage
- Avoid deeply nested OR conditions when possible

## Testing Guidelines

All query semantic tests should validate:

1. **OR within facet**: Multiple activities match if entity has ANY
2. **AND across facets**: Multiple facets must ALL match
3. **Derived grouping**: Computed correctly from entity_class + roles
4. **Grouping not stored**: Verify grouping is read-only property, not in database

### Example Test Cases

```typescript
describe('Query Semantics', () => {
  test('OR within facet - multiple activities', async () => {
    const result = await prisma.entity.findMany({
      where: {
        canonical_activities: { hasSome: ['padel', 'tennis'] }
      }
    });
    // Verify entities have padel OR tennis
  });

  test('AND across facets - activities + place_type', async () => {
    const result = await prisma.entity.findMany({
      where: {
        AND: [
          { canonical_activities: { hasSome: ['padel', 'tennis'] } },
          { canonical_place_types: { hasSome: ['sports_centre'] } }
        ]
      }
    });
    // Verify entities are sports centres with padel OR tennis
  });

  test('Derived grouping computed correctly', () => {
    const entity = {
      entity_class: 'person',
      canonical_roles: ['provides_instruction']
    };
    const grouping = lens.compute_grouping(entity);
    expect(grouping).toBe('people');
  });

  test('Grouping not stored in database', async () => {
    const entity = await prisma.entity.findUnique({ where: { id: '123' } });
    // Verify grouping field doesn't exist in database schema
    expect(entity).not.toHaveProperty('grouping_id');
    expect(entity).not.toHaveProperty('grouping');
  });
});
```

## Summary

- **Default**: OR within facet (hasSome), AND across facets
- **Grouping**: Computed at query time, NEVER stored
- **Arrays**: All dimensions are Postgres text[] with GIN indexes
- **Filters**: Use Prisma array filters (has, hasSome, hasEvery)
- **Anti-pattern**: Storing computed values like grouping in database
