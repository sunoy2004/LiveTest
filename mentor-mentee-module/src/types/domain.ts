/** Architecture §2 — mentee_profiles.guardian_consent_status */
export type GuardianConsentStatus = "PENDING" | "GRANTED" | "NOT_REQUIRED";

/** Architecture §2 — mentor_tiers.tier_id */
export type MentorTierId = "PEER" | "PROFESSIONAL" | "EXPERT";

/** Architecture §2 — sessions.status */
export type SessionStatus =
  | "PENDING_PAYMENT"
  | "SCHEDULED"
  | "COMPLETED"
  | "CANCELED"
  | "NO_SHOW";

export type SearchRole = "mentor" | "mentee" | "all";

export interface SearchResultItem {
  user_id: string;
  mentor_profile_id?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  /** Optional combined label from some gateways */
  full_name?: string | null;
  role: Exclude<SearchRole, "all">;
  expertise: string[];
  tier?: MentorTierId | null;
  /** Mentors: server-resolved price (admin override or gamification BOOK_MENTOR_SESSION base). */
  session_credit_cost?: number | null;
}


/** GET /api/v1/profiles/me — composite view for the SPA (shapes follow backend contracts). */
export interface MentoringProfileMeResponse {
  is_admin: boolean;
  mentee_profile?: {
    user_id: string;
    first_name?: string | null;
    last_name?: string | null;
    learning_goals: string[];
    education_level: string;
    is_minor: boolean;
    guardian_consent_status: GuardianConsentStatus;
    /** Mirrored from gamification wallet; mentoring DB cache updated on GET /profiles/me. */
    cached_credit_score: number;
  };
  mentor_profile?: {
    user_id: string;
    first_name?: string | null;
    last_name?: string | null;
    tier_id: MentorTierId;
    is_accepting_requests: boolean;
    expertise_areas: string[];
    total_hours_mentored: number;
  };
  /** Legacy aliases if still used */
  mentee?: MentoringProfileMeResponse["mentee_profile"];
  mentor?: MentoringProfileMeResponse["mentor_profile"];
}

export interface PostMenteeProfileBody {
  learning_goals: string[];
  education_level: string;
}

export interface SchedulingBookBody {
  connection_id: string;
  slot_id: string;
  agreed_cost: number;
}

export interface MentorshipRequestBody {
  mentor_id: string;
  intro_message: string;
}

export interface AiRecommendationItem {
  mentor_id: string;
  score?: number;
  /** Mentor row in User Service — required for POST /api/v1/requests */
  mentor_profile_id?: string | null;
  display_name?: string | null;
  expertise_areas?: string[] | null;
  tier_id?: string | null;
  session_credit_cost?: number | null;
}
