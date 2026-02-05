# Entity Classification Rules

## Purpose

This document defines the **deterministic algorithm** for classifying entities in the Edinburgh Finds engine. The classification system separates **what an entity fundamentally IS** (entity_class) from **what it DOES** (roles).

## Core Rules

### Rule 1: Single entity_class (Required)

Every entity has **exactly ONE** `entity_class` value. This is a required, single-valued field that represents the entity's primary classification.

**Valid entity_class values:**
- `place` - Physical location with coordinates or street address
- `person` - Named individual
- `organization` - Group, business, or membership entity
- `event` - Time-bounded occurrence with start/end times
- `thing` - Generic entity (fallback)

### Rule 2: Multiple roles (Optional)

Every entity has **ZERO OR MORE** `canonical_roles` values. This is an optional, multi-valued field stored as a Postgres text[] array that represents the entity's functions and capabilities.

**Pattern:**
- `entity_class` = what it fundamentally IS (primary classification)
- `canonical_roles` = what it DOES (functions/capabilities)

## Deterministic Classification Algorithm

The classification algorithm follows a **strict priority order**. Each condition is evaluated in sequence, and the first matching condition determines the entity_class:

### Priority Order (Highest to Lowest)

1. **Time-bounded** (has start/end times) → `event` (HIGHEST PRIORITY)
2. **Physical location** (lat/lng or street address) → `place`
3. **Membership/group** entity with no fixed location → `organization`
4. **Named individual** → `person`
5. **Tie-breaker**: Primary physical site → `place`, otherwise → `organization`

### Implementation Logic

```python
def resolve_entity_class(raw_data):
    """
    Resolve entity_class using deterministic priority algorithm.

    Priority (highest first):
    1. Time-bounded → event
    2. Physical location → place
    3. Membership/group → organization
    4. Named individual → person
    5. Fallback → thing
    """

    # Priority 1: Time-bounded
    if has_time_bounds(raw_data):
        return 'event'

    # Priority 2: Physical location
    if has_location(raw_data):
        return 'place'

    # Priority 3: Membership/group → organization
    if is_organization_like(raw_data):
        return 'organization'

    # Priority 4: Named individual → person
    if is_individual(raw_data):
        return 'person'

    # Fallback
    return 'thing'
```

## Concrete Examples

### Example 1: Padel tournament at Oriam

**Scenario:** A padel tournament happening at a physical venue.

**Raw attributes:**
- Name: "Padel tournament at Oriam"
- Start time: 2024-06-10T10:00:00Z
- End time: 2024-06-10T18:00:00Z
- Location: Oriam Sports Centre
- Address: Heriot-Watt University, Edinburgh
- Activities: padel

**Classification:**
- `entity_class`: `event` (time-bounded takes PRIORITY over physical location)
- `canonical_roles`: `[]` (events typically have no roles)
- `canonical_activities`: `["padel"]`

**Rationale:** Has both start/end times AND physical location, but time-bounded is higher priority in the algorithm.

---

### Example 2: Tennis club with 6 courts

**Scenario:** A tennis club with physical courts and membership requirements.

**Raw attributes:**
- Name: "Craigmillar Tennis Club"
- Address: 123 Tennis Road
- Coordinates: (55.9, -3.1)
- Has courts: Yes
- Membership required: Yes
- Activities: tennis

**Classification:**
- `entity_class`: `place` (has physical location with courts, not time-bounded)
- `canonical_roles`: `["provides_facility", "membership_org"]` (provides sports facility AND is a membership club)
- `canonical_activities`: `["tennis"]`
- `canonical_place_types`: `["sports_centre"]`

**Rationale:** Primary classification is physical place. Roles capture dual nature as both facility provider and membership organization. Court inventory goes in `sports_facility` module (domain-specific), not in place_type values.

---

### Example 3: Powerleague Portobello (multi-sport venue)

**Scenario:** A venue offering both football and padel facilities.

**Raw attributes:**
- Name: "Powerleague Portobello"
- Address: Portobello, Edinburgh
- Activities: football, padel
- Has pitches: Yes
- Has courts: Yes

**Classification:**
- `entity_class`: `place` (has physical location)
- `canonical_activities`: `["football", "padel"]` (multiple activities stored in array)
- `canonical_roles`: `["provides_facility"]` (plus others if applicable)
- `canonical_place_types`: `["sports_centre"]` or `["outdoor_facility"]`

**Note:** Courts and pitches go into `sports_facility.inventory` (domain module in lens layer), not as `place_type` values.

---

### Example 4: Freelance tennis coach

**Scenario:** An individual providing tennis coaching services.

**Raw attributes:**
- Name: "Sarah Wilson"
- Type: coach
- Activities: tennis
- No fixed location

**Classification:**
- `entity_class`: `person` (individual, no fixed location)
- `canonical_roles`: `["provides_instruction"]`
- `canonical_activities`: `["tennis"]`

**Rationale:** Named individual with no fixed physical location or time-bounded existence, so classified as 'person'. Role captures instruction-providing function.

---

### Example 5: Sports retail chain

**Scenario:** A retail business selling sports equipment but not operating any courts.

**Raw attributes:**
- Name: "Sports Direct"
- Type: retailer
- Activities: tennis, padel (sells equipment for these sports)
- No courts/facilities

**Classification:**
- `entity_class`: `organization` (business entity without fixed location)
- `canonical_roles`: `["sells_goods"]`
- `canonical_activities`: `["tennis", "padel"]`

**Rationale:** Business entity with no courts/facilities and no single fixed location (chain), so classified as 'organization'. Role captures goods-selling function.

---

### Example 6: Padel tournament (standalone event)

**Scenario:** A competitive tournament with specific dates.

**Raw attributes:**
- Name: "Edinburgh Padel Open 2024"
- Start time: 2024-05-15T09:00:00Z
- End time: 2024-05-17T18:00:00Z
- Location: Oriam (reference to venue)
- Activities: padel

**Classification:**
- `entity_class`: `event` (time-bounded)
- `canonical_roles`: `[]` (events typically have no roles)
- `canonical_activities`: `["padel"]`

**Rationale:** Time-bounded entity (has start/end times), so classified as 'event' even if it has a physical location. Events typically have no roles.

---

## Anti-Patterns (What NOT to Do)

### ❌ NEVER use entity_class to encode business type

**WRONG:**
```python
entity_class = "club"  # ❌ "club" is NOT a valid entity_class
```

**CORRECT:**
```python
entity_class = "place"
canonical_roles = ["provides_facility", "membership_org"]
```

**Why:** Business type is captured in roles, not entity_class. The entity_class should reflect the fundamental nature of the entity (physical place, person, organization, event, thing).

---

### ❌ NEVER use roles as primary classification

**WRONG:**
```python
# Treating role as primary classification
entity_class = "instructor"  # ❌ roles should not be used as entity_class
```

**CORRECT:**
```python
entity_class = "person"  # or "organization" if coaching business
canonical_roles = ["provides_instruction"]
```

**Why:** `entity_class` is the primary classification. Roles are supplementary functions/capabilities.

---

### ❌ NEVER store conflicting entity_class values

**WRONG:**
```python
# Attempting to assign multiple entity_class values
entity_class = ["place", "organization"]  # ❌ entity_class is single-valued
```

**CORRECT:**
```python
entity_class = "place"  # Primary classification
canonical_roles = ["provides_facility", "membership_org"]  # Capture dual nature in roles
```

**Why:** `entity_class` is a single-valued field. If an entity has multiple aspects, use a single `entity_class` for primary classification and capture additional aspects in `canonical_roles`.

---

## Validation Rules

All implementations must enforce these validation rules:

1. **entity_class must be one of:** place, person, organization, event, thing
2. **entity_class is required:** Every entity must have exactly one entity_class value
3. **entity_class is immutable:** Once set, entity_class should not change (indicates fundamental misclassification)
4. **canonical_roles is optional:** An entity can have zero roles
5. **canonical_roles is multi-valued:** Stored as Postgres text[] array

## Implementation Requirements

1. **Reference this document:** Add inline comments in `entity_classifier.py` referencing this document
2. **Assertion checks:** Add assertion to verify entity_class is one of the 5 valid values
3. **Deterministic logic:** Classification must be deterministic - same input always produces same output
4. **Priority-based:** Follow the priority order strictly - time-bounded → location → individual → organization

## Related Documentation

- `engine/config/entity_model.yaml` - Universal entity model definition
- `engine/docs/id_strategy.md` - ID strategy documentation
- `lenses/edinburgh_finds/lens.yaml` - Lens-specific facet definitions and role values

---

**Last Updated:** 2026-01-18
**Version:** 1.0
