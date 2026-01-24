# How-To: Add a New Lens

Adding a new Lens allows you to adapt the Edinburgh Finds engine to a new vertical (e.g., "Fitness Centers", "Art Galleries").

## Step 1: Create the Lens Directory

Create a new folder in the `lenses/` directory:

```bash
mkdir lenses/my_new_vertical
```

## Step 2: Define the Lens Contract

Create a `contract.yaml` (or similar, depending on your implementation's convention) inside your new directory. This file must define:

1.  **Facets**: What dimensions of the data are you tracking? (e.g., `specialty`, `price_range`).
2.  **Values**: The canonical list of keys for each facet.
3.  **Mapping Rules**: Regex patterns to catch raw source categories.
4.  **Module Triggers**: When should the engine include extra modules (like `fitness_details`)?

## Step 3: Register the Lens

Ensure the engine can find your lens. This usually involves adding it to a registry or ensuring it follows the directory naming convention that `scripts/run_lens_aware_extraction.py` expects.

## Step 4: Validate the Lens

Run a validation script if available to ensure your regex patterns are valid and your canonical keys match the `entity_model.yaml` constraints.

```bash
# Example (if a generic validator exists)
python scripts/validate_lens.py --lens my_new_vertical
```

## Step 5: Run Extraction

Start processing data using your new lens rules:

```bash
python scripts/run_lens_aware_extraction.py --lens my_new_vertical
```

## Step 6: Verify in UI

Open the web dashboard and check if entities are correctly classified and associated with your new lens. You may need to add a "Lens Filter" in the UI to see them specifically.
