# 🔄 Master Workflow Document: Mentor-Mentee Ecosystem

<!-- markdownlint-disable MD013 -->

This document outlines the step-by-step sequence of operations for the five most critical user journeys in the system.

## Actors Key

* 👤 **Client:** The Youngster's UI (SPA / Mobile App).
* 🚪 **Gateway:** Google Cloud API Gateway.
* 🧠 **Mentoring API:** Our FastAPI Microservice.
* 🏦 **Credit API:** External Gamification/Economy Microservice.
* 🤖 **AI API:** External Matching/Graph Microservice.
* 📢 **Broker:** Google Cloud Pub/Sub.

---

## Workflow 1: Onboarding & DPDP Compliance (India)

*Ensures minors cannot interact with adults without legal parental consent.*

1. **Registration:** Youngster registers globally via the User Service.
2. **Profile Creation:** Client calls `POST /profiles/mentee` on the Mentoring API.
3. **Age Verification:** Mentoring API checks the `is_minor` flag. If true, it hardcodes `guardian_consent_status = 'PENDING'` in Cloud SQL and returns `201 Created`.
4. **The Lockout:** The youngster can browse the UI, but if they try to call `POST /requests` to message a mentor, Mentoring API instantly returns `403 Forbidden: Guardian Consent Required`.
5. **The Legal Unlock (Asynchronous):**
    * The parents verify their identity via DigiLocker in the User Service.
    * User Service publishes `GUARDIAN_CONSENT_GRANTED` to Broker.
    * Mentoring API catches the event in the background and updates the Postgres profile to `GRANTED`.
    * The youngster is now legally cleared to participate.

---

## Workflow 2: AI Discovery & Mentor Request

*How youngsters find and initiate contact with mentors without overloading the transactional database.*

1. **Discovery:** Client loads the Dashboard. Client bypasses the Mentoring API and makes a direct call to the **AI API** (`GET /recommendations`).
2. **The Match:** AI API queries its Graph DB and returns a list of highly compatible Mentor IDs.
3. **The Pitch:** Mentee selects a mentor and calls `POST /requests` (via Gateway) with an `intro_message`.
4. **Validation:** Mentoring API checks if a pending request already exists (Postgres constraint check). If safe, it saves the request as `PENDING`.
5. **Notification:** Broker broadcasts `MENTORSHIP_REQUESTED`. The Notification Service emails the Mentor: *"You have a new request!"*
6. **The Handshake:** Mentor logs in, reads the pitch, and clicks Accept (`PUT /requests/{id}/status`).
7. **Connection Established:** Mentoring API updates request to `ACCEPTED`, creates an `ACTIVE` row in `mentorship_connections`, and broadcasts `MENTORSHIP_REQUEST_ACCEPTED` so the AI Engine learns they are now connected.

---

## Workflow 3: The Gamified Booking Saga (Distributed Transaction)

*The most critical workflow. Prevents double-booking a time slot AND double-spending credits.*

1. **Intent:** Mentee views Mentor's calendar and clicks **[ Book for 50 Credits ]**.
2. **API Call:** Client calls `POST /scheduling/book` with `slot_id` and `agreed_cost=50`.
3. **Fast Failure Check:** Mentoring API checks `cached_credit_score` in Postgres. If mentee has 30 credits, it aborts instantly (`402 Payment Required`).
4. **The Hold (Row Lock):** Mentoring API opens an ACID transaction.
    * Executes `SELECT * FROM time_slots WHERE id = slot_id FOR UPDATE`.
    * Marks `is_booked = TRUE`.
    * Creates session with status `PENDING_PAYMENT`.
5. **The Deduction (Synchronous Saga):** Mentoring API makes a highly secure, internal gRPC/REST call directly to the **Credit API**: *"Deduct 50 credits for user X. Transaction Ref: Session_999"*.
6. **The Resolution:**
    * *If Credit API succeeds:* Mentoring API commits the Postgres transaction. Session status becomes `SCHEDULED`. Mentoring API calls Google Meet API to generate a video link and saves it.
    * *If Credit API fails (e.g., insufficient funds):* Mentoring API rolls back. Session becomes `CANCELED`, time slot `is_booked = FALSE`.
7. **Event Broadcast:** Mentoring API publishes `SESSION_SCHEDULED` to Broker to trigger calendar invites.

---

## Workflow 4: Session Execution & Post-Session Gamification

*Closing the loop and rewarding the users for participating.*

1. **The Meeting:** At the scheduled time, users click the Google Meet link in Dashboard Widget A.
2. **The Debrief:** After the call, the UI prompts both users to rate the session and write notes.
3. **Logging History:** Client calls `POST /sessions/{id}/history`.
4. **JSONB Storage:** Mentoring API saves the structured ratings and unstructured text/attachments into the `JSONB` `notes_data` column. Session is updated to `COMPLETED`.
5. **Gamification Trigger:** Broker broadcasts `SESSION_COMPLETED`.
6. **The Reward:** The **Credit API** listens to this event. It awards +20 XP/Credits to the Mentee for learning, and +50 Credits to the Mentor for teaching. The ecosystem thrives!

---

## Workflow 5: Admin Dispute Resolution (The "No-Show" Refund)

*Ensuring fairness and trust in the virtual economy.*

1. **The Report:** Mentee waits 15 minutes, but the Mentor never joins the call. Mentee clicks "Report No-Show".
2. **Ticket Created:** Mentoring API logs an `OPEN` ticket in `reports_and_disputes`.
3. **Admin Review:** Operations team views the ticket in their Admin Panel. They verify the Google Meet logs and confirm the mentor was absent.
4. **Admin Action:** Admin clicks **[ Resolve: Refund Mentee ]**. Client calls `POST /admin/disputes/{id}/resolve-no-show` (Requires `X-Is-Admin: true` header).
5. **The Reverse Saga:**
    * Mentoring API updates session status to `NO_SHOW`.
    * Mentoring API makes a sync call to **Credit API**: *"Refund 50 credits to Mentee. Deduct 50 'Trust Points' from Mentor."*
6. **Quality Control:** If Mentor hits 3 `NO_SHOW` statuses, Mentoring API automatically toggles their `is_accepting_requests = FALSE` to protect future mentees.

---
