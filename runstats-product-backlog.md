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

#### P7-001: Define Health Metric Normalization

Create metric type constants and unit normalization rules.

Acceptance criteria:

- Supported metrics have stable internal names.
- Units are canonical and documented.
- Unsupported metrics can be ignored or recorded as warnings.

Validation:

- Unit tests for normalization rules.

#### P7-002: Implement Health Importer

Convert supported health payloads or fixture exports into `health_metrics`
records.

Acceptance criteria:

- Timestamped and interval metrics are supported.
- Duplicate source records are detected.
- Partial payloads import valid records and report skipped data.

Validation:

- Unit tests with fixture payloads.
- Integration tests for persistence and duplicate handling.

#### P7-003: Connect Health Import to Sync

Add health import to manual and scheduled sync paths when a supported health
export source is available.

Acceptance criteria:

- Sync can import activities only, health only, or both.
- Imported health record counts are tracked.
- Health charts update after sync.
- Unsupported direct BLE health export produces a clear UI and sync-history
  message instead of failing silently.

Validation:

- Sync service tests with fake provider exports.
- API tests for sync result counts.

#### P7-004: Evaluate Alternate Health Data Sources

If direct BLE health export is unavailable for the target watch, evaluate the
next supported path.

Acceptance criteria:

- The evaluation compares folder/import fixtures, Garmin Health SDK, Garmin
  Connect Developer Program APIs, and Garmin Connect based adapters.
- Privacy, credentials, platform support, and approval requirements are
  documented.
- A recommended path is added to the backlog before implementation starts.

Validation:

- Documentation review against official Garmin sources.

## Phase 8: Chat Assistant

### Objective

Implement a grounded chatbot that answers questions about local running and
health data using approved read-only tools.

### User Outcome

The user can ask natural language questions and receive concise answers with
supporting metrics and links back to relevant data.

### Backlog Items

#### P8-001: Implement Chat Persistence APIs

Implement:

- `POST /api/chat/sessions`
- `GET /api/chat/sessions`
- `GET /api/chat/sessions/{session_id}`
- Delete chat history endpoint
- Message storage for user and assistant messages

Acceptance criteria:

- Sessions and messages are persisted.
- Chat history can be listed and retrieved.
- Chat history is retained locally until deleted by default.
- Chat history can be deleted.
- Retention policy is read from app settings, even if only
  `retain_until_deleted` is implemented first.

Validation:

- Unit tests for chat service persistence.
- API integration tests for session, message, and delete endpoints.

#### P8-002: Implement Read-Only Chat Tools

Create approved tools for common analytics questions.

Initial tools:

- Weekly running summary
- Monthly running summary
- Fastest run by distance threshold
- Longest run
- Activity detail lookup
- Health metric trend
- Activity and health comparison
- Sync status lookup

Acceptance criteria:

- Tools call service methods, not arbitrary SQL generated by a model.
- Tools return typed summaries with row counts, date ranges, and references.
- Tools handle empty data and unsupported metrics.

Validation:

- Unit tests for every tool.
- Security test confirming tools do not expose unrestricted database access.

#### P8-003: Add Local-First LLM Provider Abstraction

Implement an interface for chatbot response generation.

Acceptance criteria:

- At least one fake provider exists for tests.
- Provider configuration is explicit.
- A local-model provider adapter is implemented first.
- Hosted provider use can be disabled.
- Model errors map to `CHAT_MODEL_UNAVAILABLE`.

Validation:

- Unit tests for fake provider and error mapping.

#### P8-004: Implement Chat Orchestration

Implement `ChatService.answer_question(session_id, question)`.

Acceptance criteria:

- User messages and assistant responses are stored.
- The service chooses approved tools based on user intent.
- Answers include concise response text, supporting data, and time range.
- Health answers avoid medical diagnosis or prescriptive advice.
- The first release supports descriptive analytics only.
- Tool trace metadata is stored without duplicating large result sets.

Validation:

- Unit tests for orchestration paths.
- Tests for unsupported questions and missing data.
- Snapshot-like tests are allowed only for stable structured response fields.

#### P8-005: Build Chat Assistant UI

Implement the React chat experience.

Acceptance criteria:

- Users can create or resume a chat session.
- Users can send questions and see responses.
- Suggested starter questions appear when useful.
- Answers link to referenced activities, charts, or sync runs.
- Empty, loading, streaming, and error states are handled.
- Users can delete chat history.

Validation:

- Component tests for session list, composer, answer rendering, and errors.
- Interaction tests with mocked chat APIs.

#### P8-006: Defer Suggested Workout Generation

Document the requirements for later suggested workout generation without adding
it to the first chatbot release.

Acceptance criteria:

- Suggested workouts are documented as a future feature.
- Guardrails require the assistant to label suggestions as general training
  ideas, not medical guidance.
- Future workout suggestions must cite recent training data used by the
  recommendation.

Validation:

- Documentation review.

## Phase 9: Sync Reliability and Scheduling

### Objective

Make sync dependable, observable, incremental, and safe to run repeatedly.

### User Outcome

The user can trust that repeated syncs import only new data, report progress,
and recover from failures.

### Backlog Items

#### P9-001: Implement Incremental Sync

Track last successful sync and request only new or changed data.

Acceptance criteria:

- Sync uses last successful import state.
- Re-running sync does not duplicate activities or health metrics.
- Failed sync does not advance successful sync markers incorrectly.

Validation:

- Unit tests for sync state transitions.
- Integration tests for repeated sync behavior.

#### P9-002: Implement Scheduled Sync

Add background scheduled sync based on device settings.

Acceptance criteria:

- Auto sync can be enabled and disabled.
- Sync interval is respected.
- Scheduled sync does not start if another sync is running.

Validation:

- Unit tests using controllable clock or scheduler fakes.

#### P9-003: Add WebSocket Progress Events

Stream progress for manual and scheduled syncs.

Acceptance criteria:

- UI receives progress stages and completion events.
- Errors are reported through structured events.
- Dropped UI connections do not cancel backend sync unexpectedly.

Validation:

- Backend WebSocket tests.
- Frontend interaction tests for progress updates.

#### P9-004: Improve Error Reporting and Retry

Make sync failures actionable.

Acceptance criteria:

- Known errors map to documented error codes.
- Sync history shows safe troubleshooting detail.
- Failed syncs can be retried.

Validation:

- Unit tests for error mapping.
- UI tests for retry behavior.

## Phase 10: Packaging, Privacy, and Data Management

### Objective

Prepare the app for everyday local use.

### User Outcome

The user can manage local data, understand privacy behavior, and run the app
without developer-only steps.

### Backlog Items

#### P10-001: Add Data Export

Allow exporting local data.

Acceptance criteria:

- Activities and health metrics can be exported in a documented format.
- Raw archived files can be included in export when requested.
- Export excludes chat history unless explicitly requested.
- Export operation is tested and does not mutate data.

Validation:

- Unit tests for export serialization.
- Integration test export from seeded database.

#### P10-002: Add Delete Data Controls

Allow deleting local app data and chat history.

Acceptance criteria:

- User can delete chat history.
- User can delete imported data for a device.
- Destructive actions require confirmation in the UI.

Validation:

- Backend tests for delete behavior.
- Frontend tests for confirmation flows.

#### P10-003: Package Local Desktop App

Package the app for local desktop use first.

Acceptance criteria:

- Startup path is documented.
- Production build can be created.
- Database location is configurable.
- The packaged app can run the backend, serve the UI, and use the local SQLite
  database.
- The package does not require hosted services for core functionality.

Validation:

- Build backend package.
- Build frontend production bundle.
- Run local smoke test.

#### P10-004: Preserve Hosted Website Path

Prepare the frontend and backend boundaries so a hosted website can be evaluated
later.

Acceptance criteria:

- Frontend environment configuration supports alternate API base URLs.
- Privacy implications of hosted activity, health, and chat data are documented.
- Hosted deployment is not required for the local desktop release.

Validation:

- Frontend build test with local and alternate API configuration.
- Documentation review.

## Cross-Phase Test Strategy

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
