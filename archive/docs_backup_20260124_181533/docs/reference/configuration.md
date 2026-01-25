Audience: Developers

# Configuration Reference

This document provides a detailed reference for all configuration files used by the Edinburgh Finds extraction engine and ingestion pipeline.

## Overview

Configuration is stored in the `engine/config/` directory. All core configuration is **vertical-agnostic** (engine-purity), while vertical-specific interpretation is handled by the Lens layer.

| File | Purpose | Sensitivity |
| :--- | :--- | :--- |
| `entity_model.yaml` | Defines the universal entity model, classes, and dimensions. | Low |
| `extraction.yaml` | LLM model settings and source trust levels. | Low |
| `sources.yaml` | API keys, base URLs, and rate limits for data sources. | **High** (Ignored) |
| `monitoring_alerts.yaml`| Monitoring thresholds and alert notification channels. | Low |

---

## Entity Model (`entity_model.yaml`)

This file is the "Source of Truth" for the engine's data structure. It defines what an entity fundamentally *is*.

### Entity Classes
Every entity must belong to exactly one class.
- `place`: Physical locations with coordinates (e.g., facilities, shops).
- `person`: Named individuals (e.g., coaches, consultants).
- `organization`: Businesses or groups without a fixed public location.
- `event`: Time-bounded occurrences.
- `thing`: Fallback for other resources.

### Dimensions
Dimensions are multi-valued, opaque `text[]` arrays in Postgres.
- `canonical_activities`: Activities supported (e.g., `padel`, `tennis`).
- `canonical_roles`: Functions the entity plays (e.g., `provides_facility`, `provides_instruction`).
- `canonical_place_types`: Classification of the physical place (e.g., `sports_centre`).
- `canonical_access`: Access requirements (e.g., `membership`, `pay_and_play`).

### Universal Modules
Structured data stored in JSONB namespaces.
- `core`: Required for all (ID, name, slug).
- `location`: Address and coordinates.
- `contact`: Phone, email, socials.
- `hours`: Operating schedules.
- `amenities`: Universal features only (`wifi`, `parking_available`, `disabled_access`).
- `time_range`: Start/end times for events.

---

## Extraction & Trust (`extraction.yaml`)

Defines how the LLM behaves and how data from different sources is prioritized during merging.

### LLM Configuration
- `model`: The specific LLM version to use (e.g., `claude-haiku-20250318`).

### Trust Levels (0-100)
Determines which source "wins" when there is a conflict for the same field.
- `manual_override`: 100 (Always wins)
- `sport_scotland`: 90
- `edinburgh_council`: 85
- `google_places`: 70
- `serper`: 50
- `osm`: 40

---

## Data Sources (`sources.yaml`)

Configures the connectors used to pull data from external APIs. This file is ignored by git; see `sources.yaml.example` for a template.

### Connector Settings
Each connector (e.g., `google_places`, `serper`, `open_street_map`) supports:
- `enabled`: Boolean toggle.
- `api_key`: Authentication credential.
- `base_url`: API endpoint.
- `rate_limits`: `requests_per_minute` and `requests_per_hour`.
- `default_params`: Standard query parameters (e.g., `radius`, `location`, `bbox`).

---

## Monitoring (`monitoring_alerts.yaml`)

Defines the health checks and thresholds for system operations.

### Alert Severities
- **CRITICAL:** Immediate action required (e.g., database down, 10% failure rate, disk full). Notifications via PagerDuty/Email.
- **WARNING:** Review within 24 hours (e.g., high LLM costs, low cache hit rate, backlog growth). Notifications via Slack/Email.
- **INFO:** Review weekly (e.g., merge conflicts, duplicate detection, throughput decline). Notifications via Email.

### Key Metrics
- `extraction_failure_rate`: Alert if > 10%.
- `llm_cost_per_day_gbp`: Warning if > £50.
- `cache_hit_rate_percent`: Warning if < 20%.
- `disk_space_free_percent`: Critical if < 10%.

---

## Validation Rules

1. **Engine Purity:** No vertical-specific terms (e.g., "padel", "coach", "venue") are allowed in `entity_model.yaml` (except in notes/examples).
2. **Postgres Native:** Dimension types in `entity_model.yaml` must match the `schema.prisma` (e.g., `text[]`).
3. **Module Namespacing:** All module data must be nested under its module key in JSONB.
