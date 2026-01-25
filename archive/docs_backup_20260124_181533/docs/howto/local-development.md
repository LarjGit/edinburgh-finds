Audience: Developers

# Local Development Setup

This guide will walk you through setting up the Edinburgh Finds engine and web frontend for local development.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+** with **PostGIS** extension
- **Git**

## Backend Setup (Python Engine)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/edinburgh_finds.git
    cd edinburgh_finds
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r engine/requirements.txt
    ```

4.  **Configure environment variables:**
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and provide your database credentials and API keys (Anthropic/OpenAI).

5.  **Configure data sources:**
    ```bash
    cp engine/config/sources.yaml.example engine/config/sources.yaml
    ```
    Add your API keys for Google Places, Serper, etc., in `engine/config/sources.yaml`.

6.  **Initialize the database:**
    ```bash
    # Ensure PostGIS is installed in your Postgres instance
    npx prisma db push --schema engine/schema.prisma
    ```

## Frontend Setup (Next.js)

1.  **Navigate to the web directory:**
    ```bash
    cd web
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the development server:**
    ```bash
    npm run dev
    ```
    The frontend will be available at `http://localhost:3000`.

## Verifying the Setup

1.  **Run a sample ingestion:**
    ```bash
    python -m engine.ingestion.cli osm "tennis"
    ```

2.  **Check the database:**
    Use `python engine/inspect_db.py` or a database client to verify that `RawIngestion` records were created.

3.  **Run extraction (requires LLM API key):**
    ```bash
    python engine/run_osm_manual.py
    ```

## Troubleshooting

- **Database Connection:** Ensure Postgres is running and the `DATABASE_URL` in `.env` is correct.
- **PostGIS:** If you see errors related to geometry types, ensure the PostGIS extension is enabled: `CREATE EXTENSION postgis;` in your database.
- **Node Versions:** Use `nvm` to ensure you are on Node 18 or higher if you encounter build errors in the web directory.
