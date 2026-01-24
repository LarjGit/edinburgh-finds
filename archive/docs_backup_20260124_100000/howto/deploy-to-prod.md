# How to Deploy to Production

Audience: DevOps.

## Frontend (Vercel)

1.  **Connect Repo**: Link your GitHub repo to Vercel.
2.  **Environment Variables**: Add all variables from `.env` to Vercel Project Settings.
3.  **Build Command**: `npm run build` (Next.js default).
4.  **Output Directory**: `.next` (Next.js default).

## Database

1.  **Provision**: Set up a managed Postgres (e.g., Supabase, Neon, RDS).
2.  **Migrate**:
    ```bash
    # From your local machine or CI/CD
    DATABASE_URL=<prod_url> npx prisma migrate deploy
    ```

Evidence: `web/README.md`
