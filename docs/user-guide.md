# RunStats User Guide

RunStats is a local-first running and health dashboard for Garmin watch data.
It stores your activities, health metrics, watch settings, sync history, and
chat history on your own computer.

This guide is for using the app after it has already been installed and started.
For developer setup, see `local-setup.md`.

## Getting Started

Open the app in your browser:

```text
http://127.0.0.1:8000
```

If you are running the frontend development server separately, open:

```text
http://127.0.0.1:5173
```

The app navigation includes:

- Dashboard
- Activities
- Health
- Chat Assistant
- Watch Settings
- Sync History
- Data Management

## Connect A Watch

Open Watch Settings to scan for and configure a Garmin watch.

1. Turn off Bluetooth on your phone if Garmin Connect keeps reconnecting to the
   watch.
2. Put the watch into its Pair Phone or discoverable Bluetooth mode.
3. In RunStats, open Watch Settings.
4. Click Scan.
5. Click Pair on the discovered physical watch.

RunStats can use Bluetooth to discover and identify supported Garmin watches.
Direct Bluetooth activity and health export is not currently available for the
Forerunner testing path, so imported activity history uses FIT files from a
folder.

## Import Activity FIT Files

FIT folder import is the main path for bringing real activity history into
RunStats.

Use one of these sources:

- A Garmin watch mounted as a drive over USB
- A folder copied from the watch's `GARMIN/ACTIVITY` directory
- A Garmin export folder containing `.fit` activity files

To import from the UI:

1. Open Watch Settings.
2. Select the physical watch.
3. Enter the full folder path in Historical FIT import folder.
4. Click Save settings.
5. Click Import FIT folder.

Example Windows path:

```text
E:\GARMIN\ACTIVITY
```

If Windows shows the watch as a portable device without a normal drive path,
copy the `.FIT` files to a normal local folder first, then enter that folder
path in RunStats.

If the import reports `0 FIT files checked`, RunStats reached the folder but did
not find files ending in `.fit`. Check the path and confirm the folder contains
activity FIT files.

On Windows, you can verify the folder contents with:

```powershell
Get-ChildItem -Path "E:\GARMIN\ACTIVITY" -Recurse -Filter *.fit
```

## Dashboard

The Dashboard summarizes your imported running data.

Use it to check recent totals, weekly or monthly distance, and recent activity
trends. If the Dashboard looks empty, import activity FIT files first or confirm
that you are using the intended local database.

## Activities

Open Activities to browse imported runs.

You can review:

- Activity name, sport, date, distance, duration, and pace
- Heart rate and elevation fields when present in the FIT file
- Activity detail pages with laps, samples, charts, and route data when the FIT
  file includes those records

If an imported run has less detail than expected, the original FIT file may not
contain laps, GPS points, or sensor samples.

## Health

Open Health to view imported health metrics such as steps, resting heart rate,
HRV, sleep, stress, body battery, respiration, and pulse ox.

Direct Bluetooth health export is not currently assumed. Health data appears
only after supported health payloads have been imported. If a metric is
unavailable, RunStats will show an empty or unavailable state rather than
guessing.

## Manual Sync

The Start sync button in Watch Settings attempts the configured direct sync path
for the selected watch.

For the current Forerunner testing path, direct Bluetooth activity and health
export may report unavailable. That is expected. Use Import FIT folder for
activity history.

Sync History records sync attempts, status, imported counts, and error codes so
you can see what happened after each attempt.

## Chat Assistant

Open Chat Assistant to ask questions about your local RunStats data.

Good questions include:

- How much did I run each week?
- What was my longest run?
- How has my pace changed recently?
- What changed after my last sync?

The assistant is grounded in approved read-only tools over your local data. If
the configured local chat model is unavailable, the app will show an error such
as `CHAT_MODEL_UNAVAILABLE`.

## Data Management

Open Data Management to export or delete local data.

You can:

- Export local RunStats data as JSON
- Include or exclude raw archived files
- Include or exclude chat history
- Delete chat history
- Delete imported activity, health, and raw-file data for a device while keeping
  the configured watch record

Deletion actions require confirmation. Sync history is retained for auditability
when imported data is deleted.

## Privacy

RunStats is local-first. By default, your data is stored in the configured local
SQLite database and raw archive folder on your computer.

Be aware that exports can include sensitive personal data, including activity
routes, heart rate, health metrics, raw files, and chat history if you choose to
include it.

For more detail, see `privacy-and-data-management.md`.

## Troubleshooting

If the app cannot load data:

- Confirm the backend is running.
- Open `http://127.0.0.1:8000/api/healthcheck`.
- If using the Vite frontend, confirm it can proxy API requests to the backend.

If scan finds no watch:

- Confirm Bluetooth is enabled.
- Put the watch into Pair Phone or discoverable mode.
- Turn off phone Bluetooth temporarily.
- Keep the watch close to the computer and keep the screen awake.

If Test connection or Probe capabilities fails:

- Discovery only proves the watch is advertising.
- Connection and probing require a direct BLE connection, which may fail if the
  watch reconnects to a phone or leaves pairing mode.
- Retry after reopening the watch's pairing screen.
- Remove stale Windows Bluetooth pairings if Windows shows the watch but
  RunStats cannot connect.

If Import FIT folder reports zero files:

- Confirm the folder path is correct.
- Confirm the folder contains files ending in `.fit`.
- Copy files from a portable-device view to a normal local folder if the watch
  does not expose a normal drive path.

If imported activities do not appear:

- Open Activities and refresh the browser.
- Confirm the import summary showed created files, not only skipped or failed
  files.
- Check Sync History or backend logs for import errors.

## Current Limitations

- Direct Bluetooth activity export is not currently implemented for the tested
  Forerunner flow.
- Direct Bluetooth health export is not currently assumed.
- Activity history import uses local FIT files.
- Health metrics require supported health payload imports.
- The app is designed for local use and does not currently provide account
  login, cloud sync, or hosted storage.
