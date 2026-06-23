# RunStats

RunStats is a local-first running and health analytics app for Garmin watch
data. It imports local activity and health files, stores everything in SQLite,
visualizes the data in a React interface, and provides a grounded chat assistant
that answers questions using the local database.

The project is designed for private, single-machine use first. Activity
records, health metrics, raw imports, sync attempts, watch settings, and chat
history stay on the user's computer unless a future feature explicitly adds a
remote service.

## What The App Does

- Discovers and pairs Garmin watches through local Bluetooth.
- Probes watch capabilities through a BLE/GATT connection.
- Imports real activity history from local Garmin `.fit` files.
- Imports supported local health payloads.
- Stores normalized activities, laps, samples, health metrics, raw import
  metadata, sync history, device settings, and chat history in SQLite.
- Shows dashboard summaries, activity lists and details, health trends, sync
  history, watch settings, and data-management controls in React.
- Answers local-data questions through a chat assistant backed by approved
  read-only tools.
- Exports and deletes local data through explicit user controls.

Current Garmin Forerunner testing supports Bluetooth discovery and capability
probing, but direct Bluetooth activity and health export are not implemented.
For real activity history, use the folder-based FIT import flow documented in
`docs/user-guide.md` and `docs/local-setup.md`.

## Repository Layout

```text
backend/    FastAPI API, SQLite models, services, importers, Bluetooth/chat providers, tests
frontend/   React/Vite application, typed API client, browser tests, frontend tests
docs/       User, setup, privacy, packaging, and domain documentation
data/       Ignored local runtime data directory placeholder
```

## Start Here

For end users:

- Read `docs/user-guide.md`.
- Use Watch Settings to pair a watch.
- Import activities with a local FIT folder path such as `E:\GARMIN\ACTIVITY`.

For local development:

```bash
npm run install:all
```

Run the backend:

```bash
cd backend
uv run uvicorn runstats.main:app --reload
```

Run the frontend in a second terminal:

```bash
npm run frontend:dev
```

Open:

```text
http://127.0.0.1:5173
```

For detailed setup, real-device validation, and troubleshooting, see
`docs/local-setup.md`.

## Requirements

- Python 3.12 or newer
- `uv`
- Node.js 20 or newer
- npm
- Bluetooth hardware for real watch discovery
- Optional: Ollama for the local chat assistant

## Validation

Run the full suite:

```bash
npm run validate
```

Run browser-level end-to-end validation:

```bash
npm run e2e:install
npm run e2e
```

The validation commands use fake providers and seeded local data. They do not
require a Garmin watch, live Bluetooth device, hosted LLM, or local LLM runtime.

## Architecture

The backend is a FastAPI app in `backend/runstats`. API routers translate HTTP
requests into service calls. Services own business logic. SQLAlchemy models and
Alembic migrations define the SQLite schema. Provider interfaces isolate
Bluetooth and chat integrations so tests can use deterministic fakes.

The frontend is a Vite React app in `frontend/src`. It uses a typed API client,
React Query for server state, route-level views for each screen, and local CSS
for layout and visual styling. During development, Vite proxies `/api` and
sync-progress WebSocket traffic to FastAPI.

The local production launcher builds the React app, applies migrations, starts
FastAPI, and serves `frontend/dist` from the backend process.

## Root Files

| Path | Purpose |
| --- | --- |
| `.editorconfig` | Shared editor defaults for indentation, final newlines, and charset. |
| `.env.example` | Template runtime configuration for local databases, raw archives, Bluetooth provider, chat provider, and scheduler timing. |
| `.gitignore` | Keeps local databases, virtual environments, build output, caches, and secrets out of source control. |
| `AGENT.md` | Project instructions and development context for coding agents. |
| `README.md` | High-level project overview, quick start, architecture, and root file map. |
| `package.json` | Root npm scripts that coordinate backend and frontend install, validation, build, and local app startup. |
| `runstats-design.md` | Product and technical design notes for the RunStats experience. |
| `runstats-product-backlog.md` | Phase backlog and implementation plan for the local-first RunStats product. |

## Folder READMEs

Each top-level folder has its own README with a file inventory:

- `backend/README.md`
- `frontend/README.md`
- `docs/README.md`
- `data/README.md`

## Privacy

RunStats treats activity routes, health metrics, raw files, and chat history as
sensitive personal data. Local data is stored in the configured SQLite database
and raw archive folder. Export and delete controls are documented in
`docs/privacy-and-data-management.md`.
