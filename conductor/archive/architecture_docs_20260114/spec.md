# Track Specification: Create Architecture Documentation

## 1. Overview
The goal of this track is to create a comprehensive `ARCHITECTURE.md` file in the project root. This document will serve as the primary architectural reference for "Edinburgh Finds," detailing the system's core philosophy, the "Universal Entity Framework," data pipelines, and trust mechanisms. It will provide a high-level map that connects the business vision (PRD) with the technical implementation.

## 2. Functional Requirements

### 2.1. File Creation and Placement
- Create `ARCHITECTURE.md` in the project root directory.
- Ensure it serves as the central architectural entry point, referencing existing detailed documentation (like `docs/architecture/`) where appropriate.

### 2.2. Core Content Sections
The document must include the following distinct sections:

1.  **System Overview:** High-level interaction of components (Frontend, Backend, Data Engine).
2.  **Universal Entity Framework Implementation:**
    -   Detailed mapping of the 5 Entity Pillars (Infrastructure, Commerce, Guidance, Organization, Momentum) to the database schema.
    -   Explanation of how the schema supports horizontal scaling across different niches (e.g., Padel, Golf) without schema migrations.
3.  **Data Ingestion & Pipeline Architecture:**
    -   Workflow of the Python data engine: Autonomous ingestion -> Processing -> Database.
    -   Triggers and scheduling (when it runs).
4.  **Confidence Grading & Trust Architecture:**
    -   Mechanisms for source tracking and conflict resolution.
    -   Handling "freshness" and confidence degradation over time.
    -   **Business Claiming Workflow:** How owners authenticate and how their inputs strictly override AI/scraped data.
5.  **Content Quality & "Local Soul" System:**
    -   Where AI content generation occurs.
    -   Programmatic enforcement of local tone and quality standards (avoiding "marketing fluff").
6.  **Key Technical Decisions:**
    -   Rationales for key choices (e.g., Next.js, Python for data, SQLite/Supabase).
7.  **Deployment & Infrastructure:**
    -   Overview of the hosting and deployment strategy.
8.  **Programmatic SEO Architecture:**
    -   Dynamic page generation strategies for long-tail queries.
    -   Static vs. Dynamic rendering (SSG/SSR/ISR) usage in Next.js.
    -   Handling scale (hundreds/thousands of auto-generated entity pages).
9.  **Scaling Path:**
    -   **Horizontal:** Strategy for adding new niches (Tennis, Climbing) and managing N×M complexity.
    -   **Vertical:** Strategy for adding new geographies (Glasgow, Manchester).

### 2.3. Visual Documentation
-   Utilize **Mermaid.js** diagrams embedded directly within the Markdown to illustrate:
    -   The Data Pipeline flow.
    -   The Universal Entity Framework schema relationships.
    -   The Business Claiming / Data Override logic.

## 3. Non-Functional Requirements
-   **Clarity:** Use clear, professional language suitable for both technical and semi-technical stakeholders.
-   **Maintenance:** The document structure should be modular to allow easy updates as the system evolves.
-   **Links:** Correctly link to other relevant files (e.g., `docs/architecture/c4-level1-context.md`, `conductor/product.md`).

## 4. Acceptance Criteria
-   `ARCHITECTURE.md` exists in the root.
-   All 9 core content sections are present and populated with accurate information based on the current codebase and PRD.
-   At least 3 Mermaid.js diagrams are included and render correctly on GitHub.
-   The document accurately describes the "Universal Entity Framework" and "Confidence Grading" systems as per the user's specific definitions.
