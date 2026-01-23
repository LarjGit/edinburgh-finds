# Documentation Suite Generator

Generate a comprehensive documentation suite by analyzing the codebase as the source of truth.

## Description

Read docs/_DOC_SPEC.md and then generate the full documentation suite it describes.

Rules:
- The repository is the source of truth. Do not guess.
- If something is unclear or not present, write "Not found in repo".
- Every non-trivial claim must include an Evidence line with file path + symbol/pointer.
- Write/update the files directly under /docs (don't just describe them in chat).

Process:
1) First scan the repo structure to identify entrypoints, routes/interfaces, config/env usage, data models, background jobs/scripts, integrations, and deploy/ops.
2) Create Mermaid diagrams:
   - docs/architecture/c4-context.mmd
   - docs/architecture/c4-container.mmd
3) Write all required docs pages.
4) Create at least 5 how-to guides based on real tasks supported by the repo.

## Audience

Developers and technical writers who need to create or update project documentation based on actual code.

## Usage

```bash
/doc-suite
```

## Output

The skill will:
- Scan the repository structure
- Generate all documentation files specified in `docs/_DOC_SPEC.md`
- Create C4 architecture diagrams
- Generate at least 5 how-to guides
- Provide a summary of created files and any gaps found
