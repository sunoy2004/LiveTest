# Gamification Service (`gamification-service`)

Central **immutable ledger** for credits: `activity_rules`, `wallets`, and append-only `ledger_transactions`. Exposes REST APIs, Redis pub/sub (consumes `mentoring.sessions.events`, publishes `credit_score_updated` on `economy.credits.events`), and a bundled **admin UI** at **`/ui`** (same origin as the API).

User Service calls it when `GAMIFICATION_SERVICE_URL` is set (booking / deduct / balance / admin top-up).

---

## Role in the system

| Concern | Implementation |
|--------|----------------|
| Persistence | PostgreSQL + SQLAlchemy 2 async (`gamification_db`) |
| API | `GET /wallet/me`, `GET /wallet/history` (user-service JWT); `POST /internal/transactions/*` (`X-Internal-Token`); `GET/PUT/POST /admin/*` (signed **session cookie** after `POST /admin/auth/login`); legacy `GET /balance/{user_id}`, `POST /deduct`, `POST /add` |
| Admin UI | Static build under `/ui` — username/password from `GAMIFICATION_ADMIN_USERNAME` / `GAMIFICATION_ADMIN_PASSWORD` |
| Realtime | Publishes after mutations; listens for `session_completed` on `mentoring.sessions.events` |

---

## Local development

```bash
cd gamification-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/gamification_db
set REDIS_URL=redis://localhost:6379/0
set JWT_SECRET=secret
set GAMIFICATION_ADMIN_USERNAME=admin
set GAMIFICATION_ADMIN_PASSWORD=your-secure-password
alembic upgrade head
uvicorn app.main:app --reload --port 8002
```

Admin UI dev (proxies API to `http://localhost:8002`; dev server uses base `/` so `/admin/*` proxies correctly):

```bash
cd gamification-service/admin-ui
npm install
npm run dev
```

Open **`http://localhost:5176/`** (not `/ui/`) while developing. Production build is still served under **`http://localhost:8002/ui/`**.

---

## Docker (root `docker-compose.yml`)

- Service **`gamification-service`** on host port **8002**
- Database **`gamification_db`** on shared Postgres (`docker/postgres/init`)

---

## Environment

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://.../gamification_db` |
| `REDIS_URL` | Same Redis as other services |
| `JWT_SECRET` | Must match user-service for `/wallet/*` bearer routes |
| `INTERNAL_API_TOKEN` | Header `X-Internal-Token` for internal APIs |
| `GAMIFICATION_ADMIN_USERNAME` / `GAMIFICATION_ADMIN_PASSWORD` | Admin UI login at `/ui` |
| `GAMIFICATION_ADMIN_SESSION_SECRET` | Optional; defaults to `JWT_SECRET` (cookie signing) |
| `CORS_ALLOW_ORIGINS` | Dev shells / MFE origins (include `http://localhost:5176` for Vite admin dev) |

---

## User Service integration

`user-service/app/services/credit_client.py` — `GAMIFICATION_SERVICE_URL` → `GET /balance/{uuid}`, `POST /deduct`, `POST /add` (legacy-compatible responses).

Mentor shell: `VITE_GAMIFICATION_SERVICE_URL` (fallback: `VITE_CREDIT_SERVICE_URL`) → `http://localhost:8002` by default.
