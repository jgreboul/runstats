# Local Desktop Package

RunStats can run as a single local FastAPI process that serves the production
React bundle and talks to the configured local SQLite database.

## Build

From the repository root:

```bash
npm run package:local
```

This creates:

- `frontend/dist/` with the production React bundle.
- `backend/dist/` with the backend Python package artifacts.

## Start

From the repository root:

```bash
npm run start:local
```

The launcher applies Alembic migrations to the configured SQLite database, then
starts the combined local app at:

```text
http://127.0.0.1:8000
```

Set `RUNSTATS_DATABASE_PATH` to choose a different SQLite file. Set
`RUNSTATS_FRONTEND_DIST_PATH` when serving a production bundle from a location
other than `frontend/dist`.

Core app functionality does not require hosted services. Watch discovery uses
the local Bluetooth provider by default, and the Chat Assistant defaults to the
configured local Ollama-compatible provider. If the local model is unavailable,
only chat answer generation is affected.

## Useful Options

The backend exposes the same launcher directly:

```bash
cd backend
uv run runstats-local --host 127.0.0.1 --port 8000
```

Use an alternate database:

```bash
cd backend
uv run runstats-local --database-path ../data/dev.sqlite3
```

Skip migration application only when the schema is already prepared:

```bash
cd backend
uv run runstats-local --skip-migrations
```
