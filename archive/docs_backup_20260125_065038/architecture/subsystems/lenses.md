# Subsystem: lenses

## Purpose
The `lenses` subsystem provides vertical-specific interpretations of the universal entity engine. It allows the same underlying data structure to be presented and enriched differently depending on the domain (e.g., "Sports & Fitness" vs. "Wine Discovery"). A lens defines the taxonomy, mapping rules, domain-specific modules, and UI presentation logic for a particular vertical.

## Key Components

### Configuration (`lens.yaml`)
Each vertical is defined by a `lens.yaml` file (e.g., `lenses/edinburgh_finds/lens.yaml`). This file is the source of truth for the vertical's domain logic.
- **Facets**: Map lens-level concepts to the four canonical database dimensions (`canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`).
- **Canonical Values**: Define the metadata (display names, SEO slugs, icons) for each value within a facet.
- **Mapping Rules**: Regex-based rules for extracting canonical values from raw source data.
- **Domain Modules**: Define vertical-specific data structures (e.g., `sports_facility` with inventory for courts) that extend the core entity model.
- **Module Triggers**: Logic that automatically attaches domain modules to entities based on their facet values and entity class.
- **Derived Groupings**: View-only groupings (e.g., "Places", "Coaches") based on entity class and roles.

### Logic & Loading (`engine/lenses/`)
- **`VerticalLens`**: The core class responsible for loading, validating, and applying lens configurations. It provides methods for mapping raw categories and computing required modules.
- **`LensRegistry`**: A central registry for managing and retrieving multiple active lenses.
- **`Validator`**: Ensures that lens configurations adhere to architectural contracts (fail-fast behavior).

## Architecture

### The Lens Abstraction
The lenses subsystem implements a "Lens Architecture" where the universal engine remains agnostic of the vertical. The lens acts as a semantic layer that:
1. **Maps** raw data into a vertical-specific taxonomy.
2. **Projects** universal dimensions into vertical-specific facets.
3. **Enriches** entities with domain-specific modules.

Evidence: `lenses/edinburgh_finds/lens.yaml`, `lenses/wine_discovery/lens.yaml`

### Facet Mapping & Dimension Reuse
Lenses can reuse the same underlying database dimensions for different semantic purposes. For example, the `wine_discovery` lens reuses `canonical_activities` for `wine_type`, while `edinburgh_finds` uses it for `activity`.

Evidence: `lenses/wine_discovery/lens.yaml:37-45`, `lenses/edinburgh_finds/lens.yaml:37-46`

### Module Trigger System
Modules are added dynamically to entities through a trigger system. When an entity is tagged with a specific facet value (e.g., `activity: padel`), the trigger adds the corresponding domain module (e.g., `sports_facility`).

Evidence: `lenses/edinburgh_finds/lens.yaml:364-370`

## Dependencies

### Internal
- **`engine-core`**: The lenses are used by the engine to process and validate data.
- **`database`**: Facets map directly to the four canonical dimensions in the database schema.

### External
- **PyYAML**: Used for parsing the `lens.yaml` configuration files.
- **Pytest**: Extensively used for validating lens configurations and processing logic.

## Data Models

### Lens Configuration Structure
```yaml
id: string
name: string
facets:
  facet_key:
    dimension_source: canonical_activities | canonical_roles | canonical_place_types | canonical_access
    ui_label: string
    display_mode: string
values:
  - key: string
    facet: string
    display_name: string
mapping_rules:
  - pattern: regex
    canonical: value_key
modules:
  module_name:
    fields:
      field_name: { type: string, description: string }
```

## Architectural Contracts
The subsystem enforces several strict contracts to ensure data integrity and system stability:
1. **Dimension Source**: Every `facet.dimension_source` MUST be one of the 4 allowed canonical dimensions.
2. **Facet Reference**: Every `value.facet` MUST reference a facet defined in the `facets` section.
3. **Canonical Reference**: Every `mapping_rules.canonical` MUST reference a value defined in the `values` section.
4. **Uniqueness**: Value keys and facet keys MUST be unique within the lens.
5. **Role Facet**: A `role` facet is typically required and is often configured as `internal-only` (not shown in UI).

Evidence: `tests/lenses/test_validator.py:15-130`, `engine/lenses/loader.py` (referenced in tests)

## Evidence
- `lenses/edinburgh_finds/lens.yaml`: Comprehensive sports/fitness vertical configuration.
- `lenses/wine_discovery/lens.yaml`: Demonstrates vertical flexibility and dimension reuse.
- `tests/lenses/test_edinburgh_finds_lens.py`: Validates architectural contracts for the Edinburgh lens.
- `tests/lenses/test_lens_processing.py`: Tests the logic for facets, groupings, and module triggers.
- `tests/lenses/test_validator.py`: Comprehensive tests for the configuration validator.
