# RunStats Frontend

Phase 3 provides the React, TypeScript, Vite, Vitest, and ESLint frontend with
the RunStats app shell, typed API client, dashboard, activity list and detail
views, health trends, and sync history.

## Install

```bash
npm install
```

## Develop

```bash
npm run dev
```

API requests use the current origin by default. During local development, Vite
proxies `/api` to `http://127.0.0.1:8000`. Set
`VITE_RUNSTATS_API_BASE_URL` only when the frontend origin can reach the backend
directly.

## Validate

```bash
npm run test
npm run lint
npm run typecheck
npm run build
```
