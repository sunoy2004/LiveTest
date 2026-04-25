# Test users (User Service seed)

Password for all non-admin seeded accounts: **`password123`**

On startup, the User Service runs seed routines that **delete every user account except** the allowlist below: **`admin@test.com`**, **`mentor_1@test.com` … `mentor_10@test.com`**, and **`mentee_1@test.com` … `mentee_10@test.com`**. Any other rows (e.g. `mentor@test.com`, `aisha@test.com`, older manual seeds) are removed so the DB matches this document.

You can also run `python -m app.seed` from the `user-service` folder to apply the same prune + seed without restarting the API.

---

##Gamification admin
user: admin
password: admin



## Admin

| Display | Email | Password |
|--------|-------|----------|
| Admin | admin@test.com | password |

---

## Mentors (10)

| Name (from email) | Email | Password |
|-------------------|-------|----------|
| Mentor 1 | mentor_1@test.com | password123 |
| Mentor 2 | mentor_2@test.com | password123 |
| Mentor 3 | mentor_3@test.com | password123 |
| Mentor 4 | mentor_4@test.com | password123 |
| Mentor 5 | mentor_5@test.com | password123 |
| Mentor 6 | mentor_6@test.com | password123 |
| Mentor 7 | mentor_7@test.com | password123 |
| Mentor 8 | mentor_8@test.com | password123 |
| Mentor 9 | mentor_9@test.com | password123 |
| Mentor 10 | mentor_10@test.com | password123 |

**Profile notes (seed):** each mentor has `tier_id` PROFESSIONAL, **Mentor level** `TIER_2`, accepting requests, expertise `Topic area {i}` + Mentoring, `total_hours_mentored = 10 × i`.

---

## Mentees (10)

| Name (from email) | Email | Password |
|-------------------|-------|----------|
| Mentee 1 | mentee_1@test.com | password123 |
| Mentee 2 | mentee_2@test.com | password123 |
| Mentee 3 | mentee_3@test.com | password123 |
| Mentee 4 | mentee_4@test.com | password123 |
| Mentee 5 | mentee_5@test.com | password123 |
| Mentee 6 | mentee_6@test.com | password123 |
| Mentee 7 | mentee_7@test.com | password123 |
| Mentee 8 | mentee_8@test.com | password123 |
| Mentee 9 | mentee_9@test.com | password123 |
| Mentee 10 | mentee_10@test.com | password123 |

**Wallet (seed):** **Mentee 1–5:** **200** credits (User Service mirror + gamification top-up). **Mentee 6–10:** **500** credits. Requires **GAMIFICATION_SERVICE_URL** for the live ledger; seed calls `GET /balance/{user_id}` then `POST /add` as needed.

**Profile notes (seed):** goals `Learning goal {i}` + Skill growth, undergraduate, guardian consent not required.

---

## Mentorship connections (ACTIVE)

Each mentee is connected to the mentor with the **same index** (for straightforward assignment and booking tests).

| Mentor | Mentee | Status |
|--------|--------|--------|
| Mentor 1 | Mentee 1 | ACTIVE |
| Mentor 2 | Mentee 2 | ACTIVE |
| Mentor 3 | Mentee 3 | ACTIVE |
| Mentor 4 | Mentee 4 | ACTIVE |
| Mentor 5 | Mentee 5 | ACTIVE |
| Mentor 6 | Mentee 6 | ACTIVE |
| Mentor 7 | Mentee 7 | ACTIVE |
| Mentor 8 | Mentee 8 | ACTIVE |
| Mentor 9 | Mentee 9 | ACTIVE |
| Mentor 10 | Mentee 10 | ACTIVE |

---

## Dashboard / scheduling demo data

- **Upcoming sessions, goals, vault sample:** seeded on the **Mentor 1 ↔ Mentee 1** connection (`mentor_1@test.com` / `mentee_1@test.com`).
- **Bookable slots:** generated for **all** mentors `mentor_1` … `mentor_10` (UTC windows); quick smoke tests often use **Mentor 1**.

---

## Reseed / refresh dashboard dummy rows

From `user-service` directory (with `DATABASE_URL` set):

```bash
python -m app.seed --force
```

`--force` clears and re-applies dashboard sessions/goals/history for the Mentor 1 ↔ Mentee 1 connection.
