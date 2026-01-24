# Edinburgh Finds

**Edinburgh Finds** is a sophisticated data ingestion and extraction platform designed to transform unstructured and semi-structured data from various sources (Google Places, OpenStreetMap, Serper) into high-quality, structured, and domain-specific entities.

It decouples the **Core Engine** (ingestion, generic extraction, deduplication, storage) from the **Lens Layer** (domain-specific logic like "Wine Discovery" or "Sports Venues"), allowing a single platform to serve multiple vertical applications.

## Key Capabilities

- **Multi-Source Ingestion**: Fetch data from Google Places, OpenStreetMap, and generic web searches.
- **LLM-Powered Extraction**: Use Large Language Models (Claude/Instructor) to intelligently parse, classify, and structure data.
- **Lens Architecture**: deeply separates "Engine Purity" (generic infrastructure) from "Domain Specificity" (business logic), enabling rapid deployment of new verticals.
- **Entity Resolution**: Sophisticated deduplication and merging strategies to create a "Golden Record" from multiple conflicting sources.
- **Next.js Dashboard**: A modern web interface for visualizing, managing, and curating the extracted data.

## Target Audience

- **Data Engineers**: Building robust pipelines for local discovery data.
- **Product Developers**: Creating vertical discovery apps (e.g., "Find the best Padel courts", "Discover natural wine bars").
- **Researchers**: Aggregating disparate data sources into a coherent dataset.
