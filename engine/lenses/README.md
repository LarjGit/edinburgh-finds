# Lens Configuration System

## Purpose

Lenses provide vertical-specific interpretation of universal engine data.
The engine knows NOTHING about domains (Padel, Wine, Restaurants).
All domain knowledge lives in Lens YAML configs.

## Lens YAML Structure

```yaml
# engine/lenses/padel/query_vocabulary.yaml
activity_keywords:
  - padel
  - tennis
  - sport
  - court

location_indicators:
  - edinburgh
  - near
  - in

facility_keywords:
  - centre
  - facility
  - venue
```

```yaml
# engine/lenses/padel/connector_rules.yaml
connectors:
  sport_scotland:
    priority: high
    triggers:
      - type: any_keyword_match
        keywords: [padel, tennis, sport]
        threshold: 1
```

## Usage

```python
from engine.lenses.query_lens import get_active_lens

lens = get_active_lens("padel")
keywords = lens.get_activity_keywords()  # ["padel", "tennis", ...]
connectors = lens.get_connectors_for_query("padel courts", features)
```

## Adding New Vertical

1. Create `engine/lenses/wine/query_vocabulary.yaml`
2. Create `engine/lenses/wine/connector_rules.yaml`
3. DONE - no code changes needed
