export type SchedulingSlot = {
  id: string;
  start_time: string;
  end_time: string;
  cost_credits: number;
};

export type BookingSchedulingContext = {
  connection_id: string;
  mentor_display_name: string;
  /** @deprecated Prefer gamification wallet; optional for legacy responses. */
  cached_credit_score?: number;
  slots: SchedulingSlot[];
};

export type BookSessionResponse = {
  request_id: string;
  session_id: string | null;
  status: string;
  meeting_url: string | null;
  start_time: string;
};
