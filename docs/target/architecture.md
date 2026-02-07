# Architecture — Universal Entity Extraction Engine

**Status:** Living Architecture  
**Scope:** Engine-Level (Vertical-Agnostic)

This document defines the concrete runtime mechanics, contracts, execution
pipelines, validation rules, and operational guarantees for the Universal Entity
Extraction Engine.

It operationalizes the immutable intent defined in `docs/system-vision.md`. Where
ambiguity exists, the system vision is authoritative.

This document may evolve deliberately over time, provided all changes preserve
the system vision’s invariants.

The engine remains independently valuable and deployable without any specific
vertical. Edinburgh Finds is a reference lens and validation application only.

---

# 1. Purpose and Scope

This document specifies how the Universal Entity Extraction Engine actually
operates at runtime.

It defines:

- Runtime architecture and execution model.
- Pipeline structure and artifact flow.
- Component boundaries and ownership.
- Explicit subsystem contracts.
- Validation and enforcement mechanisms.
- Deterministic and idempotent processing guarantees.
- Reproducibility and traceability behavior.

This document intentionally contains operational detail and implementation
constraints.

Architectural intent, principles, and non-negotiable invariants live in
`docs/system-vision.md` and must not be duplicated or weakened here.

This document applies only to the engine and its integration contracts. All
domain semantics, vertical behavior, and presentation logic remain exclusively
owned by Lens contracts and downstream applications.

### In Scope

- Execution lifecycle from input to persistence.
- Lens resolution, validation, and injection.
- Connector orchestration and ingestion boundaries.
- Extraction contracts and interpretation boundaries.
- Deduplication, merge, and persistence semantics.
- Canonical data model and storage guarantees.
- Validation gates and enforcement mechanisms.
- Determinism, idempotency, and replay guarantees.

### Out of Scope

- Domain vocabulary or taxonomies.
- Presentation semantics, UI behavior, or SEO logic.
- Vertical business rules.
- Application-layer workflows or user interfaces.
- Operational deployment infrastructure (CI/CD, hosting, networking).

---

# 2. Runtime Architecture Overview

At runtime, the system behaves as a pipeline-oriented deterministic execution
engine that transforms queries or entity identifiers into canonical structured
entity records.

The architecture consists of two strictly separated layers:

- **Engine**
  - A universal, domain-blind execution platform responsible for orchestration,
    ingestion, extraction, normalization, deduplication, merge, validation,
    persistence, and lifecycle guarantees.

- **Lens**
  - A pluggable runtime contract that defines domain vocabulary, routing intent,
    mapping rules, canonical registries, module schemas, module triggers, and
    presentation metadata.

The engine consumes Lens contracts as opaque configuration and never embeds,
infers, or hardcodes domain meaning.

---

## 2.1 Execution Model

A single execution processes an input through a strictly ordered pipeline that
produces immutable artifacts at each stage.

Conceptually:

    Input (Query or Entity Identifier)
            ↓
    Lens Resolution + Validation
            ↓
    Planning / Orchestration
            ↓
    Connector Execution
            ↓
    Raw Ingestion Persistence
            ↓
    Source Extraction
            ↓
    Lens Application
            ↓
    Classification + Module Attachment
            ↓
    Cross-Source Deduplication Grouping
            ↓
    Deterministic Merge
            ↓
    Finalization + Persistence

Each stage:

- Consumes immutable inputs.
- Produces immutable outputs.
- Performs no hidden mutation of upstream artifacts.
- Must behave deterministically over captured inputs.

---

## 2.2 Artifact Model

The pipeline operates over explicit artifact types:

| Stage | Artifact | Mutability |
|--------|-----------|-------------|
| Connector Execution | Raw Payload | Immutable once persisted |
| Raw Ingestion | RawIngestion Record | Immutable |
| Source Extraction | ExtractedEntity | Immutable |
| Deduplication | DedupGroup | Immutable |
| Merge | MergedEntity | Immutable |
| Finalization | Persisted Entity | Mutable only via idempotent upsert |

Artifact immutability is enforced by contract and validated by tests where
possible.

Downstream stages must never mutate upstream artifacts.

---

## 2.3 Execution Boundaries

The architecture enforces explicit boundaries:

### Lens Loading Boundary

- Lens contracts are loaded and validated only during bootstrap.
- No runtime component may load, reload, or mutate lens configuration.
- Lens contracts enter runtime exclusively through ExecutionContext.

### Artifact Boundary

- Raw payloads must be persisted before extraction begins.
- Extracted entities are immutable inputs to deduplication and merge.
- Merged entities are immutable inputs to finalization and persistence.

### Determinism Boundary

- External systems (APIs, LLMs) may be probabilistic.
- Once captured as raw artifacts, all downstream processing must be fully
  deterministic.

### Purity Boundary

- Engine code contains no domain semantics.
- All interpretation flows through lens contracts only.

---

## 2.4 Statelessness and Reproducibility

Each execution is fully determined by:

- Input query or entity identifier.
- Validated lens contract (content hash).
- Connector registry metadata.
- Persisted raw artifacts.

No hidden global state, implicit defaults, mutable singletons, or runtime mutation
is permitted.

This enables:

- Idempotent re-execution.
- Deterministic replay from captured artifacts.
- Auditable provenance and traceability.
- Safe backfills and schema migrations.
- Environment-independent behavior.

---

## 2.5 Failure Semantics

Failure behavior is explicit and deterministic:

- Lens validation failures
  - Abort execution before any ingestion or extraction begins.

- Connector failures
  - Failures are isolated per connector and surfaced via metrics and logs.
  - Partial ingestion may proceed depending on orchestration policy.

- Extraction failures
  - Rule-level failures degrade gracefully and never crash the entire pipeline.
  - Validation failures of contracts fail fast.

- Merge and persistence failures
  - Failures are treated as critical and abort execution.

Silent fallback behavior is forbidden.

All failures must be observable and attributable.

---

## 2.6 Non-Goals (Runtime Architecture)

The runtime architecture explicitly does NOT:

- Interpret domain semantics.
- Perform probabilistic or heuristic decision-making inside the engine.
- Maintain hidden caches or implicit state.
- Mutate historical artifacts.
- Embed connector-specific or vertical-specific behavior.
- Perform automatic self-healing of invalid configurations.

Any behavior that violates determinism, purity, or traceability is forbidden.

---

# 3. Engine–Lens Integration and Validation

This section defines how Lens contracts are resolved, validated, materialized,
and consumed by the engine at runtime.

Lens contracts are treated as immutable runtime inputs. They are loaded exactly
once during bootstrap and injected into the execution pipeline via an immutable
ExecutionContext.

No runtime component may load, modify, or directly depend on lens files,
registries, or implementation modules.

---

## 3.1 Lens Resolution and Precedence

The active lens is resolved deterministically using first-match precedence:

1. **CLI override**
   - Explicit command-line flag (e.g., `--lens wine_discovery`).

2. **Environment variable**
   - `LENS_ID` provides environment-level default.

3. **Application configuration**
   - `engine/config/app.yaml → default_lens`.

4. **Dev/Test fallback (non-production only)**
   - Absolute safety net for local development and test execution only.
   - Must be explicitly enabled (e.g., dev-mode config or `--allow-default-lens`).
   - When used, it must emit a prominent warning and persist metadata indicating fallback occurred.

Resolution must be explicit and reproducible. The resolved lens identifier must be logged and persisted as part of execution metadata. Ambiguous lens resolution is treated as a fatal error. Missing lens resolution is treated as a fatal error unless an explicitly enabled Dev/Test fallback is in effect.

---

## 3.2 Lens Loading Lifecycle

Lens loading occurs only during engine bootstrap.

The loader performs the following steps atomically:

1. Load lens definition from disk or packaged resource.
2. Validate lens schema structure.
3. Validate canonical registry integrity.
4. Validate connector references against connector registry.
5. Validate uniqueness of identifiers across rules and registries.
6. Compile and validate regex patterns.
7. Validate module schemas and field definitions.
8. Compute deterministic content hash.
9. Materialize a plain runtime contract.

Any validation failure aborts execution immediately.

No partially valid lens may enter runtime.

Lens contracts must never be reloaded or mutated during execution.

---

## 3.3 Canonical Registry Integrity

All canonical values must be declared in the lens canonical registry.

Validation rules:

- Every canonical reference in mapping rules must exist in the registry.
- Duplicate canonical identifiers are forbidden.
- Orphaned references cause validation failure.
- Registry must be deterministic and stable under serialization.
- Registry ordering must not affect runtime behavior.

The registry is the single source of truth for canonical value existence.

The engine never infers, synthesizes, or normalizes canonical values.

---

## 3.4 Connector Reference Validation

All connector identifiers referenced in lens routing rules must exist in the
engine connector registry.

Validation rules:

- Missing connector references fail fast at bootstrap.
- Silent fallback to placeholder or fake connectors is forbidden.
- Connector capability mismatches are surfaced as validation errors.

This prevents silent production misconfiguration.

---

## 3.5 Module Schema Validation

Module schemas defined by lenses are validated at load time.

Validation rules:

- Module namespace uniqueness.
- Field name uniqueness within module.
- Field type correctness.
- Optional schema constraints (required, enum, range).
- JSON schema validity where applicable.
- No field collision with universal schema.

Invalid module schemas abort execution at bootstrap.

---

## 3.6 ExecutionContext Contract

The ExecutionContext is an immutable carrier object passed through the entire
runtime pipeline.

Responsibilities:

- Identify the active lens.
- Carry the validated lens runtime contract.
- Carry reproducibility metadata.

Representative structure:

    @dataclass(frozen=True)
    class ExecutionContext:
        lens_id: str
        lens_contract: dict
        lens_hash: Optional[str]

Properties:

- Created exactly once during bootstrap.
- Never mutated.
- Contains only plain serializable data.
- Safe for logging, persistence, and replay.
- No live loaders, registries, or mutable references.

---

## 3.7 Context Propagation Rules

The ExecutionContext flows explicitly through all major runtime boundaries:

    CLI / Bootstrap
            ↓
    Planner / Orchestrator
            ↓
    Ingestion Coordination
            ↓
    Extraction Integration
            ↓
    Extractor Implementations
            ↓
    Deduplication and Merge Pipelines

Direct imports of lens loaders or registries outside bootstrap are forbidden.

Runtime components must not reach into filesystem or package resources to obtain
lens data.

---

## 3.8 Extractor Interface Contract

All extractors must accept the execution context explicitly:

    def extract(self, raw_data: dict, *, ctx: ExecutionContext) -> dict:
        ...

Lens-derived behavior must be routed through shared engine-owned helpers rather
than implemented inside individual extractors.

This ensures:

- Consistent behavior across extractors.
- Centralized validation and enforcement.
- Zero domain leakage into extractor implementations.
- Mechanical testability of purity constraints.

---

## 3.9 Enforcement Mechanisms

The following mechanisms enforce the Engine–Lens boundary:

- **Import boundary tests**
  - Engine code must not import lens loaders, registries, or lens packages.

- **Literal detection tests**
  - Prevent hardcoded canonical values or domain literals in engine code.

- **Context presence validation**
  - Missing or malformed ExecutionContext raises immediate error.

- **Bootstrap validation gates**
  - All lens validation must complete before any ingestion or extraction begins.

- **Runtime assertions**
  - Boundary violations fail fast and surface diagnostics.

Violations are treated as architectural defects.

---

## 3.10 Determinism and Versioning Guarantees

Lens contracts are versioned implicitly via content hash.

Guarantees:

- The same lens content hash must produce identical behavior.
- Hash is persisted alongside execution metadata.
- Reprocessing with a different lens hash is considered a distinct execution.
- Historical executions remain reproducible.

Lens changes must be intentional and auditable.

---
# 4. Orchestration and Execution Pipeline

This section defines the concrete end-to-end runtime pipeline and the explicit
contracts between orchestration, ingestion, extraction, lens application,
deduplication, merge, and persistence.

The pipeline is designed to be:

- Lens-driven where semantics are required.
- Deterministic over captured inputs.
- Idempotent across repeated executions.
- Fail-fast on invalid contracts.
- Reality-validatable via entity-store inspection.

---

## 4.1 Pipeline Stages (Canonical Order)

A single execution progresses through the following stages in strict order:

1. **Input**
   - Accept a natural-language query or explicit entity identifier.

2. **Lens Resolution and Validation**
   - Resolve lens_id by precedence (CLI → environment → config → fallback).
   - Load lens configuration exactly once at bootstrap.
   - Validate schema, references, and invariants.
   - Compute lens hash for reproducibility.
   - Inject validated lens contract into ExecutionContext.

3. **Planning**
   - Derive query features deterministically.
   - Select connector execution plan from lens routing rules.
   - Establish execution phases, budgets, ordering, and constraints.

4. **Connector Execution**
   - Execute connectors according to the plan.
   - Enforce rate limits, timeouts, and budgets.
   - Collect raw payloads and connector metadata.

5. **Raw Ingestion Persistence**
   - Persist raw payload artifacts and metadata (source, timestamp, hash).
   - Perform ingestion-level deduplication of identical payloads.
   - Raw artifacts become immutable inputs for downstream stages.

6. **Source Extraction**
   - For each raw artifact, run the source-specific extractor.
   - Extractors MUST NOT solicit or emit canonical dimensions.
   - This includes LLM prompts: requesting canonical fields is a boundary
     violation.
   - Extractors emit:
     - Schema-aligned universal primitives (e.g., entity_name, latitude,
       street_address, phone, website_url).
     - Raw observations required for downstream interpretation
       (e.g., raw_categories, description, connector-native fields).
   - No lens interpretation occurs at this stage.

7. **Lens Application**
   - Apply lens mapping rules to populate canonical dimensions.
   - Evaluate module triggers.
   - Execute module field rules using the generic module extraction engine.
   - Deterministic rules execute before schema-bound LLM extraction.
   - Output consists of canonical dimensions and populated modules.

   ### Default Evidence Surfaces
   - If a mapping rule omits source_fields, the engine searches:
     entity_name, summary, description, raw_categories, street_address.
   - Implementations may additionally search discovered_attributes when a field
     is not present top-level.

8. **Classification**
   - Determine entity_class using deterministic universal rules.
   - A candidate is a place if any geographic anchoring is present:
     - coordinates
     - street address
     - city
     - postcode

9. **Cross-Source Deduplication Grouping**
   - Group extracted entities believed to represent the same real-world entity
     using multi-tier strategies (external identifiers, geo similarity,
     normalized name similarity, content fingerprints).

10. **Deterministic Merge**
    - Merge each deduplication group into a single canonical entity using
      metadata-driven, field-aware deterministic rules.

11. **Finalization and Persistence**
    - Generate stable slugs and derived identifiers.
    - Upsert merged entities idempotently.
    - Persist provenance and external identifiers.
    - Finalization MUST use canonical schema keys only.
    - Legacy keys (e.g., location_lat) are forbidden.

Stages must execute in this order without reordering or shortcutting.

Note: Architectural validation requires demonstrating both the “one perfect entity” end-to-end proof and at least one successful multi-source merge, as defined in `docs/system-vision.md`.


---

## 4.2 Boundary Contracts

The pipeline enforces strict responsibility boundaries.

Each boundary defines what a stage may and may not do.

### Planning Boundary

- Produces a connector execution plan derived exclusively from lens routing rules
  and query features.
- Must not perform network calls, extraction, or persistence.
- Must be deterministic.

### Ingestion Boundary

- Raw artifacts must be persisted before any extraction begins.
- Downstream stages must never mutate raw artifacts.
- Artifact identity is stable across replays.

### Extraction Boundary (Locked Contract)

The extraction stage is split into two explicit phases with a hard contract.

#### Phase 1 — Source Extraction (Connector Adapters)

    extractor.extract(raw_payload, ctx) → primitives + raw_observations

Outputs are limited to:

- Schema primitives (e.g., entity_name, latitude, street_address, phone,
  website_url).
- Raw observations required for downstream interpretation
  (e.g., raw_categories, description, connector-native fields).

Forbidden outputs:

- Any canonical_* dimensions.
- Any modules or module fields.
- Any lens-derived interpretation or domain semantics.

Source extractors must remain strictly domain-blind.

#### Phase 2 — Lens Application (Engine-Owned Interpreters)

    apply_lens_contract(primitives, ctx.lens_contract) → canonical_* + modules

This phase:

- Applies mapping rules.
- Evaluates module triggers.
- Executes module field rules.
- Enforces deterministic ordering and validation.
- Remains domain-blind and metadata-driven.

#### Wiring Convenience

Extractors may invoke shared pipeline helpers only if those helpers are thin
pass-throughs that do not change the extractor’s output contract.

The authoritative boundary is the return type:

- Extractors return only primitives and raw observations.
- Lens application produces all canonical and module-derived fields.

#### Why This Contract Exists

- Makes extractor purity mechanically testable.
- Prevents vertical semantics leaking into extractor implementations.
- Centralizes interpretation logic for auditability and evolution.
- Prevents contributors from treating extractors as semantic layers.

### Deduplication Boundary

- Deduplication groups entities but does not resolve field conflicts.
- No merge or prioritization logic exists at this stage.

### Merge Boundary

- Merge resolves conflicts deterministically using metadata and rules.
- Merge must not call external systems or depend on runtime ordering.

### Persistence Boundary

- Finalization and persistence are the only stages permitted to write canonical
  entities to storage.
- Persistence must be idempotent.

---

## 4.3 Artifact Immutability and Flow Guarantees

All pipeline artifacts are immutable once created.

Rules:

- Raw ingestion artifacts are immutable after persistence.
- Extracted entities are immutable after creation.
- Dedup groups are immutable.
- Merged entities are immutable.
- Persisted entities may only change through idempotent upsert.

No stage may mutate upstream artifacts.

Mutation attempts are considered architectural defects.

---

## 4.4 Idempotency, Replay, and Refresh Semantics

The pipeline supports stable repeated execution.

### Idempotent Execution

- Re-running the same execution updates existing entities rather than creating
  duplicates.
- Upsert keys must be stable and deterministic.

### Deterministic Replay

- When raw artifacts are reused, all downstream processing must produce
  identical outputs.

### Refresh Execution

- External connectors and LLMs may be re-run to capture updated reality.
- Once new artifacts are captured, deterministic processing resumes.
- Refresh vs replay controls are explicit and operator-driven.

---

## 4.5 Observability and Debuggability

The pipeline must expose sufficient observability to support:

- Debugging incorrect extraction or mapping.
- Auditing merge decisions.
- Tracing provenance of fields and values.
- Reproducing historical executions.

Minimum expectations:

- Artifact identifiers logged at each stage.
- Lens hash recorded per execution.
- Connector execution metrics captured.
- Validation failures surfaced clearly.

Observability must not compromise determinism.

---
# 5. Canonical Data Model and Dimensions

This section defines the universal entity data model owned by the engine,
including canonical dimensions, module structure, storage guarantees, and
structural invariants.

The engine owns structure, indexing, persistence, and lifecycle behavior.  
Lenses own the meaning and population rules for all values.

---

## 5.1 Universal Entity Schema

All entities conform to a universal schema that remains stable across all
verticals.

Core structural components:

- **Stable entity identity**
- **entity_class**
  - One of: place, person, organization, event, thing
  - Determined deterministically by engine rules
- **Canonical dimensions**
  - Multi-valued arrays of opaque identifiers
- **Namespaced structured modules**
  - JSON structures for detailed attributes
- **Provenance and external identifiers**

The universal schema is authoritative end-to-end.

No permanent translation layers are permitted between pipeline stages or storage
layers.

Schema evolution must preserve backward compatibility or provide explicit
migration paths.

---

## 5.2 Canonical Dimensions (Universal Structure)

The engine maintains exactly four canonical dimensions. Adding, removing, or redefining canonical dimensions requires explicit architectural review and a corresponding amendment to `docs/system-vision.md`.

Structure is universal.  
Values are opaque and defined exclusively by lenses.

    canonical_activities     TEXT[]
    canonical_roles          TEXT[]
    canonical_place_types    TEXT[]
    canonical_access         TEXT[]

Engine guarantees:

- Arrays are always present (never null).
- Empty array represents absence of observed values.
- Values are treated as opaque identifiers.
- No semantic interpretation exists in engine code.
- No duplicate values within a dimension.
- Ordering is stable and deterministic.

Lens responsibilities:

- Declare allowed values in canonical registry.
- Populate values through mapping rules.
- Provide grouping, labeling, and presentation semantics.

---

## 5.3 Structural Semantics (Engine Perspective Only)

These descriptions are human mnemonics only; the engine must not implement logic that depends on these meanings.

From the engine’s perspective, dimensions are purely structural buckets.

Structural intent only (not semantic meaning):

- canonical_activities — what activities occur
- canonical_roles — what functional role the entity serves
- canonical_place_types — what physical type a place is
- canonical_access — how users engage or access

The engine does not validate semantic correctness of values.

Only registry existence and structural integrity are enforced.

---

## 5.4 Storage and Indexing Guarantees

Canonical dimensions are stored as Postgres text arrays with GIN indexes.

Storage guarantees:

- Efficient containment queries.
- Stable deterministic ordering after merge.
- No duplicate values persisted.
- Arrays always materialized (no nulls).

Indexing strategy is owned by the engine and must not leak semantics.

---

## 5.5 Namespaced Modules (Structural Contract)

Modules store structured attributes that do not belong in the universal schema.

Structural characteristics:

- Each module is a top-level namespace inside a JSON structure.
- Module schemas are defined exclusively by lenses.
- Universal modules are always available (core, location, contact, hours,
  amenities, time_range).
- “Always available” means these namespaces are structurally reserved by the engine; lenses still own module schemas/fields and all population rules (unless explicitly declared as engine-owned universal schemas).
- Domain modules are conditionally attached via lens rules.

Engine guarantees:

- Namespaced structure enforcement.
- No flattened module fields into universal schema.
- No cross-module field collisions.
- Structural validation of module payloads where applicable.
- No semantic interpretation of module fields.

---

## 5.6 Module Storage Format

Persisted module payloads follow a stable nested structure.

Example shape:

    modules:
      sports_facility:
        tennis_courts:
          total: 12
          indoor: 8
          outdoor: 4
          surfaces: ["hard_court", "clay"]
        padel_courts:
          total: 3
          indoor: 3
          covered: true
          heated: true
        booking:
          online_booking_available: true
          advance_booking_days: 7
          booking_url: "https://example.com/book"
        coaching_available: true
        equipment_rental: true
      amenities:
        parking:
          available: true
          spaces: 50
          cost: "free"
        accessibility:
          wheelchair_accessible: true
          accessible_parking: true
          accessible_changing_rooms: true
        facilities: ["changing_rooms", "showers", "cafe", "pro_shop"]

The engine treats module payloads as opaque structured data with only structural
validation applied.

---

## 5.7 Provenance and External Identifiers

Every entity retains explicit provenance information.

Provenance includes:

- Contributing sources.
- Source identifiers.
- Extraction timestamps.
- Confidence metadata where applicable.

External identifiers are preserved as first-class fields.

Engine guarantees:

- Provenance is never silently discarded.
- Provenance survives merges deterministically.
- Conflicting provenance is preserved rather than overwritten.

Provenance supports:

- Debugging and traceability.
- Trust evaluation and conflict resolution.
- Incremental enrichment strategies.
- Long-term data quality monitoring.

---

## 5.8 Data Quality Expectations

The engine prioritizes correctness and completeness of entity data.

Expectations:

- Canonical dimensions populated when evidence exists.
- Modules populated with structured detail when available.
- Null or empty fields treated as signals, not ignored silently.
- No hallucinated or fabricated data.

Incorrect or missing data is treated as a system defect unless explicitly
justified by missing upstream evidence.

---
# 6. Lens Mapping and Canonical Population

This section defines how lenses declare canonical values and how raw observations
are deterministically mapped into canonical dimensions.

The engine owns execution, validation, determinism, and enforcement.  
Lenses own semantics, vocabulary, and interpretation rules.

---

## 6.1 Lens as a Compiled Runtime Contract

A lens is not a draft configuration artifact.

A lens is a compiled, deterministic runtime contract that must be fully valid
before any execution begins.

“Compiled” means materialized once during bootstrap into a plain, serializable runtime contract; no per-execution compilation or runtime mutation is permitted.

Contract properties:

- Deterministic: identical inputs produce identical outputs.
- Fully validated: all references, schemas, and rules verified at load time.
- Versioned: content hash enables reproducibility and debugging.
- Hashable: content-addressable for cache invalidation.
- Test-backed: every rule justified by real fixtures.

Lens loading lifecycle:

    Load lens.yaml from disk
        ↓
    Schema validation
        ↓
    Canonical registry validation
        ↓
    Connector reference validation
        ↓
    Identifier uniqueness validation
        ↓
    Regex compilation validation
        ↓
    Content hash computation
        ↓
    Materialize runtime contract
        ↓
    Inject into ExecutionContext

Any validation failure aborts execution immediately.

No partially valid lens is admitted into runtime.

---

## 6.2 Canonical Registry Authority

All canonical values must be declared exactly once in a canonical registry within
the lens.

The registry is the single source of truth for:

- Allowed canonical identifiers.
- Display metadata.
- Presentation semantics.
- Cross-reference integrity.

Engine enforcement invariants:

- Every mapping rule value must exist in the registry.
- Every module referenced by triggers must exist in the module registry.
- No undeclared canonical values are permitted anywhere in runtime output.
- Orphaned references fail fast at lens load time.

This prevents silent drift and broken downstream interpretation.

---

## 6.3 Mapping Rule Structure

Mapping rules convert raw observations into canonical dimension values.

Rules must be small, composable, explicit, and auditable.

Required fields:

- id — unique identifier.
- pattern — Python-compatible regex.
- dimension — target canonical dimension.
- value — canonical registry reference.
- source_fields — raw fields inspected.
- confidence — extraction confidence.
- applicability — optional constraints.

Rules must not embed domain semantics into engine code.

All semantics live in the lens contract.

---

## 6.4 Mapping Rule Execution Semantics

The engine executes mapping rules generically and deterministically.

Execution guarantees:

- Rules execute over the union of declared source_fields. When source_fields is omitted, the engine searches all available text fields (entity_name, description, raw_categories, summary, street_address).
- First match wins per rule.
- Multiple rules may contribute to the same dimension.
- Duplicate values are deduplicated.
- Ordering is stabilized deterministically.
- Confidence metadata is preserved for merge and provenance.

Mapping never mutates raw inputs.

Mapping produces only canonical dimension values.

---

## 6.5 Evidence-Driven Vocabulary Expansion

Canonical values and mapping rules must be justified by observed real data.

Requirements:

- Every new rule must reference a real raw payload fixture.
- Fixtures must be recorded from actual connector responses.
- Rules without evidence are forbidden.
- Speculative taxonomy expansion is prohibited.

Expansion workflow:

    Capture real payload
        ↓
    Create fixture
        ↓
    Add canonical value to registry
        ↓
    Add mapping rule
        ↓
    Add validation test
        ↓
    Commit together

This preserves correctness and prevents drift.

---

## 6.6 Minimal Viable Lens Strategy

Initial lenses must start with minimal but complete coverage.

Minimum deliverables:

- At least one validation entity.
- At least one value populated per canonical dimension.
- At least one module trigger.
- At least one populated module field.

Acceptance is validated via real database inspection, not mocks.

Lenses expand incrementally based on observed data.

---

## 6.7 Lens Validation Gates

The engine enforces strict validation gates at lens load time.

Required gates:

1. Schema validation.
2. Canonical reference integrity.
3. Connector reference validation.
4. Identifier uniqueness.
5. Regex compilation validation.
6. Smoke coverage validation.
7. Fail-fast enforcement.

Any failure aborts execution immediately.

Lens errors must never reach runtime.

---

## 6.8 Separation of Semantics from Engine Logic

The engine must never embed mapping semantics.

Rules, patterns, values, and interpretation always flow through lens contracts.

Engine responsibilities:

- Execute rules generically.
- Enforce validation and determinism.
- Preserve metadata and provenance.

Lens responsibilities:

- Define all semantics and interpretation logic.
- Provide evidence-backed rules and registries.

Violation of this separation is an architectural defect.

---

## 6.9 Observability and Auditability

Mapping execution must be observable and auditable.

The system must retain:

- Which rules fired.
- Which source fields matched.
- Confidence values.
- Provenance metadata.

This supports debugging, validation, and continuous improvement.

---
# 7. Module Architecture and Field Extraction

This section defines how structured module data is extracted, validated, and
populated using declarative rules defined in lens contracts and executed by a
generic, domain-blind engine interpreter.

Modules are the primary mechanism for capturing rich, structured domain data
beyond universal primitives and canonical dimensions.

The engine owns execution, validation, determinism, and enforcement.  
Lenses own schema, semantics, and extraction intent.

---

## 7.1 Core Principle

Module field extraction is:

- Declarative.
- Lens-owned.
- Schema-driven.
- Executed by a generic engine interpreter.
- Fully domain-blind inside engine code.

No module-specific or domain-specific logic may exist in engine implementations.

All semantics live exclusively in lens contracts.

---

## 7.2 Module Definitions

Each lens defines its domain modules declaratively.

A module definition includes:

- Module name.
- Human-readable description.
- Structured schema (field hierarchy and types).
- Field extraction rules.

Modules are namespaced and attached conditionally via module triggers.

Universal modules are always available.  
Domain modules are lens-defined and conditional.

The engine validates module structure but does not interpret field meaning.

---

## 7.3 Field Rule Structure

Each module declares field_rules that describe how values are extracted.

Representative structure:

    modules:
      sports_facility:
        field_rules:
          - rule_id: extract_pitch_count
            target_path: football_pitches.five_a_side.total
            source_fields: [NumPitches, pitches_total]
            extractor: numeric_parser
            confidence: 0.90
            applicability:
              source: [sport_scotland]
              entity_class: [place]
            normalizers: [round_integer]

          - rule_id: extract_surface_type
            target_path: football_pitches.five_a_side.surface
            source_fields: [Surface, surface_type]
            extractor: regex_capture
            pattern: "(?i)(3G|4G|grass|artificial)"
            confidence: 0.85
            normalizers: [lowercase, list_wrap]

Required fields:

- rule_id — unique identifier.
- target_path — JSON path inside module namespace.
- source_fields — raw fields inspected.
- extractor — generic extractor type.
- confidence — extraction confidence.

Optional fields:

- applicability — source and entity constraints.
- normalizers — ordered post-processing pipeline.
- conditions — conditional execution guards.
- pattern / schema — extractor-specific parameters.

---

## 7.4 Extractor Vocabulary

The engine maintains a small, stable vocabulary of generic extractors.

### Deterministic Extractors

- numeric_parser
- regex_capture
- json_path
- boolean_coercion
- coalesce
- normalize
- array_builder
- string_template

These extractors operate only on structure and generic transformation logic.

No extractor may encode domain semantics.

### LLM Extractors

- llm_structured

Constraints:

- Schema-bound only (validated output).
- Evidence anchored where possible.
- Deterministic rules always run first.
- At most one LLM call per module per payload.

Adding new extractor types requires architectural review, purity validation,
documentation, and test coverage.

---

## 7.5 Execution Semantics

For each entity and each attached module:

1. Select applicable rules based on source and entity_class.
2. Execute deterministic rules first.
3. Populate fields when values are extracted successfully.
4. Evaluate conditions for remaining LLM rules.
5. Build a schema covering only remaining fields.
6. Execute a single batched LLM call if required.
7. Validate and normalize LLM outputs.
8. Write results to target paths.
9. Do not resolve cross-source conflicts here.

Module extraction must never mutate raw inputs.

Partial population is permitted.

---

## 7.6 Source Awareness

Module extraction requires source awareness.

Each execution must know:

- Which connector produced the raw payload.
- Which entity_class is being processed.

Applicability filtering and conditional logic rely on this metadata.

Source awareness must be provided explicitly through function signatures or
execution context.

Implicit global state is forbidden.

---

## 7.7 Conditions and Normalizers

### Conditions

Conditions determine whether a rule should execute.

Supported condition types:

- field_not_populated
- any_field_missing
- source_has_field
- value_present

Conditions are evaluated before rule execution.

### Normalizers

Normalizers form an ordered pipeline applied after extraction.

Properties:

- Pure functions.
- Deterministic.
- Executed left-to-right.
- No side effects.

Common normalizers:

- trim
- lowercase
- uppercase
- list_wrap
- comma_split
- round_integer

---

## 7.8 Error Handling and Degradation

The system must degrade gracefully on rule failures.

Policies:

- Deterministic rule failures:
  - Log rule_id, source, error.
  - Skip field.
  - Continue execution.

- LLM failures:
  - Log module, source, error.
  - Continue with partial module data.

- Lens validation failures:
  - Fail fast at bootstrap.
  - Abort execution.

Module extraction must never crash the entire entity pipeline due to individual
rule failure.

---

## 7.9 Conflict Resolution Rules

When multiple rules target the same target_path:

- First successful match wins.
- Conditions should prevent overwriting.
- Deterministic rules take precedence over LLM rules.

Rule ordering must be deterministic.

---

## 7.10 Purity and Enforcement

Non-negotiable constraints:

- No domain logic in engine code.
- No module-specific branching.
- No hardcoded field semantics.
- No dynamic schema inference.
- No extractor-specific special cases.

Enforcement mechanisms:

- Purity tests.
- Static analysis.
- Contract tests.
- Lens validation gates.

Violations are architectural defects.

---

## 7.11 MVP Sequencing and Acceptance

Implementation must proceed in staged validation.

Phase 1:

- Deterministic-only extraction.
- 5–10 rules for a single validation entity.
- At least one populated module field persisted.

Phase 2:

- Introduce LLM extraction under constraints.
- Validate batch behavior and confidence handling.

Acceptance criteria:

- At least one non-null module field persisted in production schema.
- Deterministic extraction validated on real fixtures.
- LLM extraction validated with schema-bound output.
- No engine purity violations.
- Source awareness enforced.
- Error handling verified.
- ≤ 1 LLM call per module per payload.

---
# 8. Field Naming Authority and Schema Alignment

This section defines how universal schema field names are enforced across the
entire pipeline and how legacy naming drift is prevented permanently.

The universal schema is the single authoritative contract for all primitive
entity fields.

---

## 8.1 Canonical Schema Authority

The schema defined in engine configuration is the sole authority for universal
field names.

Properties:

- All extractors must emit schema-aligned field names directly.
- Finalization consumes schema-aligned field names directly.
- No translation layers are permitted between stages.
- Schema evolution is explicit and versioned.

Any deviation from schema naming is considered a defect.

---

## 8.2 Boundary Between Field Classes

The pipeline distinguishes three classes of fields.

### Schema Primitives (Engine-Owned)

Produced by source extractors:

- entity_name
- latitude
- longitude
- street_address
- city
- postcode
- phone
- email
- website_url
- time fields
- identifiers

These fields are governed strictly by the universal schema.

### Canonical Dimensions (Lens-Owned)

Produced exclusively by lens mapping rules:

- canonical_activities
- canonical_roles
- canonical_place_types
- canonical_access

Extractors must never emit these fields.

### Modules (Lens-Owned)

Produced exclusively by module extraction rules:

- modules.{module_name}.*

Extractors must never emit module fields.

### Raw Observations (Permitted)

Source-specific raw fields may pass through extraction for downstream
interpretation but are not part of the canonical schema.

---

## 8.3 Legacy Naming Detection

The engine detects legacy or invalid naming patterns during extraction.

Examples of legacy patterns:

- location_*
- contact_*
- address_*
- ambiguous aliases (e.g., website instead of website_url)

Detection behavior:

- Warning during migration.
- Hard error once migration completes.

Validation must not reject legitimate raw observations.

---

## 8.4 Validation Strategy

Validation rules:

- Validate only fields that claim to be canonical primitives.
- Allow unknown keys as raw observations.
- Flag legacy naming patterns explicitly.
- Never silently discard fields.

Validation may run in strict or permissive mode based on environment.

---

## 8.5 Migration Strategy

Migration proceeds in two phases.

### Phase 1 — Compatibility

- Warn on legacy naming patterns.
- Allow execution to continue.
- Monitor warnings.

### Phase 2 — Enforcement

- Treat legacy patterns as fatal errors.
- CI enforces strict validation.
- Prevent regressions permanently.

---

## 8.6 Regression Guarantees

Regression tests must validate that schema primitives survive the pipeline
unchanged from extraction through finalization.

Tests must use real fixtures rather than mocks.

---

## 8.7 Non-Goals

- No permanent translation layers.
- No duplicate schema authorities.
- No connector-specific naming logic in finalization.
- No silent field coercion.
- No shadow schemas.

All schema authority remains centralized.

---
# 9. Deterministic Multi-Source Merge

This section defines how extracted entities from multiple sources are merged into
a single canonical entity deterministically, idempotently, and without domain
semantics.

Merge logic operates strictly after deduplication grouping and before final
persistence.

---

## 9.1 Core Principle

Multi-source merge is:

- Deterministic.
- Field-aware.
- Metadata-driven.
- Domain-blind.
- Idempotent.

Merge consumes connector trust metadata and extraction confidence but never
hardcodes connector names or domain logic.

Normative merge requirements:

- Missingness definition must be explicit and shared across all merge
  strategies.
- Inputs must be pre-sorted by (-trust, connector_id, extracted_entity.id)
  before field-level merge logic executes.

---

## 9.2 Merge Position in Pipeline

Merge occurs:

    Deduplication Grouping
            ↓
        Deterministic Merge
            ↓
    Finalization and Persistence

Merge never performs network calls or external I/O.

Merge operates only on captured artifacts.

---

## 9.3 Trust Model (Metadata-Driven)

Trust is expressed through connector registry metadata.

Representative attributes:

- trust_tier — high | medium | low
- default_priority — lower value wins

Merge logic consumes metadata values only.

Connector names must never appear in merge logic.

---

## 9.4 Field-Group Merge Strategies

Different field classes use different deterministic strategies.

- Field-group strategies must be explicitly declared and stable across runs.

### Identity and Display Fields

Examples:

- entity_name
- summary
- address fields

Strategy:

- Prefer higher trust_tier unless empty or unusable.
- Prefer more complete values deterministically.
- Tie-break by default_priority then lexicographic stable source identifier (e.g., connector_id).

---

### Geo Fields

Examples:

- latitude
- longitude

Strategy:

- Prefer explicit precision metadata if available.
- Else higher trust_tier.
- Else greater decimal precision.
- Never compute centroids.
- Tie-break by priority then lexicographic stable source identifier (e.g., connector_id).

---

### Contact and Presence Fields

Examples:

- phone
- email
- website_url
- social URLs

Strategy:

- Deterministic quality scoring based on structure only.
- Allow higher-quality crowdsourced values to win over sparse official values.
- Tie-break by quality → trust → priority → lexicographic stable source identifier (e.g., connector_id).

Quality scoring must never use external validation or network calls.

---

### Canonical Dimension Arrays

Examples:

- canonical_activities
- canonical_roles
- canonical_place_types
- canonical_access

Strategy:

- Union all values.
- Normalize values.
- Deduplicate.
- Lexicographically sort.
- No weighting or ranking.

---

### Modules JSON Structures

Strategy:

- Modules recursive merge algorithm.
- Object vs object → recursive merge.
- Array vs array:
  - Scalar arrays → concatenate, deduplicate, sort.
  - Object arrays → select wholesale from winning source.
- Type mismatch → higher trust wins wholesale.
- Per-leaf selection:
  - trust → confidence (if present) → completeness.

Confidence is normalized to 0.0–1.0 when present.

---

### Provenance and External Identifiers

Strategy:

- Always union.
- Never overwrite.
- Track all contributors.
- Determine primary source via trust metadata.

---

## 9.5 Deterministic Tie-Break Cascade

When conflicts remain:

1. trust_tier
2. quality score (if applicable)
3. confidence (if applicable)
4. completeness
5. default_priority
6. lexicographic stable source identifier (e.g., connector_id)

All merges must resolve deterministically.

---

## 9.6 Idempotency Guarantees

Given identical inputs:

- Merge output must be identical across runs.
- Ordering must remain stable.
- No randomness or iteration-order dependence permitted.

Repeated execution converges to stable state.

---

## 9.7 Error Handling

Merge must never crash due to malformed or missing data.

Invalid values are skipped with logging.

Structural conflicts preserve higher-trust data.

---

## 9.8 Observability and Provenance

Merge must retain sufficient metadata to audit decisions.

Where feasible:

- Record contributing sources.
- Track confidence.
- Preserve conflict provenance.

---

## 9.9 Non-Goals

- No domain-specific branching.
- No connector name dependencies.
- No probabilistic selection.
- No geographic centroid computation.
- No permanent translation layers.

---
# 10. Connector Architecture and Extensibility

This section defines the connector abstraction, registry metadata contract, and
scaling guarantees for integrating unlimited external data sources into the
engine.

Connectors are pluggable, self-describing components that integrate through a
stable interface and metadata-driven orchestration.

---

## 10.1 Connector Interface Contract

All connectors implement a common abstract interface.

Representative responsibilities:

- Fetch raw data from external source.
- Detect ingestion-level duplicates.
- Return raw payloads and connector metadata to the engine for persistence as immutable raw artifacts.

Interface shape:

    class BaseConnector(ABC):
        async def fetch(self, query: str) -> RawData
        async def is_duplicate(self, data: RawData) -> bool

Raw artifact persistence is owned by the engine ingestion stage; connectors must not directly write canonical entities.

The interface is intentionally minimal and domain-blind.

---

## 10.2 Connector Registry Metadata

Each connector registers a ConnectorSpec with metadata.

Representative attributes:

- name
- cost_tier — free | paid | premium
- trust_tier — high | medium | low
- default_priority — deterministic tie-breaker
- phase — discovery | enrichment
- timeout_seconds
- rate_limit
- capabilities

Registry metadata is consumed generically by orchestration and merge.

No connector-specific logic may appear outside connector implementations.

---

## 10.3 Pluggable Integration Model

Adding a connector requires:

1. Implementing the BaseConnector interface.
2. Registering metadata in the connector registry.
3. Referencing the connector from lens routing rules.

No orchestration changes are required.

---

## 10.4 Horizontal and Vertical Scaling

### Horizontal Scaling (New Verticals)

New verticals introduce specialized connectors via lens configuration.

Engine code remains unchanged.

### Vertical Enrichment (Existing Verticals)

Existing verticals continuously add enrichment connectors.

Orchestration adapts automatically based on metadata and lens routing rules.

---

## 10.5 Cross-Vertical Reuse

Some connectors may serve multiple lenses.

Each lens configures routing behavior independently.

The engine does not couple connectors to any vertical.

---

## 10.6 Connector Lifecycle

Connector lifecycle stages:

- Development
- Registration
- Lens integration
- Validation
- Production
- Monitoring

Lifecycle management is operational, not architectural.

---

## 10.7 Quality Metrics and Observability

Each connector should emit quality metrics:

- Coverage
- Freshness
- Confidence
- Cost
- Latency
- Failure rates

Metrics support operational tuning and quality monitoring.

---

## 10.8 Scaling Guarantees

The architecture supports:

- Hundreds of connectors.
- Multiple simultaneous verticals.
- Metadata-driven orchestration.
- Deterministic conflict resolution.

Connector growth must not degrade engine purity or determinism.

---

## 10.9 Non-Goals

- No hardcoded connector logic in engine orchestration.
- No connector-specific branching in merge.
- No vertical assumptions in connector interfaces.
- No implicit connector dependencies.

---
# 11. End-to-End Data Flow and Validation Semantics

This section defines the validation gates, integrity guarantees, and enforcement
mechanisms that ensure correctness, determinism, and architectural purity across
the entire system lifecycle.

Validation exists to prevent silent corruption, drift, and ambiguity.

---

## 11.1 Validation Layers

Validation operates at multiple layers.

### Design-Time Validation

- Lens schema validation.
- Canonical registry integrity.
- Connector reference validation.
- Module schema validation.
- Rule structure validation.
- Extractor vocabulary validation.

Failures block merge to main branch.

---

### Bootstrap Validation

- Lens loading validation.
- Regex compilation.
- Registry integrity.
- Connector registry resolution.
- Module schema validation.

Failures abort execution immediately.

---

### Runtime Validation

- ExecutionContext presence.
- Schema primitive validation.
- Field naming validation.
- Extraction boundary enforcement.
- Merge contract enforcement.
- Finalization enforces canonical schema keys only.
- Legacy keys (e.g., location_lat) are forbidden.

Runtime validation may fail fast or degrade gracefully depending on severity.

---

### Persistence Validation

- Schema conformity.
- Referential integrity.
- Idempotency constraints.
- Index consistency.

Persistence failures abort execution.

---

## 11.2 Fail-Fast vs Graceful Degradation

Failures are classified by blast radius.

### Fail-Fast Conditions

- Invalid lens schema or registry.
- Missing connector references.
- Schema violations.
- Contract boundary violations.
- Corrupt module schemas.

Execution aborts immediately.

---

### Graceful Degradation Conditions

- Individual rule failures.
- Partial connector failures.
- LLM extraction failures.
- Non-critical normalization errors.

Execution continues with partial results and explicit logging.

---

## 11.3 Data Integrity Guarantees

The system guarantees:

- No silent data loss.
- No silent fallback behavior.
- No implicit defaults.
- No hidden mutation of artifacts.
- Deterministic output over captured inputs.
- Idempotent persistence.

Violations are treated as defects.

---

## 11.4 Observability and Auditability

The system must expose sufficient telemetry to support:

- Traceability of field origins.
- Rule execution visibility.
- Connector performance analysis.
- Merge decision auditing.
- Regression detection.

Minimum artifacts:

- Execution identifier.
- Lens hash.
- Artifact identifiers.
- Connector metrics.
- Validation events.

---

## 11.5 CI Enforcement

CI must enforce:

- Lens validation.
- Purity tests.
- Contract tests.
- Regression tests on real fixtures.
- Schema stability tests.

Architectural regressions must block merge.

---

## 11.6 Operational Safety

Operational controls must:

- Prevent accidental schema drift.
- Surface misconfiguration early.
- Support safe reprocessing and backfills.
- Preserve reproducibility.

---

## 11.7 Non-Goals

- No silent auto-healing.
- No implicit migrations.
- No probabilistic validation.
- No environment-specific behavior divergence.

---
# 12. System Evolution, Scaling, and Governance

This section defines how the system evolves safely over time while preserving
architectural integrity, determinism, and long-term maintainability.

---

## 12.1 Scaling Dimensions

The architecture supports scaling across multiple axes.

### Connector Scale

- Hundreds of connectors may coexist.
- Registry metadata enables orchestration without code changes.
- Connector growth must not impact engine purity.

### Lens Scale

- Many lenses may coexist simultaneously.
- Each lens remains isolated and independently versioned.
- Lens changes never require engine changes.

### Data Scale

- Entity volume may grow arbitrarily.
- Storage and indexing strategies must preserve query performance.
- Merge determinism must remain stable at scale.

### Execution Scale

- Parallel execution is permitted only where determinism is preserved.
- Concurrency must not introduce race conditions or nondeterminism.

---

## 12.2 Backward Compatibility

Backward compatibility is mandatory for:

- Universal schema.
- Canonical dimensions.
- Module namespace stability.
- Connector interfaces.
- Execution contracts.

Breaking changes require explicit migration strategy and tooling.

Silent breaking changes are forbidden.

---

## 12.3 Schema Evolution Discipline

Schema evolution rules:

- Additive changes preferred.
- Deprecated fields require migration window.
- Permanent translation layers are forbidden.
- Schema changes require regression validation on real data.

---

## 12.4 Lens Evolution Discipline

Lens evolution rules:

- All new rules must be evidence-backed.
- Canonical registry growth must be justified.
- Rules must remain deterministic.
- Lens changes must be versioned and auditable.

---

## 12.5 Architectural Governance

All changes must preserve:

- Engine purity.
- Determinism.
- Idempotency.
- Lens ownership of semantics.
- Validation rigor.

Architectural reviews are mandatory for:

- New extractor types.
- New canonical dimensions.
- Merge strategy changes.
- Connector interface changes.

---

## 12.6 AI Agent Operating Rules

AI agents must:

- Treat system-vision.md as immutable constitution.
- Preserve architectural boundaries.
- Avoid introducing domain semantics into engine code.
- Prefer small, auditable changes.
- Validate changes with real fixtures.
- Fail loudly rather than introduce silent behavior.

---

## 12.7 Living Documentation

This document evolves deliberately.

Changes must:

- Be reviewed.
- Preserve invariants.
- Be consistent across docs and code.
- Be traceable.

The purpose of this document is long-term coherence, not convenience.

---
## Change Log

**2026-02 — Phase 2 Alignment**  
Formalized extraction boundary (no canonical solicitation), default evidence surfaces, geographic anchoring for classification, deterministic merge contract, and canonical-only finalization per LA-002/009/011 and DM-001–006.