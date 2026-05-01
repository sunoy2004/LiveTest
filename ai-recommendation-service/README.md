# AI recommendation service (semantic matchmaking)

Mentor recommendations for mentees using **PostgreSQL + pgvector** (default) or the legacy **in-memory graph** (`RECOMMENDATION_ENGINE=graph`). Profile text is embedded with **sentence-transformers** (`sentence-transformers/all-mpnet-base-v2`, **768 dimensions**) by default; optional **Vertex AI** embeddings are available without installing Vertex by default (see below).

## Requirements

- Python 3.12+
- PostgreSQL **with pgvector** (e.g. image `pgvector/pgvector:pg15`) — use the same **`mentoring`** database as the mentoring service (domain tables + AI `match_*` tables).
- Redis (caching + pub/sub)

## Run locally (without Vertex)

1. Copy `.env.example` to `.env` and set at least `DATABASE_URL`, `REDIS_URL`, `USER_SERVICE_URL`, `INTERNAL_API_TOKEN`, `JWT_SECRET`.
2. Install: `pip install -r requirements.txt`
3. Ensure the DB exists: `python scripts/ensure_recommendation_db.py` (creates `recommendation_db` on the server if missing; uses the same `DATABASE_URL` as the app).
4. Apply migrations: `alembic upgrade head` (Alembic uses `psycopg2`; replace `+asyncpg` with `+psycopg2` in the URL for the CLI if needed).
5. Start: `uvicorn app.main:app --reload --port 8001`

Or use Docker Compose in this directory (Postgres + Redis + app):

```bash
docker compose up --build
```

Set `USER_SERVICE_URL` to a reachable user-service (e.g. `http://host.docker.internal:8000` on Docker Desktop).

## Embedding providers

| `EMBEDDING_PROVIDER` | Description |
|----------------------|-------------|
| `opensource` (default) | `sentence-transformers` + `OPENSOURCE_MODEL` (default `sentence-transformers/all-mpnet-base-v2`, 768-d). Fully offline after the model is cached. |
| `vertex` | Vertex AI text embeddings — set `USE_VERTEX=true`, `GOOGLE_CLOUD_PROJECT`, and install optional deps: `pip install -r requirements-vertex.txt`. |

The database column is `VECTOR(768)`; both default open-source and Vertex configurations are expected to produce **768-dimensional** vectors.

## Feature flags

| Variable | Default | Description |
|---------|---------|-------------|
| `RECOMMENDATION_ENGINE` | `pgvector` | `pgvector` = SQL vector similarity; `graph` = legacy NetworkX Jaccard graph. |
| `HYBRID_SCORING` | `false` | Combine semantic score with summed `match_interactions` weights for ordering. |
| `RECOMMENDATION_CACHE_TTL` | `300` | Redis TTL (seconds) for `GET /recommendations` cache. |

## API

- `GET /health`
- `GET /recommendations?user_id=&limit=` — same contract as before (`mentor_id`, `score` in `[0,1]`).
- `POST /recommendations/feedback` — JSON `{ "target_user_id", "interaction_type": "REJECTED_SUGGESTION" | "SUCCESSFUL_MENTORSHIP" }`; actor is the JWT subject (or `X-User-Id` in gateway mode).

### Sync with mentoring domain data

Recommendations read from **`match_profiles`**, populated at startup and on reindex by reading **`mentor_profiles`**, **`mentee_profiles`**, **`users`**, **`mentor_tiers`**, and **`mentorship_connections`** in the same PostgreSQL database (`mentoring`). No HTTP snapshot is required when `DATABASE_URL` points at that DB.

The mentoring service still exposes **`GET /api/v1/internal/matchmaking-snapshot`** (with `X-Internal-Token`) for other callers; it is optional for this service.

After you **seed users**, **change profiles**, or if the AI service started before User Service had data, run a **reindex** so embeddings match the DB:

```bash
curl -sS -X POST "http://localhost:8001/internal/matchmaking/reindex" \
  -H "X-Internal-Token: change-me-in-production"
```

Use the same `INTERNAL_API_TOKEN` value as in User Service / root `docker-compose.yml`. The response reports snapshot row counts and how many `match_profiles` rows were upserted.

**Note:** Mentors only appear in recommendations if `is_accepting_requests` is true in the snapshot (stored as `match_profiles.is_active` for mentor/BOTH rows).

## Database volume note

The shared Postgres instance should include the **`mentoring`** database (created by mentoring migrations or init scripts). **Docker images for this service** run `scripts/ensure_recommendation_db.py` before Alembic so the database named in `DATABASE_URL` exists.

Manual fix (one-off):  
`docker compose exec postgres psql -U postgres -c "CREATE DATABASE mentoring;"`  
(from repo root, against the stack Postgres container).

If you see **collation version mismatch** on `template1` / `postgres`, the startup script runs `ALTER DATABASE … REFRESH COLLATION VERSION` and may fall back to `CREATE DATABASE … WITH TEMPLATE template0`. If problems persist after a Postgres image upgrade, remove the Postgres volume and recreate it (this deletes local DB data):  
`docker compose down -v` then `docker compose up -d` (use only when acceptable).

## Tests

```bash
pip install -r requirements.txt
pytest
```

Integration tests mock the recommendation/feedback services so they do not require Postgres or sentence-transformers downloads.
