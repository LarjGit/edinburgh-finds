Audience: Developers

# Adding a New Lens

A **Lens** defines a vertical-specific view of the universal entity data. Adding a new Lens (e.g., "Tennis Discovery" or "Organic Coffee") involves configuring search queries, classification rules, and UI features.

## Step 1: Create the Lens Configuration

1.  Navigate to the `lenses/` directory.
2.  Create a new folder for your Lens (e.g., `lenses/tennis_discovery/`).
3.  Create a `lens.yaml` file in that folder.

### Example `lens.yaml`
```yaml
id: tennis_discovery
name: Tennis in Edinburgh
description: Find tennis courts, clubs, and coaches.

# Initial search queries for the orchestrator
seed_queries:
  - "tennis courts edinburgh"
  - "tennis clubs edinburgh"
  - "tennis coaching edinburgh"

# Rules to classify raw records as relevant to this Lens
classification:
  required_activities: ["tennis"]
  required_classes: ["place", "person"]

# UI Configuration
ui:
  theme_color: "#32a852"
  filters:
    - dimension: canonical_access
      label: Access Type
    - dimension: canonical_place_types
      label: Facility Type
  search_placeholder: "Search for courts or coaches..."
```

## Step 2: Validate the Lens

Run the lens validator to ensure your configuration adheres to engine purity rules.

```bash
python -m engine.lenses.validator lenses/tennis_discovery/lens.yaml
```

## Step 3: Register the Lens (Optional)

If the orchestrator doesn't automatically detect the new folder, you may need to add it to the active lenses list in `engine/config/orchestration.yaml` (if applicable).

## Step 4: Run a Discovery Cycle

Test your new Lens by running a targeted ingestion:

```bash
python -m engine.orchestration.orchestrator --lens tennis_discovery --limit 5
```

## Step 5: Verify in the UI

1.  Start the web frontend (`npm run dev` in `web/`).
2.  Navigate to `http://localhost:3000/?lens=tennis_discovery`.
3.  Ensure the filters and search results reflect your configuration.

## Best Practices

- **Keep it Universal:** Avoid adding new fields to the `Entity` table for a specific Lens. Use **Dimensions** or **Modules** defined in `entity_model.yaml`.
- **Seed Broadly:** Use varied search terms in `seed_queries` to cover different sources (OSM uses tags, while Google Places uses natural language).
- **Classification is Key:** Use specific `required_activities` to prevent "noise" (e.g., a park that has a tennis court vs. just a park).
