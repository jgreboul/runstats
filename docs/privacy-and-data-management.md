# Privacy and Data Management

RunStats is local-first. Activity summaries, health metrics, raw imported files,
sync history, device settings, and chat history are stored in the configured
local SQLite database and raw archive folder unless a future feature explicitly
adds a remote service.

## Export Format

`POST /api/data-management/export` returns JSON with this top-level shape:

```json
{
  "format_version": "runstats.local-data.v1",
  "exported_at": "2026-06-22T12:00:00Z",
  "include_raw_files": false,
  "include_chat_history": false,
  "counts": {},
  "devices": [],
  "activities": [],
  "health_metrics": [],
  "raw_imports": [],
  "raw_files": [],
  "chat_sessions": []
}
```

Activities include laps and samples. Health metrics use the normalized metric
names and canonical units used by the database. Raw import metadata is always
included so an export explains where records came from.

Raw archived file content is included only when `include_raw_files` is true.
Included raw files are represented as base64 strings in `raw_files`, alongside
their raw import id, source id, kind, SHA-256 hash, local storage path, byte
size, and missing/read status.

Chat history is excluded unless `include_chat_history` is true. When included,
chat sessions contain message content and stored tool trace JSON, so the export
may contain user questions and summarized activity or health context.

## Delete Controls

`DELETE /api/data-management/chat-history` deletes all local chat sessions and
messages.

`DELETE /api/data-management/devices/{device_id}/imported-data` keeps the
configured device and settings, then deletes imported activities, activity laps,
activity samples, health metrics, raw import records, and archived raw files for
that device. Sync history is retained so failed or past sync attempts remain
auditable.

The React Data Management screen requires explicit confirmation before calling
these destructive APIs.

## Hosted Website Considerations

The frontend already supports alternate API origins through
`VITE_RUNSTATS_API_BASE_URL`, which keeps open a future hosted-frontend or
hosted-backend evaluation path. A hosted deployment is not part of the local
desktop release.

Before enabling any hosted backend or hosted chatbot provider, RunStats must
treat activity routes, health metrics, raw files, chat prompts, and chat tool
summaries as sensitive personal data. Hosted use would need explicit opt-in,
clear provider disclosure, retention settings, transport security, account or
access controls, and a deletion/export story that covers both local and hosted
copies.
