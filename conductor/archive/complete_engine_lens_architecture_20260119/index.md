# Track: Complete Engine-Lens Architecture

**Status:** Active
**Created:** 2026-01-19
**Goal:** Finalize the Engine-Lens separation by migrating to Supabase (Postgres) and removing all remaining legacy/vertical-specific code from the engine.

## Core Documents
- [Specification](./spec.md)
- [Implementation Plan](./plan.md)

## Context
This track is the direct continuation and completion of the [Engine-Lens Architecture Refactor](../engine_lens_architecture_20260118/index.md). 
An audit revealed that while the architectural boundaries were defined, the system relies on legacy SQLite workarounds and retains sports-specific logic in the core engine.

## Primary Objectives
1.  **Infrastructure:** Migrate from SQLite to Supabase (Postgres) to enable native Arrays and GIN indexes.
2.  **Purity:** Eliminate all vertical-specific code (keywords, legacy schemas) from `engine/`.
3.  **Correctness:** Fix classification priority and configuration loading bugs.
