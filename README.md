# RunStats

RunStats is a local-first Python and React application for importing Garmin
running activities and health stats, storing them in SQLite, visualizing them in
a React UI, and asking grounded chatbot questions about the local data.

The current repository includes the Phase 10 local-first experience from
`runstats-product-backlog.md`: FastAPI query APIs, SQLite persistence,
deterministic seed data, a React app shell, typed frontend API client,
dashboard, activity browsing and details, health trends, sync history, watch
settings, Bluetooth discovery through Bleak, device capability probing, FIT
activity import, normalized health payload import, and a grounded Chat
Assistant backed by approved read-only tools, plus local data export/delete
controls and a production local app startup path.

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

The Chat Assistant defaults to an Ollama-compatible local model endpoint at
`http://127.0.0.1:11434` with model `llama3.2`. See
`docs/chat-assistant.md` for provider settings and safety notes.

## Local App Package

Build the production frontend and backend package artifacts:

```bash
npm run package:local
```

Start the combined local app, which applies migrations and serves
`frontend/dist` through FastAPI:

```bash
npm run start:local
```

See `docs/local-desktop-package.md` for package details and
`docs/privacy-and-data-management.md` for export, delete, and hosted-privacy
notes.

## Validation

Run the full local validation suite:

```bash
npm run validate
```

Install the Playwright browser once, then run browser-level end-to-end
validation:

```bash
npm run e2e:install
npm run e2e
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

For real-device validation with Bleak and a local Ollama `gemma2` model, follow
`docs/local-setup.md`.
