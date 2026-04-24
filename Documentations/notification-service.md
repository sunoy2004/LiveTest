# Notification Service (`notification-service`)

The Notification Service **persists a log of domain events** for observability and future notification channels. It subscribes to **three Redis channels** used across the platform and writes rows to **PostgreSQL**.

---

## Role in the system

| Concern | Implementation |
|--------|------------------|
| Storage | `NotificationLog` table — topic, event type, JSON payload, timestamps |
| Ingest | Async Redis subscriber on `mentoring.connections.events`, `mentoring.sessions.events`, `economy.credits.events` |
| API | `GET /notifications` — last 50 notifications, newest first (read-side for admin/debug) |

This service does **not** send email/SMS by default; it **records** what happened. Extend `record_notification` / outbound adapters if you add real delivery.

**In-app realtime** (dashboard refresh for mentors/mentees) is driven by User Service publishing to Redis channel `app:events` and the User Service WebSocket (`/ws/dashboard`). The notification service does **not** replace that path; it **mirrors** cross-service topics into `notification_logs` for audit and future outbound channels. Both use the **same** `REDIS_URL` in Docker Compose.

---

## Architecture

- **`app/main.py`** — FastAPI, `create_all` + Redis listener lifespan.
- **`app/realtime/redis_listener.py`** — Subscribes to all three cross-service topics; on each message, `record_notification(...)` and commit.
- **`app/services/event_bus.py`** — Topic name constants (must match User Service / Credit / AI).

### Event alignment

Topics (string channel names):

- `mentoring.connections.events` — mentorship requests / accept flows from User Service.
- `mentoring.sessions.events` — session scheduled / completed fan-out.
- `economy.credits.events` — credit updates from Credit Service (and related).

**`mentoring.connections.events` — `type` values the listener persists** (non-exhaustive):

| `type` | Source |
|--------|--------|
| `mentorship_requested` | Mentee asks to connect to a mentor |
| `mentorship_request_accepted` | Mentor accepts connection request |
| `session_booking_requested` | Mentee requests a session slot (mentor notified via `notify_user_ids` in payload) |
| `session_booking_rejected` | Mentor declines the session request (mentee in `notify_user_ids`) |

**`mentoring.sessions.events`** includes e.g. `session_scheduled` (after mentor accepts and credits are charged) and `session_completed`.

The JSON body always includes a top-level `"type"` field (used as `event_type` in `notification_logs`) plus merged payload fields and `notify_user_ids`.

---

## HTTP API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/notifications` | List recent persisted notifications |

---

## Configuration

Copy `notification-service/.env.example` to `notification-service/.env`.

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | e.g. `postgresql://postgres:postgres@localhost:5434/notifications_db` (compose maps **5434** for host access) |
| `REDIS_URL` | Same Redis as the rest of the stack |

---

## Local development

```bash
cd notification-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# Postgres on 5434 + Redis
uvicorn app.main:app --reload --port 8003
```

---

## Docker

**`docker-compose.microservices.yml`**:

- **`notifications-db`** — Postgres 15, `notifications_db`, host **5434** → 5432.
- **`notification-service`** — build `./notification-service`, **8003:8000**, `depends_on` DB healthy, network `mentor_stack`.

```bash
cd user-service && docker compose up -d
cd .. && docker compose -f docker-compose.microservices.yml up -d notifications-db notification-service
```

---

## Operations

- [ ] Ensure Redis is the **shared** instance so publishers and this consumer see the same channels.
- [ ] Backup `notifications_data` volume.
- [ ] For high volume, add retention job or index tuning on `NotificationLog`.

---

## Troubleshooting

| Symptom | Check |
|--------|--------|
| Empty `/notifications` | Redis not receiving publishes, wrong `REDIS_URL`, listener crashed (logs) |
| DB errors | `DATABASE_URL`, migrations/schema (`create_all` on startup) |

---

## Repository layout

```
notification-service/
  app/
    main.py
    db/
    models.py
    realtime/redis_listener.py
    services/notify_service.py
  requirements.txt
  Dockerfile
  .env.example
```
