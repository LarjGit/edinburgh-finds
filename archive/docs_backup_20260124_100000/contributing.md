# Contributing Guide

Audience: New Contributors.

## Development Setup

1.  **Clone the repo**
    ```bash
    git clone <repo_url>
    ```

2.  **Environment Setup**
    - Copy `.env.example` to `.env`.
    - Fill in the required API keys.

3.  **Install Dependencies**
    - **Engine (Python)**:
      ```bash
      pip install -r engine/requirements.txt
      ```
    - **Web (Node)**:
      ```bash
      cd web
      npm install
      ```

4.  **Database**
    - Ensure Postgres is running.
    - Run migrations: `npx prisma migrate dev`.

## Code Style

- **Python**: Follows PEP 8. formatted via `black` or similar (check `pyproject.toml` if exists).
- **TypeScript**: Standard Prettier/ESLint configuration.

Evidence: `engine/requirements.txt`, `web/package.json`.
