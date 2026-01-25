# Subsystem: infrastructure

## Purpose
The infrastructure subsystem provides the necessary configuration and automation to ensure code quality, architectural integrity, and consistent development practices across the repository. It specifically focuses on enforcing "Engine Purity" and "Lens Contract" validation during the integration process.

## Key Components

### CI/CD Workflows
- **.github/workflows/tests.yml**: The primary CI pipeline that executes on push and pull requests to `main` and `develop` branches.
  - **Engine Purity Job**: Executes `scripts/check_engine_purity.sh` to ensure structural purity of the engine.
  - **Run Tests Job**: Handles environment setup (Python 3.12), dependency installation, and execution of comprehensive test suites including engine tests, purity tests, lens validation, deduplication, and module composition tests.

### Contribution Templates
- **.github/pull_request_template.md**: A standardized template for all pull requests that includes a detailed "Architectural Validation Checklist". This checklist forces contributors to verify:
  - **Engine Purity**: No imports from `lenses/`, no value-based branching on dimensions.
  - **Lens Contract Validation**: Verification of facet sources and mapping rules.
  - **Module Composition**: Proper JSONB namespacing.
  - **Testing**: Passing of specific regression and feature tests.

## Architecture
The infrastructure subsystem acts as a gatekeeper. It leverages GitHub Actions for automated validation and Markdown templates for manual process enforcement. The architecture is designed around the concept of "Engine Purity", ensuring that the core engine remains decoupled from specific lens implementations.

## Dependencies

### Internal
- **scripts/check_engine_purity.sh**: Script used by CI to validate engine decoupling.
- **tests/engine/test_purity.py**: Test suite for architectural purity.
- **tests/lenses/test_validator.py**: Test suite for LensContract integrity.
- **tests/modules/test_composition.py**: Test suite for module namespacing.

### External
- **GitHub Actions**: Execution environment for CI.
- **Python 3.12**: Runtime for test execution.
- **pytest**: Test runner and coverage reporting tool.

## Evidence
- Evidence: .github/workflows/tests.yml:1-73
- Evidence: .github/pull_request_template.md:1-76
