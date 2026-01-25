# Subsystem: engine-ingestion

## Purpose
The `engine-ingestion` subsystem is responsible for fetching raw data from various external sources (APIs, Overpass API, ArcGIS REST, etc.) and persisting it for later processing. It ensures data integrity through deduplication, respects external service limits via rate limiting, and handles transient failures using retry logic with exponential backoff.

## Key Components

### Connectors
All connectors inherit from `BaseConnector` (in `base.py`) which defines the standard interface:
- **SerperConnector** (`serper.py`): Fetches Google search results via Serper.dev API.
- **GooglePlacesConnector** (`google_places.py`): Interfaces with the new Google Places v1 API for rich venue data.
- **OSMConnector** (`open_street_map.py`): Queries the Overpass API for OpenStreetMap geographic and facility data.
- **OpenChargeMapConnector** (`open_charge_map.py`): Retrieves EV charging station data.
- **SportScotlandConnector** (`sport_scotland.py`): Fetches sports facility data from GeoServer WFS.
- **EdinburghCouncilConnector** (`edinburgh_council.py`): Connects to Edinburgh Council's ArcGIS REST services for civic facilities.

### Infrastructure & Utilities
- **RateLimiter** (`rate_limiting.py`): Implements sliding window rate limiting to prevent API quota exhaustion.
- **Retry Logic** (`retry_logic.py`): Provides a `@retry_with_backoff` decorator for handling transient network and API errors.
- **Deduplication** (`deduplication.py`): Uses SHA-256 content hashing to identify and skip already ingested data.
- **Storage** (`storage.py`): Manages the filesystem structure for raw data, organized by source and timestamp in `engine/data/raw/`.
- **CLI** (`cli.py`): Unified command-line interface for manual ingestion, status reporting, and connector management.

## Architecture

The subsystem follows a plugin-based architecture where each data source is encapsulated in a dedicated connector class.

### Data Flow
1. **Trigger**: Ingestion is initiated via the CLI or orchestration layer.
2. **Fetch**: The connector executes the source-specific request logic (HTTP, WFS, etc.).
3. **Deduplicate**: A SHA-256 hash of the response is computed and checked against the `RawIngestion` table.
4. **Persist**:
   - **Filesystem**: Raw JSON is saved to `engine/data/raw/<source>/<YYYYMMDD>_<record_id>.json`.
   - **Database**: A record is created in the `RawIngestion` table with the file path, content hash, and metadata.

## Dependencies

### Internal
- **database**: Uses Prisma client to interact with the `RawIngestion` table.
- **config**: Consumes API keys and rate limits from `engine/config/sources.yaml`.

### External
- **aiohttp**: For asynchronous HTTP requests.
- **Prisma**: Database ORM.
- **PyYAML**: For configuration parsing.
- **External APIs**: Google Places, Serper, OSM Overpass, ArcGIS, GeoServer.

## Data Models
The primary data model is the `RawIngestion` table (defined in `schema.prisma`), which tracks:
- `source`: The identifier for the data source.
- `source_url`: The URL or query used for ingestion.
- `file_path`: Location of the raw data on disk.
- `hash`: SHA-256 content fingerprint.
- `status`: Success/failure state.
- `metadata_json`: Source-specific statistics (e.g., result counts).

## Configuration
Connectors are configured in `engine/config/sources.yaml`:
- **API Keys**: Authenticated access to Serper and Google Places.
- **Rate Limits**: `requests_per_minute` and `requests_per_hour`.
- **Retry Settings**: `max_attempts`, `initial_delay`, `backoff_factor`.

## Evidence
- **Base Interface**: `engine/ingestion/base.py:1-112`
- **Ingestion Logic**: `engine/ingestion/connectors/google_places.py:145-212` (save/hash/record)
- **Rate Limiting**: `engine/ingestion/rate_limiting.py:46-150` (Sliding window implementation)
- **Deduplication**: `engine/ingestion/deduplication.py:34-60` (SHA-256 logic)
- **Storage Organization**: `engine/ingestion/storage.py:1-137`
- **CLI Capabilities**: `engine/ingestion/cli.py:1-450`
