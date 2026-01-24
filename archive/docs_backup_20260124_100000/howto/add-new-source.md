# How to Add a New Data Source

Audience: Data Engineers.

This guide explains how to register a new data ingestion source.

## Steps

1.  **Update Configuration**
    Open `engine/config/sources.yaml` (or create it from `.example`).
    Add a new entry for your source:

    ```yaml
    new_source_name:
      enabled: true
      api_key: "YOUR_KEY"
      base_url: "https://api.example.com"
      rate_limits:
        requests_per_minute: 60
    ```

2.  **Create Connector Script**
    Create a new script in `engine/ingestion/connectors/` (if using modular structure) or a standalone script like `engine/run_new_source.py`.

    Your script should:
    - Fetch data from `base_url`.
    - Create `RawIngestion` records in the database.

3.  **Run Ingestion**
    ```bash
    python engine/run_new_source.py
    ```

Evidence: `engine/config/sources.yaml.example`
