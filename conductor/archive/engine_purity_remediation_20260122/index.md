# Track: Engine Purity Remediation

**Status:** Active
**Created:** 2026-01-22

This track addresses the critical blocking violations and architectural debts identified following the initial Engine Purity schema migration. While the database schema has been successfully migrated to the universal `Entity` model, the application logic (extraction, seeding, ingestion) remains fractured, relying on legacy `Listing` and vertical-specific `VENUE` concepts.

## Core Documents
- [Implementation Plan](./plan.md) - Step-by-step execution checklist.
- [Specification](./spec.md) - Detailed requirements and remediation targets.
- [Review Findings](../../../ENGINE_PURITY_REVIEW.md) - The audit triggering this track.

## Goal
To synchronize the application logic (Python codebase) with the new vertical-agnostic Database Schema, ensuring the system is executable, stable, and architecturally pure.