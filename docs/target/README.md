# Target Architecture

This directory contains the **target/aspirational architecture** for the Universal Entity Extraction Engine.

These documents define:
- **What we're building toward** (the vision)
- **How the system should work** (the ideal state)
- **Immutable architectural principles** (the constitution)

## Documents in This Directory

### `system-vision.md` — The Architectural Constitution
**Status:** Immutable

Defines the 10 non-negotiable invariants that must remain true for the system's lifetime:
1. Engine Purity (zero domain knowledge)
2. Lens Ownership (all semantics in YAML contracts)
3. Zero Engine Changes for New Verticals
4. Determinism and Idempotency
5. Canonical Registry Authority
6. Fail-Fast Validation
7. Schema-Bound LLM Usage
8. No Permanent Translation Layers
9. Engine Independence
10. No Reference-Lens Exceptions

Also defines success criteria including the "One Perfect Entity" validation requirement.

### `architecture.md` — The Runtime Implementation Specification
**Status:** Living Architecture (evolves deliberately)

Defines the concrete runtime mechanics:
- 11-stage execution pipeline
- Engine-Lens integration contracts
- Extraction boundary (Phase 1: primitives, Phase 2: canonical)
- Deterministic merge semantics
- Validation gates and enforcement mechanisms

**Important:** This is the detailed technical specification that operationalizes the system-vision.md invariants.

## Relationship to As-Built Documentation

**Target vs. As-Built:**
- **This directory (`docs/target/`)**: The aspirational architecture we're building toward
- **Parent directory (`docs/`)**: As-built documentation reflecting current system state

When working on the codebase:
1. **Read target architecture first** to understand the vision and principles
2. **Check as-built docs** to understand current implementation state
3. **Plan changes** that move current state toward target architecture

## For AI Agents

**CRITICAL:** Before making ANY architectural change, you must:
1. Read `system-vision.md` to understand immutable invariants
2. Read `architecture.md` to understand runtime contracts
3. Confirm compliance in your response before proceeding

The target architecture documents are the ultimate authority for all architectural decisions.

## For Developers

These documents define:
- **What's non-negotiable** (system-vision.md invariants)
- **How things should work** (architecture.md specification)
- **Why we make certain decisions** (both documents provide rationale)

If you're unsure whether a change is architecturally sound, consult these documents first.

---

**Last Updated:** 2026-02-07
