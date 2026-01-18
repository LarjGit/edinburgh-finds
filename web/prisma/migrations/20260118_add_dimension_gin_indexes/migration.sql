-- ============================================================
-- GIN Indexes for Dimension Arrays (Postgres/Supabase Only)
-- ============================================================
-- This migration adds GIN (Generalized Inverted Index) indexes
-- to the text[] array columns for fast faceted filtering.
--
-- IMPORTANT: These indexes are REQUIRED for production performance
-- when using Postgres/Supabase. GIN indexes enable efficient
-- array containment queries used by the faceted search.
--
-- NOTE: This migration is for Postgres/Supabase only.
-- SQLite does not support GIN indexes or array types.
-- This file will be applied during the SQLite → Postgres migration.
-- ============================================================

-- GIN indexes are REQUIRED for fast faceted filtering on text[] arrays

CREATE INDEX IF NOT EXISTS entities_activities_gin ON entities USING GIN (canonical_activities);

CREATE INDEX IF NOT EXISTS entities_roles_gin ON entities USING GIN (canonical_roles);

CREATE INDEX IF NOT EXISTS entities_place_types_gin ON entities USING GIN (canonical_place_types);

CREATE INDEX IF NOT EXISTS entities_access_gin ON entities USING GIN (canonical_access);

-- ============================================================
-- Index Benefits:
-- ============================================================
-- - Fast containment queries: WHERE 'value' = ANY(array_column)
-- - Fast overlap queries: WHERE array_column && ARRAY['val1', 'val2']
-- - Fast contains queries: WHERE array_column @> ARRAY['value']
-- - Efficient for faceted search with OR/AND combinations
-- ============================================================
