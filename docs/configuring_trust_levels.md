# Configuring Field-Level Trust Levels

## Overview

Trust levels determine which data source wins when multiple sources provide conflicting values for the same field. This guide explains how to configure, adjust, and validate trust levels in the extraction engine.

**Key Concepts:**
- **Field-level trust**: Trust scores assigned per field, not per entire record
- **Configurable hierarchy**: Easily adjust which sources are trusted more
- **Conflict resolution**: Higher trust wins when sources disagree
- **Manual override**: Human-verified data always has highest trust (100)

---

## Trust Level Configuration File

Trust levels are defined in `engine/config/extraction.yaml`.

**Location:** `engine/config/extraction.yaml`

**Current Configuration:**

```yaml
llm:
  model: "claude-haiku-20250318"

trust_levels:
  manual_override: 100      # Human-verified data (always wins)
  sport_scotland: 90        # Official Scottish government data
  edinburgh_council: 85     # Official Edinburgh Council data
  google_places: 70         # Google's verified business database
  serper: 50                # Search results (less reliable)
  osm: 40                   # Crowdsourced data (variable quality)
  open_charge_map: 40       # Crowdsourced EV charging data
  unknown_source: 10        # Fallback for unrecognized sources
```

---

## Trust Level Guidelines

### Trust Ranges

| Range | Category | Examples | When to Use |
|-------|----------|----------|-------------|
| **90-100** | Authoritative | Government data, manual verification | Official sources, human-verified |
| **70-85** | Commercial Verified | Google Places, Yelp, Tripadvisor | Paid APIs with verification processes |
| **50-65** | Aggregated | Search results, news articles | Third-party aggregators, media |
| **30-45** | Crowdsourced | OpenStreetMap, community databases | User-generated content with some moderation |
| **10-25** | Unverified | Scraped data, unknown sources | Web scraping, unverified sources |

### Selecting Trust Levels

**Questions to Ask:**

1. **Is the source official?**
   - Government/Council → 85-90
   - Commercial verified → 70-85
   - Community/Crowd → 30-45

2. **Does the source verify data?**
   - Manual verification → +10-15
   - Automated checks → +5-10
   - No verification → 0

3. **How often is data updated?**
   - Real-time/frequent → +5
   - Occasional → 0
   - Stale → -10

4. **What's the error rate?**
   - <1% errors → +5
   - 1-5% errors → 0
   - >5% errors → -10

---

## Adding a New Source

### Step 1: Determine Trust Level

Let's say you're adding **Strava Segments** as a source.

**Analysis:**
- **Source type**: Commercial API (Strava)
- **Verification**: Users create segments, some Strava verification
- **Update frequency**: Real-time
- **Error rate**: ~3% (user-generated boundaries can be imprecise)

**Trust Calculation:**
- Base (commercial): 70
- User-generated: -10
- Real-time updates: +5
- **Final Trust: 65**

### Step 2: Add to Configuration

Edit `engine/config/extraction.yaml`:

```yaml
trust_levels:
  manual_override: 100
  sport_scotland: 90
  edinburgh_council: 85
  google_places: 70
  strava: 65  # ← ADD YOUR SOURCE HERE
  serper: 50
  osm: 40
  open_charge_map: 40
  unknown_source: 10
```

### Step 3: Verify Configuration

**Test that trust level is loaded:**

```bash
python -c "
from engine.extraction.config import load_extraction_config

config = load_extraction_config()
print('Strava trust level:', config['trust_levels']['strava'])
# Expected output: 65
"
```

---

## Adjusting Existing Trust Levels

### When to Adjust

**Increase trust when:**
- Source improves data quality over time
- You discover the source is more reliable than expected
- Source adds verification processes

**Decrease trust when:**
- Source has frequent errors
- Data becomes stale
- Source removes verification

### Example: Increasing OSM Trust

**Scenario:** After running extraction, you notice OSM opening hours are more accurate than Google Places (community keeps them updated).

**Before:**
```yaml
trust_levels:
  google_places: 70
  osm: 40
```

**Analysis:**
- OSM opening_hours field is frequently updated by local community
- Google Places opening_hours often outdated
- But OSM phone numbers are still unreliable

**Solution: Field-specific trust override (future feature)**

For now, adjust overall trust:

**After:**
```yaml
trust_levels:
  google_places: 70
  osm: 50  # Increased from 40 (better opening hours data observed)
```

**Note:** Field-specific trust levels (e.g., `osm.opening_hours: 75, osm.phone: 30`) are a planned Phase 10 feature.

---

## Testing Trust Hierarchy

### Test Scenario: Conflicting Phone Numbers

**Setup:**
- Google Places provides: `+441315397071`
- OSM provides: `+441315397072`

**Expected Behavior:**
- Google (trust 70) > OSM (trust 40)
- **Result:** Google's phone number wins

**Test:**

```python
# Create test case
from engine.extraction.merging import merge_listings

listings = [
    {
        "source": "google_places",
        "phone": "+441315397071",
        "trust_score": 70,
    },
    {
        "source": "osm",
        "phone": "+441315397072",
        "trust_score": 40,
    }
]

merged = merge_listings(listings)
assert merged["phone"] == "+441315397071"  # Google wins
assert merged["source_info"]["phone"] == "google_places"
```

### Verify in Production

After adjusting trust levels, check merge conflicts in health dashboard:

```bash
python -m engine.extraction.health
```

**Look for "Merge Conflicts" section:**

```
MERGE CONFLICTS

Total Conflicts: 3

┌──────────────┬──────────────┬──────────────────┬──────────────────┐
│ Listing      │ Field        │ Conflict         │ Resolution       │
├──────────────┼──────────────┼──────────────────┼──────────────────┤
│ Game4Padel   │ phone        │ +4413... vs +... │ Google wins (T70)│
│ Portobello   │ opening_hours│ {...} vs {...}   │ Manual review    │
└──────────────┴──────────────┴──────────────────┴──────────────────┘
```

**Analysis:**
- "Google wins (T70)" means Google's trust level (70) was higher
- "Manual review" means trust levels were too close, needs human decision

---

## Manual Override (Trust 100)

### When to Use Manual Override

**Use `manual_override` for:**
- Human-verified data
- Business owner claims
- Data corrected after manual inspection

**Example:**

A business owner contacts you: "Our phone number is wrong on your site."

**Workflow:**

1. **Verify** the correct information with the business owner
2. **Update** listing with manual override
3. **Document** source as `manual_override`

```python
# Update listing with manual override
await db.listing.update(
    where={"id": "clx123..."},
    data={
        "phone": "+441315397073",  # Correct number from owner
        "source_info": json.dumps({
            "phone": "manual_override"  # Trust level: 100
        }),
        "field_confidence": json.dumps({
            "phone": 100  # Highest trust
        })
    }
)
```

**Result:**
- Future extractions won't override this field (trust 100 always wins)
- `source_info` shows "manual_override" for transparency

---

## Advanced: Weighted Merging

### Future Feature: Confidence-Weighted Merging

**Current (simple):** Highest trust wins

**Planned (Phase 10):** Weighted average based on confidence scores

**Example:**

```python
# Current behavior (Phase 9)
Source A (trust=70): phone = "+441315397071"
Source B (trust=65): phone = "+441315397071"  # Same value
→ Result: "+441315397071" (trust=70)

# Future behavior (Phase 10)
Source A (trust=70, confidence=0.9): latitude = 55.9533
Source B (trust=65, confidence=0.95): latitude = 55.9535
→ Result: Weighted average based on trust × confidence
→ latitude = 55.9534 (blended value)
```

**Configuration (future):**

```yaml
merging:
  strategy: "weighted"  # vs "highest_trust"
  confidence_weight: 0.3  # How much to weight confidence vs trust
  min_trust_gap: 15  # Only merge if trust gap < 15
```

---

## Troubleshooting Trust Levels

### Issue: Wrong Source Winning Merges

**Symptom:**
```
ERROR: OSM phone number overriding Google Places despite lower trust
```

**Diagnosis:**

```bash
# Check actual trust levels
python -c "
from engine.extraction.config import load_extraction_config
config = load_extraction_config()
print('OSM trust:', config['trust_levels']['osm'])
print('Google trust:', config['trust_levels']['google_places'])
"
```

**Common Causes:**

1. **Typo in source name**: `osm` vs `open_street_map` (doesn't match config)
2. **Default trust used**: Source not in config, gets `unknown_source: 10`
3. **Manual override exists**: A `manual_override` entry is overriding everything

**Fix:**

Ensure source names match exactly:
- `extractor.source_name = "osm"`
- `extraction.yaml: osm: 40`
- `RawIngestion.source = "osm"`

---

### Issue: Trust Level Not Applied

**Symptom:**
```
WARNING: Trust level not found for source 'strava', using default (10)
```

**Diagnosis:**

```bash
# Verify source is in config
grep "strava" engine/config/extraction.yaml
```

**Fix:**

Add to `extraction.yaml`:
```yaml
trust_levels:
  # ...
  strava: 65  # ADD THIS LINE
  # ...
```

**Verify:**

```bash
# Reload config and test
python -m engine.extraction.run --source=strava --limit=1
# Should now see "Using trust level: 65" in logs
```

---

## Best Practices

### 1. Document Trust Rationale

**Good Practice:**

```yaml
trust_levels:
  # Official Scottish Sports Council data - government verified
  sport_scotland: 90

  # Google Places API - commercial verification, frequent updates
  google_places: 70

  # OpenStreetMap - crowdsourced, variable quality but community-moderated
  osm: 40
```

**Why:** Makes it clear why trust levels were chosen, helps future adjustments.

### 2. Review Trust Levels Quarterly

**Workflow:**

1. **Run health dashboard**, note conflict patterns
2. **Analyze merge conflicts**, see which sources are winning
3. **Adjust trust levels** if data quality has changed
4. **Re-extract** with `--force-retry` if needed

```bash
# Quarterly review
python -m engine.extraction.health > health_report_$(date +%Y%m%d).txt
# Review merge conflicts section
# Adjust trust levels in extraction.yaml
# Re-extract affected records
python -m engine.extraction.run --source=osm --force-retry
```

### 3. Use Manual Override Sparingly

**Rule:** Only use `manual_override` (trust 100) for human-verified data.

**Bad:**
```python
# DON'T use manual override just because you prefer a source
source_info["phone"] = "manual_override"  # ✗ Bad
```

**Good:**
```python
# DO use manual override for verified data
# After calling business and confirming phone number
source_info["phone"] = "manual_override"  # ✓ Good
```

### 4. Test Trust Changes Before Production

**Before:**
```bash
# Test with dry-run first
python -m engine.extraction.run --source=google_places --limit=10 --dry-run
```

**After adjusting trust:**
```bash
# Dry-run to preview merge results
python -m engine.extraction.run --source=google_places --limit=10 --dry-run

# If results look good, run for real
python -m engine.extraction.run --source=google_places --force-retry
```

---

## Real-World Examples

### Example 1: Promoting a High-Quality Source

**Scenario:** You discover that Sport Scotland's facility data is more accurate than expected.

**Initial config:**
```yaml
trust_levels:
  sport_scotland: 80
  google_places: 70
```

**Analysis:**
- 100% of Sport Scotland coordinates match site visits
- Google Places has 5% error rate (wrong buildings, outdated locations)

**Action: Increase Sport Scotland trust**

```yaml
trust_levels:
  sport_scotland: 90  # Increased from 80 (high accuracy verified)
  google_places: 70
```

**Result:**
- Sport Scotland now wins coordinate conflicts against Google
- Better data quality for sports facilities

---

### Example 2: Demoting a Degraded Source

**Scenario:** OpenChargeMap data quality has degraded (community abandoned project).

**Initial config:**
```yaml
trust_levels:
  open_charge_map: 40
```

**Analysis:**
- Last updated: 2 years ago (stale data)
- 20% of charging stations no longer exist
- User reports increasing errors

**Action: Decrease trust**

```yaml
trust_levels:
  open_charge_map: 20  # Decreased from 40 (stale data, high error rate)
```

**Alternative: Remove source entirely**

If data is too poor, stop extracting:

```python
# Remove from extractor map in run.py
extractors = {
    "google_places": GooglePlacesExtractor,
    # "open_charge_map": OpenChargeMapExtractor,  # ← Comment out
}
```

---

## Summary

**Key Takeaways:**

1. **Trust levels are configurable** in `engine/config/extraction.yaml`
2. **Higher trust wins** conflicts (manual override = 100 always wins)
3. **Adjust based on observed quality**, not assumptions
4. **Test changes** with `--dry-run` before production
5. **Document rationale** for trust levels
6. **Review quarterly** and adjust as sources evolve

**Quick Reference:**

```yaml
# engine/config/extraction.yaml

trust_levels:
  manual_override: 100    # Human-verified (always wins)
  government_source: 90   # Official data
  commercial_verified: 70 # Paid APIs with verification
  aggregator: 50          # Search results, news
  crowdsourced: 40        # Community data
  unverified: 20          # Scraped, unverified
  unknown_source: 10      # Fallback
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-17
**Related Docs:**
- [Extraction Engine Overview](./extraction_engine_overview.md) - Trust hierarchy explanation
- [Troubleshooting Guide](./troubleshooting_extraction.md) - Trust level errors
