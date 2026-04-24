# Common UI Shell (`common-ui-shell`)

The **shell** is the primary **host** application: login, layout, admin entry, and **Module Federation** loading of the mentor/mentee micro-frontend (`mentor-mentee-module`). It runs on **Vite + React** and talks to **User Service** for authentication.

---

## Role in the system

| Concern | Implementation |
|--------|------------------|
| Identity | Login/register against `VITE_USER_SERVICE_URL`; JWT + user profile in `localStorage` (shared keys with the remote MFE) |
| Routing | `/login`, `/dashboard`, `/admin`, `/mentoring/*` → federated `MentorMfeRemote` |
| Remote MFE | `@originjs/vite-plugin-federation` — remote name `mentorMentee`, loads `remoteEntry.js` |
| Dev proxy | Same-origin `import()` of remote: `/__mentor_remote__` → `http://127.0.0.1:$VITE_MFE_REMOTE_PORT` |

---

## Architecture

### Federation model

- **Shell** (`common-ui-shell`): `remotes.mentorMentee` → URL built from env (see below).
- **Remote** (`mentor-mentee-module`): exposes `./App` as `mentorMentee/...`, shared singletons: `react`, `react-dom`, `react-router-dom`.

### Important dev constraint

The federation plugin expects the **remote** to serve a **built** `remoteEntry.js`. For integrated dev:

- Build the mentor app (or watch build) and serve with `vite preview` on the MFE port, **or**
- Use `npm run dev:integrated` from the shell (runs mentor `serve:federation` + shell `dev` concurrently — see `package.json`).

### Key files

- `vite.config.ts` — Federation host config, proxy prefix `/__mentor_remote__`, port **3000** for dev server.
- `src/App.tsx` — Routes and `MentorMfeRemote` for `/mentoring/*`.
- `src/context/AuthContext.tsx` / `src/lib/auth.ts` — User Service URLs and token handling.

---

## Configuration

Copy `common-ui-shell/.env.example` to `common-ui-shell/.env`.

| Variable | Description |
|----------|-------------|
| `VITE_USER_SERVICE_URL` | User Service base URL (e.g. `http://localhost:8000`) — login and optional `/me` refresh |
| `VITE_MFE_REMOTE_PORT` | Port where **mentor-mentee-module** serves `remoteEntry.js` via `vite preview` (default **5001**). Must match the remote’s port. |
| `VITE_MENTOR_REMOTE_ENTRY` | Optional. Full URL to `remoteEntry.js` for production/CDN. If unset, dev uses `/__mentor_remote__/assets/remoteEntry.js` (proxied). |

---

## Local development

### Shell only (remote already running on 5001)

```bash
cd common-ui-shell
npm install
npm run dev
# Opens Vite on http://localhost:3000 (see vite.config.ts)
```

### Integrated (build remote + serve + shell)

```bash
cd common-ui-shell
npm run dev:integrated
```

Or manually: in `mentor-mentee-module` run `npm run build && npm run serve:federation`; in `common-ui-shell` run `npm run dev`.

---

## Production / deployment

1. **Build** mentor-mentee-module and host `remoteEntry.js` + assets on a stable HTTPS origin (or same origin as shell).
2. Set `VITE_MENTOR_REMOTE_ENTRY` at build time to the full URL of `remoteEntry.js` (e.g. `https://cdn.example.com/mentor/assets/remoteEntry.js`).
3. Set `VITE_USER_SERVICE_URL` to the public User Service URL.
4. **Build** the shell: `npm run build`; serve `dist/` with any static host or CDN. Ensure CORS and CSP allow loading remote chunks from the mentor origin if cross-origin.

### CORS

Browser calls from the shell origin to User Service must be allowed by User Service `CORS_ORIGINS`.

---

## Port summary (typical local)

| Service | Port |
|---------|------|
| Common UI shell (Vite) | 3000 |
| Mentor MFE (`vite preview` / federation) | 5001 (via `VITE_MFE_REMOTE_PORT`) |
| User Service | 8000 |

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| Remote fails to load | Mentor built (`npm run build`), `serve:federation` on correct port, `VITE_MFE_REMOTE_PORT` matches |
| CORS on `import(remote)` | Use dev proxy path `/__mentor_remote__` or set absolute `VITE_MENTOR_REMOTE_ENTRY` |
| Login fails | `VITE_USER_SERVICE_URL`, User Service up, CORS |
| Auth missing in MFE | Same `localStorage` keys; user opens app via shell origin (not raw MFE origin in prod without matching storage) |

---

## Repository layout

```
common-ui-shell/
  src/
    App.tsx
    pages/
    context/
    features/mentoring/
  vite.config.ts
  package.json
  .env.example
```
