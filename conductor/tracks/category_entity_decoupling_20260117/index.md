# Track: Category-Entity Decoupling

**Status:** Active
**Created:** 2026-01-17

## Overview
This track addresses the architectural mismatch where "Activity" categories (Padel, Tennis) were incorrectly modeled as children of the "Venue" entity type. We are refactoring the system to treat categories and entity types as orthogonal concepts.

## Key Documents
- [Product Spec](./spec.md) - Problem definition and goals.
- [Implementation Plan](./plan.md) - Step-by-step refactoring guide.

## Context
Triggered by the realization that "Padel" (and other sports) must apply to Coaches, Retailers, and Clubs, not just Venues.
