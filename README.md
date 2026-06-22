# RunStats

RunStats is a local-first Python and React application for importing Garmin
running activities and health stats, storing them in SQLite, visualizing them in
a React UI, and asking grounded chatbot questions about the local data.

The current repository includes the Phase 5 experience from
`runstats-product-backlog.md`: FastAPI query APIs, SQLite persistence,
deterministic seed data, a React app shell, typed frontend API client,
dashboard, activity browsing and details, health trends, sync history, watch
settings, Bluetooth discovery through Bleak, and device capability probing.

## Repository Layout

```text
backend/
  runstats/
  tests/
frontend/
  src/
  tests/
data/
docs/
AGENT.md
runstats-design.md
runstats-product-backlog.md
```

Local data under `data/` is ignored by source control except for
`data/.gitkeep`.

## Prerequisites

- Python 3.12 or newer
- `uv`
- Node.js 20 or newer
- npm

## Install

For a step-by-step local development walkthrough, see
`docs/local-setup.md`.

```bash
npm run install:all
```

This installs backend dependencies through `uv` and frontend dependencies
through npm.

## Development

Run the backend development server:

```bash
cd backend
uv run uvicorn runstats.main:app --reload
```

The backend healthcheck is available at:

```text
GET /api/healthcheck
```

Run the frontend development server:

```bash
npm run frontend:dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000` by default. Set
`VITE_RUNSTATS_API_BASE_URL` only when serving the frontend from an origin that
can reach the backend directly.

Apply backend database migrations:

```bash
cd backend
uv run alembic upgrade head
```

Seed deterministic development data:

```bash
cd backend
uv run python -m runstats.db.seed
```

Set `RUNSTATS_DATABASE_PATH` to use a non-default SQLite file. The backend uses
the Bleak Bluetooth provider by default; set `RUNSTATS_WATCH_PROVIDER=fake` for
deterministic fake Garmin devices during development or tests.

## Validation

Run the full local validation suite:

```bash
npm run validate
```

Run backend validation only:

```bash
npm run backend:validate
```

Run frontend validation only:

```bash
npm run frontend:validate
```

The validation commands do not require a physical Garmin watch, live Bluetooth
device, hosted LLM, or local LLM runtime.
