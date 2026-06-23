# Local Setup

This guide helps a junior engineer run RunStats locally against a real Garmin
watch and a local Ollama model. The default path below is real hardware testing,
not the fake provider used by automated tests.

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
- Bluetooth enabled on the test computer
- A Garmin Forerunner 935 or newer watch, charged and nearby
- Ollama installed locally

Check the basics:

```bash
python --version
uv --version
node --version
npm --version
ollama --version
```

## First Install

From the repository root:

```bash
npm run install:all
```

This installs backend dependencies with `uv` and frontend dependencies with
npm.

Install the browser used by the end-to-end validation suite:

```bash
npm run e2e:install
```

## Create A Real-Device `.env`

Copy the template:

```powershell
Copy-Item .env.example .env
```

For macOS or Linux shells:

```bash
cp .env.example .env
```

Use these values for real local testing:

```dotenv
RUNSTATS_DATABASE_PATH=./data/real-device.sqlite3
RUNSTATS_RAW_ARCHIVE_PATH=./data/archive/raw-imports
RUNSTATS_FRONTEND_DIST_PATH=./frontend/dist
RUNSTATS_WATCH_PROVIDER=bleak
RUNSTATS_LOCAL_CHAT_BASE_URL=http://127.0.0.1:11434
RUNSTATS_LOCAL_CHAT_MODEL=gemma2
RUNSTATS_LOCAL_CHAT_TIMEOUT_SECONDS=30
RUNSTATS_SYNC_SCHEDULER_POLL_SECONDS=60
```

Relative paths in `.env` are resolved from the repository root. Use absolute
paths if you want the database or archive somewhere else.

Use `RUNSTATS_WATCH_PROVIDER=fake` only when you intentionally want deterministic
mock watch behavior. Real-device testing uses `bleak`.

## Prepare Ollama

Pull the starting local model:

```bash
ollama pull gemma2
```

Start Ollama if your installation does not run it automatically:

```bash
ollama serve
```

In another terminal, confirm Ollama responds:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

For macOS or Linux shells:

```bash
curl http://127.0.0.1:11434/api/tags
```

You should see `gemma2` in the local model list after `ollama pull gemma2`.

## Prepare The Database

From the repository root:

```bash
cd backend
uv run alembic upgrade head
cd ..
```

Do not seed the real-device database unless you specifically want sample data
mixed into the same SQLite file. For a clean hardware test, start with the empty
database created by migrations.

Optional seeded sandbox:

```bash
uv --project backend run python -m runstats.db.seed --database-path data/seeded-sandbox.sqlite3
```

The seed command is a one-shot database task. It writes deterministic sample
rows, prints a JSON summary, and returns to the prompt. It does not start
FastAPI, Vite, or any background server. If something is still listening on
port `8000` or `5173` after this command exits, it is an earlier app process
that should be stopped separately.

To run the seeded sandbox as a single foreground app in the active terminal,
build the frontend and start the combined local server against that database:

```bash
npm run package:frontend
uv --project backend run runstats-local --database-path data/seeded-sandbox.sqlite3
```

This applies migrations, starts FastAPI, and serves the built React app from
`frontend/dist` at:

```text
http://127.0.0.1:8000
```

Keep that terminal open while testing. Press `Ctrl+C` in the same terminal to
stop the app.

## Put The Watch In A Discoverable State

Before scanning from RunStats:

1. Charge the watch or keep it above low battery.
2. Keep it within a few feet of the computer.
3. Enable Bluetooth on the computer.
4. Put the watch into its phone-pairing or discoverable Bluetooth flow.
5. If Garmin Connect on a phone keeps taking the connection, temporarily turn
   off phone Bluetooth during the test.

The exact watch menu varies by model. On many Forerunner models, look for a
phone, Bluetooth, or Pair Phone option in settings.

## Run The Backend

Open terminal 1 at the repository root:

```bash
cd backend
uv run uvicorn runstats.main:app --reload
```

This is a foreground development server. Keep terminal 1 open while testing and
press `Ctrl+C` in that terminal to stop the backend.

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

## Run The Frontend

Open terminal 2 at the repository root:

```bash
npm run frontend:dev
```

This is a foreground development server. Keep terminal 2 open while testing and
press `Ctrl+C` in that terminal to stop the frontend.

The frontend usually listens on:

```text
http://127.0.0.1:5173
```

Open that URL in a browser. The Vite dev server proxies `/api` requests to the
backend at `http://127.0.0.1:8000`.

## Real Device Validation Checklist

Use this checklist for a first hardware pass.

1. Open Watch Settings.
2. Click Scan.
3. Confirm the real Garmin watch appears.
4. Pair the watch.
5. Click Test connection.
6. Click Probe capabilities.
7. Record whether direct BLE activity export or direct BLE health export is
   detected.
8. Open Sync History and verify the app remains responsive after the probe.
9. Ask Chat Assistant: `What changed after my last sync?`
10. Confirm the answer is produced by the local `gemma2` model or, if Ollama is
    unavailable, that the UI reports `CHAT_MODEL_UNAVAILABLE`.

Current expected limitation: direct BLE export is not assumed for Forerunner
935+ watches. If the capability probe does not detect a known export service,
manual sync can fail with `WATCH_EXPORT_FAILED`. That is a valid result for the
hardware validation pass. Use folder-based FIT import next.

## Import Real Activity FIT Files

If direct BLE export is unavailable, import FIT files from a local folder.
Common sources are:

- A mounted Garmin watch over USB
- A folder copied from the watch's `GARMIN/ACTIVITY` directory
- A Garmin export folder containing `.fit` activity files

First, get the device id after pairing:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/devices | ConvertTo-Json -Depth 8
```

For macOS or Linux shells:

```bash
curl http://127.0.0.1:8000/api/devices
```

Then import the FIT folder:

```bash
cd backend
uv run python -m runstats.importers.fit_folder --device-id <device-id> --folder-path "E:\GARMIN\ACTIVITY"
cd ..
```

Replace `<device-id>` with the paired device id and replace the folder path with
the real path on your machine.

You can also import from the UI:

1. Open Watch Settings.
2. Select the physical watch.
3. Enter the folder path in Historical FIT import folder.
4. Click Save settings.
5. Click Import FIT folder.

After import:

1. Open Activities and confirm real runs appear.
2. Click a real activity and confirm laps, samples, charts, and route data load
   when present in the FIT file.
3. Open Dashboard and confirm totals update.
4. Ask Chat Assistant: `How much did I run each week?`

## Import Real Health Payloads

Direct BLE health export is currently not assumed. If you have a supported
local JSON health payload, import it through the API:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Uri http://127.0.0.1:8000/api/imports/health-payload `
  -Body '{"device_id":"<device-id>","file_path":"D:/Garmin/Health/daily-health.json"}'
```

Supported metric names normalize to `steps`, `resting_hr`, `hrv`, `sleep`,
`stress`, `body_battery`, `respiration`, and `pulse_ox`.

## Run The Local Production App

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

## Automated Validation

Run the standard validation suite from the repository root:

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

Run browser-level end-to-end validation:

```bash
npm run e2e
```

The e2e suite starts a temporary local backend with seeded data, the fake watch
provider, and a fake chat provider. It validates the implemented app end to end
without requiring physical hardware or Ollama.

Real-device validation is manual because it depends on local Bluetooth hardware,
watch state, operating-system permissions, and the specific Garmin model.

## Troubleshooting

If the frontend cannot load data:

- Confirm the backend terminal is still running.
- Open `http://127.0.0.1:8000/api/healthcheck`.
- Confirm the frontend was started with `npm run frontend:dev`.
- Avoid setting `VITE_RUNSTATS_API_BASE_URL` unless you need a custom backend
  origin.

If the database has no data:

- Confirm you are using the intended `RUNSTATS_DATABASE_PATH`.
- Run `cd backend`.
- Run `uv run alembic upgrade head`.
- Import real FIT files or intentionally seed a sandbox database.
- Restart the backend.

If Watch Settings scan fails:

- Confirm `.env` has `RUNSTATS_WATCH_PROVIDER=bleak`.
- Confirm Bluetooth is enabled.
- Confirm the operating system has granted Bluetooth or local device access.
- Keep the watch nearby and in a discoverable state.
- Temporarily disable phone Bluetooth if the phone keeps reconnecting first.
- Restart the backend after changing `.env`.

If scan works but Test connection or Probe capabilities targets
`seed-device-forerunner-935`:

- The app is using the seeded sample watch, not the physical watch.
- In Watch Settings, choose the newly paired watch from the Watch dropdown. The
  real watch id is a UUID, and its Bluetooth address should look like a normal
  adapter address rather than `seed-ble-forerunner-935`.
- For hardware testing, prefer the clean real-device database from
  `RUNSTATS_DATABASE_PATH=./data/real-device.sqlite3` instead of the seeded
  sandbox database.

If scan works for the physical watch but Test connection or Probe capabilities
fails:

- Discovery only proves the watch is advertising. Test connection and Probe
  capabilities require a direct BLE/GATT connection, which can fail if the watch
  has stopped advertising, left pairing mode, or reconnected to a phone.
- Keep phone Bluetooth off during the test, keep the watch awake, and reopen the
  watch's Pair Phone or discoverable Bluetooth screen before retrying.
- Remove stale Windows Bluetooth pairings for the watch and pair again from
  RunStats if Windows shows the watch but RunStats cannot connect.
- Direct BLE activity and health export can still be unavailable after a
  successful probe. In that case, use folder-based FIT import for activities and
  supported health payload imports for health metrics.

If Test connection fails:

- Wake the watch screen and keep it nearby.
- Retry after a fresh scan.
- Remove stale OS-level Bluetooth pairings if the operating system shows the
  watch but RunStats cannot connect.
- Check Sync History or backend logs for stable error codes.

If direct sync fails with `WATCH_EXPORT_FAILED`:

- This can be expected for current Forerunner testing.
- Use folder-based FIT import for activities.
- Use supported JSON health payload import for health metrics.
- Keep the capability probe notes with the test report.

If Chat Assistant answers fail:

- Confirm Ollama is running.
- Run `ollama pull gemma2`.
- Confirm `.env` has `RUNSTATS_LOCAL_CHAT_MODEL=gemma2`.
- Confirm `RUNSTATS_LOCAL_CHAT_BASE_URL` matches your local Ollama endpoint.
- The backend error code `CHAT_MODEL_UNAVAILABLE` means RunStats could query
  local data but could not reach the configured chat model.

If the backend fails with `WinError 10013` or a port is already in use:

- Check whether another process is listening on the default backend port:

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess
```

- If the owner is a stale local dev process, stop it from the terminal where it
  is running, or stop it by process id:

```powershell
Stop-Process -Id <OwningProcess>
```

- Or run Uvicorn on another port:

```bash
cd backend
uv run uvicorn runstats.main:app --reload --port 8001
```

Then start the frontend with an explicit backend URL:

```powershell
$env:VITE_RUNSTATS_API_BASE_URL="http://127.0.0.1:8001"
npm run frontend:dev
```
