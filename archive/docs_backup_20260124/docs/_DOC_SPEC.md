\# Repo Documentation Suite Spec



\## Goal

Generate a docs suite by reading the repo source code as the source of truth.

No guessing. If not found in repo, say "Not found in repo".



\## Required files to create/update

\- docs/\_index.md

\- docs/product.md

\- docs/quickstart.md

\- docs/reference/configuration.md

\- docs/reference/interfaces.md

\- docs/reference/data-model.md

\- docs/architecture/overview.md

\- docs/architecture/c4-context.mmd

\- docs/architecture/c4-container.mmd

\- docs/operations/runbook.md

\- docs/security.md

\- docs/testing.md

\- docs/contributing.md

\- docs/howto/ (at least 5 guides)

\- docs/architecture/decisions/ (ADRs if any major decisions are discoverable)



\## Rules

\- Plain English.

\- Start each doc with: Audience: ...

\- Every non-trivial claim must include:

&nbsp; Evidence: <file path> (<symbol or brief pointer>)

\- Mermaid diagrams for the two C4 files.



