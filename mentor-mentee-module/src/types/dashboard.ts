/** GET /dashboard/upcoming-session — empty state when no session or request */
export type UpcomingSessionResponse = {
  session_id: string | null;
  booking_request_id: string | null;
  start_time: string | null;
  meeting_url: string | null;
  status: string | null;
  partner_name: string | null;
  session_credit_cost?: number | null;
  price?: number | null;
};

export type UpcomingSessionItemResponse = {
  session_id: string | null;
  booking_request_id: string | null;
  start_time: string;
  meeting_url: string | null;
  status: string;
  partner_name: string | null;
  session_credit_cost?: number | null;
  price?: number | null;
  mentor?: { id: string; name: string; tier: string } | null;
  mentee?: { id: string; name: string } | null;
};

export type GoalItemResponse = {
  id: string;
  title: string;
  status: string;
};

export type VaultItemResponse = {
  session_id: string;
  start_time: string;
  notes: Record<string, unknown>;
  mentor_rating: number | null;
  mentee_rating: number | null;
  partner_name: string | null;
};

/** GET /dashboard/stats */
export type DashboardStatsResponse = {
  active_partners: number;
  hours_total: number;
  hours_this_week: number;
  sessions_completed: number;
  active_sessions: number;
};

/** GET /dashboard/session-booking-requests — mentoring_db.session_booking_requests */
export type SessionBookingLedgerItem = {
  request_id: string;
  status: string;
  requested_time: string | null;
  created_at: string | null;
  viewer_role: "mentee" | "mentor";
  partner_name: string | null;
  mentor_user_id: string | null;
  mentee_user_id: string | null;
};
