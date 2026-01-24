# Configuration Reference

Audience: Developers and DevOps.

The application is configured via Environment Variables and YAML configuration files.

## Environment Variables

The `.env` file controls database connections and API keys.

| Variable                | Description                          | Required | Evidence       |
| :---------------------- | :----------------------------------- | :------- | :------------- |
| `DATABASE_URL`          | PostgreSQL connection string.        | Yes      | `.env.example` |
| `ANTHROPIC_API_KEY`     | API key for LLM extraction (Claude). | Yes      | `.env.example` |
| `GOOGLE_PLACES_API_KEY` | Key for fetching venue data.         | Yes      | `.env.example` |
| `SERPER_API_KEY`        | Key for web search (Serper.dev).     | Yes      | `.env.example` |
|                         |                                      |          |                |

## YAML Configuration

The source of truth for the Entity Model and Lenses.

- **Entity Model**: `engine/config/entity_model.yaml` (Defines the universal schema).
- **Lenses**: `lenses/*.yaml` (Defines vertical-specific overrides).

Evidence: `engine/config/README.md` (inferred), `engine/config/entity_model.yaml`
