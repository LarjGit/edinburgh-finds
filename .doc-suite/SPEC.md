DOC-SUITE (Universal) — Documentation Suite Generator

Audience: Developers

This specification is designed to run consistently on Gemini, Claude, and Codex using the SAME instructions.
It avoids context exhaustion by using disk-backed state, atomic work units, and explicit execution control.

How to run (public interface)

Only the following commands are supported:

DOC-SUITE: FULL [AUTO]
DOC-SUITE: DELTA [AUTO]
DOC-SUITE: STEP
DOC-SUITE: FINALIZE

Execution mode rule (MANDATORY)

If AUTO is present → run automatically to completion.

If AUTO is NOT present → default to STEP mode.

The agent MUST NOT infer execution mode implicitly.

Examples:

DOC-SUITE: FULL


→ Prepare only, then wait for STEP commands.

DOC-SUITE: FULL AUTO


→ Run everything automatically to completion.

DOC-SUITE: DELTA


→ Detect changes only, then wait for STEP commands.

DOC-SUITE: DELTA AUTO


→ Apply delta and regenerate automatically.

Dispatch rule (MANDATORY)

Only execute an operation if the user message contains a line beginning exactly with:

DOC-SUITE:


If the user message does not contain this prefix:

Do not execute anything.

Ask the user to provide a DOC-SUITE command.

Hard rules (non-negotiable)
Atomicity

STEP produces exactly ONE document and then stops.

No chaining

After a STEP completes and the manifest is updated, the agent MUST stop and wait for the next user command.

Limits
MAX_FILES_PER_STEP = 20
MAX_LOC_PER_STEP   = 2000


If limits are exceeded, the subsystem must be chunked deterministically.

Disk is truth

Always read and write temp/doc-manifest.json.

Never rely on memory for state.

Discovery is metadata-first

Inventory reads file paths and lightweight headers only.

Full implementations are only read during STEP.

Evidence is bounded (cheap citations)

Cite only technical claims (APIs, behavior, defaults, constraints, flows).

Cite only from files opened in the current STEP.

Format:

Evidence: path:line-range

No stale docs after FULL

FULL must archive and delete all prior docs before regeneration.

No speculation

If a file was not opened in the current STEP, it must not be referenced.

Output structure
docs/
temp/doc-manifest.json
temp/repo-map.json
temp/doc-coverage-report.md
archive/docs_backup_YYYYMMDD_HHMMSS/

Platform notes

Prefer PowerShell-compatible commands on Windows.
Do not assume bash, rg, grep, sed, awk, or wc are installed.
Git may be used when available.

For line counts on Windows:

(Get-Content <path>).Count for small files

Get-Content <path> | Measure-Object -Line for large files

Operation: DOC-SUITE: FULL [AUTO]

Goal: Perform a clean full regeneration.

Internal phases (automatic):

Reset

If docs/ exists → archive to:

archive/docs_backup_<timestamp>/


Delete:

docs/
temp/doc-manifest.json
temp/repo-map.json
temp/doc-coverage-report.md


Recreate empty skeleton:

docs/
docs/architecture/subsystems/
docs/reference/
docs/howto/
docs/operations/


Inventory + Manifest

Inventory all repo files excluding:

.git/, node_modules/, archive/, docs/, temp/
dist/, build/, out/, .next/, .turbo/, .cache/
__pycache__/, .pytest_cache/, .venv/, venv/
coverage artifacts, editor folders
generated bundles (*.map, *.chunk.js, *.min.js)


Classify files:

source | config | test | script | doc | other


Collect LOC and lightweight symbols (headers only).

Group into subsystems by directory and entrypoint heuristics.

Chunk into work items respecting limits.

Write:

temp/repo-map.json
temp/doc-manifest.json


Execution control

If AUTO:

Execute STEP repeatedly until no todo items remain.

Execute FINALIZE automatically.

If STEP mode:

Stop and wait for DOC-SUITE: STEP.

Operation: DOC-SUITE: DELTA [AUTO]

Goal: Incrementally regenerate documentation based on code changes.

Internal phases:

Preconditions

If no manifest exists:

"No manifest found. Run DOC-SUITE: FULL."


Stop.

Change detection

If git baseline exists:

git diff --name-only baseline_commit..HEAD


Else:

Compare file hashes.

Inventory drift protection

If changed files include source/config/test/script files not present in manifest:

"Inventory drift detected. Run DOC-SUITE: FULL."


Stop.

Delta rules

Changed file → owning work item = todo

Added file → mark owning item todo

Deleted file → mark owning item todo + flag orphan docs

Moved/renamed → treat as delete + add

Shared files → mark dependents + reference docs

Lockfiles → mark reference docs

Ignore generated paths

If >20% of source files changed → recommend FULL

Execution control

If AUTO:

Execute STEP repeatedly until no todo items remain.

Execute FINALIZE automatically.

If STEP mode:

Stop and wait for DOC-SUITE: STEP.

Operation: DOC-SUITE: STEP

Goal: Generate exactly ONE document.

Steps:

Load temp/doc-manifest.json.

Select next work item with status = todo.

Mark it doing and persist manifest immediately.

Open only the files listed for this work item.

Build a local citation index.

Write the document to the specified output path.

Document format

First line:

Audience: Developers


Sections:

Overview

Components

Data Flow

Configuration Surface

Public Interfaces

Examples (from opened files only)

Edge Cases / Notes

Mermaid only if it meaningfully clarifies a flow.

Prohibitions

No speculation

No invented behavior

No references to unopened files

Save the doc.

Update manifest (status done, hashes optional).

Stop immediately and summarize the single file created.

Operation: DOC-SUITE: FINALIZE

Goal: Generate cross-cutting docs, workflows, validation, and cleanup.

Phase A — Core and Reference

Generate:

CORE

docs/_index.md
docs/architecture/overview.md
docs/architecture/c4-context.md
docs/architecture/c4-container.md


REFERENCE (only if applicable)

docs/reference/module-index.md
docs/reference/configuration.md
docs/reference/api.md
docs/reference/data-model.md
docs/reference/cli.md


Remove stale reference docs that no longer apply.

Phase B — Workflow Discovery (MANDATORY)

Infer real workflows from:

README / onboarding

Entrypoints

Build and package files

CLI definitions

API routes

Configuration surface

Subsystem docs

If no confident workflows exist:

Generate minimal sensible workflows based on repo signals.

Phase C — How-To Generation

For each workflow:

docs/howto/<workflow-slug>.md


Each guide must include:

Audience

Objective

Concrete commands and file references

Links to subsystems and configs

Troubleshooting notes

If zero guides are generated:

Delete docs/howto/.

Phase D — Operations

If CI/CD, Docker, infra, or monitoring exists:

docs/operations/runbook.md


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

temp/doc-coverage-report.md


Update manifest:

baseline_commit
baseline_timestamp


Stop.

Recommended usage
Full rebuild (safe / stepped)
DOC-SUITE: FULL
DOC-SUITE: STEP   (repeat as desired)
DOC-SUITE: FINALIZE

Full rebuild (automatic)
DOC-SUITE: FULL AUTO

Delta update (safe / stepped)
DOC-SUITE: DELTA
DOC-SUITE: STEP   (repeat as desired)
DOC-SUITE: FINALIZE

Delta update (automatic)
DOC-SUITE: DELTA AUTO