# Refactor Brief: Faceted Canonical Taxonomy + Entity Class Anchor + Module-Based Schemas

## Goal

Refactor the codebase so that:

1. **Entity classification** is represented by a single required field: `entity_class` (engine anchor for extraction/validation).
    
2. **Canonical taxonomy** is explicitly **faceted**: every canonical value belongs to exactly **one facet** (e.g., activity, place_type, access, listing_type).
    
3. Extraction/storage uses **reusable modules** (location/contact/hours/amenities/etc.) and avoids duplicating the same attribute across multiple “schemas.”
    
4. Mapping raw categories → canonical values still works, but canonical values now include facet membership + UI labels.
    
5. UI filtering/SEO pages are driven by **facets + values**, not implied hierarchy (“venue subtypes” etc.).
    

This is a “clean redesign” not a patch: remove conflation between “entity types as categories” and “entity type enum for extraction”.

---

## Non-negotiable modelling rules

Implement these invariants in code + config validation:

### R1 — Every canonical value belongs to exactly one facet

Example: `padel` is a value in facet `activity`.  
`gym` is a value in facet `place_type`.  
`membership` is a value in facet `access`.  
No value appears in two facets.

### R2 — `entity_class` is single-valued and required

Every entity/listing has exactly one `entity_class`.  
Recommended baseline classes: `place | person | organization | event | thing | concept`  
(You can start with the subset you need now; structure must allow future expansion.)

### R3 — Facets are for navigation/SEO, not for internal schema logic by default

Facet values are used for:

- filtering
    
- navigation groupings
    
- SEO page generation
    

Schema/module triggering is separate and explicit (see Manifest).

### R4 — Modules are reusable bundles of structured fields; modules must not duplicate fields

Example: `phone_number` exists only in module `contact`.  
If places and people need phones, they both include `contact`.

### R5 — Strong/Soft module attachment

- Strong trigger: `entity_class` → required modules
    
- Soft trigger: selected canonical values → optional additional modules  
    This mapping must be explicit in a manifest file.
    

---

## New/Updated configuration files

### 1) `engine/config/taxonomy.yaml` (replace current `canonical_categories.yaml` taxonomy section)

Create a new canonical taxonomy file with this structure:

- `facets`: defines facet keys, UI labels, sort/order, and whether facet is globally shown
    
- `values`: defines canonical value records including:
    
    - `key` (stable id used in storage; snake_case)
        
    - `facet` (which facet it belongs to)
        
    - `display_name` (UI label)
        
    - `description` (internal docs)
        
    - `search_keywords` (synonyms)
        

Example shape (illustrative):

`facets:   activity:     ui_label: "What do you want to do?"     order: 10     show_in_ui: true   place_type:     ui_label: "Place type"     order: 20     show_in_ui: true   access:     ui_label: "Booking & access"     order: 30     show_in_ui: false   # can be conditional in UI   listing_type:     ui_label: "Type"     order: 5     show_in_ui: true  values:   - key: padel     facet: activity     display_name: "Padel"     description: "Padel courts and facilities"     search_keywords: ["padel", "pádel", "paddle tennis", "padel court"]    - key: gym     facet: place_type     display_name: "Gym"     description: "Fitness facilities"     search_keywords: ["gym", "fitness", "health club", "gymnasium"]    - key: membership     facet: access     display_name: "Membership"     description: "Membership required"     search_keywords: ["members only", "membership", "private club"]    - key: coach     facet: listing_type     display_name: "Coach"     description: "Individual or organisation providing coaching services"     search_keywords: ["coach", "instructor", "trainer", "lessons"]`

**Important:** Values such as `venue`, `retail`, `coach`, `club`, `event` must be treated as **listing_type facet values** (UI concept), not as the engine’s schema anchor. The engine anchor is `entity_class` (R2).

### 2) `engine/config/mapping_rules.yaml`

Move/keep mapping rules separate from taxonomy definitions. Keep your current `mapping_rules` logic but:

- mapping target should now be a canonical `values.key`
    
- ensure mapped keys exist in taxonomy values
    

### 3) `engine/config/entity_model.yaml`

Define `entity_class` and required base modules per class.

Example:

`entity_classes:   place:     required_modules: ["core", "location"]   person:     required_modules: ["core", "contact"]   organization:     required_modules: ["core", "contact"]   event:     required_modules: ["core", "time_range"]`

### 4) `engine/config/module_manifest.yaml`

Define soft triggers from canonical values to modules.

Example:

`value_triggers:   padel:     add_modules: ["sports_facility"]   gym:     add_modules: ["hours", "amenities"]   cafe:     add_modules: ["hours", "amenities", "hospitality"]`

Also define “facet-level triggers” only if needed (generally avoid unless truly universal).

---

## Data model changes (code + storage)

Update the listing/entity model so it has:

- `entity_class: str` (required, single)
    
- `canonical_values: list[str]` (flat list of canonical value keys)
    
- `canonical_facets: optional derived structure` (either computed at runtime or stored; prefer computed)
    
- `raw_categories: list[str]` unchanged (provenance)
    
- `modules: dict[module_name, module_payload]` (structured extracted data per module)
    

**Do NOT** store namespaced strings like `act:padel`. Store `padel` and attach facet metadata via taxonomy.

---

## Refactor tasks (explicit steps)

### Task 1 — Introduce new taxonomy loader + validators

Implement `taxonomy_loader.py` that loads `taxonomy.yaml` and provides:

- `get_facets()`
    
- `get_values()`
    
- `value_exists(key) -> bool`
    
- `facet_for_value(key) -> facet_key`
    
- `ui_label_for_facet(facet_key)`
    
- `ui_label_for_value(key)`
    
- Validation: every value has exactly one facet; no duplicate keys; all facets referenced exist.
    

### Task 2 — Split mapping rules into its own module and validate mappings

Implement/modify `category_mapper.py` to:

- load `mapping_rules.yaml`
    
- map raw strings to canonical value keys
    
- apply confidence threshold
    
- validate that mapped canonical keys exist in taxonomy
    

### Task 3 — Add `entity_class` resolution

Create a deterministic step `resolve_entity_class()` that outputs one of the allowed entity classes.  
Initial approach can be simple:

- If existing system has `entity_type` enum, map it to new `entity_class`:
    
    - VENUE/PLACE-like → place
        
    - COACH/PERSON-like → person (or organization if it’s an academy)
        
    - RETAIL → organization or place depending on whether physical location exists; pick one consistent rule
        
    - CLUB → organization
        
    - EVENT → event
        

Make this mapping explicit and testable (no hidden heuristics unless necessary).

### Task 4 — Implement modules framework

Create `engine/modules/` with module schemas (field definitions + validators).  
Start with minimal set:

- `core` (id, name, slug, updated_at)
    
- `location` (address, lat, lng, locality)
    
- `contact` (phone, email, website, socials)
    
- `hours` (opening hours structure)
    
- `amenities` (wifi, parking, toilets)  
    Optional domain modules (only if needed now):
    
- `sports_facility` (court_count, pitch_count, surfaces) — keep it generic, not sport-specific unless required.
    

### Task 5 — Implement module selection logic (strong/soft triggers)

Implement `compute_required_modules(entity_class, canonical_values)`:

- Start with required modules from `entity_model.yaml` for entity_class
    
- Add modules from `module_manifest.yaml` for each canonical value present
    
- Return final ordered unique list
    

### Task 6 — Refactor extraction pipeline to run module extractors

Change extraction flow to:

1. collect raw categories
    
2. map to canonical values
    
3. resolve entity_class
    
4. compute modules
    
5. run extractors per module and validate payload
    
6. store into `modules[module_name] = payload`
    

### Task 7 — Remove “venue subtypes” semantics everywhere

- Remove any references implying hierarchy between canonical categories.
    
- Delete/replace section headers in old canonical YAML.
    
- Ensure the code never assumes “gym implies venue” etc.
    

### Task 8 — Refactor UI/filter/SEO code to facet-driven display

If you have UI config generation:

- Render filters grouped by taxonomy facets and facet `order`.
    
- Show facet UI labels from config, not hardcoded.
    
- Implement “conditional facet display”: hide a facet if it has <2 values present in current result set.
    

### Task 9 — Backward compatibility strategy (if needed)

If there is existing data stored as `canonical_categories`, migrate it to `canonical_values` (same strings).  
If there is existing `entity_type`, map to `entity_class`.  
Provide a migration script with idempotent behavior.

### Task 10 — Tests

Add tests to enforce invariants:

- Taxonomy validation tests
    
- Mapping rules → canonical values exist
    
- entity_class required and from allowed set
    
- module selection outputs correct modules for known examples
    
- no duplicate field definitions across modules (at least detect collisions in module schema registry)
    
- end-to-end sample entities (place+padel+gym etc.)
    

---

## Concrete classification decisions to encode now (so Claude doesn’t guess)

### Facets to implement for this directory vertical

Implement these facet keys (can expand later):

- `activity`
    
- `place_type`
    
- `access`
    
- `listing_type`
    

### Move your current keys into facets like this

- `activity`: padel, tennis, squash, badminton, pickleball, table_tennis, golf, climbing, yoga, martial_arts
    
- `place_type`: sports_centre, gym, swimming_pool, outdoor_pitch
    
- `access`: private_club, public_facility (or rename to membership/open_to_public; decide and apply consistently)
    
- `listing_type`: venue, retail, coach, club, event (UI types)
    

### Engine anchor

Implement `entity_class` separately from `listing_type`.  
For now map:

- listing_type venue → entity_class place
    
- listing_type retail → entity_class organization (or place if you want physical shops; pick one)
    
- listing_type coach → entity_class person (or organization for academies; define rule)
    
- listing_type club → entity_class organization
    
- listing_type event → entity_class event
    

**Do not** rely on category keys to be schema triggers; use entity_class + module manifest.

---

## Acceptance criteria (definition of done)

Claude must ensure:

1. `taxonomy.yaml` exists with facets + values; loader validates invariants.
    
2. `mapping_rules.yaml` maps raw → canonical value keys; mapper validates existence.
    
3. Every listing/entity has `entity_class` (required) + `canonical_values` list.
    
4. Module framework exists; modules are selected via `entity_model.yaml` + `module_manifest.yaml`.
    
5. Extraction pipeline populates `modules` dict with validated payloads.
    
6. UI filtering uses facets + UI labels from taxonomy; no hardcoded facet names.
    
7. No code references “venue subtypes” or hierarchical category assumptions.
    
8. Tests cover taxonomy validation, mapping, module selection, and at least one end-to-end extraction example.