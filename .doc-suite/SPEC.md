DOC-SUITE (Universal) — Documentation Suite Generator

Audience: Developers

This spec is designed to run on Gemini, Claude, and Codex with the SAME instructions.
It avoids context exhaustion by using disk-backed state and atomic steps.

How to run (same for all agents)

Tell the agent to execute one operation at a time using these exact phrases:

DOC-SUITE: RESET-FULL

DOC-SUITE: INIT

DOC-SUITE: STEP

DOC-SUITE: RUN (optional convenience loop)

DOC-SUITE: DELTA-INIT

DOC-SUITE: FINALIZE

Important: STEP must produce exactly ONE output, then stop.

Hard rules (non-negotiable)

Atomic: STEP produces exactly ONE doc output, then stops.

No chaining: After writing a file and updating the manifest in a STEP, you MUST return a text response immediately. Do not start the next work item until the user provides a new prompt.

Limits:

MAX_FILES_PER_STEP = 20

MAX_LOC_PER_STEP = 2000
If exceeded, split into chunks.

Disk is truth:

Always read/write temp/doc-manifest.json

Discovery is metadata-first:

INIT uses file lists + headers/signatures, not full implementations.

Evidence is bounded (cheap citations):

Cite only technical claims (APIs, behavior, defaults, constraints, data flows).

Cite only from files opened in that STEP.

Format: Evidence: path:line-range

No stale docs after full:

RESET-FULL archives and deletes docs before regenerating.

No speculation:

If you didn’t open it in this step, you can’t claim it.

Output structure

docs/
temp/doc-manifest.json
temp/repo-map.json
temp/doc-coverage-report.md
archive/docs_backup_YYYYMMDD_HHMMSS/

Platform note

Prefer PowerShell-compatible commands on Windows.
Do not assume bash, rg, grep, sed, or awk are installed.
Git may be used when available.

Operation: DOC-SUITE: RESET-FULL

Goal: Remove legacy docs and start a clean full regeneration.

Steps:

If docs/ exists, archive it to:
archive/docs_backup_<timestamp>/

Delete docs/ entirely.

Delete these files if they exist:

temp/doc-manifest.json

temp/repo-map.json

temp/doc-coverage-report.md

Recreate empty docs skeleton directories:

docs/

docs/architecture/subsystems/

docs/reference/

docs/howto/

docs/operations/

Then execute DOC-SUITE: INIT.

Stop.

Result: Guaranteed no lingering legacy documentation.

Operation: DOC-SUITE: INIT

Goal: Create repo inventory and manifest without reading full code.

Steps:

Inventory all files in the repo, excluding:
.git/, node_modules/, dist/, build/, archive/, generated artifacts, docs outputs.

Classify each file as:
source | config | test | script | doc | other

For source/config files:

collect LOC

collect lightweight symbols and imports by reading headers/signatures only

Group files into subsystems using directory roots and entrypoint heuristics.

Chunk subsystems into work items so each work item respects:

<= MAX_FILES_PER_STEP

<= MAX_LOC_PER_STEP

Write:

temp/repo-map.json

temp/doc-manifest.json

Stop. INIT must not generate documentation.

Minimum manifest requirements:

limits

inventory summary

files map:
kind, loc, optional sha256, subsystem, chunk_id, symbols, imports

work.queue[]:
work_id, subsystem, chunk_id, files[], output_path, status(todo/doing/done/blocked)

work.reference_queue[] for reference docs

Operation: DOC-SUITE: STEP

Goal: Complete exactly ONE work.queue item.

Steps:

Load temp/doc-manifest.json.

Select next work item with status = todo.

Mark it doing and persist manifest immediately.

Open only the files listed for that work item.

Build a local citation index while reading:
symbol or config-key -> line range

Write the doc to the output_path.

Doc requirements:

First line: Audience: Developers

Sections:
Overview
Components
Data Flow
Configuration Surface
Public Interfaces
Examples (from opened files only)
Edge Cases / Notes

Mermaid only if it clarifies a flow.

Evidence rules:

Cite only technical claims.

Cite only from files opened in this STEP.

Format: Evidence: path:line-range

Prohibitions:

No speculation

No invented behavior

No references to unopened files

Save the doc.

Update manifest:
mark work item done
store doc hash (optional)
update file hashes (optional)

Terminate turn immediately with a brief summary of the single file created.

Stop.

Operation: DOC-SUITE: RUN (optional)

Goal: Convenience loop to finish all todo work items.

Behavior:

Repeatedly execute STEP until no todo items remain.

If the agent cannot guarantee context stability, do not use RUN.

Stop.

Operation: DOC-SUITE: DELTA-INIT

Goal: Mark what docs need regeneration based on changes.

Steps:

If git is available and baseline commit exists:
changed_files = git diff --name-only baseline..HEAD

Else:
compute file hashes and compare.

Apply delta rules:
a) Changed file -> owning work item becomes todo
b) Added file -> classify and mark todo
c) Deleted file -> remove and flag orphan docs
d) Moved/renamed -> delete + add
e) Shared files -> mark dependents + reference docs
f) Lockfiles -> mark reference docs
g) Ignore non-code paths
h) If >20% changed -> recommend RESET-FULL

Update manifest delta fields.

Stop.

Operation: DOC-SUITE: FINALIZE

Goal: Generate cross-cutting documentation, derive workflows, validate coverage, and clean up empty artifacts.

Phase A — Core and Reference

Generate:

CORE

docs/_index.md

docs/architecture/overview.md

docs/architecture/c4-context.md

docs/architecture/c4-container.md

REFERENCE

docs/reference/module-index.md

docs/reference/configuration.md

docs/reference/api.md (if applicable)

docs/reference/data-model.md (if applicable)

docs/reference/cli.md (if applicable)

Only generate reference docs for surfaces that exist.
Remove stale reference docs that no longer apply.

Phase B — Workflow Discovery (MANDATORY)

Infer real user workflows from:

README and onboarding docs

entrypoints and main modules

build and package files

CLI definitions

API routes

configuration surface

subsystem docs

Derive workflows users realistically perform.
If no workflows can be confidently inferred, generate minimal sensible ones based only on repo signals.

Phase C — How-To Generation

For each discovered workflow:

Generate:
docs/howto/<workflow-slug>.md

Each guide must include:

Audience

Objective

Concrete commands and file references

Links to subsystems and configs

Troubleshooting notes

If zero howtos were generated:
Delete docs/howto/ entirely.

Phase D — Operations Documentation

Detect operational concerns:
CI/CD, Docker, deployment, infra, monitoring.

If present:
Generate docs/operations/runbook.md

If none:
Ensure docs/operations/ does not exist.

Phase E — Validation and Coverage

Validate:

Manifest parses correctly

Every source file is assigned, shared, or excluded

No duplicate ownership

All done items have outputs

No empty generated directories remain

Generate:
temp/doc-coverage-report.md including counts, workflows, and gaps.

Stop.

Recommended workflows

Full rebuild:

DOC-SUITE: RESET-FULL

DOC-SUITE: RUN or repeated STEP

DOC-SUITE: FINALIZE

Incremental update:

DOC-SUITE: DELTA-INIT

DOC-SUITE: RUN or repeated STEP

DOC-SUITE: FINALIZE