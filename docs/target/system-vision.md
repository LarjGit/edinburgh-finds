# Universal Entity Extraction Engine — System Vision

**Status:** Architectural Constitution  
**Scope:** Engine-Level (Vertical-Agnostic)

This document defines the immutable intent, constraints, and success criteria for the Universal Entity Extraction Engine. It governs all architectural and implementation decisions regardless of which verticals or applications consume the engine.

Edinburgh Finds is the first reference lens and application built on top of the engine. It exists to validate the architecture, not to define or constrain it.

---

## 1. Core Mission

Build a horizontal, vertical-agnostic entity extraction engine that transforms natural language queries into complete, accurate entity records through AI-powered multi-source orchestration.

The engine is universal. It stores and processes entities using generic classifications, opaque canonical dimensions, and namespaced structured modules. All domain knowledge — vocabulary, interpretation, mapping, display semantics, and vertical behavior — lives exclusively in pluggable Lens contracts.

The engine must remain independently valuable and deployable without any specific vertical. Any number of verticals (sports discovery, wine discovery, restaurants, events, or future domains) may consume the engine without requiring engine code changes.

Verticals exist to validate and exercise the engine, not to shape its internal architecture.

---

## 2. Immutable Invariants (Non-Negotiable)

These invariants must remain true for the lifetime of the system. Violations are architectural defects regardless of whether functionality appears to work.

1. **Engine Purity**
    - The engine contains zero domain knowledge.
    - No domain-specific terms, taxonomies, or logic may exist in engine code.
    - The engine operates only on generic structures and opaque values.

2. **Lens Ownership of Semantics**
    - All domain semantics live exclusively in Lens contracts.
    - Lenses define vocabulary, mapping rules, canonical values, module schemas, routing behavior, and display metadata.
    - The engine treats Lens content as opaque configuration and never embeds interpretation logic.

3. **Zero Engine Changes or Refactoring for New Verticals**
    - Adding a new vertical must require **zero engine code changes, refactoring, or structural modification**.
    - New behaviour must be achieved solely through Lens configuration and contracts.

4. **Determinism and Idempotency**
    - Given the same inputs and lens contract, the system must always produce the same outputs.
    - Re-running the same query must update existing entities rather than creating duplicates.
    - All tie-breaking and merge behavior must be deterministic.

5. **Canonical Registry Authority**
    - All canonical values must be declared in a canonical registry.
    - No undeclared or ad-hoc canonical values may exist in the system.
    - Orphaned references are invalid and must fail fast.

6. **Fail-Fast Validation**
    - Invalid Lens contracts must fail at load time before execution begins.
    - Silent fallback behaviour is forbidden.

7. **Schema-Bound LLM Usage**
    - LLMs may only produce schema-validated structured output.
    - Free-form or unvalidated LLM output is forbidden.
    - Deterministic extraction must always be preferred when possible.

8. **No Permanent Translation Layers**
    - Universal schema field names are authoritative end-to-end.
    - No permanent mapping or translation layers may exist between pipeline stages.

9. **Engine Independence**
    - The engine must remain independently useful without any specific vertical.
    - No architectural decision may assume the existence of a particular lens or application.
    
10. **No Reference-Lens Exceptions**
    - The reference lens (e.g., Edinburgh Finds) must never receive special treatment, shortcuts, or exceptions in engine code.
    - Any behaviour that cannot be expressed through a Lens contract is an architectural defect.


---

## 3. Architectural Boundaries

The system is composed of two strictly separated layers:

- **The Engine** — A universal, domain-blind execution platform responsible for orchestration, extraction, normalization, merging, persistence, and lifecycle guarantees.
- **Lenses** — Pluggable vertical interpretation layers that define all domain semantics, vocabulary, mapping logic, display metadata, and vertical behaviour.

This separation is absolute and must be preserved over time.

### Engine Responsibilities

The engine owns:

- Universal entity classification (e.g., place, person, organization, event, thing).
- Storage and indexing of canonical dimensions as opaque values.
- Storage and validation of namespaced structured modules.
- Deterministic orchestration of ingestion, extraction, deduplication, merging, and persistence.
- Execution of generic extraction, normalization, and merge logic.
- Enforcement of validation gates, determinism guarantees, and purity constraints.
- Provenance tracking and reproducibility guarantees.

The engine does not interpret the meaning of any domain value. It operates solely on structure, metadata, and generic contracts.

### Lens Responsibilities

Lenses own all domain interpretation, including:

- Domain vocabulary and query interpretation semantics.
- Connector routing rules and vertical-specific orchestration intent.
- Mapping rules from raw observations to canonical dimension values.
- Canonical value registries and display metadata.
- Domain module schemas and extraction rules.
- Module attachment rules and derived groupings.
- Presentation semantics such as labels, icons, and SEO metadata.

Lenses are treated as compiled runtime contracts consumed by the engine. The engine never embeds lens semantics and never assumes the presence of any particular lens.

### Boundary Enforcement

The following boundaries are mandatory:

- Engine code must not contain domain-specific terminology, literals, or logic.
- Engine code must not import or directly depend on lens implementation modules.
- All semantic interpretation must flow through lens contracts only.
- The engine may validate lens structure and references but must not interpret their meaning.
- Domain behavior must never be introduced through conditional logic in the engine.

Violations of these boundaries are architectural defects and must be corrected immediately, even if functionality appears correct.

---

## 4. Data Philosophy

The system treats data as a structured, evolving representation of real-world entities rather than as loosely typed documents or application-specific records.

The data model is intentionally designed to separate **universal structure** from **domain interpretation**.

### Universal Structure

All entities share a universal structural model:

- A stable entity identity.
- A universal entity class (place, person, organization, event, thing).
- A fixed set of canonical dimensions represented as multi-valued arrays.
- Namespaced structured modules for detailed attributes.
- Explicit provenance and external identifiers.

The structure of this model is owned by the engine and remains stable across all verticals.

Canonical dimensions provide consistent queryable structure across domains, but their values are treated as opaque by the engine and interpreted exclusively by lenses.

### Opaque Semantics

The engine never assigns meaning to domain values. Strings such as activity names, roles, place types, or access models are opaque identifiers from the engine’s perspective.

All semantic meaning, labeling, grouping, and presentation is defined entirely by lens contracts. This allows multiple verticals to interpret the same underlying entity data differently without modifying the engine or schema.

### Namespaced Modules

Detailed attributes are stored in namespaced modules rather than flattened into a single schema. Modules allow the system to:

- Capture deep, structured domain data without polluting the universal schema.
- Evolve independently per vertical without breaking existing data contracts.
- Avoid field collisions and accidental semantic coupling.
- Preserve clarity of ownership and responsibility.

Modules represent the primary mechanism for capturing rich, differentiating data beyond basic listings.

### Rich Data Over Shallow Listings

The system prioritizes completeness and depth of information over superficial coverage. Commodity listing data (name, address, phone) is not sufficient to deliver meaningful value.

High-quality entities capture quantitative, structured detail that allows users to understand what an entity actually offers, not just that it exists.

### Provenance as First-Class Data

Every entity retains explicit provenance information, including contributing sources, external identifiers, and verification context.

Provenance enables:

- Debugging and traceability.
- Trust evaluation and conflict resolution.
- Incremental enrichment and refresh strategies.
- Long-term data quality monitoring.

Provenance is not optional metadata; it is a core part of the data model.

### Evidence Model

The engine recognizes a fixed set of evidence surfaces produced in Phase 1:

- Structured primitives (name, address, coordinates, categories, etc.).
- Narrative surfaces (summary, description).
- Source observations.

Lenses may reason only over these surfaces.
Evidence surfaces carry no semantics; interpretation occurs exclusively through lens contracts.
The creation or removal of an evidence surface is a Vision-level change.

---

## 5. Determinism, Trust & Reproducibility

The system is designed to behave predictably, transparently, and repeatably. These properties are foundational for operating a large-scale ingestion and extraction platform.

Determinism applies to the processing of captured inputs. External systems (APIs, LLMs, live data sources) may produce variable outputs; once those outputs are captured as raw inputs, all downstream processing must be fully deterministic.

### Deterministic Behavior

Given the same inputs, configuration, and lens contract, the system must always produce identical outputs.

All processing stages — orchestration, extraction, mapping, deduplication, merging, and persistence — must avoid non-deterministic behavior. Any ambiguity must be resolved using explicit, deterministic tie-break rules.

Determinism enables:

- Safe reprocessing and backfills.
- Reliable debugging and regression analysis.
- Confidence that changes produce intentional outcomes.
- Stable behavior across environments and time.

### Idempotency

Re-running the same query or ingestion process must update existing entities rather than creating duplicates or divergent state.

Idempotency applies across the entire pipeline, including raw ingestion, extraction, deduplication, merging, and persistence.

Repeated execution should converge toward a stable, correct representation of the underlying real-world entity.

### Trust as Metadata, Not Logic

The system treats source trust as data rather than as hardcoded logic.

Trust signals, priority, confidence, and provenance are expressed as metadata and consumed generically by the engine. No domain or connector-specific assumptions are embedded in merge or selection logic.

This allows trust models to evolve without architectural changes and prevents implicit bias from creeping into the engine.

### Reproducibility and Traceability

The system must support reproducibility of results and traceability of decisions.

This includes:

- The ability to associate outputs with the lens contract version or hash used.
- Preservation of provenance and contributing sources.
- Stable deterministic behavior across repeated executions.
- Clear auditability of how values were derived.

Reproducibility enables confident iteration, debugging, and long-term system evolution.

### Merge is Constitutional

The formation of a single entity from many observations follows a deterministic constitution:

- Field-group strategies.
- Explicit missingness semantics.
- Metadata-driven tie-break.
- Deep module merge.

Merge behavior is not an implementation detail; it defines truth.
Merge must not contain connector-specific conditions; only trust metadata may influence outcomes.

---

## 6. What Success Looks Like

Success is measured by the quality, completeness, accuracy, and trustworthiness of the entity data produced by the system — not by code coverage, feature count, or throughput alone.

The ultimate validation of the system is the contents of the entity store.

### End-to-End Proof Requirement (One Perfect Entity)

The system is not considered validated until at least **one real-world entity** has flowed end-to-end through the full pipeline with **no architectural compromises**:

Query → Orchestration → Ingestion → Extraction → Lens Mapping → Classification → Module Attachment → Module Population → Deduplication → Deterministic Merge → Finalization → Persistence.

One Perfect Entity requires canonical dimensions and at least one module field.
Geographic coordinates are an optional OPE+Geo quality gate.

The validation entity must produce a persisted record in the entity store with:

- Correct `entity_class`.
- Non-empty canonical dimensions where evidence exists.
- All triggered modules attached and **at least one** module field populated.
- Accurate universal primitives (identity, location, contact where available).
- Provenance and external IDs preserved.

### What Is a Place

A location is recognized when any reliable geographic anchoring is present
(coordinates, street address, city, postcode).

Partial success (e.g., primitives only, single-source only, empty modules) is not considered architecture validation.

### Multi-Source Merge Validation Gate

The system is not considered complete unless at least one entity has been produced by **merging data from multiple independent sources**.

Validation must demonstrate:

- Multiple raw ingestions persisted for the same real-world entity.
- Correct cross-source deduplication grouping.
- Deterministic, metadata-driven merge producing a single canonical entity.
- Idempotent re-runs converging on the same merged output.

### Complete Entities

A high-quality entity record contains:

- Correct entity classification.
- Meaningful canonical dimensions populated where data exists.
- Relevant domain modules attached and populated with structured detail.
- Accurate universal fields (identity, location, contact, time).
- Explicit provenance and external identifiers.

Empty or null fields should be the exception, not the norm, when data is available from upstream sources.

The system aims to capture what an entity actually offers, not merely that it exists.

### Acceptable Incompleteness

Not all missing data represents a failure.

The following cases are acceptable:

1. **The facility or attribute does not exist in reality.**
2. **The data is not available from any current source.**

These cases should be visible and trackable but do not represent system defects.

### Unacceptable Incompleteness

The following cases represent system defects and must be addressed:

1. **Extraction failures** where available data was not captured.
2. **Classification errors** where entities are misclassified or mis-labeled.
3. **Mapping gaps** where observed data fails to populate canonical dimensions.
4. **Merge errors** where correct data is lost or overridden incorrectly.

Silent data loss is always considered a defect.

### Accuracy and Integrity

The system prioritizes correctness over coverage.

- Entities must not contain hallucinated or fabricated data.
- Canonical dimensions must reflect only what is supported by evidence.
- Entity classification must be deterministic and reliable.
- Deduplication must merge identical entities and avoid false positives.

A smaller set of highly accurate entities is preferable to a larger set of incomplete or incorrect entities.

### Reality-Based Validation

Validation must prioritize real data and real system behavior.

- End-to-end validation against the entity store is the primary correctness signal.
- Real connector payloads and recorded fixtures are preferred over synthetic mocks.
- Manual inspection and targeted sampling are legitimate validation tools, especially in early phases.
- Automated tests are supportive but never sufficient. The entity store remains the authoritative correctness signal: if tests pass but the persisted entities are incomplete or incorrect, the system is failing.


Tests that pass but produce incorrect real-world data are considered failures.

---

## 7. Non-Goals & Explicit Exclusions

This system intentionally does NOT attempt to solve the following problems. Introducing any of these behaviors into the engine is considered architectural drift.

### Domain Semantics in the Engine

- The engine must never encode domain-specific knowledge, terminology, or logic.
- The engine must not contain hardcoded taxonomies, activity lists, role types, place types, or domain heuristics.
- The engine must not interpret the meaning of canonical dimension values.

Any feature that requires domain awareness belongs in a Lens, not in the engine.

### Implicit or Hidden Behavior

- The engine must not rely on implicit defaults, magic constants, or undocumented assumptions.
- All behavior must be explicitly driven by configuration, metadata, or clearly defined contracts.
- Silent fallbacks or hidden recovery logic are forbidden.

Unexpected behavior is worse than visible failure.

### Probabilistic or Non-Reproducible Logic in Core Processing

- Core pipeline stages must not contain randomness, sampling, or time-based behavior.
- Merge outcomes must not depend on iteration order, hash ordering, or unstable data structures.
- Tie-break logic must always resolve deterministically.

Probabilistic behavior is acceptable only at system boundaries (external APIs, LLMs) and must be captured as input data before deterministic processing begins.

### Permanent Translation Layers

- The system must not maintain permanent translation layers between pipeline stages.
- Universal schema field names must remain authoritative end-to-end.
- Legacy naming must be eliminated rather than accommodated indefinitely.

Translation layers introduce ambiguity, hidden coupling, and long-term technical debt.

### Premature Taxonomy Expansion

- The system must not introduce speculative canonical values, categories, or domain structures without observed evidence from real data.
- Taxonomy growth must be evidence-driven and validated against real payloads.

Speculative modeling creates noise and reduces accuracy.

### Over-Optimization Before Correctness

- Performance optimization must not compromise correctness, clarity, or determinism.
- Caching, concurrency, or batching strategies must preserve reproducibility and auditability.

Correctness always precedes optimization.

---

## 8. How Humans and AI Agents Should Use This Document

This document is the architectural constitution of the system. It defines what must remain true regardless of implementation details, refactoring, or expansion.

All contributors — human and automated — must treat this document as the primary source of truth for architectural intent.

### When Designing or Modifying the System

Before making changes, ask:

- Does this preserve engine purity?
- Does this keep all domain semantics inside lenses?
- Does this maintain determinism and idempotency?
- Does this avoid introducing implicit behavior or hidden coupling?
- Does this improve data quality in the entity store?

If the answer to any of these is unclear or negative, the change should be reconsidered.

### When Adding Features

Features should be justified in terms of:

- Improved data completeness or accuracy.
- Stronger determinism or reproducibility guarantees.
- Better enforcement of architectural boundaries.
- Reduced operational risk or ambiguity.

Features that primarily increase complexity without improving data quality or architectural integrity should be avoided.

### When Using AI Agents

AI agents should:

- Treat this document as immutable architectural guidance.
- Avoid introducing domain logic into engine code.
- Preserve explicit boundaries and contracts.
- Prefer small, incremental changes with clear validation.
- Validate changes using real data whenever possible.
- Fail loudly rather than introducing silent fallback behavior.

Agents should not optimize for convenience, speed, or superficial correctness at the expense of architectural integrity.

### When Resolving Ambiguity

If a design decision is ambiguous:

- Prefer solutions that strengthen determinism, explicitness, and traceability.
- Prefer moving semantics into lenses rather than into the engine.
- Prefer correctness and clarity over cleverness or abstraction.

If uncertainty remains, the ambiguity should be documented and resolved explicitly rather than left implicit.

### Living Governance

This document may evolve deliberately as the system matures, but changes must be:

- Intentional and reviewed.
- Backwards compatible with core principles whenever possible.
- Justified by real operational evidence.
- Reflected consistently across architecture and implementation.

The purpose of this document is stability, clarity, and long-term coherence — not rapid experimentation.

---
## Change Log

**2026-02-06 – Phase 2 Clarifications**
Added Evidence Model section defining Phase 1 surfaces and binding them to lens-owned semantics; formalized deterministic merge as constitutional with connector-blind constraint; clarified OPE vs OPE+Geo; clarified place recognition via any geographic anchor.
