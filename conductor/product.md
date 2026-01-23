# PRD (summary for AI context)

## 1. Core Mission & USP

Mission: To build the premier hyper-local, niche-focused discovery platform, starting with Padel in Edinburgh.

USP: "AI-Scale, Local Soul" — Using LLMs to autonomously source, ingest, and structure data at scale, while delivering a "locally curated" UX that feels like advice from a knowledgeable friend.

## 2. The Universal Entity Framework (Architecture)

The system uses a "Flexible Attribute Bucket" strategy to support **any** niche via a generic, scalable structure (see `/ARCHITECTURE.md`):

- **Classification:** A universal `entity_class` (place, person, organization, event, thing).
- **Dimensions:** Multi-valued arrays (`canonical_activities`, `canonical_roles`, `canonical_place_types`, `canonical_access`) stored as Postgres arrays.
- **Attributes:** Vertical-specific data is stored in flexible JSON `modules` (e.g., `sports_facility`, `wine_production`) managed by Lenses.
- **Lenses:** A YAML-configured layer that interprets the universal data for specific verticals (e.g., Padel, Wine), deriving navigation, facets, and display rules without engine code changes.
- **Ecosystem Graph:** Relationships (e.g., "teaches_at", "plays_at") connecting entities to map the local community.

## 3. Data Ingestion & Extraction Engine

The platform relies on an autonomous Python-based ETL pipeline:

- **Ingestion:** Connectors fetch raw data from diverse sources (Google Places, Serper, OSM, etc.) and store it as `RawIngestion` records.
- **Extraction:** A hybrid engine uses:
    - **Deterministic rules** for structured APIs (Google, SportScotland).
    - **LLM-based extraction** (Instructor + Claude) for unstructured data (Search snippets, OSM tags).
- **Deduplication:** A multi-stage process (External ID -> Slug -> Fuzzy Match) to prevent duplicates.
- **Trust:** Field-level trust scoring ensures "Golden Data" (Admin/Official) overrides crowdsourced data.

## 4. The Target Audience

- **Enthusiasts:** Beginners (where to start?), Active players (how to improve?), and Problem-Solvers (where is available?).
- **Business Owners:** Seeking high-intent leads and visibility. The platform is a **marketing channel**, not a booking engine.

## 5. Content & Quality Standards

- **Voice:** "The Knowledgeable Local Friend." Content must include geographic context (neighborhoods) and practical quirks.
- **Forbidden:** Marketing fluff, vague superlatives, and generic AI-sounding summaries.
- **Trust Architecture:** Tiered confidence system. **Business-claimed data** is the gold standard. We prioritize _credibility over completeness_.

## 6. Growth & Monetization Logic

- **Phase 1 (Growth):** Free listings, SEO-first (Programmatic Long-Tail), and community trust.
- **Phase 2 (Revenue):** Transition to a Freemium model (Premium listings, analytics, and featured placement).
- **Non-Goals:** No payment processing or real-time booking integrations for the MVP.