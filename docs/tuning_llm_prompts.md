# Tuning LLM Prompts for Extraction

## Overview

LLM-based extractors (Serper, OSM) use prompt templates to guide Claude in extracting structured data from unstructured text. Well-crafted prompts significantly improve extraction quality, reduce errors, and lower costs.

This guide explains how to customize prompts for different sources, test prompt changes, and optimize for quality and cost.

**LLM Extractors:**
- **Serper**: Search result snippets (very unstructured)
- **OSM**: Free-text tags and descriptions (semi-structured)

**Deterministic Extractors (No LLM):**
- Google Places, Sport Scotland, Edinburgh Council, OpenChargeMap use rule-based extraction (no prompts needed)

---

## Prompt Architecture

### Base Prompt Template

**Location:** `engine/extraction/prompts/extraction_base.txt`

**Purpose:** Defines global extraction rules applicable to all sources.

**Key Sections:**

```
1. Role Definition: "You are a data extraction assistant..."
2. Null Semantics Rules: How to handle missing data
3. Extraction Guidelines: General rules (precision, required fields)
4. Field-Specific Rules: Phone numbers, postcodes, coordinates
5. Validation: Pre-submission checks
6. Output Format: JSON schema instructions
```

**Used By:** All LLM extractors (inherited)

---

### Source-Specific Prompts

**Location:** `engine/extraction/prompts/<source>_extraction.txt`

**Purpose:** Customize extraction for source-specific data characteristics.

**Examples:**
- `serper_extraction.txt`: Search snippets (fragments, inconsistencies)
- `osm_extraction.txt`: Free-text tags (key=value pairs, multilingual)

**Structure:**

```
1. Context: Data characteristics of this source
2. Extraction Strategy: Source-specific techniques
3. Special Cases: Edge cases unique to this source
4. Expected Outcomes: What fields are likely null
```

---

## Prompt Construction

### How Prompts Are Combined

```python
# In llm_client.py

def build_prompt(source: str, raw_data: Dict) -> str:
    # Step 1: Load base prompt
    base_prompt = load_prompt("extraction_base.txt")

    # Step 2: Load source-specific prompt
    source_prompt = load_prompt(f"{source}_extraction.txt")

    # Step 3: Format raw data into context
    context = format_raw_data(raw_data)

    # Step 4: Combine
    full_prompt = f"""
{base_prompt}

{source_prompt}

## RAW DATA CONTEXT

{context}

Extract venue information from the above context.
"""

    return full_prompt
```

**Result:**

```
[Base Rules: Null semantics, validation, etc.]
[Source-Specific Rules: Serper snippet aggregation]
[Raw Data: Actual search snippets to extract from]
[Instruction: Extract venue information]
```

---

## Customizing Prompts

### When to Customize

**Customize when:**
- Extraction quality is poor (high null rates, hallucinations)
- LLM misinterprets source-specific data formats
- New edge cases discovered during testing
- Cost optimization needed (shorter prompts = fewer tokens)

**Don't customize when:**
- Extraction is already >90% accurate
- Issue is with raw data quality, not prompt
- Problem can be solved with validation rules in `validate()` method

---

### Step-by-Step: Improving Serper Extraction

**Problem:** Serper extractor frequently hallucinates phone numbers.

#### Step 1: Diagnose the Issue

**Run extraction with verbose output:**

```bash
python -m engine.extraction.run --source=serper --limit=10 --verbose
```

**Analyze output:**

```
Extracted Record 1:
  entity_name: "Game4Padel Edinburgh"
  phone: "+441315397071"  ← Hallucinated (not in snippets!)
  street_address: null
  city: "Edinburgh"

Extracted Record 2:
  entity_name: "Portobello Padel Club"
  phone: "+441234567890"  ← Obviously fake number
  street_address: "123 Main St"  ← Not in snippets!
  city: "Edinburgh"
```

**Root Cause:** LLM is inferring/guessing phone numbers instead of using `null`.

---

#### Step 2: Locate Relevant Prompt Section

**Edit:** `engine/extraction/prompts/serper_extraction.txt`

**Find the contact information section:**

```
## EXTRACTION STRATEGY

...

3. **Contact Information**
   - Phone numbers: Must convert to E.164 format (+44...)
   - Common formats in snippets: "0131 539 7071", "Call: 0131-539-7071", etc.
   - Website: Extract only if a clear official website is mentioned
```

**Analysis:** Prompt doesn't emphasize "only if explicitly mentioned".

---

#### Step 3: Strengthen Prompt

**Before:**

```
3. **Contact Information**
   - Phone numbers: Must convert to E.164 format (+44...)
   - Common formats in snippets: "0131 539 7071", "Call: 0131-539-7071", etc.
```

**After:**

```
3. **Contact Information - EXTRACT ONLY IF EXPLICITLY MENTIONED**
   - Phone numbers: ONLY extract if a phone number appears in the snippets
     - If no phone number in snippets → phone: null
     - Do NOT infer, guess, or create phone numbers
     - Format: Must convert to E.164 format (+44...)
     - Common formats in snippets: "0131 539 7071", "Call: 0131-539-7071", etc.
   - Website: Extract ONLY if a clear official website URL is mentioned
     - Do NOT use Google Maps links or directory URLs
     - If no website mentioned → website_url: null
```

**Changes:**
- ✅ Added "ONLY IF EXPLICITLY MENTIONED" (emphasis)
- ✅ Explicit instruction: "If no phone → null"
- ✅ Prohibition: "Do NOT infer, guess, or create"

---

#### Step 4: Test Prompt Change

**Create test case with fixture:**

```python
# File: engine/extraction/tests/test_serper_extractor.py

def test_no_hallucinate_phone():
    """Test that phone is null when not in snippets"""
    # Fixture with NO phone number
    raw_data = {
        "organic": [
            {
                "title": "Game4Padel Edinburgh - Padel Courts",
                "snippet": "Find padel courts in Edinburgh. Open 7 days a week."
            }
        ]
    }

    extractor = SerperExtractor()
    extracted = extractor.extract(raw_data)

    # Phone should be null (not hallucinated)
    assert extracted["phone"] is None, "Phone should be null when not in snippets"


def test_extract_phone_when_present():
    """Test that phone is extracted when present"""
    raw_data = {
        "organic": [
            {
                "title": "Game4Padel Edinburgh",
                "snippet": "Contact us at 0131 539 7071 for bookings."
            }
        ]
    }

    extractor = SerperExtractor()
    extracted = extractor.extract(raw_data)

    # Phone should be extracted and formatted
    assert extracted["phone"] == "+441315397071"
```

**Run tests:**

```bash
pytest engine/extraction/tests/test_serper_extractor.py::test_no_hallucinate_phone -v
pytest engine/extraction/tests/test_serper_extractor.py::test_extract_phone_when_present -v
```

---

#### Step 5: Verify in Production

**Re-extract Serper records:**

```bash
python -m engine.extraction.run --source=serper --limit=20 --force-retry --verbose
```

**Check null rates in health dashboard:**

```bash
python -m engine.extraction.health
```

**Expected Outcome:**

```
FIELD NULL RATES

┌─────────────────────┬──────────────┬──────────┐
│ Field               │ Null Rate    │ Status   │
├─────────────────────┼──────────────┼──────────┤
│ phone (serper)      │ 75.00%       │ ✓ Good   │  ← Increased from 20% (less hallucination)
└─────────────────────┴──────────────┴──────────┘
```

**Note:** Higher null rate = good (means less hallucination for unstructured data).

---

## Prompt Tuning Techniques

### Technique 1: Emphasize Critical Rules

**Use formatting to draw attention:**

**Weak:**
```
Phone numbers should be null if not found.
```

**Strong:**
```
**CRITICAL: Phone numbers**
- ONLY extract if explicitly mentioned in the raw data
- If no phone number found → phone: null
- Do NOT infer, guess, or create phone numbers
```

**Why:** LLMs respond better to visual emphasis and explicit prohibitions.

---

### Technique 2: Provide Examples

**Before (vague):**
```
Extract categories from the text.
```

**After (specific):**
```
Extract categories from the text.

**Examples:**
- Text: "Indoor padel facility with coaching"
  → categories: ["Padel", "Indoor Venue", "Coaching Available"]

- Text: "Sports centre offering tennis and squash"
  → categories: ["Sports Centre", "Tennis", "Squash"]

- Text: "No categories mentioned"
  → categories: null
```

**Why:** Examples clarify expected behavior and edge cases.

---

### Technique 3: Explicit Null Semantics

**Critical for extraction quality:**

```
## NULL SEMANTICS - FOLLOW EXACTLY

1. **Use `null` for missing information**
   - Not found in text → null
   - Unclear or ambiguous → null
   - NEVER use "Unknown", "N/A", "", or 0 for missing data

2. **For booleans: null ≠ false**
   - null = "not mentioned"
   - true = "explicitly yes"
   - false = "explicitly no"

   Example:
   - "Has wheelchair access" → wheelchair_accessible: true
   - "Not wheelchair accessible" → wheelchair_accessible: false
   - No mention of accessibility → wheelchair_accessible: null
```

**Why:** Null semantics are counter-intuitive for LLMs; explicit rules reduce errors.

---

### Technique 4: Prevent Common Hallucinations

**Identify hallucination patterns:**

```bash
# Check for suspicious data
python -c "
from prisma import Prisma
import asyncio

async def check_hallucinations():
    db = Prisma()
    await db.connect()

    # Find listings with phone numbers from Serper
    listings = await db.extractedlisting.find_many(
        where={'source': 'serper'},
        take=100
    )

    for listing in listings:
        attrs = json.loads(listing.attributes or '{}')
        phone = attrs.get('phone')
        if phone and phone.startswith('+44123'):  # Suspicious pattern
            print(f'Suspicious phone: {phone} (ID: {listing.id})')

    await db.disconnect()

asyncio.run(check_hallucinations())
"
```

**Add anti-hallucination rules:**

```
## ANTI-HALLUCINATION RULES

**Do NOT:**
- Create placeholder phone numbers (e.g., +441234567890, +440000000000)
- Infer addresses from city names alone (e.g., "123 Main Street, Edinburgh")
- Generate opening hours if only "Open 7 days" is mentioned
- Create website URLs (e.g., "www.venuename.com") if not in text
- Assume coordinates from city/area names

**If you don't know, use null.**
```

---

### Technique 5: Source-Specific Handling

**Tailor prompts to data characteristics:**

**Serper (unstructured fragments):**

```
## SERPER DATA CHARACTERISTICS

Snippets are:
- Fragments from web pages (NOT complete data)
- Often incomplete or contradictory
- May mention multiple venues

**Strategy:**
- Expect HIGH null rates (60-80% for optional fields)
- Aggregate info from multiple snippets
- Use null aggressively when uncertain
```

**OSM (semi-structured tags):**

```
## OSM DATA CHARACTERISTICS

Tags are:
- Key=value pairs (e.g., sport=padel;tennis)
- Often multilingual
- User-generated (variable quality)

**Strategy:**
- Parse key=value carefully (watch for semicolons)
- Handle multiple values per key
- Translate non-English tags if clear meaning
```

---

## Testing Prompt Changes

### Unit Testing

**Test specific extraction scenarios:**

```python
# engine/extraction/tests/test_serper_extractor.py

def test_phone_null_when_missing():
    """Verify phone is null when not in snippets"""
    extractor = SerperExtractor()
    raw = {"organic": [{"title": "Venue", "snippet": "No contact info"}]}
    result = extractor.extract(raw)
    assert result["phone"] is None

def test_phone_formatted_when_present():
    """Verify phone is extracted and formatted"""
    extractor = SerperExtractor()
    raw = {"organic": [{"snippet": "Call 0131 539 7071"}]}
    result = extractor.extract(raw)
    assert result["phone"] == "+441315397071"

def test_ambiguous_phone_null():
    """Verify phone is null when ambiguous"""
    extractor = SerperExtractor()
    raw = {"organic": [
        {"snippet": "Phone: 0131 539 7071"},
        {"snippet": "Call: 0131 123 4567"}  # Conflicting!
    ]}
    result = extractor.extract(raw)
    # Should be null due to conflict
    assert result["phone"] is None
```

---

### Regression Testing (Snapshots)

**Prevent prompt changes from breaking existing extractions:**

```bash
# Step 1: Create snapshot BEFORE prompt change
python -m engine.extraction.run --source=serper --limit=10 --dry-run > snapshots/serper_before.json

# Step 2: Edit prompt (engine/extraction/prompts/serper_extraction.txt)

# Step 3: Create snapshot AFTER prompt change
python -m engine.extraction.run --source=serper --limit=10 --dry-run > snapshots/serper_after.json

# Step 4: Compare
diff snapshots/serper_before.json snapshots/serper_after.json

# Step 5: Verify improvements
# - Fewer hallucinations? ✓
# - More nulls for missing data? ✓
# - No new errors? ✓
```

---

### A/B Testing (Advanced)

**Test two prompt versions and compare quality:**

```bash
# Version A (current prompt)
python -m engine.extraction.run --source=serper --limit=50 > results_prompt_a.json

# Version B (new prompt)
# (Temporarily swap prompt file)
cp engine/extraction/prompts/serper_extraction_v2.txt engine/extraction/prompts/serper_extraction.txt
python -m engine.extraction.run --source=serper --limit=50 --force-retry > results_prompt_b.json

# Compare quality metrics
python scripts/compare_extraction_quality.py results_prompt_a.json results_prompt_b.json
```

**Quality Metrics:**
- Null rate (should be high for unstructured sources)
- Hallucination rate (count obviously fake data)
- Field coverage (how many fields extracted per record)
- Validation errors (failed format checks)

---

## Optimizing for Cost

### Token Reduction

**LLM costs scale with tokens. Reduce prompt size without sacrificing quality.**

#### Before (verbose):

```
You are a data extraction assistant for Edinburgh Finds, a hyper-local discovery platform
that helps enthusiasts find venues, coaches, and clubs for their hobbies. Your task is to
extract structured venue information from the provided raw data context, ensuring that all
extracted data is accurate, complete, and properly formatted according to our schema.

When extracting data, you must follow these critical rules for handling missing or unknown
information. These rules are extremely important and must be followed exactly as specified...
```

**Token Count:** ~150 tokens

#### After (concise):

```
You are a data extraction assistant. Extract structured venue data from the context below.

CRITICAL RULES:
- Use null for missing data (NOT "Unknown", "", or 0)
- Only extract explicitly stated information
- Do not infer or hallucinate data
```

**Token Count:** ~40 tokens

**Savings:** 110 tokens × 1000 extractions = £0.03 saved (small, but adds up)

---

### Conditional Sections

**Include sections only when relevant:**

```python
# In build_prompt()

def build_prompt(source: str, raw_data: Dict) -> str:
    base = load_prompt("extraction_base.txt")

    # Only include opening hours rules if source provides hours
    if source in ["google_places", "sport_scotland"]:
        base += load_prompt_section("opening_hours_rules.txt")

    # Only include multilingual rules for OSM
    if source == "osm":
        base += load_prompt_section("multilingual_handling.txt")

    return base + format_context(raw_data)
```

**Why:** Shorter prompts = fewer tokens = lower cost

---

## Prompt Maintenance

### Version Control

**Track prompt changes in git:**

```bash
# Before editing
git log engine/extraction/prompts/serper_extraction.txt

# Make changes

# Commit with descriptive message
git add engine/extraction/prompts/serper_extraction.txt
git commit -m "fix(prompts): Reduce Serper phone hallucinations

Added explicit prohibition against inferring phone numbers.
Expected outcome: Higher null rate for phone field (less hallucination).

Tested on 50 records, hallucination rate dropped from 20% to 2%."
```

---

### Quarterly Review

**Schedule:** Every 3 months

**Workflow:**

```bash
# 1. Run health dashboard, capture current metrics
python -m engine.extraction.health > health_$(date +%Y%m%d).txt

# 2. Identify problem areas
# Example: Serper phone field has 30% hallucination rate

# 3. Update prompts to address issues

# 4. Re-test
pytest engine/extraction/tests/test_serper_extractor.py -v

# 5. Re-extract sample
python -m engine.extraction.run --source=serper --limit=100 --force-retry

# 6. Compare metrics
python -m engine.extraction.health > health_after_$(date +%Y%m%d).txt
diff health_before.txt health_after.txt
```

---

## Real-World Examples

### Example 1: Fixing OSM Tag Parsing

**Problem:** OSM tags like `sport=padel;tennis` only extract "padel", miss "tennis".

**Root Cause:** Prompt doesn't explain semicolon-separated values.

**Fix:**

**Edit:** `engine/extraction/prompts/osm_extraction.txt`

**Add:**

```
## OSM TAG PARSING RULES

**Multiple Values (semicolon-separated):**

OSM tags often contain multiple values separated by semicolons.

Examples:
- sport=padel;tennis → Both padel AND tennis are offered
- amenity=cafe;restaurant → Both cafe AND restaurant

**Extraction:**
- Split on semicolons
- Extract each value separately
- Example: sport=padel;tennis → categories: ["Padel", "Tennis"]
```

**Test:**

```python
def test_osm_multi_sport_tags():
    """Test parsing semicolon-separated sport tags"""
    raw = {
        "elements": [{
            "tags": {
                "name": "Multi-Sport Centre",
                "sport": "padel;tennis;squash"
            }
        }]
    }

    extractor = OSMExtractor()
    result = extractor.extract(raw)

    # Should extract all sports
    assert "Padel" in result["categories"]
    assert "Tennis" in result["categories"]
    assert "Squash" in result["categories"]
```

---

### Example 2: Handling Serper Snippet Conflicts

**Problem:** Different snippets provide conflicting phone numbers.

**Current Behavior:** LLM picks one arbitrarily.

**Desired Behavior:** Use `null` when conflicting.

**Fix:**

**Edit:** `engine/extraction/prompts/serper_extraction.txt`

**Update snippet aggregation section:**

```
## SNIPPET AGGREGATION - CONFLICT HANDLING

When multiple snippets provide DIFFERENT values for the same field:

**Conflicting Contact Info:**
- If different phone numbers appear → phone: null (we can't know which is correct)
- If different emails appear → email: null
- If different addresses appear → Choose the most complete, or null if equally detailed

**Conflicting Ratings:**
- Use the rating from the official source (not aggregator sites)
- If multiple official ratings → Use the one with more reviews
- If unclear → rating: null

**Rule: When in doubt, use null.**
```

---

## Troubleshooting Prompt Issues

### Issue 1: LLM Ignoring Instructions

**Symptom:**
```
Prompt says "use null for missing data"
But LLM returns: phone: "Not available"
```

**Diagnosis:**
- Instruction not emphasized enough
- Conflicting instructions in prompt

**Fix:**

```
## CRITICAL: NULL SEMANTICS (FOLLOW EXACTLY)

**DO THIS:**
- Missing data → null
- Unknown value → null

**DO NOT DO THIS:**
- "Not available" ✗
- "Unknown" ✗
- "N/A" ✗
- "" (empty string) ✗
- 0 (for missing numbers) ✗

If you use any of the above, the extraction will FAIL validation.
Use null ONLY.
```

---

### Issue 2: High Retry Rate (Validation Failures)

**Symptom:**
```
[WARNING] LLM retry 1/2: Pydantic validation error (phone format invalid)
[WARNING] LLM retry 2/2: Pydantic validation error (phone format invalid)
[ERROR] Extraction failed after max retries
```

**Diagnosis:**
- LLM not following format rules (e.g., E.164 for phone)

**Fix:**

```
## PHONE NUMBER FORMAT - CRITICAL

**Format: E.164 (REQUIRED)**
- Must start with +44
- No spaces, no dashes, no parentheses
- Just digits after +44

**Examples:**
- "0131 539 7071" → "+441315397071" ✓
- "07700 900123" → "+447700900123" ✓
- "+44 (0)131 539 7071" → "+441315397071" ✓

**Invalid Formats (will fail validation):**
- "+44 131 539 7071" ✗ (has spaces)
- "+44-131-539-7071" ✗ (has dashes)
- "0131 539 7071" ✗ (not E.164)

If you cannot format correctly → use null
```

---

### Issue 3: Prompt Too Long (High Costs)

**Symptom:**
```
LLM cost report: £2.50 per 100 records (expected: £0.30)
```

**Diagnosis:**
- Prompt is too verbose
- Redundant sections

**Fix:**

**Audit token usage:**

```bash
# Count tokens in prompt
python -c "
from anthropic import Anthropic

client = Anthropic()

with open('engine/extraction/prompts/serper_extraction.txt', 'r') as f:
    prompt = f.read()

# Estimate tokens (rough: 1 token ≈ 4 characters)
estimated_tokens = len(prompt) / 4
print(f'Estimated tokens: {estimated_tokens}')
"
```

**Trim unnecessary content:**
- Remove redundant examples
- Combine similar rules
- Use bullet points instead of paragraphs

---

## Summary

**Key Takeaways:**

1. **Two-tier prompts**: Base prompt (global rules) + Source prompt (source-specific)
2. **Emphasize critical rules**: Use formatting, examples, explicit prohibitions
3. **Test changes**: Unit tests, snapshots, A/B testing
4. **Optimize for cost**: Trim verbose sections, conditional rules
5. **Review quarterly**: Update prompts as data characteristics change

**Prompt Quality Checklist:**

- [ ] Null semantics clearly defined
- [ ] Anti-hallucination rules included
- [ ] Field-specific format rules (phone, postcode, etc.)
- [ ] Source-specific data characteristics explained
- [ ] Examples provided for ambiguous cases
- [ ] Validation rules stated
- [ ] Tested with unit tests and snapshots

**Quick Reference:**

```bash
# Test prompt change
pytest engine/extraction/tests/test_serper_extractor.py -v

# Create snapshot before change
python -m engine.extraction.run --source=serper --limit=10 --dry-run > snapshot_before.json

# Re-extract with new prompt
python -m engine.extraction.run --source=serper --limit=20 --force-retry

# Check quality
python -m engine.extraction.health
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-17
**Related Docs:**
- [Extraction Engine Overview](./extraction_engine_overview.md) - LLM extraction architecture
- [Adding a New Extractor](./adding_new_extractor.md) - Creating prompts for new sources
- [Troubleshooting Guide](./troubleshooting_extraction.md) - LLM errors and solutions
