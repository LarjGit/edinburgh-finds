Audience: Developers

# Modifying the Entity Model

The **Universal Entity Model** is the core schema shared across the engine, the database, and the frontend. Modifying it requires updating the YAML definition and regenerating the code artifacts.

## Step 1: Update the YAML Definition

The source of truth is `engine/config/entity_model.yaml`.

### Adding a New Dimension
Dimensions are arrays of strings used for filtering.
```yaml
dimensions:
  # ... existing dimensions
  canonical_price_range:
    description: "Price level (e.g., $, $$, $$$)"
```

### Adding a New Module
Modules are JSONB namespaces for structured data.
```yaml
modules:
  # ... existing modules
  social_media:
    fields:
      instagram: string
      twitter: string
      facebook: string
```

## Step 2: Regenerate Schemas

After changing the YAML, you must run the schema generator to update Python, TypeScript, and Prisma files.

```bash
# Full regeneration
python -m engine.schema.generate --force --format --typescript --prisma
```

This updates:
- `engine/schema/entity.py` (Pydantic models)
- `engine/schema.prisma` (Database schema)
- `web/types/entity.ts` (TypeScript interfaces)
- `web/prisma/schema.prisma` (Frontend database schema)

## Step 3: Migrate the Database

Apply the changes to your PostgreSQL database.

```bash
npx prisma db push --schema engine/schema.prisma
```

## Step 4: Update the Extractor (If Needed)

If you added fields that the LLM should now extract, you may need to update the prompt templates in `engine/extraction/base.py` or the Pydantic extraction model.

The schema generator automatically updates the Pydantic extraction model if you use the `--pydantic-extraction` flag.

## Step 5: Verify the End-to-End Flow

1.  **Extract a sample:** Run a small extraction and verify the new fields are populated in the `Entity` table.
2.  **Frontend Types:** Ensure the web frontend compiles without errors. The new fields should be available in the `Entity` TypeScript type.
3.  **UI Display:** Update components in `web/components/` to render the new data if necessary.

## Important Note on Engine Purity

Never add fields to the universal model that are specific to only one vertical (e.g., `has_clay_court`). Instead, use a generic dimension like `canonical_activities` or a flexible module that can be interpreted differently by various Lenses.
