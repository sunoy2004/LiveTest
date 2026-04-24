# 📘 Master Architecture Document: Mentor-Mentee Microservice

<!-- markdownlint-disable MD013 -->

## 🏢 1. Architecture Blueprint

### 1.1 Core Architectural Principles

* **Domain-Driven Design (DDD):** This microservice owns only the "Mentoring" domain. Identity is managed by the User Service; Gamification/Credits are managed by the Credit Service; and AI matching is handled by a separate Graph DB service.
* **Virtual Economy (Saga Pattern):** Booking a mentor utilizes a "Hold & Deduct" distributed transaction to prevent double-spending of credits.
* **Admin-Regulated Economy:** Mentors do not set prices. Admins control inflation via a Global Tier System.
* **DPDP Act (2023) Compliance:** Full adherence to Indian law regarding minors. Data is sovereign to GCP India, and verifiable parental consent is hardcoded into the business logic.
* **Mobile-First SPA UI:** No nested sidebars. The UI relies on visual Dashboard Widgets (Upcoming, Matchmaker Carousel, Goals, Vault).

### 1.2 The Technology Stack (Google Cloud Platform)

* **API Gateway:** **Google Cloud API Gateway** + **Cloud Armor** (WAF & Rate Limiting).
* **Application Server:** **Google Cloud Run** (Serverless, Auto-scaling containers).
* **Framework:** **FastAPI (Python)** with SQLAlchemy 2.0 (Async) and Pydantic V2.
* **Database:** **Cloud SQL for PostgreSQL** (Hosted in `asia-south1` or `asia-south2`).
* **Message Broker:** **Google Cloud Pub/Sub** (For Event-Driven CQRS and Notifications).
* **Security Auth:** Asymmetric JWT (RS256). API Gateway validates signatures and passes `X-User-Id` to FastAPI.

---

## 🗄️ 2. Database Schema Design (PostgreSQL)

### 2.1 Admin & Economy Configuration

* **`mentor_tiers`** *(Global pricing controlled by Admins)*
  * `tier_id` (VARCHAR, Primary Key) - e.g., `PEER`, `PROFESSIONAL`, `EXPERT`
  * `tier_name` (VARCHAR)
  * `session_credit_cost` (INTEGER) - e.g., 50, 100, 250

### 2.2 Domain Profiles

* **`mentee_profiles`** *(What the user wants to learn)*
  * `id` (UUID, PK)
  * `user_id` (UUID, Unique, Not Null) - *From User Service*
  * `learning_goals` (TEXT[])
  * `education_level` (VARCHAR)
  * `is_minor` (BOOLEAN, Not Null)
  * `guardian_consent_status` (ENUM: `PENDING`, `GRANTED`, `NOT_REQUIRED`)
  * `cached_credit_score` (INTEGER, Default: 0) - *Async cache for fast booking checks.*

* **`mentor_profiles`** *(What the user can offer)*
  * `id` (UUID, PK)
  * `user_id` (UUID, Unique, Not Null)
  * `tier_id` (VARCHAR, FK ➔ `mentor_tiers.tier_id`)
  * `is_accepting_requests` (BOOLEAN, Default: TRUE)
  * `expertise_areas` (TEXT[])
  * `total_hours_mentored` (INTEGER, Default: 0)

### 2.3 Relationship Engine

* **`mentorship_requests`**
  * `id` (UUID, PK)
  * `mentee_id` (UUID, FK ➔ `mentee_profiles.id`)
  * `mentor_id` (UUID, FK ➔ `mentor_profiles.id`)
  * `status` (ENUM: `PENDING`, `ACCEPTED`, `DECLINED`)
  * `intro_message` (TEXT)
  * *Constraint:* `UNIQUE(mentee_id, mentor_id) WHERE status = 'PENDING'`

* **`mentorship_connections`**
  * `id` (UUID, PK)
  * `mentee_id` (UUID, FK)
  * `mentor_id` (UUID, FK)
  * `status` (ENUM: `ACTIVE`, `PAUSED`, `COMPLETED`)

### 2.4 Scheduling & Booking Engine

* **`time_slots`** *(Strict ACID concurrency locking used here)*
  * `id` (UUID, PK)
  * `mentor_id` (UUID, FK)
  * `start_time` (TIMESTAMPTZ, Not Null) - *Always stored in UTC*
  * `end_time` (TIMESTAMPTZ, Not Null)
  * `is_booked` (BOOLEAN, Default: FALSE)

* **`sessions`**
  * `id` (UUID, PK)
  * `connection_id` (UUID, FK)
  * `slot_id` (UUID, Unique, FK)
  * `status` (ENUM: `PENDING_PAYMENT`, `SCHEDULED`, `COMPLETED`, `CANCELED`, `NO_SHOW`)
  * `meeting_url` (VARCHAR, Nullable)

### 2.5 Gamification & Safety Data

* **`goals`** *(For Widget C: Quests)*
  * `id` (UUID, PK), `connection_id` (UUID, FK), `title` (VARCHAR), `status` (ENUM)
* **`session_history`** *(For Widget D: Vault)*
  * `id` (UUID, PK), `session_id` (UUID, Unique FK)
  * `notes_data` (**JSONB**) - *Flexible storage for notes, AI transcripts, attachments.*
  * `mentor_rating` (SMALLINT), `mentee_rating` (SMALLINT)
* **`reports_and_disputes`** *(For Admins)*
  * `id` (UUID, PK), `session_id` (UUID, FK), `reported_by` (UUID)
  * `reason_category` (ENUM: `NO_SHOW`, `SAFETY`, `OTHER`)
  * `status` (ENUM: `OPEN`, `RESOLVED`)

---

## 🌐 3. REST API Design (FastAPI)

*(All endpoints assume the API Gateway has passed `X-User-Id` in the headers).*

### 3.1 Profiles & Onboarding

* **`GET /api/v1/profiles/me`**
  * *Returns:* Mentee and Mentor profile details, including `cached_credit_score`.
* **`POST /api/v1/profiles/mentee`**
  * *Body:* `{"learning_goals": ["Python"], "education_level": "College"}`
  * *Returns:* `201 Created`

### 3.2 Scheduling & Booking (The Saga)

* **`GET /api/v1/scheduling/availability?mentor_id={id}`**
  * *Returns:* Mentor's available `time_slots` and their `session_credit_cost` (fetched via `mentor_tiers` JOIN).
* **`POST /api/v1/scheduling/book`** 🏆 *(The Distributed Transaction)*
  * *Body:* `{"connection_id": "conn_123", "slot_id": "slot_456", "agreed_cost": 50}`
  * *Logic:*
        1. Fast check if `cached_credit_score >= agreed_cost`.
        2. `SELECT FOR UPDATE` on `time_slots` to prevent race conditions.
        3. Make sync gRPC call to Credit Service to deduct credits.
        4. If success: Commit as `SCHEDULED`. If fail: Rollback to `CANCELED`.
  * *Returns:* `201 Created` with `meeting_url` OR `402 Payment Required`.

### 3.3 Dashboard UIs (Optimized Reads)

* **`GET /api/v1/dashboard/upcoming-session`** ➔ Powers Widget A
* **`GET /api/v1/dashboard/goals`** ➔ Powers Widget C
* **`GET /api/v1/dashboard/vault`** ➔ Powers Widget D

### 3.4 Admin Controls (Requires `X-Is-Admin: true`)

* **`PUT /api/v1/admin/tiers/{tier_id}`** ➔ Update global pricing for a tier.
* **`PUT /api/v1/admin/profiles/{mentee_id}/revoke-consent`** ➔ Instantly suspends minor's access due to parent withdrawal (DPDP).
* **`POST /api/v1/admin/disputes/{dispute_id}/resolve-no-show`** ➔ Triggers reverse saga: refunds mentee, flags mentor.

---

## 📡 4. Google Cloud Pub/Sub Events

To maintain decoupled architecture, this service interacts with the ecosystem via asynchronous Pub/Sub topics.

### 4.1 Consumed Events (What this service listens to)

**Topic: `economy.credits.events`**

* **Event:** `CREDIT_SCORE_UPDATED`
* **Payload:** `{"user_id": "usr_123", "new_total": 450}`
* **Action:** FastAPI updates the `mentee_profiles.cached_credit_score` in Postgres (CQRS pattern).

**Topic: `identity.users.events`**

* **Event:** `GUARDIAN_CONSENT_GRANTED`
* **Payload:** `{"user_id": "usr_123", "status": "GRANTED"}`
* **Action:** Updates `mentee_profiles.guardian_consent_status`.

### 4.2 Published Events (What this service broadcasts)

**Topic: `mentoring.connections.events`**

* **Event:** `MENTORSHIP_REQUEST_ACCEPTED`
* **Payload:** `{"connection_id": "conn_1", "mentor_id": "mtr_1", "mentee_id": "mte_1"}`
* **Consumers:** AI Matching Engine (updates Graph DB edge weight), Notification Service.

**Topic: `mentoring.sessions.events`**

* **Event:** `SESSION_SCHEDULED`
* **Payload:** `{"session_id": "sess_1", "mentor_id": "mtr_1", "start_time": "2026-04-10T14:00:00Z", "meeting_url": "..."}`
* **Consumers:** Notification Service (sends email/WhatsApp invites).

* **Event:** `SESSION_COMPLETED`
* **Payload:** `{"session_id": "sess_1", "mentor_rating": 5, "mentee_rating": 4}`
* **Consumers:** Credit/Gamification Service (rewards users with XP for completing a session), AI Matching Engine.

---
