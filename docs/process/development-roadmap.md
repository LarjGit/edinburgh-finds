# Development Roadmap

**Status:** Current Direction (replaceable at any time)  
**Last Updated:** 2026-02-11  

---

## R-01: Converge Repository to New Governance Model

### 1. Intent
Complete repository-wide alignment to the governance triad so that:
- Methodology governs execution (HOW)
- Roadmap defines direction (WHAT/WHY)
- Catalog functions as neutral work ledger (RECORD)

Eliminate all operational remnants of the legacy governance model.

### 2. Type
Infrastructure

### 3. Target Area
Repository documentation, navigation, prompts, comments, and governance terminology.

### 4. Scope Boundary
- Update all legacy document paths:
  - `docs/development-methodology.md` → `docs/process/development-methodology.md`
  - `docs/progress/audit-catalog.md` → `docs/progress/development-catalog.md`
- Remove operational use of “audit” terminology.
- Align CLAUDE.md navigation with the governance triad.
- Ensure catalog reads as neutral ledger (items + proofs only).
- May update broken references to golden docs, but not their contents.

### 5. Success Definition
- Zero operational references remain to:
  - `docs/development-methodology.md`
  - `docs/progress/audit-catalog.md`
  - “audit catalog” as an active governance object
- CLAUDE.md reflects the governance triad.
- All documentation links resolve.
- A new agent can start work without ambiguity.

### 6. Exclusions
- Changes to `docs/system-vision.md`
- Changes to `docs/target-architecture.md`
- Application/runtime behavior changes
- Re-auditing catalog items
- Altering catalog entry structure

### 7. Ordering / Dependencies
Must precede: All new feature work  
Blocked by: None  
Parallel-safe: No

### 8. Status
- [x] Planned  
- [x] In Progress  
- [x] Complete  

---

## R-02: Implement Data Connector Tier System

### 1. Intent
Establish a prioritized data acquisition strategy that maximizes data quality and coverage while minimizing operational complexity and cost. The system should enable Edinburgh Finds to operate with authoritative baseline data first, then layer in Edinburgh-specific enrichment, without premature optimization or connector sprawl.

### 2. Type
Infrastructure

### 3. Target Area
Data acquisition pipeline, connector integration capabilities.

### 4. Scope Boundary

**Tier 1 (Foundation - Needed for Launch):**
- Overture Maps: Edinburgh POI baseline with persistent GERS IDs, monthly refresh capability
- Companies House API: UK business verification and entity validation
- Firecrawl: Web scraping with LLM-ready markdown output (free tier: 500 credits)

**Tier 2 (Enrichment - Add Post-Launch):**
- TellMeScotland: Planning and licensing signals specific to Scotland
- Jina Reader: Supplementary web scraping (free tier: 10M tokens, 200 RPM)
- Wikidata Query Service: Entity linking and enrichment (QIDs as external references, not primary keys)

**Tier 3 (Conditional - Only If Gap Validated):**
- Define evaluation criteria for: Foursquare Places API, Yelp Fusion API, Eventbrite API
- Implement only after validating specific need against Tier 1+2 capabilities

**Tier 4 (Explicitly Rejected):**
- Document rationale for exclusion: TomTom, Mapbox, Meta APIs, Meetup, Reddit, Apify, ScrapingBee, Bright Data, Perplexity, Geoapify, Nominatim

**Out of Scope:**
- Changes to existing 6 connectors (Google Places, OSM, Sport Scotland, Edinburgh Council, Open Charge Map, Serper)
- Modifications to confidence grading methodology (A/B/C/X system)
- Venue data schema changes
- Frontend/UI changes
- Paid API tier usage (stay on free tiers for Tier 1 & 2)

### 5. Success Definition

- Edinburgh POI baseline dataset from Overture Maps is queryable
- All Tier 1 connectors are operational and producing data
- All Tier 2 connectors are operational and enriching venue records
- Tier system is documented with clear rationale for each tier placement
- Zero API costs incurred during Tier 1 & 2 implementation
- System can answer: "What data sources contributed to this venue record?"

### 6. Exclusions

- Implementation details (let methodology discover optimal approach)
- Specific module/file structure decisions
- Technical architecture choices
- How connectors integrate with existing pipeline
- Data transformation logic

### 7. Ordering / Dependencies

Must precede: Launch preparation, bulk venue population  
Blocked by: R-01 (governance convergence)  
Parallel-safe: No

**Logical ordering:**
1. Tier 1 connectors first (foundation cannot be skipped)
2. Tier 2 connectors after Tier 1 complete
3. Tier 3 evaluation only after product validation with Tier 1+2

### 8. Status

- [ ] Planned  
- [ ] In Progress  
- [ ] Complete  

**Milestones:**
- [ ] Tier 1 complete: Foundation connectors operational
- [ ] Tier 2 complete: Enrichment connectors operational
- [ ] Documentation: Tier system rationale captured
- [ ] Evaluation framework: Tier 3 promotion criteria defined