# Chat Assistant

RunStats Chat Assistant answers descriptive questions about imported local
running, health, and sync data. It uses a fixed set of backend tools instead of
letting a model run arbitrary SQL.

## Current Release

Implemented chat surfaces:

- Local chat session and message persistence.
- `POST /api/chat/sessions`, `GET /api/chat/sessions`,
  `GET /api/chat/sessions/{session_id}`, `DELETE /api/chat/sessions`, and
  `POST /api/chat/sessions/{session_id}/messages`.
- Read-only tools for weekly and monthly running summaries, fastest and longest
  runs, activity detail lookup, health metric trends, activity-to-health
  comparisons, and recent sync status.
- A provider abstraction with a fake provider for tests and an
  Ollama-compatible local HTTP provider for local model use.
- React Chat Assistant UI with session resume, starter questions, answer
  supporting data, references back to app views, pending states, error states,
  and delete-history controls.

Tool traces are stored as lightweight metadata: intent, tool names, row counts,
time range, metrics, notes, and referenced activity, health, or sync IDs.

## Local Model Configuration

Chat provider selection is stored in app settings. The default provider is
local with `local_chat_provider = "ollama"`.

Runtime environment variables for the local model adapter:

```bash
$env:RUNSTATS_LOCAL_CHAT_BASE_URL="http://127.0.0.1:11434"
$env:RUNSTATS_LOCAL_CHAT_MODEL="llama3.2"
$env:RUNSTATS_LOCAL_CHAT_TIMEOUT_SECONDS="20"
```

For macOS or Linux shells:

```bash
export RUNSTATS_LOCAL_CHAT_BASE_URL="http://127.0.0.1:11434"
export RUNSTATS_LOCAL_CHAT_MODEL="llama3.2"
export RUNSTATS_LOCAL_CHAT_TIMEOUT_SECONDS="20"
```

If the configured model is unavailable, the API returns
`CHAT_MODEL_UNAVAILABLE`. Unit and component tests use fakes and do not require
a local model runtime.

Hosted providers remain disabled for this local-first release.

## Safety

- The chatbot does not execute model-generated SQL.
- Chat tools call existing read-only service methods.
- Tool results sent to a model are summarized, not full database dumps.
- Health-related answers must describe observed data and avoid diagnosis,
  prescriptions, or medical advice.
- Chat history is retained locally until deleted by default. The service reads
  the configured retention policy; `retain_until_deleted` is the implemented
  behavior for this release.

## Future Suggested Workouts

Suggested workout generation is deferred. Before adding it:

- Label generated workouts as general training ideas, not medical or clinical
  guidance.
- Cite the recent training data used by the suggestion.
- Keep health metrics descriptive and avoid medical interpretation.
- Provide a clear unavailable-data state when recent training data is too thin
  for a useful suggestion.
