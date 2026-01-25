Audience: Developers

# Lenses Subsystem

The Lenses subsystem is the vertical-specific interpretation layer of the Edinburgh Finds engine. It defines how universal entities (places, people, organizations) are classified, grouped, and extended with domain-specific data for a particular product or vertical (e.g., Sports, Wine).

## Overview

A "Lens" owns all vertical-specific knowledge. While the core engine handles universal data (names, locations, core attributes), the Lens layer defines the taxonomy, mapping rules, and extended data structures (Domain Modules) that make the data meaningful for a specific use case.

## Components

### VerticalLens (`engine/lenses/loader.py`)
The primary object representing a vertical. It is initialized from a `lens.yaml` file and encapsulates all taxonomy and interpretation logic.
- **Fail-Fast Validation**: Validates the configuration against architectural contracts at load time.
- **Mapping Engine**: Applies regex-based `mapping_rules` to convert raw source categories into canonical values.
- **Module Orchestrator**: Determines which domain modules should be attached to an entity based on its classification.

### Lens Registry (`engine/lenses/loader.py`)
A global registry that manages loaded `VerticalLens` instances. It allows the engine to retrieve the correct interpretation logic by `lens_id`.

### Lens Validator (`engine/lenses/validator.py`)
Enforces the 5 Architectural Contracts that ensure lens configurations are compatible with the engine:
1. Every `facet.dimension_source` must be one of the 4 allowed DB columns (`canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`).
2. Every `value.facet` must reference an existing facet.
3. Every `mapping_rules.canonical` must reference an existing value.
4. Every `value.key` must be unique within the lens.
5. Facet keys must be unique.

### Lens Operations (`engine/lenses/ops.py`)
Provides the low-level database API for managing entity membership in lenses via the `LensEntity` join table.
- `attach_entity_to_lens`: Creates a membership record.
- `detach_entity_from_lens`: Removes a membership record.

### Configuration Objects
- **FacetDefinition**: Maps a lens-level concept (e.g., "Interest") to a database dimension.
- **CanonicalValue**: Defines display metadata (name, SEO slug, icon, color) for a specific classification.
- **DerivedGrouping**: Logic for grouping entities in the UI (e.g., "Coaches & Instructors") without storing the grouping in the DB.
- **ModuleTrigger**: Rules that fire based on an entity's classification to attach domain-specific data structures.

## Data Flow

### 1. Initialization
The `LensRegistry` scans the `lenses/` directory for `lens.yaml` files. Each file is loaded into a `VerticalLens` object. During loading, the `LensValidator` ensures the configuration is structurally sound.

### 2. Classification & Mapping
During ingestion or extraction, raw category strings from sources (e.g., Google Places types, OSM tags) are passed to `VerticalLens.map_raw_category()`. This method uses regex patterns to identify matching canonical values.
- **Evidence**: `engine/lenses/loader.py:377-405`

### 3. Module Attachment
Once an entity is classified, the engine calls `VerticalLens.get_required_modules()`. If the entity's classification matches a `ModuleTrigger` (e.g., an entity with activity `padel` triggers the `sports_facility` module), the engine knows to include those extra fields in the extraction process.
- **Evidence**: `engine/lenses/loader.py:440-462`

### 4. Query-Time Interpretation
When the frontend requests data for a specific lens:
1. The engine retrieves the `VerticalLens` from the registry.
2. It uses `DerivedGrouping` logic to organize entities for navigation filters.
3. It uses `FacetDefinition` and `CanonicalValue` metadata to render the UI (labels, icons, colors).

## Configuration Surface (`lens.yaml`)

The `lens.yaml` is the source of truth for a vertical. It is divided into several key sections:

| Section | Purpose |
| :--- | :--- |
| `facets` | Defines the dimensions of classification (Activity, Role, Access, etc.). |
| `values` | The taxonomy of canonical values within those facets. |
| `mapping_rules` | Regex patterns for automated classification from raw data. |
| `derived_groupings` | UI-only groupings for navigation and landing pages. |
| `modules` | Schemas for vertical-specific data (e.g., `inventory` for sports facilities). |
| `module_triggers` | Logic connecting classification to module attachment. |

## Public Interfaces

### `VerticalLens` Methods
- `map_raw_category(raw_category: str) -> List[str]`: Maps raw strings to canonical keys.
- `get_required_modules(entity_class, canonical_values) -> List[str]`: Identifies domain modules to attach.
- `compute_grouping(entity) -> Optional[str]`: Determines which UI grouping an entity belongs to.

### Database Operations
- `attach_entity_to_lens(entity_id, lens_id)`: Registers an entity as belonging to a lens.

## Edge Cases / Notes
- **Internal Facets**: The `role` facet is typically marked as `display_mode: internal` and used for logic (like groupings and triggers) but hidden from the end-user.
- **Confidence Thresholds**: Mapping rules can include a `confidence` score. The `VerticalLens` defaults to a `0.7` threshold for accepting a match.
- **Universal Roles**: Lenses should use universal function-style roles (e.g., `provides_facility`, `provides_instruction`) rather than vertical-specific terms (e.g., `Venue`, `Coach`) for the key, while using the `display_name` for terminology.
