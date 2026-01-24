Audience: Developers

# Ingestion Connectors

## Overview
The Ingestion Connectors subsystem provides a set of specialized modules for fetching raw data from various external APIs and data portals. Each connector is responsible for authenticating with a specific source, executing queries, and persisting the raw response (usually JSON or GeoJSON) to both the filesystem and the `RawIngestion` table in the database.

## Components

### OSMConnector
Fetches geographic and facility data from the OpenStreetMap Overpass API.
- **Purpose**: Primarily used for discovering sports facilities and venues using Overpass QL.
- **Key Features**: Supports spatial filtering (around a center point) and tag-based filtering (e.g., `sport`, `leisure`).
- **Files**: `engine/ingestion/connectors/open_street_map.py`

### GooglePlacesConnector
Integrates with the Google Places API (New/v1) to fetch venue and business data.
- **Purpose**: Provides detailed place information including ratings, addresses, and location coordinates.
- **Key Features**: Uses the Text Search API with field masking to optimize data retrieval.
- **Files**: `engine/ingestion/connectors/google_places.py`

### SerperConnector
A wrapper for the Serper API to retrieve Google search results.
- **Purpose**: Used for broad discovery and gathering web snippets about venues.
- **Key Features**: Simplifies search result extraction without direct web scraping.
- **Files**: `engine/ingestion/connectors/serper.py`

### EdinburghCouncilConnector
Fetches official civic and facility data from the City of Edinburgh Council Open Spatial Data Portal.
- **Purpose**: Enrichment of venue data with official civic context (e.g., wards, neighborhoods) and discovering council-owned facilities.
- **Key Features**: Interfaces with ArcGIS REST Feature Services.
- **Files**: `engine/ingestion/connectors/edinburgh_council.py`

### OpenChargeMapConnector
Retrieves EV charging station data from the OpenChargeMap API.
- **Purpose**: Supplements venue profiles with nearby charging infrastructure information.
- **Key Features**: Coordinate-based proximity searches.
- **Files**: `engine/ingestion/connectors/open_charge_map.py`

### SportScotlandConnector
Fetches official Scottish sports facility data from SportScotland via WFS.
- **Purpose**: Provides verified facility attributes (surface type, size, capacity) for sports venues.
- **Key Features**: Uses OGC Web Feature Service (WFS) with spatial bounding box filters for Edinburgh.
- **Files**: `engine/ingestion/connectors/sport_scotland.py`

## Data Flow
1.  **Initialize**: The connector loads configuration from `engine/config/sources.yaml`.
2.  **Fetch**: Executes an asynchronous HTTP request (POST/GET) to the external API using `aiohttp`.
3.  **Deduplicate**: Computes a SHA-256 hash of the response content and checks against the `RawIngestion` table.
4.  **Save**: If new, saves the raw JSON/GeoJSON to `engine/data/raw/<source>/` and creates a record in the `RawIngestion` table with metadata.

## Configuration Surface
Connectors are configured in `engine/config/sources.yaml`. Key configuration points include:
- `api_key`: Required for Google Places, Serper, and OpenChargeMap.
- `base_url`: The API endpoint.
- `timeout_seconds`: Request timeout (default usually 30-60s).
- `default_params`: Source-specific parameters like radius, location, or WFS versions.

## Public Interfaces
All connectors inherit from `BaseConnector` and implement:
- `source_name` (property): Returns the unique identifier for the source.
- `fetch(query)` (async): Executes the API call.
- `save(data, source_url)` (async): Persists data and database record.
- `is_duplicate(content_hash)` (async): Checks for existing data.

## Examples

### Fetching from OSM
```python
connector = OSMConnector()
data = await connector.fetch("padel")
file_path = await connector.save(data, "https://overpass-api.de/api/interpreter")
```

## Edge Cases / Notes
- **Rate Limiting**: Connectors rely on the `BaseConnector` or external configuration to respect source-specific rate limits.
- **Empty Results**: Most connectors handle empty responses by saving an "empty" record to prevent repeated unsuccessful queries.
- **Spatial Boundaries**: Edinburgh-specific connectors (Council, SportScotland) use predefined bounding boxes or center points.

## Evidence
- `OSMConnector` implementation: `engine/ingestion/connectors/open_street_map.py:34-190`
- `GooglePlacesConnector` implementation: `engine/ingestion/connectors/google_places.py:36-193`
- `SerperConnector` implementation: `engine/ingestion/connectors/serper.py:35-181`
- `EdinburghCouncilConnector` implementation: `engine/ingestion/connectors/edinburgh_council.py:44-193`
- `OpenChargeMapConnector` implementation: `engine/ingestion/connectors/open_charge_map.py:46-189`
- `SportScotlandConnector` implementation: `engine/ingestion/connectors/sport_scotland.py:53-239`
- `RawIngestion` usage: `engine/ingestion/connectors/open_street_map.py:171-180`
- Hash-based deduplication: `engine/ingestion/connectors/open_street_map.py:190`
