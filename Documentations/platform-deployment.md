# Platform deployment (Mentor–Mentee monorepo)

This document describes how **all services** fit together, default **ports**, **Docker networking**, **environment alignment**, and a practical **startup order** for local and containerized deployments.

---

## Service map

| Component | Path | Typical role |
|-----------|------|----------------|
| **User Service** | `user-service/` | Auth, mentoring `/api/v1`, WebSocket dashboard, internal snapshot for AI, Redis event fan-out |
| **AI Service** | `ai-service/` | `GET /recommendations`, in-memory graph, Redis listeners |
| **Gamification Service** | `gamification-service/` | Immutable credit ledger, balance / deduct / add (legacy), Redis listener (session rewards), admin UI at `/ui` |
| **Notification Service** | `notification-service/` | Persists events from Redis topics |
| **Common UI Shell** | `common-ui-shell/` | Host app, Module Federation consumer |
| **Mentor–Mentee MFE** | `mentor-mentee-module/` | Federated remote UI |

**Infrastructure shared across Docker Compose files:**

- **PostgreSQL** — separate databases: `users_db` (User), `gamification_db` (Gamification), `notifications_db` (Notification).
- **Redis** — single deployment (`user-redis` in User Service compose) used for WebSocket envelopes and **cross-service pub/sub** channels.

---

## Network: `mentor_stack`

- **`user-service/docker-compose.yml`** declares a network with **name** `mentor_stack` (not the default project network).
- **`docker-compose.microservices.yml`** declares `usernet` as **external: true** with **name: `mentor_stack`** so AI, Gamification, and Notification attach to the same bridge as User Service and Redis.

**Rule:** Start User Service compose **first** so the network (and `user-redis`) exist:

```bash
cd user-service
docker compose up -d
```

Then:

```bash
cd E:\mentor-mentee
docker compose -f docker-compose.microservices.yml up -d
```

---

## Port reference (defaults)

| Service | Host port | Notes |
|---------|-----------|--------|
| User Service API | 8000 | |
| AI Service | 8001 | mapped from container 8000 |
| Gamification Service | 8002 | |
| Notification Service | 8003 | |
| Postgres (users) | 5432 | from `user-service/docker-compose.yml` |
| Postgres (gamification) | 5433 | from `docker-compose.microservices.yml` |
| Postgres (notifications) | 5434 | from `docker-compose.microservices.yml` |
| Redis | 6379 | container `user-redis` |
| Common UI shell (Vite) | 3000 | not in root compose — run locally |
| Mentor MFE (preview) | 5001 | not in root compose — run locally |

---

## Redis channels (cross-service)

Aligned string topics (see each service’s `event_bus` or `event_bus`-like module):

| Channel | Typical publishers | Typical consumers |
|-----------|-------------------|-------------------|
| `app:events` | User Service | User Service WS fan-out (in-process path) |
| `mentoring.connections.events` | User Service | AI Service, Notification Service |
| `mentoring.sessions.events` | User Service | AI Service, Gamification Service (session_completed rewards), Notification Service |
| `economy.credits.events` | Gamification Service (+ User Service fan-out for credit_updated) | Notification Service |

**Requirement:** Every service must use the **same** `REDIS_URL` pointing at the shared Redis instance.

---

## Secrets and alignment

| Name | Must match across |
|------|-------------------|
| `JWT_SECRET` | User Service, AI Service |
| `INTERNAL_API_TOKEN` | User Service (`/internal/...`), AI Service (`USER_SERVICE_URL` + header) |

---

## Environment matrix (quick)

### User Service (Docker)

Set via `user-service/docker-compose.yml` or override file:

- `DATABASE_URL` → `user-db`
- `REDIS_URL` → `redis://redis:6379/0`
- `GAMIFICATION_SERVICE_URL` → `http://gamification-service:8000` when Gamification stack is up
- `CORS_ORIGINS` → include `http://localhost:3000` and production shell URL

### AI Service (Docker / `docker-compose.microservices.yml`)

- `REDIS_URL=redis://user-redis:6379/0`
- `USER_SERVICE_URL=http://user-service-api:8000`
- `JWT_SECRET`, `INTERNAL_API_TOKEN` aligned with User Service

### Gamification / Notification (microservices compose)

- DB URLs use service hostnames `gamification-db`, `notifications-db`
- `REDIS_URL=redis://user-redis:6379/0`

### Frontends (build-time `VITE_*`)

- **Shell**: `VITE_USER_SERVICE_URL`, `VITE_MFE_REMOTE_PORT`, optional `VITE_MENTOR_REMOTE_ENTRY`
- **MFE**: `VITE_USER_SERVICE_URL`, `VITE_MENTORING_API_BASE_URL` (User Service), `VITE_AI_API_BASE_URL`, `VITE_MFE_REMOTE_PORT`

---

## Recommended startup sequence (full dev stack)

1. **Data plane**: `user-service` Docker (Postgres + Redis + API), or local Postgres + Redis + `uvicorn`.
2. **Microservices** (optional): `docker-compose.microservices.yml` — AI, Gamification+DB, Notification+DB.
3. **MFE**: `mentor-mentee-module` — `npm run build && npm run serve:federation`.
4. **Shell**: `common-ui-shell` — `npm run dev` (or `dev:integrated`).

Health checks:

- `GET http://localhost:8000/health` — User
- `GET http://localhost:8001/health` — AI
- `GET http://localhost:8002/health` — Credit
- `GET http://localhost:8003/health` — Notification

---

## Production notes

- Use **managed Postgres/Redis** or hardened Helm charts; replace default passwords.
- Terminate TLS at ingress; set `CORS_ORIGINS` to real origins only.
- Frontends: build with production `VITE_*` URLs; host shell and remote assets on HTTPS; configure `VITE_MENTOR_REMOTE_ENTRY` for federation.
- Do not expose `/internal/*` without network policies and strong `INTERNAL_API_TOKEN`.
- Set `AI_TRUST_GATEWAY_HEADERS` only if a gateway validates users before AI.

---

## Root-level compose files

| File | Purpose |
|------|---------|
| `user-service/docker-compose.yml` | User API + Postgres + Redis + `mentor_stack` |
| `docker-compose.microservices.yml` | AI, Credit+DB, Notification+DB (external network) |
| `mentor-mentee-module/backend/docker-compose.yml` | Standalone Postgres for optional legacy backend only |

---

## Related per-service docs

- [ai-service.md](./ai-service.md)
- [common-ui-shell.md](./common-ui-shell.md)
- [gamification-service.md](./gamification-service.md)
- [mentor-mentee-module.md](./mentor-mentee-module.md)
- [notification-service.md](./notification-service.md)
- [user-service.md](./user-service.md)
