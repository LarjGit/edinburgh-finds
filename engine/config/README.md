# Configuration Directory

This directory contains configuration files for the data ingestion pipeline.

## Setup

1. **Copy the example configuration:**
   ```bash
   cp sources.yaml.example sources.yaml
   ```

2. **Add your API keys:**
   Edit `sources.yaml` and replace placeholder values with your actual API credentials.

3. **Enable/disable sources:**
   Set `enabled: true` or `enabled: false` for each source as needed.

## File Overview

- **sources.yaml.example** - Template configuration file (committed to git)
- **sources.yaml** - Your actual configuration with API keys (gitignored, never commit this!)

## Configuration Structure

Each data source has the following structure:

```yaml
source_name:
  enabled: true|false          # Whether to use this source
  api_key: "YOUR_KEY_HERE"     # API credentials (null if not required)
  base_url: "https://..."      # Base URL for API requests
  timeout_seconds: 30          # Request timeout
  rate_limits:
    requests_per_minute: 60    # Rate limit per minute
    requests_per_hour: 1000    # Rate limit per hour
  default_params:              # Optional: Source-specific defaults
    key: value
```

## Security

- **NEVER** commit `sources.yaml` to version control
- **NEVER** share API keys in public repositories
- The `.gitignore` file is configured to exclude `sources.yaml`
- Only commit changes to `sources.yaml.example`

## Getting API Keys

### Serper API
- Sign up: https://serper.dev/
- Free tier: 2,500 queries/month

### Google Places API
- Get key: https://developers.google.com/maps/documentation/places/web-service/get-api-key
- Pricing: https://developers.google.com/maps/billing-and-pricing

### OpenChargeMap API
- Get key: https://openchargemap.org/site/develop/api
- Free with attribution

### OpenStreetMap
- No API key required
- Public API with usage limits
- Be respectful: https://operations.osmfoundation.org/policies/api/

## Rate Limiting

Rate limits are enforced per source to prevent:
- Exceeding API quotas
- Getting blocked by providers
- Incurring unexpected costs

The ingestion system will automatically throttle requests to stay within configured limits.

## Loading Configuration

```python
from engine.ingestion.config import load_sources_config

# Load configuration
config = load_sources_config()

# Access source config
serper_config = config['serper']
api_key = serper_config['api_key']
rate_limit = serper_config['rate_limits']['requests_per_minute']
```
