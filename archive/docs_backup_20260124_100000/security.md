# Security

Audience: Security Engineers and Developers.

## Authentication & Authorization

- **Database**: Secured via standard PostgreSQL authentication (User/Password) in the connection string.
- **API Keys**: All external service keys (Anthropic, Google, Serper) are stored in environment variables and never committed to code.

Evidence: `.env.example`, `.gitignore`.

## Data Protection

- **Sensitive Data**: The application currently focuses on public data (venues, events). No PII beyond public business contact info is targeted.
- **Input Validation**: All data entering the system is validated via Pydantic models (Engine) or Zod/Typescript (Web).

## Secrets Management

Secrets are managed via `.env` files locally and platform-specific secret managers (e.g., Vercel Environment Variables) in production.

Evidence: `web/README.md` (Deploy on Vercel section).
