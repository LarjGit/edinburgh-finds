# DEPLOYMENT.md

**Project:** Edinburgh Finds — Universal Entity Extraction Engine
**Generated:** 2026-02-08
**Status:** Production Deployment Guide

---

## Table of Contents

1. [Overview](#overview)
2. [Infrastructure Architecture](#infrastructure-architecture)
3. [Prerequisites](#prerequisites)
4. [Environment Variables](#environment-variables)
5. [Frontend Deployment (Next.js)](#frontend-deployment-nextjs)
6. [Backend Deployment (Python Engine)](#backend-deployment-python-engine)
7. [Database Setup (Supabase)](#database-setup-supabase)
8. [Monitoring and Observability](#monitoring-and-observability)
9. [CI/CD Pipeline](#cicd-pipeline)
10. [Scaling Strategies](#scaling-strategies)
11. [Security Hardening](#security-hardening)
12. [Disaster Recovery](#disaster-recovery)
13. [Cost Optimization](#cost-optimization)
14. [Troubleshooting](#troubleshooting)

---

## Overview

The Universal Entity Extraction Engine is a **vertical-agnostic discovery platform** that separates a universal Python-based **Entity Engine** from vertical-specific **Lens Layers** (YAML config). This deployment guide covers the production setup for both the frontend (Next.js 16) and backend (Python ETL pipeline) components.

### Deployment Strategy

- **Frontend:** Vercel (or alternative cloud platform with Next.js support)
- **Backend:** Cloud Run (Google Cloud), AWS Lambda, or Dockerized deployment
- **Database:** Supabase (managed PostgreSQL with connection pooling)
- **CDN:** Vercel Edge Network or Cloudflare
- **External Services:** Anthropic Claude API, Serper API, Google Places API, OpenStreetMap

### Architecture Principles

1. **Stateless Services:** Both frontend and backend are stateless for horizontal scaling
2. **Database-Centric State:** All state lives in PostgreSQL (Supabase)
3. **Edge Caching:** Pre-rendered pages cached at CDN edge locations (Next.js ISR)
4. **Async Pipeline:** ETL pipeline runs asynchronously with job queuing
5. **Secrets Management:** Centralized secret storage with environment-based injection

---

## Infrastructure Architecture

The deployment architecture follows a **three-tier model** with edge caching and external service integration:

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

### Key Components

#### Edge Layer
- **CDN:** Serves static assets (images, JS/CSS bundles, fonts) with global distribution
- **Edge Cache:** Next.js ISR (Incremental Static Regeneration) for pre-rendered pages

#### Frontend Tier
- **Next.js 16 App:** React 19 server components with App Router
- **Prisma Client:** Type-safe database queries with connection pooling

#### Backend Tier
- **Engine API:** FastAPI or Flask REST API for orchestration endpoints
- **Orchestration System:** Query planner, connector router, budget manager
- **Extraction Pipeline:** Parallel execution with LLM integration and deduplication
- **Prisma Client Python:** ORM layer for database operations

#### Database Tier
- **Primary Database:** Supabase PostgreSQL with Entity, RawIngestion, and ExtractedEntity tables
- **Connection Pooler:** PgBouncer for efficient connection management
- **Read Replica (Optional):** Query offloading and analytics workloads
- **Automated Backups:** Point-in-time recovery and daily snapshots

#### External Services
- **Anthropic Claude API:** Structured extraction via Instructor
- **Serper API:** Web search and entity discovery
- **Google Places API:** Place details and reviews
- **OpenStreetMap API:** Geospatial data (free tier)
- **Sport Scotland API:** Facilities data (public registry)
- **Custom Data Sources:** Vertical-specific scrapers and APIs

---

## Prerequisites

### Required Accounts

1. **Vercel Account** (for frontend hosting)
   - Sign up at https://vercel.com
   - Install Vercel CLI: `npm install -g vercel`

2. **Supabase Account** (for PostgreSQL database)
   - Sign up at https://supabase.com
   - Create a new project
   - Note down the `DATABASE_URL` connection string

3. **Google Cloud / AWS Account** (for backend hosting)
   - **Google Cloud:** Cloud Run for containerized backend
   - **AWS:** Lambda + API Gateway for serverless backend

4. **API Keys**
   - **Anthropic Claude API:** https://console.anthropic.com
   - **Serper API:** https://serper.dev
   - **Google Places API:** https://console.cloud.google.com

### Local Development Tools

```bash
# Frontend
Node.js >= 20.x
npm >= 10.x

# Backend
Python >= 3.10
pip >= 23.x
Docker >= 24.x (for containerization)

# Database
Prisma CLI: npm install -g prisma
```

---

## Environment Variables

### Shared Variables

These environment variables are required for both frontend and backend:

```bash
# Database Connection
DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public&pgbouncer=true&connection_limit=1"

# API Keys
ANTHROPIC_API_KEY="sk-ant-api03-..."
SERPER_API_KEY="your-serper-api-key"
GOOGLE_PLACES_API_KEY="your-google-places-api-key"

# Environment
NODE_ENV="production"
LOG_LEVEL="INFO"
```

### Frontend-Specific Variables

```bash
# Next.js Configuration
NEXT_PUBLIC_API_URL="https://api.edinburghfinds.com"
NEXT_PUBLIC_SITE_URL="https://edinburghfinds.com"

# Vercel Environment (auto-set)
VERCEL="1"
VERCEL_ENV="production"
VERCEL_URL="edinburghfinds.vercel.app"
```

### Backend-Specific Variables

```bash
# Engine Configuration
ENGINE_ENV="production"
MAX_WORKERS="10"
RATE_LIMIT_ANTHROPIC="50"  # requests per minute
RATE_LIMIT_SERPER="100"    # requests per minute

# Timeouts (seconds)
CONNECTOR_TIMEOUT="30"
EXTRACTION_TIMEOUT="60"
```

### Security Best Practices

1. **Never commit secrets** to version control
2. **Use `.env.example`** for documentation, `.env` for local values
3. **Rotate API keys** every 90 days
4. **Use secret managers** for production (Google Secret Manager, AWS Secrets Manager)
5. **Restrict database access** to specific IP ranges or VPC

---

## Frontend Deployment (Next.js)

### Step 1: Prepare Repository

Ensure your repository is configured for Vercel deployment:

```bash
# Navigate to web directory
cd web

# Verify build works locally
npm install
npm run build
npm run start  # Test production build locally

# Lint check
npm run lint
```

### Step 2: Configure Vercel Project

#### Option A: Vercel CLI Deployment

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy to preview environment
vercel

# Deploy to production
vercel --prod
```

#### Option B: Vercel Dashboard Deployment

1. Visit https://vercel.com/new
2. Import your GitHub repository
3. Configure project settings:
   - **Framework Preset:** Next.js
   - **Root Directory:** `web`
   - **Build Command:** `npm run build`
   - **Output Directory:** `.next` (auto-detected)
   - **Install Command:** `npm install`

### Step 3: Configure Environment Variables

In Vercel Dashboard → Settings → Environment Variables:

```bash
# Database
DATABASE_URL=postgresql://...?pgbouncer=true&connection_limit=1

# API Keys (encrypted by Vercel)
ANTHROPIC_API_KEY=sk-ant-api03-...
SERPER_API_KEY=...
GOOGLE_PLACES_API_KEY=...

# Public Variables
NEXT_PUBLIC_API_URL=https://api.edinburghfinds.com
NEXT_PUBLIC_SITE_URL=https://edinburghfinds.com

# Environment
NODE_ENV=production
LOG_LEVEL=INFO
```

**Important:** Mark sensitive variables as "Encrypted" in Vercel dashboard.

### Step 4: Generate Prisma Client

Vercel automatically runs Prisma generation during build. Ensure your `package.json` includes:

```json
{
  "scripts": {
    "postinstall": "prisma generate",
    "build": "next build"
  }
}
```

If using Prisma migrations, add a custom build script:

```json
{
  "scripts": {
    "vercel-build": "prisma generate && prisma migrate deploy && next build"
  }
}
```

### Step 5: Configure Domain

1. Go to Vercel Dashboard → Domains
2. Add your custom domain (e.g., `edinburghfinds.com`)
3. Configure DNS records:
   - **A Record:** Point to Vercel IP (provided in dashboard)
   - **CNAME Record:** `www` → `cname.vercel-dns.com`
4. Enable **Automatic HTTPS** (handled by Vercel)

### Step 6: Configure Incremental Static Regeneration (ISR)

For entity pages with ISR:

```typescript
// app/[slug]/page.tsx
export const revalidate = 3600; // Revalidate every 1 hour

export async function generateStaticParams() {
  const entities = await prisma.entity.findMany({
    select: { slug: true },
    take: 100, // Generate top 100 entities at build time
  });

  return entities.map((entity) => ({
    slug: entity.slug,
  }));
}
```

Configure in `next.config.js`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone', // For Docker deployment
  experimental: {
    isrMemoryCacheSize: 0, // Disable in-memory cache for Vercel Edge
  },
};

module.exports = nextConfig;
```

### Step 7: Monitoring and Logging

Vercel provides built-in monitoring. For enhanced observability:

1. **Enable Vercel Analytics:**
   ```bash
   npm install @vercel/analytics
   ```

   ```tsx
   // app/layout.tsx
   import { Analytics } from '@vercel/analytics/react';

   export default function RootLayout({ children }) {
     return (
       <html>
         <body>
           {children}
           <Analytics />
         </body>
       </html>
     );
   }
   ```

2. **Configure Error Tracking (Sentry):**
   ```bash
   npm install @sentry/nextjs
   ```

   ```javascript
   // sentry.client.config.js
   import * as Sentry from "@sentry/nextjs";

   Sentry.init({
     dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
     tracesSampleRate: 1.0,
     environment: process.env.VERCEL_ENV || 'development',
   });
   ```

### Step 8: Deploy and Verify

```bash
# Push to main branch (triggers auto-deployment)
git push origin main

# Or deploy manually
vercel --prod
```

**Verification Checklist:**
- [ ] Homepage loads at `https://edinburghfinds.com`
- [ ] Entity pages render correctly
- [ ] Database queries succeed
- [ ] No console errors in browser DevTools
- [ ] Lighthouse score > 90 (Performance, Accessibility, SEO)

---

## Backend Deployment (Python Engine)

The Python engine can be deployed using **Cloud Run** (Google Cloud), **AWS Lambda**, or **Docker** on any container platform. This guide covers all three approaches.

### Deployment Option A: Google Cloud Run (Recommended)

#### Step 1: Create Dockerfile

Create `engine/Dockerfile`:

```dockerfile
# ============================================================
# Edinburgh Finds Engine - Production Dockerfile
# ============================================================

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY engine/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install additional production dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    gunicorn \
    python-multipart

# Copy engine source code
COPY engine/ ./engine/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run FastAPI application
CMD ["uvicorn", "engine.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
```

#### Step 2: Create FastAPI Application

Create `engine/api/main.py`:

```python
"""
Edinburgh Finds Engine API
FastAPI application for orchestration and extraction endpoints.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import os

from engine.orchestration.cli import run_orchestration
from engine.extraction.cli import run_extraction_single

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Edinburgh Finds Engine API",
    description="Universal Entity Extraction Engine",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://edinburghfinds.com",
        "https://www.edinburghfinds.com",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request models
class OrchestrationRequest(BaseModel):
    query: str
    lens_id: str = "edinburgh_finds"
    budget: float = 1.0


class ExtractionRequest(BaseModel):
    raw_ingestion_id: str


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "service": "edinburgh-finds-engine",
        "version": "1.0.0",
    }


# Orchestration endpoint
@app.post("/api/orchestrate")
async def orchestrate_query(
    request: OrchestrationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Orchestrate a multi-source query.

    Returns immediately with a job_id. Client polls /api/status/{job_id}.
    """
    try:
        logger.info(f"Orchestration request: {request.query}")

        # Run orchestration in background
        job_id = f"orch_{request.query[:20]}_{os.urandom(4).hex()}"
        background_tasks.add_task(
            run_orchestration,
            query=request.query,
            lens_id=request.lens_id,
            budget=request.budget,
        )

        return {
            "status": "accepted",
            "job_id": job_id,
            "message": "Orchestration started",
        }
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Extraction endpoint
@app.post("/api/extract")
async def extract_entity(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks,
):
    """
    Extract structured entity from raw ingestion.

    Returns immediately with a job_id. Client polls /api/status/{job_id}.
    """
    try:
        logger.info(f"Extraction request: {request.raw_ingestion_id}")

        # Run extraction in background
        job_id = f"extr_{request.raw_ingestion_id}_{os.urandom(4).hex()}"
        background_tasks.add_task(
            run_extraction_single,
            raw_ingestion_id=request.raw_ingestion_id,
        )

        return {
            "status": "accepted",
            "job_id": job_id,
            "message": "Extraction started",
        }
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Status endpoint (future implementation with job queue)
@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """Check status of a background job."""
    # TODO: Implement job queue with Redis or database-backed queue
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Job queue not yet implemented",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

#### Step 3: Build and Push Docker Image

```bash
# Set project variables
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export SERVICE_NAME="edinburgh-finds-engine"

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Configure Docker for GCR
gcloud auth configure-docker

# Build Docker image
docker build -f engine/Dockerfile -t gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest .

# Push to Google Container Registry
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest
```

#### Step 4: Deploy to Cloud Run

```bash
# Deploy service
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "LOG_LEVEL=INFO,ENGINE_ENV=production" \
  --set-secrets "DATABASE_URL=database-url:latest,ANTHROPIC_API_KEY=anthropic-key:latest,SERPER_API_KEY=serper-key:latest,GOOGLE_PLACES_API_KEY=google-places-key:latest"

# Get service URL
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
```

#### Step 5: Configure Secrets (Google Secret Manager)

```bash
# Create secrets
echo -n "postgresql://..." | gcloud secrets create database-url --data-file=-
echo -n "sk-ant-api03-..." | gcloud secrets create anthropic-key --data-file=-
echo -n "your-serper-key" | gcloud secrets create serper-key --data-file=-
echo -n "your-google-key" | gcloud secrets create google-places-key --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding database-url \
  --member=serviceAccount:${SERVICE_ACCOUNT_EMAIL} \
  --role=roles/secretmanager.secretAccessor
```

#### Step 6: Test Deployment

```bash
# Get service URL
export SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

# Test health endpoint
curl ${SERVICE_URL}/health

# Test orchestration endpoint
curl -X POST ${SERVICE_URL}/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"query": "padel courts in Edinburgh", "lens_id": "edinburgh_finds"}'
```

---

### Deployment Option B: AWS Lambda + API Gateway

#### Step 1: Create Lambda Handler

Create `engine/lambda_handler.py`:

```python
"""
AWS Lambda handler for Edinburgh Finds Engine.
Uses Mangum to adapt FastAPI to Lambda.
"""

from mangum import Mangum
from engine.api.main import app

# Lambda handler
handler = Mangum(app, lifespan="off")
```

#### Step 2: Package Lambda Deployment

```bash
# Create deployment package
cd engine
pip install -t package/ -r requirements.txt
pip install -t package/ mangum fastapi uvicorn

# Add application code
cp -r engine/ package/
cp lambda_handler.py package/

# Create ZIP file
cd package
zip -r ../lambda_deployment.zip .
cd ..
```

#### Step 3: Deploy to AWS Lambda

```bash
# Set AWS variables
export AWS_REGION="us-east-1"
export LAMBDA_FUNCTION_NAME="edinburgh-finds-engine"
export LAMBDA_ROLE_ARN="arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role"

# Create Lambda function
aws lambda create-function \
  --function-name ${LAMBDA_FUNCTION_NAME} \
  --runtime python3.12 \
  --role ${LAMBDA_ROLE_ARN} \
  --handler lambda_handler.handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 300 \
  --memory-size 2048 \
  --environment Variables="{LOG_LEVEL=INFO,ENGINE_ENV=production}"

# Update Lambda environment variables (secrets from AWS Secrets Manager)
aws lambda update-function-configuration \
  --function-name ${LAMBDA_FUNCTION_NAME} \
  --environment Variables="{DATABASE_URL=$(aws secretsmanager get-secret-value --secret-id database-url --query SecretString --output text)}"
```

#### Step 4: Create API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
  --name "edinburgh-finds-api" \
  --description "Edinburgh Finds Engine API"

# Configure API Gateway integration with Lambda
# (Use AWS Console or CloudFormation for complex setup)
```

---

### Deployment Option C: Docker on Any Platform

#### Step 1: Build and Test Locally

```bash
# Build Docker image
docker build -f engine/Dockerfile -t edinburgh-finds-engine:latest .

# Run locally
docker run -p 8080:8080 \
  -e DATABASE_URL="postgresql://..." \
  -e ANTHROPIC_API_KEY="sk-ant-api03-..." \
  -e SERPER_API_KEY="..." \
  -e GOOGLE_PLACES_API_KEY="..." \
  edinburgh-finds-engine:latest

# Test health endpoint
curl http://localhost:8080/health
```

#### Step 2: Push to Container Registry

```bash
# Tag image
docker tag edinburgh-finds-engine:latest your-registry.com/edinburgh-finds-engine:latest

# Push to registry
docker push your-registry.com/edinburgh-finds-engine:latest
```

#### Step 3: Deploy to Kubernetes (Optional)

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edinburgh-finds-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: edinburgh-finds-engine
  template:
    metadata:
      labels:
        app: edinburgh-finds-engine
    spec:
      containers:
      - name: engine
        image: your-registry.com/edinburgh-finds-engine:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: anthropic
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2"
---
apiVersion: v1
kind: Service
metadata:
  name: edinburgh-finds-engine-service
spec:
  selector:
    app: edinburgh-finds-engine
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

Deploy to Kubernetes:

```bash
kubectl apply -f k8s/deployment.yaml
kubectl get services
```

---

## Database Setup (Supabase)

### Step 1: Create Supabase Project

1. Visit https://supabase.com/dashboard
2. Click "New Project"
3. Configure project:
   - **Name:** `edinburgh-finds-production`
   - **Database Password:** (generate strong password)
   - **Region:** Select closest to your users (e.g., `us-east-1`)
   - **Plan:** Pro or higher (for production workloads)

### Step 2: Configure Connection Pooling

Supabase uses **PgBouncer** for connection pooling. Use the pooled connection string:

```bash
# Pooled connection (use for Prisma and all application connections)
DATABASE_URL="postgresql://postgres.PROJECT_REF:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true&connection_limit=1"

# Direct connection (only for migrations)
DIRECT_URL="postgresql://postgres.PROJECT_REF:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
```

Update `web/prisma/schema.prisma`:

```prisma
datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_URL") // For migrations only
}
```

### Step 3: Run Prisma Migrations

```bash
# Generate Prisma client
cd web
npx prisma generate

# Run migrations (uses DIRECT_URL)
npx prisma migrate deploy

# Verify tables
npx prisma studio
```

### Step 4: Configure Database Indexes

Ensure these indexes exist for optimal query performance:

```sql
-- Entity table indexes (already in Prisma schema)
CREATE INDEX IF NOT EXISTS "Entity_entity_name_idx" ON "Entity"("entity_name");
CREATE INDEX IF NOT EXISTS "Entity_entity_class_idx" ON "Entity"("entity_class");
CREATE INDEX IF NOT EXISTS "Entity_city_idx" ON "Entity"("city");
CREATE INDEX IF NOT EXISTS "Entity_postcode_idx" ON "Entity"("postcode");
CREATE INDEX IF NOT EXISTS "Entity_latitude_longitude_idx" ON "Entity"("latitude", "longitude");

-- GIN indexes for array columns (critical for performance)
CREATE INDEX IF NOT EXISTS "Entity_canonical_activities_idx" ON "Entity" USING GIN ("canonical_activities");
CREATE INDEX IF NOT EXISTS "Entity_canonical_roles_idx" ON "Entity" USING GIN ("canonical_roles");
CREATE INDEX IF NOT EXISTS "Entity_canonical_place_types_idx" ON "Entity" USING GIN ("canonical_place_types");
CREATE INDEX IF NOT EXISTS "Entity_canonical_access_idx" ON "Entity" USING GIN ("canonical_access");

-- JSONB indexes for modules
CREATE INDEX IF NOT EXISTS "Entity_modules_idx" ON "Entity" USING GIN ("modules");
```

### Step 5: Configure Backups

Supabase Pro includes automatic backups. Configure additional settings:

1. Go to **Database → Backups**
2. Enable **Point-in-Time Recovery (PITR)** (7-day retention)
3. Schedule **Daily Snapshots** (30-day retention)
4. Download manual backup for disaster recovery:

```bash
# Export database backup
pg_dump -h aws-0-us-east-1.pooler.supabase.com \
  -U postgres.PROJECT_REF \
  -d postgres \
  -F c \
  -f edinburgh_finds_backup_$(date +%Y%m%d).dump
```

### Step 6: Configure Database Monitoring

Supabase provides built-in monitoring. Set up alerts:

1. Go to **Database → Monitoring**
2. Configure alerts for:
   - **Connection count** > 80% of pool size
   - **Query duration** > 5 seconds
   - **Database size** > 80% of plan limit
   - **Replication lag** > 30 seconds

---

## Monitoring and Observability

### Application Logging

#### Frontend (Next.js)

Use structured logging with Winston or Pino:

```typescript
// lib/logger.ts
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
    },
  },
});

// Usage
logger.info({ userId: '123', action: 'view_entity' }, 'User viewed entity');
```

#### Backend (Python)

Use Python's `logging` module:

```python
# engine/utils/logger.py
import logging
import os

def setup_logger(name: str) -> logging.Logger:
    """Configure structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

# Usage
logger = setup_logger(__name__)
logger.info(f"Orchestration started for query: {query}")
```

### Error Tracking (Sentry)

#### Frontend Integration

```bash
npm install @sentry/nextjs
npx @sentry/wizard -i nextjs
```

```typescript
// sentry.client.config.ts
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 1.0,
  environment: process.env.VERCEL_ENV || 'development',
  integrations: [
    new Sentry.BrowserTracing(),
    new Sentry.Replay(),
  ],
});
```

#### Backend Integration

```bash
pip install sentry-sdk
```

```python
# engine/api/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
    environment=os.getenv("ENGINE_ENV", "development"),
)
```

### Performance Monitoring

#### Application Performance Monitoring (APM)

Use **New Relic**, **Datadog**, or **Grafana Cloud** for APM:

```python
# New Relic integration
import newrelic.agent
newrelic.agent.initialize('newrelic.ini')

app = newrelic.agent.wsgi_application()(app)
```

#### Database Query Monitoring

Use **Prisma Pulse** or **pganalyze** for PostgreSQL monitoring:

```bash
# Install pganalyze collector (for Supabase)
# Configure in Supabase dashboard → Database → Query Insights
```

### Uptime Monitoring

Use **UptimeRobot**, **Pingdom**, or **BetterUptime**:

1. Monitor frontend: `https://edinburghfinds.com`
2. Monitor backend health: `https://api.edinburghfinds.com/health`
3. Monitor database: Supabase built-in monitoring

Configure alerts:
- Email notifications for downtime
- Slack/Discord webhooks for critical errors
- PagerDuty for on-call rotation

---

## CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  # Test job (runs first)
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Python dependencies
        run: |
          pip install -r engine/requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run Engine Tests
        run: |
          pytest engine/tests/ -v --cov=engine --cov-report=term-missing

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Node dependencies
        working-directory: web
        run: npm ci

      - name: Run Frontend Lint
        working-directory: web
        run: npm run lint

      - name: Build Frontend
        working-directory: web
        run: npm run build
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

  # Deploy frontend to Vercel
  deploy-frontend:
    name: Deploy Frontend
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
          working-directory: web

  # Deploy backend to Cloud Run
  deploy-backend:
    name: Deploy Backend
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker

      - name: Build Docker image
        run: |
          docker build -f engine/Dockerfile -t gcr.io/${{ secrets.GCP_PROJECT_ID }}/edinburgh-finds-engine:${{ github.sha }} .
          docker tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/edinburgh-finds-engine:${{ github.sha }} gcr.io/${{ secrets.GCP_PROJECT_ID }}/edinburgh-finds-engine:latest

      - name: Push Docker image
        run: |
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/edinburgh-finds-engine:${{ github.sha }}
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/edinburgh-finds-engine:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy edinburgh-finds-engine \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/edinburgh-finds-engine:latest \
            --platform managed \
            --region us-central1 \
            --allow-unauthenticated \
            --memory 2Gi \
            --cpu 2 \
            --timeout 300

  # Run database migrations
  migrate-database:
    name: Run Database Migrations
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        working-directory: web
        run: npm ci

      - name: Run Prisma Migrations
        working-directory: web
        run: npx prisma migrate deploy
        env:
          DIRECT_URL: ${{ secrets.DIRECT_DATABASE_URL }}
```

### Required GitHub Secrets

Configure in **Settings → Secrets and Variables → Actions**:

```bash
# Vercel
VERCEL_TOKEN="your-vercel-token"
VERCEL_ORG_ID="your-org-id"
VERCEL_PROJECT_ID="your-project-id"

# Google Cloud
GCP_SA_KEY="your-service-account-json"
GCP_PROJECT_ID="your-project-id"

# Database
DATABASE_URL="postgresql://...?pgbouncer=true"
DIRECT_DATABASE_URL="postgresql://...direct-connection"

# API Keys
ANTHROPIC_API_KEY="sk-ant-api03-..."
SERPER_API_KEY="your-serper-key"
GOOGLE_PLACES_API_KEY="your-google-key"
```

### Deploy Previews

Vercel automatically creates deploy previews for pull requests. Configure in `.github/workflows/preview.yml`:

```yaml
name: Deploy Preview

on:
  pull_request:
    branches: [ main ]

jobs:
  deploy-preview:
    name: Deploy Preview
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Vercel (Preview)
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: web
          alias-domains: pr-${{ github.event.pull_request.number }}.edinburghfinds.com
```

---

## Scaling Strategies

### Frontend Scaling (Vercel)

Vercel automatically scales Next.js applications:

- **Edge Network:** Automatic global CDN distribution
- **Serverless Functions:** Auto-scales to zero, handles spikes
- **ISR Caching:** Reduces database load with incremental static regeneration

**Optimization Tips:**

1. **Use ISR for entity pages:**
   ```typescript
   export const revalidate = 3600; // 1 hour
   ```

2. **Implement infinite scroll pagination:**
   ```typescript
   // Avoid: await prisma.entity.findMany() (loads all)
   // Use: Cursor-based pagination with take/skip
   ```

3. **Enable Vercel Edge Config** for dynamic feature flags

### Backend Scaling (Cloud Run)

Cloud Run automatically scales based on traffic:

```bash
# Configure autoscaling
gcloud run services update edinburgh-finds-engine \
  --min-instances 1 \
  --max-instances 100 \
  --concurrency 80 \
  --cpu-throttling \
  --memory 2Gi \
  --cpu 2
```

**Scaling Configuration:**

- **Min Instances:** Keep 1-2 instances warm to avoid cold starts
- **Max Instances:** Set to 100 for high-traffic scenarios
- **Concurrency:** 80 requests per container (adjust based on workload)
- **CPU Throttling:** Enabled to save costs during idle periods

**Optimization Tips:**

1. **Use connection pooling:**
   ```python
   # Prisma Client Python uses connection pooling by default
   # Ensure DATABASE_URL includes pgbouncer=true
   ```

2. **Implement request queuing:**
   ```python
   # Use Celery or Redis Queue for long-running tasks
   ```

3. **Cache expensive queries:**
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=100)
   def get_entity_by_slug(slug: str):
       return prisma.entity.find_unique(where={"slug": slug})
   ```

### Database Scaling (Supabase)

Supabase PostgreSQL can scale vertically and horizontally:

#### Vertical Scaling

1. Upgrade plan in Supabase Dashboard
2. Options:
   - **Pro:** 8GB RAM, 2 vCPU
   - **Team:** 16GB RAM, 4 vCPU
   - **Enterprise:** Custom sizing

#### Horizontal Scaling (Read Replicas)

```bash
# Enable read replicas in Supabase Dashboard
# Update connection strings:

# Write operations (primary)
DATABASE_URL="postgresql://...primary..."

# Read operations (replica)
DATABASE_READ_REPLICA_URL="postgresql://...replica..."
```

Configure Prisma to use replicas:

```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// Read-only client (future implementation)
datasource dbReplica {
  provider = "postgresql"
  url      = env("DATABASE_READ_REPLICA_URL")
}
```

#### Connection Pooling Tuning

```bash
# Configure PgBouncer pool size
# Supabase default: 15 connections per client
# Adjust in Supabase Dashboard → Database → Connection Pooling

# Set connection_limit in DATABASE_URL
DATABASE_URL="postgresql://...?pgbouncer=true&connection_limit=1"
```

### Rate Limiting

Implement rate limiting for external API calls:

```python
# engine/utils/rate_limiter.py
import time
from collections import defaultdict

class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def allow_request(self, key: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()

        # Remove old requests outside window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < self.window_seconds
        ]

        # Check if under limit
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True

        return False

# Usage
anthropic_limiter = RateLimiter(max_requests=50, window_seconds=60)

if not anthropic_limiter.allow_request("anthropic"):
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

---

## Security Hardening

### API Key Rotation

Implement 90-day rotation schedule:

1. **Generate new API keys** in respective provider dashboards
2. **Add new keys** to secret manager with versioning
3. **Deploy applications** with new keys
4. **Verify functionality** in production
5. **Revoke old keys** after 24-hour grace period

```bash
# Example: Rotate Anthropic API key
gcloud secrets versions add anthropic-key --data-file=new_key.txt

# Update Cloud Run to use latest version
gcloud run services update edinburgh-finds-engine \
  --set-secrets "ANTHROPIC_API_KEY=anthropic-key:latest"
```

### HTTPS Enforcement

Vercel and Cloud Run enforce HTTPS by default. For custom domains:

1. **Vercel:** Automatic HTTPS with Let's Encrypt
2. **Cloud Run:** Automatic HTTPS for `*.run.app` domains
3. **Custom Domain:** Configure Cloud Load Balancer with SSL certificate

### Database Security

1. **Enable SSL/TLS:** Supabase enforces SSL by default
2. **IP Whitelisting:** Restrict database access to Cloud Run VPC
3. **Connection Pooling:** Use PgBouncer to prevent connection exhaustion attacks
4. **Row-Level Security (RLS):** Enable for user-facing tables

```sql
-- Example RLS policy (if implementing user authentication)
ALTER TABLE "Entity" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public entities are viewable by everyone"
  ON "Entity"
  FOR SELECT
  USING (true);
```

### API Rate Limiting

Implement rate limiting on API Gateway or Cloud Run:

```python
# FastAPI rate limiting middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/orchestrate")
@limiter.limit("10/minute")
async def orchestrate_query(request: Request):
    ...
```

### Input Validation

Use Pydantic for strict input validation:

```python
from pydantic import BaseModel, Field, validator

class OrchestrationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    lens_id: str = Field("edinburgh_finds", regex=r"^[a-z_]+$")
    budget: float = Field(1.0, ge=0.1, le=10.0)

    @validator("query")
    def sanitize_query(cls, v):
        """Remove potentially harmful characters."""
        return v.replace("<", "").replace(">", "").strip()
```

### Secrets Management Best Practices

1. **Never commit secrets** to version control
2. **Use secret managers:** Google Secret Manager, AWS Secrets Manager, HashiCorp Vault
3. **Rotate secrets quarterly**
4. **Audit access logs** for secret retrieval
5. **Encrypt secrets at rest** (handled by secret managers)

---

## Disaster Recovery

### Backup Strategy

#### Database Backups

Supabase Pro includes:
- **Point-in-Time Recovery (PITR):** 7-day retention
- **Daily Snapshots:** 30-day retention

Manual backup schedule:

```bash
# Weekly full backup (cron job)
#!/bin/bash
DATE=$(date +%Y%m%d)
pg_dump -h aws-0-us-east-1.pooler.supabase.com \
  -U postgres.PROJECT_REF \
  -d postgres \
  -F c \
  -f "/backups/edinburgh_finds_${DATE}.dump"

# Upload to S3
aws s3 cp "/backups/edinburgh_finds_${DATE}.dump" \
  s3://edinburgh-finds-backups/db/

# Retain for 90 days
aws s3 ls s3://edinburgh-finds-backups/db/ \
  | awk '{if($1 < "'$(date -d '90 days ago' +%Y-%m-%d)'") print $4}' \
  | xargs -I {} aws s3 rm s3://edinburgh-finds-backups/db/{}
```

#### Application Backups

Version control serves as application backup. Tag releases:

```bash
git tag -a v1.0.0 -m "Production release v1.0.0"
git push origin v1.0.0
```

### Recovery Procedures

#### Scenario 1: Database Corruption

```bash
# Restore from PITR
# In Supabase Dashboard → Database → Backups → Restore

# Or restore from manual backup
pg_restore -h aws-0-us-east-1.pooler.supabase.com \
  -U postgres.PROJECT_REF \
  -d postgres \
  -F c \
  "/backups/edinburgh_finds_20260208.dump"
```

#### Scenario 2: Failed Deployment

```bash
# Rollback Cloud Run deployment
gcloud run services update-traffic edinburgh-finds-engine \
  --to-revisions PREVIOUS_REVISION=100

# Rollback Vercel deployment
vercel rollback <deployment-url>
```

#### Scenario 3: Data Loss

```bash
# Restore entities from ExtractedEntity table
# (The extraction pipeline is idempotent)
python -m engine.orchestration.entity_finalizer --rebuild
```

### Recovery Time Objective (RTO) and Recovery Point Objective (RPO)

- **RTO (Frontend):** < 5 minutes (Vercel rollback)
- **RTO (Backend):** < 10 minutes (Cloud Run rollback)
- **RTO (Database):** < 30 minutes (PITR restore)
- **RPO (Database):** < 1 minute (PITR continuous archiving)
- **RPO (Application):** 0 (version control)

---

## Cost Optimization

### Frontend Costs (Vercel)

**Vercel Pro Pricing:**
- **Base:** $20/month per team member
- **Bandwidth:** $40/TB beyond 1TB included
- **Function Executions:** $40/million beyond 1 million included
- **ISR Prerendering:** Included

**Optimization Strategies:**

1. **Maximize ISR usage** to reduce function executions
2. **Optimize images** with Next.js Image component (auto-optimization)
3. **Use Edge Functions** for faster responses and lower costs
4. **Enable caching headers** for static assets

### Backend Costs (Cloud Run)

**Google Cloud Run Pricing:**
- **CPU:** $0.00002400 per vCPU-second
- **Memory:** $0.00000250 per GiB-second
- **Requests:** $0.40 per million requests
- **Free Tier:** 2 million requests/month, 360,000 GiB-seconds/month

**Monthly Cost Estimate (10,000 requests/day):**
```
Requests: 300,000 requests/month = $0.12
CPU: 300,000 requests × 2 sec/request × 2 vCPU × $0.000024 = $28.80
Memory: 300,000 requests × 2 sec/request × 2 GiB × $0.0000025 = $3.00
Total: ~$32/month
```

**Optimization Strategies:**

1. **Reduce cold starts:** Keep min-instances=1
2. **Optimize request duration:** Cache queries, use efficient algorithms
3. **Use CPU throttling** to save costs during idle periods
4. **Batch operations** instead of individual API calls

### Database Costs (Supabase)

**Supabase Pro Pricing:**
- **Base:** $25/month
- **Includes:** 8GB database, 100GB bandwidth, 50GB storage
- **Overage:** $0.125/GB storage, $0.09/GB bandwidth

**Optimization Strategies:**

1. **Archive old RawIngestion records** (> 90 days)
2. **Vacuum database regularly** to reclaim space
3. **Use connection pooling** to reduce connection overhead
4. **Index optimization** to reduce query costs

```sql
-- Archive old raw ingestions
DELETE FROM "RawIngestion"
WHERE "createdAt" < NOW() - INTERVAL '90 days';

-- Vacuum database
VACUUM FULL;
```

### External API Costs

**Anthropic Claude API:**
- **Claude Sonnet 4.5:** $3.00 per million input tokens, $15.00 per million output tokens
- **Monthly Budget:** Set limits in orchestration budget manager

**Serper API:**
- **Free Tier:** 2,500 searches/month
- **Pro:** $50/month for 30,000 searches

**Google Places API:**
- **Free Tier:** $200 credit/month
- **Place Details:** $0.017 per request

**Optimization Strategies:**

1. **Cache API responses** in database (RawIngestion table)
2. **Implement request deduplication** to avoid redundant calls
3. **Use budget manager** to cap API spending
4. **Prefer free data sources** (OSM, Sport Scotland) when possible

---

## Troubleshooting

### Common Issues

#### Issue 1: Database Connection Errors

**Symptom:**
```
Error: P1001: Can't reach database server at `aws-0-us-east-1.pooler.supabase.com`
```

**Solutions:**

1. **Check DATABASE_URL format:**
   ```bash
   # Correct format with pgbouncer
   DATABASE_URL="postgresql://postgres.PROJECT_REF:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true&connection_limit=1"
   ```

2. **Verify connection pooling:**
   ```bash
   # Test connection
   psql "postgresql://postgres.PROJECT_REF:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
   ```

3. **Check Supabase status:**
   - Visit https://status.supabase.com
   - Check Supabase Dashboard → Database → Connection Info

#### Issue 2: Vercel Build Failures

**Symptom:**
```
Error: Command "prisma generate" timed out after 5 minutes
```

**Solutions:**

1. **Increase build timeout** in `vercel.json`:
   ```json
   {
     "buildCommand": "prisma generate && next build",
     "framework": "nextjs",
     "installCommand": "npm ci"
   }
   ```

2. **Use cached Prisma client:**
   ```json
   {
     "cacheDirectories": ["node_modules/.prisma"]
   }
   ```

3. **Check DATABASE_URL availability** during build (required for Prisma)

#### Issue 3: Cloud Run Cold Starts

**Symptom:**
```
First request after idle period takes 10+ seconds
```

**Solutions:**

1. **Set min-instances=1:**
   ```bash
   gcloud run services update edinburgh-finds-engine --min-instances 1
   ```

2. **Optimize Docker image size:**
   ```dockerfile
   # Use slim base image
   FROM python:3.12-slim

   # Multi-stage build to reduce size
   FROM python:3.12 AS builder
   RUN pip install --no-cache-dir -r requirements.txt

   FROM python:3.12-slim
   COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
   ```

3. **Implement health check warming:**
   ```bash
   # Cron job to keep instance warm
   */5 * * * * curl https://api.edinburghfinds.com/health
   ```

#### Issue 4: Rate Limit Errors from External APIs

**Symptom:**
```
AnthropicError: rate_limit_error: Rate limit exceeded
```

**Solutions:**

1. **Implement exponential backoff:**
   ```python
   import time
   from anthropic import RateLimitError

   def call_anthropic_with_retry(prompt, max_retries=3):
       for attempt in range(max_retries):
           try:
               return client.completions.create(prompt=prompt)
           except RateLimitError:
               wait_time = 2 ** attempt
               time.sleep(wait_time)
       raise Exception("Max retries exceeded")
   ```

2. **Use budget manager** to limit concurrent requests:
   ```python
   # engine/orchestration/budget_manager.py
   max_concurrent_requests = 5
   semaphore = asyncio.Semaphore(max_concurrent_requests)
   ```

3. **Cache responses** in RawIngestion table to avoid redundant API calls

#### Issue 5: Slow Database Queries

**Symptom:**
```
Query took 5+ seconds to execute
```

**Solutions:**

1. **Check missing indexes:**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM "Entity" WHERE "city" = 'Edinburgh';
   ```

2. **Add GIN indexes for array queries:**
   ```sql
   CREATE INDEX "Entity_canonical_activities_idx" ON "Entity" USING GIN ("canonical_activities");
   ```

3. **Use connection pooling:**
   ```bash
   DATABASE_URL="...?pgbouncer=true&connection_limit=1"
   ```

4. **Enable query logging** in Supabase Dashboard → Database → Query Insights

### Debugging Commands

```bash
# Frontend (Next.js)
cd web
npm run build  # Test build locally
npm run start  # Test production build

# Backend (Python)
cd engine
pytest -v  # Run tests
python -m engine.api.main  # Run locally

# Docker
docker build -f engine/Dockerfile -t test .
docker run -p 8080:8080 test
curl http://localhost:8080/health

# Database
psql $DATABASE_URL  # Connect to database
\dt  # List tables
\d "Entity"  # Describe Entity table

# Cloud Run
gcloud run services describe edinburgh-finds-engine --region us-central1
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=edinburgh-finds-engine" --limit 50
```

### Monitoring Dashboards

1. **Vercel Dashboard:** https://vercel.com/your-team/edinburgh-finds
   - Real-time function logs
   - Performance analytics
   - Error tracking

2. **Cloud Run Logs:** https://console.cloud.google.com/run
   - Request logs
   - Error logs
   - Performance metrics

3. **Supabase Dashboard:** https://supabase.com/dashboard/project/PROJECT_REF
   - Query performance
   - Connection pool status
   - Database size

4. **Sentry Dashboard:** https://sentry.io/organizations/your-org/issues
   - Error tracking
   - Performance monitoring
   - User feedback

---

## Appendix

### Deployment Checklist

Use this checklist before production deployment:

#### Pre-Deployment

- [ ] All tests pass locally (`pytest`, `npm run build`)
- [ ] Linting passes (`npm run lint`)
- [ ] Environment variables configured in secret manager
- [ ] Database migrations tested in staging environment
- [ ] API keys validated and working
- [ ] Connection pooling configured correctly
- [ ] Backup strategy tested (restore from backup)

#### Deployment

- [ ] Frontend deployed to Vercel (or alternative)
- [ ] Backend deployed to Cloud Run (or alternative)
- [ ] Database migrations applied (`prisma migrate deploy`)
- [ ] Health checks passing (`/health` endpoints)
- [ ] SSL certificates valid and auto-renewing
- [ ] Custom domains configured and DNS propagated

#### Post-Deployment

- [ ] Smoke tests pass (manual testing of key flows)
- [ ] Monitoring dashboards configured (Sentry, New Relic)
- [ ] Uptime monitoring active (UptimeRobot)
- [ ] Error alerts configured (email, Slack)
- [ ] Performance baselines recorded (Lighthouse scores)
- [ ] Documentation updated (DEPLOYMENT.md, CHANGELOG.md)

### Environment-Specific Configuration

#### Development

```bash
NODE_ENV=development
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://localhost:5432/edinburgh_finds_dev
ANTHROPIC_API_KEY=sk-ant-api03-...
```

#### Staging

```bash
NODE_ENV=staging
LOG_LEVEL=INFO
DATABASE_URL=postgresql://...staging.supabase.com...
ANTHROPIC_API_KEY=sk-ant-api03-...
VERCEL_ENV=preview
```

#### Production

```bash
NODE_ENV=production
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://...production.supabase.com...
ANTHROPIC_API_KEY=sk-ant-api03-...
VERCEL_ENV=production
```

### Additional Resources

- **Next.js Deployment:** https://nextjs.org/docs/deployment
- **Vercel Documentation:** https://vercel.com/docs
- **Google Cloud Run:** https://cloud.google.com/run/docs
- **Supabase Documentation:** https://supabase.com/docs
- **Prisma Deployment:** https://www.prisma.io/docs/guides/deployment
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment

---

**End of DEPLOYMENT.md**
**Generated:** 2026-02-08
**Maintained by:** Edinburgh Finds Team
**Contact:** [Your contact information]
