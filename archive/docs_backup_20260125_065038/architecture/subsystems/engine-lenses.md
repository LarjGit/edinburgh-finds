# Subsystem: engine-lenses

## Purpose
The `engine-lenses` subsystem provides the core machinery for vertical-specific interpretation of the universal entity model. A "lens" defines how the engine should display, filter, and augment entities for a specific domain (e.g., sports, wine, tourism). It decouples the universal storage of entities from their domain-specific presentation and logic.

## Key Components

### Lens Loading & Management
- **VerticalLens (`loader.py`)**: The primary class representing a domain lens. It handles loading YAML configurations, applying mapping rules, computing derived groupings, and identifying required domain modules.
- **LensRegistry (`loader.py`)**: A centralized registry that manages loaded `VerticalLens` instances, providing global access to lens configurations by ID.

### Validation & Contracts
- **Lens Configuration Validator (`validator.py`)**: Enforces strict architectural contracts between the engine and lens layers. It ensures all facets reference supported dimensions and that all mapping rules point to valid canonical values.
- **Contract Enforcement**: Validation is fail-fast, occurring at load time to prevent runtime errors from misconfigured lenses.

### Membership & Operations
- **Lens Membership Ops (`ops.py`)**: Provides the API for managing which entities belong to which lenses via the `LensEntity` table. This is the source of truth for vertical-specific entity scoping.

### Interpretation Logic
- **DerivedGrouping (`loader.py`)**: Logic for computing view-only entity groupings at query time based on attributes (e.g., "Places with a specific role").
- **ModuleTrigger (`loader.py`)**: Defines rules for when to attach domain-specific data modules (e.g., "Attach sports_facility module if activity is padel").

## Architecture
The subsystem operates as an **interpretation layer** on top of the universal entity model. It uses a **declarative configuration** approach (via `lens.yaml` files) to define domain logic without requiring code changes in the core engine.

### Key Patterns:
- **Fail-Fast Validation**: Configuration errors raise `LensConfigError` immediately upon registry initialization.
- **Schema-Agnostic Grouping**: Derived groupings allow for complex UI navigation categories that are not persisted as columns in the database.
- **Trigger-Based Augmentation**: Entities are augmented with domain-specific modules only when specific facet/value conditions are met.

## Dependencies

### Internal
- `engine.modules.validator`: Used for strict YAML parsing and module namespace validation.
- `prisma`: Used by `ops.py` for managing `LensEntity` records.

### External
- `PyYAML`: For configuration file parsing.
- `re`: Extensive use of regex for mapping raw source categories to canonical lens values.

## Data Models

### Lens Membership (`LensEntity`)
- `lensId`: String identifier for the lens (e.g., "edinburgh_finds").
- `entityId`: Foreign key to the universal `Entity` table.
- (Implicitly managed via Prisma in `ops.py`)

## Evidence
- `engine/lenses/loader.py`: Implementation of `VerticalLens`, `LensRegistry`, and interpretation logic.
- `engine/lenses/validator.py`: Implementation of the 5 architectural contracts for lens configuration.
- `engine/lenses/ops.py`: Database operations for entity-lens membership.
- `engine/lenses/__init__.py`: Package entry point.
