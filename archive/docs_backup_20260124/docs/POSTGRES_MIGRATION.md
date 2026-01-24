# PostgreSQL Migration Guide

## Overview

This guide documents the migration from SQLite to PostgreSQL/Supabase for the Edinburgh Finds project. This migration is part of the Engine-Lens Architecture implementation (Track: complete_engine_lens_architecture_20260119).

## Why PostgreSQL?

The Engine-Lens architecture requires native database features that SQLite doesn't support:

1. **Native Array Types (`String[]`)**: For multi-valued dimensions (activities, roles, place_types, access)
2. **GIN Indexes**: For fast faceted filtering on arrays
3. **Native JSONB**: For modules and discovered_attributes with better query performance
4. **Scalability**: Better performance for production workloads

## Migration Status

### ✅ Completed
- [x] Schema generation updated to use PostgreSQL (PR f43c83b)
- [x] Prisma schemas regenerated with `String[]` arrays and `Json` types
- [x] GIN index migration prepared (20260118_add_dimension_gin_indexes)
- [x] Migration lock updated to `postgresql` provider
- [x] Environment configuration template created (`.env.example`)

### 📋 Pending (Phase 4)
- [ ] Set up PostgreSQL database (local or Supabase)
- [ ] Update DATABASE_URL in .env
- [ ] Run Prisma migrations
- [ ] Verify GIN indexes are created
- [ ] Re-ingest data from sources
- [ ] Run extraction pipeline

## Database Setup Options

### Option 1: Local PostgreSQL

```bash
# Install PostgreSQL
# macOS: brew install postgresql@15
# Ubuntu: sudo apt-get install postgresql-15

# Create database
createdb edinburgh_finds

# Update .env
DATABASE_URL="postgresql://localhost:5432/edinburgh_finds"
```

### Option 2: Supabase (Recommended for Production)

1. Create a new Supabase project at https://supabase.com
2. Navigate to Settings → Database
3. Copy the connection string
4. Update `.env`:

```bash
DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"
```

## Running the Migration

Once you have a PostgreSQL database:

```bash
# 1. Install dependencies
npm install

# 2. Generate Prisma Client
npx prisma generate

# 3. Run migrations (this will create all tables and GIN indexes)
npx prisma migrate deploy

# OR for development (with confirmation prompts):
npx prisma migrate dev

# 4. Verify GIN indexes were created
npx prisma db execute --stdin <<SQL
SELECT
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE indexname LIKE '%_gin%';
SQL
```

Expected output should include:
```
Listing | Listing_activities_gin   | CREATE INDEX Listing_activities_gin ON Listing USING gin (canonical_activities)
Listing | Listing_roles_gin        | CREATE INDEX Listing_roles_gin ON Listing USING gin (canonical_roles)
Listing | Listing_place_types_gin  | CREATE INDEX Listing_place_types_gin ON Listing USING gin (canonical_place_types)
Listing | Listing_access_gin       | CREATE INDEX Listing_access_gin ON Listing USING gin (canonical_access)
```

## Schema Changes Summary

### Before (SQLite)
```prisma
datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

model Listing {
  canonical_activities String?   @default("[]")  // JSON string
  canonical_roles String?   @default("[]")       // JSON string
  modules      String?                            // JSON string
}
```

### After (PostgreSQL)
```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Listing {
  canonical_activities String[]  @default([])     // Native array
  canonical_roles String[]  @default([])          // Native array
  modules      Json                                // Native JSONB
}
```

## GIN Index Benefits

GIN (Generalized Inverted Index) indexes enable fast queries on array columns:

```typescript
// Fast containment queries (uses GIN index)
const venues = await prisma.listing.findMany({
  where: {
    canonical_activities: {
      has: 'padel'  // Fast with GIN index
    }
  }
});

// Fast overlap queries
const venues = await prisma.listing.findMany({
  where: {
    canonical_activities: {
      hasSome: ['padel', 'tennis']  // Fast with GIN index
    }
  }
});
```

Without GIN indexes, these queries would require full table scans.

## Troubleshooting

### Migration fails with "relation does not exist"
If you have old SQLite migrations, Prisma may try to apply them. Solution:
```bash
# Reset migration history and create baseline
npx prisma migrate reset
```

### GIN indexes not created
Check that the migration file `20260118_add_dimension_gin_indexes/migration.sql` was applied:
```bash
npx prisma migrate status
```

### Connection refused
Verify DATABASE_URL is correct and PostgreSQL is running:
```bash
# Test connection
psql $DATABASE_URL
```

## Next Steps

After completing the migration:

1. **Phase 4.1**: Run fresh data ingestion
2. **Phase 4.2**: Run lens-aware extraction pipeline
3. **Phase 4.3**: Verify array and JSONB data structure
4. **Phase 5**: Update frontend query layer for native array filters

## References

- [Prisma PostgreSQL Documentation](https://www.prisma.io/docs/concepts/database-connectors/postgresql)
- [PostgreSQL GIN Indexes](https://www.postgresql.org/docs/current/gin.html)
- [Supabase Documentation](https://supabase.com/docs)
- [Complete Engine-Lens Architecture Spec](../conductor/tracks/complete_engine_lens_architecture_20260119/spec.md)
