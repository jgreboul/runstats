# RunStats Frontend

React, TypeScript, Vite, Vitest, and ESLint frontend for RunStats. The app
includes dashboard, activity, health, chat, watch settings, sync history, and
data management views.

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
directly. Leave it unset when FastAPI serves `frontend/dist` for the local app.

## Validate

```bash
npm run test
npm run lint
npm run typecheck
npm run build
```
