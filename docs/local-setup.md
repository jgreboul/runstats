# Local Setup

This guide helps a new engineer run RunStats locally from a fresh checkout.
RunStats has two local services:

- A FastAPI backend in `backend/`
- A Vite React frontend in `frontend/`

The backend stores local data in SQLite under `data/` by default. The frontend
uses the Vite dev server and proxies API requests to the backend.

## Prerequisites

Install these before starting:

- Python 3.12 or newer
- `uv`
- Node.js 20 or newer
- npm
- Git

Check the basics:

```bash
python --version
uv --version
node --version
npm --version
```

## First Install

From the repository root:

```bash
npm run install:all
```

This installs backend dependencies with `uv` and frontend dependencies with
npm.

## Configure Local Watch Behavior

For day-to-day development without a physical Garmin watch, use the fake watch
provider:

```bash
$env:RUNSTATS_WATCH_PROVIDER="fake"
```

For macOS or Linux shells:

```bash
export RUNSTATS_WATCH_PROVIDER=fake
```

The fake provider returns deterministic Garmin Forerunner devices and lets the
Watch Settings screen scan, pair, test connection, probe capabilities, and run
mock sync flows without Bluetooth hardware.

To use real local Bluetooth discovery, leave `RUNSTATS_WATCH_PROVIDER` unset or
set it to `bleak`. The Bleak provider requires Bluetooth to be enabled and may
require operating-system permission for local device access.

## Prepare the Database

Apply migrations:

```bash
cd backend
uv run alembic upgrade head
```

Seed representative development data:

```bash
uv run python -m runstats.db.seed
```

Return to the repository root before starting both services:

```bash
cd ..
```

## Run the Backend

Open terminal 1 at the repository root:

```bash
cd backend
uv run uvicorn runstats.main:app --reload
```

The backend listens on:

```text
http://127.0.0.1:8000
```

Check that it is healthy:

```text
http://127.0.0.1:8000/api/healthcheck
```

Expected response:

```json
{
  "status": "ok",
  "service": "runstats",
  "version": "0.1.0"
}
```

## Run the Frontend

Open terminal 2 at the repository root:

```bash
npm run frontend:dev
```

The frontend usually listens on:

```text
http://127.0.0.1:5173
```

Open that URL in a browser. The Vite dev server proxies `/api` requests to the
backend at `http://127.0.0.1:8000`.

## Try the App

Useful first checks:

1. Open Dashboard and confirm seeded charts and recent activity data load.
2. Open Activities and click a seeded activity.
3. Open Health and switch between available metrics.
4. Open Sync History and confirm seeded sync runs load.
5. Open Chat Assistant and ask a seeded-data question.
6. Open Watch Settings.
7. Click Scan.
8. Pair a fake Forerunner watch.
9. Click Test connection.
10. Click Probe capabilities.
11. Start a manual sync.

If you are using the real Bleak provider, scan results depend on nearby BLE
devices, Bluetooth permissions, and whether a supported Garmin watch is
advertising.

## Common Environment Variables

Set these only when needed:

```bash
$env:RUNSTATS_DATABASE_PATH="D:\MYDOCS\MyGitHub\runstats\data\dev.sqlite3"
$env:RUNSTATS_RAW_ARCHIVE_PATH="D:\MYDOCS\MyGitHub\runstats\data\archive\raw-imports"
$env:RUNSTATS_FRONTEND_DIST_PATH="D:\MYDOCS\MyGitHub\runstats\frontend\dist"
$env:RUNSTATS_WATCH_PROVIDER="fake"
$env:RUNSTATS_LOCAL_CHAT_BASE_URL="http://127.0.0.1:11434"
$env:RUNSTATS_LOCAL_CHAT_MODEL="llama3.2"
```

For macOS or Linux shells:

```bash
export RUNSTATS_DATABASE_PATH="$PWD/data/dev.sqlite3"
export RUNSTATS_RAW_ARCHIVE_PATH="$PWD/data/archive/raw-imports"
export RUNSTATS_FRONTEND_DIST_PATH="$PWD/frontend/dist"
export RUNSTATS_WATCH_PROVIDER=fake
export RUNSTATS_LOCAL_CHAT_BASE_URL="http://127.0.0.1:11434"
export RUNSTATS_LOCAL_CHAT_MODEL="llama3.2"
```

The Chat Assistant uses an Ollama-compatible local model by default. If no
local model is running, chat answer requests return `CHAT_MODEL_UNAVAILABLE`;
the rest of the app continues to work. See `docs/chat-assistant.md`.

Frontend API requests normally work through the Vite proxy. Set
`VITE_RUNSTATS_API_BASE_URL` only when the frontend is served from an origin
that can directly reach the backend:

```bash
$env:VITE_RUNSTATS_API_BASE_URL="http://127.0.0.1:8000"
```

## Run the Local Production App

Build and run the combined local app from the repository root:

```bash
npm run package:local
npm run start:local
```

`npm run start:local` applies migrations, starts FastAPI, serves the production
React bundle from `frontend/dist`, and uses the configured local SQLite
database. Open:

```text
http://127.0.0.1:8000
```

See `local-desktop-package.md` for details.

## Validation

Run the full validation suite from the repository root:

```bash
npm run validate
```

This runs:

- Backend tests
- Backend linting
- Backend type checking
- Frontend tests
- Frontend linting
- Frontend type checking
- Frontend production build

Run backend checks only:

```bash
npm run backend:validate
```

Run frontend checks only:

```bash
npm run frontend:validate
```

Validation does not require a physical Garmin watch, live Bluetooth hardware,
a hosted LLM, or a local LLM runtime.

## Troubleshooting

If the frontend cannot load data:

- Confirm the backend terminal is still running.
- Open `http://127.0.0.1:8000/api/healthcheck`.
- Confirm the frontend was started with `npm run frontend:dev`.
- Avoid setting `VITE_RUNSTATS_API_BASE_URL` unless you need a custom backend
  origin.

If the database has no data:

- Run `cd backend`.
- Run `uv run alembic upgrade head`.
- Run `uv run python -m runstats.db.seed`.
- Restart the backend.

If Watch Settings scan fails:

- For development without hardware, set `RUNSTATS_WATCH_PROVIDER=fake` before
  starting the backend.
- For real Bluetooth, confirm Bluetooth is enabled and the operating system has
  granted local device permissions.
- Keep the watch nearby and make sure it is advertising or discoverable.

If Chat Assistant answers fail:

- Confirm a local Ollama-compatible service is running if chat is configured
  with the default local provider.
- Confirm `RUNSTATS_LOCAL_CHAT_BASE_URL` and `RUNSTATS_LOCAL_CHAT_MODEL` match
  your local model runtime.
- The backend error code `CHAT_MODEL_UNAVAILABLE` means RunStats could query
  local data but could not reach the configured chat model.

If a port is already in use:

- Stop the process currently using the port.
- Or run Uvicorn on another port:

```bash
cd backend
uv run uvicorn runstats.main:app --reload --port 8001
```

Then start the frontend with an explicit backend URL:

```bash
$env:VITE_RUNSTATS_API_BASE_URL="http://127.0.0.1:8001"
npm run frontend:dev
```
