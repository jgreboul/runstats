# RunStats Agent Guide

This file guides AI coding assistants working in this repository. The primary
product references are:

- `runstats-design.md`
- `runstats-product-backlog.md`
- `AGENT.md`

Read these files before implementing a backlog item or changing application
architecture.

## Mission

Implement RunStats as a local-first Python and React application that connects
to a Garmin watch, imports running activities and health stats, stores them in
SQLite, renders them in a React UI, and provides a grounded chatbot for asking
questions about the local data.

The assistant should build incrementally, keep changes well tested, and leave
the repository easier to continue than it found it.

## Working Rules

- Implement the requested backlog item end to end when feasible.
- Keep changes scoped to the current task.
- Prefer existing project patterns once they exist.
- Add or update tests with every behavior change.
- Treat a comprehensive unit test suite as required validation for implemented
  logic, not as optional cleanup.
- Do not require a physical Garmin watch, live Bluetooth device, or hosted LLM
  for unit tests.
- Mock Bluetooth providers, FIT payloads, schedulers, clocks, and LLM providers
  in tests.
- Keep health data privacy requirements visible in code and UI decisions.
- Update documentation when behavior, commands, or architecture changes.

## Expected Repository Shape

The intended layout is:

```text
backend/
  runstats/
    api/
    bluetooth/
    chat/
    db/
    importers/
    services/
  tests/
frontend/
  src/
  tests/
data/
runstats-design.md
runstats-product-backlog.md
AGENT.md
```

If implementation discovers a better structure, update the documentation and
explain the reason in the implementation summary.

## Implementation Workflow

1. Identify the relevant backlog item or design section.
2. Inspect the current code before editing.
3. Plan the smallest useful vertical slice.
4. Add or update tests first when the expected behavior is clear.
5. Implement the change.
6. Run targeted tests for the changed area.
7. Run the broader validation suite before final handoff when practical.
8. Update docs or backlog status if the implementation changes the plan.
9. Provide a concise implementation summary, validation results, and proposed
   git commit metadata.

## Backend Guidelines

- Use FastAPI for HTTP and WebSocket APIs.
- Keep route handlers thin. Put domain behavior in services.
- Use SQLAlchemy 2.x models and sessions for persistence.
- Use Alembic for schema changes.
- Use Pydantic models for request and response contracts.
- Keep database values in canonical metric units.
- Use explicit structured errors with stable error codes.
- Ensure imports and sync writes are transactional.
- Keep provider-specific Bluetooth behavior behind `WatchProvider`.
- Keep chatbot database access behind approved read-only service methods and
  tools.

## Frontend Guidelines

- Use React with TypeScript.
- Use typed API clients.
- Use TanStack Query or the selected data-fetching pattern consistently.
- Build real app screens, not marketing pages.
- Every view should handle loading, empty, success, and error states.
- Watch Settings must handle Bluetooth unavailable, scanning, pairing,
  connected, syncing, failed, and succeeded states.
- Chat Assistant must show useful unavailable-data states and link answers back
  to referenced activities, charts, or sync runs when those references exist.

## Chatbot Safety Rules

- The chatbot must not execute arbitrary model-generated SQL directly.
- Chat tools must be read-only.
- Tool results sent to an LLM should be the minimum useful summaries, not the
  entire database.
- Hosted model usage must be explicit and configurable.
- Unit tests must use a fake LLM provider.
- Health-related answers must describe observed data trends and avoid diagnosis
  or medical advice.
- Store tool traces as lightweight metadata: intent, date range, metrics, row
  counts, and referenced ids.

## Testing Requirements

Every implemented change must be validated by tests. The expected level depends
on the changed surface area.

### Unit Tests

Unit tests are required for new or changed:

- Services
- Importers
- Normalizers
- Analytics functions
- Chat tools and orchestration
- Bluetooth provider adapters
- Error mapping
- Configuration parsing
- Frontend utility functions and API clients

Unit tests should cover:

- Success paths
- Empty data
- Missing optional fields
- Invalid input
- Duplicate detection
- Permission or provider failures
- Boundary dates and time ranges

### Integration Tests

Integration tests are required for:

- FastAPI endpoints
- Database migrations
- SQLite persistence behavior
- Import transactions
- Sync lifecycle
- WebSocket progress streams

Use temporary databases for tests. Do not share local developer data across
tests.

### Frontend Tests

Frontend tests are required for:

- Route rendering
- Forms and validation
- Tables and filters
- Loading, empty, and error states
- Watch setup interactions
- Chat message submission and answer rendering

Mock backend APIs for component tests unless an end-to-end test is explicitly
being written.

### End-to-End Tests

Add Playwright or equivalent tests once the app shell is stable.

Important flows:

- Dashboard loads with seeded data.
- Activity filters and details work.
- Watch settings can scan, pair, save settings, and run fake sync.
- Chat Assistant answers a seeded-data question and links to source data.

## Validation Protocol

Before final handoff, run the most complete practical validation.

At minimum:

- Run targeted tests for touched backend or frontend areas.
- Run linting and type checks for touched language surfaces if configured.
- Run migration checks when database schema changes.
- Run frontend build when UI build configuration changes.

If a full suite cannot be run, state exactly what was run and why the remaining
validation was not run.

Do not claim validation succeeded unless the command was actually run.

## Suggested Validation Commands

The exact commands may change as tooling is added. Keep this section updated.

Root commands:

```bash
npm run install:all
npm run validate
```

Backend commands:

```bash
cd backend
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy runstats
```

Frontend commands:

```bash
cd frontend
npm install
npm test
npm run lint
npm run typecheck
npm run build
```

The root `npm run validate` command wraps backend tests, backend linting,
backend type checking, frontend tests, frontend linting, frontend type checking,
and the frontend production build.

## Commit Handoff Requirement

After implementing a change, provide proposed git commit metadata in the final
response. Do this even if the assistant does not create the commit.

Use this format:

```text
Proposed commit title:
<imperative summary, 72 characters or fewer>

Proposed commit description:
- What changed: <short description of implementation>
- Validation: <commands/tests run and outcomes>
- Notes: <migration, docs, or follow-up context if relevant>
```

A good title is specific and action-oriented, for example:

- `Add SQLite models and initial migration`
- `Implement activity summary API`
- `Add chat assistant persistence endpoints`

Do not include vague titles such as `Update files` or `Fix stuff`.

## Final Response Checklist

When work is complete, the assistant should report:

- What changed
- Tests or validation commands run
- Any validation that could not be run
- Proposed commit title
- Proposed commit description

Keep the summary concise, but include enough validation detail for the next
developer to trust the handoff.

## When Blocked

If implementation is blocked:

- Explain the blocker clearly.
- State what was already validated or inspected.
- Suggest the smallest next decision needed.
- Do not invent behavior that conflicts with `runstats-design.md`.
