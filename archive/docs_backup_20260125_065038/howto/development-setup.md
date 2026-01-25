# Development Setup

Follow these steps to set up a local development environment for Edinburgh Finds.

## Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL** (or a Supabase account)
- **Git**

## 1. Clone the Repository
```bash
git clone https://github.com/your-repo/edinburgh_finds.git
cd edinburgh_finds
```

## 2. Data Engine Setup (Python)
The data engine handles ETL and ingestion.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r engine/requirements.txt
```

### Environment Configuration
Create a `.env` file in the root directory:
```env
DATABASE_URL="postgresql://user:password@localhost:5432/edinburgh_finds"
ANTHROPIC_API_KEY="your-key-here"
SERPER_API_KEY="your-key-here"
GOOGLE_PLACES_API_KEY="your-key-here"
```

## 3. Web Application Setup (Next.js)
The web application provides the discovery interface.

```bash
cd web
npm install
```

### Environment Configuration
Create a `web/.env` file:
```env
DATABASE_URL="postgresql://user:password@localhost:5432/edinburgh_finds"
```

## 4. Initialize the Database
Generate the schema from YAML and apply migrations.

```bash
# From the root directory
python -m engine.schema.generate

# Apply migrations
cd web
npx prisma migrate dev
```

## 5. Running the Application

### Start the Web App
```bash
cd web
npm run dev
```

### Run an Ingestion Task
```bash
# From the root directory (with venv active)
python engine/run_osm_manual.py --query "Tennis courts in Edinburgh"
```

---
*Evidence: engine/requirements.txt, web/package.json, and conductor/tech-stack.md.*
