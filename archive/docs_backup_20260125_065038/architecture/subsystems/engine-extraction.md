# Subsystem: engine-extraction

## Purpose
The `engine-extraction` subsystem is responsible for transforming raw data from various ingestion sources into structured, validated entity records. It handles the complexity of mapping heterogeneous source data (unstructured tags, API responses, etc.) into a canonical schema while preserving source-specific "discovered" attributes.

## Key Components

### Core Extraction Logic
- **BaseExtractor (base.py)**: Abstract base class defining the extraction interface (`extract`, `validate`, `split_attributes`). It also provides common utilities for logging and rich text extraction.
- **Entity Classifier (entity_classifier.py)**: Implements a deterministic priority-based algorithm to assign an `entity_class` (place, person, organization, event, thing) based on data characteristics (e.g., presence of coordinates, time bounds).
- **Lens Integration (base.py:extract_with_lens_contract)**: Orchestrates the extraction pipeline using a `LensContract` to apply lens-specific mapping rules, distribute values to dimensions, and trigger additional modules.
- **Attribute Splitter (attribute_splitter.py)**: Utility to separate schema-defined fields from extra "discovered" attributes, ensuring the core database remains clean while preserving peripheral data.

### Data Models & Validation
- **EntityExtraction (models/entity_extraction.py)**: A Pydantic model **automatically generated** from `engine/config/schemas/entity.yaml`. It enforces strict validation for fields like UK postcodes (EH12 9GR format), E.164 phone numbers, and URLs.

### Post-Extraction & Merging
- **Field-Level Merging (merging.py)**: Implements an intelligent merging strategy using a `TrustHierarchy` defined in `extraction.yaml`. Fields are merged independently, choosing values from the most trusted source (e.g., Google Places > OSM) with confidence tie-breakers.
- **Conflict Detection (merging.py)**: Identifies and flags "merge conflicts" where sources provide different values and the trust difference is below a specific threshold.
- **Summary Synthesis (utils/summary_synthesis.py)**: An LLM-powered utility that generates high-quality descriptions following the "Knowledgeable Local Friend" brand voice. It uses structured facts and rich text to create character-limited summaries (e.g., `padel_summary`).

### Execution & Error Management
- **Extraction CLI (run.py)**: The main entry point for running extraction. Supports single record mode (`--raw-id`), source-specific batches (`--source`), and "dry run" simulations.
- **Quarantine & Retry (quarantine.py)**: Records failed extractions in a `FailedExtraction` table. Provides a `ExtractionRetryHandler` to re-attempt failed records with exponential backoff or manual intervention.

## Architecture
The subsystem employs a **hybrid extraction strategy**:
1.  **Deterministic Extraction**: Used for high-quality, structured sources (like Google Places) where mapping is straightforward and reliable.
2.  **LLM-Powered Extraction**: Used for unstructured or noisy sources (like OSM) where intelligent interpretation of free-form text or tags is required.

### Merging & Provenance
The engine supports **Multi-Source Entity Resolution**. When an entity is discovered across multiple sources:
- Trust levels (0-100) determine the "winner" for each field.
- `source_info` and `field_confidence` are tracked for every merged field to maintain data provenance.

### Data Flow
1.  **Ingest**: Raw payload from `RawIngestion` table is passed to the appropriate extractor.
2.  **Classify**: `resolve_entity_class` determines the primary entity type.
3.  **Extract**: Source-specific logic (or LLM) maps raw fields to the schema.
4.  **Lens Apply**: (Optional) `LensContract` mappings are applied to canonicalize categories and activities.
5.  **Validate**: Extracted data is validated against schema rules and Pydantic models.
6.  **Split**: Fields are separated into "attributes" (schema-defined) and "discovered_attributes" (flexible storage).
7.  **Merge**: (If applicable) Multiple source extractions are merged into a single listing based on trust hierarchy.

## Dependencies
### Internal
- **engine-core**: Consumes configuration (`entity_model.yaml`, `extraction.yaml`) and provides logging infrastructure.
- **database**: Extracted data is ultimately persisted via the schema defined in `schema.prisma` (ExtractedEntity and ExtractedListing tables).

### External
- **instructor / anthropic**: Powers the LLM-based extraction logic and summary synthesis.
- **pydantic**: Used for structured data validation and modeling (`EntityExtraction`).
- **phonenumbers**: Used for E.164 normalization of phone numbers.
- **pyyaml**: For loading extraction and entity model configurations.

## Evidence
- `engine/extraction/base.py`: Definition of `BaseExtractor` and `extract_with_lens_contract`.
- `engine/extraction/entity_classifier.py`: Implementation of the deterministic classification algorithm.
- `engine/extraction/llm_client.py`: Instructor-based LLM client for structured extraction.
- `engine/extraction/models/entity_extraction.py`: Generated Pydantic model for entity validation.
- `engine/extraction/merging.py`: Trust-based field merging and conflict detection logic.
- `engine/extraction/utils/summary_synthesis.py`: LLM synthesis of brand-aligned summaries.
- `engine/extraction/run.py`: CLI execution logic for single and batch extraction.
- `engine/extraction/quarantine.py`: Failure recording and retry orchestration.
- `engine/config/entity_model.yaml`: Source of truth for entity classes and required modules.
