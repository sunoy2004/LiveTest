# Mentoring Service (FastAPI)

Domain service for mentee/mentor profiles, mentorship requests, and connections. Auth is via gateway header `X-User-Id` (JWT validated upstream).

## Configure the database (you don’t have one yet)

The API expects **PostgreSQL** and a connection string in **`DATABASE_URL`** inside **`backend/.env`**.

### Recommended: Docker (creates DB + user for you)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows) and start it.
2. In a terminal:

```powershell
cd path\to\mentor-mentee\backend
copy .env.example .env
docker compose up -d
docker compose ps
```

Wait until the `db` service is **healthy** (or run `docker compose logs -f db` until Postgres accepts connections).

3. Apply schema:

```powershell
alembic upgrade head
```

Your `.env` can stay as the default:

`postgresql+asyncpg://postgres:postgres@localhost:5432/mentoring`

- **User:** `postgres`  
- **Password:** `postgres`  
- **Database:** `mentoring` (created by Docker Compose)  
- **Host/port:** `localhost:5432`

If **port 5432 is already in use**, change `docker-compose.yml` to `"5433:5432"` and set  
`DATABASE_URL=...postgres:postgres@localhost:5433/mentoring`.

### Alternative: PostgreSQL installed on Windows

1. Install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/windows/) and note the superuser password you set.
2. Open **pgAdmin** or `psql` and run:

```sql
CREATE DATABASE mentoring;
```

(If you use a user other than `postgres`, grant that user access to `mentoring`.)

3. Edit **`backend/.env`**:

```env
DATABASE_URL=postgresql+asyncpg://YOUR_USER:YOUR_PASSWORD@localhost:5432/mentoring
```

4. Run `alembic upgrade head` from **`backend`**.

### If Alembic says “connection refused”

Nothing is listening on the host/port in `DATABASE_URL`—start Docker Compose or the Windows PostgreSQL service, and confirm the port matches `.env`.

---

## App setup

```powershell
cd path\to\mentor-mentee\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

After the database is up and migrations are applied:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: `http://localhost:8000/api/v1`
- OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Headers

All business routes require `X-User-Id: <uuid>` (simulates API Gateway after JWT validation).

## Scope (this slice)

- `POST /api/v1/profiles/mentee`, `GET /api/v1/profiles/me`
- `POST /api/v1/profiles/mentor` (needed so mentors exist before requests)
- `POST /api/v1/requests`, `PUT /api/v1/requests/{id}/status`
- DPDP: `guardian_consent_status == PENDING` → `403` on creating requests
- Stub `publish_event` logs `MENTORSHIP_REQUEST_ACCEPTED` on accept

Scheduling, credits, and AI matching are **not** implemented here.
