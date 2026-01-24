Audience: Developers

# Extraction Services

## Overview
The Extraction Services subsystem provides the core infrastructure for transforming raw ingestion data into structured, validated entities. It manages high-level concerns including LLM interaction, result caching, cost tracking, cross-source entity merging, and robust error handling via a quarantine system.

## Components

### LLM Structured Extraction (`InstructorClient`)
The `InstructorClient` serves as the primary gateway to LLM services, specifically optimized for structured data extraction using the Anthropic Claude API and the `instructor` library.
- **Structured Output**: Uses Pydantic models to enforce schema validation on LLM responses.
- **Auto-Retry**: Implements a retry loop (default 2 retries) that feeds validation error messages back to the LLM to correct its output.
- **Evidence**: `engine/extraction/llm_client.py:65-173`

### Extraction Caching (`check_llm_cache`, `store_llm_cache`)
To minimize API costs and latency, the system employs a disk-backed cache using the `ExtractedEntity` table.
- **Deterministic Keys**: Cache keys are SHA-256 hashes of the raw data, prompt, and model name.
- **Persistence**: Results are stored in the `extraction_hash` field of the `ExtractedEntity` table.
- **Evidence**: `engine/extraction/llm_cache.py:38-66`

### Cost & Usage Tracking (`LLMUsageTracker`)
Provides real-time monitoring of token consumption and estimated spend.
- **Model Pricing**: Maintains a pricing table for Claude-3 variants (Haiku, Sonnet, Opus).
- **Aggregations**: Tracks usage by data source and model for financial reporting.
- **Evidence**: `engine/extraction/llm_cost.py:75-156`

### Trust-Based Merging (`EntityMerger`, `TrustHierarchy`)
Intelligently combines data from multiple sources into a single unified listing.
- **Field-Level Trust**: Each field is merged independently using a source-based trust hierarchy defined in `extraction.yaml`.
- **Conflict Detection**: Identifies and flags discrepancies between sources when trust levels are closely matched.
- **Agreement Scoring**: Calculates a confidence score based on how many sources agree on a specific field value.
- **Evidence**: `engine/extraction/merging.py:126-218`

### Entity Deduplication (`Deduplicator`)
Implements a multi-layered strategy to identify duplicate entities across different sources.
- **Strategy Cascade**:
    1. **External IDs**: Precise matching on Google Place IDs or OSM IDs.
    2. **Slug Matching**: URL-safe identifier comparison.
    3. **Fuzzy Matching**: Weighted combination of name similarity (using FuzzyWuzzy) and geographic proximity (Haversine formula).
- **Evidence**: `engine/extraction/deduplication.py:270-305`

### Quarantine & Recovery (`ExtractionRetryHandler`)
Manages extraction failures to ensure no data is lost during processing.
- **FailedExtraction Table**: Records errors, retry counts, and full error details.
- **Offline Retries**: Provides a mechanism to re-run extractions for failed records after fixing configuration or logic issues.
- **Evidence**: `engine/extraction/quarantine.py:204-290`

## Data Flow
1. **Cache Check**: Before calling the LLM, the system computes an `extraction_hash` and checks the database for a hit.
2. **Extraction**: If a miss, the `InstructorClient` sends the raw data and prompt to the LLM.
3. **Validation**: The response is validated against a Pydantic model. If it fails, the error is fed back to the LLM for a retry.
4. **Storage**: Successful extractions are stored in `ExtractedEntity` with their cache hash.
5. **Deduplication**: New entities are checked against existing listings using the `Deduplicator`.
6. **Merging**: If a match is found, the `EntityMerger` updates the unified listing using the trust hierarchy.

## Configuration Surface
- **`extraction.yaml`**: Configures trust levels for sources (e.g., `google_places: 80`, `osm: 60`) and the default LLM model.
- **Evidence**: `engine/extraction/merging.py:42-53`

## Public Interfaces
- `InstructorClient.extract(prompt, response_model, context, ...)`: Core extraction method.
- `EntityMerger.merge_entities(extracted_entities)`: Combines multiple records into one.
- `Deduplicator.find_match(entity1, entity2)`: Determines if two entities are the same.
- `retry_failed_extractions(db, ...)`: Batch process for recovering quarantined items.
