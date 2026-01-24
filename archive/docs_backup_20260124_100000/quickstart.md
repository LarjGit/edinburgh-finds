# Quickstart Guide

Audience: Developers.

Get the system running on your local machine in 10 minutes.

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

## Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-org/edinburgh_finds.git
    cd edinburgh_finds
    ```

2.  **Configure Environment**
    ```bash
    cp .env.example .env
    # Edit .env and add your DATABASE_URL and API Keys
    ```

3.  **Install Dependencies**
    ```bash
    # Python Engine
    pip install -r engine/requirements.txt

    # Frontend
    cd web
    npm install
    ```

4.  **Initialize Database**
    ```bash
    cd web
    npx prisma migrate dev
    ```

5.  **Run the App**
    ```bash
    npm run dev
    ```
    Visit `http://localhost:3000`.

Evidence: `docs/contributing.md`
