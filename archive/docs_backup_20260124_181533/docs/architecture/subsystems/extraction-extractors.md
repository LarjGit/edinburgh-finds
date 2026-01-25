Audience: Developers

# Extraction Subsystem: Extractors

## Overview
The Extractors layer is responsible for transforming raw data from various providers (OSM, Google Places, Council APIs, etc.) into structured entity fields defined by the system's schema. It employs two primary strategies:
1. **Deterministic Extraction**: Used for sources with clean, structured API responses (JSON/GeoJSON).
2. **LLM-Based Extraction**: Used for unstructured or semi-structured sources (OSM tags, search snippets) that require semantic understanding to map to the schema.

All extractors inherit from a `BaseExtractor` and implement standard `extract`, `validate`, and `split_attributes` methods.

## Components

### LLM-Based Extractors
These extractors use the `InstructorClient` (Anthropic) to parse complex or unstructured data into a Pydantic `EntityExtraction` model.

| Extractor | Source | Implementation Strategy |
|:---|:---|:---|
| `OSMExtractor` | OpenStreetMap | Aggregates OSM nodes/ways tags into context; uses prompts with classification rules to map free-form tags to schema fields. |
| `SerperExtractor` | Google Search | Aggregates search titles and snippets; uses LLM to identify the primary entity and extract details from fragmented information. |

### Deterministic Extractors
These extractors use direct mapping and utility functions to parse structured data.

| Extractor | Source | Data Format | Key Features |
|:---|:---|:---|:---|
| `GooglePlacesExtractor` | Google Places API | JSON (Places v1) | Formats phone/postcode; parses `weekdayDescriptions` for opening hours; extracts rich text for synthesis. |
| `EdinburghCouncilExtractor` | Edinburgh Council | GeoJSON (ArcGIS) | Handles multiple naming conventions (`FACILITY_NAME` vs `SITE_NAME`); extracts occupancy/accessibility details. |
| `SportScotlandExtractor` | Sport Scotland | GeoJSON (WFS) | Infers specific sports fields (e.g., `tennis_total_courts`) from facility type and property fields. |
| `OpenChargeMapExtractor` | OpenChargeMap | JSON | Extracts EV-specific connection details (type, power, level) into discovered attributes. |

## Data Flow
1. **Ingest**: Raw data is fetched by Ingestion Connectors (e.g., `engine/ingestion/connectors/`).
2. **Extract**: The appropriate Extractor transforms raw data into a flat dictionary of potential fields.
3. **Validate**: Extracted data is validated for required fields (e.g., `entity_name`) and format (e.g., E.164 phone numbers).
4. **Split**: `split_attributes` separates schema-defined fields from source-specific "discovered" attributes.
5. **Normalize**: External IDs are added to `external_ids` for cross-source deduplication.

## Configuration Surface
Extractors utilize prompts stored in `engine/extraction/prompts/` (e.g., `osm_extraction.txt`, `serper_extraction.txt`). Classification rules are injected dynamically into these prompts.

## Public Interfaces
All extractors implement:
- `extract(raw_data: Dict) -> Dict`: Transforms provider data to schema-aligned fields.
- `validate(extracted: Dict) -> Dict`: Ensures data integrity.
- `split_attributes(extracted: Dict) -> Tuple[Dict, Dict]`: Returns `(core_attributes, discovered_attributes)`.

## Examples

### OSM Tag Aggregation
Evidence: `engine/extraction/extractors/osm_extractor.py:126-173`
The `OSMExtractor` aggregates multiple OSM elements (nodes, ways, relations) into a single context string, allowing the LLM to synthesize data from related OSM entities.

### Deterministic Postcode Extraction
Evidence: `engine/extraction/extractors/google_places_extractor.py:117-142`
The `extract_postcode_from_address` utility uses regex to pull UK postcodes from full address strings when the source doesn't provide them as separate fields.

## Edge Cases / Notes
- **Coordinate Order**: GeoJSON (Council/Sport Scotland) uses `[longitude, latitude]`, while the system schema uses `[latitude, longitude]`. Extractors explicitly swap these.
- **Null Semantics**: LLM extractors are prompted to use `null` for missing information to avoid hallucinations.
- **Provenance**: Extractors often store original IDs (e.g., `node/12345`) in `external_ids` to support downstream merging.
