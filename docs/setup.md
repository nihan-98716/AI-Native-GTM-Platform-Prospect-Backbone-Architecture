# Setup & Installation

## Requirements

- **Docker:** Version 20.10+
- **Docker Compose:** Version 2.0+
- **OpenAI API Key:** Required for agent workflows.
- **Apollo API Key:** (Optional) Required for live enrichment and sourcing runs.

## Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Environment Configuration:**
    Copy the example environment file and fill in your secrets.
    ```bash
    cp infra/env.example .env
    ```
    *Note: At a minimum, `OPENAI_API_KEY` must be provided in the `.env` file for the agent workflows to function.*

## One-Command Startup

The entire platform can be started with a single command:

```bash
docker compose up --build
```

This command will:
1.  Start the PostgreSQL and Redis services.
2.  Build and start the Backend (FastAPI).
3.  Build and start the Frontend (Next.js).
4.  Start the background Worker process.
5.  Run database migrations and seed the demo environment.

## Accessing the Platform

- **Frontend UI:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

## Demo Login Process

The platform is pre-seeded with a demo tenant and user. Authentication is handled via JWT.

1.  Open the Frontend UI.
2.  The system will automatically use a pre-issued demo token for the `acme` tenant.
3.  If you need to generate a new token or test RBAC, use the `/v1/auth/token` endpoint in the API Docs.

## Seeded Environment

Upon startup, the system automatically seeds the following (via `backbone/app/seed/`):
- **Tenant:** `acme` (slug: `acme-corp`)
- **User:** `admin@acme.corp` (roles: `admin`)
- **Data:** A set of demo accounts, contacts, and signals to allow immediate testing of the Prospecting vertical slice without needing external API keys.

To disable auto-seeding, set `AUTO_SEED_ON_STARTUP=false` in your `.env` file.
