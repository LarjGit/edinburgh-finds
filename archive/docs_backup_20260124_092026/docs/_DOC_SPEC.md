# Repo Documentation Suite Spec

## Goal

Generate a comprehensive, exhaustive docs suite by systematically analyzing every line of code in the repository as the source of truth.

**No guessing. No hand-waving. If not found in repo, say "Not found in repo".**

Every module, file, class, function, configuration option, and capability must be documented in detail.

## Documentation Philosophy

1. **Exhaustive Coverage**: Every Python module, TypeScript component, YAML config, and CLI script must appear in the docs
2. **Deep Technical Detail**: Document implementations, algorithms, data flows - not just high-level summaries
3. **Evidence-Based**: Every claim must cite specific file paths, line numbers, or code symbols
4. **User-Centric**: Complex subsystems need tutorial-style explanations with real examples
5. **Completeness Check**: Before finalizing, verify every source file is represented in some doc

## Required Files to Create/Update

### Core Documentation
- docs/\_index.md (comprehensive table of contents)
- docs/product.md (complete product vision and capabilities)
- docs/quickstart.md (detailed setup with all prerequisites)
- docs/contributing.md (development workflow, coding standards)
- docs/security.md (security model, authentication, authorization)
- docs/testing.md (all test types, snapshot testing, validation)

### Reference Documentation (COMPREHENSIVE)
- docs/reference/configuration.md
  - **EVERY** environment variable (type, purpose, default, examples)
  - Complete entity_model.yaml schema (all entity classes, dimensions, modules with field-by-field breakdown)
  - Complete lens.yaml schema (facets, values, mapping_rules, modules, triggers, SEO templates with examples)
  - All CLI flags and options
  - Monitoring/alert configurations

- docs/reference/interfaces.md
  - Every CLI command with full option reference
  - Every API endpoint (if applicable)
  - Every script entry point with usage examples

- docs/reference/data-model.md
  - Full ERD with Mermaid diagram
  - Every table, column with types and constraints
  - Index strategy and rationale
  - Migration procedures

- docs/reference/module-index.md (NEW)
  - Alphabetical index of every Python module
  - One-line purpose for each
  - Evidence: file path

### Architecture Documentation (DETAILED)
- docs/architecture/overview.md
  - Complete system decomposition
  - All major subsystems with boundaries
  - Full technology stack
  - Data flow diagrams

- docs/architecture/c4-context.md (Mermaid C4 context diagram)
- docs/architecture/c4-container.md (Mermaid C4 container diagram)

- docs/architecture/subsystems/ (NEW - detailed subsystem docs)
  - ingestion-pipeline.md
    - All 6+ connectors (Google Places, OSM, Serper, Sport Scotland, Edinburgh Council, Open Charge Map)
    - Rate limiting, retry logic, health checks
    - Deduplication algorithms
    - Storage mechanisms
    - Summary reporting

  - extraction-engine.md
    - LLM client architecture (Instructor integration, caching, cost tracking)
    - Entity classifier implementation
    - All extractor implementations (one per connector)
    - Attribute splitting, category mapping
    - Merging and deduplication logic
    - Quarantine and health systems

  - orchestration.md (CRITICAL - currently undocumented)
    - Execution plan structure
    - Phase system (DISCOVERY → STRUCTURED → ENRICHMENT)
    - Condition evaluation (budget, confidence, query features)
    - Execution context management
    - Connector coordination
    - Trust level conflict resolution

  - schema-system.md
    - YAML parser implementation
    - All generators: Pydantic, TypeScript, Prisma, Python FieldSpec
    - Validation rules
    - Code generation algorithms

  - lens-system.md (CRITICAL - currently superficial)
    - Lens loader architecture
    - Validator implementation
    - Lens ops (operations on lens definitions)
    - Module trigger evaluation
    - Facet interpretation and mapping
    - Derived grouping computation
    - SEO template rendering

  - resolution-merging.md
    - Entity deduplication algorithms
    - Conflict resolution (trust levels, golden data model)
    - Merging strategies
    - Quarantine workflow
    - Health check implementation

### Operations Documentation
- docs/operations/runbook.md
  - Complete deployment procedures
  - Monitoring and alerting setup
  - Backup and recovery procedures
  - Scaling strategies
  - Troubleshooting guide for common issues

- docs/operations/cost-management.md (NEW)
  - LLM cost tracking mechanisms
  - Cost reporting and analysis
  - Budget controls and thresholds
  - Optimization strategies

### How-To Guides (COMPREHENSIVE - minimum 15 guides)
- docs/howto/run-ingestion-google-places.md
- docs/howto/run-ingestion-osm.md
- docs/howto/run-ingestion-serper.md
- docs/howto/run-ingestion-sport-scotland.md
- docs/howto/run-ingestion-edinburgh-council.md
- docs/howto/run-ingestion-open-charge-map.md
- docs/howto/configure-new-lens.md (DETAILED walkthrough of every lens.yaml section)
- docs/howto/add-new-entity-type.md
- docs/howto/add-new-extractor.md
- docs/howto/configure-llm-prompts.md
- docs/howto/tune-extraction-quality.md
- docs/howto/manage-schema-migrations.md
- docs/howto/interpret-orchestration-plans.md
- docs/howto/debug-extraction-failures.md
- docs/howto/monitor-costs.md
- docs/howto/configure-trust-levels.md
- docs/howto/use-snapshot-testing.md
- docs/howto/deploy-to-production.md
- docs/howto/inspect-database.md
- docs/howto/configure-monitoring-alerts.md

Each how-to must:
- Use real code examples from the repository
- Reference actual config files with line numbers
- Explain decision points and trade-offs
- Include troubleshooting tips

### Architecture Decision Records
- docs/architecture/decisions/ (ADRs for discoverable major decisions)

## Documentation Rules

1. **Plain English**: Write for human readers, not machines
2. **Audience Declaration**: Every doc starts with "Audience: ..."
3. **Evidence Required**: Every non-trivial claim must include:
   ```
   Evidence: <file_path> (<symbol/class/function> or line range)
   ```
4. **Mermaid Diagrams**: Use for C4 diagrams, ERDs, flow diagrams
5. **Real Examples**: All code examples must be actual code from the repo
6. **Completeness**: If a subsystem has 10 components, document all 10

## Quality Gates

Before marking documentation as complete:

1. **Module Coverage**: Verify every .py file under engine/ is mentioned in docs
2. **Config Coverage**: Every field in entity_model.yaml and lens.yaml is documented
3. **CLI Coverage**: Every script in engine/scripts/ has a how-to or reference entry
4. **Depth Check**: No major subsystem (ingestion, extraction, orchestration, schema, lens) has less than 1000 words
5. **Evidence Audit**: Spot-check 10 random evidence citations - do they point to real code?
