# Engine-Lens Architecture Review & Next Steps (Codex)

Date: 2026-01-19
Scope: static code review vs conductor/tracks/engine_lens_architecture_20260118; no tests executed.

## Executive Summary
- Status: Not yet complete. There are blockers that prevent closing the track and moving on without risk.
- Primary blockers: Supabase/Postgres migration not completed; engine still contains vertical-specific schema and entity_type pipeline; classification order mismatch; lens trigger condition shape mismatch; confidence thresholds hardcoded.

## Findings (ordered by severity)

1) BLOCKER: Database layer is still SQLite plus JSON strings, so required Postgres array and GIN behavior is unverified and not actually implemented.
   Evidence: `web/prisma/schema.prisma:20` (sqlite provider), `web/prisma/schema.prisma:52-62` (canonical_* stored as JSON strings, modules String).
   Impact: Prisma array filters plus GIN indexes cannot be validated; query layer in `web/lib/lens-query.ts` assumes Postgres arrays.
   Required fix: Migrate to Supabase/Postgres, update provider and type definitions, run migrations and array filter tests.

2) BLOCKER: Engine is not yet vertical-agnostic; legacy sports-specific schema and ingestion path remain the default.
   Evidence: `engine/schema/venue.py:39` (tennis_summary, padel_summary etc), `engine/ingest.py:8` (VENUE_FIELDS), `engine/extraction/run.py:187` (entity_type defaults to VENUE).
   Impact: Architecture still couples engine to sports and venue schema and entity_type pipeline; violates spec goals of opaque dimensions plus lens-only interpretation.

3) HIGH: Classification priority order does not match spec (organization should be checked before person).
   Evidence: `engine/extraction/entity_classifier.py:303-312` (person checked before organization).
   Impact: Membership orgs can be misclassified as person, cascading into wrong entity_class and roles.

4) HIGH: Engine classifier still embeds vertical-specific heuristics and emits lens-specific values.
   Evidence: `engine/extraction/entity_classifier.py:89-96` (coach and instructor keywords), `engine/extraction/entity_classifier.py:210-215` (sports_centre default).
   Impact: Violates opaque values and no vertical concepts in engine; introduces sports-specific values in core classification.

5) MEDIUM: ModuleTrigger conditions shape mismatch (lens YAML uses list; loader expects dict), so conditions may be ignored in VerticalLens.get_required_modules.
   Evidence: `engine/lenses/loader.py:203-229` (conditions assumed dict), `lenses/edinburgh_finds/lens.yaml:423-430` (conditions as list).
   Impact: Triggers can apply without entity_class gating when using VerticalLens.get_required_modules; tests do not cover list shape.

6) MEDIUM: Confidence threshold is hardcoded (0.7) in engine and lens loader instead of being driven by lens config.
   Evidence: `engine/extraction/base.py:262-277`, `engine/lenses/loader.py:438-451`.
   Impact: Violates spec note that thresholds live in lens config; limits per-lens tuning and future verticals.

## Can We Move On?
Not yet. The architectural boundary is mostly in place, but the system still runs through legacy, vertical-specific paths and the Postgres/Supabase contract is unproven. Closing the track now would leave core success criteria unfulfilled.

## Recommended Next Stages (Priority Order)

1) Supabase/Postgres migration (required to close this track)
   - Switch Prisma datasource to Postgres.
   - Make canonical_* fields native String[] with @default([]) and modules as Json.
   - Apply the GIN index migration and run tests/query/test_prisma_array_filters.py.
   - Verify EXPLAIN uses GIN indexes.

2) Complete engine purity cleanup
   - Remove or quarantine legacy engine/schema/venue.py plus entity_type-driven extraction flow.
   - Route extractors through extract_with_lens_contract (or clearly separate legacy paths).
   - Ensure no vertical-specific defaults (for example sports_centre) are emitted from engine.

3) Fix classification plus lens trigger semantics
   - Update entity_class priority order (event -> place -> organization -> person -> thing).
   - Remove vertical-specific heuristics from classifier; move to lens mapping rules.
   - Align module_triggers conditions shape (dict vs list) and add tests for real YAML.

4) Data re-ingestion plus validation in Postgres
   - Re-run extraction with lens-aware pipeline.
   - Validate canonical_* arrays, module namespacing, and derived groupings.

5) Frontend plus product-layer integration
   - Wire UI filters to lens facets and array filters.
   - Add Supabase-backed query tests for derived groupings and facets.
