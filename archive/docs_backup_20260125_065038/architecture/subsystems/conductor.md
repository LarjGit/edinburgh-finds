# Subsystem: conductor

## Purpose
The Conductor subsystem serves as the central orchestration layer and "source of truth" for the project. It defines the product vision, technical architecture, development workflows, and quality standards that govern all other subsystems. It is designed to provide a deterministic framework for both AI agents and human developers to collaborate effectively.

## Key Components
- **Product Definition (`product.md`):** Outlines the core mission, Universal Entity Framework, and growth strategy.
- **Technology Stack (`tech-stack.md`):** Defines the authorized frontend, backend, and database technologies, as well as the schema management strategy.
- **Development Workflow (`workflow.md`):** Estantshes rigorous protocols for Task-Driven Development (TDD), CI-awareness, Git commit standards, and the "Definition of Done."
- **Tracks Registry (`tracks.md`):** Manages project milestones and archives completed development tracks.
- **Product Design Guidelines (`product-guidelines.md`):** Defines the "Sophisticated Canvas" design philosophy, UX principles, and "Local Artisan" tone of voice.
- **Code Styleguides:** Language-specific standards for Python (Google Style), React (Functional/Hooks), and TypeScript (Google Style/gts).
- **Execution State (`setup_state.json`):** Maintains internal state for the conductor extension to ensure session continuity.

## Architecture
Conductor operates as a meta-subsystem that defines the rules and patterns for the rest of the codebase. It enforces the **Engine-Lens Architecture**, where a vertical-agnostic "Entity Engine" is separated from vertical-specific "Lens Layers" via YAML configurations. The workflow is disk-backed, ensuring that all plans, decisions, and progress are persisted in the repository rather than in-memory.

## Dependencies
### Internal
- **All Subsystems**: Every part of the repository (Engine, Web, Scripts) is expected to adhere to the standards and workflows defined in Conductor.
- **Engine Schema**: The "Single Source of Truth" principle for schemas is documented here and implemented in the `engine/schema` subsystem.

### External
- **Git**: Heavily utilized for task tracking via `git notes` and phase checkpointing.
- **Next.js & Prisma**: Technologies authorized and configured within the Conductor framework.

## Data Models
The Conductor system manages its own "meta-data":
- **Tracks**: High-level milestones registered in `tracks.md`.
- **Plans**: Granular task lists stored in `plan.md` files within specific track directories.
- **Checkpoints**: Git-based snapshots of phase completion with attached verification reports.

## Configuration
Conductor defines several key project configurations:
- **Quality Gates**: Mandatory checks including >80% code coverage and passing automated tests.
- **Commit Guidelines**: Structured format (`type(scope): description`) for all repository changes.
- **Naming Conventions**: Specific rules for Python (`snake_case`), TypeScript (`lowerCamelCase`), and React (`PascalCase`).

## Evidence
- `conductor/product.md`: Section 2 (Universal Entity Framework definition)
- `conductor/tech-stack.md`: Schema Management section (YAML-based single source of truth)
- `conductor/workflow.md`: Task Workflow and Quality Gates sections
- `conductor/code_styleguides/python.md`: Google Python Style Guide summary
- `conductor/tracks.md`: History of architectural refactors and engine purity remediation
