---
description: Generate the complete /docs suite by orchestrating doc agents and diagram agents using the outline→section-chunks pattern to keep orchestrator context lean.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
---

# Generate Complete Documentation Suite (Orchestrator v3 - Section-Chunked)

You are the orchestrator. You MUST follow the section-chunked pattern to keep context lean.

## Core Principle: Outline→Section-Chunks Pattern

Doc subagents NEVER return full documents. Instead:
1. First call: Return outline (≤50 lines)
2. Subsequent calls: Return one section at a time (≤400 lines each)

This keeps orchestrator context bounded regardless of doc size.

## Workflow

### Phase 1: Extract Global Constraints

1. Read docs/target/system-vision.md and docs/target/architecture.md
2. Extract into GLOBAL CONSTRAINTS (max 100 lines):
   - System name, tech stack, key patterns
   - Naming conventions, terminology
   - Cross-cutting concerns (auth, logging, etc.)
   - Immutable invariants
   - Engine vs Lens boundaries

### Phase 2: Generate Diagrams

For each diagram type needed:
1. Call diagram subagent with GLOBAL CONSTRAINTS
2. Receive Mermaid code (max 150 lines)
3. Store diagram text for later inclusion in docs

Diagram types:
- diagram-architecture
- diagram-c4
- diagram-component
- diagram-contribution-flow
- diagram-dependency
- diagram-deployment
- diagram-er
- diagram-network
- diagram-sequence
- diagram-state
- diagram-user-journey

### Phase 3: Generate Docs (Section-by-Section)

For each doc type in order:

**Document Order:**
1. ARCHITECTURE.md (needs: diagram-architecture, diagram-c4, diagram-dependency, diagram-sequence)
2. DATABASE.md (needs: diagram-er)
3. API.md (needs: diagram-sequence)
4. FEATURES.md (needs: diagram-user-journey, diagram-sequence)
5. ONBOARDING.md (needs: none)
6. FRONTEND.md (needs: diagram-component, diagram-state)
7. BACKEND.md (needs: diagram-component, diagram-sequence)
8. DEPLOYMENT.md (needs: diagram-deployment, diagram-network)
9. DEVELOPMENT.md (needs: diagram-contribution-flow)
10. CONFIGURATION.md (needs: none)

**For each document:**

**Step 3a: Get Outline**
1. Call doc subagent with:
   - GLOBAL CONSTRAINTS
   - Required diagrams for this doc
   - Instruction: `task: "outline"`
2. Receive outline (max 50 lines) with format:
   ```markdown
   # [Document Title]

   ## Section: [Heading 1]
   Description: [One-line description]
   Estimated lines: [number]

   ## Section: [Heading 2]
   Description: [One-line description]
   Estimated lines: [number]
   ```

**Step 3b: Create Skeleton**
1. Parse outline to extract section headings
2. Write skeleton file to docs/generated/[FILENAME] with:
   - Document title
   - Section headings from outline
   - Placeholder comment: `<!-- SECTION PENDING: [heading] -->`

**Step 3c: Fill Sections**
For each section in outline:
1. Call doc subagent with:
   - GLOBAL CONSTRAINTS
   - Required diagrams
   - Current skeleton file content
   - Instruction: `task: "section: [heading name]"`
2. Receive section content (≤400 lines)
3. Use Edit tool to replace placeholder with section content
4. Section content should:
   - Reference diagrams: ` ```mermaid\n[diagram content]\n``` `
   - Reference other docs: `[Doc Name](FILENAME.md#section)`
   - Follow GLOBAL CONSTRAINTS for all naming

### Phase 4: Review & Fix

For each completed doc:
1. Call review-docs subagent with:
   - The specific doc file path
   - GLOBAL CONSTRAINTS
   - All other completed docs (for cross-references)
2. Receive patch instructions in format:
   ```markdown
   ## PATCH 1
   SECTION: ## [Heading Name]
   ACTION: REPLACE
   REASON: [Why this change is needed]
   CONTENT:
   [replacement content, max 300 lines]

   ## PATCH 2
   SECTION: ## [Heading Name]
   ACTION: INSERT_AFTER
   REASON: [Why this change is needed]
   CONTENT:
   [new content to insert, max 300 lines]

   ## PATCH 3
   SECTION: ## [Heading Name]
   ACTION: DELETE
   REASON: [Why this section should be removed]
   ```
3. Apply patches using Edit tool

### Phase 5: Final Validation

1. Check all cross-references resolve
2. Verify diagram content is embedded correctly
3. Generate docs/generated/README.md with navigation structure:
   ```markdown
   # Generated Documentation Suite

   Generated on: [timestamp]

   ## Documents
   - [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
   - [DATABASE.md](DATABASE.md) - Database schema and data model
   - [API.md](API.md) - API endpoints and contracts
   - [FEATURES.md](FEATURES.md) - Feature documentation
   - [ONBOARDING.md](ONBOARDING.md) - Developer onboarding guide
   - [FRONTEND.md](FRONTEND.md) - Frontend architecture
   - [BACKEND.md](BACKEND.md) - Backend architecture
   - [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment procedures
   - [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflow
   - [CONFIGURATION.md](CONFIGURATION.md) - Configuration reference

   ## Quality Checks
   - All cross-references validated
   - All diagrams embedded
   - Compliance with GLOBAL CONSTRAINTS verified
   ```
4. Generate CHANGELOG.md with:
   - Generation timestamp
   - List of docs created/updated
   - Summary of review issues and resolutions
   - Any warnings or notes

## Context Budget Enforcement

At any moment, orchestrator context contains:
- GLOBAL CONSTRAINTS: ~100 lines
- Diagram outputs: ~150 lines each (reused across docs)
- Current outline: ~50 lines
- Current section being written: ~400 lines
- **Maximum per doc iteration: ~700 lines**

This scales to unlimited doc size because we process incrementally.

## Error Handling

If a subagent exceeds limits:
1. Truncate the response at the limit
2. Log warning to CHANGELOG.md
3. Request rewrite with explicit line count reminder

If a subagent returns malformed output:
1. Log the issue to CHANGELOG.md
2. Skip that section with a placeholder: `<!-- ERROR: Failed to generate [section] -->`
3. Continue with remaining sections

## Final Output

Print summary:
```
✅ Documentation generation complete

Files generated:
- docs/generated/ARCHITECTURE.md (X lines)
- docs/generated/DATABASE.md (X lines)
[... etc ...]
- docs/generated/CHANGELOG.md

Review issues: X blocking, Y important, Z minor
Context budget: Peak XXX lines (within 700 line target)

Next steps:
- Review generated docs in docs/generated/
- Address any blocking review issues
- Move approved docs to docs/ root when ready
```

## Agent Mapping

- architecture-docs → docs/generated/ARCHITECTURE.md
- database-docs → docs/generated/DATABASE.md
- api-docs → docs/generated/API.md
- features-docs → docs/generated/FEATURES.md
- onboarding-docs → docs/generated/ONBOARDING.md
- frontend-docs → docs/generated/FRONTEND.md
- backend-docs → docs/generated/BACKEND.md
- deployment-docs → docs/generated/DEPLOYMENT.md
- development-docs → docs/generated/DEVELOPMENT.md
- configuration-docs → docs/generated/CONFIGURATION.md
