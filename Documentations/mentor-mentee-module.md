# Mentor–Mentee Module (`mentor-mentee-module`)

This package is the **micro-frontend (remote)** loaded by **common-ui-shell** via **Module Federation** (`@originjs/vite-plugin-federation`). It implements the mentoring **dashboard**, **match discovery** (AI), **scheduling**, **requests**, **wallet UI**, and related flows. API calls target the **User Service** (`/api/v1/...`) and the **AI service** (`/recommendations`) using Vite env base URLs.

There is also an optional **legacy Python backend** under `mentor-mentee-module/backend/` (Postgres + FastAPI). The **primary integration path** in this repo is **User Service** as the mentoring API — configure the MFE to point at User Service unless you intentionally run the standalone backend.

---

## Role in the system

| Concern | Implementation |
|--------|------------------|
| Federation remote | Exposes `./src/App.tsx` as `mentorMentee/App`; `remoteEntry.js` served from `vite preview` (or static CDN) |
| Mentoring REST | `VITE_MENTORING_API_BASE_URL` + paths in `src/config/mentoring.ts` → `/api/v1/...` on User Service |
| AI recommendations | `VITE_AI_API_BASE_URL` + `GET /recommendations` (see `src/lib/api/ai.ts`, `client.ts`) |
| Auth | Reads same `localStorage` keys as shell (`AUTH_TOKEN_KEY`, `AUTH_USER_KEY`) — see `lib/authStorage.ts`, `mentoringFetch` headers |
| Dashboard realtime | WebSocket to User Service `/ws/dashboard` via `useDashboardWebSocket.ts` |

---

## Architecture

### Frontend

- **`vite.config.ts`** — Federation **remote** plugin, `name: "mentorMentee"`, port from `VITE_MFE_REMOTE_PORT` (default **5001**), CORS middleware for cross-origin chunk loading when needed.
- **`src/config/mentoring.ts`** — Central list of `/api/v1` paths (profiles, scheduling, requests, dashboard, admin).
- **`src/lib/api/client.ts`** — `mentoringFetch` adds `Authorization` + `X-User-Id` from shell storage.
- **`src/context/MentorShellAuthContext.tsx`** — Bridges shell auth into the remote.

### Optional backend (`mentor-mentee-module/backend/`)

- FastAPI app with `GET /health` and `api_router` under configurable prefix.
- **`backend/docker-compose.yml`** — Only **Postgres** (`mentoring` DB on port 5432) — **conflicts** with User Service Postgres if both bind 5432 on the host. Use one stack or change ports.
- Use this backend only if you are developing that API surface separately; otherwise point the MFE at User Service.

---

## Configuration

Copy `mentor-mentee-module/.env.example` to `.env`.

| Variable | Description |
|----------|-------------|
| `VITE_USER_SERVICE_URL` | Identity base URL (aligned with shell), e.g. `http://localhost:8000` |
| `VITE_MENTORING_API_BASE_URL` | **Mentoring REST** — typically same origin as User Service: `http://localhost:8000` |
| `VITE_AI_API_BASE_URL` | AI Matching service, e.g. `http://localhost:8001` |
| `VITE_MFE_REMOTE_PORT` | Port for federation preview — must match **common-ui-shell** `VITE_MFE_REMOTE_PORT` (default **5001**) |

Optional dev-only (see `client.ts`):

- `VITE_DEV_USER_ID` — force `X-User-Id`
- `VITE_DEV_IS_ADMIN` — `true` to send `X-Is-Admin: true`

---

## Local development

### As federation remote (typical)

```bash
cd mentor-mentee-module
npm install
npm run build
npm run serve:federation
# Serves remoteEntry on VITE_MFE_REMOTE_PORT (5001)
```

Hot workflow (from comments in `.env.example`):

- Terminal A: `npm run build:watch`
- Terminal B: `npm run serve:federation`

Or one-shot: `npm run dev:federation` (build + preview).

### With the shell

Start User Service + Redis + (optional) AI + Credit. Start this remote as above. Start **common-ui-shell** `npm run dev` (or `npm run dev:integrated` from shell folder).

---

## Production build

```bash
npm run build
```

Deploy `dist/` to static hosting; set **`VITE_*` at build time** for production API URLs. The **shell** must reference the deployed `remoteEntry.js` URL via `VITE_MENTOR_REMOTE_ENTRY` when the remote is not proxied.

---

## Ports (local defaults)

| Process | Port |
|---------|------|
| `vite preview` / federation | 5001 |
| User Service | 8000 |
| AI Service | 8001 |

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| 401/403 on API | Token in localStorage, `VITE_MENTORING_API_BASE_URL`, User Service auth |
| AI recommendations fail | `VITE_AI_API_BASE_URL`, AI service JWT same secret as User Service |
| Remote not found | Build output, `serve:federation`, shell proxy / `VITE_MENTOR_REMOTE_ENTRY` |
| WS issues | User Service `/ws/dashboard`, token query param, Redis behind User Service |

---

## Repository layout

```
mentor-mentee-module/
  src/
    App.tsx
    config/mentoring.ts
    lib/api/
    hooks/
  vite.config.ts
  package.json
  .env.example
  backend/           # optional standalone FastAPI + compose for Postgres only
    app/
    docker-compose.yml
    .env.example
```
