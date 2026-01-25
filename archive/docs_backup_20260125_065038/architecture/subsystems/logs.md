# Subsystem: logs

## Purpose
The logs subsystem contains operational log files generated during data ingestion and extraction processes. These logs help identify data quality issues and missing mapping configurations.

## Key Components
- `logs/unmapped_categories.log`: A list of categories encountered during ingestion that do not have a corresponding mapping in the system's category taxonomy.

## Architecture
The logs are generated as append-only text files by various parts of the engine (e.g., `validator.py`, `category_mapper.py`) when they encounter data that requires manual intervention or configuration updates.

## Dependencies
### Internal
- `engine/modules/validator.py`: May log validation failures.
- `engine/extraction/utils/category_mapper.py`: Logs categories that cannot be mapped to the internal schema.

### External
- None.

## Data Models
Not applicable for this subsystem as it contains plain text logs.

## Configuration
No specific configuration for this subsystem, though the location and verbosity may be controlled by general engine logging configuration.

## Evidence
- `logs/unmapped_categories.log`: Observed entries such as "health_club", "sports_club", "leisure=sports_centre", and "Pádel". Evidence: logs/unmapped_categories.log:1-10
