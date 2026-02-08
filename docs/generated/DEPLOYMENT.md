# Deployment Guide

**System:** Universal Entity Extraction Engine
**Reference Application:** Edinburgh Finds
**Last Updated:** 2026-02-08

## Table of Contents

1. [Overview](#overview)
2. [Deployment Architecture](#deployment-architecture)
3. [Environment Configuration](#environment-configuration)
4. [Infrastructure Requirements](#infrastructure-requirements)
5. [Deployment Environments](#deployment-environments)
6. [Frontend Deployment (Vercel)](#frontend-deployment-vercel)
7. [Backend Deployment (Python Engine)](#backend-deployment-python-engine)
8. [Database Setup (Supabase)](#database-setup-supabase)
9. [CI/CD Pipeline](#cicd-pipeline)
10. [Monitoring & Observability](#monitoring--observability)
11. [Scaling Considerations](#scaling-considerations)
12. [Security Hardening](#security-hardening)
13. [Troubleshooting](#troubleshooting)

---

## Overview

The Universal Entity Extraction Engine deploys as a **two-tier architecture**:

- **Frontend Tier:** Next.js 16 web application (React 19, TypeScript, Tailwind CSS v4)
- **Backend Tier:** Python extraction engine (orchestration, ingestion, extraction, lens application)
- **Database Tier:** PostgreSQL (Supabase) with Prisma ORM

**Deployment Philosophy:**
- Frontend: Serverless edge deployment (Vercel recommended for Next.js optimization)
- Backend: Containerized Python engine (Cloud Run, AWS Lambda, or Docker-based platforms)
- Database: Managed PostgreSQL with automatic backups and connection pooling

---

## Deployment Architecture

```mermaid
graph TB
    %% Users
    subgraph Users["<b>USERS</b>"]
        Browser["Web Browser<br/>(Desktop/Mobile)"]
        APIClient["API Clients<br/>(Future)"]
    end

    %% CDN & Edge Layer
    subgraph EdgeLayer["<b>EDGE LAYER</b>"]
        CDN["CDN<br/>(Static Assets)<br/>• Images<br/>• JS/CSS Bundles<br/>• Fonts"]
        EdgeCache["Edge Cache<br/>(Next.js ISR)<br/>• Pre-rendered Pages<br/>• Revalidation"]
    end

    %% Frontend Tier
    subgraph FrontendTier["<b>FRONTEND TIER</b><br/>(Vercel / Cloud Platform)"]
        NextJS["Next.js 16 App<br/>(React 19)<br/>• App Router<br/>• Server Components<br/>• API Routes"]
        PrismaClient["Prisma Client<br/>(TypeScript)<br/>• Type-Safe Queries<br/>• Connection Pooling"]
    end

    %% Backend Tier
    subgraph BackendTier["<b>BACKEND TIER</b><br/>(Cloud Run / Lambda / Docker)"]
        EngineAPI["Python Engine API<br/>• FastAPI / Flask<br/>• Orchestration Endpoint<br/>• Health Checks"]
        OrchSystem["Orchestration System<br/>• Query Planner<br/>• Connector Router<br/>• Budget Manager"]
        ExtractionPipeline["Extraction Pipeline<br/>• Parallel Execution<br/>• LLM Integration<br/>• Deduplication"]
        PrismaPython["Prisma Client Python<br/>• ORM Layer<br/>• Transaction Support"]
    end

    %% Database Tier
    subgraph DatabaseTier["<b>DATABASE TIER</b><br/>(Supabase - PostgreSQL)"]
        Primary["Primary Database<br/>• Entity Tables<br/>• RawIngestion<br/>• ExtractedEntity"]
        Replica["Read Replica<br/>(Optional)<br/>• Query Offloading<br/>• Analytics"]
        Backup["Automated Backups<br/>• Point-in-Time Recovery<br/>• Daily Snapshots"]
        ConnectionPool["Connection Pooler<br/>(PgBouncer)<br/>• Max Connections<br/>• Transaction Mode"]
    end

    %% External Services
    subgraph ExternalServices["<b>EXTERNAL SERVICES</b>"]
        AnthropicAPI["Anthropic Claude API<br/>• Structured Extraction<br/>• Instructor Integration<br/>• Rate Limiting"]
        SerperAPI["Serper API<br/>• Web Search<br/>• Entity Discovery"]
        GooglePlacesAPI["Google Places API<br/>• Place Details<br/>• Reviews & Ratings"]
        OSMAPI["OpenStreetMap API<br/>• Geo Data<br/>• Free Tier"]
        SportScotAPI["Sport Scotland API<br/>• Facilities Data<br/>• Public Registry"]
        CustomAPIs["Custom Data Sources<br/>• Vertical-Specific<br/>• Web Scrapers"]
    end

    %% Infrastructure & Operations
    subgraph InfraOps["<b>INFRASTRUCTURE & OPERATIONS</b>"]
        SecretMgr["Secret Manager<br/>• API Keys<br/>• Database Credentials<br/>• Environment Variables"]
        Monitor["Monitoring & Logging<br/>• Error Tracking (Sentry)<br/>• Performance Metrics<br/>• Query Analytics"]
        LoadBalancer["Load Balancer<br/>(Optional)<br/>• Health Checks<br/>• Auto-Scaling"]
    end

    %% Data Flow Connections
    Browser --> EdgeCache
    Browser --> NextJS
    APIClient -.->|"Future"| EngineAPI

    EdgeCache --> CDN
    NextJS --> PrismaClient
    NextJS --> EngineAPI

    EngineAPI --> OrchSystem
    OrchSystem --> ExtractionPipeline
    ExtractionPipeline --> PrismaPython

    PrismaClient --> ConnectionPool
    PrismaPython --> ConnectionPool
    ConnectionPool --> Primary

    Primary --> Replica
    Primary --> Backup

    ExtractionPipeline --> AnthropicAPI
    OrchSystem --> SerperAPI
    OrchSystem --> GooglePlacesAPI
    OrchSystem --> OSMAPI
    OrchSystem --> SportScotAPI
    OrchSystem --> CustomAPIs

    SecretMgr --> NextJS
    SecretMgr --> EngineAPI
    Monitor --> NextJS
    Monitor --> EngineAPI
    LoadBalancer -.->|"Optional"| EngineAPI

    %% Network Boundaries
    Users -.->|"HTTPS"| EdgeLayer
    EdgeLayer -.->|"HTTPS"| FrontendTier
    FrontendTier -.->|"Internal Network<br/>(VPC/Private)"| BackendTier
    BackendTier -.->|"Secure Connection<br/>(SSL/TLS)"| DatabaseTier
    BackendTier -.->|"HTTPS<br/>(API Keys)"| ExternalServices

    %% Styling
    classDef userLayer fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    classDef edgeLayer fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    classDef frontendLayer fill:#e1f5ff,stroke:#0066cc,stroke-width:2px,color:#000
    classDef backendLayer fill:#e8f5e9,stroke:#4caf50,stroke-width:2px,color:#000
    classDef dbLayer fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    classDef externalLayer fill:#fce4ec,stroke:#e91e63,stroke-width:2px,color:#000
    classDef infraLayer fill:#f5f5f5,stroke:#616161,stroke-width:2px,color:#000

    class Users userLayer
    class EdgeLayer edgeLayer
    class FrontendTier frontendLayer
    class BackendTier backendLayer
    class DatabaseTier dbLayer
    class ExternalServices externalLayer
    class InfraOps infraLayer
```

### Network Architecture

```mermaid
graph LR
    subgraph Public["Public Internet"]
        User["User Browser"]
        ExtAPI1["Serper API<br/>(HTTPS)"]
        ExtAPI2["Google Places API<br/>(HTTPS)"]
        ExtAPI3["OpenStreetMap<br/>Overpass API<br/>(HTTPS)"]
        ExtAPI4["SportScotland API<br/>(HTTPS)"]
        ExtAPI5["EventBrite API<br/>(HTTPS)"]
        ExtAPI6["Anthropic Claude API<br/>(HTTPS)"]
    end

    subgraph Internal["Internal Application Network"]
        subgraph Web["Next.js Web Application"]
            WebApp["Next.js Server<br/>(Port 3000)"]
            API["API Routes<br/>/api/*"]
        end

        subgraph Engine["Python Engine"]
            Orchestrator["Query Orchestration<br/>(Planner + Registry)"]
            Connectors["Connector Layer<br/>(6 Data Sources)"]
            Extractors["Extraction Engine<br/>(Hybrid Rules + LLM)"]
            LensEngine["Lens Application<br/>(Canonical Mapping)<br/>⚠️ Partial Implementation"]
            Merge["Merge & Finalization<br/>(Deduplication)"]
        end

        subgraph Data["Database Layer"]
            DB["PostgreSQL<br/>(Supabase)<br/>Prisma Client"]
        end
    end

    %% User flows
    User -->|"HTTPS"| WebApp
    WebApp -->|"Server-Side Rendering"| User

    %% Web App internal flows
    WebApp -->|"API Calls"| API
    API -->|"Prisma ORM"| DB

    %% Web App reads finalized entities only (Engine invoked via CLI)
    API -->|"GET /api/entities/:slug"| DB
    API -->|"GET /api/entities?filter=..."| DB

    %% Engine internal pipeline
    Orchestrator -->|"Phase-based<br/>Execution Plan"| Connectors
    Connectors -->|"Raw Payloads"| DB
    Extractors -->|"ExtractedEntity<br/>Records"| DB
    LensEngine -->|"Canonical<br/>Dimensions"| Merge
    Merge -->|"Entity Upsert<br/>(Idempotent)"| DB

    %% Connectors → External APIs
    Connectors -->|"HTTPS<br/>API Key:<br/>SERPER_API_KEY"| ExtAPI1
    Connectors -->|"HTTPS<br/>API Key:<br/>GOOGLE_PLACES_API_KEY"| ExtAPI2
    Connectors -->|"HTTPS<br/>Public API"| ExtAPI3
    Connectors -->|"HTTPS<br/>Public/API Key"| ExtAPI4
    Connectors -->|"HTTPS<br/>Public API"| ExtAPI5

    %% LLM extraction
    Extractors -->|"HTTPS<br/>API Key:<br/>ANTHROPIC_API_KEY<br/>Instructor SDK"| ExtAPI6
    LensEngine -->|"HTTPS<br/>Schema-Bound<br/>Extraction"| ExtAPI6

    %% Engine ↔ Database
    Orchestrator -->|"Prisma Client<br/>Python"| DB
    Extractors -->|"Prisma Client<br/>Python"| DB

    %% Styling
    classDef publicNode fill:#e1f5ff,stroke:#0288d1,stroke-width:2px
    classDef webNode fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef engineNode fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef dbNode fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef apiNode fill:#fce4ec,stroke:#c2185b,stroke-width:2px

    class User,ExtAPI1,ExtAPI2,ExtAPI3,ExtAPI4,ExtAPI5,ExtAPI6 publicNode
    class WebApp,API webNode
    class Orchestrator,Connectors,Extractors,LensEngine,Merge engineNode
    class DB dbNode
```

---

## Environment Configuration

### Required Environment Variables

All environments require the following variables:

```bash
# ============================================================
# DATABASE CONFIGURATION
# ============================================================
# PostgreSQL connection string (Supabase recommended)
# Format: postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public
DATABASE_URL="postgresql://postgres:password@hostname:5432/database_name?schema=public"

# ============================================================
# API KEYS (REQUIRED)
# ============================================================
# Anthropic Claude API for LLM extraction
ANTHROPIC_API_KEY="sk-ant-api03-..."

# Google Places API for venue data
GOOGLE_PLACES_API_KEY="your-google-places-api-key"

# Serper API for web search-based ingestion
SERPER_API_KEY="your-serper-api-key"

# ============================================================
# OPTIONAL CONFIGURATION
# ============================================================
# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL="INFO"

# Node environment (development, production, test)
NODE_ENV="production"

# Next.js build optimization
NEXT_TELEMETRY_DISABLED=1
```

### Environment-Specific Overrides

**Development:**
```bash
NODE_ENV="development"
LOG_LEVEL="DEBUG"
DATABASE_URL="postgresql://localhost:5432/edinburgh_finds_dev"
```

**Staging:**
```bash
NODE_ENV="staging"
LOG_LEVEL="INFO"
DATABASE_URL="postgresql://staging.supabase.co:5432/edinburgh_finds_staging"
```

**Production:**
```bash
NODE_ENV="production"
LOG_LEVEL="WARNING"
DATABASE_URL="postgresql://production.supabase.co:5432/edinburgh_finds_prod"
```

---

## Infrastructure Requirements

### Minimum Requirements

**Frontend (Next.js):**
- **Platform:** Vercel, Netlify, AWS Amplify, or Docker-based hosting
- **Memory:** 512MB minimum, 1GB recommended
- **CPU:** 0.5 vCPU minimum
- **Node.js:** v20.x or later
- **Build Time:** ~2-5 minutes

**Backend (Python Engine):**
- **Platform:** Google Cloud Run, AWS Lambda, Azure Container Instances, or Docker
- **Memory:** 2GB minimum, 4GB recommended (for LLM extraction workloads)
- **CPU:** 1 vCPU minimum, 2 vCPU recommended
- **Python:** 3.10+ required
- **Startup Time:** ~10-30 seconds (cold start)
- **Execution Timeout:** 300 seconds minimum (for multi-source orchestration)

**Database (PostgreSQL):**
- **Provider:** Supabase (recommended), AWS RDS, Google Cloud SQL, Azure Database
- **PostgreSQL Version:** 14+ required (for GIN indexes on TEXT[] arrays)
- **Storage:** 10GB minimum, auto-scaling recommended
- **Connections:** 100 concurrent connections minimum (use PgBouncer pooling)
- **Backups:** Daily automated backups, 7-day retention minimum

### Recommended Production Configuration

**Frontend:**
- Vercel Pro plan with edge caching
- CDN: Cloudflare or Vercel Edge Network
- ISR revalidation: 3600 seconds (1 hour) for entity pages

**Backend:**
- Google Cloud Run with auto-scaling (0-10 instances)
- 4GB memory, 2 vCPU per instance
- Max 300 concurrent requests per instance
- Request timeout: 300 seconds

**Database:**
- Supabase Pro plan with connection pooling
- Primary + read replica for analytics workloads
- Point-in-time recovery enabled
- Daily backups with 30-day retention

---

## Deployment Environments

### Development Environment

**Purpose:** Local development and testing

**Setup:**
```bash
# 1. Clone repository
git clone https://github.com/your-org/edinburgh-finds.git
cd edinburgh-finds

# 2. Install dependencies
cd web && npm install
cd ..
python -m pip install -r engine/requirements.txt

# 3. Set up local database (optional - use Supabase dev instance)
# Or use local PostgreSQL:
# createdb edinburgh_finds_dev

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your API keys and DATABASE_URL

# 5. Generate Prisma client and sync database
cd web
npx prisma generate
npx prisma db push

# 6. Run development servers
npm run dev  # Frontend on http://localhost:3000

# In separate terminal:
cd engine
python -m engine.orchestration.cli run "test query"  # Backend engine
```

**Database:** Local PostgreSQL or Supabase free tier
**API Keys:** Development/test API keys with rate limits
**Monitoring:** Console logging only

### Staging Environment

**Purpose:** Pre-production validation and QA testing

**Infrastructure:**
- **Frontend:** Vercel preview deployment (automatic for PRs)
- **Backend:** Google Cloud Run (staging project) or Docker staging server
- **Database:** Supabase staging instance (separate from production)

**Deployment Trigger:** Merge to `develop` branch or manual trigger

**Configuration:**
```bash
# Vercel environment variables (set in Vercel dashboard)
DATABASE_URL=$STAGING_DATABASE_URL
ANTHROPIC_API_KEY=$STAGING_ANTHROPIC_KEY
NODE_ENV=staging
```

**Validation:**
- Run smoke tests against staging environment
- Verify database migrations apply cleanly
- Test external API integrations
- Check performance benchmarks

### Production Environment

**Purpose:** Live user-facing application

**Infrastructure:**
- **Frontend:** Vercel production deployment with global CDN
- **Backend:** Google Cloud Run (production project) with auto-scaling
- **Database:** Supabase production instance with read replicas

**Deployment Trigger:** Merge to `main` branch (with approval gate)

**Configuration:**
```bash
# Vercel production environment variables
DATABASE_URL=$PRODUCTION_DATABASE_URL
ANTHROPIC_API_KEY=$PRODUCTION_ANTHROPIC_KEY
NODE_ENV=production
LOG_LEVEL=WARNING
NEXT_TELEMETRY_DISABLED=1
```

**Pre-Deployment Checklist:**
- [ ] All tests passing (pytest, ESLint)
- [ ] Database migration tested in staging
- [ ] Performance benchmarks meet SLA (Core Web Vitals)
- [ ] Security scan completed (no critical vulnerabilities)
- [ ] Rollback plan documented

---

## Frontend Deployment (Vercel)

### Why Vercel?

Vercel is the **recommended hosting platform** for Next.js applications:
- Zero-configuration deployment for Next.js
- Global edge network with automatic CDN
- Incremental Static Regeneration (ISR) support
- Automatic HTTPS and custom domain support
- Built-in preview deployments for PRs

### Deployment Steps

#### 1. Connect Repository

```bash
# Install Vercel CLI (optional)
npm i -g vercel

# Login to Vercel
vercel login

# Link project
cd web
vercel link
```

#### 2. Configure Environment Variables

In Vercel dashboard (Project Settings → Environment Variables):

```bash
# Required for all environments
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_PLACES_API_KEY=...
SERPER_API_KEY=...

# Production-specific
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

#### 3. Configure Build Settings

**Build Command:** `npm run build` (default)
**Output Directory:** `.next` (default)
**Install Command:** `npm install` (default)

**Advanced Settings:**
- **Node.js Version:** 20.x
- **Framework Preset:** Next.js
- **Root Directory:** `web/` (if deploying from monorepo)

#### 4. Deploy

**Automatic (Git Integration):**
```bash
# Push to main branch → production deployment
git push origin main

# Push to PR → preview deployment
git push origin feature-branch
```

**Manual (CLI):**
```bash
cd web
vercel --prod  # Deploy to production
vercel         # Deploy preview
```

#### 5. Configure Custom Domain

In Vercel dashboard:
1. Go to Project Settings → Domains
2. Add custom domain (e.g., `edinburghfinds.com`)
3. Update DNS records as instructed
4. Vercel automatically provisions SSL certificate

### Performance Optimization

**Incremental Static Regeneration (ISR):**
```typescript
// app/entities/[slug]/page.tsx
export const revalidate = 3600; // Revalidate every 1 hour

export async function generateStaticParams() {
  // Pre-render top 100 entities at build time
  const entities = await prisma.entity.findMany({
    take: 100,
    orderBy: { updatedAt: 'desc' }
  });
  return entities.map(e => ({ slug: e.slug }));
}
```

**Edge Caching:**
- Static assets cached indefinitely at edge
- Dynamic routes cached with `stale-while-revalidate`
- API routes use conditional caching headers

---

## Backend Deployment (Python Engine)

### Deployment Options

#### Option 1: Google Cloud Run (Recommended)

**Why Cloud Run?**
- Serverless with automatic scaling (0 to N instances)
- Pay-per-use pricing (no idle costs)
- Docker-based deployment (flexible runtime)
- Integrated load balancing and HTTPS
- Supports long-running requests (up to 60 minutes)

**Deployment Steps:**

1. **Create Dockerfile:**
```dockerfile
# engine/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy engine code
COPY . .

# Generate Prisma client
RUN prisma generate

# Expose port (Cloud Run uses PORT env var)
ENV PORT=8080
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
  CMD curl -f http://localhost:8080/health || exit 1

# Run FastAPI server (or Flask)
CMD ["uvicorn", "engine.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

2. **Build and Push Image:**
```bash
# Configure Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and push to Google Container Registry
cd engine
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/engine:latest

# Or use Docker + Artifact Registry
docker build -t gcr.io/YOUR_PROJECT_ID/engine:latest .
docker push gcr.io/YOUR_PROJECT_ID/engine:latest
```

3. **Deploy to Cloud Run:**
```bash
gcloud run deploy engine \
  --image gcr.io/YOUR_PROJECT_ID/engine:latest \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=$DATABASE_URL,ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
```

4. **Configure Secret Manager Integration:**
```bash
# Store secrets in Google Secret Manager
echo -n "your-anthropic-key" | gcloud secrets create anthropic-api-key --data-file=-

# Grant Cloud Run access to secret
gcloud run services update engine \
  --update-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest
```

#### Option 2: AWS Lambda (Serverless)

**Use Case:** Event-driven extraction (triggered by S3 uploads, SQS messages)

**Limitations:**
- 15-minute execution timeout (may not suit full orchestration pipeline)
- 10GB memory maximum
- Cold start latency (5-30 seconds)

**Deployment:**
```bash
# Use AWS SAM or Serverless Framework
npm install -g serverless
serverless deploy --stage production
```

#### Option 3: Docker on VPS/Kubernetes

**Use Case:** Self-hosted or on-premise deployments

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  engine:
    build: ./engine
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Deploy:
```bash
docker-compose up -d
```

### Backend API Design (Future)

**Current State:** Engine runs via CLI (`python -m engine.orchestration.cli`). Web frontend reads finalized entities from database only.

**Future:** REST API for real-time entity enrichment

**Recommended Framework:** FastAPI (async support, automatic OpenAPI docs)

**Example Endpoint:**
```python
# engine/api/main.py
from fastapi import FastAPI
from engine.orchestration.orchestrator import run_orchestration

app = FastAPI()

@app.post("/api/v1/entities/discover")
async def discover_entities(query: str):
    """Execute orchestration pipeline and return entities"""
    result = await run_orchestration(query)
    return {"entities": result.entities, "sources": result.sources}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## Database Setup (Supabase)

### Why Supabase?

- **Managed PostgreSQL:** No server management, automatic backups
- **Connection Pooling:** Built-in PgBouncer for high concurrency
- **Realtime APIs:** WebSocket support (future feature)
- **Auth & Storage:** Integrated authentication and file storage
- **Free Tier:** Generous limits for development/staging

### Setup Steps

#### 1. Create Supabase Project

1. Sign up at [supabase.com](https://supabase.com)
2. Create new project (choose region closest to users)
3. Note database password (stored in password manager)

#### 2. Configure Connection Pooling

**Transaction Mode (Recommended):**
- Supports Prisma migrations and complex queries
- Connection string: `postgresql://...:6543/postgres?pgbouncer=true`

**Session Mode:**
- For long-running transactions
- Connection string: `postgresql://...:5432/postgres`

#### 3. Apply Database Schema

```bash
cd web

# Generate Prisma client from schema
npx prisma generate

# Apply schema to database
npx prisma db push  # Development (non-destructive)

# Or create migration
npx prisma migrate dev --name init  # Creates migration file
npx prisma migrate deploy  # Apply migrations in production
```

#### 4. Configure Database Indexes

Prisma schema already includes critical indexes:

```prisma
model Entity {
  // ...
  @@index([entity_name])
  @@index([entity_class])
  @@index([city])
  @@index([postcode])
  @@index([latitude, longitude])  // Geospatial queries
  @@index([createdAt])
  @@index([updatedAt])
}
```

**Additional Indexes (Manual SQL):**
```sql
-- GIN index for array dimensions (canonical_activities, etc.)
CREATE INDEX idx_canonical_activities ON "Entity" USING GIN (canonical_activities);
CREATE INDEX idx_canonical_roles ON "Entity" USING GIN (canonical_roles);
CREATE INDEX idx_canonical_place_types ON "Entity" USING GIN (canonical_place_types);

-- Full-text search on entity names
CREATE INDEX idx_entity_name_fts ON "Entity" USING GIN (to_tsvector('english', entity_name));
```

#### 5. Configure Backups

Supabase Pro:
- Daily automated backups (7-day retention)
- Point-in-time recovery (up to 30 days)

Manual Backup:
```bash
# Export database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore from backup
psql $DATABASE_URL < backup_20260208.sql
```

---

## CI/CD Pipeline

### Current State

**No automated CI/CD configured yet** (no `.github/workflows/` files or Vercel config).

### Recommended Setup (GitHub Actions + Vercel)

#### 1. Frontend CI/CD (Vercel)

**Automatic Deployment:**
- Push to `main` → production deployment
- Push to `develop` → staging deployment
- PR creation → preview deployment

**Quality Gates:**
```yaml
# .github/workflows/frontend-ci.yml
name: Frontend CI

on:
  pull_request:
    paths:
      - 'web/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 20
      - run: npm ci
        working-directory: web
      - run: npm run lint
        working-directory: web
      - run: npm run build
        working-directory: web
```

#### 2. Backend CI/CD (Google Cloud Build)

```yaml
# cloudbuild.yaml
steps:
  # Run tests
  - name: 'python:3.11'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        pip install -r requirements.txt
        pytest --cov=engine --cov-report=term

  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/engine:$SHORT_SHA', 'engine/']

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/engine:$SHORT_SHA']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'engine'
      - '--image=gcr.io/$PROJECT_ID/engine:$SHORT_SHA'
      - '--region=us-central1'
      - '--platform=managed'

images:
  - 'gcr.io/$PROJECT_ID/engine:$SHORT_SHA'
```

#### 3. Database Migrations (GitHub Actions)

```yaml
# .github/workflows/db-migrate.yml
name: Database Migration

on:
  push:
    branches:
      - main
    paths:
      - 'web/prisma/schema.prisma'
      - 'engine/config/schemas/*.yaml'

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 20
      - run: npm ci
        working-directory: web
      - run: npx prisma migrate deploy
        working-directory: web
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

---

## Monitoring & Observability

### Logging Strategy

**Frontend (Next.js):**
- **Development:** Console logs
- **Production:** Structured JSON logs to stdout (collected by Vercel)

**Backend (Python):**
- **Development:** Console logs with DEBUG level
- **Production:** Structured JSON logs with WARNING level

**Example Logging Configuration:**
```python
# engine/utils/logging.py
import logging
import json
import sys

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
```

### Error Tracking

**Recommended Tool:** Sentry

**Setup:**
```bash
# Frontend
npm install @sentry/nextjs

# Backend
pip install sentry-sdk
```

**Configuration:**
```typescript
// web/sentry.client.config.ts
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1, // 10% of transactions
  enabled: process.env.NODE_ENV === "production"
});
```

```python
# engine/utils/sentry.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("NODE_ENV"),
    traces_sample_rate=0.1
)
```

### Performance Monitoring

**Metrics to Track:**
- **Frontend:**
  - Core Web Vitals (LCP, FID, CLS)
  - Page load time
  - API response time
  - Error rate

- **Backend:**
  - Orchestration execution time
  - Extraction latency
  - LLM API latency
  - Database query time
  - Error rate by source

**Tools:**
- **Vercel Analytics:** Built-in Web Vitals tracking
- **Cloud Monitoring (GCP):** Backend metrics, logs, traces
- **Prisma Pulse (Future):** Database query performance monitoring

### Health Checks

**Frontend Health Check:**
```typescript
// web/app/api/health/route.ts
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET() {
  try {
    // Check database connectivity
    await prisma.$queryRaw`SELECT 1`;
    return NextResponse.json({ status: 'healthy', db: 'connected' });
  } catch (error) {
    return NextResponse.json(
      { status: 'unhealthy', db: 'disconnected', error: error.message },
      { status: 503 }
    );
  }
}
```

**Backend Health Check:**
```python
# engine/api/main.py
@app.get("/health")
async def health_check():
    # Check database
    try:
        await prisma.raw_query("SELECT 1")
        db_status = "connected"
    except:
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "version": "1.0.0"
    }
```

---

## Scaling Considerations

### Horizontal Scaling

**Frontend (Next.js on Vercel):**
- Automatically scales to handle traffic spikes
- Edge caching reduces origin load
- ISR reduces database queries

**Backend (Cloud Run):**
- Auto-scales from 0 to max instances (configurable)
- Each instance handles up to 300 concurrent requests
- Cold start optimization: Keep min 1 instance warm

**Database (Supabase):**
- Connection pooling handles up to 100 concurrent connections
- Read replicas for analytics/reporting workloads
- Vertical scaling: Upgrade to larger instance class

### Vertical Scaling Triggers

**Upgrade Backend Instances When:**
- Average extraction time exceeds 30 seconds
- Memory usage consistently above 80%
- Cold start time exceeds 10 seconds

**Upgrade Database When:**
- Connection pool saturation (>90% utilization)
- Query latency exceeds 200ms (p95)
- Storage approaching 80% capacity

### Cost Optimization

**Current Architecture Costs (Estimated Monthly):**
- **Supabase Free Tier:** $0 (500MB database, 2GB bandwidth)
- **Supabase Pro:** $25 (8GB database, 50GB bandwidth, 7-day backups)
- **Vercel Hobby:** $0 (100GB bandwidth)
- **Vercel Pro:** $20 (1TB bandwidth, better performance)
- **Anthropic Claude API:** Variable ($0.80 per 1M input tokens, $4 per 1M output tokens)
- **Google Places API:** $0-$200 (based on query volume)
- **Serper API:** $50/month (5,000 searches)

**Total Estimated Cost (Small Production):** $100-300/month

**Optimization Strategies:**
- Cache LLM extraction results (avoid redundant API calls)
- Use free-tier connectors (OSM, EventBrite) where possible
- Implement request deduplication at orchestration level
- Use ISR to minimize database queries

---

## Security Hardening

### API Key Management

**NEVER commit secrets to git:**
```bash
# Use environment variables only
DATABASE_URL=...
ANTHROPIC_API_KEY=...
```

**Secret Storage:**
- **Development:** `.env` file (gitignored)
- **Staging/Production:** Google Secret Manager, AWS Secrets Manager, or Vercel Environment Variables

### Database Security

**Connection Security:**
- Always use SSL/TLS connections (`?sslmode=require`)
- Use connection pooling to prevent exhaustion attacks
- Limit database user permissions (principle of least privilege)

**Row-Level Security (RLS):**
```sql
-- Example: Restrict entities by lens membership
ALTER TABLE "Entity" ENABLE ROW LEVEL SECURITY;

CREATE POLICY lens_access ON "Entity"
  FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM "LensEntity"
    WHERE "LensEntity"."entityId" = "Entity".id
      AND "LensEntity"."lensId" = current_setting('app.current_lens')
  ));
```

### Rate Limiting

**Frontend API Routes:**
```typescript
// web/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const rateLimitMap = new Map<string, number[]>();

export function middleware(request: NextRequest) {
  const ip = request.ip || 'unknown';
  const now = Date.now();
  const timestamps = rateLimitMap.get(ip) || [];

  // Allow 100 requests per minute
  const recentRequests = timestamps.filter(t => now - t < 60000);

  if (recentRequests.length >= 100) {
    return NextResponse.json({ error: 'Rate limit exceeded' }, { status: 429 });
  }

  recentRequests.push(now);
  rateLimitMap.set(ip, recentRequests);

  return NextResponse.next();
}
```

**Backend API (Cloud Run):**
- Use Cloud Armor for DDoS protection
- Configure per-IP rate limits at load balancer level

### CORS Configuration

```typescript
// web/next.config.js
module.exports = {
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: 'https://edinburghfinds.com' },
          { key: 'Access-Control-Allow-Methods', value: 'GET, POST, OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' }
        ]
      }
    ];
  }
};
```

---

## Troubleshooting

### Common Deployment Issues

#### 1. Database Connection Failures

**Symptoms:**
- `Error: P1001: Can't reach database server`
- `Connection pool timeout`

**Solutions:**
```bash
# Check DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql://USER:PASSWORD@HOST:5432/DB?schema=public

# Verify Supabase connection pooling
# Use port 6543 for PgBouncer: postgresql://...host.supabase.co:6543/postgres?pgbouncer=true

# Test connection manually
psql $DATABASE_URL -c "SELECT 1"
```

#### 2. Prisma Client Generation Failures

**Symptoms:**
- `Error: Prisma Client not found`
- `PrismaClient is unable to be run in the browser`

**Solutions:**
```bash
# Regenerate Prisma client
cd web
npx prisma generate

# Ensure schema.prisma is up-to-date
python -m engine.schema.generate --all

# Verify Prisma in dependencies
npm list @prisma/client
```

#### 3. Next.js Build Errors

**Symptoms:**
- `Module not found: Can't resolve '@/lib/prisma'`
- `Type error: Cannot find module`

**Solutions:**
```bash
# Clear Next.js cache
cd web
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Rebuild
npm run build
```

#### 4. Cloud Run Deployment Failures

**Symptoms:**
- `Container failed to start`
- `Health check failed`

**Solutions:**
```bash
# Check Cloud Run logs
gcloud run logs read engine --region=us-central1

# Test Docker image locally
docker run -p 8080:8080 \
  -e DATABASE_URL=$DATABASE_URL \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  gcr.io/PROJECT_ID/engine:latest

# Verify health endpoint
curl http://localhost:8080/health
```

#### 5. LLM Extraction Timeouts

**Symptoms:**
- `anthropic.APITimeoutError: Request timed out`
- `Extraction taking longer than expected`

**Solutions:**
```python
# Increase timeout in Instructor configuration
client = instructor.patch(
    anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")),
    timeout=60.0  # Increase from default 30s
)

# Reduce batch size in extraction
# Process entities in smaller chunks
```

### Debugging Checklist

**Pre-Deployment:**
- [ ] All tests passing (`pytest`, `npm run build`)
- [ ] Schema validation passes (`python -m engine.schema.generate --validate`)
- [ ] Environment variables configured (check Vercel/Cloud Run dashboard)
- [ ] Database migrations applied (`npx prisma migrate deploy`)
- [ ] API keys valid and not rate-limited

**Post-Deployment:**
- [ ] Health checks returning 200 OK
- [ ] Database connectivity verified
- [ ] Static assets loading from CDN
- [ ] API routes responding correctly
- [ ] Error tracking capturing exceptions (Sentry)

---

## Summary

The Universal Entity Extraction Engine deploys as a modern serverless application with three tiers:

1. **Frontend (Next.js on Vercel):** Global edge deployment with automatic scaling
2. **Backend (Python on Cloud Run):** Containerized orchestration engine with auto-scaling
3. **Database (PostgreSQL on Supabase):** Managed database with connection pooling and backups

**Key Strengths:**
- Zero-downtime deployments with preview environments
- Automatic scaling based on traffic
- Pay-per-use pricing (no idle costs)
- Built-in monitoring and error tracking
- Secure secret management

**Next Steps:**
1. Set up production Supabase instance
2. Configure Vercel project and environment variables
3. Create Google Cloud Run service
4. Implement CI/CD pipeline (GitHub Actions)
5. Configure monitoring (Sentry, Vercel Analytics)
6. Document runbooks for incident response

---

**Document Status:** Complete
**Last Validated:** 2026-02-08
**Review Cycle:** Quarterly or after major infrastructure changes
