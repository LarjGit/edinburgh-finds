---
description: Generate the complete /docs suite by orchestrating doc agents and diagram agents. The orchestrator saves files; subagents only return text.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
---

# Generate Complete Documentation Suite (Orchestrator v2)

You are the orchestrator. You MUST:
- Read architectural authorities first.
- Call subagents to produce content (doc sections and diagrams are both â€œcontent producersâ€).
- Save outputs to /docs/*.md.
- Ensure consistent cross-links.
- Run a review agent at the end and apply fixes.

## 0) Read architectural authorities first (MANDATORY)
Read:
- docs/target/system-vision.md
- docs/target/architecture.md

Extract their non-negotiable constraints into <=10 bullets called "GLOBAL CONSTRAINTS".
These constraints apply to all doc outputs and must be included in each doc agent call.

## 1) Dependency graph (doc -> prerequisites)

- docs/ARCHITECTURE.md:
  - diagram-architecture
  - diagram-c4
  - diagram-dependency
  - diagram-sequence

- docs/DATABASE.md:
  - diagram-er

- docs/API.md:
  - diagram-sequence

- docs/FEATURES.md:
  - diagram-user-journey
  - diagram-sequence

- docs/ONBOARDING.md:
  - (none)

- docs/FRONTEND.md:
  - diagram-component
  - diagram-state

- docs/BACKEND.md:
  - diagram-component
  - diagram-sequence

- docs/DEPLOYMENT.md:
  - diagram-deployment
  - diagram-network

- docs/DEVELOPMENT.md:
  - diagram-contribution-flow

- docs/CONFIGURATION.md:
  - (none)

## 2) Execution protocol (applies to EVERY doc)
For each document:
A) Run each prerequisite subagent and capture its returned text exactly.
B) Call the doc subagent with:
   - GLOBAL CONSTRAINTS
   - ARTIFACTS: the prerequisite outputs (diagrams etc.)
   - Any repo snippets it requests (use Read/Glob/Grep)
C) The doc subagent MUST return a complete Markdown file body for that doc.
D) Orchestrator writes it to the correct path under /docs.

## 3) Ensure folder structure exists
Create if missing:
- docs/
- docs/diagrams/ (optional; only use if you decide to save diagrams separately)

## 4) Generate documents in this order

1) ARCHITECTURE.md
   - prereqs: diagram-architecture, diagram-c4, diagram-dependency, diagram-sequence
   - doc agent: architecture-docs
   - write: docs/ARCHITECTURE.md

2) DATABASE.md
   - prereq: diagram-er
   - doc agent: database-docs
   - write: docs/DATABASE.md

3) API.md
   - prereq: diagram-sequence
   - doc agent: api-docs
   - write: docs/API.md

4) FEATURES.md
   - prereqs: diagram-user-journey, diagram-sequence
   - doc agent: features-docs
   - write: docs/FEATURES.md

5) ONBOARDING.md
   - doc agent: onboarding-docs
   - write: docs/ONBOARDING.md

6) FRONTEND.md
   - prereqs: diagram-component, diagram-state
   - doc agent: frontend-docs
   - write: docs/FRONTEND.md

7) BACKEND.md
   - prereqs: diagram-component, diagram-sequence
   - doc agent: backend-docs
   - write: docs/BACKEND.md

8) DEPLOYMENT.md
   - prereqs: diagram-deployment, diagram-network
   - doc agent: deployment-docs
   - write: docs/DEPLOYMENT.md

9) DEVELOPMENT.md
   - prereq: diagram-contribution-flow
   - doc agent: development-docs
   - write: docs/DEVELOPMENT.md

10) CONFIGURATION.md
   - doc agent: configuration-docs
   - write: docs/CONFIGURATION.md

11) CHANGELOG.md
   - Orchestrator generates this directly (no subagent):
     - Include generation date/time
     - List all docs written/updated
     - Summarize major decisions/inferences
     - Include review issues (from review-docs) and whether applied

## 5) Review + fix pass (MANDATORY)
After writing all docs:
- Call subagent: review-docs
- Provide:
  - GLOBAL CONSTRAINTS
  - List of generated doc paths
- review-docs returns:
  - Issue list
  - Concrete patch suggestions per file (exact replacements)
Apply fixes by editing the affected docs (Write).

## 6) Final output
Print:
- List of files generated/updated
- Any review issues remaining
- Suggested cadence for re-runs
