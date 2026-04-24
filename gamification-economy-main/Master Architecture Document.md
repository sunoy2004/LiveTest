


Here is the complete, official **Master Architecture Document for the Gamification & Economy Microservice**. 

This document serves as the absolute source of truth for your engineering team to build the "Central Bank" of your networking club.

---

# 📘 Master Architecture Document: Gamification & Economy Microservice

## 🏢 1. Architecture Blueprint

### 1.1 Core Architectural Principles
*   **The "Central Bank" Pattern:** This microservice is the strict, sole authority on point balances. Ecosystem services (like Events or Forums) do not dictate credit values; they emit generic domain events. This service translates those events into credits.
*   **Immutable FinTech Ledger:** To ensure zero "economy-breaking" bugs and a perfect audit trail, credit balances are calculated using an append-only ledger. Rows are never `UPDATED` or `DELETED`.
*   **Whole Integer Gamification:** To maximize dopamine and user satisfaction, all credits are positive or negative integers. No floating-point decimals.
*   **Dynamic Configurable Rules:** Operations teams can dynamically alter the economy (change point values, disable exploited rules) via the database without requiring code deployments.
*   **Shared Contract Library:** To prevent database duplication, all microservices share a lightweight code library (`networking-club-core`) containing the strict string Enums (the "Action Verbs") required to spend or earn points.

### 1.2 The Technology Stack (Google Cloud Platform)
*   **API Gateway:** **Google Cloud API Gateway** + **Cloud Armor** (WAF).
*   **Application Server:** **Google Cloud Run** (Serverless containers).
*   **Framework:** **FastAPI (Python)** using Pydantic V2 and SQLAlchemy 2.0.
*   **Database:** **Cloud SQL for PostgreSQL** *(Logically isolated as `db_gamification` on the shared GCP instance to eliminate extra server costs).*
*   **Message Broker:** **Google Cloud Pub/Sub**.

---

## 🗄️ 2. Database Schema Design (PostgreSQL)

### 2.1 The Dynamic Rule Engine
*   **`activity_rules`** *(Admin-configurable economy dictionary)*
    *   `rule_code` (VARCHAR, Primary Key) - e.g., `ATTEND_STANDARD_EVENT`, `BOOK_MENTOR_SESSION`.
    *   `transaction_type` (ENUM: `EARN`, `SPEND`)
    *   `base_credit_value` (INTEGER, Not Null) - e.g., `50`
    *   `is_active` (BOOLEAN, Default: TRUE) - *Admins can toggle this instantly.*
    *   `cooldown_seconds` (INTEGER, Default: 0) - *Prevents spam-farming points.*
    *   `updated_at` (TIMESTAMPTZ)

### 2.2 The User State
*   **`wallets`** *(Current Snapshot)*
    *   `user_id` (UUID, Primary Key) - *Foreign reference to Global Identity.*
    *   `current_balance` (INTEGER, Default: 0) - *The spendable currency.*
    *   `lifetime_earned` (INTEGER, Default: 0) - *Total accumulated. (Used for all-time leaderboards so spending doesn't drop your rank).*
    *   `last_updated_at` (TIMESTAMPTZ)

### 2.3 The Immutable Audit Trail
*   **`ledger_transactions`** *(The Financial Heartbeat)*
    *   `transaction_id` (UUID, Primary Key)
    *   `user_id` (UUID, Not Null, Indexed)
    *   `rule_code` (VARCHAR, Not Null) ➔ FK: `activity_rules.rule_code`
    *   `amount` (INTEGER, Not Null) - *e.g., `+50` or `-100`*
    *   `balance_after` (INTEGER, Not Null) - *Snapshot of wallet after this row.*
    *   `idempotency_key` (VARCHAR, Unique Constraint) - *Prevents double-awarding if the network glitches and sends an event twice.*
    *   `created_at` (TIMESTAMPTZ, Default: NOW())

---

## 🌐 3. REST API Design (FastAPI)

### 3.1 Public APIs (Called by Client via Gateway)
*   **`GET /api/v1/wallet/me`**
    *   *Returns (200 OK):* `{"current_balance": 450, "lifetime_earned": 1200}`
*   **`GET /api/v1/wallet/history`**
    *   *Returns (200 OK):* Paginated list of ledger entries for UI display.

### 3.2 Internal APIs (Zero-Trust VPC Inter-Service Calls)
*   **`POST /api/v1/internal/transactions/deduct`** 🏆 *(The Saga Endpoint)*
    *   *Purpose:* Called synchronously by Mentor or Event modules during a purchase.
    *   *Body:* `{"user_id": "usr_123", "rule_code": "BOOK_MENTOR_SESSION", "amount": 50, "idempotency_key": "booking_req_999"}`
    *   *Logic:* Opens ACID Tx ➔ Checks Wallet ➔ Inserts Ledger ➔ Updates Wallet.
    *   *Returns:* `200 OK` (Approved) OR `402 Payment Required` (Insufficient Funds).

### 3.3 Admin APIs (Requires `X-Is-Admin: true`)
*   **`PUT /api/v1/admin/rules/{rule_code}`**
    *   *Body:* `{"base_credit_value": 100, "is_active": true}`
    *   *Purpose:* Instantly adjust the economy to fight inflation.
*   **`POST /api/v1/admin/wallet/{user_id}/grant`**
    *   *Body:* `{"amount": 500, "reason": "Won Hackathon", "rule_code": "ADMIN_OVERRIDE"}`

---

## 📡 4. Ecosystem Choreography (Pub/Sub Events)

### 4.1 Asynchronous Earning (Listening to the Ecosystem)
The Gamification service utilizes an internal **Event Mapper** to translate generic ecosystem events into ledger credits.
*   **Topic: `events.webinars`** ➔ Listens for `ATTENDANCE_LOGGED` ➔ Maps to `ATTEND_STANDARD_EVENT`.
*   **Topic: `mentoring.sessions`** ➔ Listens for `SESSION_COMPLETED` ➔ Maps to `DELIVER_MENTOR_SESSION` (for mentor) and `ATTEND_MENTEE_SESSION` (for mentee).
*   **Topic: `identity.users`** ➔ Listens for `SECURE_GUARDIAN_CONSENT` ➔ Maps to high-value reward.

### 4.2 Broadcasting State (Updating the Ecosystem)
Whenever a `wallet` is updated via Ledger insertion, this service broadcasts the new state.
*   **Topic: `economy.credits.events`**
*   **Event:** `CREDIT_SCORE_UPDATED`
*   **Payload:** `{"user_id": "usr_123", "new_current_balance": 500, "new_lifetime_earned": 1250}`
*   **Consumers:** Mentor-Mentee DB (for fast-read caching), AI Matching DB (to factor activity levels into recommendation weights).

---

## 🔄 5. Master Workflows

### Workflow A: Passive Asynchronous Earning
1.  **Trigger:** Youngster attends a webinar.
2.  **Broadcast:** Event Service publishes `ATTENDANCE_LOGGED` to Pub/Sub.
3.  **Translation:** Gamification Service consumes the event and maps it to the `ATTEND_STANDARD_EVENT` rule.
4.  **Database Execution:** Gamification API queries `activity_rules`. If active, it opens a Postgres transaction, inserts `+50` into `ledger_transactions` (using an Idempotency Key to prevent duplicate processing), and updates `wallets`.
5.  **State Sync:** Gamification Service broadcasts `CREDIT_SCORE_UPDATED`.

### Workflow B: Synchronous Spending (The Distributed Transaction)
1.  **Intent:** Youngster clicks "Book Mentor for 100 Credits".
2.  **The Hold:** Mentor Service locks the time slot and marks it `PENDING_PAYMENT`.
3.  **The Call:** Mentor Service makes a fast, synchronous HTTP call to `POST /internal/transactions/deduct`.
4.  **Validation:** Gamification API checks the `wallets` table.
    *   *If `current_balance` < 100:* Returns `402 Payment Required`. Mentor Service rolls back the booking.
    *   *If `current_balance` >= 100:* Proceeds to Step 5.
5.  **The Deduction:** Gamification API inserts `-100` into the ledger, drops the wallet balance by 100, and returns `200 OK`.
6.  **Resolution:** Mentor Service commits the booking as `SCHEDULED`.

### Workflow C: Admin Dynamic Economy Override
1.  **Intent:** Admins want to incentivize answering forum questions.
2.  **Action:** Admin UI calls `PUT /api/v1/admin/rules/PROVIDE_HELPFUL_ANSWER` changing the value from `10` to `50`.
3.  **Result:** The database row is updated. Instantly, all subsequent asynchronous earning events processed by Workflow A will award 50 points instead of 10. Zero code recompilation required.

### Workflow D: Crash Recovery & Idempotency
1.  **Glitch:** Pub/Sub network retry sends the exact same "Webinar Attended" event twice.
2.  **Defense:** Gamification API attempts to insert the ledger row using the same generated `idempotency_key` (e.g., `webinar_99_reward_usr_1`).
3.  **Resolution:** PostgreSQL throws a unique constraint violation. Gamification API catches it, ignores the message, and acknowledges it. The youngster is safely protected from double-awarding.

---
