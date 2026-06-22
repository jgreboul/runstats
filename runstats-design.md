# RunStats Application Design

## Overview

RunStats is a local-first Python and React application for collecting running
activities and health statistics from a Garmin watch over Bluetooth, storing the
normalized data in SQLite, and presenting trends, details, and sync controls in
a browser-based UI. It also includes a chatbot that lets the user ask natural
language questions about running history, activity details, and health trends.

The application has five major parts:

- A Python backend server that exposes REST and streaming APIs to the UI.
- A Bluetooth sync service that discovers, pairs with, and imports data from the
  Garmin watch.
- A SQLite database that stores watch metadata, activities, samples, health
  metrics, and sync history.
- A chatbot service that translates user questions into safe analytical queries
  against the local database and returns grounded answers.
- A React UI that shows dashboards, activity details, health trends, and watch
  connection settings.

## Goals

- Connect to a Garmin watch using Bluetooth Low Energy from the local computer.
- Allow the user to configure, pair, test, and monitor the watch connection from
  the UI.
- Export running activities and health statistics from the watch.
- Parse imported activity files and health metric payloads into normalized
  application records.
- Persist all imported data in a local SQLite database.
- Serve data to a React UI through a Python backend API.
- Allow the user to ask questions about running stats and health data in a
  chatbot interface.
- Ground chatbot answers in local database records, with enough context for the
  user to understand which metrics and time ranges were used.
- Support incremental sync so repeated imports only fetch new or changed data.
- Keep the system usable without cloud services once the watch connection is
  configured.

## Non-Goals

- Providing a public multi-user hosted service.
- Replacing Garmin Connect as a full device management platform.
- Editing workouts, routes, or watch settings.
- Performing medical interpretation of health metrics.
- Supporting every Garmin device-specific Bluetooth capability in the first
  release.

## Key Assumptions

- The first release targets local desktop use where the backend, database, and
  browser UI run on the same machine.
- The first supported Garmin family is Forerunner 935 and newer. The app should
  identify these watches as primary targets during scan, pairing, import, and
  manual testing.
- Bluetooth access is handled by the Python backend, not directly by the browser.
- The backend uses SQLite as the source of truth.
- Activity payloads are expected to be available as FIT files or equivalent
  binary records from the watch sync layer.
- Bluetooth capabilities vary by Garmin model, so the sync layer is isolated
  behind a provider interface. This allows the app to add model-specific support
  or a Garmin Connect fallback later without changing the UI or database model.
- Direct activity and health export over Bluetooth for the Forerunner 935 must
  be treated as an implementation risk until verified. The first implementation
  should support historical FIT folder import and raw file archiving so the data
  model, analytics, UI, and chatbot can progress even if direct Bluetooth export
  requires a model-specific adapter or alternate integration.
- The chatbot accesses data through read-only application tools and service
  methods. It should not execute arbitrary model-generated SQL directly against
  the database.
- The chatbot should use a configurable provider abstraction. The first provider
  target is a local model, with hosted providers considered later.
- Chat history is retained locally until the user deletes it by default. Later
  retention settings can add options such as 90-day retention or no saved chat
  history.
- AI-generated suggested workouts are a future capability. The first chatbot
  release should focus on descriptive analytics and comparison questions.
- The product should support local desktop use first and preserve a path toward
  a hosted website later.

## Proposed Technology Stack

### Backend

- Python 3.12+
- FastAPI for HTTP APIs and WebSocket sync progress updates
- Uvicorn for local development serving
- SQLAlchemy 2.x for database access
- Alembic for schema migrations
- Pydantic for API request and response models
- `bleak` for cross-platform Bluetooth Low Energy discovery and connection
- `fitparse`, `garmin-fit-sdk`, or a similar parser for FIT activity files
- APScheduler or a simple background task runner for scheduled sync
- Provider-neutral LLM client interface for chatbot responses
- Local LLM provider adapter first, such as an Ollama-compatible local HTTP
  provider
- Optional local embedding or text search support for finding relevant activity
  notes, sync logs, and saved summaries

### Database

- SQLite
- WAL mode enabled for better concurrent reads while sync writes are happening
- One local database file, for example `data/runstats.sqlite3`

### Frontend

- React
- TypeScript
- Vite
- TanStack Query for API data fetching and cache management
- React Router for navigation
- Recharts for charts
- React Leaflet and Leaflet for activity route maps
- A small component library or local design system for tables, forms, tabs,
  modals, and toasts

## High-Level Architecture

```text
+------------------+        HTTP/WebSocket        +----------------------+
| React UI         | <---------------------------> | FastAPI Backend      |
|                  |                              |                      |
| - Dashboard      |                              | - Activity API       |
| - Activities     |                              | - Health API         |
| - Health Trends  |                              | - Device API         |
| - Watch Settings |                              | - Sync API           |
| - Chat Assistant |                              | - Chat API           |
+------------------+                              +----------+-----------+
                                                               |
                                                               |
                                                       SQLAlchemy
                                                               |
                                                     +---------v---------+
                                                     | SQLite Database   |
                                                     +---------+---------+
                                                               |
                                      +------------------------+-------------------+
                                      |                                            |
                             +--------v--------+                         +---------v---------+
                             | Chat Service    |                         | Sync Service      |
                             |                 |                         |                  |
                             | - Query tools   |                         | - BLE discovery   |
                             | - LLM provider  |                         | - Pair/connect    |
                             | - Answer trace  |                         | - Export/import   |
                             +-----------------+                         | - FIT parsing     |
                                                                       +---------+---------+
                                                                                 |
                                                                                 |
                                                                       +---------v---------+
                                                                       | Garmin Watch      |
                                                                       +-------------------+
```

## Backend Modules

```text
backend/
  runstats/
    api/
      activities.py
      devices.py
      health.py
      imports.py
      settings.py
      sync.py
      chat.py
    chat/
      agent.py
      prompts.py
      tools.py
    bluetooth/
      scanner.py
      garmin_client.py
      provider.py
    db/
      models.py
      session.py
      migrations/
    importers/
      fit_importer.py
      health_importer.py
      normalizer.py
    services/
      activity_service.py
      analytics_service.py
      chat_service.py
      device_service.py
      health_service.py
      settings_service.py
      sync_service.py
    main.py
```

### API Layer

The API layer validates requests, serializes responses, and delegates business
logic to services. It should not contain Bluetooth or parser-specific code.

Primary route groups:

- `/api/devices`
- `/api/sync`
- `/api/activities`
- `/api/health`
- `/api/imports`
- `/api/chat`
- `/api/settings`

### Bluetooth Layer

The Bluetooth layer is responsible for watch discovery, connection, device
capability detection, and raw export operations.

Core interfaces:

```python
class WatchProvider:
    async def scan(self) -> list[DiscoveredWatch]:
        ...

    async def connect(self, device_id: str) -> WatchConnection:
        ...

    async def export_activities(self, since: datetime | None) -> list[RawExport]:
        ...

    async def export_health_stats(self, since: datetime | None) -> list[RawExport]:
        ...
```

The initial implementation should include a Garmin capability probe for
Forerunner 935 and newer watches. If direct activity or health export over BLE
is available, implement it behind the Garmin BLE provider. If it is not
available, keep the provider interface in place and rely on folder-based FIT
import as the bootstrap path while a model-specific adapter, Garmin Health SDK,
or Garmin Connect based integration is evaluated.

The provider interface keeps the rest of the application independent from
Garmin protocol details.

### Import Layer

The import layer converts raw watch exports into normalized domain records.

Responsibilities:

- Parse FIT files or watch payloads.
- Detect duplicate activities.
- Normalize units.
- Extract lap, split, GPS, heart-rate, cadence, elevation, and power samples.
- Extract health metrics such as resting heart rate, HRV, stress, steps, sleep,
  body battery, respiration, and pulse ox when available.
- Return structured records ready for persistence.

### Service Layer

The service layer coordinates database access and domain workflows.

Examples:

- `DeviceService.scan_for_watches()`
- `DeviceService.save_connection_settings()`
- `SyncService.run_manual_sync(device_id)`
- `ActivityService.list_activities(filters)`
- `HealthService.get_metric_series(metric, range)`
- `AnalyticsService.get_running_summary(range)`
- `ChatService.answer_question(session_id, question)`

### Chatbot Layer

The chatbot layer lets the user ask natural language questions about their
running and health data. It should be implemented as a backend service so the UI
does not need direct database or model-provider access.

Example questions:

- "How many miles did I run last month?"
- "What was my average pace for runs over 5K this year?"
- "Did my resting heart rate improve during weeks when I ran more?"
- "Show my longest run with heart-rate details."
- "Compare my weekly mileage before and after my last race."

The chatbot should answer by using approved read-only tools:

- Activity summary queries
- Activity search and filtering
- Activity detail lookup
- Health metric time-series queries
- Correlation and comparison helpers
- Sync status lookup

The model should not receive unrestricted database access. If text-to-SQL is
added later, generated SQL must be validated against an allowlist of read-only
tables, columns, aggregate functions, and row limits before execution.

Chatbot responses should include:

- A concise answer
- Key supporting numbers
- Time range used
- Relevant activities or metrics consulted
- A note when the data is incomplete or the requested metric is unavailable

The chatbot is not a medical or coaching authority. For health-related answers,
it should describe observed trends in the user's data and avoid diagnosis or
medical advice.

The first chatbot release should focus on descriptive analytics. Suggested
workouts can be added later after the analytics layer is reliable. Any workout
suggestions must be clearly labeled as general training ideas, not medical
guidance, and should explain the recent data used to generate them.

## Sync Flow

1. The user opens Watch Settings in the React UI.
2. The UI calls `POST /api/devices/scan`.
3. The backend scans for nearby BLE devices and returns likely Garmin watches.
4. The user selects a watch and starts pairing.
5. The UI calls `POST /api/devices/{device_id}/pair`.
6. The backend stores the selected watch identity and connection settings.
7. The user starts a sync from the UI, or a scheduled sync runs.
8. The backend connects to the watch.
9. The sync service requests new activity and health exports since the last
   successful sync.
10. Importers parse raw files or payloads into normalized records.
11. The service writes records to SQLite inside transactions.
12. The backend updates sync status and sends progress events to the UI.
13. The UI invalidates cached queries and refreshes dashboards and activity
   lists.

## Chatbot Flow

1. The user opens the Chat Assistant in the React UI.
2. The UI creates or resumes a chat session.
3. The user asks a natural language question.
4. The UI calls `POST /api/chat/sessions/{session_id}/messages` or opens a
   streaming chat endpoint.
5. The backend stores the user message.
6. The chat service classifies the request and selects approved analytical
   tools.
7. The selected tools query activities, health metrics, sync history, or derived
   analytics through service-layer methods.
8. The chat service sends only the needed summaries and tool results to the LLM
   provider.
9. The backend streams or returns an answer with cited metrics and time ranges.
10. The backend stores the assistant response and any tool trace metadata.

## Database Design

### `devices`

Stores known watches.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | Internal UUID |
| `name` | TEXT | Display name from watch or user |
| `model` | TEXT | Garmin model when detectable |
| `bluetooth_address` | TEXT | Platform-specific identifier |
| `serial_number` | TEXT NULL | Device serial when available |
| `firmware_version` | TEXT NULL | Last detected firmware version |
| `paired_at` | DATETIME NULL | First successful pairing time |
| `last_seen_at` | DATETIME NULL | Last BLE discovery or connection |
| `created_at` | DATETIME | Record creation time |
| `updated_at` | DATETIME | Record update time |

### `device_settings`

Stores configurable sync behavior.

| Column | Type | Notes |
| --- | --- | --- |
| `device_id` | TEXT PRIMARY KEY | References `devices.id` |
| `auto_sync_enabled` | BOOLEAN | Whether background sync is enabled |
| `sync_interval_minutes` | INTEGER | Background sync interval |
| `import_activities` | BOOLEAN | Import running activities |
| `import_health_stats` | BOOLEAN | Import health metrics |
| `preferred_units` | TEXT | `metric` or `imperial` |
| `historical_fit_import_folder` | TEXT NULL | Local FIT folder fallback |

### `device_capabilities`

Stores the latest detected capabilities for a configured watch.

| Column | Type | Notes |
| --- | --- | --- |
| `device_id` | TEXT PRIMARY KEY | References `devices.id` |
| `supports_ble_activity_export` | BOOLEAN | Direct activity export over BLE |
| `supports_ble_health_export` | BOOLEAN | Direct health export over BLE |
| `supports_folder_import` | BOOLEAN | Local folder import available |
| `capability_notes` | TEXT NULL | Human-readable probe result |
| `probed_at` | DATETIME NULL | Last capability probe time |

### `app_settings`

Stores local application preferences that are not specific to one watch.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PRIMARY KEY | Single-row settings record |
| `raw_archive_path` | TEXT | Directory for retained raw imports |
| `chat_provider` | TEXT | `local`, `hosted`, or `disabled` |
| `local_chat_provider` | TEXT | Local provider adapter, for example `ollama` |
| `hosted_chat_provider` | TEXT NULL | Hosted provider when enabled |
| `chat_retention_policy` | TEXT | `retain_until_deleted`, `retain_90_days`, or `do_not_retain` |
| `created_at` | DATETIME | Record creation time |
| `updated_at` | DATETIME | Record update time |

### `sync_runs`

Tracks sync attempts.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | Internal UUID |
| `device_id` | TEXT | References `devices.id` |
| `status` | TEXT | `running`, `succeeded`, `failed`, `cancelled` |
| `started_at` | DATETIME | Start timestamp |
| `finished_at` | DATETIME NULL | End timestamp |
| `activities_imported` | INTEGER | Count imported |
| `health_records_imported` | INTEGER | Count imported |
| `error_message` | TEXT NULL | Failure detail |

### `activities`

Stores one row per activity.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | Internal UUID |
| `device_id` | TEXT | References `devices.id` |
| `source_activity_id` | TEXT | Watch or file activity identifier |
| `sport` | TEXT | `running`, `trail_running`, etc. |
| `name` | TEXT | Display name |
| `started_at` | DATETIME | Activity start time |
| `duration_seconds` | REAL | Moving or elapsed duration |
| `distance_meters` | REAL | Total distance |
| `calories` | INTEGER NULL | Calories when available |
| `avg_heart_rate` | INTEGER NULL | Beats per minute |
| `max_heart_rate` | INTEGER NULL | Beats per minute |
| `avg_cadence` | REAL NULL | Steps per minute |
| `avg_pace_seconds_per_km` | REAL NULL | Normalized pace |
| `elevation_gain_meters` | REAL NULL | Total ascent |
| `training_effect` | REAL NULL | Garmin training metric if available |
| `raw_file_id` | TEXT NULL | References imported raw file |
| `created_at` | DATETIME | Import timestamp |

Add a unique index on `(device_id, source_activity_id)` to prevent duplicate
imports.

### `activity_laps`

Stores lap and split summaries.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | Internal UUID |
| `activity_id` | TEXT | References `activities.id` |
| `lap_index` | INTEGER | Zero-based order |
| `started_at` | DATETIME | Lap start |
| `duration_seconds` | REAL | Lap duration |
| `distance_meters` | REAL | Lap distance |
| `avg_heart_rate` | INTEGER NULL | Beats per minute |
| `avg_pace_seconds_per_km` | REAL NULL | Lap pace |

### `activity_samples`

Stores time-series samples for charts and maps.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | Local row id |
| `activity_id` | TEXT | References `activities.id` |
| `sample_time` | DATETIME | Timestamp |
| `elapsed_seconds` | REAL | Seconds from activity start |
| `distance_meters` | REAL NULL | Cumulative distance |
| `latitude` | REAL NULL | GPS latitude |
| `longitude` | REAL NULL | GPS longitude |
| `elevation_meters` | REAL NULL | Elevation |
| `heart_rate` | INTEGER NULL | Beats per minute |
| `cadence` | REAL NULL | Steps per minute |
| `power_watts` | REAL NULL | Running power |
| `speed_meters_per_second` | REAL NULL | Speed |

Add an index on `(activity_id, elapsed_seconds)`.

### `health_metrics`

Stores daily or timestamped health values.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | Local row id |
| `device_id` | TEXT | References `devices.id` |
| `metric_type` | TEXT | `steps`, `resting_hr`, `hrv`, `sleep`, etc. |
| `start_time` | DATETIME | Metric interval start |
| `end_time` | DATETIME NULL | Metric interval end |
| `value` | REAL | Numeric value |
| `unit` | TEXT | Unit label |
| `source_record_id` | TEXT NULL | Source identifier |

Add an index on `(metric_type, start_time)`.

### `raw_imports`

Stores metadata for raw exported files or payloads.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | Internal UUID |
| `device_id` | TEXT | References `devices.id` |
| `source_id` | TEXT | Source file or payload identifier |
| `kind` | TEXT | `activity_fit`, `health_payload`, etc. |
| `sha256` | TEXT | Content hash |
| `storage_path` | TEXT | Local archived raw file path |
| `imported_at` | DATETIME | Import timestamp |

Raw exports should be retained on disk by default for archiving and replay. The
default archive location should be configurable, for example
`data/archive/raw-imports/`.

### `chat_sessions`

Stores chatbot conversations.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | Internal UUID |
| `title` | TEXT NULL | Optional generated or user-edited title |
| `created_at` | DATETIME | Session creation time |
| `updated_at` | DATETIME | Last message time |

### `chat_messages`

Stores user and assistant messages.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | Internal UUID |
| `session_id` | TEXT | References `chat_sessions.id` |
| `role` | TEXT | `user`, `assistant`, `system`, or `tool` |
| `content` | TEXT | Message text |
| `tool_trace_json` | TEXT NULL | JSON summary of tool calls and result metadata |
| `created_at` | DATETIME | Message timestamp |

Tool traces should store query intent, date range, metric names, row counts, and
referenced activity ids. They should not store large duplicated result sets.

Chat history is retained locally until deleted by default. A later settings
screen can expose retention options such as retain forever, retain for 90 days,
or do not retain completed sessions.

## API Design

### Device and Connection APIs

`POST /api/devices/scan`

Starts a Bluetooth scan and returns discovered watches.

```json
{
  "scan_seconds": 10
}
```

Response:

```json
{
  "devices": [
    {
      "id": "ble-identifier",
      "name": "Garmin Forerunner",
      "rssi": -58,
      "model_hint": "Forerunner",
      "is_known": false
    }
  ]
}
```

`POST /api/devices/pair`

Pairs or registers a selected watch.

```json
{
  "bluetooth_device_id": "ble-identifier",
  "display_name": "My Forerunner"
}
```

`GET /api/devices`

Lists configured watches.

`PATCH /api/devices/{device_id}/settings`

Updates sync and unit settings.

`POST /api/devices/{device_id}/test-connection`

Attempts to connect and returns device status.

`POST /api/devices/{device_id}/probe-capabilities`

Runs a capability probe for the configured watch.

Response:

```json
{
  "device_id": "device-uuid",
  "supports_ble_activity_export": false,
  "supports_ble_health_export": false,
  "supports_folder_import": true,
  "capability_notes": "Direct BLE export was not detected for this device. Use folder import until another adapter is configured."
}
```

`GET /api/devices/{device_id}/capabilities`

Returns the latest stored capability result.

### Settings APIs

`GET /api/settings`

Returns application settings such as raw archive location, chatbot provider,
and chat retention policy.

`PATCH /api/settings`

Updates application settings.

Example request:

```json
{
  "raw_archive_path": "data/archive/raw-imports",
  "chat_provider": "local",
  "local_chat_provider": "ollama",
  "chat_retention_policy": "retain_until_deleted"
}
```

### Sync APIs

`POST /api/sync-runs`

Starts a manual sync.

```json
{
  "device_id": "device-uuid",
  "include_activities": true,
  "include_health": true
}
```

`GET /api/sync-runs`

Lists recent sync attempts.

`GET /api/sync-runs/{sync_run_id}`

Returns one sync run.

`WS /api/sync-runs/{sync_run_id}/events`

Streams sync progress events.

Example event:

```json
{
  "type": "progress",
  "stage": "importing_activities",
  "message": "Imported 3 of 8 activities",
  "percent": 62
}
```

### Activity APIs

`GET /api/activities`

Supports filters:

- `from`
- `to`
- `sport`
- `min_distance_meters`
- `max_distance_meters`
- `limit`
- `offset`

`GET /api/activities/{activity_id}`

Returns summary, laps, and selected derived stats.

`GET /api/activities/{activity_id}/samples`

Returns time-series samples for charts and maps.

`GET /api/activities/summary`

Returns aggregate totals by week, month, or year.

### Health APIs

`GET /api/health/metrics`

Lists available metric types.

`GET /api/health/series`

Query parameters:

- `metric_type`
- `from`
- `to`
- `bucket`

Returns chart-ready health metric values.

### Import APIs

`POST /api/imports/fit-folder`

Imports historical FIT files from a local folder and stores retained raw files
in the configured archive location.

```json
{
  "device_id": "device-uuid",
  "folder_path": "D:/Garmin/Activities",
  "recursive": true
}
```

Response:

```json
{
  "created": 24,
  "skipped": 3,
  "failed": 1,
  "raw_files_archived": 24
}
```

### Chat APIs

`POST /api/chat/sessions`

Creates a new chat session.

```json
{
  "title": "Spring training questions"
}
```

`GET /api/chat/sessions`

Lists recent chat sessions.

`GET /api/chat/sessions/{session_id}`

Returns a chat session with messages.

`DELETE /api/chat/sessions/{session_id}`

Deletes one chat session and its messages.

`DELETE /api/chat/sessions`

Deletes all chat history.

`POST /api/chat/sessions/{session_id}/messages`

Sends a user question and returns the assistant response.

```json
{
  "message": "How did my weekly mileage change over the last 12 weeks?"
}
```

Response:

```json
{
  "message_id": "assistant-message-uuid",
  "answer": "You averaged 24.6 km per week over the last 12 weeks, up from 18.2 km in the previous 12-week period.",
  "supporting_data": {
    "time_range": "2026-03-28 to 2026-06-20",
    "metrics": ["weekly_distance"],
    "activity_count": 38
  }
}
```

`WS /api/chat/sessions/{session_id}/stream`

Streams assistant tokens and tool progress for longer answers.

Example stream event:

```json
{
  "type": "tool_result",
  "tool": "weekly_running_summary",
  "summary": "12 weekly buckets returned"
}
```

## React UI Design

### Main Navigation

- Dashboard
- Activities
- Health
- Chat Assistant
- Watch Settings
- Sync History

### Dashboard

The dashboard gives a quick view of recent running and health trends.

Primary widgets:

- Weekly running distance
- Monthly running distance
- Recent activities
- Pace trend
- Heart-rate trend
- Steps trend
- Last sync status

### Activities View

The activities view supports scanning, filtering, and drilling into details.

Features:

- Activity table with date, name, distance, pace, time, heart rate, and elevation
- Filters for date range, sport, distance, and search text
- Activity detail page with summary cards
- Lap table
- Pace, heart-rate, cadence, elevation, and power charts
- GPS map when coordinates are available

### Health View

The health view shows longer-term wellness trends.

Features:

- Metric selector
- Date range selector
- Daily, weekly, and monthly aggregation
- Charts for steps, resting heart rate, HRV, sleep duration, stress, and body
  battery when available
- Data availability states for unsupported watch metrics

### Chat Assistant View

The Chat Assistant view provides a conversational way to inspect running and
health data.

Features:

- Chat session list
- Message composer
- Streaming assistant responses
- Suggested starter questions based on available data
- Inline supporting numbers for answers
- Links from answers to referenced activities, health charts, or sync runs
- Clear unavailable-data states when the question depends on missing metrics
- Option to delete chat history

The assistant should be useful for exploratory questions, comparisons, and quick
summaries. Examples include:

- "What is my fastest 5K this year?"
- "Which runs had unusually high heart rate for their pace?"
- "Summarize my sleep and training load for the past month."
- "Did my cadence change on longer runs?"
- "What changed after my last watch sync?"

### Watch Settings View

The Watch Settings view is where the user configures the Garmin connection.

Features:

- Bluetooth permission and adapter status
- Scan for watches
- List discovered watches with signal strength and known-device status
- Pair or reconnect selected watch
- Rename configured watch
- Test connection
- Probe and display watch import capabilities
- Show whether direct BLE activity export, direct BLE health export, and folder
  import are supported
- Toggle automatic sync
- Configure sync interval
- Choose whether to import activities, health stats, or both
- Choose a folder for historical FIT import when direct export is unavailable
- Choose preferred units
- Show last successful sync and last failed sync
- Manual sync button
- Connection troubleshooting messages from backend status codes

Suggested UI states:

- No watch configured
- Bluetooth unavailable
- Scanning
- Watch discovered
- Pairing
- Connected
- Syncing
- Sync failed
- Last sync succeeded

### Sync History View

The sync history view helps diagnose imports.

Features:

- List of sync runs
- Status, start time, duration, imported counts, and error message
- Drill into sync stages and warnings
- Retry failed sync

## Data Normalization

All imported values should be stored in canonical metric units:

- Distance: meters
- Duration: seconds
- Speed: meters per second
- Pace: seconds per kilometer
- Elevation: meters
- Temperature: Celsius
- Heart rate: beats per minute
- Cadence: steps per minute
- Power: watts

The UI can convert values for display based on user preferences.

## Duplicate Detection

Duplicate detection should use multiple signals:

- Device id
- Source activity id
- FIT file checksum
- Activity start time
- Duration and distance tolerance

The primary uniqueness rule is `(device_id, source_activity_id)`. If the source
activity id is missing, the importer should fall back to checksum and activity
start time matching.

## Error Handling

Backend errors should use structured responses:

```json
{
  "error": {
    "code": "WATCH_CONNECTION_FAILED",
    "message": "Unable to connect to the configured watch.",
    "details": {
      "device_id": "device-uuid"
    }
  }
}
```

Common error codes:

- `BLUETOOTH_UNAVAILABLE`
- `WATCH_NOT_FOUND`
- `WATCH_CONNECTION_FAILED`
- `WATCH_PAIRING_FAILED`
- `WATCH_EXPORT_FAILED`
- `IMPORT_PARSE_FAILED`
- `DATABASE_WRITE_FAILED`
- `SYNC_ALREADY_RUNNING`
- `CHAT_MODEL_UNAVAILABLE`
- `CHAT_QUERY_UNSUPPORTED`
- `CHAT_TOOL_FAILED`

The UI should show concise user-facing messages and keep technical detail
available in sync history.

## Security and Privacy

- Store data locally by default.
- Retain raw imported files locally by default for archive and replay.
- Do not transmit activity or health data to external services unless a future
  feature explicitly enables that behavior.
- Avoid storing Bluetooth secrets or tokens in plain text when the platform
  provides secure credential storage.
- Treat health data as sensitive.
- Make chatbot provider choice explicit if a hosted model would receive user
  questions or summarized health and activity data.
- Default the chatbot provider to a local model adapter.
- Keep chatbot database access read-only.
- Retain chat history locally by default and allow users to delete it.
- Make database location configurable.
- Provide an export and delete-data path in a future release.

## Development Milestones

### Milestone 1: Local Backend and Database

- Create FastAPI application skeleton.
- Create SQLite models and migrations.
- Add activity, health, and basic analytics query APIs with sample seeded data.
- Add basic React shell and dashboard.

### Milestone 2: Watch Configuration UI

- Add device scan, pair, settings, and test-connection API contracts.
- Implement Watch Settings UI using mocked backend responses.
- Add sync history table.

### Milestone 3: Forerunner Discovery and Connection

- Integrate `bleak`.
- Implement Bluetooth adapter status and scan for Forerunner 935 and newer.
- Store selected watch in SQLite.
- Add connection testing.
- Add a capability probe to determine whether direct activity and health export
  are available over BLE for the target watch.

### Milestone 4: Activity Import

- Implement local raw file archiving.
- Support folder-based historical FIT import as the bootstrap and fallback path.
- Parse FIT files.
- Store activities, laps, samples, and raw import metadata.
- Render activity list and detail pages from real data.
- Add direct watch export only after target-device capability is verified.

### Milestone 5: Health Import

- Export supported health metrics.
- Store normalized health records.
- Render health trend charts.

### Milestone 6: Chat Assistant

- Add chat session and message storage.
- Implement read-only analytics tools for common running and health questions.
- Add provider-neutral LLM client interface with a local-model provider first.
- Add Chat Assistant UI with streaming responses.
- Link chatbot answers back to activities and health charts.
- Limit the first release to descriptive analytics.

### Milestone 7: Sync Polish

- Add incremental sync.
- Add scheduled sync.
- Add WebSocket progress updates.
- Improve error messages and retry behavior.

### Milestone 8: Packaging and Future Guidance

- Package the app for local desktop use.
- Keep the frontend compatible with a future hosted website deployment.
- Add export and delete-data flows.
- Add chatbot retention settings.
- Add suggested workouts after descriptive analytics are reliable and validated.

## Resolved Product Decisions

- First supported watch family: Garmin Forerunner 935 and newer.
- Direct BLE export from Forerunner 935 is unknown and must be verified through
  a capability probe.
- Raw exported files should be retained locally for archiving and replay.
- Historical FIT folder import should be supported as a bootstrap and fallback
  path.
- Product delivery should support local desktop use first and keep a future
  hosted website path open.
- Standard charting library: Recharts.
- Standard mapping library: React Leaflet with Leaflet.
- Chatbot provider: configurable, starting with a local model provider.
- Chat history retention: retain locally until deleted by default.
- Chatbot scope: descriptive analytics first; suggested workouts later.

## Remaining Open Questions

- Which Forerunner 935+ models should be included in the first manual hardware
  validation matrix beyond the Forerunner 935 itself?
- If direct BLE export is not available, should the first alternate integration
  be folder import only, Garmin Health SDK, Garmin Connect Developer Program
  APIs, or another Garmin Connect based path?
- Which local model runtime and model should be the default recommendation for
  the chatbot after hardware requirements are known?
- What hosted deployment model is desired later: static frontend plus local
  backend, fully hosted backend, or desktop app with optional remote access?

## Recommended First Implementation Path

Start with the backend API, SQLite schema, and React UI using seeded or
folder-imported FIT files. This validates the data model, analytics service, UI,
and chatbot question-answering flow before depending on device-specific
Bluetooth export behavior. Add local raw file archiving from the beginning.
Then add the Forerunner capability probe and Bluetooth provider behind the
`WatchProvider` interface, connecting any verified direct export path to the
same importer pipeline.
