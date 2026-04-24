
---

### 🧠 The Standardized "Amount" Logic (The Golden Rule)

Inside the Gamification Microservice, the logic for evaluating *any* transaction (whether async earn or sync spend) will follow this exact flow:

1. **Check the Payload:** Did the incoming payload include an `"amount"` field?
2. **If YES (Explicit Override):** The Gamification engine ignores the database's default value and uses the payload's `amount`.
3. **If NO (Database Default):** The Gamification engine queries the `activity_rules` table and uses the `base_credit_value`.

### 🔄 How this looks in practice (Standardized Payloads)

#### Scenario 1: Standard Earning (Relying on the Admin's DB configuration)
A youngster attends a normal pulse group meeting. The Event Service doesn't care about points, so it omits the `amount` field.
```json
{
  "rule_code": GamificationRules.ATTEND_STANDARD_EVENT,
  "user_id": "usr_123",
  "idempotency_key": "pulse_meeting_456"
}
```
*Result:* Gamification sees `amount` is missing. It checks the DB, sees `base_credit_value = 50`, and credits the user 50 points.

#### Scenario 2: Special Earning (Overriding the DB configuration)
The youngster wins the Summer Hackathon. The Event Service wants to give a massive custom reward.
```json
{
  "rule_code": GamificationRules.ATTEND_STANDARD_EVENT,
  "user_id": "usr_123",
  "amount": 1000,           // Standardized explicit override!
  "reason": "Won the Summer Hackathon",
  "idempotency_key": "hackathon_winner_789"
}
```
*Result:* Gamification sees `"amount": 1000`. It ignores the DB default of 50, and credits the user 1,000 points.

#### Scenario 3: Synchronous Spending (The Saga)
A youngster buys a premium event ticket or books an executive mentor.
```json
{
  "rule_code": GamificationRules.PURCHASE_PREMIUM_EVENT,
  "user_id": "usr_123",
  "amount": 100,            // Required for all spending!
  "idempotency_key": "ticket_purchase_ai_webinar"
}
```

---

### 🛡️ Why Spending MUST always include the "amount"

You might ask: *"If the database has a `base_credit_value` for spending, why does the Mentor or Event microservice need to pass the `amount` at all?"*

**We must mandate the `amount` field for spending to protect against Price Desync (Race Conditions).**

Imagine this scenario:
1. Youngster opens the Mentor App. The app fetches the Mentor's price: **50 Credits**.
2. The youngster hesitates for 5 minutes before clicking "Book".
3. Meanwhile, an Admin logs into the dashboard and increases the Mentor Tier price to **100 Credits**.
4. The youngster clicks "Book".
5. *If the Mentor service didn't pass the `amount`:* The Gamification service would look at the DB, deduct 100 credits, and the youngster would be furious because they agreed to 50 on their screen.

By forcing the emitting microservice to pass `"amount": 50` during a Spend transaction, the Gamification Service acts as the final validator. If the Admin changed the price, the Gamification service can safely process the 50 credits the user originally agreed to (or reject it with an error saying "Price has updated"), protecting the trust in your virtual economy.

Standardizing the field to **`amount`** simplifies the API contracts immensely. 
* For earning, it is **Optional** (used only for custom bonuses).
* For spending, it is **Required** (acting as a price lock).

