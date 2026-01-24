# C4 Level 3: Component Diagram (Web Application)

**Generated:** 2026-01-15
**System:** Edinburgh Finds
**Container:** Web Application

## Purpose

This diagram breaks down the Web Application container into its main components and their interactions.

## Diagram

```mermaid
graph TB
    User["User"]

    subgraph WebApp["Web Application"]
        Layout["App Layout<br/><b>Tech: Next.js</b><br/>Root layout and shell"]
        HomePage["Home Page<br/><b>Tech: React Server Component</b><br/>Renders listing preview"]
        PrismaClient["Prisma Client<br/><b>Tech: @prisma/client</b><br/>DB access"]
        AttributeUtils["Attribute Utils<br/><b>Tech: TypeScript</b><br/>Parse and format listing data"]
        Styles["Global Styles<br/><b>Tech: Tailwind CSS</b><br/>Base styling"]
    end

    DB["Database<br/><b>Tech: SQLite (Prisma)</b>"]

    User -->|"HTTPS"| HomePage
    Layout -->|"Wraps"| HomePage
    HomePage -->|"Parse/format"| AttributeUtils
    HomePage -->|"Query listings"| PrismaClient
    PrismaClient -->|"Prisma / SQL"| DB
    Styles -->|"Apply"| HomePage
```

## Components

| Component | Responsibility |
|-----------|----------------|
| App Layout | Defines page shell and document structure |
| Home Page | Fetches listings and renders summary view |
| Prisma Client | Database access layer |
| Attribute Utils | Parse and format JSON attributes for display |
| Global Styles | Base styling for the app |
