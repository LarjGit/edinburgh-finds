# Specification: Conductor Documentation Synchronization

## 1. Overview
The current Conductor documentation (`product.md`, `tech-stack.md`, `workflow.md`, `product-guidelines.md`) has drifted from the actual state of the codebase (e.g., Prisma versions). This track aims to conduct a deep analysis of the codebase and update these documents to ensure they accurately reflect the "ground truth" of the project's configuration, architecture, and workflows.

## 2. Scope
The following files will be reviewed and updated:
-   `conductor/product.md`: Verify mission alignment and high-level architectural descriptions against the project structure.
-   `conductor/tech-stack.md`: Synchronize dependencies, versions (e.g., Prisma, Next.js, Python libs), and tools with `package.json`, `requirements.txt`, and config files.
-   `conductor/workflow.md`: Validate and update development commands (testing, linting, building) and workflow protocols to match actual scripts.
-   `conductor/product-guidelines.md`: Ensure design and quality guidelines align with existing implementation patterns.

## 3. Methodology
-   **Deep Codebase Alignment:** Analysis will go beyond simple version checking. We will inspect code patterns, folder structures, and configuration files to ensure the documentation captures *how* the system is built, not just *what* is installed.
-   **Code as Source of Truth:** In cases of discrepancy, the documentation will be updated to match the existing working code.

## 4. Success Criteria
-   `tech-stack.md` accurately lists current versions of all major dependencies (e.g., Prisma 7.x).
-   `workflow.md` contains executable and correct commands for the current environment.
-   Architectural descriptions in `product.md` match the actual file organization.
-   All discrepancies are resolved by updating the documentation.
