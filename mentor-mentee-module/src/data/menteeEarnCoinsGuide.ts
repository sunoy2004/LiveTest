/**
 * Mentee-facing copy for “Earn coins”.
 * Live amounts match `activity_rules.base_credit_value` from gamification-service Alembic seeds
 * (ATTEND_MENTEE_SESSION, RESOLVE_NO_SHOW_REFUND, LEGACY_CREDIT_ADD, ADMIN_GRANT).
 * Roadmap rows follow `Gamification Rule Dictionary.md` (amounts are admin-configurable when shipped).
 */

export type MenteeEarnWay = {
  title: string;
  description: string;
  /** Human-readable reward line, e.g. "+10 coins" or "Admin-configured" */
  reward: string;
};

/** Rules that exist in the ledger today (mentee-relevant earns). */
export const menteeEarnWaysLive: MenteeEarnWay[] = [
  {
    title: "Attend your mentoring session",
    description:
      "When a booked 1:1 completes, you earn for showing up on time (rule ATTEND_MENTEE_SESSION). Published after the session is marked complete.",
    reward: "+10 coins (base)",
  },
  {
    title: "Dispute refund",
    description:
      "If an admin resolves a dispute in your favor (e.g. mentor no-show), a credit may be applied (rule RESOLVE_NO_SHOW_REFUND).",
    reward: "+1 coins (seed default; may match session cost in production)",
  },
  {
    title: "Welcome or migration credit",
    description:
      "One-off or migration top-ups can post as LEGACY_CREDIT_ADD when accounts are funded.",
    reward: "+1 coin per unit (seed default)",
  },
  {
    title: "Promotional grant",
    description: "Support or marketing may add coins via ADMIN_GRANT from the gamification admin.",
    reward: "Varies (admin)",
  },
];

/** Product dictionary — not all rules are wired in this repo yet; amounts are set in admin when enabled. */
export const menteeEarnWaysRoadmap: MenteeEarnWay[] = [
  {
    title: "Complete your profile",
    description: "Photo, bio, and learning goals (COMPLETE_PROFILE).",
    reward: "Admin-configured",
  },
  {
    title: "Secure guardian consent",
    description: "For minors: verified guardian flow (SECURE_GUARDIAN_CONSENT).",
    reward: "Admin-configured (high value)",
  },
  {
    title: "Refer friends",
    description: "Invite others (REFER_NEW_MEMBER) and hit milestones (REFERRAL_MILESTONE_REACHED).",
    reward: "Admin-configured",
  },
  {
    title: "Top ratings & reliability",
    description: "Quality incentives such as RECEIVE_TOP_RATING; complements session attendance.",
    reward: "Admin-configured",
  },
  {
    title: "Events & community",
    description:
      "Workshops, forums, Q&A (e.g. ATTEND_STANDARD_EVENT, POST_COMMUNITY_ASK, PROVIDE_HELPFUL_ANSWER).",
    reward: "Admin-configured",
  },
];
