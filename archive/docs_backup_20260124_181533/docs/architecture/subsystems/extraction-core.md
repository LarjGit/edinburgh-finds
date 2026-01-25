Audience: Developers

# Extraction Core Subsystem

The Extraction Core is responsible for transforming raw ingestion payloads into structured entity data. It employs a deterministic classification algorithm and a "Lens" contract mechanism to ensure vertical-agnostic processing while allowing for domain-specific enrichment through modules.

## Overview

The extraction process follows a "universal first" approach. Every entity is classified into one of five base classes (place, person, organization, event, thing) and then enriched with canonical values (activities, roles, access) and namespaced modules based on its characteristics and the active Lens.

## Components

### BaseExtractor
`engine/extraction/base.py:18`
An abstract base class that defines the mandatory interface for all source-specific extraction implementations.
- **extract()**: Transforms raw payload into a flat dictionary of fields.
- **validate()**: Ensures extracted fields adhere to schema rules and normalization.
- **split_attributes()**: Separates schema-defined fields from "discovered" attributes to be stored in JSONB.
- **extract_with_logging()**: Wrapper that handles performance timing and structured logging.

### Entity Classifier
`engine/extraction/entity_classifier.py:228`
A deterministic priority-based resolver that determines the `entity_class` of a record.
- **Priority Order**:
  1. Time-bounded (`start_datetime` / `end_datetime`) -> `event`
  2. Physical location (`latitude` / `longitude` / `address`) -> `place`
  3. Organization-like (type hints / specific categories) -> `organization`
  4. Named individual (type: person) -> `person`
  5. Fallback -> `thing`

### Lens Contract Processor
`engine/extraction/base.py:144`
The `extract_with_lens_contract` function implements the core Engine-Lens boundary logic. It uses a `LensContract` (provided as a plain dictionary) to:
- Map raw categories to canonical values using regex patterns.
- Distribute canonical values into specific dimensions (`canonical_activities`, `canonical_roles`, etc.).
- Evaluate module triggers based on facets and values.

## Data Flow

1. **Raw Load**: Raw ingestion data is loaded from the filesystem (pointed to by `RawIngestion.file_path`).
2. **Lens Mapping**: Regex patterns from the Lens are applied to raw categories to find canonical matches.
3. **Classification**: `resolve_entity_class` is called to determine the base type based on presence of coordinates, dates, or type hints.
4. **Dimension Distribution**: Canonical values are assigned to Postgres `text[]` columns based on the Lens facet definitions.
5. **Module Triggering**: The system checks `module_triggers` in the Lens contract. If an entity has a specific activity or role, additional modules (e.g., `tennis_courts`, `opening_hours`) are added to the requirement list.
6. **Persistence**: The result is saved to the `ExtractedEntity` table, with schema fields in columns and extra data in `discovered_attributes`.

## Configuration Surface

- **extraction.yaml**: Configures LLM model parameters and source trust levels for automated merging. `engine/extraction/config.py:12`
- **entity_model.yaml**: Defines the required universal modules (e.g., `core`, `location`) for each base entity class. `engine/extraction/entity_classifier.py:350`
- **LensContract**: A dynamic configuration object defining facets, values, mapping rules, and vertical-specific module triggers.

## Public Interfaces

### `extract_with_lens_contract(raw_data, lens_contract)`
`engine/extraction/base.py:144`
Primary entry point for lens-aware extraction. Returns a structured dictionary ready for database insertion.

### `resolve_entity_class(raw_data)`
`engine/extraction/entity_classifier.py:228`
The source of truth for entity typing. Ensures every record is assigned exactly one of the five valid entity classes.

### `get_extraction_fields()`
`engine/extraction/schema_utils.py:19`
Returns the list of universal `FieldSpec` objects that the extractor should attempt to populate for every entity.

## Edge Cases / Notes
- **Deduplication**: The extraction pipeline uses `dedupe_preserve_order` to ensure that repeated module triggers or overlapping mapping rules do not produce duplicate database entries. `engine/extraction/base.py:112`
- **Confidence Threshold**: Mapping rules can specify a confidence level; rules below the configured `confidence_threshold` (default 0.7) are ignored. `engine/extraction/base.py:215`
- **Events and Roles**: By specification, entities classified as `event` have their `canonical_roles` cleared to avoid logic conflicts with organization/person roles. `engine/extraction/entity_classifier.py:328`

## Evidence
- Evidence: engine/extraction/base.py:18-108
- Evidence: engine/extraction/base.py:144-279
- Evidence: engine/extraction/entity_classifier.py:228-335
- Evidence: engine/extraction/schema_utils.py:19-27
