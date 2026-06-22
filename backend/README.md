# RunStats Backend

The backend provides the local FastAPI service, structured API errors,
configurable SQLite persistence, SQLAlchemy models, Alembic migrations,
deterministic development seed data, and provider-backed Garmin watch discovery.

## Install

```bash
uv sync --extra dev
```

## Run

```bash
uv run uvicorn runstats.main:app --reload
```

Healthcheck:

```text
GET /api/healthcheck
```

Core query APIs:

```text
GET /api/activities
GET /api/activities/{activity_id}
GET /api/activities/{activity_id}/samples
GET /api/activities/summary
GET /api/health/metrics
GET /api/health/series
GET /api/sync-runs
GET /api/sync-runs/{sync_run_id}
GET /api/settings
PATCH /api/settings
POST /api/imports/fit-folder
POST /api/imports/health-payload
POST /api/devices/scan
POST /api/devices/pair
GET /api/devices
PATCH /api/devices/{device_id}/settings
POST /api/devices/{device_id}/test-connection
POST /api/devices/{device_id}/probe-capabilities
GET /api/devices/{device_id}/capabilities
```

## Configuration

The SQLite path is configurable through `RUNSTATS_DATABASE_PATH`. If unset, the
backend uses `../data/runstats.sqlite3` from this package directory. The raw
import archive path is configurable through `RUNSTATS_RAW_ARCHIVE_PATH`.

The watch provider is configurable through `RUNSTATS_WATCH_PROVIDER`:

- `bleak` uses the local Bluetooth adapter through Bleak. This is the default.
- `fake` returns deterministic Garmin Forerunner profiles for tests and mock
  workflows.

The Bleak capability probe connects to the selected watch and inspects exposed
GATT services. Direct BLE activity and health export stay disabled unless a
known direct export service is detected; folder-based FIT import remains the
next import path for Forerunner 935 validation.

## Migrations

Apply the current schema:

```bash
uv run alembic upgrade head
```

Downgrade to an empty schema:

```bash
uv run alembic downgrade base
```

## Seed Data

Seed deterministic development data:

```bash
uv run python -m runstats.db.seed
```

Use a temporary or alternate database path:

```bash
uv run python -m runstats.db.seed --database-path ../data/dev.sqlite3
```

## Import Historical FIT Files

Import a folder through the API:

```text
POST /api/imports/fit-folder
```

```json
{
  "device_id": "device-uuid",
  "folder_path": "D:/Garmin/Activities",
  "recursive": true
}
```

Import the same folder from the command line:

```bash
uv run python -m runstats.importers.fit_folder --device-id device-uuid --folder-path "D:/Garmin/Activities"
```

Use `--database-path` and `--raw-archive-path` to target alternate local data
locations.

## Import Health Payload Fixtures

Import a local JSON health payload through the API:

```text
POST /api/imports/health-payload
```

```json
{
  "device_id": "device-uuid",
  "file_path": "D:/Garmin/Health/daily-health.json"
}
```

Supported metric names normalize to `steps`, `resting_hr`, `hrv`, `sleep`,
`stress`, `body_battery`, `respiration`, and `pulse_ox`. Canonical units are
documented in `docs/health-import-sources.md` and enforced by the importer.

## Validate

```bash
uv run pytest
uv run ruff check .
uv run mypy runstats
```
