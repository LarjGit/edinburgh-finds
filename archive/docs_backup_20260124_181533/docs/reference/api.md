Audience: Developers

# API Documentation

The Edinburgh Finds frontend communicates with the database via Next.js API routes. These routes are "Lens-aware," meaning they filter and transform data based on the active vertical.

## Endpoints

### `GET /api/entities`
Lists entities matching the current Lens and filter criteria.

**Query Parameters:**
- `lens`: (Required) The ID of the active Lens (e.g., `edinburgh_finds`).
- `q`: Search query string.
- `activity`: Filter by activity dimension.
- `lat`, `lng`, `radius`: Spatial filter.
- `limit`, `offset`: Pagination.

### `GET /api/entities/[slug]`
Retrieves full details for a single entity.

### `GET /api/lenses`
Lists all available Lenses configured in the system.

### `GET /api/lenses/[id]/config`
Returns the UI configuration for a specific Lens, including available filters and search features.

---

## Response Format

All successful responses return JSON with the following envelope:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "count": 12,
    "total": 150,
    "lens": "edinburgh_finds"
  }
}
```

## Error Handling

The API uses standard HTTP status codes:
- `200 OK`: Request succeeded.
- `400 Bad Request`: Missing or invalid parameters.
- `404 Not Found`: Entity or Lens does not exist.
- `500 Internal Server Error`: Engine or Database failure.

Errors are returned with an error message:
```json
{
  "success": false,
  "error": "Lens 'invalid_lens' not found."
}
```
