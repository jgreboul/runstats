# RunStats Backend

The backend is the local FastAPI service for RunStats. It owns API routing,
SQLite persistence, data imports, Bluetooth watch discovery, sync orchestration,
chat grounding, export/delete controls, migrations, and backend validation.

## Run

```bash
uv run uvicorn runstats.main:app --reload
```

Healthcheck:

```text
GET /api/healthcheck
```

## Install

```bash
uv sync --extra dev
```

## Validate

```bash
uv run pytest
uv run ruff check .
uv run mypy runstats
```

## Configuration

The backend reads environment variables with the `RUNSTATS_` prefix. It loads
`.env` from the current directory or repository root.

Key settings:

- `RUNSTATS_DATABASE_PATH`: SQLite database path.
- `RUNSTATS_RAW_ARCHIVE_PATH`: retained raw import archive path.
- `RUNSTATS_FRONTEND_DIST_PATH`: built React app path for the local app server.
- `RUNSTATS_WATCH_PROVIDER`: `bleak` for real Bluetooth or `fake` for tests.
- `RUNSTATS_LOCAL_CHAT_BASE_URL`: Ollama-compatible chat endpoint.
- `RUNSTATS_LOCAL_CHAT_MODEL`: local chat model name.
- `RUNSTATS_SYNC_SCHEDULER_POLL_SECONDS`: automatic sync polling interval.

Relative paths are resolved from the repository root.

## API Surface

```text
GET    /api/healthcheck
GET    /api/activities
GET    /api/activities/{activity_id}
GET    /api/activities/{activity_id}/samples
GET    /api/activities/summary
GET    /api/health/metrics
GET    /api/health/series
POST   /api/imports/fit-folder
POST   /api/imports/health-payload
POST   /api/devices/scan
POST   /api/devices/pair
GET    /api/devices
PATCH  /api/devices/{device_id}/settings
POST   /api/devices/{device_id}/test-connection
POST   /api/devices/{device_id}/probe-capabilities
GET    /api/devices/{device_id}/capabilities
GET    /api/sync-runs
GET    /api/sync-runs/{sync_run_id}
POST   /api/sync-runs
POST   /api/sync-runs/{sync_run_id}/retry
WS     /api/sync-runs/{sync_run_id}/events
GET    /api/settings
PATCH  /api/settings
POST   /api/chat/sessions
GET    /api/chat/sessions
GET    /api/chat/sessions/{session_id}
POST   /api/chat/sessions/{session_id}/messages
DELETE /api/chat/sessions/{session_id}
DELETE /api/chat/sessions
POST   /api/data-management/export
DELETE /api/data-management/chat-history
DELETE /api/data-management/devices/{device_id}/imported-data
```

## Local App Launcher

Run the combined local app after building the frontend:

```bash
uv run runstats-local
```

The launcher applies migrations, starts FastAPI, and serves the production React
bundle from `RUNSTATS_FRONTEND_DIST_PATH`.

## File Inventory

### Package And Tooling

| Path | Purpose |
| --- | --- |
| `README.md` | Backend overview and file inventory. |
| `alembic.ini` | Alembic configuration used for database migrations. |
| `pyproject.toml` | Python package metadata, dependencies, scripts, pytest, Ruff, and mypy settings. |
| `uv.lock` | Locked backend dependency graph for reproducible `uv` installs. |

### Application Root

| Path | Purpose |
| --- | --- |
| `runstats/__init__.py` | Backend package marker. |
| `runstats/config.py` | Runtime settings, repository-relative path resolution, and SQLite URL helpers. |
| `runstats/local_app.py` | CLI entry point for the combined local backend and built frontend server. |
| `runstats/main.py` | FastAPI application factory, lifespan setup, router registration, provider wiring, and static frontend serving. |
| `runstats/py.typed` | Marks the package as typed for mypy and downstream type checkers. |
| `runstats/schemas.py` | Pydantic request and response models shared by API routers and services. |

### API Routers

| Path | Purpose |
| --- | --- |
| `runstats/api/__init__.py` | API router package marker. |
| `runstats/api/activities.py` | Activity list, detail, sample, and summary endpoints. |
| `runstats/api/chat.py` | Chat session, message, answer, and deletion endpoints. |
| `runstats/api/data_management.py` | Local export and delete endpoints for privacy/data controls. |
| `runstats/api/devices.py` | Watch scan, pair, settings, connection test, and capability probe endpoints. |
| `runstats/api/errors.py` | Structured application error type and FastAPI exception handlers. |
| `runstats/api/health.py` | Health metric descriptor and time-series endpoints. |
| `runstats/api/healthcheck.py` | Simple service health endpoint. |
| `runstats/api/imports.py` | FIT folder and health payload import endpoints. |
| `runstats/api/settings.py` | Local application settings read/update endpoints. |
| `runstats/api/sync.py` | Manual sync, retry, history, detail, and WebSocket progress endpoints. |

### Bluetooth Providers

| Path | Purpose |
| --- | --- |
| `runstats/bluetooth/__init__.py` | Public Bluetooth provider exports. |
| `runstats/bluetooth/bleak_provider.py` | Real BLE provider using Bleak for discovery, connection tests, and GATT capability probing. |
| `runstats/bluetooth/factory.py` | Selects the configured watch provider. |
| `runstats/bluetooth/fake.py` | Deterministic fake Garmin provider for tests and mock workflows. |
| `runstats/bluetooth/provider.py` | Provider protocols, dataclasses, and expected provider errors. |

### Chat Providers

| Path | Purpose |
| --- | --- |
| `runstats/chat/__init__.py` | Public chat provider exports. |
| `runstats/chat/factory.py` | Selects the configured chat response provider. |
| `runstats/chat/fake.py` | Deterministic fake chat provider for tests. |
| `runstats/chat/ollama.py` | Ollama-compatible local chat provider client. |
| `runstats/chat/provider.py` | Chat provider protocol and response dataclasses. |
| `runstats/chat/tools.py` | Approved read-only local data tools used to ground assistant answers. |

### Database

| Path | Purpose |
| --- | --- |
| `runstats/db/__init__.py` | Database package marker. |
| `runstats/db/models.py` | SQLAlchemy models for devices, settings, capabilities, raw imports, activities, laps, samples, health metrics, sync runs, settings, and chat history. |
| `runstats/db/seed.py` | Deterministic development seed data command and reusable seed helpers. |
| `runstats/db/session.py` | SQLAlchemy engine, session factory, and FastAPI session dependency helpers. |

### Migrations

| Path | Purpose |
| --- | --- |
| `runstats/db/migrations/env.py` | Alembic environment setup and settings-aware database URL wiring. |
| `runstats/db/migrations/script.py.mako` | Alembic migration file template. |
| `runstats/db/migrations/versions/0001_initial_schema.py` | Initial schema creation from SQLAlchemy metadata. |
| `runstats/db/migrations/versions/0002_device_settings_fit_folder.py` | Adds per-device historical FIT folder setting. |
| `runstats/db/migrations/versions/0003_sync_error_codes.py` | Adds sync error-code support. |

### Importers

| Path | Purpose |
| --- | --- |
| `runstats/importers/__init__.py` | Importer package marker. |
| `runstats/importers/fit_activity.py` | FIT activity parser that extracts activity, laps, samples, GPS, and sensor fields. |
| `runstats/importers/fit_folder.py` | CLI entry point for importing a folder of activity FIT files. |
| `runstats/importers/health_payload.py` | Parser for supported local JSON health payload files. |

### Services

| Path | Purpose |
| --- | --- |
| `runstats/services/__init__.py` | Services package marker. |
| `runstats/services/activity_service.py` | Activity list, detail, samples, and summary query logic. |
| `runstats/services/analytics_service.py` | Higher-level analytics used by chat tools. |
| `runstats/services/chat_service.py` | Chat session lifecycle, grounding, tool trace, and provider orchestration. |
| `runstats/services/data_management_service.py` | Local export, raw-file inclusion, chat export, and data deletion logic. |
| `runstats/services/device_service.py` | Watch scan, pair, settings, connection test, and capability persistence logic. |
| `runstats/services/health_import_service.py` | Health payload normalization and persistence. |
| `runstats/services/health_service.py` | Health metric descriptor and time-series query logic. |
| `runstats/services/import_service.py` | FIT file import orchestration, duplicate detection, raw archive writes, and activity persistence. |
| `runstats/services/settings_service.py` | Local app settings read/update logic. |
| `runstats/services/sync_scheduler.py` | Background scheduler for auto-sync eligible devices. |
| `runstats/services/sync_service.py` | Manual/scheduled sync lifecycle, progress events, retry handling, and error-code mapping. |
| `runstats/services/time_buckets.py` | Shared day/week/month/year bucket calculations. |

### Tests

| Path | Purpose |
| --- | --- |
| `tests/e2e_server.py` | Test server entry point used by frontend Playwright e2e tests. |
| `tests/fit_fixtures.py` | Helpers that build minimal FIT files for parser/import tests. |
| `tests/test_app.py` | FastAPI app factory and health/application behavior tests. |
| `tests/test_config.py` | Runtime settings and path resolution tests. |
| `tests/test_database.py` | Database engine/session behavior tests. |
| `tests/test_migrations.py` | Alembic migration coverage and schema expectations. |
| `tests/test_models.py` | SQLAlchemy model relationship and persistence tests. |
| `tests/test_package.py` | Backend package metadata/import tests. |
| `tests/test_phase10_data_management.py` | Export/delete data-management API and service tests. |
| `tests/test_phase2_api.py` | Early activity API behavior tests. |
| `tests/test_phase2_services.py` | Early activity service and seeded data tests. |
| `tests/test_phase4_api.py` | Device settings API tests. |
| `tests/test_phase4_services.py` | Device settings service tests. |
| `tests/test_phase5_bluetooth_provider.py` | Bluetooth provider discovery, filtering, and capability behavior tests. |
| `tests/test_phase6_api.py` | FIT folder import API tests. |
| `tests/test_phase6_fit_parser.py` | FIT parser tests. |
| `tests/test_phase6_import_service.py` | FIT import service tests. |
| `tests/test_phase6_sync_imports.py` | Sync-to-import integration tests. |
| `tests/test_phase7_health_import.py` | Health payload import tests. |
| `tests/test_phase8_chat.py` | Chat service, tools, and API tests. |
| `tests/test_phase9_sync_reliability.py` | Sync progress, retry, scheduler, and error-code reliability tests. |
| `tests/test_seed.py` | Deterministic seed command and idempotency tests. |
