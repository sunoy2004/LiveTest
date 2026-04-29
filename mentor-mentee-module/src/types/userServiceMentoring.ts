export type ConnectedMentorItem = {
  connection_id: string;
  mentor_id: string;
  mentor_name: string;
  expertise: string[];
  total_hours: number;
  tier: string | null;
  session_credit_cost: number | null;
};

export type AvailableSlotItem = {
  slot_id: string;
  start_time: string;
  end_time: string;
  /** Coins charged when booking this slot (from User Service time_slots.cost_credits). */
  cost_credits: number;
  is_booked?: boolean;
  pending_request_id?: string | null;
};


export type BookSessionSimpleResponse = {
  request_id: string;
  session_id: string | null;
  status: string;
  meeting_url: string | null;
  start_time: string;
};

export type IncomingSessionRequestItem = {
  request_id: string;
  connection_id: string;
  slot_id: string;
  start_time: string;
  end_time: string;
  agreed_cost: number;
  mentee_name: string;
  status: string;
};

export type MentorProfilePublic = {
  id: string;
  user_id: string;
  tier_id: string;
  pricing_tier: string;
  base_credit_override: number | null;
  is_accepting_requests: boolean;
  expertise_areas: string[] | null;
  total_hours_mentored: number;
  headline?: string | null;
  bio?: string | null;
  current_title?: string | null;
  current_company?: string | null;
  years_experience?: number | null;
  professional_experiences?: Array<Record<string, unknown>> | null;
};

export type MentorProfileDetail = {
  mentor_profile: MentorProfilePublic;
  email: string;
  display_name: string;
};

