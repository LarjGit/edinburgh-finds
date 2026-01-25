# Subsystem: root

## Purpose
The root subsystem contains project-wide configuration files, environment definitions, and version control settings that govern the entire repository.

## Key Components
- `.env.example`: Provides a template for required environment variables, including database connections and API keys for external services (Anthropic, Google, Serper).
- `.gitignore`: Defines files and directories to be excluded from version control, such as environment secrets, build artifacts, temporary files, and raw data.
- `.gitattributes`: Specifies repository-wide path attributes, notably marking auto-generated schema files in the engine.
- `pytest.ini`: (Implicitly part of root) Configures the pytest environment for the project.

## Architecture
These files provide the foundation for the development environment. The `.env` system ensures that sensitive credentials and environment-specific settings are kept out of version control while providing a clear interface for configuration. The git configuration files maintain repository hygiene by excluding transient data and marking generated code.

## Dependencies
### External
- **Git**: Used for version control and repository management.
- **Anthropic API**: Used for LLM-based data extraction.
- **Google Places API**: Used for venue data ingestion.
- **Serper API**: Used for search-based data discovery.

## Configuration
The project relies on several key environment variables defined in `.env`:
- `DATABASE_URL`: Connection string for the PostgreSQL database.
- `ANTHROPIC_API_KEY`: Authentication for Anthropic's Claude API.
- `GOOGLE_PLACES_API_KEY`: Authentication for Google Places API.
- `SERPER_API_KEY`: Authentication for Serper API.
- `LOG_LEVEL`: Controls the verbosity of application logs.

## Evidence
- `.env.example`: lines 10-25 (API keys and database configuration)
- `.gitattributes`: lines 1-7 (Generated schema files marking)
- `.gitignore`: (Standard exclusions for Python, Node.js, and data files)
