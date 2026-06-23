# RunStats Frontend

The frontend is the React interface for RunStats. It provides the dashboard,
activity browser, health trends, chat assistant, watch settings, manual sync,
FIT folder import controls, sync history, and local data-management screens.

The app is built with React, TypeScript, Vite, React Query, Vitest, Testing
Library, Playwright, and ESLint.

## Develop

```bash
npm install
npm run dev
```

During local development, Vite serves the frontend and proxies `/api` and
WebSocket sync-progress traffic to:

```text
http://127.0.0.1:8000
```

Leave `VITE_RUNSTATS_API_BASE_URL` unset for normal local development and for
the combined local app served by FastAPI. Set it only when the browser can reach
a custom backend origin directly.

## Validate

```bash
npm run test
npm run lint
npm run typecheck
npm run build
```

Run browser-level e2e validation:

```bash
npm run e2e:install
npm run e2e
```

The e2e suite builds the frontend, starts a seeded local FastAPI server, and
drives the real React app through a browser.

## File Inventory

### Package And Tooling

| Path | Purpose |
| --- | --- |
| `README.md` | Frontend overview and file inventory. |
| `eslint.config.js` | ESLint configuration for TypeScript and React code. |
| `index.html` | Vite HTML entry point and root DOM container. |
| `package-lock.json` | Locked npm dependency graph for reproducible installs. |
| `package.json` | Frontend npm scripts and dependencies. |
| `playwright.config.ts` | Browser e2e configuration and local app startup wiring. |
| `tsconfig.app.json` | TypeScript settings for application source. |
| `tsconfig.json` | TypeScript project references root. |
| `tsconfig.node.json` | TypeScript settings for Node-based config files. |
| `vite.config.ts` | Vite, React plugin, Vitest, and local API/WebSocket proxy configuration. |

### End-To-End Tests

| Path | Purpose |
| --- | --- |
| `e2e/runstats.spec.ts` | Playwright browser test covering the built RunStats app against a seeded backend. |

### Source Root

| Path | Purpose |
| --- | --- |
| `src/App.css` | Main application styling for layout, navigation, panels, tables, forms, charts, watch settings, sync progress, and responsive behavior. |
| `src/App.tsx` | Application shell, sidebar navigation, route definitions, and not-found state. |
| `src/index.css` | Global CSS reset, base typography, body background, and root sizing. |
| `src/main.tsx` | React entry point that creates the root, QueryClient, router, and app shell. |
| `src/vite-env.d.ts` | Vite-provided TypeScript environment declarations. |

### API Client

| Path | Purpose |
| --- | --- |
| `src/api/runstats.ts` | Typed client for all backend APIs, query-key factories, request helpers, response types, error normalization, FIT folder import, and sync WebSocket URL construction. |

### Shared Components And Utilities

| Path | Purpose |
| --- | --- |
| `src/components/StatusViews.tsx` | Shared page header, loading, empty, error, and stat-card components. |
| `src/lib/formatters.ts` | Date, duration, number, distance, pace, and status formatting helpers. |

### Views

| Path | Purpose |
| --- | --- |
| `src/views/ActivitiesView.tsx` | Activity list, filters, activity detail, laps, samples, charts, and route/sample presentation. |
| `src/views/ChatAssistantView.tsx` | Chat sessions, prompts, answers, supporting data, and references. |
| `src/views/DashboardView.tsx` | High-level running summary, recent activity, health preview, and sync status dashboard. |
| `src/views/DataManagementView.tsx` | Local data export and delete controls. |
| `src/views/HealthView.tsx` | Health metric selector, filters, availability messaging, summaries, and trend chart. |
| `src/views/SyncHistoryView.tsx` | Sync run list, filters, sync detail page, failure notes, and retry action. |
| `src/views/WatchSettingsView.tsx` | Watch discovery, pairing, settings, capability probe, connection test, manual sync, sync progress, and FIT folder import UI. |

### Tests

| Path | Purpose |
| --- | --- |
| `tests/App.test.tsx` | App-level view, navigation, and route behavior tests with mocked backend responses. |
| `tests/WatchSettingsView.test.tsx` | Watch settings, scan/pair, connection, sync, FIT folder import, and error-state tests. |
| `tests/api.test.ts` | API client request, response, error, query-key, and URL helper tests. |
| `tests/setup.ts` | Vitest and Testing Library global test setup. |

## User Workflows Implemented Here

- Dashboard scanning for totals and recent status.
- Activity filtering and drill-down.
- Health metric exploration.
- Local chat over imported data.
- Watch discovery, pairing, and settings.
- FIT folder import from a backend-readable local path.
- Manual sync progress display.
- Sync history and retry.
- Data export and deletion.
