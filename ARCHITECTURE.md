# Architecture: Edinburgh Finds

## 1. System Overview

Edinburgh Finds is a hyper-local, niche-focused discovery platform designed to connect enthusiasts with the entities that power their hobbies. The system operates on a "Knowledgeable Local Friend" philosophy, combining AI-driven scale with a curated, human-centric user experience.

The system is composed of three primary subsystems:
1.  **Frontend (Web Application):** A Next.js-based user interface that delivers a fast, SEO-optimized experience.
2.  **Data Engine (Ingestion):** An autonomous Python-based pipeline that sources, deduplicates, and structures data from multiple external APIs.
3.  **Universal Entity Framework (Database):** A flexible schema designed to support any vertical (e.g., Padel, Golf) without structural changes.

## 6. Key Technical Decisions

### 6.1. Next.js (App Router)
-   **Why:** Provides server-side rendering (SSR) for SEO and static site generation (SSG) for performance. The App Router architecture aligns with React's modern server components model.
-   **Trade-off:** Higher complexity than a plain SPA, but essential for a content-heavy discovery platform.

### 6.2. Python for Data Engine
-   **Why:** Python's ecosystem for data processing (Pandas, Pydantic) and scraping/automation is superior to Node.js. It allows for robust, type-safe ETL pipelines.
-   **Integration:** Decoupled from the frontend, interacting primarily via the database and file system.

### 6.3. SQLite (Dev) to Supabase (Prod)
-   **Why:** SQLite simplifies local development (zero config). Supabase (PostgreSQL) provides a scalable, managed production database with strong relational integrity.
-   **Constraint:** We use Prisma to abstract the database differences, ensuring the schema works on both.

### 6.4. Prisma ORM
-   **Why:** Provides type-safety across both TypeScript (Frontend) and Python (Data Engine) using the same schema definition.
