# Quickstart Guide

This guide will get you up and running with the Edinburgh Finds platform.

## Prerequisites

- **Python 3.10+**: For the extraction engine.
- **Node.js 18+**: For the web dashboard.
- **PostgreSQL**: A running Postgres database.
- **API Keys**:
  - Anthropic API Key (for LLM extraction)
  - Google Places API Key (optional, for ingestion)
  - Serper API Key (optional, for search ingestion)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd edinburgh_finds
```

### 2. Backend Setup (Engine)
Create a virtual environment and install dependencies:

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r engine/requirements.txt
```

### 3. Frontend Setup (Web)
Install Node.js dependencies:

```bash
cd web
npm install
cd ..
```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and provide your configuration:
   - `DATABASE_URL`: Your Postgres connection string.
   - `ANTHROPIC_API_KEY`: Required for extraction.

3. Initialize the Database:
   ```bash
   # From the project root (ensure venv is active)
   python -m engine.schema.migrate
   # OR if using Prisma CLI directly
   prisma migrate dev --schema=engine/schema.prisma
   ```

## Running the System

### 1. Start the Ingestion (Example)
Run a manual ingestion script to fetch data:

```bash
python engine/ingest.py
```

### 2. Start the Web Dashboard
Launch the Next.js development server:

```bash
cd web
npm run dev
```
Visit `http://localhost:3000` to view the dashboard.

## Next Steps

- Read the [Architecture Overview](architecture/overview.md) to understand the system.
- Check [How to Run Extraction](howto/run-extraction.md) for more workflows.
