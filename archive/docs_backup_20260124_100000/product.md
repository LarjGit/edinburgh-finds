# Product Definition

Audience: Product Managers, Developers, and Stakeholders.

## Core Mission & USP

**Edinburgh Finds** is a hyper-local, niche-focused discovery platform.

- **Mission**: To build the premier discovery platform starting with Padel in Edinburgh.
- **USP**: "AI-Scale, Local Soul". We use LLMs to autonomously source and structure data while delivering a curated user experience.

Evidence: `conductor/product.md` (Section 1)

## Architecture Philosophy

The platform is built on a **Universal Entity Framework**.

1.  **Universal Engine**: A vertical-agnostic core that stores entities (People, Places, Organizations) with opaque dimensions (activities, roles).
2.  **Lenses**: A configuration layer that interprets this universal data for specific niches (e.g., Padel, Wine). This allows the engine to remain pure while supporting diverse verticals.

Evidence: `conductor/product.md` (Section 2), `engine/config/entity_model.yaml` (Header comments)

## Target Audience

- **Enthusiasts**: From beginners seeking "where to start" to active players looking for partners or tournaments.
- **Business Owners**: Using the platform as a high-intent marketing channel.

Evidence: `conductor/product.md` (Section 4)

## Quality Standards

- **Voice**: "The Knowledgeable Local Friend".
- **Trust**: We prioritize credibility. Business-claimed data is the gold standard ("Golden Data").
- **Content**: No marketing fluff; focus on geographic context and practical utility.

Evidence: `conductor/product.md` (Section 5)
