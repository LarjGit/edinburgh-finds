# Lens System Subsystem

The **Lens System** is the mechanism through which the generic Edinburgh Finds engine is adapted for specific domains or "Verticals". It allows the same infrastructure to power diverse applications like a "Wine Discovery App" and a "Local Sports Finder" without modifying the core engine code.

## Core Responsibilities

- **Domain Definition**: Specifying what categories and attributes matter for a specific vertical.
- **Data Mapping**: Translating raw data from various sources into the domain's terminology.
- **Entity Filtering**: Defining the membership criteria for entities belonging to the lens.
- **UI Customization**: Providing labels and display logic for the web dashboard.

## The Lens Contract

Every lens is defined by a **Lens Contract**, a structured configuration (usually YAML) that the engine reads at runtime.

### Key Components of a Contract:

1.  **Facets**: Logical groupings of canonical values (e.g., `activity`, `amenity`).
2.  **Mapping Rules**: Regex or string-match patterns that map raw source categories to canonical keys.
    - Example: `(?i)padel` -> `padel_tennis`.
3.  **Module Triggers**: Logic that adds specific data modules to an entity based on its canonical values.
    - Example: If an entity has activity `wine`, add the `wine_production` module.
4.  **Display Labels**: Human-readable names for the canonical keys used in the UI.

**Evidence**: `engine/extraction/base.py` (`extract_with_lens_contract`) and `lenses/` directory.

## Directory Structure

Lenses are located in the `lenses/` root directory:
- `lenses/edinburgh_finds/`: The primary local discovery lens.
- `lenses/wine_discovery/`: A vertical-specific lens for wine enthusiasts.

## Design Philosophy: Decoupling

The Lens System enforces the **Engine Purity** principle. The Engine provides the "How" (how to extract, how to merge), while the Lens provides the "What" (what is a wine bar, what is a tennis club). This decoupling ensures that improvements to the core extraction logic benefit all lenses simultaneously.
