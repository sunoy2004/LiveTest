# User Service (`user-service`)

The User Service is the **core backend** for this monorepo: **identity** (JWT auth), **profiles**, **scheduling**, **sessions**, **mentorship requests**, **admin** routes, **WebSocket dashboard**, and **internal APIs** for the AI service. It uses **PostgreSQL**, **Redis** (pub/sub + WebSocket fan-out), and optionally integrates **Gamification Service** (credits ledger) via HTTP.

---

## Role in the system

| Concern | Implementation |
|--------|------------------|
| Auth | JWT access tokens; `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| CORS | `CORS_ORIGINS` — comma-separated browser origins (shell + Vite ports) |
| Mentoring API surface | Routes under `/api/v1/...` (profiles, scheduling, requests, dashboard, admin) |
| Realtime | WebSocket `/ws/dashboard?token=<JWT>`; Redis channel `app:events` for envelope to WS clients |
| Cross-service events | Publishes to `mentoring.connections.events`, `mentoring.sessions.events`, `economy.credits.events` via `app/services/event_bus.py` |
| AI graph bootstrap | `GET /internal/matchmaking/snapshot` — internal token header `X-Internal-Token` |
| Credits | Optional `GAMIFICATION_SERVICE_URL` — balance/deduct/add through `credit_client.py` |

---

## Architecture (high level)

### Entry

- **`app/main.py`** — FastAPI, CORS, includes `router`, WebSocket `/ws/dashboard`.
- **`app/routes/__init__.py`** — Mounts `auth`, `scheduling`, `sessions`, `api/v1`, `internal`.

### Notable areas

- **`app/routes/auth.py`** — Login/register/token flows.
- **`app/routes/v1/`** — Versioned mentoring REST API (`router.py`, `requests.py`, `admin.py`, etc.).
- **`app/routes/internal.py`** — `GET /internal/matchmaking/snapshot` for AI hydration.
- **`app/services/event_bus.py`** — Central publish: in-app `EVENT_CHANNEL` + Redis topic fan-out for microservices.
- **`app/services/booking_service.py`**, **`session_completion_service.py`**, **`mentorship_request_service.py`** — Domain logic + events.
- **`app/services/credit_client.py`** — HTTP to Gamification Service when configured.
- **`app/services/matchmaking_snapshot.py`** — Builds mentor/mentee payload for AI graph.

### Data

- SQLAlchemy models in **`app/models.py`** (and related); **`app/db_patches.py`** for incremental schema fixes; **`app/seed.py`** for dev data.

---

## HTTP surface (overview)

| Area | Prefix / path |
|------|----------------|
| Health | `GET /health` |
| Auth | `/auth/...` (see `routes/auth.py`) |
| Scheduling / sessions | `/scheduling/...`, `/sessions/...` |
| Mentoring v1 | `/api/v1/...` |
| Internal | `/internal/matchmaking/snapshot` |
| WebSocket | `WS /ws/dashboard?token=...` |

Exact paths are defined in route modules; the mentor MFE uses **`VITE_MENTORING_API_BASE_URL`** pointing at this service’s origin + `/api/v1/...`.

---

## Configuration

Copy `user-service/.env.example` to `user-service/.env` for local **non-Docker** runs.

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | **Host**: `postgresql://...@localhost:5432/users_db`. **Inside Docker**: use service name `user-db`, not `localhost`. |
| `REDIS_URL` | `redis://localhost:6379/0` (host) or `redis://redis:6379/0` (compose service `redis`) |
| `JWT_SECRET` | Shared secret for signing JWTs — **must match AI service** `JWT_SECRET` |
| `CORS_ORIGINS` | Comma-separated origins, e.g. `http://localhost:3000,http://localhost:5173` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default 60 |
| `GAMIFICATION_SERVICE_URL` | Optional, e.g. `http://localhost:8002` or `http://gamification-service:8000` in Docker |
| `INTERNAL_API_TOKEN` | Shared with **AI service** for `/internal/matchmaking/snapshot` |
| `USERSERVICE_RESET_ADMIN_PASSWORD` | Dev convenience — set `false` in production |

---

## Local development (uvicorn on host)

```bash
cd user-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# Start Postgres (users_db) and Redis locally — or use Docker only for DB/Redis
uvicorn app.main:app --reload --port 8000
```

---

## Docker (`user-service/docker-compose.yml`)

Defines the **foundation stack** for the repo:

| Service | Role |
|---------|------|
| `user-db` | Postgres 15, `users_db`, port **5432** |
| `redis` | Container name **`user-redis`**, port **6379** |
| `user-service` | **8000:8000**, env wired to `user-db` and `redis` |

Network name: **`mentor_stack`** (explicit `name:`) — **required** so `docker-compose.microservices.yml` can attach AI/Gamification/Notification with `external: true`.

**Bring up:**

```bash
cd user-service
docker compose up -d
```

Verify: `GET http://localhost:8000/health`

---

## Cross-service wiring

| Consumer | What to set on User Service |
|----------|-----------------------------|
| AI Service | `INTERNAL_API_TOKEN`, snapshot uses User Service URL from AI side as `USER_SERVICE_URL` |
| Gamification Service | `GAMIFICATION_SERVICE_URL` when booking/deduct should hit credits |
| Frontends | `CORS_ORIGINS` includes shell URL |

---

## Operations checklist

- [ ] Rotate `JWT_SECRET` and redeploy all services that verify the same JWT (AI, etc.).
- [ ] Set `INTERNAL_API_TOKEN` to a strong random value; sync with AI service.
- [ ] Production: `USERSERVICE_RESET_ADMIN_PASSWORD=false`.
- [ ] Postgres backups for `user_data` volume.

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| AI empty graph | `INTERNAL_API_TOKEN`, network from AI container to `user-service-api:8000` |
| WS disconnects | Token expiry, `REDIS_URL`, listener errors in logs |
| CORS errors from browser | `CORS_ORIGINS` |

---

## Repository layout

```
user-service/
  app/
    main.py
    models.py
    schemas.py
    routes/
    services/
    realtime/
  requirements.txt
  Dockerfile
  docker-compose.yml
  .env.example
```
