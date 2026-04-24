# AI Matching Service (`ai-recommendation-service/`)

The AI service provides **mentor recommendations** for mentees. The default engine is **PostgreSQL + pgvector** (semantic similarity on 768-d embeddings). A legacy **in-memory graph** (NetworkX / Jaccard) remains available via `RECOMMENDATION_ENGINE=graph`. The service stays in sync via **Redis pub/sub**, re-hydrates from User Service on startup, and can refresh profiles when `mentoring.profiles.matching` events are published.

---

## Role in the system

| Concern | Implementation |
|--------|------------------|
| Recommendations | `GET /recommendations?user_id=…&limit=…` — **pgvector**: cosine similarity on embeddings from profile text; optional `HYBRID_SCORING` adds interaction weights. **graph**: Jaccard overlap with edge bumps from events |
| Feedback | `POST /recommendations/feedback` — records `REJECTED_SUGGESTION` / `SUCCESSFUL_MENTORSHIP` in `match_interactions` |
| Cold start / snapshot | `GET {USER_SERVICE_URL}/internal/matchmaking/snapshot` (protected by `INTERNAL_API_TOKEN`) |
| Live updates | Redis: `mentoring.connections.events`, `mentoring.sessions.events`, `mentoring.profiles.matching` |
| Auth | JWT (`JWT_SECRET`) unless `AI_TRUST_GATEWAY_HEADERS=true` |

---

## Architecture

### Components

- **`app/main.py`** — FastAPI app; lifespan: bootstrap snapshot (graph + optional pgvector upsert) → Redis listener.
- **`app/services/recommendation_service.py`** — pgvector query + Redis cache, or delegates to `graph.py` when `RECOMMENDATION_ENGINE=graph`.
- **`app/services/graph.py`** — Legacy `GraphStore` (Jaccard + edge bumps).
- **`app/realtime/redis_listener.py`** — Subscribes to connection, session, and profile topics; updates graph and/or `match_interactions`.
- **`alembic/`** — `match_profiles` (`VECTOR(768)`), `match_interactions`, IVFFlat index.

Source tree: repository directory **`ai-recommendation-service/`** (root `docker-compose.yml` builds this path as service `ai-service`).

### Data flow

1. **Startup**: If `USER_SERVICE_URL` and `INTERNAL_API_TOKEN` are set, HTTP GET to `/internal/matchmaking/snapshot` loads the full graph.
2. **Runtime**: Redis messages adjust edge weights so recommendations reflect accepted mentorships and completed sessions without restarting.

### Dependencies

- **Redis** — Same instance as User Service (`REDIS_URL`); required for live graph updates.
- **User Service** — Snapshot endpoint + JWT secret alignment for `/recommendations`.

---

## HTTP API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/recommendations` | Query: `user_id` (required), `limit` (1–50, default 5). Headers: `Authorization: Bearer <JWT>` (unless trust-gateway mode), optional `X-User-Id` must match token subject |
| POST | `/recommendations/feedback` | JSON body: `target_user_id`, `interaction_type` (`REJECTED_SUGGESTION` \| `SUCCESSFUL_MENTORSHIP`). Actor = JWT subject (or `X-User-Id` in trust-gateway mode) |

---

## Configuration

Copy `ai-recommendation-service/.env.example` to `.env` for local runs.

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes (pgvector) | e.g. `postgresql+asyncpg://postgres:postgres@localhost:5432/recommendation_db` |
| `REDIS_URL` | Yes | e.g. `redis://localhost:6379/0` |
| `USER_SERVICE_URL` | Recommended | User Service base URL (no trailing slash) |
| `INTERNAL_API_TOKEN` | Recommended | Must match User Service for snapshot |
| `JWT_SECRET` | Yes (prod) | Must match User Service for Bearer tokens |
| `EMBEDDING_PROVIDER` | Optional | `opensource` (default) or `vertex` + `USE_VERTEX=true` |
| `RECOMMENDATION_ENGINE` | Optional | `pgvector` (default) or `graph` |
| `AI_TRUST_GATEWAY_HEADERS` | Optional | `true` = trust gateway headers (`X-User-Id`) |

---

## Local development

```bash
cd ai-recommendation-service
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
# Ensure User Service + Redis are up; set .env
uvicorn app.main:app --reload --port 8001
```

Default local port in docs/examples: **8001** (to avoid clashing with User Service on 8000).

---

## Docker

- **Image**: `ai-recommendation-service/Dockerfile` — `alembic upgrade head && uvicorn …`.
- **Compose**: root `docker-compose.yml` service **`ai-service`** builds `./ai-recommendation-service`, adds `DATABASE_URL` to `recommendation_db` on the shared `pgvector` Postgres image, maps **8001:8000**.

**Prerequisite**: Start User Service stack first so network `mentor_stack` exists and Redis (`user-redis`) is reachable:

```bash
cd user-service
docker compose up -d
cd ..
docker compose -f docker-compose.microservices.yml up -d ai-service
```

---

## Operations checklist

- [ ] `JWT_SECRET` identical to User Service.
- [ ] `INTERNAL_API_TOKEN` identical to User Service.
- [ ] Redis URL points to the **same** Redis the User Service uses (shared pub/sub).
- [ ] After User Service DB changes that affect mentors/mentees, restart AI service or rely on Redis events + gradual bump (snapshot only runs at startup).
- [ ] Do not set `AI_TRUST_GATEWAY_HEADERS=true` unless an API gateway validates callers.

---

## Troubleshooting

| Symptom | Check |
|--------|--------|
| Empty graph at startup | `USER_SERVICE_URL` / `INTERNAL_API_TOKEN`, User Service logs, `GET /internal/matchmaking/snapshot` manually with header |
| 401 on `/recommendations` | Token expiry, `JWT_SECRET` mismatch, or user_id query vs token `user_id` |
| Graph never updates | Redis connectivity, channel names, User Service publishing to `mentoring.connections.events` / `mentoring.sessions.events` |

---

## Repository layout (service root)

```
ai-service/
  app/
    main.py
    schemas.py
    realtime/redis_listener.py
    services/graph.py
    services/event_bus.py
  requirements.txt
  Dockerfile
  .env.example
```
