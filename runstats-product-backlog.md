# RunStats Product Backlog

## Purpose

This backlog translates `runstats-design.md` into an implementation plan. It is
organized by phases so the product can be built incrementally while keeping each
release testable and useful.

Each backlog item should produce working software, tests, and updated
documentation when behavior changes.

## Delivery Principles

- Build the local data model and backend APIs before depending on live Garmin
  Bluetooth behavior.
- Target Garmin Forerunner 935 and newer first.
- Keep the Bluetooth, import, analytics, and chatbot layers behind explicit
  interfaces so they can be tested with fakes.
- Treat direct BLE export from the Forerunner 935 as a capability to verify, not
  as an assumption.
- Support folder-based FIT import and raw file archiving as the bootstrap and
  fallback path.
- Store canonical values in metric units and convert only at the presentation
  edge.
- Treat health data as sensitive by default.
- Add tests with every implementation change.
- Prefer small, vertical slices that can be manually exercised in the UI or API.

## Definition of Done

An item is done only when:

- The requested behavior is implemented.
- Unit tests cover the new or changed logic.
- API and database changes have integration tests where appropriate.
- Frontend behavior has component or interaction tests where appropriate.
- Migrations, seed data, and documentation are updated when needed.
- The relevant test suite has been run and the result is recorded in the
  implementation summary.
- The implementing agent provides a proposed git commit title and description.

## Phase 0: Project Scaffold and Development Tooling

### Objective

Create the repository structure, development commands, and test infrastructure
needed for reliable incremental work.

### User Outcome

Developers can install dependencies, run the backend, run the frontend, run
tests, and understand the project layout.

### Backlog Items

All Phase 0 backlog items are complete. See `DONE Backlog Items`.

## Phase 1: Backend Foundation and SQLite Data Model

### Objective

Implement the FastAPI backend, SQLite persistence, migrations, and core models
from the design.

### User Outcome

The application can store and query devices, activities, health metrics, sync
runs, and chat records using local SQLite.

### Backlog Items

All Phase 1 backlog items are complete. See `DONE Backlog Items`.

## Phase 2: Core Query APIs and Analytics Services

### Objective

Expose stable backend APIs for activities, health metrics, sync history, and
derived summaries before building deeper UI features.

### User Outcome

The frontend and chatbot can query reliable, tested backend services.

### Backlog Items

All Phase 2 backlog items are complete. See `DONE Backlog Items`.

## Phase 3: React Shell, Dashboard, and Data Views

### Objective

Build the first usable frontend experience against the backend APIs.

### User Outcome

The user can open the app, view dashboards, browse activities, inspect health
trends, and see sync history from seeded or imported data.

### Backlog Items

All Phase 3 backlog items are complete. See `DONE Backlog Items`.

## Phase 4: Watch Configuration UI and Mocked Device Backend

### Objective

Build the watch setup workflow before requiring live Bluetooth.

### User Outcome

The user can scan for a watch, select one, save settings, test the connection,
and start a mocked sync from the UI.

### Backlog Items

All Phase 4 backlog items are complete. See `DONE Backlog Items`.

## Phase 5: Forerunner Bluetooth Discovery and Capability Probe

### Objective

Integrate Bluetooth discovery and connection behind the `WatchProvider`
interface, then verify what activity and health export capabilities are
available for Forerunner 935 and newer watches.

### User Outcome

The app can discover and connect to supported nearby Garmin watches from the
Watch Settings view, and the implementation team knows whether direct BLE export
is viable for the target watch family.

### Backlog Items

All Phase 5 backlog items are complete. See `DONE Backlog Items`.

## Phase 6: Activity Import Pipeline

### Objective

Import running activities from raw exports or FIT files into the normalized
database schema.

### User Outcome

The user can see real running activities, laps, samples, and trends in the UI.

### Backlog Items

All Phase 6 backlog items are complete. See `DONE Backlog Items`.

## Phase 7: Health Import Pipeline

### Objective

Import supported health metrics into normalized time-series records.

### User Outcome

The user can view health trends such as steps, resting heart rate, HRV, sleep,
stress, body battery, respiration, and pulse ox when available.

### Backlog Items

All Phase 7 backlog items are complete. See `DONE Backlog Items`.

## Phase 8: Chat Assistant

### Objective

Implement a grounded chatbot that answers questions about local running and
health data using approved read-only tools.

### User Outcome

The user can ask natural language questions and receive concise answers with
supporting metrics and links back to relevant data.

### Backlog Items

All Phase 8 backlog items are complete. See `DONE Backlog Items`.

## Phase 9: Sync Reliability and Scheduling

### Objective

Make sync dependable, observable, incremental, and safe to run repeatedly.

### User Outcome

The user can trust that repeated syncs import only new data, report progress,
and recover from failures.

### Backlog Items

All Phase 9 backlog items are complete. See `DONE Backlog Items`.

## Phase 10: Packaging, Privacy, and Data Management

### Objective

Prepare the app for everyday local use.

### User Outcome

The user can manage local data, understand privacy behavior, and run the app
without developer-only steps.

### Backlog Items

All Phase 10 backlog items are complete. See `DONE Backlog Items`.

## Cross-Phase Test Strategy

Implementation status: Complete. See `DONE Backlog Items`.

### Backend Unit Tests

Required for:

- Services
- Importers
- Normalizers
- Analytics methods
- Chat tools and orchestration
- Error mapping
- Configuration parsing

### Backend Integration Tests

Required for:

- API endpoints
- Database migrations
- Transactional imports
- Sync lifecycle
- WebSocket event streams

### Frontend Tests

Required for:

- API client behavior
- Route rendering
- Form validation
- Loading, empty, and error states
- Data tables and charts with representative data
- Chat interaction flows

### End-to-End Tests

Add after the app shell is stable.

Primary flows:

- Open dashboard with seeded data.
- Browse activity details.
- Change watch settings with fake backend.
- Run fake sync and observe progress.
- Ask a chatbot question and follow a referenced activity link.

## Backlog Maintenance

When implementation begins:

- Mark the active backlog item in the working notes or issue tracker.
- Keep changes scoped to one or a small group of related backlog items.
- Update this backlog when scope changes or new technical tasks are discovered.
- Do not mark an item complete unless its validation has run successfully or the
  remaining validation gap is explicitly documented.

## DONE Backlog Items

### P0-001: Create Monorepo Structure

Status: Done

Implemented:

- Created the root project scaffold with `backend/`, `frontend/`, `data/`, and
  `docs/`.
- Added backend package and test directories.
- Added frontend source and test directories.
- Added root `.gitignore` so generated local data, virtual environments,
  `node_modules`, build output, and cache directories are excluded.
- Added root `README.md` documenting the project layout and setup commands.

Validation:

- Verified scaffolded directories and files exist.
- Verified local generated data is ignored through `.gitignore` rules.
- Ran `npm run validate` successfully.

### P0-002: Configure Python Backend Tooling

Status: Done

Implemented:

- Added `backend/pyproject.toml` using `uv` with Python package metadata,
  runtime dependencies, and development dependencies.
- Configured `pytest`, `ruff`, and `mypy`.
- Added a minimal typed `runstats` backend package and unit tests.
- Added `backend/README.md` with install and validation commands.
- Generated `backend/uv.lock`.

Validation:

- Ran `uv --project backend sync --extra dev --python C:\Python314\python.exe`
  successfully.
- Ran backend tests through `npm run validate`: 2 tests passed.
- Ran backend linting through `npm run validate`: `ruff check .` passed.
- Ran backend type checking through `npm run validate`: `mypy runstats` passed.

### P0-003: Configure Frontend Tooling

Status: Done

Implemented:

- Added a Vite, React, and TypeScript frontend scaffold.
- Added Recharts, React Leaflet, Leaflet, TanStack Query, and React Router
  dependencies for future phases.
- Configured Vitest, React Testing Library, ESLint, and TypeScript project
  references.
- Added a minimal app shell with the planned primary navigation.
- Added frontend component tests and `frontend/README.md`.
- Generated `frontend/package-lock.json`.

Validation:

- Ran `npm --prefix frontend install` successfully.
- Ran frontend tests through `npm run validate`: 3 tests passed.
- Ran frontend linting through `npm run validate`: ESLint passed.
- Ran frontend type checking through `npm run validate`: `tsc -b` passed.
- Ran frontend production build through `npm run validate`: Vite build passed.

### P0-004: Establish CI-Ready Validation Commands

Status: Done

Implemented:

- Added root `package.json` scripts for installation, backend validation,
  frontend validation, and full validation.
- Added `npm run install:all`.
- Added `npm run validate`.
- Updated `README.md` and `AGENT.md` with the exact validation commands.
- Validation commands do not require a Garmin watch, Bluetooth hardware, hosted
  LLM, or local LLM runtime.

Validation:

- Ran `npm run validate` successfully.
- Full validation covered backend tests, backend linting, backend type checking,
  frontend tests, frontend linting, frontend type checking, and frontend build.

### P1-001: Create FastAPI Application Skeleton

Status: Done

Implemented:

- Added `backend/runstats/main.py` with a `create_app` factory and module-level
  `app` for Uvicorn.
- Added route registration under `/api`.
- Added `GET /api/healthcheck`, returning service status and version metadata.
- Added structured API error handlers that return the stable `{"error": ...}`
  envelope for application, HTTP, and validation errors.
- Documented the local Uvicorn launch command in `README.md` and
  `backend/README.md`.

Validation:

- Ran `uv run pytest` successfully: 12 tests passed.
- Added app creation and healthcheck API tests.
- Added an API test for structured 404 errors.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P1-002: Add Database Session and Settings

Status: Done

Implemented:

- Added `backend/runstats/config.py` with Pydantic settings for
  `RUNSTATS_DATABASE_PATH` and `RUNSTATS_RAW_ARCHIVE_PATH`.
- Added SQLite URL generation and default local data paths.
- Added SQLAlchemy engine and session factory helpers in
  `backend/runstats/db/session.py`.
- Enabled SQLite foreign keys and WAL mode on engine connections.
- Added FastAPI database session dependency wiring for future route handlers.

Validation:

- Ran `uv run pytest` successfully: 12 tests passed.
- Added settings environment-loading and local directory tests.
- Added an integration test for isolated temporary SQLite session lifecycle and
  WAL mode.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P1-003: Implement Core Database Models

Status: Done

Implemented:

- Added SQLAlchemy 2.x models for `devices`, `device_settings`,
  `device_capabilities`, `app_settings`, `sync_runs`, `activities`,
  `activity_laps`, `activity_samples`, `health_metrics`, `raw_imports`,
  `chat_sessions`, and `chat_messages`.
- Added foreign-key relationships and cascade behavior for device-owned,
  activity-owned, and chat-owned records.
- Added the activity duplicate-prevention uniqueness constraint on
  `(device_id, source_activity_id)`.
- Added indexes for sync history, activities, laps, samples, health metrics,
  raw imports, and chat history.
- Stored canonical activity and health values in metric-oriented columns that
  match `runstats-design.md`.

Validation:

- Ran `uv run pytest` successfully: 12 tests passed.
- Added model tests for duplicate activity rejection and ordered relationship
  behavior.
- Added migration smoke coverage that verifies all core tables are created.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P1-004: Add Alembic Migrations

Status: Done

Implemented:

- Added `backend/alembic.ini`.
- Added Alembic migration environment under `backend/runstats/db/migrations`.
- Added initial schema migration `0001_initial_schema`.
- Implemented downgrade support back to an empty schema.
- Documented migration upgrade and downgrade commands in `backend/README.md`.

Validation:

- Ran `uv run pytest` successfully: 12 tests passed.
- Added migration integration test that upgrades a temporary database from empty
  to the current schema.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P1-005: Add Seed Data for Development

Status: Done

Implemented:

- Added deterministic seed generation in `backend/runstats/db/seed.py`.
- Seed data includes a Garmin Forerunner 935 device, device settings,
  capabilities, app settings, three runs, laps, samples, health metrics, raw
  imports, sync runs, and a chat session with messages.
- Added an idempotent seed command through `uv run python -m runstats.db.seed`.
- Documented seed commands in `README.md` and `backend/README.md`.

Validation:

- Ran `uv run pytest` successfully: 12 tests passed.
- Added seed generation tests for required record counts and fixed device data.
- Added an integration test showing the seeded database can answer summary
  queries for total distance, activity count, and available health metrics.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P2-001: Implement Activity Service and APIs

Status: Done

Implemented:

- Added `ActivityService` for filtered activity lists, activity detail, ordered
  samples, and aggregate activity summaries.
- Added `GET /api/activities`, `GET /api/activities/{activity_id}`,
  `GET /api/activities/{activity_id}/samples`, and
  `GET /api/activities/summary`.
- Supported date, sport, and distance filters, limit/offset pagination, derived
  pace and speed values, lap detail, GPS availability, and chart-ready sample
  ordering.

Validation:

- Ran `uv run pytest` successfully: 26 tests passed.
- Added unit tests for activity filtering, derived values, summaries, and sample
  ordering.
- Added API integration tests for list, detail, samples, summary, filtering,
  pagination, and not-found errors.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P2-002: Implement Health Service and APIs

Status: Done

Implemented:

- Added `HealthService` for stored metric discovery and bucketed time-series
  aggregation.
- Added `GET /api/health/metrics` and `GET /api/health/series`.
- Supported date ranges, daily/weekly/monthly buckets, sum aggregation for
  steps, average/min/max/total metadata, and useful empty responses for missing
  metrics.

Validation:

- Ran `uv run pytest` successfully: 26 tests passed.
- Added unit tests for metric discovery, bucket aggregation, and missing metric
  empty states.
- Added API integration tests for metric discovery, time-series queries, and
  unavailable metric responses.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P2-003: Implement Sync Run Query APIs

Status: Done

Implemented:

- Added `SyncService` for listing and retrieving sync history.
- Added `GET /api/sync-runs` and `GET /api/sync-runs/{sync_run_id}`.
- Included duration calculation, limit/offset pagination, device/status
  filtering, and safe error summaries for failed sync runs.

Validation:

- Ran `uv run pytest` successfully: 26 tests passed.
- Added unit tests for sync run serialization, ordering, duration, and safe
  error summary handling.
- Added API integration tests for list, detail, and not-found errors.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P2-004: Implement Analytics Service

Status: Done

Implemented:

- Added `AnalyticsService` with weekly running summary, monthly running summary,
  fastest runs by distance threshold, longest runs, pace trend, heart-rate
  trend, and health metric comparison methods.
- Returned typed serializable result models for dashboard and future chatbot
  use.
- Centralized date range validation and calendar bucketing across activity,
  health, and analytics services.
- Added mixed-unit awareness for health metric comparisons.

Validation:

- Ran `uv run pytest` successfully: 26 tests passed.
- Added unit tests for every analytics method.
- Added edge case tests for empty data and mixed health metric units.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P2-005: Implement Application Settings APIs

Status: Done

Implemented:

- Added `SettingsService` for reading and patching single-row application
  settings.
- Added `GET /api/settings` and `PATCH /api/settings`.
- Implemented design defaults for raw archive path, local chatbot provider,
  hosted chatbot provider, and retain-until-deleted chat retention.
- Used typed request validation so invalid chatbot provider and retention
  values are rejected with structured validation errors.

Validation:

- Ran `uv run pytest` successfully: 26 tests passed.
- Added unit tests for settings defaults, updates, persistence, and validation.
- Added API integration tests for read, update, and invalid setting requests.
- Ran `uv run ruff check .` successfully.
- Ran `uv run mypy runstats` successfully.

### P3-001: Create App Shell and Navigation

Status: Done

Implemented:

- Replaced the Phase 0 placeholder with a usable React application shell.
- Kept primary navigation for Dashboard, Activities, Health, Chat Assistant,
  Watch Settings, and Sync History.
- Added bookmarkable routes for dashboard, activity list, activity detail,
  health, sync history, and sync run detail.
- Added shared loading, empty, and error state components used across Phase 3
  data views.

Validation:

- Ran `npm run validate` successfully: backend tests, linting, type checking,
  frontend tests, linting, type checking, and frontend production build passed.
- Frontend component tests cover primary navigation and route rendering.

### P3-002: Implement API Client Layer

Status: Done

Implemented:

- Added typed frontend client functions for activities, activity summaries,
  activity samples, health metrics, health series, sync runs, and sync run
  detail endpoints.
- Added normalized `ApiError` handling for structured backend errors, invalid
  responses, and local backend network failures.
- Added documented TanStack Query key factories with stable resource and
  parameter shapes.
- Documented `VITE_RUNSTATS_API_BASE_URL` for alternate local backend origins.

Validation:

- Ran `npm run validate` successfully.
- Added API client unit tests for request parameter serialization, structured
  error normalization, network error normalization, and query key shapes.

### P3-003: Build Dashboard View

Status: Done

Implemented:

- Added dashboard summary widgets for weekly distance, monthly distance,
  average pace, and last sync status.
- Added Recharts panels for pace trend, heart-rate trend, and steps trend.
- Added a recent activities panel sourced from the activity list API.
- Added empty, loading, and error states for dashboard data.

Validation:

- Ran `npm run validate` successfully.
- Added component tests with mocked API data for dashboard rendering.
- Ran Edge headless visual smoke for the dashboard at
  `data/phase3-dashboard-smoke-final.png`.
- Vite production build passed and reported a bundle-size warning for the
  current Recharts and Leaflet chunk.

### P3-004: Build Activities View

Status: Done

Implemented:

- Added activity list filters for date range, sport, distance range, and search
  text.
- Added activity table columns for date, name, sport, distance, pace, duration,
  heart rate, and elevation.
- Added activity detail route with summary cards, fact list, lap table, and
  sample charts.
- Added a React Leaflet route map when coordinate samples exist.
- Added a clear no-map state when GPS samples are unavailable.
- Kept route rendering privacy-oriented by drawing the GPS trace without
  external map tiles.

Validation:

- Ran `npm run validate` successfully.
- Added component tests for activity search filtering, activity detail
  rendering, route map rendering, and no-GPS map state.
- Ran Edge headless visual smoke for activity detail at
  `data/phase3-activity-detail-smoke.png`.
- Existing backend API integration tests remained passing.

### P3-005: Build Health View

Status: Done

Implemented:

- Added health metric selector, date range controls, and daily/weekly/monthly
  aggregation bucket controls.
- Added health metric summary cards and a Recharts trend chart.
- Added unavailable-data handling for known but unsupported or not-yet-imported
  metrics such as body battery.

Validation:

- Ran `npm run validate` successfully.
- Added component tests for metric selection and unavailable metric empty
  states.

### P3-006: Build Sync History View

Status: Done

Implemented:

- Added sync history table with status, start time, duration, imported activity
  counts, imported health record counts, and error summaries.
- Added status filtering.
- Added sync run detail route with summary cards and failed-run inspection.

Validation:

- Ran `npm run validate` successfully.
- Added component tests for failed sync run detail rendering.

### P4-001: Implement Device API Contracts

Status: Done

Implemented:

- Added fake-backed device scan, pair, list, settings patch, and connection test
  endpoints.
- Added deterministic fake Garmin watch profiles, including Forerunner 935+
  scan data and an offline profile for failure states.
- Persisted device settings, including automatic sync, import toggles,
  preferred units, sync interval, and historical FIT import folder.
- Added a migration for `device_settings.historical_fit_import_folder`.

Validation:

- Ran `npm run validate` successfully.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase4_services.py tests/test_phase4_api.py tests/test_migrations.py`.
- Ran backend linting successfully:
  `uv run ruff check runstats tests/test_phase4_services.py tests/test_phase4_api.py tests/test_migrations.py`.
- Ran backend type checking successfully: `uv run mypy runstats`.
- Added unit tests for device service scan, pair, settings, and connection
  behavior.
- Added API integration tests for device scan, pair, list, settings patch, and
  test connection.

### P4-002: Build Watch Settings View

Status: Done

Implemented:

- Replaced the Watch Settings placeholder with a real React configuration view.
- Added scan, discovered-watch, pairing, no-watch, connected, failed connection,
  syncing, succeeded, and failed sync UI states.
- Added controls for automatic sync, sync interval, activity import, health
  import, preferred units, and historical FIT import folder.
- Displayed direct BLE activity export, direct BLE health export, and folder
  import capability states.
- Added typed frontend API client functions and query keys for device workflows.

Validation:

- Ran `npm run validate` successfully.
- Ran targeted frontend tests successfully:
  `npm run test -- WatchSettingsView.test.tsx api.test.ts App.test.tsx`.
- Ran frontend linting successfully: `npm run lint`.
- Ran frontend type checking successfully: `npm run typecheck`.
- Added interaction tests for scan, pair, settings save, connection test,
  Bluetooth unavailable state, and manual sync completion.

### P4-003: Add Mock Sync Progress

Status: Done

Implemented:

- Added `POST /api/sync-runs` to create a mocked manual sync run.
- Added `WS /api/sync-runs/{sync_run_id}/events` for deterministic fake progress
  events.
- Added a fake sync lifecycle that updates sync history to succeeded or failed
  based on the fake provider connection outcome.
- Connected the Watch Settings manual sync control to the progress stream and
  completion states.

Validation:

- Ran `npm run validate` successfully.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase4_services.py tests/test_phase4_api.py tests/test_migrations.py`.
- Ran targeted frontend tests successfully:
  `npm run test -- WatchSettingsView.test.tsx api.test.ts App.test.tsx`.
- Added backend service and API tests for fake sync creation, progress events,
  success finalization, and failure finalization.
- Added frontend interaction coverage for streamed progress and sync completion.

### P5-001: Implement WatchProvider Interface

Status: Done

Implemented:

- Added explicit watch provider contracts under `backend/runstats/bluetooth` for
  provider status, scanning, watch identity resolution, connection tests,
  capability probes, and future raw activity or health exports.
- Moved deterministic fake Garmin watches behind `FakeWatchProvider` so tests and
  mock workflows do not require Bluetooth hardware.
- Added provider error mapping from `WatchProviderError` to the stable
  structured API error envelope.
- Added `RUNSTATS_WATCH_PROVIDER` with `bleak` as the default local provider and
  `fake` as the deterministic test/development option.

Validation:

- Ran `npm run validate` successfully after Phase 5 implementation.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase4_services.py tests/test_phase4_api.py tests/test_phase5_bluetooth_provider.py tests/test_config.py`.
- Ran backend linting successfully: `uv run ruff check .`.
- Ran backend type checking successfully: `uv run mypy runstats`.

### P5-002: Integrate Bleak Scanner

Status: Done

Implemented:

- Added `BleakWatchProvider` for local BLE scanning through Bleak.
- Identified likely Garmin Forerunner watches by advertised name and Garmin
  manufacturer-data hints.
- Normalized Bleak scan results into app-level discovered-watch records with
  Bluetooth identifier, display name, RSSI, model hint, and known-device state.
- Returned clean `BLUETOOTH_UNAVAILABLE` structured errors when scanning cannot
  access a Bluetooth adapter.

Validation:

- Added unit tests with mocked Bleak scanner responses for Forerunner name
  matching, Garmin manufacturer-data matching, non-watch filtering, and
  Bluetooth-unavailable failures.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase5_bluetooth_provider.py`.
- Manual local Bluetooth hardware validation was not run in this environment.

### P5-003: Implement Watch Pairing and Connection Test

Status: Done

Implemented:

- Updated `DeviceService` and the devices API to resolve selected watch metadata
  through the configured provider before storing a device record.
- Preserved fake-backed pairing and connection behavior for tests and mock sync
  flows.
- Kept successful connection tests updating `last_seen_at` and device metadata
  when provider data is available.
- Returned user-safe connection failure messages while preserving stable
  `error_code` values for the UI.

Validation:

- Ran backend service and API tests for scan, pair, list, settings, connection
  success, connection failure, and structured provider errors.
- Ran targeted frontend tests successfully:
  `npm run test -- WatchSettingsView.test.tsx api.test.ts`.
- Manual local Bluetooth hardware validation was not run in this environment.

### P5-004: Probe Forerunner Export Capabilities

Status: Done

Implemented:

- Added `POST /api/devices/{device_id}/probe-capabilities` to run and persist a
  provider capability probe.
- Added `GET /api/devices/{device_id}/capabilities` to return the latest stored
  result.
- Added Watch Settings UI and typed frontend client support for capability
  probing and refreshed capability state.
- Stored support for direct BLE activity export, direct BLE health export, and
  folder import independently so probes can identify activity-only, health-only,
  both, or neither.
- Documented the current import-path decision: for Forerunner 935 validation,
  use folder-based FIT import next unless a live hardware probe identifies a
  known direct BLE export service; evaluate Garmin Health SDK or Garmin Connect
  Developer Program APIs for richer health export.

Validation:

- Added fake provider capability-matrix tests, including a profile that reports
  both direct activity and health export support.
- Added mocked Bleak service-inspection tests for direct activity export
  detection.
- Added API integration tests for probe and latest-capabilities endpoints.
- Added frontend interaction tests for running a probe and showing updated
  capability state.
- Manual Forerunner 935 hardware validation was not run in this environment.

### P6-001: Add Raw Import Archive

Status: Done

Implemented:

- Added activity import archiving through `ActivityImportService`, hashing every
  FIT payload with SHA-256 before persistence.
- Retained imported FIT files under the configured raw archive path by default.
- Used persisted `app_settings.raw_archive_path` when present, falling back to
  runtime `RUNSTATS_RAW_ARCHIVE_PATH`.
- Detected duplicate raw files by device, kind, and SHA-256 before parsing or
  writing a second raw import record.
- Stored `raw_imports` metadata pointing at the retained archive file.

Validation:

- Added service tests for hashing, duplicate raw payload detection, persisted
  archive path behavior, and retained-file metadata.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase6_fit_parser.py tests/test_phase6_import_service.py tests/test_phase6_api.py tests/test_phase6_sync_imports.py tests/test_phase4_services.py tests/test_phase4_api.py`.

### P6-002: Implement FIT Activity Parser

Status: Done

Implemented:

- Added `FitActivityParser` using `fitparse` to parse FIT activity payloads.
- Normalized distance, duration, pace, heart rate, cadence, elevation,
  training effect, laps, samples, speed, power, and GPS coordinates into
  canonical metric values.
- Handled missing optional fields safely while requiring enough start time,
  duration, and distance data to create a valid activity.
- Added stable malformed-file errors through `FitActivityParseError`.

Validation:

- Added generated valid FIT fixture coverage for parser extraction.
- Added parser tests for missing optional fields and malformed FIT bytes.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase6_fit_parser.py tests/test_phase6_import_service.py tests/test_phase6_api.py tests/test_phase6_sync_imports.py tests/test_phase4_services.py tests/test_phase4_api.py`.

### P6-003: Implement Activity Import Service

Status: Done

Implemented:

- Persisted parsed activities, laps, samples, and raw import metadata through
  `ActivityImportService`.
- Added duplicate activity detection by source activity id, raw checksum, and
  fallback start-time/duration/distance signature.
- Kept each file import transactionally consistent in SQLite and removed the
  retained raw file if the corresponding DB write fails.
- Reported created activity counts back into manual sync runs.

Validation:

- Added SQLite integration tests for successful import, duplicate activity
  skipping, duplicate raw skipping, and rollback on failed activity persistence.
- Added direct sync import tests verifying activity counts in sync history.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase6_fit_parser.py tests/test_phase6_import_service.py tests/test_phase6_api.py tests/test_phase6_sync_imports.py tests/test_phase4_services.py tests/test_phase4_api.py`.

### P6-004: Add Folder Import Bootstrap

Status: Done

Implemented:

- Added `POST /api/imports/fit-folder` for local historical FIT folder import.
- Added `uv run python -m runstats.importers.fit_folder` for command-line
  folder imports.
- Returned folder import summaries with created, skipped, failed, archived
  counts, and per-file statuses.
- Kept folder import independent from direct watch export capability so it works
  for watches that only support folder-based import.
- Documented the API and command in `backend/README.md`.

Validation:

- Added service tests with generated FIT fixture files.
- Added API integration tests for successful folder import, failed malformed
  files, missing folder errors, and rendering imported activities through
  `GET /api/activities`.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase6_fit_parser.py tests/test_phase6_import_service.py tests/test_phase6_api.py tests/test_phase6_sync_imports.py tests/test_phase4_services.py tests/test_phase4_api.py`.

### P6-005: Connect Verified Direct Activity Export

Status: Done

Implemented:

- Updated manual sync to call direct activity export only when stored device
  capabilities confirm BLE activity export support.
- Routed direct provider exports through the same raw archive and activity
  import service used by folder import.
- Returned a clear failed sync event and sync-history error summary when direct
  activity export is unsupported.
- Kept Garmin-specific export details behind `WatchProvider`; the importer only
  receives raw activity payloads.

Validation:

- Added sync integration tests with fake supported direct export payloads.
- Added sync integration tests for unsupported direct export and clear
  folder-import messaging.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase6_fit_parser.py tests/test_phase6_import_service.py tests/test_phase6_api.py tests/test_phase6_sync_imports.py tests/test_phase4_services.py tests/test_phase4_api.py`.

### P7-001: Define Health Metric Normalization

Status: Done

Implemented:

- Added stable internal metric names for `steps`, `resting_hr`, `hrv`, `sleep`,
  `stress`, `body_battery`, `respiration`, and `pulse_ox`.
- Added canonical unit normalization for counts, beats per minute,
  milliseconds, sleep hours, scores, breaths per minute, and percent values.
- Added alias handling for common JSON export names and Garmin-style summary
  fields.
- Reported unsupported metrics and invalid records as import warnings instead
  of crashing the whole payload.

Validation:

- Added parser unit tests for supported metric aliases, unit conversion, daily
  summary expansion, and unsupported metric handling.
- Ran `npm run validate` successfully.

### P7-002: Implement Health Importer

Status: Done

Implemented:

- Added `HealthPayloadParser` for JSON health payloads and fixture exports.
- Added `HealthImportService` to persist normalized health records into
  `health_metrics`.
- Archived raw health payloads as `raw_imports.kind = "health_payload"` under
  the configured local raw archive path.
- Added duplicate detection by raw payload, raw source, source record id, and
  exact metric signature.
- Supported partial payload imports where valid records are stored and skipped
  records are reported with warnings.
- Added `POST /api/imports/health-payload` for local JSON payload imports.

Validation:

- Added persistence and duplicate-handling integration tests.
- Added API integration coverage for importing a local health payload and
  discovering the resulting metric through `GET /api/health/metrics`.
- Ran `npm run validate` successfully.

### P7-003: Connect Health Import to Sync

Status: Done

Implemented:

- Updated manual sync to import direct provider health exports only when stored
  capabilities report direct BLE health export support.
- Tracked imported health record counts from the real health import service
  instead of a mock count.
- Preserved activity-only, health-only, and combined sync requests through the
  existing `ManualSyncRequest` flags.
- Returned clear sync progress and sync-history messages when direct BLE health
  export is unsupported.
- Invalidated frontend health and activity queries after sync completion or
  failure so charts refresh after imports.

Validation:

- Added sync service tests for supported direct health export, persisted record
  counts, and unsupported direct health export messaging.
- Updated API sync tests to assert real imported health record counts.
- Ran `npm run validate` successfully.

### P7-004: Evaluate Alternate Health Data Sources

Status: Done

Implemented:

- Added `docs/health-import-sources.md` comparing local health fixture imports,
  Garmin Health SDK, Garmin Connect Developer Program Health API, and Garmin
  Connect based adapters.
- Documented privacy, credential, platform, approval, and commercial access
  implications for each source.
- Recommended the local JSON payload import path as the near-term bootstrap and
  replay workflow.
- Deferred Garmin Health SDK and Garmin Connect Developer Program integrations
  until RunStats intentionally adds mobile-app or OAuth credential flows.

Validation:

- Reviewed official Garmin Health API, Garmin Connect Developer Program FAQ,
  and Garmin Health SDK FAQ pages on 2026-06-22.
- Ran `npm run validate` successfully.

### P8-001: Implement Chat Persistence APIs

Status: Done

Implemented:

- Added chat session create, list, retrieve, delete-one, and delete-all APIs
  under `/api/chat/sessions`.
- Added `POST /api/chat/sessions/{session_id}/messages` for persisted user
  messages and assistant responses.
- Serialized stored message tool traces as lightweight supporting data.
- Read chat retention policy from app settings, with `retain_until_deleted` as
  the implemented behavior for this release.

Validation:

- Added chat service persistence tests for create, list, retrieve, message
  storage, delete-one, and delete-all behavior.
- Added API integration tests for chat session, message, and delete endpoints.
- Ran targeted backend tests successfully: `uv run pytest tests/test_phase8_chat.py`.

### P8-002: Implement Read-Only Chat Tools

Status: Done

Implemented:

- Added an approved read-only chat tool registry for weekly running summary,
  monthly running summary, fastest run by distance threshold, longest run,
  activity detail lookup, health metric trend, activity and health comparison,
  and sync status lookup.
- Routed tools through existing service-layer methods instead of arbitrary SQL.
- Returned typed summaries with row counts, time ranges, metrics, notes, and
  references to activities, health charts, and sync runs.
- Handled empty running data and unavailable health metrics with notes.

Validation:

- Added unit tests covering every initial chat tool.
- Added a security test confirming the registry is read-only and exposes no
  unrestricted SQL execution tool.
- Ran targeted backend tests successfully: `uv run pytest tests/test_phase8_chat.py`.

### P8-003: Add Local-First LLM Provider Abstraction

Status: Done

Implemented:

- Added a provider-neutral `ChatResponseProvider` protocol.
- Added deterministic `FakeChatProvider` for unit and API tests.
- Added an Ollama-compatible local HTTP provider adapter.
- Added explicit runtime settings for local chat base URL, model, and timeout.
- Kept hosted provider use disabled for this local-first release.
- Mapped unavailable model failures to `CHAT_MODEL_UNAVAILABLE`.

Validation:

- Added provider-backed orchestration tests using the fake provider.
- Added service and API tests for `CHAT_MODEL_UNAVAILABLE` error mapping.
- Ran targeted backend tests successfully: `uv run pytest tests/test_phase8_chat.py`.

### P8-004: Implement Chat Orchestration

Status: Done

Implemented:

- Added `ChatService.answer_question(session_id, question)`.
- Stored user questions and assistant responses.
- Added deterministic intent routing to approved tools for descriptive
  analytics questions.
- Included supporting data, row counts, time ranges, references, and notes in
  assistant responses.
- Stored tool trace metadata without duplicating full result sets.
- Added health-answer guardrails and deferred workout-generation responses.

Validation:

- Added orchestration tests for weekly summaries, fastest runs, longest-run
  detail, unavailable health metrics, unsupported questions, deferred workout
  requests, and model errors.
- Ran targeted backend tests successfully: `uv run pytest tests/test_phase8_chat.py`.

### P8-005: Build Chat Assistant UI

Status: Done

Implemented:

- Replaced the Chat Assistant placeholder with a real React chat experience.
- Added session list, new chat, resume chat, message composer, pending answer
  state, error state, starter questions, supporting-data display, references,
  and delete-history controls.
- Added typed frontend chat API client methods and query keys.
- Linked chat answer references back to activities, health charts, and sync
  runs.
- Updated Health view to honor `?metric=` links from chat references.

Validation:

- Added frontend API client tests for chat list, create, retrieve, ask, delete,
  and query key shapes.
- Added app interaction tests for chat history rendering and sending a grounded
  question with linked references.
- Ran targeted frontend tests successfully:
  `npm run test -- App.test.tsx api.test.ts`.

### P8-006: Defer Suggested Workout Generation

Status: Done

Implemented:

- Added `docs/chat-assistant.md` documenting suggested workout generation as a
  future feature.
- Documented guardrails requiring suggestions to be labeled as general training
  ideas, not medical guidance.
- Documented that future workout suggestions must cite recent training data
  used by the recommendation.
- Added an unsupported/deferred chatbot response for workout-generation
  requests in the first release.

Validation:

- Reviewed the new chat assistant documentation.
- Added orchestration test coverage for deferred workout-generation requests.
- Ran targeted backend tests successfully: `uv run pytest tests/test_phase8_chat.py`.
- Ran full validation successfully: `npm run validate`.

### P9-001: Implement Incremental Sync

Status: Done

Implemented:

- Refactored sync execution so manual and scheduled syncs use the latest
  successful sync `finished_at` as the provider `since` marker.
- Extended the watch provider export contract to accept an optional `since`
  marker for activity and health exports.
- Kept failed sync attempts out of successful sync marker selection.
- Preserved duplicate protection for repeated activity and health imports so
  repeated syncs skip already imported payloads and records.

Validation:

- Added Phase 9 backend tests for successful, failed, and repeated sync marker
  transitions.
- Added repeated health sync coverage proving duplicate health records are not
  created.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase9_sync_reliability.py tests/test_phase4_services.py tests/test_phase4_api.py tests/test_migrations.py`.

### P9-002: Implement Scheduled Sync

Status: Done

Implemented:

- Added `SyncScheduler` with deterministic `run_due_syncs(now=...)` behavior
  for tests and a background app lifecycle loop for normal runtime.
- Scheduled sync reads `auto_sync_enabled`, `sync_interval_minutes`, and import
  toggles from device settings.
- Scheduled sync skips devices whose latest sync is still running.
- Added `RUNSTATS_SYNC_SCHEDULER_POLL_SECONDS` for the background polling
  interval.

Validation:

- Added scheduler tests using explicit clock values for due, not-due, and
  already-running sync states.
- Ran backend linting and type checking successfully:
  `uv run ruff check .` and `uv run mypy runstats`.

### P9-003: Add WebSocket Progress Events

Status: Done

Implemented:

- Changed WebSocket sync progress to observe stored progress events instead of
  finalizing sync state.
- Stored progress events for manual, scheduled, and retry syncs in the app
  progress store.
- Added structured failed progress events with `error_code`.
- Preserved terminal fallback events for sync runs whose in-memory progress
  events are no longer available.

Validation:

- Added API WebSocket coverage showing failed progress events are available
  after backend sync completion.
- Kept frontend manual sync progress interaction tests passing with the typed
  progress event model.

### P9-004: Improve Error Reporting and Retry

Status: Done

Implemented:

- Added nullable `sync_runs.error_code` with Alembic migration
  `0003_sync_error_codes`.
- Mapped known provider and import failures to documented sync error codes such
  as `WATCH_CONNECTION_FAILED`, `WATCH_EXPORT_FAILED`, `IMPORT_PARSE_FAILED`,
  `DATABASE_WRITE_FAILED`, and `SYNC_ALREADY_RUNNING`.
- Added `POST /api/sync-runs/{sync_run_id}/retry` for failed sync retries.
- Updated Sync History UI to show error codes and retry failed sync runs.
- Added frontend API typing for sync error codes and retry requests.

Validation:

- Added backend retry and error-code tests for failed syncs.
- Added frontend interaction coverage for retrying a failed sync from Sync
  History.
- Ran targeted frontend tests successfully:
  `npm test -- tests/WatchSettingsView.test.tsx tests/App.test.tsx`.

### P10-001: Add Data Export

Status: Done

Implemented:

- Added `DataManagementService.export_data` and
  `POST /api/data-management/export`.
- Exported devices, activities with laps and samples, health metrics, raw import
  metadata, and optional raw archived file bytes in documented
  `runstats.local-data.v1` JSON.
- Kept chat history excluded by default and included it only when
  `include_chat_history` is explicitly requested.
- Added a Data Management UI export flow with raw-file and chat-history options.
- Documented the export format in `docs/privacy-and-data-management.md`.

Validation:

- Added backend service tests for export serialization, raw-file inclusion,
  chat opt-in behavior, and non-mutating export counts.
- Added API integration coverage for exporting from seeded data.
- Added frontend API and app interaction tests for export requests.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase10_data_management.py tests/test_app.py tests/test_config.py`.
- Ran targeted frontend tests successfully:
  `npm run test -- api.test.ts App.test.tsx`.

### P10-002: Add Delete Data Controls

Status: Done

Implemented:

- Added `DELETE /api/data-management/chat-history` to delete all local chat
  sessions and messages.
- Added `DELETE /api/data-management/devices/{device_id}/imported-data` to
  delete imported activities, laps, samples, health metrics, raw import records,
  and archived raw files for one device while keeping the configured device.
- Added Data Management UI controls with confirmation gates for chat-history and
  device-data deletion.
- Kept Sync History records after device-data deletion for auditability.

Validation:

- Added backend service and API tests for chat deletion, device imported-data
  deletion, file deletion counts, and missing-device errors.
- Added frontend app interaction coverage for confirmation-gated destructive
  actions.
- Ran targeted backend tests successfully:
  `uv run pytest tests/test_phase10_data_management.py tests/test_app.py tests/test_config.py`.
- Ran targeted frontend tests successfully:
  `npm run test -- api.test.ts App.test.tsx`.

### P10-003: Package Local Desktop App

Status: Done

Implemented:

- Added `RUNSTATS_FRONTEND_DIST_PATH` and FastAPI static serving for the
  production React bundle with SPA route fallback.
- Added `runstats-local`, which applies Alembic migrations and starts the
  combined local API/UI server against the configured SQLite database.
- Added root scripts: `package:backend`, `package:frontend`, `package:local`,
  and `start:local`.
- Documented the local package and startup flow in `README.md`,
  `backend/README.md`, `docs/local-setup.md`, and
  `docs/local-desktop-package.md`.
- Added `backend/dist/` to `.gitignore` for generated package artifacts.

Validation:

- Added backend app tests proving the production frontend bundle is served and
  `/api` errors remain structured.
- Built the backend package successfully with `uv build`.
- Built the frontend production bundle successfully with `npm run build`.
- Local smoke coverage is provided by the production bundle serving app test.

### P10-004: Preserve Hosted Website Path

Status: Done

Implemented:

- Preserved frontend alternate API origin support through
  `VITE_RUNSTATS_API_BASE_URL`.
- Documented hosted privacy implications for activity, health, raw file, chat
  prompt, and chat tool-summary data in
  `docs/privacy-and-data-management.md`.
- Kept hosted deployment out of the local desktop release path.
- Updated frontend docs to clarify when to leave the API base URL unset.

Validation:

- Built the frontend production bundle with the default local API configuration.
- Built the frontend production bundle with
  `VITE_RUNSTATS_API_BASE_URL=http://127.0.0.1:8001`.
- Reviewed and updated privacy and local package documentation.

### XPT-001: Add Cross-Phase End-to-End Validation

Status: Done

Implemented:

- Added Playwright browser e2e coverage for the primary cross-phase flows:
  dashboard load, activity browse/detail, watch pair/probe/settings/fake sync,
  chat answer references, and local data export.
- Added a seeded local e2e FastAPI server that applies migrations, serves the
  built frontend bundle, and uses fake watch/chat providers for deterministic
  end-to-end validation.
- Added root and frontend e2e scripts plus Chromium install scripts.
- Scoped Vitest to frontend unit/integration tests so Playwright specs run only
  under the Playwright runner.

Validation:

- Installed Playwright Chromium with `npm run e2e:install`.
- Ran full standard validation successfully: `npm run validate`.
- Ran browser e2e validation successfully: `npm run e2e` with 5 passing
  Playwright tests.

### XPT-002: Document Real-Device Local Validation

Status: Done

Implemented:

- Added `.env.example` for real local testing with the Bleak watch provider,
  repo-relative SQLite/archive/frontend paths, and Ollama `gemma2`.
- Updated backend configuration to load `.env` from the backend or repository
  root and resolve configured relative paths from the repository root.
- Reworked `docs/local-setup.md` into a junior-friendly real-device setup guide
  covering Bluetooth/Garmin pairing, Ollama `gemma2`, clean database startup,
  local development servers, production local app startup, FIT folder import,
  health payload import, and troubleshooting.
- Updated README, backend README, frontend README, and AGENT guidance with the
  new e2e and real-device validation commands.

Validation:

- Added backend config tests for `.env` loading and repo-root path resolution.
- Ran full standard validation successfully: `npm run validate`.
- Ran a non-invasive Bleak provider smoke check confirming the real Bluetooth
  provider dependency is available.
- Documented the physical Garmin/Bluetooth validation steps; hardware testing
  remains a manual checklist because no real watch is attached in this
  development environment.

### XPT-003: Refresh UI Theme

Status: Done

Implemented:

- Updated the application theme to use the requested ColorHunt palette:
  `#0F2854`, `#1C4D8D`, `#4988C4`, and `#BDE8F5`.
- Refreshed shared CSS tokens, page background, navigation, panels, buttons,
  forms, status surfaces, route map styling, and chart colors to match the new
  palette while keeping semantic success/warning/error colors readable.

Validation:

- Ran frontend unit/integration coverage through `npm run validate`.
- Built the frontend production bundle successfully.
- Ran browser e2e validation successfully: `npm run e2e`.
