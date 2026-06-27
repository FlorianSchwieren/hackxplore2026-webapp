# Baumpate Backend

FastAPI backend for the HackXplore Karlsruhe "Smart Watering for Urban Trees" demo.

## Quick Start

```bash
cp .env.example .env
uv sync --extra dev
make migrate
make seed
make run
```

The API is served under `/api/v1`; liveness is available at `GET /healthz` and
`GET /api/v1/healthz`.

Keep real Supabase values in `.env` only. Never commit the service role key or DB password.
