Audience: Developers

# Data Model

Edinburgh Finds uses a PostgreSQL database with PostGIS for spatial operations and JSONB for extensible entity data.

## Core Tables

### `RawIngestion`
Stores the unmodified data fetched from external connectors.
- `id`: UUID Primary Key.
- `connector`: String (e.g., `osm`, `google_places`).
- `raw_data`: JSONB (The full response from the source).
- `hash`: SHA256 of the raw data for deduplication.
- `status`: Enum (`pending`, `processed`, `quarantined`).

### `Entity`
The unified representation of a discovered object.
- `id`: UUID Primary Key.
- `class`: Enum (`place`, `person`, `organization`, `event`, `thing`).
- `slug`: Unique string for URL routing.
- `data`: JSONB (Structured modules like `core`, `location`, `contact`).
- `dimensions`: JSONB (Mapping of dimension keys to `text[]` arrays).
- `location`: Geometry (Point) for spatial indexing.

### `EntitySourceLink`
Maps an `Entity` back to its original `RawIngestion` records.
- `entity_id`: Foreign Key to `Entity`.
- `raw_id`: Foreign Key to `RawIngestion`.
- `field_trust`: JSONB (Snapshot of which fields came from this source).

### `LLMCache`
Reduces costs by storing LLM results for identical prompts.
- `prompt_hash`: Unique hash of the prompt and model settings.
- `response`: JSONB (The structured extraction result).

---

## The Unified Entity Model (JSONB)

The `Entity.data` field follows a modular structure defined in `engine/config/entity_model.yaml`.

### Example JSONB Structure
```json
{
  "core": {
    "name": "Meadows Tennis Club",
    "description": "Public tennis courts in the heart of Edinburgh."
  },
  "location": {
    "address_line_1": "Melville Drive",
    "city": "Edinburgh",
    "postcode": "EH9 1ND",
    "lat": 55.9412,
    "lng": -3.1934
  },
  "contact": {
    "website": "https://www.edinburgh.gov.uk/tennis",
    "phone": "+44 131 123 4567"
  },
  "amenities": {
    "parking_available": true,
    "wifi": false,
    "disabled_access": true
  }
}
```

## Dimensions

Dimensions are stored as a mapping of keys to arrays, allowing for flexible tagging and filtering.
- `canonical_activities`: `["tennis", "coaching"]`
- `canonical_access`: `["pay_and_play", "membership"]`
- `canonical_place_types`: `["sports_centre", "park"]`
