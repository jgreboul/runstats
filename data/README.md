# RunStats Local Data

This folder is reserved for local runtime data such as SQLite databases, raw
import archives, and temporary real-device test files.

Most files in this folder are intentionally ignored by Git because they can
contain sensitive personal activity, location, health, raw watch, and chat data.

## File Inventory

| Path | Purpose |
| --- | --- |
| `.gitkeep` | Keeps the `data/` directory present in a fresh checkout. |
| `README.md` | Explains the local data directory and privacy expectations. |

## Common Local Files

These files may appear while using or testing RunStats, but they should not be
committed:

| Path | Purpose |
| --- | --- |
| `runstats.sqlite3` | Default local SQLite database when no custom database path is configured. |
| `real-device.sqlite3` | Example real-device testing database from `docs/local-setup.md`. |
| `seeded-sandbox.sqlite3` | Optional deterministic sample-data database. |
| `archive/raw-imports/` | Raw imported FIT or health payload archive folder. |
| `*.sqlite3-wal` and `*.sqlite3-shm` | SQLite write-ahead log and shared-memory sidecar files. |

Before sharing logs, screenshots, exports, or database files from this folder,
check for activity routes, timestamps, health metrics, device identifiers, and
chat history.
