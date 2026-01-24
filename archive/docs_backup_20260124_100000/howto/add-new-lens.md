# How to Add a New Lens

Audience: Product Managers and Developers.

Lenses allow the engine to serve new verticals (e.g., "Wine", "Coffee") without code changes.

## Steps

1.  **Create Lens Directory**
    Create a folder `lenses/<new_vertical_id>`.

2.  **Create Configuration**
    Add `lens.yaml` inside that folder.

    ```yaml
    id: "new_vertical"
    name: "New Vertical"
    description: "Discovery for X"
    facet_mapping:
      activities:
        - "activity_a"
        - "activity_b"
    ```

3.  **Register Lens**
    Ensure the web application is aware of the new lens (usually auto-detected or added to a registry).

Evidence: `lenses/` directory structure.
