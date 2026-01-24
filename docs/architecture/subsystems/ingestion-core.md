Audience: Developers

# Ingestion Core Subsystem

The Ingestion Core provides the foundational infrastructure for fetching raw data from various external sources. It enforces consistency across different data providers while handling common concerns like rate limiting, retries, duplicate prevention, and storage organization.

## Overview

The subsystem is built around a pluggable connector architecture. Each data source is implemented as a concrete class inheriting from a common base interface. This ensures that the ingestion pipeline can interact with any source using a unified set of operations.

## Components

### BaseConnector (`engine/ingestion/base.py`)
An abstract base class that defines the contract for all data source connectors. It requires implementations for fetching data, saving it, and checking for duplicates.
- **Evidence**: `engine/ingestion/base.py:20-39`

### RateLimiter (`engine/ingestion/rate_limiting.py`)
Manages API quota consumption using a sliding time window. It supports both per-minute and per-hour limits and can be applied via decorators or direct calls.
- **Evidence**: `engine/ingestion/rate_limiting.py:64-96`

### Retry Logic (`engine/ingestion/retry_logic.py`)
Provides a decorator-based mechanism for retrying failed operations with exponential backoff. It handles transient network errors and service interruptions.
- **Evidence**: `engine/ingestion/retry_logic.py:59-105`

### Filesystem Storage (`engine/ingestion/storage.py`)
Handles the persistence of raw JSON data. It organizes files by source and timestamp, ensuring a consistent directory structure (`engine/data/raw/<source>/<YYYYMMDD>_<id>.json`).
- **Evidence**: `engine/ingestion/storage.py:55-83`

### Summary & Status (`engine/ingestion/summary_report.py`, `engine/ingestion/cli.py`)
Provides reporting capabilities by aggregating data from the `RawIngestion` database table. It tracks success rates, error counts, and recent activity per source.
- **Evidence**: `engine/ingestion/summary_report.py:46-100`

## Data Flow

1.  **Invocation**: The system (via CLI or Orchestrator) initializes a concrete connector.
2.  **Rate Limit Check**: The `rate_limited` decorator checks if the current request exceeds the sliding window quota.
3.  **Data Fetching**: The connector executes the `fetch` method, wrapped in `retry_with_backoff` to handle transient failures.
4.  **Deduplication**: A content hash is computed and checked against existing `RawIngestion` records.
5.  **Persistence**: If the content is new:
    -   Raw data is saved to the filesystem via `save_json`.
    -   A metadata record is created in the database.
6.  **Reporting**: Ingestion statistics are updated and made available via the CLI or summary reports.

## Configuration Surface

The ingestion core is primarily configured via `engine/config/sources.yaml` (referenced in code):
- **Rate Limits**: `requests_per_minute`, `requests_per_hour`.
- **Retry Policies**: `max_attempts`, `initial_delay`, `backoff_factor`.
- **Evidence**: `engine/ingestion/rate_limiting.py:276-302`, `engine/ingestion/retry_logic.py:149-195`

## Public Interfaces

### Connector Interface
- `async fetch(query: str) -> dict`: Retrieves raw data from the source.
- `async save(data: dict, source_url: str) -> str`: Persists data and returns the file path.
- `async is_duplicate(content_hash: str) -> bool`: Checks if data has already been ingested.

### Decorators
- `@rate_limited(source, requests_per_minute, requests_per_hour)`: Limits execution frequency.
- `@retry_with_backoff(max_retries, initial_delay, backoff_factor)`: Adds resilience to async calls.

## Examples

### Running via CLI
```bash
# Fetch data from Serper
python -m engine.ingestion.cli serper "restaurants in Edinburgh"

# View ingestion status
python -m engine.ingestion.cli status
```

## Edge Cases / Notes
- **Duplicate Prevention**: Content hashing happens *before* saving to avoid filesystem and database bloat.
- **Sliding Window**: The rate limiter uses a `deque` of timestamps to accurately track requests over moving intervals, rather than fixed clock buckets.
- **Database Resilience**: Summary reporting includes error handling for database connection failures, returning empty stats instead of crashing.
