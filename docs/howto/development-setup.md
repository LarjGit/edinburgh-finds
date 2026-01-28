# Development Setup Guide

Follow these steps to set up the Edinburgh Finds development environment on your local machine.

## Prerequisites
- **Python 3.12+**
- **Node.js 20+** (with npm)
- **Git**
- **LLM API Keys**: Anthropic (for extraction).

## 1. Repository Setup
```bash
git clone <repo-url>
cd edinburgh_finds
```

## 2. Backend (Engine) Setup
Create a virtual environment and install dependencies:
```bash
# Create venv
python -m venv venv

# Activate venv
# Windows:
.\venv\Scripts\activate
# Unix/Mac:
source venv/bin/activate

# Install dependencies
pip install -r engine/requirements.txt
```

### Configure Environment
Copy the example environment file and fill in your keys:
```bash
cp .env.example .env
```
Ensure `ANTHROPIC_API_KEY` is set.

## 3. Frontend (Web) Setup
Install Node.js dependencies:
```bash
cd web
npm install
```

## 4. Database Initialization
Generate the Prisma clients and push the schema to your local development database (SQLite):
```bash
# From the root directory
# Generate Python Prisma client
python -m prisma generate --schema=engine/schema.prisma

# Generate JS Prisma client and push schema
cd web
npx prisma generate
npx prisma db push
```

## 5. Running the Application

### Start the Discovery Web App
```bash
cd web
npm run dev
```
The app will be available at `http://localhost:3000`.

### Run an Ingestion Test
```bash
python -m engine.ingestion.cli google_places "test query"
```

## 6. Verification
Run the core tests to ensure everything is configured correctly:
```bash
pytest tests/engine/test_purity.py
```

---
*Evidence: web/package.json, engine/requirements.txt, docs/architecture/subsystems/engine.md*
