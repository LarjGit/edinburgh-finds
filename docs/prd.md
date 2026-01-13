# Product Requirements Document (PRD)

## 1. Executive Summary

Edinburgh Finds (edinburghfinds.co.uk) is a scalable, AI‑driven local discovery platform designed to map and maintain the **long tail of hobbies, interests, and niche activities** within a city. The product addresses the persistent failure of traditional directories: stale data, shallow coverage, and poor local relevance.

The platform will launch with a **Vertical MVP focused on Padel in Edinburgh**, using this constrained domain to validate the core system hypothesis:

> *That AI‑assisted ingestion and maintenance can sustainably power a high‑quality, deeply local directory at scale.*

Once proven, the same blueprint will be replicated horizontally across additional niches and vertically across new geographies.

---

## 2. Product Vision

To become the **digital heartbeat of local communities whatever their interests are**.

Edinburgh Finds connects enthusiasts with the *entire ecosystem* surrounding their interest — for example venues, retailers, coaches, clubs, and events — while simultaneously providing local businesses with a **high‑intent discovery and lead channel**.

The platform is not a marketplace or a booking engine. Its core value is **clarity, completeness, and trust** in fragmented local information.

---

## 3. Product Scope & Non‑Goals (MVP)

### In Scope

* Discovery and aggregation of local interests and hobby ecosystems
* Structured representation of entities and their relationships
* SEO‑first content and landing pages
* Lead routing and intent capture (e.g. enquiries, outbound clicks)

### Explicit Non‑Goals (MVP)

* Payments or transaction processing
* Real‑time availability or booking calendars
* Peer‑to‑peer messaging
* Social‑network style feeds or moderation‑heavy community features

These exclusions are intentional to preserve focus on the platform's core competency: **authoritative discovery at scale**.

---

## 4. User Journeys

Understanding who uses Edinburgh Finds and why they come shapes every product decision. The platform serves three primary user journeys:

### Journey 1: The Complete Beginner
**Context**: "I just moved to Edinburgh and want to try padel – where do I start?"

**Needs**:
* What is padel and is it for me?
* Which venues welcome beginners?
* Do I need my own equipment or can I hire?
* Are there coaches who can teach me the basics?

**Success**: User discovers a beginner-friendly venue, understands what to expect, and takes action (visits, books, or enquires).

### Journey 2: The Active Participant
**Context**: "I've been playing for 6 months – where can I find better competition?"

**Needs**:
* Which clubs run regular social sessions or leagues?
* Are there coaches who focus on intermediate technique?
* What's the standard at different venues?
* When are the upcoming tournaments or events?

**Success**: User finds pathways to improve and connects with the local community at their skill level.

### Journey 3: The Practical Problem-Solver
**Context**: "My usual venue is fully booked – what are my alternatives?"

**Needs**:
* Which other venues are nearby with similar facilities?
* What are their peak times and typical availability?
* Are there outdoor options if weather permits?
* Can I see all Edinburgh venues on a map?

**Success**: User discovers a suitable alternative and successfully books or visits.

### Journey 4: Business User Journey
**Context**: "We run a padel venue/coaching service – how do we get found?"

**Needs**:
* Is our business accurately represented?
* Can we update our details when things change?
* Are people actually finding us through the platform?
* How do we stand out from competitors?

**Success**: Business claims their profile, maintains accurate information, and receives qualified enquiries.

---

## 5. Launch Strategy: The Edinburgh Pilot

### Local‑First Identity

Launching on edinburghfinds.co.uk establishes immediate geographic relevance, trust, and search intent alignment.

### Geographic Constraint

Initial coverage is restricted to **Edinburgh & the Lothians**, ensuring high data density and manageable validation during the MVP phase.

### Vertical Focus: Padel

Padel is selected as the pilot vertical due to:

* Rapid local growth
* Clear ecosystem boundaries
* Manageable entity count (~8-12 venues, ~15-20 coaches, handful of retailers and clubs)

The objective is to exhaustively map the local Padel ecosystem (e.g. Powerleague Portobello, Thistle Padel, specialist retailers) and become the **canonical online resource** for the sport in the city.

### Scalability Path

Once the Padel blueprint is validated, the system will:

1. Expand horizontally to other niches (e.g. Golf, Wild Swimming, Climbing)
2. Expand geographically to additional UK cities (Glasgow, Manchester, Bristol)

---

## 6. Unique Selling Proposition: "AI‑Scale, Local Soul"

Traditional directories fail due to the **Maintenance Paradox**: comprehensive coverage requires constant updates, but manual maintenance does not scale.

Edinburgh Finds resolves this through a hybrid model:

* **Autonomous Ingestion** – AI systems continuously discover, extract, and structure local data from across the web.
* **Curated Output** – AI‑generated summaries and insights are tuned to feel like guidance from a knowledgeable local expert.

The result is a platform that scales like software but *feels* human and local.

---

## 7. Core Conceptual Model: The Universal Entity Framework

Every hobby or interest is treated as an ecosystem composed of various universal entity pillars, for example:

1. **Infrastructure** – Venues and physical spaces
2. **Commerce** – Retailers, hire services, pro‑shops
3. **Guidance** – Coaches, tutors, instructors
4. **Organization** – Clubs, teams, social groups
5. **Momentum** – Events, tournaments, meetups, clinics

This niche‑agnostic model allows the platform to scale horizontally without redefining its core structure.

---

## 8. Data Quality & Trust Architecture

Data quality and trust are foundational to the product's value. The platform employs a **tiered confidence system** with explicit conflict resolution rules.

### Cold-Start Data Strategy

Before businesses engage with the platform, initial credibility is established through:

1. **Manual verification of core entities** – All primary venues (8-12 for Padel) are manually researched and verified pre-launch
2. **Transparent confidence scoring** – Each entity page displays last verification date and data source
3. **Clear claiming status** – Unclaimed listings are explicitly labeled: "This business hasn't claimed their profile yet"
4. **Conservative presentation** – Only high-confidence data points are displayed; uncertain information is omitted rather than presented with caveats

### Data Conflict Resolution Hierarchy

When multiple sources provide conflicting information, the system follows this priority order:

1. **Business-claimed data** (highest confidence) – Direct updates from verified business owners
2. **AI-detected changes** (high confidence) – Automated detection of website updates, official announcements
3. **Community reports** (medium confidence) – User-submitted corrections, flagged for manual review
4. **Baseline scraped data** (low confidence) – Initial automated extraction, displayed only if no higher-confidence source exists

### Special Case: Critical Status Changes

For business-critical updates (closures, relocations, major facility changes):

* Community reports trigger immediate review rather than waiting for scheduled updates
* Potentially outdated listings show a banner: "We're verifying recent reports about this venue"
* Multiple independent community reports escalate confidence and may trigger immediate status changes

### Freshness Expectations by Entity Type

Every entity carries an implicit **freshness expectation** based on its type, for example:

* **Venues**: Quarterly verification (facilities change slowly)
* **Coaches**: Monthly verification (availability and pricing change more frequently)
* **Events**: Real-time (time-sensitive by nature)
* **Retailers**: Bi-monthly verification (stock and hours change moderately)
* **Clubs**: Quarterly verification (membership details relatively stable)

The system prioritizes *credibility over completeness* when conflicts arise.

---

## 9. Content Quality Standards: Defining "Local Soul"

AI-generated content must meet a high bar to feel genuinely local and expert-driven. This requires explicit quality standards, not just the aspiration of "sounding local."

### The Voice: Knowledgeable Local Friend

Content should read as if written by someone who:
* Lives in Edinburgh and knows the city intimately
* Has actually visited or engaged with the entities they're describing
* Understands the practical realities of the hobby (weather, timing, local customs)
* Offers genuine insight, not generic promotional copy

### Content Quality Examples

**❌ Generic AI (Fails the bar)**
> "Powerleague Portobello is a popular padel venue located in Edinburgh. It offers indoor and outdoor courts with modern facilities. The venue is suitable for players of all skill levels."

**✅ Local Soul (Meets the bar)**
> "Powerleague Portobello sits right by the beach – bring layers, because the sea breeze is real even on the indoor courts. The facility's split between 3 indoor and 2 outdoor courts means you've usually got options, though the outdoor courts are weather-dependent (and let's be honest, that's most of the year in Edinburgh)."

### Mandatory Content Elements

Every venue description must include:

1. **Geographic context** – Neighborhood, landmarks, transport links
2. **Practical insight** – Parking, typical busy times, local quirks
3. **Skill-level guidance** – Who this venue serves best
4. **Distinctive details** – What makes this venue different from alternatives

### Forbidden Patterns

Content must never include:

* Vague superlatives ("amazing," "incredible," "fantastic") without supporting detail
* Promotional language that sounds like marketing copy
* Claims about quality or popularity without basis in observable fact

### Quality Assurance Process

* **Pre-launch**: All venue summaries manually reviewed and rewritten if necessary
* **Ongoing**: Monthly sampling of 20% of AI-generated content for quality drift
* **User feedback**: "Was this description helpful?" feedback mechanism on every entity page

---

## 10. Programmatic SEO & Search Strategy

Edinburgh Finds is designed as an **SEO‑generating system**, not a static content site.

### Long‑Tail Capture

Automated creation of high‑intent, hyper‑local pages such as:

* "Padel Coaches in Leith"
* "Indoor Padel Courts in Morningside"
* "Where to Buy Padel Equipment in Edinburgh"
* "Padel Clubs Near Haymarket"

### Domain Authority

The geographic domain reinforces relevance and supports topical authority within local search results.

### Internal Linking Web

Entities are programmatically cross‑linked (e.g. coach → venue → event), improving crawlability and reinforcing topical clusters.

### Realistic SEO Timeline

* **Months 1-3**: Indexing and baseline visibility
* **Months 4-6**: Long-tail keywords begin ranking
* **Months 7-12**: Competitive keywords gain traction
* **Year 2+**: Domain authority compounds, top-funnel queries rank

SEO is a long game. Early traffic will come from other channels.

---

## 11. Year 1 Distribution Strategy

SEO takes 6-12 months to deliver meaningful traffic. The platform needs early adopters and validation before organic search pays off.

### Direct Community Engagement (Months 1-2)

* **Facebook Groups**: Direct outreach to Edinburgh padel community groups with "We built this for you" positioning
* **WhatsApp Communities**: Partner with existing player groups to share the resource
* **Venue Partnerships**: Approach 2-3 friendly venues to embed the directory on their website ("Find other Edinburgh venues")

### Influencer & Ambassador Seeding (Months 2-4)

* Identify 5-10 active local players/coaches with social presence
* Provide early access and invite feedback
* Create shareable "ultimate guide" content they can distribute

### Small Paid Experiments (Months 3-6)

* Google Ads for "padel Edinburgh" and variants (budget: £200-300/month)
* Purpose: Validate search intent and keyword conversion, not scale
* Facebook/Instagram ads targeting Edinburgh users interested in racquet sports

### PR & Content Hooks (Months 4-8)

* Pitch local Edinburgh media: "New platform maps city's padel boom"
* Create newsworthy content: "Edinburgh's padel scene grew 200% in 2024" (data-driven)
* Approach hobby bloggers and lifestyle writers

### Success Metrics for Distribution

* 500 unique visitors in Month 1 (pre-SEO)
* 20+ business enquiries generated
* 5+ venues claiming profiles
* 50+ email subscribers for updates

---

## 12. Content & Authority Strategy: The AI Content Hub

Beyond listings, the platform establishes authority through (mostly AI generated) supportive content:

* **Educational Primers** – Beginner guides and equipment explainers
* **Local Roundups** – City‑specific insights and trends
* **Dynamic Updates** – AI‑detected local news, openings, and deadlines

All content adopts a consistent **Edinburgh‑centric voice** to reinforce brand identity and local authenticity.

Example content pieces for Padel vertical:

* "Complete Beginner's Guide to Padel in Edinburgh"
* "Indoor vs Outdoor Padel: What to Expect in Edinburgh Weather"
* "The 5 Best Padel Retailers in Edinburgh (And What They Stock)"

---

## 13. MVP Feature Prioritization

Features are built in phases to validate the core loop quickly while managing scope.

### Phase 1: Launch-Critical (Weeks 1-8)

**Must-have for launch**:

1. **Static venue pages** with AI-generated summaries meeting quality bar
2. **Basic search/filter** by location and entity type (venues, coaches, retailers)
3. **Google Maps integration** for venue discovery
4. **Business claiming portal** (manual approval workflow initially)
5. **Contact/enquiry capture** for lead generation validation

**Success criteria**: Can a user find what they need? Can a business claim their listing?

### Phase 2: Post-Launch Validation (Weeks 9-16)

**Add after core loop is proven**:

1. **User reviews and ratings** (simple 5-star + text)
2. **Enhanced filtering** (indoor/outdoor, beginner-friendly, price range)
3. **Email notifications** for businesses when users enquire
4. **Basic analytics dashboard** for claimed businesses (views, clicks, enquiries)

**Success criteria**: Are users engaging beyond initial discovery? Are businesses seeing value?

### Phase 3: Authority Building (Months 5-8)

**Add after initial traction**:

1. **Dynamic content hub** with guides and local insights
2. **Event calendar** with automated ingestion
3. **Advanced search** with multi-faceted filtering
4. **Comparison tools** (compare venues side-by-side)

**Success criteria**: Is the platform becoming a destination, not just a lookup tool?

### Explicitly Deferred (Post-MVP)

* Booking integration
* Payment processing
* Mobile app
* User accounts and profiles
* Social features (beyond reviews)

---

## 14. Monetization Roadmap

### Phase 1: Growth (Year 1)

* Free listings to maximise coverage and SEO dominance
* Focus on data quality and user trust
* Validate lead generation value for businesses

### Phase 2: Lead Generation (Year 2)

* **Freemium model** introduced:
  * Free: Basic listing, appears in search
  * Premium (£29-49/month): Enhanced visibility, analytics, priority placement
* Revenue from:
  * Pay-per-click on outbound links
  * Enquiry form submissions (£2-5 per qualified lead)
  * Featured placement in search results

### Phase 3: Premium Tools (Year 3+)

* Subscriptions for verified badges, enhanced visibility, and analytics
* Business tools: Review response, competitor insights, customer CRM
* API access for third-party integrations

### Strategic Direction: Passive vs Active Facilitation

**Initial positioning: Passive monetization** (media play)
* Platform remains neutral discovery layer
* Revenue from attention and lead routing
* Lower operational complexity
* Easier to scale horizontally across niches

**Potential evolution: Active facilitation** (SaaS platform)
* Embedded booking, CRM tools, business intelligence
* Deeper business relationships and higher LTV
* Requires significant product investment
* May limit horizontal scaling speed

Decision point: After Year 1, evaluate based on business engagement and unit economics.

Monetization is layered **after trust and authority are established**, not before.

---

## 15. Risks & Mitigation Strategies

### Risk 1: AI Content Quality Deterioration

**Risk**: Google penalizes AI-generated content as low-quality, or users perceive descriptions as generic and unhelpful.

**Likelihood**: Medium | **Impact**: Critical

**Mitigation**:
* Human review of all venue summaries pre-launch (100% coverage for MVP)
* Ongoing quality sampling: 20% monthly audit of AI-generated content
* User feedback mechanism: "Was this helpful?" on every entity page
* Quality metrics dashboard tracking user engagement by content type
* Editorial guidelines strictly enforced with AI content generation prompts

### Risk 2: Padel Ecosystem Too Small for Validation

**Risk**: The Edinburgh padel vertical has insufficient entity volume or complexity to prove the AI maintenance model scales.

**Likelihood**: Low | **Impact**: High

**Mitigation**:
* Define explicit success threshold: "If we can maintain <15 entities with <3 hours/week manual effort, model works"
* Track time spent on data maintenance from Week 1
* Have backup vertical ready (Tennis: 40+ venues in Edinburgh) if Padel proves too small
* The real test is automation efficiency, not absolute entity count

### Risk 3: Businesses Don't Engage or See Value

**Risk**: Business owners ignore claiming invitations and don't perceive the platform as valuable.

**Likelihood**: Medium | **Impact**: High

**Mitigation**:
* Include basic analytics in free tier: "Your venue was viewed 247 times last month"
* Proactive outreach: Personal emails to venue managers with traffic data after Month 2
* Showcase early wins: Case study from first engaged business
* Reduce friction: 5-minute claiming process, instant approval for contact detail updates
* Demonstrate value before asking: 3 months free traffic before introducing premium tiers

### Risk 4: Data Freshness Cannot Be Maintained

**Risk**: Automated systems fail to detect changes; directory becomes stale despite AI assistance.

**Likelihood**: Medium | **Impact**: Critical

**Mitigation**:
* Manual fallback: Quarterly human verification of all core entities (acceptable at MVP scale)
* Community reporting incentives: Public acknowledgment for helpful corrections
* Business self-interest: Claimed profiles are self-maintaining
* Monitoring dashboard: Automated alerts when entities haven't been verified within expected timeframe
* Accept imperfection: Better to be 90% accurate with transparent confidence scoring than claim 100%

### Risk 5: SEO Takes Too Long; Traffic Doesn't Materialize

**Risk**: Organic search is slower than expected; platform lacks users to validate business value.

**Likelihood**: Medium | **Impact**: High

**Mitigation**:
* Multi-channel distribution strategy (see Section 11) doesn't rely on SEO for Year 1
* Paid search experiments validate demand and intent early
* Partnership traffic (venue websites, club newsletters) provides baseline while SEO builds
* Realistic timeline: Position Year 1 as "building authority," Year 2 as "harvesting traffic"

### Risk 6: Horizontal Scaling Breaks the Model

**Risk**: What works for Padel doesn't generalize to other niches (different data structures, maintenance needs, or business models).

**Likelihood**: Low-Medium | **Impact**: High

**Mitigation**:
* Universal entity framework (Section 7) designed for niche-agnosticism
* Second vertical (Tennis or Climbing) added in Month 9-12 as proof of scalability
* Document "porting process" with first expansion: time required, customizations needed
* Accept that some niches may not fit: better to know early than scale prematurely

---

## 16. Success Definition (MVP)

The MVP is considered successful if Edinburgh Finds achieves:

### Quantitative Benchmarks (6 months post-launch)

* **Coverage**: 100% of Edinburgh padel venues mapped (target: 8-12 entities)
* **Traffic**: 1,000+ organic monthly visitors
* **Engagement**: 50+ business enquiries generated
* **Claims**: 40%+ of venues have claimed profiles
* **Efficiency**: <5 hours/week maintenance time for full padel vertical

### Qualitative Validation

* Users describe the platform as "the go-to resource for Edinburgh padel"
* Businesses report qualified leads and traffic value
* Local community (Facebook groups, clubs) references and links to Edinburgh Finds
* Venue managers ask "When are you adding [other hobby]?"

### Strategic Validation

This validates the system's ability to:
1. Scale AI maintenance model beyond initial niche
2. Generate organic search traffic for long-tail local queries
3. Provide genuine value to both users and businesses
4. Justify horizontal expansion to additional niches

If these criteria are met, the platform proceeds to add a second vertical (Tennis or Climbing) while maintaining the Padel foundation.

---

## 17. Appendix: Key Assumptions to Test

The MVP is designed to validate these core assumptions:

1. **AI can generate locally authentic content** that passes user and search engine quality bars
2. **Automated data maintenance** is sufficient to keep directories fresh at scale
3. **Users prefer comprehensive ecosystem mapping** over fragmented single-purpose tools
4. **Businesses will claim and maintain profiles** when shown traffic value
5. **Long-tail local search** generates sufficient volume to build a sustainable platform
6. **The universal entity framework** generalizes across different hobby verticals

Each assumption has explicit success criteria and kill conditions defined in the roadmap.
