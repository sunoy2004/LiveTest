### 📚 The Global Gamification Dictionary

#### 1. Identity & Onboarding (Growth & Compliance)
*Reward youngsters for setting up their accounts properly and helping the club grow.*
*   `COMPLETE_PROFILE` **(Earn)**: Adding a profile picture, bio, and learning goals.
*   `SECURE_GUARDIAN_CONSENT` **(Earn - High Value)**: Rewarding minors who successfully get their parents to complete the DPDP Act DigiLocker verification. *(This dramatically increases legal onboarding conversion rates!)*
*   `REFER_NEW_MEMBER` **(Earn)**: Bringing a friend into the club.
*   `REFERRAL_MILESTONE_REACHED` **(Earn)**: Bonus for bringing in 5, 10, or 20 friends.

#### 2. Mentor-Mentee Domain (The module we just built)
*Driving quality interactions and reliability.*
*   `BOOK_MENTOR_SESSION` **(Spend)**: Deducting credits to schedule a 1-on-1.
*   `DELIVER_MENTOR_SESSION` **(Earn - High Value)**: The mentor successfully teaching a session.
*   `ATTEND_MENTEE_SESSION` **(Earn - Low Value)**: The mentee showing up on time (encourages reliability).
*   `RECEIVE_TOP_RATING` **(Earn)**: Getting a 5-star review (Quality Control incentive).
*   `NO_SHOW_PENALTY` **(Spend/Penalty)**: Deducting points if a user misses a booked session without canceling.

#### 3. Events & Networking Domain
*Encouraging active participation in groups.*
*   `ATTEND_STANDARD_EVENT` **(Earn)**: Joining a free webinar or local offline meetup.
*   `PURCHASE_PREMIUM_EVENT` **(Spend)**: Buying a ticket to a VIP workshop or guest-speaker session.
*   `HOST_PULSE_MEETING` **(Earn)**: Taking the initiative to lead a small peer-to-peer study group.
*   `EVENT_SPEAKER_BONUS` **(Earn)**: Presenting a topic to peers.

#### 4. Community & Knowledge Sharing (Forums/Q&A)
*Creating a vibrant, self-sustaining community where peers help peers.*
*   `POST_COMMUNITY_ASK` **(Earn - Micro)**: Asking a thoughtful question.
*   `PROVIDE_HELPFUL_ANSWER` **(Earn)**: Replying to a peer's ask.
*   `ANSWER_UPVOTED` **(Earn)**: Community-driven quality control (earning points when others find your answer useful).

#### 5. Career & Opportunities (Jobs/Internships)
*The ultimate real-world value of the club.*
*   `UNLOCK_JOB_BOARD` **(Spend - One Time)**: Paying a sum of credits to unlock the premium internship listings.
*   `APPLY_FOR_INTERNSHIP` **(Spend - Micro)**: Costing a small amount of credits to apply for a job. *(Why Spend? This acts as a spam-filter. It forces youngsters to only apply for jobs they actually want, rather than spamming 100 partners with low-effort resumes).*
*   `SECURE_INTERNSHIP` **(Earn - Massive)**: The ultimate reward for landing a role through a club Partner.

---

### ⚙️ How Admins Will Use This
In your Admin Dashboard, the operations team will see a clean table listing these exact string names. Next to each, they will have a text box to type in the `base_credit_value` and a toggle switch for `is_active`. 

If the community is lacking in peer-to-peer help, the admin can simply change the value of `PROVIDE_HELPFUL_ANSWER` from `10` to `50` credits for the weekend to incentivize youngsters to help each other out!
